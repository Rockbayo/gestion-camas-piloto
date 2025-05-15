#!/usr/bin/env python3
"""
Script de limpieza para el proyecto CPC (Control de Producción para Camas)
Elimina archivos temporales y optimiza el almacenamiento.

Uso:
    python cleanup.py [--dry-run] [--verbose]

Opciones:
    --dry-run       Muestra qué archivos se eliminarían sin realizar cambios
    --verbose       Muestra información detallada durante la ejecución
"""

import os
import sys
import argparse
import shutil
import time
from datetime import datetime, timedelta
import re

def parse_args():
    """Analiza los argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(description="Script de limpieza para el proyecto CPC")
    parser.add_argument('--dry-run', action='store_true', help="Simular ejecución sin eliminar archivos")
    parser.add_argument('--verbose', action='store_true', help="Mostrar información detallada")
    return parser.parse_args()

def print_verbose(message, verbose=False):
    """Imprime mensajes solo cuando verbose es True."""
    if verbose:
        print(message)

def get_file_age_days(filepath):
    """Obtiene la edad del archivo en días."""
    try:
        mtime = os.path.getmtime(filepath)
        age = (time.time() - mtime) / (60 * 60 * 24)  # Convertir segundos a días
        return age
    except Exception as e:
        print(f"Error al obtener la edad del archivo {filepath}: {e}")
        return 0

def delete_file(filepath, dry_run=False, verbose=False):
    """Elimina un archivo si no estamos en modo dry-run."""
    try:
        if dry_run:
            print_verbose(f"[SIMULACIÓN] Se eliminaría: {filepath}", True)
            return True
        else:
            print_verbose(f"Eliminando: {filepath}", verbose)
            os.remove(filepath)
            return True
    except Exception as e:
        print(f"Error al eliminar {filepath}: {e}")
        return False

def cleanup_temp_dir(temp_dir, dry_run=False, verbose=False):
    """Limpia el directorio temporal eliminando archivos antiguos."""
    if not os.path.exists(temp_dir):
        print_verbose(f"El directorio {temp_dir} no existe, omitiendo...", verbose)
        return 0
    
    count = 0
    print_verbose(f"Limpiando directorio temporal: {temp_dir}", verbose)
    
    for filename in os.listdir(temp_dir):
        filepath = os.path.join(temp_dir, filename)
        if os.path.isfile(filepath):
            # Eliminar archivos temporales más antiguos que 1 día
            if get_file_age_days(filepath) > 1:
                if delete_file(filepath, dry_run, verbose):
                    count += 1
    
    return count

def cleanup_logs(logs_dir, max_age_days=7, dry_run=False, verbose=False):
    """Limpia archivos de log antiguos."""
    if not os.path.exists(logs_dir):
        print_verbose(f"El directorio {logs_dir} no existe, omitiendo...", verbose)
        return 0
    
    count = 0
    print_verbose(f"Limpiando logs antiguos en: {logs_dir}", verbose)
    
    for filename in os.listdir(logs_dir):
        if not filename.endswith('.log'):
            continue
        
        filepath = os.path.join(logs_dir, filename)
        if os.path.isfile(filepath) and get_file_age_days(filepath) > max_age_days:
            if delete_file(filepath, dry_run, verbose):
                count += 1
    
    return count

def cleanup_pycache(root_dir, dry_run=False, verbose=False):
    """Elimina archivos __pycache__ y .pyc de forma recursiva."""
    count = 0
    
    for root, dirs, files in os.walk(root_dir):
        # Eliminar directorios __pycache__
        if '__pycache__' in dirs:
            pycache_path = os.path.join(root, '__pycache__')
            if dry_run:
                print_verbose(f"[SIMULACIÓN] Se eliminaría directorio: {pycache_path}", True)
                count += len([f for f in os.listdir(pycache_path) if os.path.isfile(os.path.join(pycache_path, f))])
            else:
                print_verbose(f"Eliminando directorio: {pycache_path}", verbose)
                try:
                    file_count = len([f for f in os.listdir(pycache_path) if os.path.isfile(os.path.join(pycache_path, f))])
                    shutil.rmtree(pycache_path)
                    count += file_count
                except Exception as e:
                    print(f"Error al eliminar {pycache_path}: {e}")
        
        # Eliminar archivos .pyc
        for file in files:
            if file.endswith('.pyc'):
                pyc_path = os.path.join(root, file)
                if delete_file(pyc_path, dry_run, verbose):
                    count += 1
    
    return count

def cleanup_migrations(migrations_dir, keep_latest=3, dry_run=False, verbose=False):
    """Limpia migraciones antiguas manteniendo las más recientes."""
    if not os.path.exists(migrations_dir):
        print_verbose(f"El directorio {migrations_dir} no existe, omitiendo...", verbose)
        return 0
    
    count = 0
    print_verbose(f"Limpiando migraciones antiguas en: {migrations_dir}", verbose)
    
    # Solo procesar archivos de migración con el patrón correcto
    migration_files = []
    pattern = re.compile(r'^[0-9a-f]+_.*\.py$')
    
    for filename in os.listdir(migrations_dir):
        if pattern.match(filename) and not filename.startswith('__'):
            filepath = os.path.join(migrations_dir, filename)
            if os.path.isfile(filepath):
                migration_files.append((filepath, os.path.getmtime(filepath)))
    
    # Ordenar por tiempo de modificación (más reciente primero)
    migration_files.sort(key=lambda x: x[1], reverse=True)
    
    # Mantener las keep_latest migraciones más recientes
    if len(migration_files) > keep_latest:
        for filepath, _ in migration_files[keep_latest:]:
            if delete_file(filepath, dry_run, verbose):
                count += 1
    
    return count

def find_unused_uploads(uploads_dir, db_file=None, days_threshold=30, dry_run=False, verbose=False):
    """
    Identifica y elimina archivos subidos que no están referenciados en la base de datos
    o que son más antiguos que el umbral especificado.
    """
    if not os.path.exists(uploads_dir):
        print_verbose(f"El directorio {uploads_dir} no existe, omitiendo...", verbose)
        return 0
    
    count = 0
    print_verbose(f"Buscando archivos subidos no utilizados en: {uploads_dir}", verbose)
    
    # En este ejemplo simplemente eliminamos archivos antiguos
    # En una implementación real, verificaríamos referencias en la base de datos
    for root, _, files in os.walk(uploads_dir):
        for file in files:
            # Excluir archivos especiales
            if file.startswith('.') or file == '.gitkeep':
                continue
                
            filepath = os.path.join(root, file)
            if get_file_age_days(filepath) > days_threshold:
                if delete_file(filepath, dry_run, verbose):
                    count += 1
    
    return count

def cleanup_abandoned_sessions(flask_session_dir, max_age_days=7, dry_run=False, verbose=False):
    """Limpia archivos de sesión de Flask abandonados."""
    if not os.path.exists(flask_session_dir):
        print_verbose(f"El directorio {flask_session_dir} no existe, omitiendo...", verbose)
        return 0
    
    count = 0
    print_verbose(f"Limpiando sesiones abandonadas en: {flask_session_dir}", verbose)
    
    for filename in os.listdir(flask_session_dir):
        filepath = os.path.join(flask_session_dir, filename)
        if os.path.isfile(filepath) and get_file_age_days(filepath) > max_age_days:
            if delete_file(filepath, dry_run, verbose):
                count += 1
    
    return count

def main():
    """Función principal del script de limpieza."""
    args = parse_args()
    dry_run = args.dry_run
    verbose = args.verbose
    
    # Contador total
    total_cleaned = 0
    
    # Directorio base del proyecto
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Mensaje de inicio
    print("=" * 50)
    print(f"Script de limpieza CPC - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if dry_run:
        print("Modo: SIMULACIÓN (no se eliminarán archivos)")
    print("=" * 50)
    
    # Limpiar directorios temporales
    temp_dirs = [
        os.path.join(base_dir, 'uploads', 'temp'),
        os.path.join(base_dir, 'tmp'),
        os.path.join(base_dir, 'instance')
    ]
    
    for temp_dir in temp_dirs:
        count = cleanup_temp_dir(temp_dir, dry_run, verbose)
        total_cleaned += count
        print(f"- Limpiados {count} archivos temporales en {os.path.basename(temp_dir)}")
    
    # Limpiar archivos de log
    logs_dir = os.path.join(base_dir, 'logs')
    count = cleanup_logs(logs_dir, 7, dry_run, verbose)  # Conservar logs de 7 días
    total_cleaned += count
    print(f"- Limpiados {count} archivos de log antiguos")
    
    # Limpiar __pycache__ y .pyc
    count = cleanup_pycache(base_dir, dry_run, verbose)
    total_cleaned += count
    print(f"- Limpiados {count} archivos de caché de Python")
    
    # Limpiar migraciones antiguas
    migrations_dir = os.path.join(base_dir, 'migrations', 'versions')
    count = cleanup_migrations(migrations_dir, 3, dry_run, verbose)  # Conservar 3 migraciones más recientes
    total_cleaned += count
    print(f"- Limpiadas {count} migraciones antiguas")
    
    # Buscar archivos subidos no utilizados
    uploads_dir = os.path.join(base_dir, 'uploads')
    count = find_unused_uploads(uploads_dir, None, 30, dry_run, verbose)  # Archivos más antiguos que 30 días
    total_cleaned += count
    print(f"- Limpiados {count} archivos subidos antiguos o no utilizados")
    
    # Limpiar sesiones abandonadas
    flask_session_dir = os.path.join(base_dir, 'flask_session')
    count = cleanup_abandoned_sessions(flask_session_dir, 7, dry_run, verbose)
    total_cleaned += count
    print(f"- Limpiadas {count} sesiones abandonadas")
    
    # Resumen final
    print("=" * 50)
    print(f"Total de archivos limpiados: {total_cleaned}")
    if dry_run:
        print("NOTA: Esta fue solo una simulación. Ejecute sin --dry-run para eliminar los archivos.")
    print("=" * 50)

if __name__ == "__main__":
    main()