#!/usr/bin/env python3
"""
Script para ejecutar las migraciones y actualizar la base de datos 
eliminando las tablas de causas y pérdidas.
"""

import os
import subprocess
import sys

# Colores para mensajes en la consola
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_heading(message):
    """Muestra un encabezado"""
    print(f"\n{Colors.BLUE}=== {message} ==={Colors.RESET}")

def print_info(message):
    """Muestra un mensaje informativo"""
    print(f"{Colors.GREEN}[INFO]{Colors.RESET} {message}")

def print_warning(message):
    """Muestra un mensaje de advertencia"""
    print(f"{Colors.YELLOW}[ADVERTENCIA]{Colors.RESET} {message}")

def print_error(message):
    """Muestra un mensaje de error"""
    print(f"{Colors.RED}[ERROR]{Colors.RESET} {message}")

def run_command(command, error_message="Error al ejecutar el comando"):
    """Ejecuta un comando y muestra el resultado"""
    try:
        print_info(f"Ejecutando: {command}")
        process = subprocess.Popen(
            command, 
            shell=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        stdout, stderr = process.communicate()
        
        if stdout:
            print(stdout)
        
        if stderr:
            print_warning(f"Salida de error: {stderr}")
            
        if process.returncode != 0:
            print_error(f"{error_message}. Código de salida: {process.returncode}")
            return False
            
        return True
    except Exception as e:
        print_error(f"{error_message}: {str(e)}")
        return False

def check_project_root():
    """Verifica que el script se ejecute desde la raíz del proyecto"""
    if not os.path.exists("app") or not os.path.exists("config.py"):
        print_error("Este script debe ejecutarse desde la raíz del proyecto de Gestión de Camas.")
        sys.exit(1)

def check_migration_file_exists():
    """Verifica que el archivo de migración exista"""
    migration_files = []
    for root, dirs, files in os.walk("migrations/versions"):
        for file in files:
            if file.endswith(".py") and ("eliminar_causas_perdidas" in file or "f987d521e987" in file):
                migration_files.append(os.path.join(root, file))
    
    if not migration_files:
        print_error("No se encontró el archivo de migración para eliminar causas y pérdidas.")
        print_warning("Asegúrese de que el archivo migrations/versions/eliminar_causas_perdidas.py existe.")
        return False
    
    print_info(f"Archivo de migración encontrado: {migration_files[0]}")
    return True

def main():
    """Función principal para ejecutar las migraciones"""
    print_heading("MIGRACIÓN DE BASE DE DATOS - ELIMINAR CAUSAS Y PÉRDIDAS")
    
    # Verificaciones previas
    check_project_root()
    if not check_migration_file_exists():
        response = input("¿Desea continuar a pesar de no encontrar el archivo de migración? (s/n): ")
        if response.lower() != 's':
            sys.exit(1)
    
    # Realizar copia de seguridad de la base de datos
    print_heading("COPIA DE SEGURIDAD")
    print_warning("Se recomienda realizar una copia de seguridad de la base de datos antes de continuar.")
    response = input("¿Ha realizado una copia de seguridad de la base de datos? (s/n): ")
    if response.lower() != 's':
        print_warning("Se recomienda hacer una copia de seguridad antes de continuar.")
        response = input("¿Desea continuar sin copia de seguridad? (s/n): ")
        if response.lower() != 's':
            sys.exit(1)
    
    # Ejecutar las migraciones
    print_heading("EJECUTANDO MIGRACIONES")
    if not run_command("flask db upgrade", "Error al ejecutar la migración"):
        sys.exit(1)
    
    # Verificar estado de las tablas
    print_heading("VERIFICANDO TABLAS")
    if not run_command("python manage.py check_db", "Error al verificar la base de datos"):
        print_warning("Verificación de base de datos mostró posibles errores.")
    
    # Resumen y siguientes pasos
    print_heading("PROCESO COMPLETADO")
    print_info("La migración para eliminar causas y pérdidas se ha ejecutado correctamente.")
    print_info("Pasos adicionales recomendados:")
    print("1. Ejecute el script de limpieza para eliminar archivos inservibles:")
    print("   python cleanup.py")
    print("2. Reinicie la aplicación para aplicar todos los cambios:")
    print("   python run.py")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_warning("\nOperación cancelada por el usuario.")
        sys.exit(1)