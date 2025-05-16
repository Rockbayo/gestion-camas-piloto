# app/__init__.py
import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from config import Config

# Inicialización de extensiones
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Por favor inicie sesión para acceder a esta página.'
csrf = CSRFProtect()

# Quitar la línea problemática: login = login_manager

# Definir funciones auxiliares antes de create_app
def register_error_handlers(app):
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500

def register_cli_commands(app):
    @app.cli.command("init-db")
    def init_db():
        """Inicializa la base de datos con datos básicos."""
        from app.models import Documento, Usuario
        
        if Usuario.query.first() is None:
            doc = Documento.query.get(1)
            if not doc:
                doc = Documento(doc_id=1, documento='Cedula de Ciudadania')
                db.session.add(doc)
            
            admin = Usuario(
                nombre_1='Admin',
                apellido_1='Sistema',
                cargo='Administrador',
                num_doc=999999,
                documento_id=1,
                username='admin'
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("Base de datos inicializada con usuario admin")
        else:
            print("Ya existen usuarios en la base de datos")
    
    @app.cli.command("importar-historico")
    def importar_historico_cmd():
        """Importa datos históricos desde un archivo Excel."""
        import os
        from app.utils.optimizado import importar_historico
        
        archivo = input("Ruta del archivo Excel: ")
        if not os.path.exists(archivo):
            print(f"El archivo {archivo} no existe.")
            return
        
        print(f"Importando datos desde {archivo}...")
        importar_historico(archivo)
            
    
def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Inicializar extensiones
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    
    # Registrar blueprints - las rutas se importan automáticamente en __init__.py
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)
    
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    from app.siembras import bp as siembras_bp
    app.register_blueprint(siembras_bp, url_prefix='/siembras')
    
    from app.cortes import bp as cortes_bp
    app.register_blueprint(cortes_bp, url_prefix='/cortes')
    
    from app.reportes import reportes as reportes_bp
    app.register_blueprint(reportes_bp)
    
    # Añadir filtros personalizados para fechas
    from app.utils.optimizado import add_date_filter
    add_date_filter(app)
    
    # Manejar errores
    register_error_handlers(app)
    
    # Configurar comandos CLI
    register_cli_commands(app)
    
    # Configurar logging...
    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/cpc.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('CPC startup')
    
    return app