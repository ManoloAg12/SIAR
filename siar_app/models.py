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

# En siar_app/models.py
# (Asegúrese de tener 'db' y 'func' importados)

class tbl_perfiles_riego(db.Model):
    __tablename__ = 'tbl_perfiles_riego'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('tbl_usuarios.id'), nullable=False)
    
    nombre_perfil = db.Column(db.String(100), nullable=False) 
    descripcion = db.Column(db.Text, nullable=True)
    
    # --- ¡LÓGICA CORREGIDA! ---
    # 1. Umbral de EMERGENCIA (Si baja de esto, regar)
    umbral_humedad_min = db.Column(db.SmallInteger, nullable=False, default=25)
    
    # 2. Umbral de AHORRO (Si supera esto, NO regar)
    umbral_humedad_max = db.Column(db.SmallInteger, nullable=False, default=60)

    # 3. Duración (Para riegos PROGRAMADOS)
    duracion_riego_seg = db.Column(db.SmallInteger, nullable=False, default=10)
    
    # --- 'frecuencia_minima_horas' HA SIDO ELIMINADO ---
    
    usuario = db.relationship('tbl_usuarios', backref=db.backref('perfiles', lazy=True))
    horarios = db.relationship('tbl_horarios', backref='perfil', lazy=True)


class tbl_horarios(db.Model):
    __tablename__ = 'tbl_horarios'
    id = db.Column(db.Integer, primary_key=True)
    
    # A qué dispositivo pertenece este horario
    dispositivo_id = db.Column(db.Integer, db.ForeignKey('tbl_dispositivos.id'), nullable=False)
    
    # Qué perfil (y por tanto qué duración/umbral) debe usar
    perfil_id = db.Column(db.Integer, db.ForeignKey('tbl_perfiles_riego.id'), nullable=False)
    
    hora_riego = db.Column(db.Time, nullable=False)
    dias_semana = db.Column(db.String(15), nullable=False) # "1,3,5" (L,M,V)
    activo = db.Column(db.Boolean, nullable=False, default=True)