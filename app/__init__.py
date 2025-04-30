from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from config import Config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    
    # Registrar blueprints
    from app.auth import auth as auth_bp
    app.register_blueprint(auth_bp)
    
    from app.siembras import siembras as siembras_bp
    app.register_blueprint(siembras_bp)
    
    from app.cortes import cortes as cortes_bp
    app.register_blueprint(cortes_bp)
    
    from app.reportes import reportes as reportes_bp
    app.register_blueprint(reportes_bp)
    
    # Importar rutas principales
    from app import routes
    
    return app

from app import models