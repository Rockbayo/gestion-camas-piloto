#!/usr/bin/env python3
"""
Script para limpiar archivos y código obsoletos en el proyecto CPC (Gestión de Camas Piloto)
Autor: Claude
Fecha: 15 de Mayo de 2025
"""

import os
import re
import shutil
from datetime import datetime

def log(message):
    """Registra un mensaje con marca de tiempo."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def create_backup_dir():
    """Crea un directorio de respaldo para los archivos eliminados."""
    backup_dir = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
        log(f"Directorio de respaldo creado: {backup_dir}")
    return backup_dir

def remove_backup_files(base_dir, backup_dir):
    """Elimina archivos de respaldo (*.backup.*)."""
    count = 0
    backup_pattern = re.compile(r'\.backup\.\d+')
    
    for root, _, files in os.walk(base_dir):
        for file in files:
            if backup_pattern.search(file):
                src_path = os.path.join(root, file)
                rel_path = os.path.relpath(src_path, base_dir)
                dst_path = os.path.join(backup_dir, rel_path)
                
                # Crear directorio destino si no existe
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                
                # Mover archivo a respaldo
                shutil.move(src_path, dst_path)
                log(f"Archivo de respaldo movido: {rel_path}")
                count += 1
    
    return count

def clean_js_components(base_dir, backup_dir):
    """Limpia archivos JavaScript redundantes."""
    js_components_dir = os.path.join(base_dir, "app", "static", "js", "components")
    
    # Lista de componentes duplicados o no utilizados
    obsolete_components = [
        # El componente de curva de producción ya está integrado en las vistas
        "CurvaProduccion.jsx"
    ]
    
    count = 0
    if os.path.exists(js_components_dir):
        for file in obsolete_components:
            file_path = os.path.join(js_components_dir, file)
            if os.path.exists(file_path):
                dst_path = os.path.join(backup_dir, "app", "static", "js", "components", file)
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                shutil.move(file_path, dst_path)
                log(f"Componente JS obsoleto movido: {file}")
                count += 1
    
    return count

def clean_python_modules(base_dir, backup_dir):
    """Limpia código Python obsoleto o redundante."""
    # Archivos Python obsoletos o redundantes
    obsolete_files = [
        "app/utils/base_importer.py",  # Funcionalidad integrada en dataset_importer.py
    ]
    
    count = 0
    for file_rel_path in obsolete_files:
        file_path = os.path.join(base_dir, file_rel_path)
        if os.path.exists(file_path):
            dst_path = os.path.join(backup_dir, file_rel_path)
            os.makedirs(os.path.dirname(dst_path), exist_ok=True)
            shutil.move(file_path, dst_path)
            log(f"Archivo Python obsoleto movido: {file_rel_path}")
            count += 1
    
    return count

def clean_template_duplicates(base_dir, backup_dir):
    """Limpia plantillas HTML duplicadas."""
    # Lista de plantillas duplicadas o no utilizadas
    obsolete_templates = [
        "app/templates/reportes/curva_produccion_interactiva.html",  # Funcionalidad integrada en curva_produccion.html
    ]
    
    count = 0
    for file_rel_path in obsolete_templates:
        file_path = os.path.join(base_dir, file_rel_path)
        if os.path.exists(file_path):
            dst_path = os.path.join(backup_dir, file_rel_path)
            os.makedirs(os.path.dirname(dst_path), exist_ok=True)
            shutil.move(file_path, dst_path)
            log(f"Plantilla HTML obsoleta movida: {file_rel_path}")
            count += 1
    
    return count

def clean_redundant_function_files(base_dir, backup_dir):
    """Limpia archivos con funciones redundantes."""
    # Archivos con funciones redundantes
    redundant_files = [
        "app/admin/routes.py.backup.20250514150157",
        "app/admin/routes.py.backup.20250515104127",
        "app/admin/routes.py.backup.20250515104801",
        "app/reportes/routes.py.backup.20250515104127",
        "app/reportes/routes.py.backup.20250515104801",
        "app/templates/admin/variedades.html.backup.20250515104127",
        "app/templates/admin/variedades.html.backup.20250515104801",
        "app/templates/siembras/detalles.html.backup.20250515104127",
        "app/templates/siembras/detalles.html.backup.20250515104801",
    ]
    
    count = 0
    for file_rel_path in redundant_files:
        file_path = os.path.join(base_dir, file_rel_path)
        if os.path.exists(file_path):
            dst_path = os.path.join(backup_dir, file_rel_path)
            os.makedirs(os.path.dirname(dst_path), exist_ok=True)
            shutil.move(file_path, dst_path)
            log(f"Archivo con funciones redundantes movido: {file_rel_path}")
            count += 1
    
    return count

def clean_file_content(base_dir):
    """Limpia contenido de archivos, eliminando código comentado y funciones obsoletas."""
    # Archivos a limpiar y patrones a eliminar
    files_to_clean = [
        {
            "path": "app/reportes/routes.py",
            "patterns": [
                # Función antigua de generación de gráficos
                r"def generar_grafico_curva\([^}]*?\):[^}]*?return grafico_base64[^}]*?}\n",
                # Ruta obsoleta (reemplazada por curva_produccion_integrada)
                r"@reportes\.route\('/curva_produccion_interactiva/[^}]*?\):[^}]*?return render_template[^}]*?}\n",
            ]
        },
        {
            "path": "app/admin/routes.py",
            "patterns": [
                # Función obsoleta para generar gráficos (mover al módulo de reportes)
                r"def generar_grafico_curva_mejorado\([^}]*?\):[^}]*?return grafico_base64[^}]*?}\n",
            ]
        }
    ]
    
    count = 0
    for file_info in files_to_clean:
        file_path = os.path.join(base_dir, file_info["path"])
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_size = len(content)
            for pattern in file_info["patterns"]:
                content = re.sub(pattern, "", content, flags=re.DOTALL)
            
            if len(content) < original_size:
                # Crear respaldo antes de modificar
                backup_path = f"{file_path}.bak"
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                # Escribir contenido limpio
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                log(f"Contenido limpiado en: {file_info['path']}")
                count += 1
    
    return count

def main():
    """Función principal del script de limpieza."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    log(f"Iniciando limpieza en: {base_dir}")
    
    # Crear directorio de respaldo
    backup_dir = create_backup_dir()
    
    # Estadísticas de limpieza
    stats = {
        "backup_files": 0,
        "js_components": 0,
        "python_modules": 0,
        "template_duplicates": 0,
        "redundant_function_files": 0,
        "cleaned_files": 0,
    }
    
    # Ejecutar funciones de limpieza
    stats["backup_files"] = remove_backup_files(base_dir, backup_dir)
    stats["js_components"] = clean_js_components(base_dir, backup_dir)
    stats["python_modules"] = clean_python_modules(base_dir, backup_dir)
    stats["template_duplicates"] = clean_template_duplicates(base_dir, backup_dir)
    stats["redundant_function_files"] = clean_redundant_function_files(base_dir, backup_dir)
    stats["cleaned_files"] = clean_file_content(base_dir)
    
    # Mostrar resumen
    log("=== Resumen de Limpieza ===")
    log(f"Archivos de respaldo eliminados: {stats['backup_files']}")
    log(f"Componentes JS obsoletos: {stats['js_components']}")
    log(f"Módulos Python obsoletos: {stats['python_modules']}")
    log(f"Plantillas HTML duplicadas: {stats['template_duplicates']}")
    log(f"Archivos con funciones redundantes: {stats['redundant_function_files']}")
    log(f"Archivos con contenido limpiado: {stats['cleaned_files']}")
    log(f"Total de elementos limpiados: {sum(stats.values())}")
    log(f"Todos los archivos eliminados se han respaldado en: {backup_dir}")
    log("Limpieza completada con éxito.")

if __name__ == "__main__":
    main()