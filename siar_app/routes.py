import requests
import secrets
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
    tbl_lecturas_humedad, tbl_bitacora_eventos, tbl_dispositivos, tbl_perfiles_riego
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text 
from flask_mail import Message # <-- AÑADIR IMPORTACIÓN
from . import db, mail # <-- AÑADIR 'mail
from sqlalchemy import text, not_
from datetime import datetime, timezone, timedelta

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
@bp.route('/api/crear_perfil', methods=['POST'])
def crear_perfil():
    """
    API Endpoint para crear un nuevo perfil de riego.
    Recibe datos de un formulario.
    """
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "No autorizado"}), 401
    
    try:
        # Usamos request.form porque enviaremos datos de formulario, no JSON
        data = request.form
        
        # Validamos que los datos numéricos no estén vacíos
        umbral = data.get('umbral_humedad')
        duracion = data.get('duracion_riego_seg')
        frecuencia = data.get('frecuencia_minima_horas')

        if not (umbral and duracion and frecuencia):
            flash('Todos los campos numéricos son obligatorios.', 'danger')
            return jsonify({"status": "error", "message": "Campos numéricos obligatorios"}), 400

        # Creamos el nuevo objeto de perfil
        nuevo_perfil = tbl_perfiles_riego(
            usuario_id=session['user_id'],
            nombre_perfil=data.get('nombre_perfil'),
            descripcion=data.get('descripcion'),
            umbral_humedad=int(umbral),
            duracion_riego_seg=int(duracion),
            frecuencia_minima_horas=int(frecuencia)
        )
        
        db.session.add(nuevo_perfil)
        db.session.commit()
        
        flash('¡Perfil creado exitosamente!', 'success')
        return jsonify({"status": "ok", "message": "Perfil creado"})

    except Exception as e:
        db.session.rollback()
        print(f"Error al crear perfil: {e}")
        flash(f'Error al crear perfil: {e}', 'danger')
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



@bp.route('/home')
def home():
    if 'user_id' not in session:
        flash('Debe iniciar sesión para ver esta página.', 'info')
        return redirect(url_for('main.login'))
    
    current_user_id = session['user_id']
    user_name = session.get('user_name', 'Usuario')
    device_status = 'Desconocido'
    perfiles_list = []
    weather_data = None
    configuracion_actual = None 
    dispositivos_list = []
    
    try:
        usuario = tbl_usuarios.query.get(current_user_id)
        if not usuario:
            flash("Error de sesión, inicie de nuevo.", 'danger')
            return redirect(url_for('main.login'))

        dispositivo = tbl_dispositivos.query.filter_by(usuario_id=current_user_id).first()
        
        if dispositivo:
            device_status = dispositivo.estado_actual
            # --- ¡LÓGICA SIMPLIFICADA! ---
            configuracion_actual = dispositivo.configuracion
            # ¡Ya no buscamos horarios_actuales!
            # -----------------------------
        else:
            device_status = 'No Asignado'

        dispositivos_list = tbl_dispositivos.query.filter_by(usuario_id=current_user_id).order_by(tbl_dispositivos.nombre_dispositivo).all()
        perfiles_list = tbl_perfiles_riego.query.order_by(tbl_perfiles_riego.nombre_perfil).all()
        
        if usuario.ciudad and usuario.pais:
            weather_data = get_weather(usuario.ciudad, usuario.pais.codigo_iso)
            
    except Exception as e:
        print(f"Error al buscar datos del dashboard: {e}")

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
        configuracion_actual=configuracion_actual, # <-- Solo pasamos la config
        dispositivos=dispositivos_list
        # ¡horarios_actuales ELIMINADO!
    )

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
@bp.route('/api/aplicar_perfil', methods=['POST'])
def aplicar_perfil():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "No autorizado"}), 401
    try:
        data = request.json
        perfil_id = data.get('perfil_id')
        
        perfil = tbl_perfiles_riego.query.get(perfil_id)
        if not perfil:
            return jsonify({"status": "error", "message": "Perfil no encontrado"}), 404
        
        dispositivo_usuario = tbl_dispositivos.query.filter_by(usuario_id=session['user_id']).first()
        if not dispositivo_usuario:
             return jsonify({"status": "error", "message": "Dispositivo no encontrado"}), 404

        # Validar que el dispositivo esté online
        if dispositivo_usuario.estado_actual != 'online':
            return jsonify({"status": "error", "message": f"Error: El dispositivo está '{dispositivo_usuario.estado_actual}'."}), 400

        config_activa = dispositivo_usuario.configuracion

        if config_activa:
            print("Configuración existente encontrada. Actualizando...")
            config_activa.umbral_humedad_minima = perfil.umbral_humedad
            config_activa.duracion_riego_segundos = perfil.duracion_riego_seg
            # --- ¡AÑADIR ESTE CAMPO! ---
            config_activa.frecuencia_minima_horas = perfil.frecuencia_minima_horas
            config_activa.perfil_activo_id = perfil.id
        else:
            print("Configuración no encontrada. Creando una nueva...")
            config_activa = tbl_configuracion(
                dispositivo_id=dispositivo_usuario.id,
                umbral_humedad_minima=perfil.umbral_humedad,
                duracion_riego_segundos=perfil.duracion_riego_seg,
                # --- ¡AÑADIR ESTE CAMPO! ---
                frecuencia_minima_horas = perfil.frecuencia_minima_horas,
                modo_automatico=True,
                perfil_activo_id = perfil.id     
            )
            db.session.add(config_activa)
        
        db.session.commit()
        return jsonify({"status": "ok", "message": f"Perfil '{perfil.nombre_perfil}' aplicado."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
# ========================================================
    
#dinamismo para las cartas
# --- ¡¡FUNCIÓN REEMPLAZADA!! ---
#dinamismo para las cartas
@bp.route('/api/get_dynamic_status')
def get_dynamic_status():
    """
    Devuelve el estado actualizado del dispositivo y la BBDD como JSON.
    ¡NUEVO: También comprueba si el dispositivo se ha desconectado!
    """
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "No autorizado"}), 401
        
    device_status_val = 'Desconocido'
    db_status_val = "Desconectado"
    
    try:
        # 1. Revisar estado del dispositivo
        dispositivo = tbl_dispositivos.query.filter_by(usuario_id=session['user_id']).first()
        if dispositivo:
            device_status_val = dispositivo.estado_actual
            
            # --- ¡NUEVA LÓGICA DE TIMEOUT! ---
            # Si el estado es "online" o "regando", verificamos su última lectura.
            if device_status_val in ['online', 'regando']:
                # Buscamos la última lectura de humedad (que actúa como "heartbeat")
                ultima_lectura = tbl_lecturas_humedad.query.filter_by(
                    dispositivo_id=dispositivo.id
                ).order_by(tbl_lecturas_humedad.timestamp.desc()).first()

                if ultima_lectura:
                    # Comparamos el timestamp de la lectura con la hora actual (ambos en UTC)
                    ahora_utc = datetime.now(timezone.utc)
                    segundos_transcurridos = (ahora_utc - ultima_lectura.timestamp).total_seconds()

                    # DEFINIMOS EL TIMEOUT (ej: 35 segundos)
                    # El ESP32 reporta cada 10s, si falla 3 veces seguidas, está offline.
                    TIMEOUT_SEGUNDOS = 35 

                    if segundos_transcurridos > TIMEOUT_SEGUNDOS:
                        # ¡El dispositivo se ha desconectado!
                        print(f"TIMEOUT: Dispositivo {dispositivo.id} está offline. Última lectura hace {segundos_transcurridos}s.")
                        dispositivo.estado_actual = 'offline'
                        db.session.commit()
                        device_status_val = 'offline' # Actualizamos el valor a devolver
                
                else:
                    # Si está 'online' pero NUNCA ha enviado una lectura,
                    # lo dejamos pasar por ahora (podría estar arrancando).
                    pass
            # --- FIN DE LA LÓGICA DE TIMEOUT ---
            
        else:
            device_status_val = 'No Asignado'
            
    except Exception as e:
        db.session.rollback() # Hacemos rollback en caso de error en la comprobación
        print(f"Error al buscar dispositivo o comprobar timeout: {e}")
        device_status_val = 'Error'

    try:
        # 2. Revisar estado de la BBDD
        db.session.execute(text('SELECT 1'))
        db_status_val = "Conectado (SQLAlchemy)"
    except Exception as e:
        db_status_val = f"Error: {e}"

    # 3. Devolver ambos valores como JSON
    return jsonify({
        "device_status": device_status_val,
        "db_status": db_status_val
    })
# --- FIN DE LA FUNCIÓN REEMPLAZADA ---



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
    """
    # Validamos que el usuario esté logueado
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "No autorizado"}), 401
    
    try:
        # Buscamos el dispositivo asociado al usuario en sesión
        dispositivo = tbl_dispositivos.query.filter_by(usuario_id=session['user_id']).first()
        
        if not dispositivo:
            return jsonify({"humedad": "--"}) # Usuario no tiene dispositivo

        # Buscamos la última (más reciente) lectura de ese dispositivo
        lectura = tbl_lecturas_humedad.query.filter_by(dispositivo_id=dispositivo.id).order_by(tbl_lecturas_humedad.timestamp.desc()).first()
        
        if lectura:
            # Devolvemos el valor redondeado
            return jsonify({"humedad": int(round(lectura.valor_humedad))})
        else:
            # No se han registrado lecturas
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
# --- API (Para el ESP32) ---
# (Sin cambios)

# api para conectar asl ESP32
@bp.route('/api/configuracion', methods=['GET'])
def get_configuracion():
    config_obj = tbl_configuracion.query.first()
    if config_obj:
        config_data = {
            "umbral_min": config_obj.umbral_humedad_minima,
            "duracion_seg": config_obj.duracion_riego_segundos,
            "modo_auto": config_obj.modo_automatico
        }
    else:
        config_data = {"umbral_min": 40, "duracion_seg": 15, "modo_auto": True}
    return jsonify(config_data)

#Api para conocer las lecturas de la humedad del suelo
@bp.route('/api/lectura', methods=['POST'])
def post_lectura():
    datos = request.json
    humedad = datos.get('humedad')
    if humedad is None:
        return jsonify({"status": "error", "message": "Falta el dato 'humedad'"}), 400
        
    dispositivo_id_fijo = 1 

    try:
        nueva_lectura = tbl_lecturas_humedad(
            dispositivo_id=dispositivo_id_fijo,
            valor_humedad=humedad
        )
        db.session.add(nueva_lectura)
        db.session.commit()
        
        print(f"Datos recibidos desde ESP32: {datos}")
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