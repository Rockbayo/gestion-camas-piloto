from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from config import Config

# Inicialización de extensiones
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Por favor, inicia sesión para acceder a esta página.'

def create_app(config_class=Config):
    """Crear y configurar la aplicación Flask."""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Inicializar extensiones con la app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    
    # Registrar blueprints
    from app.routes import main_bp
    app.register_blueprint(main_bp)
    
    from app.auth import auth_bp
    app.register_blueprint(auth_bp)
    
    from app.siembras import siembras_bp
    app.register_blueprint(siembras_bp)
    
    from app.cortes import cortes_bp
    app.register_blueprint(cortes_bp)
    
    from app.reportes import reportes_bp
    app.register_blueprint(reportes_bp)
    
    return app

from app import models