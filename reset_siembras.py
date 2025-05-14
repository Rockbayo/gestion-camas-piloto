#!/usr/bin/env python3
"""
Script para restablecer las bases de datos eliminando todas las siembras y cortes,
manteniendo la estructura del sistema y datos maestros.
Esto prepara el sistema para cargar exclusivamente el histórico.

Uso: python reset_siembras.py
"""

import os
import sys
import datetime
import shutil
import click
from sqlalchemy import text

# Ajustar la ruta para importar la aplicación
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Importar la aplicación y modelos
from app import create_app, db
from app.models import Siembra, Corte

# Directorio para backups
BACKUP_DIR = 'backups'

def create_backup():
    """Crea una copia de seguridad de la base de datos"""
    click.echo("Creando copia de seguridad...")
    
    # Asegurar que existe el directorio de backups
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
    
    # Crear nombre del archivo con timestamp
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(BACKUP_DIR, f'backup_siembras_{timestamp}.sql')
    
    # Obtener configuración de BD desde la aplicación
    app = create_app()
    with app.app_context():
        db_user = app.config.get('DB_USER', 'root')
        db_password = app.config.get('DB_PASSWORD', '')
        db_host = app.config.get('DB_HOST', 'localhost')
        db_name = app.config.get('DB_NAME', 'cpc_optimized')
        
        # Comando para mysqldump
        cmd = f'mysqldump -u {db_user} -p"{db_password}" -h {db_host} {db_name} > {backup_file}'
        
        # Ejecutar comando
        try:
            os.system(cmd)
            click.echo(f"Backup creado: {backup_file}")
            return True
        except Exception as e:
            click.echo(f"Error al crear backup: {str(e)}")
            return False

def reset_siembras_cortes():
    """Elimina todas las siembras y cortes de la base de datos"""
    app = create_app()
    
    with app.app_context():
        try:
            # Iniciar transacción
            db.session.begin()
            
            # Desactivar restricciones de clave foránea temporalmente
            db.session.execute(text('SET FOREIGN_KEY_CHECKS=0;'))
            
            # 1. Eliminar cortes primero (dependen de siembras)
            num_cortes = Corte.query.count()
            click.echo(f"Eliminando {num_cortes} cortes...")
            db.session.execute(text('TRUNCATE TABLE cortes;'))
            
            # 2. Eliminar siembras
            num_siembras = Siembra.query.count()
            click.echo(f"Eliminando {num_siembras} siembras...")
            db.session.execute(text('TRUNCATE TABLE siembras;'))
            
            # Reactivar restricciones de clave foránea
            db.session.execute(text('SET FOREIGN_KEY_CHECKS=1;'))
            
            # Confirmar cambios
            db.session.commit()
            
            click.echo("Datos eliminados correctamente.")
            return True
            
        except Exception as e:
            # Revertir cambios en caso de error
            db.session.rollback()
            click.echo(f"Error al eliminar datos: {str(e)}")
            return False

def main():
    """Función principal del script"""
    click.echo("=== RESET DE SIEMBRAS Y CORTES ===")
    
    # Pedir confirmación
    if not click.confirm("Este proceso eliminará TODAS las siembras y cortes. ¿Desea continuar?", default=False):
        click.echo("Operación cancelada.")
        return
    
    # Crear backup
    if not click.confirm("¿Desea omitir la creación de backup?", default=False):
        if not create_backup():
            if not click.confirm("Error al crear backup. ¿Desea continuar de todos modos?", default=False):
                click.echo("Operación cancelada.")
                return
    
    # Restablecer tablas
    if reset_siembras_cortes():
        click.echo("\n=== RESET COMPLETADO ===")
        click.echo("Ahora puede importar los datos históricos utilizando:")
        click.echo("python manage.py importar-historico")
    else:
        click.echo("\n=== ERROR EN EL RESET ===")
        click.echo("Se produjo un error durante el proceso.")

if __name__ == "__main__":
    main()