from . import db  # Importamos la instancia 'db' creada en __init__.py
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.sql import func # Para la fecha/hora automática

class tbl_paises(db.Model):
    __tablename__ = 'tbl_paises'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    codigo_iso = db.Column(db.String(2), unique=True, nullable=False)
    
    # Relación (inversa): Le dice a un País qué usuarios tiene
    usuarios = db.relationship('tbl_usuarios', backref='pais', lazy=True)

class tbl_usuarios(db.Model):
    __tablename__ = 'tbl_usuarios'
    id = db.Column(db.Integer, primary_key=True)
    
    # Campos del formulario de registro
    nombre_completo = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    nombre_usuario = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False) # Guardamos el hash
    telefono = db.Column(db.String(20), nullable=True)
    direccion = db.Column(db.Text, nullable=True)
    ciudad = db.Column(db.String(100), nullable=True)
    
    # Relación (directa): La llave foránea
    pais_id = db.Column(db.Integer, db.ForeignKey('tbl_paises.id'), nullable=False)
    
    # Metadatos
    fecha_creacion = db.Column(db.DateTime(timezone=True), server_default=func.now())
    
    # Métodos de contraseña (más limpio que en routes.py)
    def set_password(self, password):
        """Genera el hash de la contraseña."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verifica el hash de la contraseña."""
        return check_password_hash(self.password_hash, password)

# --- MODELOS ADICIONALES DEL PROYECTO SIAR ---

class tbl_dispositivos(db.Model):
    __tablename__ = 'tbl_dispositivos'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('tbl_usuarios.id'), nullable=False)
    nombre_dispositivo = db.Column(db.String(100), nullable=False)
    device_api_key = db.Column(db.String(64), unique=True, nullable=False)
    estado_actual = db.Column(db.String(50), default='offline')
    last_heartbeat = db.Column(db.DateTime(timezone=True), server_default=func.now())
    
    # Relaciones
    usuario = db.relationship('tbl_usuarios', backref=db.backref('dispositivos', lazy=True))
    configuracion = db.relationship('tbl_configuracion', backref='dispositivo', uselist=False, lazy=True)

class tbl_configuracion(db.Model):
    __tablename__ = 'tbl_configuracion'
    id = db.Column(db.Integer, primary_key=True)
    dispositivo_id = db.Column(db.Integer, db.ForeignKey('tbl_dispositivos.id'), unique=True, nullable=False)
    umbral_humedad_minima = db.Column(db.SmallInteger, nullable=False, default=40)
    duracion_riego_segundos = db.Column(db.SmallInteger, nullable=False, default=15)
    frecuencia_minima_horas = db.Column(db.SmallInteger, nullable=False, default=4)
    modo_automatico = db.Column(db.Boolean, nullable=False, default=True)
    perfil_activo_id = db.Column(db.Integer, db.ForeignKey('tbl_perfiles_riego.id'), nullable=True)
    perfil_activo = db.relationship('tbl_perfiles_riego', lazy='joined')


class tbl_lecturas_humedad(db.Model):
    __tablename__ = 'tbl_lecturas_humedad'
    id = db.Column(db.BigInteger, primary_key=True)
    dispositivo_id = db.Column(db.Integer, db.ForeignKey('tbl_dispositivos.id'), nullable=False)
    valor_humedad = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime(timezone=True), server_default=func.now())

class tbl_bitacora_eventos(db.Model):
    __tablename__ = 'tbl_bitacora_eventos'
    id = db.Column(db.BigInteger, primary_key=True)
    dispositivo_id = db.Column(db.Integer, db.ForeignKey('tbl_dispositivos.id'), nullable=False)
    tipo_evento = db.Column(db.String(50), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime(timezone=True), server_default=func.now())

class tbl_perfiles_riego(db.Model):
    __tablename__ = 'tbl_perfiles_riego'
    id = db.Column(db.Integer, primary_key=True)
    
    # Llave foránea para que cada usuario tenga sus propios perfiles
    usuario_id = db.Column(db.Integer, db.ForeignKey('tbl_usuarios.id'), nullable=False)
    
    # --- Campos solicitados por usted ---
    
    # 1. Nombre (ej: "Rosas", "Huerto", "Suculentas")
    nombre_perfil = db.Column(db.String(100), nullable=False) 
    
    # 2. Descripcion (ej: "Para rosas que necesitan tierra húmeda pero no encharcada")
    descripcion = db.Column(db.Text, nullable=True) # La hacemos opcional
    
    # 3. Humedad (El umbral MÍNIMO antes de que se active el riego)
    umbral_humedad = db.Column(db.SmallInteger, nullable=False) # Ej: 35 (para 35%)
    
    # 4. Tiempo de Riego (Cuántos segundos regará la bomba)
    duracion_riego_seg = db.Column(db.SmallInteger, nullable=False) # Ej: 20 (para 20 segundos)
    
    # --- Campo que le sugiero (¡Importante!) ---
    
    # 5. Frecuencia de Riego (Cuántas horas esperar como MÍNIMO entre riegos)
    #    Esto es vital para evitar que el sistema riegue 10 veces en un día
    #    solo porque la tierra se seca rápido.
    frecuencia_minima_horas = db.Column(db.SmallInteger, default=4, nullable=False)


    
    # Relación con el usuario
    usuario = db.relationship('tbl_usuarios', backref=db.backref('perfiles', lazy=True))