"""
Módulo de inicialización principal de la aplicación Flask.

Mejoras:
- Estructura más clara y organizada
- Mejor manejo de dependencias
- Documentación más completa
- Configuración más modular
"""

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
csrf = CSRFProtect()

# Configuración del LoginManager
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Por favor inicie sesión para acceder a esta página.'
login_manager.login_message_category = 'info'

def create_app(config_class=Config):
    """
    Factory function para crear la aplicación Flask.
    
    Args:
        config_class: Clase de configuración a usar
        
    Returns:
        Instancia de la aplicación Flask configurada
    """
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Inicializar extensiones
    initialize_extensions(app)
    
    # Registrar blueprints
    register_blueprints(app)
    
    # Configurar manejo de errores
    register_error_handlers(app)
    
    # Registrar comandos CLI
    register_cli_commands(app)
    
    # Configurar logging
    configure_logging(app)
    
    return app

def initialize_extensions(app):
    """Inicializa todas las extensiones Flask."""
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    
    # Importar y configurar filtros personalizados
    from app.utils.date_filter import configure_date_filters
    configure_date_filters(app)

def register_blueprints(app):
    """Registra todos los blueprints de la aplicación."""
    from app.main import bp as main_bp
    from app.auth import bp as auth_bp
    from app.admin import bp as admin_bp
    from app.siembras import bp as siembras_bp
    from app.cortes import bp as cortes_bp
    from app.reportes import reportes as reportes_bp
    from app.perdidas import bp as perdidas_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(siembras_bp, url_prefix='/siembras')
    app.register_blueprint(cortes_bp, url_prefix='/cortes')
    app.register_blueprint(reportes_bp)
    app.register_blueprint(perdidas_bp)

def register_error_handlers(app):
    """Registra manejadores de errores personalizados."""
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500

def register_cli_commands(app):
    """Registra comandos personalizados para la CLI de Flask."""
    @app.cli.command("init-db")
    def init_db():
        """Inicializa la base de datos con datos básicos."""
        from app.models import Documento, Usuario, Rol, Permiso
        
        # Transacción única para mejor rendimiento
        with db.session.begin_nested():
            # Crear permiso si no existe
            permiso_importar = Permiso.query.filter_by(codigo='importar_datos').first()
            if not permiso_importar:
                permiso_importar = Permiso(
                    codigo='importar_datos', 
                    descripcion='Permite importar datos históricos y datasets'
                )
                db.session.add(permiso_importar)
            
            # Crear rol admin si no existe
            rol_admin = Rol.query.filter_by(nombre='admin').first()
            if not rol_admin:
                rol_admin = Rol(
                    nombre='admin',
                    descripcion='Administrador del sistema con acceso completo'
                )
                db.session.add(rol_admin)
                db.session.flush()
            
            # Asignar permiso al rol
            if permiso_importar not in rol_admin.permisos:
                rol_admin.permisos.append(permiso_importar)
            
            # Verificar y crear documento si es necesario
            doc = Documento.query.get(1)
            if not doc:
                doc = Documento(doc_id=1, documento='Cedula de Ciudadania')
                db.session.add(doc)
            
            # Crear/actualizar usuario admin
            admin = Usuario.query.filter_by(username='admin').first()
            if not admin:
                admin = Usuario(
                    nombre_1='Admin',
                    apellido_1='Sistema',
                    cargo='Administrador',
                    num_doc=999999,
                    documento_id=1,
                    username='admin',
                    rol_id=rol_admin.rol_id  # Asignar rol de admin
                )
                admin.set_password('admin123')
                db.session.add(admin)
                app.logger.info("Base de datos inicializada con usuario admin")
                print("✅ Base de datos inicializada con usuario admin")
            else:
                # Actualizar el rol del admin existente
                admin.rol_id = rol_admin.rol_id
                app.logger.info("Usuario admin existente actualizado con rol de administrador")
                print("✅ Usuario admin existente actualizado con rol de administrador")
        
        # Confirmar todos los cambios
        db.session.commit()
    
    @app.cli.command("update-admin-permissions")
    def update_admin_permissions():
        """Actualiza los permisos del administrador para incluir importación de datos."""
        from app.models import Usuario, Rol, Permiso
        
        try:
            # Usar get_or_create para el permiso
            permiso_importar = Permiso.query.filter_by(codigo='importar_datos').first()
            if not permiso_importar:
                permiso_importar = Permiso(
                    codigo='importar_datos', 
                    descripcion='Permite importar datos históricos y datasets'
                )
                db.session.add(permiso_importar)
            
            # Usar get_or_create para el rol admin
            rol_admin = Rol.query.filter_by(nombre='admin').first()
            if not rol_admin:
                rol_admin = Rol(
                    nombre='admin',
                    descripcion='Administrador del sistema con acceso completo'
                )
                db.session.add(rol_admin)
                db.session.flush()  # Necesario para obtener el ID antes de usarlo
            
            # Asignar permiso al rol si no lo tiene ya
            if not rol_admin.permisos or permiso_importar not in rol_admin.permisos:
                rol_admin.permisos.append(permiso_importar)
            
            # Actualizar usuario admin
            admin = Usuario.query.filter_by(username='admin').first()
            if admin:
                admin.rol_id = rol_admin.rol_id
                app.logger.info("Permisos del administrador actualizados correctamente")
                print("✅ Permisos del administrador actualizados correctamente")
            else:
                app.logger.warning("No se encontró usuario admin")
                print("⚠️ No se encontró usuario admin")
            
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error al actualizar permisos del admin: {str(e)}")
            print(f"❌ Error: {str(e)}")
    
    @app.cli.command("importar-historico")
    def importar_historico_cmd():
        """Importa datos históricos desde un archivo Excel incluyendo pérdidas."""
        import click
        
        archivo = click.prompt("Ruta del archivo Excel", type=click.Path(exists=True))
        click.echo(f"Importando datos desde {archivo}...")
        
        try:
            # Usar el importador optimizado
            from app.utils.importar_historico import HistoricalImporter
            result = HistoricalImporter.importar_historico(archivo)
            
            if 'error' in result:
                click.secho(f"Error: {result['error']}", err=True, fg='red')
                if 'detalles_errores' in result and result['detalles_errores']:
                    click.echo("Detalles de errores:")
                    for i, error in enumerate(result['detalles_errores'][:5], 1):
                        click.echo(f"{i}. Fila {error['fila']}: {error['error']}")
                    if len(result['detalles_errores']) > 5:
                        click.echo(f"... y {len(result['detalles_errores']) - 5} errores más.")
            else:
                click.secho("Importación completada con éxito:", fg='green')
                click.echo(f"Siembras creadas: {result.get('siembras_creadas', 0)}")
                click.echo(f"Cortes creados: {result.get('cortes_creados', 0)}")
                click.echo(f"Pérdidas creadas: {result.get('perdidas_creadas', 0)}")
                click.echo(f"Causas de pérdida creadas: {result.get('causas_perdida_creadas', 0)}")
                if result.get('errores', 0) > 0:
                    click.echo(f"Registros con errores: {result.get('errores', 0)}")
        except Exception as e:
            click.secho(f"Error al realizar la importación: {str(e)}", err=True, fg='red')

def configure_logging(app):
    """Configura el sistema de logging de la aplicación."""
    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
            
        file_handler = RotatingFileHandler(
            'logs/cpc.log',
            maxBytes=10240,
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('CPC startup')

# Importar modelos para que Flask-Migrate los detecte
from app.models import (
    Documento, Rol, Permiso, Usuario, Bloque, Cama, Lado, BloqueCamaLado,
    Flor, Color, FlorColor, Variedad, Area, Densidad, Siembra, Corte,
    TipoLabor, LaborCultural, CausaPerdida, Perdida,
    VistaProduccionAcumulada, VistaProduccionPorDia
)