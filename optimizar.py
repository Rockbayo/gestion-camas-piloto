#!/usr/bin/env python3
"""
Script para optimizar la estructura del proyecto Flask de Gestión de Cultivos
Elimina archivos innecesarios y consolida código redundante
"""

import os
import sys
import shutil
import re
import subprocess
import click
from datetime import datetime

# Lista de archivos a eliminar
FILES_TO_DELETE = [
    "app/models.py.bak",
    "optimize_system.py",
    "importar_historico.py",
    "migrations/versions/e0a8fcdd3553_eliminar_campo_fecha_perdida_de_perdidas.py"
]

# Funciones redundantes a consolidar
CONSOLIDATION_TASKS = [
    {"source": "importar_mejorado.py", "target": "manage.py", "function": "add_importar_command"},
    {"source": "db_management.py", "target": "manage.py", "function": "merge_db_commands"}
]

def create_backup():
    """Crea una copia de seguridad del proyecto"""
    backup_dir = "backups"
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"{backup_dir}/project_backup_{timestamp}.zip"
    
    click.echo(f"Creando copia de seguridad en {backup_file}...")
    try:
        # Excluir directorios innecesarios del backup
        subprocess.run(f"zip -r {backup_file} . -x '*.pyc' -x '__pycache__/*' -x 'venv/*' -x 'env/*' -x '*.zip'", shell=True, check=True)
        click.echo(f"Backup creado exitosamente")
        return True
    except Exception as e:
        click.echo(f"Error al crear backup: {e}")
        return False

def delete_unnecessary_files():
    """Elimina archivos innecesarios"""
    click.echo("\nArchivos a eliminar:")
    for file_path in FILES_TO_DELETE:
        if os.path.exists(file_path):
            click.echo(f"- {file_path}")
        else:
            click.echo(f"- {file_path} (no existe)")
    
    if click.confirm("\n¿Desea continuar con la eliminación de archivos?", default=False):
        for file_path in FILES_TO_DELETE:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    click.echo(f"✓ Eliminado: {file_path}")
                except Exception as e:
                    click.echo(f"✗ Error al eliminar {file_path}: {e}")
        return True
    else:
        click.echo("Eliminación de archivos cancelada")
        return False

def add_importar_command(source_file, target_file):
    """Agrega el comando de importación histórica a manage.py"""
    # Simplemente muestra instrucciones, implementación real sería más compleja
    click.echo(f"Para agregar el comando de importar histórico de {source_file} a {target_file}:")
    click.echo("1. Crear una nueva función 'importar_historico_cmd()' en manage.py")
    click.echo("2. Registrar el comando como '@cli.command()'")
    click.echo("3. Mover la lógica principal desde importar_mejorado.py a la nueva función")
    click.echo("Esto requiere modificación manual para asegurar la integración correcta")
    
def merge_db_commands(source_file, target_file):
    """Consolida los comandos de db_management.py en manage.py"""
    # Similar a la función anterior, instrucciones para consolidación manual
    click.echo(f"Para consolidar comandos de BD de {source_file} a {target_file}:")
    click.echo("1. Revisar y transferir los comandos únicos de db_management.py a manage.py")
    click.echo("2. Asegurarse que no haya duplicación de funcionalidad")
    click.echo("Esto requiere revisión manual cuidadosa")

def execute_consolidation_tasks():
    """Ejecuta tareas de consolidación de código"""
    click.echo("\nTareas de consolidación de código disponibles:")
    for idx, task in enumerate(CONSOLIDATION_TASKS, 1):
        click.echo(f"{idx}. Consolidar '{task['function']}' de {task['source']} en {task['target']}")
    
    if click.confirm("\n¿Desea ejecutar las tareas de consolidación?", default=False):
        for task in CONSOLIDATION_TASKS:
            click.echo(f"\nConsolidando {task['function']} de {task['source']} en {task['target']}...")
            # Ejecutar la función correspondiente
            globals()[task['function']](task['source'], task['target'])
        return True
    else:
        click.echo("Consolidación de código cancelada")
        return False

def main():
    """Función principal del script"""
    click.echo("=== OPTIMIZACIÓN DEL PROYECTO DE GESTIÓN DE CULTIVOS ===\n")
    
    # Verificar que estamos en el directorio raíz
    if not os.path.exists("app") or not os.path.exists("manage.py"):
        click.echo("Error: Este script debe ejecutarse desde el directorio raíz del proyecto")
        return 1
    
    # Crear backup
    if click.confirm("¿Desea crear una copia de seguridad antes de continuar?", default=True):
        if not create_backup():
            if not click.confirm("Error al crear backup. ¿Desea continuar de todos modos?", default=False):
                return 1
    
    # Eliminar archivos innecesarios
    delete_unnecessary_files()
    
    # Ejecutar tareas de consolidación
    execute_consolidation_tasks()
    
    click.echo("\n=== OPTIMIZACIÓN COMPLETADA ===")
    click.echo("NOTA: Algunas tareas requieren revisión manual posterior.")
    click.echo("Verifique el funcionamiento de la aplicación después de estos cambios.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())