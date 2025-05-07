#!/usr/bin/env python3
"""
Script para eliminar archivos y directorios relacionados con módulos no utilizados,
específicamente los módulos de causas y pérdidas que ya no se utilizan en el proyecto.
"""

import os
import shutil
import sys

# Colores para mensajes en la consola
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'

def print_info(message):
    """Muestra un mensaje informativo"""
    print(f"{Colors.GREEN}[INFO]{Colors.RESET} {message}")

def print_warning(message):
    """Muestra un mensaje de advertencia"""
    print(f"{Colors.YELLOW}[ADVERTENCIA]{Colors.RESET} {message}")

def print_error(message):
    """Muestra un mensaje de error"""
    print(f"{Colors.RED}[ERROR]{Colors.RESET} {message}")

def delete_file(file_path):
    """Elimina un archivo si existe"""
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            print_info(f"Archivo eliminado: {file_path}")
            return True
        except Exception as e:
            print_error(f"Error al eliminar archivo {file_path}: {str(e)}")
            return False
    else:
        print_warning(f"Archivo no encontrado: {file_path}")
        return False

def delete_directory(dir_path):
    """Elimina un directorio si existe"""
    if os.path.exists(dir_path):
        try:
            shutil.rmtree(dir_path)
            print_info(f"Directorio eliminado: {dir_path}")
            return True
        except Exception as e:
            print_error(f"Error al eliminar directorio {dir_path}: {str(e)}")
            return False
    else:
        print_warning(f"Directorio no encontrado: {dir_path}")
        return False

def main():
    """Función principal para eliminar archivos y directorios inservibles"""
    # Comprobación de seguridad: ejecutar solo desde la raíz del proyecto
    if not os.path.exists("app") or not os.path.exists("config.py"):
        print_error("Este script debe ejecutarse desde la raíz del proyecto de Gestión de Camas.")
        sys.exit(1)
    
    print_info("Iniciando limpieza de archivos y directorios inservibles...")
    
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
        
        # Scripts de prueba para causas
        "test_import_causas.py",
        "test_import_web.py"
    ]
    
    # Directorios a eliminar
    dirs_to_delete = [
        "app/perdidas",
        "app/templates/perdidas"
    ]
    
    # Eliminar archivos
    deleted_files = 0
    for file_path in files_to_delete:
        if delete_file(file_path):
            deleted_files += 1
    
    # Eliminar directorios (solo si están vacíos)
    deleted_dirs = 0
    for dir_path in dirs_to_delete:
        if os.path.exists(dir_path) and not os.listdir(dir_path):
            if delete_directory(dir_path):
                deleted_dirs += 1
    
    # Búsqueda y eliminación de archivos .pyc compilados relacionados
    pyc_count = 0
    for root, dirs, files in os.walk("app"):
        for file in files:
            if file.endswith(".pyc") and ("perdidas" in file or "causas" in file):
                pyc_path = os.path.join(root, file)
                if delete_file(pyc_path):
                    pyc_count += 1
    
    # Resumen de limpieza
    print_info("\nResumen de limpieza:")
    print(f"- Archivos eliminados: {deleted_files}/{len(files_to_delete)}")
    print(f"- Directorios eliminados: {deleted_dirs}/{len(dirs_to_delete)}")
    print(f"- Archivos .pyc eliminados: {pyc_count}")
    
    # Instrucciones adicionales
    print_info("\nLimpieza completada. Para completar el proceso:")
    print("1. Ejecute el comando de migración para eliminar las tablas:")
    print("   flask db upgrade")
    print("2. Verifique que no quedan referencias a 'causas' o 'perdidas' en la base de datos:")
    print("   python manage.py check_db")
    print("3. Actualice la documentación del proyecto si es necesario")

if __name__ == "__main__":
    main()