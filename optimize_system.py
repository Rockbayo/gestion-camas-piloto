#!/usr/bin/env python3
"""
Script de optimización para el Sistema de Gestión de Cultivos
Este script realiza una limpieza completa y optimización del sistema.

Uso:
python optimize_system.py
"""

import os
import sys
import shutil
import subprocess
import re
import argparse
from datetime import datetime

# Colores para la consola
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

# Constantes
BACKUP_DIR = 'backups'
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Función para imprimir mensajes
def print_message(message, msg_type='info'):
    prefix = {
        'info': f"{Colors.BLUE}[INFO]{Colors.ENDC}",
        'success': f"{Colors.GREEN}[SUCCESS]{Colors.ENDC}",
        'warning': f"{Colors.WARNING}[WARNING]{Colors.ENDC}",
        'error': f"{Colors.FAIL}[ERROR]{Colors.ENDC}",
        'step': f"{Colors.HEADER}[PASO]{Colors.ENDC}",
    }.get(msg_type, '')
    
    print(f"{prefix} {message}")

# Función para pedir confirmación
def confirm(message, default=True):
    prompt = f"{message} {'[Y/n]' if default else '[y/N]'}: "
    response = input(prompt).strip().lower()
    
    if not response:
        return default
    return response[0] == 'y'

# Función para crear backup
def create_backup():
    print_message("Creando copia de seguridad del proyecto...", 'step')
    
    # Crear directorio de backup si no existe
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
    
    # Crear nombre de archivo de backup con timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(BACKUP_DIR, f"backup_{timestamp}.zip")
    
    try:
        # Excluir directorios y archivos innecesarios
        exclude_args = "--exclude='__pycache__' --exclude='*.pyc' --exclude='venv' --exclude='env' --exclude='backups'"
        
        # Crear archivo zip con todos los archivos del proyecto
        cmd = f"zip -r {exclude_args} {backup_file} ."
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            print_message(f"Error al crear backup: {result.stderr}", 'error')
            return False
            
        print_message(f"Backup creado exitosamente: {backup_file}", 'success')
        return True
    except Exception as e:
        print_message(f"Error al crear backup: {str(e)}", 'error')
        return False

# Función para ejecutar un comando
def run_command(command, error_message="Error al ejecutar comando"):
    try:
        print_message(f"Ejecutando: {command}")
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            print_message(f"{error_message}: {result.stderr}", 'error')
            return False
            
        return True
    except Exception as e:
        print_message(f"{error_message}: {str(e)}", 'error')
        return False

# Función para limpiar models.py
def clean_models_file():
    print_message("Eliminando referencias a módulos obsoletos en models.py...", 'step')
    
    models_file = os.path.join(PROJECT_ROOT, 'app', 'models.py')
    if not os.path.exists(models_file):
        print_message(f"El archivo {models_file} no existe", 'error')
        return False
    
    # Hacer una copia de seguridad
    shutil.copy2(models_file, f"{models_file}.bak")
    
    try:
        with open(models_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Eliminar property total_perdidas
        pattern = re.compile(r"@hybrid_property\s*\ndef\s+total_perdidas\(self\).*?return\s+0.*?\n", re.DOTALL)
        content = pattern.sub('', content)
        
        # Eliminar import de Causa y Perdida
        pattern = re.compile(r"from\s+app.models\s+import\s+\((.*?)\)", re.DOTALL)
        match = pattern.search(content)
        if match:
            imports = match.group(1)
            imports = re.sub(r',\s*Causa\s*', '', imports)
            imports = re.sub(r',\s*Perdida\s*', '', imports)
            content = pattern.sub(f"from app.models import ({imports})", content)
        
        # Guardar el archivo modificado
        with open(models_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print_message("models.py actualizado correctamente", 'success')
        return True
    except Exception as e:
        print_message(f"Error al limpiar models.py: {str(e)}", 'error')
        shutil.copy2(f"{models_file}.bak", models_file)  # Restaurar backup
        return False

# Función para eliminar archivos y directorios obsoletos
def clean_obsolete_files():
    print_message("Eliminando archivos y directorios obsoletos...", 'step')
    
    # Lista de archivos a eliminar
    files_to_delete = [
        # Módulo de pérdidas
        "app/perdidas/__init__.py",
        "app/perdidas/forms.py",
        "app/perdidas/routes.py",
        
        # Plantillas de pérdidas
        "app/templates/perdidas/crear.html",
        "app/templates/perdidas/editar.html",
        "app/templates/perdidas/index.html",
        
        # Plantillas de administración de causas
        "app/templates/admin/causas.html",
        "app/templates/admin/importar_causas.html",
        "app/templates/admin/importar_causas_directo.html",
        
        # Utilidades para importación de causas
        "app/utils/causas_importer.py",
        
        # Scripts redundantes
        "init_database.py",
        "reset_database.py",
        "run_migrations.py",
        "update_models.py",
        "update_users.py",
        "cleanup.py",
        
        # README duplicado
        "README2.md",
    ]
    
    # Directorios a eliminar si están vacíos
    dirs_to_delete = [
        "app/perdidas",
        "app/templates/perdidas"
    ]
    
    # Eliminar archivos
    deleted_files = 0
    for file_path in files_to_delete:
        full_path = os.path.join(PROJECT_ROOT, file_path)
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
                print_message(f"Archivo eliminado: {file_path}", 'info')
                deleted_files += 1
            except Exception as e:
                print_message(f"Error al eliminar archivo {file_path}: {str(e)}", 'error')
    
    # Eliminar directorios (solo si están vacíos)
    deleted_dirs = 0
    for dir_path in dirs_to_delete:
        full_path = os.path.join(PROJECT_ROOT, dir_path)
        if os.path.exists(full_path) and os.path.isdir(full_path) and not os.listdir(full_path):
            try:
                os.rmdir(full_path)
                print_message(f"Directorio eliminado: {dir_path}", 'info')
                deleted_dirs += 1
            except Exception as e:
                print_message(f"Error al eliminar directorio {dir_path}: {str(e)}", 'error')
    
    # Búsqueda y eliminación de archivos .pyc compilados relacionados
    pyc_count = 0
    for root, dirs, files in os.walk(os.path.join(PROJECT_ROOT, "app")):
        for file in files:
            if file.endswith(".pyc") and ("perdidas" in file or "causas" in file):
                pyc_path = os.path.join(root, file)
                try:
                    os.remove(pyc_path)
                    print_message(f"Archivo .pyc eliminado: {os.path.relpath(pyc_path, PROJECT_ROOT)}", 'info')
                    pyc_count += 1
                except Exception as e:
                    print_message(f"Error al eliminar archivo {os.path.relpath(pyc_path, PROJECT_ROOT)}: {str(e)}", 'error')
    
    # Resumen de limpieza
    print_message("\nResumen de limpieza:", 'success')
    print_message(f"- Archivos eliminados: {deleted_files}")
    print_message(f"- Directorios eliminados: {deleted_dirs}")
    print_message(f"- Archivos .pyc eliminados: {pyc_count}")
    
    return True

# Función para actualizar README.md
def update_readme():
    print_message("Actualizando archivo README.md...", 'step')
    
    readme_file = os.path.join(PROJECT_ROOT, 'README.md')
    readme2_file = os.path.join(PROJECT_ROOT, 'README2.md')
    
    # Si no existe README2, no hay nada que consolidar
    if not os.path.exists(readme2_file):
        print_message("No existe README2.md para consolidar", 'info')
        return True
    
    # Hacer backup del README original
    if os.path.exists(readme_file):
        shutil.copy2(readme_file, f"{readme_file}.bak")
    
    # Consolidar información de ambos README en uno solo
    try:
        with open(readme_file, 'r', encoding='utf-8') as f:
            readme1_content = f.read()
        
        with open(readme2_file, 'r', encoding='utf-8') as f:
            readme2_content = f.read()
        
        # Tomar lo mejor de ambos README
        # (Simplificado: aquí usaríamos el contenido de README2 que es más completo)
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(readme2_content)
        
        # Eliminar README2 después de consolidar
        os.remove(readme2_file)
        
        print_message("README.md actualizado correctamente", 'success')
        return True
    except Exception as e:
        print_message(f"Error al actualizar README.md: {str(e)}", 'error')
        # Restaurar backup si existe
        if os.path.exists(f"{readme_file}.bak"):
            shutil.copy2(f"{readme_file}.bak", readme_file)
        return False

# Actualizar índices de la base de datos
def update_db_indexes():
    print_message("Actualizando índices de la base de datos...", 'step')
    
    # Ejecutar comando manage.py para actualizar índices
    command = "python manage.py update_indexes"
    
    if run_command(command, "Error al actualizar índices de la base de datos"):
        print_message("Índices de la base de datos actualizados correctamente", 'success')
        return True
    else:
        print_message("Fallo al actualizar índices. Intente manualmente: python manage.py update_indexes", 'warning')
        return False

# Función principal que ejecuta todo el proceso
def main():
    parser = argparse.ArgumentParser(description="Script de optimización para el Sistema de Gestión de Cultivos")
    parser.add_argument('--no-backup', action='store_true', help='No crear copia de seguridad antes de los cambios')
    args = parser.parse_args()
    
    print_message("\n=== INICIANDO OPTIMIZACIÓN DEL SISTEMA ===\n", 'header')
    
    # Verificar que estamos en el directorio raíz del proyecto
    if not os.path.exists('app') or not os.path.exists('config.py'):
        print_message("Este script debe ejecutarse desde el directorio raíz del proyecto", 'error')
        return 1
    
    # Crear copia de seguridad
    if not args.no_backup:
        if not create_backup() and not confirm("La copia de seguridad falló. ¿Desea continuar de todos modos?", False):
            print_message("Operación cancelada por el usuario", 'warning')
            return 1
    else:
        print_message("Omitiendo creación de copia de seguridad", 'warning')
    
    # Ejecutar pasos de optimización
    steps = [
        ("Limpiar referencias en models.py", clean_models_file),
        ("Actualizar README", update_readme),
        ("Eliminar archivos obsoletos", clean_obsolete_files),
        ("Actualizar índices de base de datos", update_db_indexes)
    ]
    
    for step_name, step_func in steps:
        if confirm(f"¿Desea {step_name.lower()}?", True):
            if not step_func():
                if not confirm(f"Hubo un problema al {step_name.lower()}. ¿Desea continuar con los siguientes pasos?", True):
                    print_message("Operación cancelada por el usuario", 'warning')
                    return 1
        else:
            print_message(f"Omitiendo: {step_name}", 'info')
    
    # Verificar la base de datos
    if confirm("¿Desea verificar la integridad de la base de datos?", True):
        run_command("python manage.py check_db", "Advertencia al verificar la base de datos")
    
    print_message("\n=== OPTIMIZACIÓN COMPLETADA ===\n", 'header')
    print_message("Recomendaciones finales:", 'info')
    print_message("1. Comprobar que el sistema funciona correctamente")
    print_message("2. Revisar los cambios en app/models.py")
    print_message("3. Ejecutar todas las pruebas del sistema")
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print_message("\nOperación interrumpida por el usuario", 'warning')
        sys.exit(1)