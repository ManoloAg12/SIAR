import requests
import secrets
import re
from sqlalchemy import desc
from config import Config
from flask import (
    Blueprint, render_template, request, jsonify, g, 
    redirect, url_for, flash, 
    session # <--- IMPORTANTE: Importar 'session'
)
# Importamos la instancia 'db' y nuestros modelos
from . import db
from .models import (
    tbl_usuarios, tbl_paises, tbl_configuracion, 
    tbl_lecturas_humedad, tbl_bitacora_eventos, tbl_dispositivos, tbl_perfiles_riego, 
    tbl_horarios
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text 
from flask_mail import Message # <-- AÑADIR IMPORTACIÓN
from . import db, mail # <-- AÑADIR 'mail
from sqlalchemy import text, not_
from datetime import datetime, timezone, timedelta
# --- ¡NUEVO! DEFINIMOS SU ZONA HORARIA LOCAL ---
# GMT-6 (El Salvador)
USER_TIMEZONE = timezone(timedelta(hours=-6))

bp = Blueprint('main', __name__)


# --- FUNCIÓN HELPER PARA ENVIAR CORREO ---
def send_welcome_email(user_email, user_name):
    """Envía el correo de bienvenida en segundo plano."""
    try:
        msg = Message(
            subject="¡Bienvenido a SIAR!",
            recipients=[user_email],
            html=render_template('email/welcome_email.html', user_name=user_name)
        )
        mail.send(msg)
        print(f"Correo de bienvenida enviado a {user_email}")
    except Exception as e:
        print(f"Error al enviar correo de bienvenida: {e}")
        # No detenemos el registro si el correo falla, solo lo reportamos.
        pass

# --- Rutas Web (Para el navegador) ---
@bp.route('/')
@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Muestra la página de login, maneja el registro y el inicio de sesión."""
    
    if 'user_id' in session:
        return redirect(url_for('main.home'))

    if request.method == 'POST':
        form_type = request.form.get('form_type')
        
        if form_type == 'register':
            try:
                # 1. Recoger datos
                nombre_completo = request.form.get('nombre_completo')
                email = request.form.get('email')
                nombre_usuario = request.form.get('nombre_usuario')
                password = request.form.get('password')
                
                pais = tbl_paises.query.filter_by(codigo_iso=request.form.get('pais')).first()
                if not pais:
                    flash(f'Error: País no encontrado.', 'danger')
                    return redirect(url_for('main.login'))

                # 2. Crear objeto de usuario
                nuevo_usuario = tbl_usuarios(
                    nombre_completo=nombre_completo,
                    email=email,
                    nombre_usuario=nombre_usuario,
                    telefono=request.form.get('telefono'),
                    direccion=request.form.get('direccion'),
                    ciudad=request.form.get('ciudad'),
                    pais_id=pais.id 
                )
                nuevo_usuario.set_password(password)
                
                # 3. Guardar en BBDD
                db.session.add(nuevo_usuario)
                db.session.commit()
                
                # --- ¡NUEVO! ENVIAR CORREO DE BIENVENIDA ---
                send_welcome_email(nuevo_usuario.email, nuevo_usuario.nombre_completo)
                # -------------------------------------------
                
                flash('¡Cuenta creada exitosamente! Se ha enviado un correo de bienvenida.', 'success')
            
            except IntegrityError:
                db.session.rollback() 
                flash('Error: El correo electrónico o el nombre de usuario ya están registrados.', 'danger')
            except Exception as e:
                db.session.rollback()
                flash(f'Error inesperado al crear la cuenta: {e}', 'danger')
            
            return redirect(url_for('main.login'))
        
        elif form_type == 'login':
            # --- LÓGICA DE INICIO DE SESIÓN ---
            try:
                nombre_usuario = request.form.get('nombre_usuario')
                password = request.form.get('password')
                
                usuario = tbl_usuarios.query.filter_by(nombre_usuario=nombre_usuario).first()
                
                if usuario and usuario.check_password(password):
                    session.clear()
                    session['user_id'] = usuario.id
                    session['user_name'] = usuario.nombre_completo 
                    
                    return redirect(url_for('main.home'))
                else:
                    flash('Usuario o contraseña incorrectos.', 'danger')
            
            except Exception as e:
                flash(f'Error inesperado al iniciar sesión: {e}', 'danger')

            return redirect(url_for('main.login'))

    return render_template('login.html')

@bp.route('/logout')
def logout():
    """Cierra la sesión del usuario."""
    session.clear() 
    flash('Ha cerrado sesión exitosamente.', 'success')
    return redirect(url_for('main.login'))

#Api para crear perfiles de riego 
# En siar_app/routes.py

@bp.route('/api/crear_perfil', methods=['POST'])
def crear_perfil():
    """Crea un nuevo perfil de riego (con doble umbral)."""
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "No autorizado"}), 401
    
    try:
        data = request.form
        umbral_min = data.get('umbral_humedad_min')
        umbral_max = data.get('umbral_humedad_max')
        duracion = data.get('duracion_riego_seg')

        if not (umbral_min and umbral_max and duracion):
            return jsonify({"status": "error", "message": "Todos los campos numéricos son obligatorios"}), 400

        # Validar que min sea menor que max
        if int(umbral_min) >= int(umbral_max):
             return jsonify({"status": "error", "message": "El Umbral Mínimo debe ser menor que el Umbral Máximo"}), 400

        nuevo_perfil = tbl_perfiles_riego(
            usuario_id=session['user_id'],
            nombre_perfil=data.get('nombre_perfil'),
            descripcion=data.get('descripcion'),
            umbral_humedad_min=int(umbral_min),
            umbral_humedad_max=int(umbral_max),
            duracion_riego_seg=int(duracion)
        )
        db.session.add(nuevo_perfil)
        db.session.commit()
        
        flash('¡Perfil creado exitosamente!', 'success')
        return jsonify({"status": "ok", "message": "Perfil creado"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

# api para el clima
def get_weather(city, country_code):
    """
    Función helper para llamar a la API de OpenWeatherMap.
    """
    if not Config.WEATHER_API_KEY or Config.WEATHER_API_KEY == 'SU_API_KEY_AQUI':
        print("ADVERTENCIA: API Key de OpenWeatherMap no configurada.")
        return None

    try:
        # Construimos la URL de la API
        base_url = "http://api.openweathermap.org/data/2.5/weather"
        params = {
            'q': f'{city},{country_code}',
            'appid': Config.WEATHER_API_KEY,
            'units': 'metric', # Para grados Celsius
            'lang': 'es'      # Para descripciones en español
        }
        
        response = requests.get(base_url, params=params, timeout=5)
        response.raise_for_status() # Lanza un error si la petición falla
        
        data = response.json()
        
        # Procesamos la respuesta en un diccionario simple
        weather_info = {
            "temp": int(round(data['main']['temp'])), # 23.5 -> 24
            "description": data['weather'][0]['description'].capitalize(), # "nubes" -> "Nubes"
            "icon": data['weather'][0]['icon'], # Ej: "04d"
            "main_condition": data['weather'][0]['main'] # Ej: "Rain", "Clouds", "Clear"
        }
        
        return weather_info

    except requests.exceptions.RequestException as e:
        print(f"Error al llamar a la API del clima: {e}")
        return None
    except KeyError:
        print("Error: Respuesta inesperada de la API del clima.")
        return None



# En siar_app/routes.py
# En siar_app/routes.py

# --- RUTA PRINCIPAL (MODIFICADA) ---
@bp.route('/home')
def home():
    if 'user_id' not in session:
        flash('Debe iniciar sesión para ver esta página.', 'info')
        return redirect(url_for('main.login'))
    
    current_user_id = session['user_id']
    user_name = session.get('user_name', 'Usuario')
    device_status = 'Desconocido'
    configuracion_actual = None 
    horarios_list = []
    is_raining = False 
    has_events = False 
    
    try:
        usuario = tbl_usuarios.query.get(current_user_id)
        if not usuario:
            flash("Error de sesión, inicie de nuevo.", 'danger')
            return redirect(url_for('main.login'))

        dispositivos_list = tbl_dispositivos.query.filter_by(usuario_id=current_user_id).order_by(tbl_dispositivos.nombre_dispositivo).all()
        perfiles_list = tbl_perfiles_riego.query.order_by(tbl_perfiles_riego.nombre_perfil).all()
        
        # Asumimos 1 dispositivo por ahora
        dispositivo = dispositivos_list[0] if dispositivos_list else None
        
        if dispositivo:
            device_status = dispositivo.estado_actual
            configuracion_actual = dispositivo.configuracion
            # ¡NUEVO! Cargar los horarios de ESE dispositivo
            horarios_list = tbl_horarios.query.filter_by(dispositivo_id=dispositivo.id).order_by(tbl_horarios.hora_riego).all()
        else:
            device_status = 'No Asignado'

        # Chequeo de clima
        if usuario.ciudad and usuario.pais:
            weather_data = get_weather(usuario.ciudad, usuario.pais.codigo_iso)
            if weather_data:
                condiciones_lluvia = ['Rain', 'Drizzle', 'Thunderstorm', 'Snow']
                if weather_data['main_condition'] in condiciones_lluvia:
                    is_raining = True
        
        # Chequeo de eventos (para botón de reporte)
        if dispositivos_list:
            device_ids = [d.id for d in dispositivos_list]
            event_count = db.session.query(tbl_bitacora_eventos.id).filter(
                tbl_bitacora_eventos.dispositivo_id.in_(device_ids),
                tbl_bitacora_eventos.tipo_evento.like('riego%')
            ).count()
            if event_count > 0:
                has_events = True
            
    except Exception as e:
        print(f"Error al buscar datos del dashboard: {e}")

    # (Lógica de db_status sin cambios)
    db_status = "Desconectado"
    try:
        db.session.execute(text('SELECT 1'))
        db_status = "Conectado (SQLAlchemy)"
    except Exception as e:
        db_status = f"Error: {e}"

    return render_template(
        'home.html', 
        db_status=db_status, 
        user_name=user_name,
        device_status=device_status,
        perfiles=perfiles_list,
        current_user_id=current_user_id,
        weather=weather_data,
        configuracion_actual=configuracion_actual,
        dispositivos=dispositivos_list,
        horarios=horarios_list, # <-- ¡NUEVO!
        is_raining=is_raining,
        has_events=has_events
    )

# En siar_app/routes.py
# (Asegúrese de tener Message, mail, tbl_usuarios, tbl_dispositivos,
# tbl_bitacora_eventos, session, jsonify, y render_template importados)

@bp.route('/api/send_report_email', methods=['POST'])
def send_report_email():
    """
    Recopila todos los datos del usuario y envía el reporte por correo.
    """
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "No autorizado"}), 401

    try:
        usuario = tbl_usuarios.query.get(session['user_id'])
        if not usuario:
            return jsonify({"status": "error", "message": "Usuario no encontrado"}), 404

        # 1. Obtener todos los dispositivos del usuario
        dispositivos_usuario = tbl_dispositivos.query.filter_by(usuario_id=usuario.id).all()
        if not dispositivos_usuario:
             return jsonify({"status": "error", "message": "No tiene dispositivos"}), 400

        # 2. Obtener los IDs de esos dispositivos
        device_ids = [d.id for d in dispositivos_usuario]

        # 3. Obtener TODOS los eventos de riego de esos dispositivos
        eventos_riego = tbl_bitacora_eventos.query.filter(
            tbl_bitacora_eventos.dispositivo_id.in_(device_ids),
            tbl_bitacora_eventos.tipo_evento.like('riego%')
        ).order_by(tbl_bitacora_eventos.timestamp.desc()).all()

        if not eventos_riego:
            return jsonify({"status": "error", "message": "No hay eventos de riego para reportar."}), 400

        # 4. Renderizar el template del email con los datos
        html_body = render_template(
            'email/report_email.html', 
            usuario=usuario, 
            dispositivos=dispositivos_usuario, # Lista de objetos dispositivo
            eventos=eventos_riego             # Lista de objetos evento
        )
        
        # 5. Configurar y enviar el correo
        msg = Message(
            subject="SIAR - Reporte de Actividad de Riego",
            recipients=[usuario.email],
            html=html_body
        )
        mail.send(msg)
        
        print(f"Reporte de correo enviado exitosamente a {usuario.email}")
        return jsonify({"status": "ok", "message": "Reporte enviado exitosamente."})

    except Exception as e:
        print(f"Error al enviar reporte por correo: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
# crear dispositivo 
# ===== CAMBIO 1: API /crear_dispositivo (MODIFICADA) =====
@bp.route('/api/crear_dispositivo', methods=['POST'])
def crear_dispositivo():
    """
    Crea un nuevo dispositivo.
    Genera una API Key única.
    YA NO CREA UNA CONFIGURACIÓN POR DEFECTO.
    """
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "No autorizado"}), 401
    
    try:
        data = request.form
        nombre_dispositivo = data.get('nombre_dispositivo')
        
        if not nombre_dispositivo:
            return jsonify({"status": "error", "message": "El nombre es obligatorio"}), 400

        # 1. Generar la clave única (64 caracteres hexadecimales)
        api_key = secrets.token_hex(32)

        # 2. Crear el dispositivo
        nuevo_dispositivo = tbl_dispositivos(
            usuario_id=session['user_id'],
            nombre_dispositivo=nombre_dispositivo,
            device_api_key=api_key,
            estado_actual='offline'
        )
        db.session.add(nuevo_dispositivo)
        db.session.commit()

        # 3. YA NO SE CREA LA CONFIGURACIÓN POR DEFECTO (ELIMINADO)
        
        flash(f'¡Dispositivo "{nombre_dispositivo}" creado con éxito!', 'success')
        return jsonify({"status": "ok", "message": "Dispositivo creado"})

    except Exception as e:
        db.session.rollback()
        print(f"Error al crear dispositivo: {e}")
        flash(f'Error al crear dispositivo: {e}', 'danger')
        return jsonify({"status": "error", "message": str(e)}), 500

#api para aplicar perfil 
# ===== CAMBIO 2: API /aplicar_perfil (MODIFICADA) =====

# ========================================================
# En siar_app/routes.py

@bp.route('/api/crear_horario', methods=['POST'])
def crear_horario():
    """
    Crea o ACTUALIZA un horario programado.
    ¡MODIFICADO! Ahora TAMBIÉN actualiza el perfil de emergencia.
    """
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "No autorizado"}), 401
    
    try:
        data = request.form
        perfil_id = data.get('perfil_id')
        hora_riego_str = data.get('hora_riego') 
        dias_semana_list = request.form.getlist('dias_semana')
        device_id = data.get('device_id')
        
        if not device_id:
             return jsonify({"status": "error", "message": "Falta 'device_id'"}), 400
        
        dispositivo = tbl_dispositivos.query.filter_by(
            id=device_id, 
            usuario_id=session['user_id']
        ).first()
        
        if not dispositivo:
            return jsonify({"status": "error", "message": "Dispositivo no encontrado"}), 404
        
        if not perfil_id or not hora_riego_str or not dias_semana_list:
            return jsonify({"status": "error", "message": "Todos los campos son requeridos"}), 400

        dias_string = ",".join(dias_semana_list)
        hora_obj = datetime.strptime(hora_riego_str, '%H:%M').time()

        # --- ¡LÓGICA DE CONFIGURACIÓN CORREGIDA! ---
        config_activa = dispositivo.configuracion
        
        if not config_activa:
            # Si no hay config, la creamos con el perfil_id
            config_activa = tbl_configuracion(
                dispositivo_id=dispositivo.id,
                perfil_activo_id=perfil_id, 
                modo_automatico=True
            )
            db.session.add(config_activa)
            print(f"Configuración creada para Dispositivo {dispositivo.id}")
        else:
            # Si YA hay config, FORZAMOS la actualización del perfil de emergencia.
            config_activa.perfil_activo_id = perfil_id 
            print(f"Perfil de emergencia actualizado a ID: {perfil_id} para Dispositivo {dispositivo.id}")
        # --- FIN DE CORRECCIÓN ---

        # --- Lógica de "Upsert" de Horario (sin cambios) ---
        mensaje_exito = ""
        # 1. Buscar si ya existe CUALQUIER horario para ESE dispositivo
        horario_existente = tbl_horarios.query.filter_by(
            dispositivo_id=dispositivo.id
        ).first()

        if horario_existente:
            # 2. Si existe, ACTUALIZARLO (sobrescribir)
            print(f"Actualizando horario existente (ID: {horario_existente.id}) a las {hora_obj}...")
            horario_existente.perfil_id = perfil_id
            horario_existente.dias_semana = dias_string
            horario_existente.hora_riego = hora_obj 
            horario_existente.activo = True
            mensaje_exito = "Horario actualizado exitosamente."
        else:
            # 3. Si no existe, CREARLO
            print(f"Creando nuevo horario a las {hora_obj}...")
            nuevo_horario = tbl_horarios(
                dispositivo_id=dispositivo.id,
                perfil_id=perfil_id,
                hora_riego=hora_obj,
                dias_semana=dias_string,
                activo=True
            )
            db.session.add(nuevo_horario)
            mensaje_exito = "Horario creado exitosamente."
        # --- Fin Lógica Upsert ---
        
        db.session.commit()
        
        flash(mensaje_exito, 'success')
        return jsonify({"status": "ok", "message": mensaje_exito}), 201

    except Exception as e:
        db.session.rollback()
        print(f"Error al crear/actualizar horario: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
#dinamismo para las cartas
# --- ¡REEMPLAZAR LA FUNCIÓN ANTIGUA POR ESTA! ---

# En siar_app/routes.py
# (Asegúrese de tener 'get_weather', 'tbl_usuarios', etc. importados)
@bp.route('/api/system_status')
def get_system_status():
    """
    Devuelve el estado actual del sistema para el sondeo (polling) del frontend.
    """
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "No autorizado"}), 401

    try:
        # 1. Obtener el dispositivo y su estado
        dispositivo = tbl_dispositivos.query.filter_by(usuario_id=session['user_id']).first()
        
        if not dispositivo:
            return jsonify({
                "device_status": "No Asignado",
                "is_raining": False,
                "modo_automatico": False
            })

        device_status = dispositivo.estado_actual # 'online', 'offline', 'regando'

        # 2. Obtener la configuración
        config = tbl_configuracion.query.filter_by(dispositivo_id=dispositivo.id).first()
        modo_automatico = config.modo_automatico if config else False

        # 3. (IMPORTANTE) Lógica para verificar la lluvia
        # Necesitamos re-llamar a la API del clima aquí
        is_raining = False # Por defecto
        usuario = tbl_usuarios.query.get(session['user_id'])
        
        if usuario.ciudad and usuario.pais:
            weather_data = get_weather(usuario.ciudad, usuario.pais.codigo_iso)
            if weather_data and weather_data['main_condition'] == 'Rain':
                is_raining = True

        return jsonify({
            "device_status": device_status,
            "is_raining": is_raining,
            "modo_automatico": modo_automatico
        })

    except Exception as e:
        print(f"Error en /api/system_status: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# En siar_app/routes.py
# (Asegúrese de tener 'datetime', 'timezone', 'tbl_usuarios', 'db', 'text', 'get_weather', 'jsonify', 'session' importados)

@bp.route('/api/get_dynamic_status')
def get_dynamic_status():
    """
    Devuelve el estado actualizado.
    ¡MODIFICADO! Esta función YA NO pone dispositivos 'online',
    solo se encarga de marcarlos 'offline' por timeout.
    """
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "No autorizado"}), 401
        
    device_status_val = 'Desconocido'
    db_status_val = "Desconectado"
    device_id_val = None
    device_status_text = 'Desconocido'
    is_raining_val = False 
    
    try:
        usuario = tbl_usuarios.query.get(session['user_id']) 
        if not usuario:
             return jsonify({"status": "error", "message": "Usuario no encontrado"}), 404

        # 1. Revisar estado del dispositivo
        dispositivo = tbl_dispositivos.query.filter_by(usuario_id=session['user_id']).first()
        
        if dispositivo:
            device_id_val = dispositivo.id
            device_status_val = dispositivo.estado_actual
            
            # --- LÓGICA DE TIMEOUT MODIFICADA ---
            
            # Solo aplicamos timeout si el dispositivo CREE estar 'online' o 'regando'
            if device_status_val in ['online', 'regando']:
                
                if dispositivo.last_heartbeat:
                    ahora_utc = datetime.now(timezone.utc)
                    segundos_transcurridos = (ahora_utc - dispositivo.last_heartbeat).total_seconds()
                    
                    # Mantenemos los 20 segundos como solicitó
                    TIMEOUT_SEGUNDOS = 20 

                    if segundos_transcurridos > TIMEOUT_SEGUNDOS:
                        # Ha pasado demasiado tiempo, lo marcamos offline
                        print(f"TIMEOUT: Dispositivo {dispositivo.id} está offline. Último latido hace {segundos_transcurridos}s.")
                        dispositivo.estado_actual = 'offline' 
                        db.session.commit()
                        device_status_val = 'offline'
                    
                    # Si no ha pasado el timeout, 'device_status_val' ('online' o 'regando') es correcto.
                    # ELIMINAMOS EL BLOQUE 'ELSE' QUE FORZABA A 'ONLINE'.
                    
                else:
                    # Si el estado es 'online' pero no hay latido (recién creado o error),
                    # lo forzamos a 'offline' para corregir el estado.
                    print(f"CORRECCIÓN: Dispositivo {dispositivo.id} estaba 'online' sin latido. Forzando a 'offline'.")
                    dispositivo.estado_actual = 'offline'
                    db.session.commit()
                    device_status_val = 'offline'
            
            # Si el estado es 'offline' o 'offline_manual', simplemente lo reportamos.
            # No hacemos nada más. 'device_status_val' ya es correcto.
            
            # --- Fin Lógica Timeout ---
            
        else:
            device_status_val = 'No Asignado'

        # 2. Revisar estado de la BBDD
        try:
            db.session.execute(text('SELECT 1'))
            db_status_val = "Conectado (SQLAlchemy)"
        except Exception as e:
            db_status_val = f"Error: {e}"

        # 3. Revisar estado del clima
        if usuario.ciudad and usuario.pais:
            weather_data = get_weather(usuario.ciudad, usuario.pais.codigo_iso)
            if weather_data:
                condiciones_lluvia = ['Rain', 'Drizzle', 'Thunderstorm', 'Snow']
                if weather_data['main_condition'] in condiciones_lluvia:
                    is_raining_val = True
            
    except Exception as e:
        db.session.rollback()
        print(f"Error al buscar dispositivo o clima: {e}")
        device_status_val = 'Error'


    # 4. Formatear el texto de estado
    if device_status_val == 'offline': device_status_text = 'Offline'
    elif device_status_val == 'online': device_status_text = 'Online'
    elif device_status_val == 'regando': device_status_text = 'Regando'
    elif device_status_val == 'offline_manual': device_status_text = 'Mantenimiento'
    else: device_status_text = 'Desconocido'

    # 5. Devolver todo como JSON
    return jsonify({
        "device_status": device_status_val,
        "db_status": db_status_val,
        "device_id": device_id_val,
        "device_status_text": device_status_text,
        "is_raining": is_raining_val
    })


#dinamismo para el togle de activar el modo automatico
@bp.route('/api/toggle_modo_automatico', methods=['POST'])
def toggle_modo_automatico():
    """
    Activa o desactiva el modo de riego automático para el dispositivo del usuario.
    """
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "No autorizado"}), 401
    
    try:
        data = request.json
        new_state = data.get('new_state') # Recibirá true o false
        
        if new_state is None:
            return jsonify({"status": "error", "message": "Falta el 'new_state'"}), 400

        # Asumimos un dispositivo por usuario por ahora
        dispositivo = tbl_dispositivos.query.filter_by(usuario_id=session['user_id']).first()
        
        if not dispositivo or not dispositivo.configuracion:
            return jsonify({"status": "error", "message": "Configuración no encontrada"}), 404

        # Actualizar el estado en la base de datos
        config_activa = dispositivo.configuracion
        config_activa.modo_automatico = new_state
        
        db.session.commit()
        
        return jsonify({"status": "ok", "message": "Modo automático actualizado."})

    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    

@bp.route('/api/ultima_humedad')
def get_ultima_humedad():
    """
    Endpoint para que el dashboard consulte la humedad más reciente.
    ¡MODIFICADO! Solo devuelve un valor si el dispositivo está 'online'.
    """
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "No autorizado"}), 401
    
    try:
        # Buscamos el dispositivo asociado al usuario en sesión
        dispositivo = tbl_dispositivos.query.filter_by(usuario_id=session['user_id']).first()
        
        if not dispositivo:
            return jsonify({"humedad": "--"}) # Usuario no tiene dispositivo

        # --- ¡NUEVA LÓGICA DE VERIFICACIÓN! ---
        # Comprobamos el estado del dispositivo ANTES de buscar la humedad.
        # Este estado es actualizado por la lógica de timeout en /api/get_dynamic_status
        if dispositivo.estado_actual not in ['online', 'regando']:
            # Si el dispositivo está 'offline', 'error', etc., no mostramos la última humedad.
            return jsonify({"humedad": "--"}) 
        # --- FIN DE LA LÓGICA DE VERIFICACIÓN ---

        # Si llegamos aquí, el dispositivo SÍ está online.
        # Buscamos la última (más reciente) lectura de ese dispositivo
        lectura = tbl_lecturas_humedad.query.filter_by(
            dispositivo_id=dispositivo.id
        ).order_by(tbl_lecturas_humedad.timestamp.desc()).first()
        
        if lectura:
            # Devolvemos el valor redondeado
            return jsonify({"humedad": int(round(lectura.valor_humedad))})
        else:
            # No se han registrado lecturas (aunque esté online)
            return jsonify({"humedad": "--"}) 
    
    except Exception as e:
        print(f"Error al obtener última humedad: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    

@bp.route('/api/actividad_reciente')
def get_actividad_reciente():
    """
    Endpoint para que el dashboard consulte los últimos eventos.
    """
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "No autorizado"}), 401
    
    try:
        dispositivo = tbl_dispositivos.query.filter_by(usuario_id=session['user_id']).first()
        
        if not dispositivo:
            return jsonify([]) # Devuelve lista vacía si no hay dispositivo

        # Buscamos los últimos 5 eventos para este dispositivo
        eventos = tbl_bitacora_eventos.query.filter_by(dispositivo_id=dispositivo.id).order_by(tbl_bitacora_eventos.timestamp.desc()).limit(5).all()
        
        # Formateamos la salida para que sea amigable (JSON)
        lista_actividad = []
        for ev in eventos:
            lista_actividad.append({
                "tipo_evento": ev.tipo_evento,
                "descripcion": ev.descripcion,
                # Formateamos el timestamp para que sea legible
                "timestamp": ev.timestamp.strftime('%d/%m/%Y %I:%M %p') 
            })
            
        return jsonify(lista_actividad)
    
    except Exception as e:
        print(f"Error al obtener actividad reciente: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    
# api para la configuracion del mantenimiento del dispositivo
@bp.route('/api/set_device_manual_status', methods=['POST'])
def set_device_manual_status():
    """
    Endpoint para el switch Habilitar/Deshabilitar del dashboard.
    """
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "No autorizado"}), 401
    
    try:
        data = request.json
        device_id = data.get('device_id')
        new_state_bool = data.get('new_state') # true = Habilitado, false = Deshabilitado

        if device_id is None or new_state_bool is None:
            return jsonify({"status": "error", "message": "Faltan 'device_id' o 'new_state'"}), 400

        # Buscamos el dispositivo y nos aseguramos que pertenece al usuario
        dispositivo = tbl_dispositivos.query.filter_by(
            id=device_id, 
            usuario_id=session['user_id']
        ).first()

        if not dispositivo:
            return jsonify({"status": "error", "message": "Dispositivo no encontrado"}), 404

        if new_state_bool == True:
            # User quiere "Habilitar". Lo ponemos en 'offline'
            # y dejamos que el ESP32 o el timeout hagan el resto.
            dispositivo.estado_actual = 'offline' 
        else:
            # User quiere "Deshabilitar" (Mantenimiento).
            dispositivo.estado_actual = 'offline_manual' # Un estado especial
        
        db.session.commit()
        
        return jsonify({"status": "ok", "new_db_state": dispositivo.estado_actual})

    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    
# En siar_app/routes.py

@bp.route('/api/consumo_semanal')
def get_consumo_semanal():
    """
    (PARA EL DASHBOARD)
    Calcula el consumo de agua de los últimos 7 días para el gráfico.
    ¡MODIFICADO! Ahora usa la zona horaria local (GMT-6) para agrupar los días.
    """
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "No autorizado"}), 401
    
    try:
        dispositivo = tbl_dispositivos.query.filter_by(usuario_id=session['user_id']).first()
        if not dispositivo:
            return jsonify({"labels": [], "data": []})

        caudal = Config.LITROS_POR_SEGUNDO
        
        labels = []
        data = []
        
        # --- ¡CAMBIO AQUÍ! ---
        # Antes: hoy = datetime.now(timezone.utc).date()
        # Ahora: Usamos la hora local para saber qué día es "hoy"
        hoy_local = datetime.now(USER_TIMEZONE).date() 
        # --- FIN DEL CAMBIO ---

        regex_segundos = re.compile(r'(\d+(\.\d+)?)s')
        
        for i in range(6, -1, -1):
            dia = hoy_local - timedelta(days=i) # 'dia' es ahora una fecha local (ej: Martes 11)
            
            dias_semana = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sab', 'Dom']
            labels.append(f"{dias_semana[dia.weekday()]} {dia.day:02d}")

            # --- ¡CAMBIO AQUÍ! ---
            # Creamos los límites del día (00:00 y 23:59) USANDO LA ZONA HORARIA LOCAL
            
            # Ej: 11-Nov 00:00:00 (GMT-6)
            inicio_dia_local = datetime(dia.year, dia.month, dia.day, 0, 0, 0, tzinfo=USER_TIMEZONE)
            
            # Ej: 12-Nov 00:00:00 (GMT-6)
            fin_dia_local = inicio_dia_local + timedelta(days=1)
            # --- FIN DEL CAMBIO ---
            
            eventos_del_dia = tbl_bitacora_eventos.query.filter(
                tbl_bitacora_eventos.dispositivo_id == dispositivo.id,
                tbl_bitacora_eventos.tipo_evento.like('riego%'),
                # SQLAlchemy convertirá automáticamente estas horas locales a UTC
                # para compararlas con la base de datos (que está en UTC/TIMESTAMPTZ)
                tbl_bitacora_eventos.timestamp >= inicio_dia_local,
                tbl_bitacora_eventos.timestamp < fin_dia_local
            ).all()

            total_segundos_dia = 0
            for evento in eventos_del_dia:
                if evento.descripcion and isinstance(evento.descripcion, str):
                    match = regex_segundos.search(evento.descripcion)
                    if match:
                        total_segundos_dia += float(match.group(1))
            
            consumo_dia = round(total_segundos_dia * caudal, 1)
            data.append(consumo_dia)

        return jsonify({"labels": labels, "data": data})

    except Exception as e:
        print(f"Error al obtener consumo semanal: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
# (Sin cambios)

# api para conectar asl ESP32
# En siar_app/routes.py

# En siar_app/routes.py

@bp.route('/api/configuracion', methods=['GET'])
def get_configuracion():
    """
    Entrega la configuración al ESP32.
    NO envía umbrales si no hay perfil asignado.
    """
    
    api_key = request.args.get('device_key')
    if not api_key: return jsonify({"error": "Falta 'device_key'"}), 400
    dispositivo = tbl_dispositivos.query.filter_by(device_api_key=api_key).first()
    if not dispositivo: return jsonify({"error": "Dispositivo no autorizado"}), 404
    
    usuario = dispositivo.usuario
    config_obj = dispositivo.configuracion
    
    is_raining = False
    if usuario.ciudad and usuario.pais:
        weather_data = get_weather(usuario.ciudad, usuario.pais.codigo_iso)
        if weather_data:
            condiciones_lluvia = ['Rain', 'Drizzle', 'Thunderstorm', 'Snow']
            if weather_data['main_condition'] in condiciones_lluvia:
                is_raining = True

    # --- LÓGICA DE CONFIGURACIÓN MODIFICADA ---
    
    # 1. Preparamos el JSON base
    config_data = {
        "modo_programado_activo": False,
        "horarios": []
    }
    
    # 2. Revisamos si hay configuración (perfil de emergencia)
    if config_obj and config_obj.perfil_activo:
        # ¡SÍ HAY PERFIL! Añadimos los umbrales.
        config_data["umbral_min"] = config_obj.perfil_activo.umbral_humedad_min
        config_data["umbral_max"] = config_obj.perfil_activo.umbral_humedad_max
        
        # 3. Revisamos el modo automático (solo si hay config)
        if config_obj.modo_automatico and not is_raining:
            config_data["modo_programado_activo"] = True

    # 4. (Sin cambios) Obtenemos los horarios
    horarios_db = tbl_horarios.query.filter_by(dispositivo_id=dispositivo.id, activo=True).all()
    lista_horarios_json = []
    for h in horarios_db:
        lista_horarios_json.append({
            "hora": h.hora_riego.strftime('%H:%M'),
            "dias": h.dias_semana,
            "duracion": h.perfil.duracion_riego_seg
        })
    config_data["horarios"] = lista_horarios_json
    # --- FIN DE MODIFICACIÓN ---

    return jsonify(config_data)

#Api para conocer las lecturas de la humedad del suelo#Api para conocer las lecturas de la humedad del suelo
#Api para conocer las lecturas de la humedad del suelo
# En siar_app/routes.py
# (Asegúrese de tener 'datetime', 'timezone' importados)

@bp.route('/api/lectura', methods=['POST'])
def post_lectura():
    datos = request.json
    humedad = datos.get('humedad')
    api_key = datos.get('device_key')
    
    if humedad is None or api_key is None:
        return jsonify({"status": "error", "message": "Faltan 'humedad' o 'device_key'"}), 400
        
    try:
        dispositivo = tbl_dispositivos.query.filter_by(device_api_key=api_key).first()
        if not dispositivo:
            return jsonify({"status": "error", "message": "Dispositivo no encontrado"}), 404

        # --- ¡LÓGICA MODIFICADA! ---
        
        # 1. El latido actualiza el timestamp
        dispositivo.last_heartbeat = datetime.now(timezone.utc)

        # 2. Solo cambia a 'online' SI el estado era 'offline'.
        # Respeta 'offline_manual', 'regando', y 'online'.
        if dispositivo.estado_actual == 'offline':
             dispositivo.estado_actual = 'online'
        
        # 3. Guardamos la lectura (SIN RECHAZAR 0% o 100%)
        nueva_lectura = tbl_lecturas_humedad(
            dispositivo_id=dispositivo.id,
            valor_humedad=humedad
        )
        db.session.add(nueva_lectura)
        print(f"Datos (latido) ({humedad}%) recibidos y guardados.")
        # --- FIN DE MODIFICACIÓN ---

        db.session.commit()
        return jsonify({"status": "recibido"}), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"Error al guardar la lectura: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Api para conococer el estado    
@bp.route('/api/device/status', methods=['POST'])
def set_device_status():
    """
    Endpoint para que el ESP32 actualice su propio estado.
    Ej: {'device_key': '...', 'status': 'online'}
    Ej: {'device_key': '...', 'status': 'regando'}
    """
    datos = request.json
    api_key = datos.get('device_key')
    nuevo_estado = datos.get('status') # 'online', 'regando', 'error'

    if not api_key or not nuevo_estado:
        return jsonify({"status": "error", "message": "Faltan 'device_key' o 'status'"}), 400

    try:
        # Buscamos el dispositivo por su API Key
        dispositivo = tbl_dispositivos.query.filter_by(device_api_key=api_key).first()
        
        if dispositivo:
            dispositivo.estado_actual = nuevo_estado
            db.session.commit()
            return jsonify({"status": "ok", "message": f"Estado actualizado a {nuevo_estado}"})
        else:
            return jsonify({"status": "error", "message": "Dispositivo no encontrado"}), 404
            
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    
# En siar_app/routes.py

@bp.route('/api/log_riego', methods=['POST'])
def log_riego_evento():
    """
    (PARA EL ESP32)
    Endpoint para que el ESP32 reporte un ciclo de riego completado.
    ¡MODIFICADO! Ahora acepta humedad_actual para logs descriptivos.
    Recibe: {
        "device_key": "...", 
        "duracion_seg": 15,
        "humedad_actual": 29.5  <-- ¡NUEVO CAMPO OPCIONAL!
    }
    """
    datos = request.json
    api_key = datos.get('device_key')
    duracion_segundos = datos.get('duracion_seg')
    humedad = datos.get('humedad_actual') # Será None si no se envía

    if not api_key or duracion_segundos is None:
        return jsonify({"status": "error", "message": "Faltan 'device_key' o 'duracion_seg'"}), 400

    try:
        dispositivo = tbl_dispositivos.query.filter_by(device_api_key=api_key).first()
        if not dispositivo:
            return jsonify({"status": "error", "message": "Dispositivo no encontrado"}), 404
        
        tipo_evento_log = ""
        descripcion_log = ""
        
        if humedad is not None:
            # ¡Es un riego de emergencia/sensor!
            tipo_evento_log = "riego_sensor" # Tipo específico
            descripcion_log = f"Riego por sensor activado. Duración: {duracion_segundos}s. Humedad detectada: {humedad}%."
        else:
            # Es un riego programado (o manual en el futuro)
            tipo_evento_log = "riego_programado"
            descripcion_log = f"Riego programado completado. Duración: {duracion_segundos}s."
        
        # Guardamos el evento descriptivo
        nuevo_evento = tbl_bitacora_eventos(
            dispositivo_id=dispositivo.id,
            tipo_evento=tipo_evento_log, 
            descripcion=descripcion_log
        )
        db.session.add(nuevo_evento)
        db.session.commit()
        
        return jsonify({"status": "ok", "message": "Riego registrado"})
            
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    
# En siar_app/routes.py

@bp.route('/api/consumo_agua')
def get_consumo_agua():
    """
    (PARA EL DASHBOARD)
    Consulta el consumo total.
    ¡MODIFICADO! Ahora usa RegEx para extraer los segundos de la descripción.
    """
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "No autorizado"}), 401
    
    try:
        dispositivo = tbl_dispositivos.query.filter_by(usuario_id=session['user_id']).first()
        if not dispositivo:
            return jsonify({"consumo_total": 0})

        caudal = Config.LITROS_POR_SEGUNDO
        
        # 2. Sumamos todos los segundos de riego registrados
        # Buscamos cualquier tipo de evento que contenga 'riego'
        eventos_riego = tbl_bitacora_eventos.query.filter(
            tbl_bitacora_eventos.dispositivo_id == dispositivo.id,
            tbl_bitacora_eventos.tipo_evento.like('riego%') # 'riego_sensor', 'riego_programado'
        ).all()
        
        total_segundos_riego = 0
        
        # Expresión regular para encontrar "XXs" (ej: "15s", "20.5s")
        regex_segundos = re.compile(r'(\d+(\.\d+)?)s') 

        for evento in eventos_riego:
            try:
                # Buscar el patrón (ej: "15s") en la descripción
                match = regex_segundos.search(evento.descripcion)
                if match:
                    # match.group(1) es el número encontrado (ej: "15")
                    total_segundos_riego += float(match.group(1))
            except Exception:
                pass # Ignorar si la descripción es inválida

        # 3. Calculamos el total de litros
        total_litros = total_segundos_riego * caudal
        
        return jsonify({"consumo_total": round(total_litros, 1)})
    
    except Exception as e:
        print(f"Error al obtener consumo de agua: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500