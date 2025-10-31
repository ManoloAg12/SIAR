import os

class Config:
    """Configuración base de la aplicación SIAR."""
    
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'una-clave-secreta-muy-dificil'
    
    # --- CONEXIÓN A POSTGRESQL ---
    db_user = 'programador'
    db_pass = 'admin123'
    db_host = 'localhost'
    db_port = '5432'
    db_name = 'siar'
    
    DATABASE_URL = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

    # --- CONFIGURACIÓN DE SQLALCHEMY ---
    # Usa la misma URL de la base de datos
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or DATABASE_URL
    
    # Desactiva una función de seguimiento de SQLAlchemy que no necesitamos
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # --- CLAVE DE API DEL CLIMA ---
    # Pegue aquí su clave de OpenWeatherMap
    WEATHER_API_KEY = os.environ.get('WEATHER_API_KEY') or 'adb5244d3089558b748a8f08cec298ca'