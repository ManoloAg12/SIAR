import os
from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail

# 1. Creamos la instancia de SQLAlchemy globalmente
db = SQLAlchemy()
mail = Mail()

def create_app(config_class=Config):
    """
    Factory de la aplicación: Crea y configura la instancia de Flask.
    """
    app = Flask(__name__)
    
    # 1. Cargar la configuración desde el archivo config.py
    app.config.from_object(config_class)

    # 2. Inicializar la base de datos con nuestra aplicación
    db.init_app(app)
    mail.init_app(app)

    # 3. Registrar las rutas (Blueprints)
    with app.app_context():
        # Importamos las rutas
        from . import routes
        app.register_blueprint(routes.bp)

        # Importamos los modelos para que SQLAlchemy los "conozca"
        from . import models 
        
        # 4. Creamos todas las tablas definidas en models.py
        #    en la base de datos (si no existen ya)
        db.create_all()

    print("Aplicación SIAR (con SQLAlchemy) creada exitosamente.")
    
    return app