import requests
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

bp = Blueprint('main', __name__)

# --- Rutas Web (Para el navegador) ---
@bp.route('/')
@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Muestra la página de login, maneja el registro y el inicio de sesión."""
    
    # Si el usuario ya está logueado, redirigirlo al home
    if 'user_id' in session:
        return redirect(url_for('main.home'))

    if request.method == 'POST':
        form_type = request.form.get('form_type')
        
        if form_type == 'register':
            # --- LÓGICA DE REGISTRO ---
            try:
                pais = tbl_paises.query.filter_by(codigo_iso=request.form.get('pais')).first()
                if not pais:
                    flash(f'Error: País no encontrado.', 'danger')
                    return redirect(url_for('main.login'))

                nuevo_usuario = tbl_usuarios(
                    nombre_completo=request.form.get('nombre_completo'),
                    email=request.form.get('email'),
                    nombre_usuario=request.form.get('nombre_usuario'),
                    telefono=request.form.get('telefono'),
                    direccion=request.form.get('direccion'),
                    ciudad=request.form.get('ciudad'),
                    pais_id=pais.id 
                )
                nuevo_usuario.set_password(request.form.get('password'))
                
                db.session.add(nuevo_usuario)
                db.session.commit()
                
                flash('¡Cuenta creada exitosamente! Ya puede iniciar sesión.', 'success')
            
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
                    session['user_name'] = usuario.nombre_completo # <-- Aquí guardamos el nombre
                    
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
    """Muestra el dashboard principal (home.html)."""
    
    if 'user_id' not in session:
        flash('Debe iniciar sesión para ver esta página.', 'info')
        return redirect(url_for('main.login'))
    
    user_name = session.get('user_name', 'Usuario')
    device_status = 'Desconocido'
    perfiles_list = []
    weather_data = None # Variable para el clima
    
    try:
        # Buscamos al usuario y su dispositivo
        usuario = tbl_usuarios.query.get(session['user_id'])
        if not usuario:
            flash("Error de sesión, inicie de nuevo.", 'danger')
            return redirect(url_for('main.login'))

        dispositivo = tbl_dispositivos.query.filter_by(usuario_id=session['user_id']).first()
        
        if dispositivo:
            device_status = dispositivo.estado_actual
        else:
            device_status = 'No Asignado'

        perfiles_list = tbl_perfiles_riego.query.filter_by(usuario_id=session['user_id']).order_by(tbl_perfiles_riego.nombre_perfil).all()
        
        # --- ¡NUEVO! OBTENER DATOS DEL CLIMA ---
        if usuario.ciudad and usuario.pais:
            # Usamos la ciudad y el código de país (ej: 'SV') del usuario
            weather_data = get_weather(usuario.ciudad, usuario.pais.codigo_iso)
        # ------------------------------------
            
    except Exception as e:
        print(f"Error al buscar datos del dashboard: {e}")

    # Prueba de conexión a la BBDD
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
        weather=weather_data  # <--- ¡NUEVA VARIABLE AÑADIDA!
    )

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