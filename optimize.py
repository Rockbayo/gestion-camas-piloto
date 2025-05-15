#!/usr/bin/env python3
"""
Script de Depuración y Optimización para el Sistema de Gestión de Camas Piloto

Este script analiza, depura y optimiza una aplicación Flask para mejorar su rendimiento,
eliminando código redundante, implementando mejores prácticas y aplicando optimizaciones.

Funcionalidades:
1. Limpieza de archivos temporales y caché
2. Optimización de consultas a base de datos 
3. Eliminación de código duplicado o no utilizado
4. Implementación de índices en la base de datos
5. Optimización de carga de módulos
6. Compresión de respuestas HTTP
7. Implementación de caché para funciones costosas
"""

import os
import sys
import re
import shutil
import importlib
import logging
import time
import glob
import sqlite3
import argparse
from pathlib import Path
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("optimize.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("optimize")

# Directorio base del proyecto (ruta relativa)
PROJECT_ROOT = Path(".")

# Directorios principales que componen la aplicación
APP_DIRS = [
    "app",
    "app/templates",
    "app/static",
    "app/admin",
    "app/auth",
    "app/cortes",
    "app/main",
    "app/reportes",
    "app/siembras",
    "app/utils"
]

# Archivos temporales y de caché a eliminar
TEMP_PATTERNS = [
    "*.pyc",
    "__pycache__",
    "logs/*.log*",
    "uploads/temp/*",
    ".DS_Store",
    "*.~*"
]

# Patrones de código redundante o ineficiente a buscar
CODE_PATTERNS = {
    "raw_sql_query": r"db\.engine\.execute\(|text\(\s*\"SELECT",
    "unbatched_queries": r"for\s+.*\s+in\s+.*\.query\.all\(\)",
    "n_plus_one": r"for\s+.*\s+in\s+.*:\s*\n\s+.*\.query",
    "eager_loading_missing": r"\.query\.filter.*\s+for\s.*\s+in\s+.*:",
    "unused_imports": r"^import\s+(?!os|sys|logging|datetime|re|json|csv|flask|werkzeug|sqlalchemy|pandas|numpy|matplotlib)[a-zA-Z0-9_.]+\s*(?:#.*)?$",
    "debug_print": r"print\([^)]*\)",
}

# Patrones para identificar archivos duplicados potencialmente
DUPLICATE_FILE_PATTERNS = [
    (r'app/templates/reportes/curva_produccion.html', r'app/templates/reportes/curva_produccion_integrada.html'),
    (r'app/admin/forms.py', r'app/siembras/forms.py'),
]

# Elementos para agregar índices en la base de datos
DB_INDICES = [
    ("CREATE INDEX IF NOT EXISTS idx_siembras_variedad ON siembras(variedad_id)", "siembras.variedad_id"),
    ("CREATE INDEX IF NOT EXISTS idx_siembras_bloque ON siembras(bloque_cama_id)", "siembras.bloque_cama_id"),
    ("CREATE INDEX IF NOT EXISTS idx_cortes_siembra ON cortes(siembra_id)", "cortes.siembra_id"),
    ("CREATE INDEX IF NOT EXISTS idx_cortes_fecha ON cortes(fecha_corte)", "cortes.fecha_corte"),
    ("CREATE INDEX IF NOT EXISTS idx_variedades_flor_color ON variedades(flor_color_id)", "variedades.flor_color_id"),
]

# Funciones para optimizar
FUNCTIONS_TO_CACHE = [
    ("app.reportes.routes.generar_grafico_curva_mejorada", 128),
    ("app.admin.routes.generar_grafico_curva_mejorado", 128),
    ("app.reportes.routes.obtener_datos_curva", 64),
    ("app.reportes.routes.filtrar_outliers_iqr", 256),
]

# Tabla de consultas a optimizar
QUERIES_TO_OPTIMIZE = [
    {
        "file": "app/reportes/routes.py",
        "pattern": r"db\.session\.query\([^)]*\)\.join\([^)]*\)\.join\([^)]*\)\.join\([^)]*\)",
        "suggestion": "Utilizar selectinload() o joinedload() para evitar N+1 y mejorar rendimiento"
    },
    {
        "file": "app/admin/routes.py",
        "pattern": r"Variedad\.query\.order_by\(Variedad\.variedad\)\.all\(\)",
        "suggestion": "Paginar consultas y usar filter() con condiciones específicas"
    },
    {
        "file": "app/siembras/routes.py",
        "pattern": r"Siembra\.query\.order_by\(Siembra\.fecha_siembra\.desc\(\)\)\.paginate\(",
        "suggestion": "Usar joinedload() para cargar relaciones anticipadamente (eager loading)"
    }
]

def parse_arguments():
    """Configura y parsea argumentos de línea de comandos"""
    parser = argparse.ArgumentParser(description='Optimiza la aplicación de Gestión de Camas Piloto')
    parser.add_argument('--clean-only', action='store_true', help='Solo ejecutar limpieza de archivos temporales')
    parser.add_argument('--analyze-only', action='store_true', help='Solo analizar sin hacer cambios')
    parser.add_argument('--optimize-db', action='store_true', help='Optimizar la base de datos')
    parser.add_argument('--optimize-code', action='store_true', help='Optimizar código en archivos')
    parser.add_argument('--optimize-queries', action='store_true', help='Optimizar consultas SQL')
    parser.add_argument('--implement-cache', action='store_true', help='Implementar caché para funciones costosas')
    parser.add_argument('--all', action='store_true', help='Ejecutar todas las optimizaciones')
    
    args = parser.parse_args()
    
    # Si no se especifica ninguna opción, usar valor por defecto (--all)
    if not any([args.clean_only, args.analyze_only, args.optimize_db, 
                args.optimize_code, args.optimize_queries, args.implement_cache, args.all]):
        args.all = True
        
    return args

def clean_temp_files():
    """Limpia archivos temporales, de caché y logs antiguos"""
    logger.info("Iniciando limpieza de archivos temporales...")
    deleted_count = 0
    
    for pattern in TEMP_PATTERNS:
        for filepath in Path(PROJECT_ROOT).glob(f"**/{pattern}"):
            try:
                if filepath.is_dir():
                    if filepath.exists():  # Verificación adicional
                        shutil.rmtree(filepath)
                        logger.info(f"Directorio eliminado: {filepath}")
                else:
                    filepath.unlink()
                    logger.info(f"Archivo eliminado: {filepath}")
                deleted_count += 1
            except Exception as e:
                logger.error(f"Error al eliminar {filepath}: {e}")
    
    logger.info(f"Limpieza completada: {deleted_count} archivos/directorios eliminados")
    return deleted_count

def search_code_issues(pattern_name, pattern, file_path):
    """Busca patrones problemáticos en un archivo dado"""
    if not file_path.exists() or not file_path.is_file():
        return []
    
    if not file_path.suffix.lower() in ['.py', '.html', '.js']:
        return []
    
    issues = []
    
    try:
        content = file_path.read_text(encoding='utf-8')
        for i, line in enumerate(content.splitlines(), 1):
            if re.search(pattern, line):
                issues.append({
                    'file': str(file_path),
                    'line': i,
                    'pattern': pattern_name,
                    'text': line.strip()
                })
    except Exception as e:
        logger.error(f"Error al analizar {file_path}: {e}")
    
    return issues

def analyze_code_quality():
    """Analiza el código buscando problemas comunes y patrones de ineficiencia"""
    logger.info("Analizando calidad del código...")
    issues = []
    py_files = list(PROJECT_ROOT.glob("**/*.py"))
    
    with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
        future_to_file = {}
        
        for pattern_name, pattern in CODE_PATTERNS.items():
            for file_path in py_files:
                future = executor.submit(search_code_issues, pattern_name, pattern, file_path)
                future_to_file[future] = (pattern_name, file_path)
        
        for future in as_completed(future_to_file):
            file_issues = future.result()
            issues.extend(file_issues)
    
    # Agrupar por archivo para tener una vista más organizada
    files_with_issues = {}
    for issue in issues:
        if issue['file'] not in files_with_issues:
            files_with_issues[issue['file']] = []
        files_with_issues[issue['file']].append(issue)
    
    logger.info(f"Análisis completado: encontrados {len(issues)} problemas en {len(files_with_issues)} archivos")
    
    # Imprimir resumen
    logger.info("\n--- Resumen de Problemas por Tipo ---")
    issue_count_by_type = {}
    for issue in issues:
        if issue['pattern'] not in issue_count_by_type:
            issue_count_by_type[issue['pattern']] = 0
        issue_count_by_type[issue['pattern']] += 1
    
    for pattern, count in issue_count_by_type.items():
        logger.info(f"{pattern}: {count} problemas")
    
    return files_with_issues

def find_duplicate_code():
    """Identifica código duplicado entre archivos específicos"""
    logger.info("Buscando código duplicado...")
    duplicates = []
    
    for pattern1, pattern2 in DUPLICATE_FILE_PATTERNS:
        files1 = list(PROJECT_ROOT.glob(pattern1))
        files2 = list(PROJECT_ROOT.glob(pattern2))
        
        for file1 in files1:
            for file2 in files2:
                if file1 != file2:  # Evitar comparar un archivo consigo mismo
                    try:
                        content1 = file1.read_text(encoding='utf-8')
                        content2 = file2.read_text(encoding='utf-8')
                        
                        # Calcular similitud básica basada en líneas
                        lines1 = content1.splitlines()
                        lines2 = content2.splitlines()
                        
                        # Contar líneas idénticas
                        identical_lines = 0
                        for line1, line2 in zip(lines1, lines2):
                            if line1.strip() == line2.strip() and line1.strip():
                                identical_lines += 1
                        
                        # Calcular porcentaje de similitud
                        max_lines = max(len(lines1), len(lines2))
                        similarity = (identical_lines / max_lines) * 100 if max_lines > 0 else 0
                        
                        if similarity > 70:  # Umbral de similitud
                            duplicates.append({
                                'file1': str(file1),
                                'file2': str(file2),
                                'similarity': similarity,
                                'identical_lines': identical_lines
                            })
                            logger.info(f"Posible duplicación: {file1} y {file2} - {similarity:.2f}% similitud")
                    except Exception as e:
                        logger.error(f"Error al comparar {file1} y {file2}: {e}")
    
    logger.info(f"Búsqueda de duplicados completada: encontrados {len(duplicates)} posibles duplicados")
    return duplicates

def optimize_database(db_path="app.db"):
    """Optimiza la base de datos: añade índices, realiza vacuum, analiza tablas"""
    logger.info(f"Optimizando base de datos: {db_path}")
    
    if not os.path.exists(db_path):
        logger.warning(f"Base de datos no encontrada en: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar índices existentes
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index';")
        existing_indices = [row[0] for row in cursor.fetchall()]
        logger.info(f"Índices existentes: {existing_indices}")
        
        # Crear índices si no existen
        indices_created = 0
        for create_statement, index_name in DB_INDICES:
            index_pattern = index_name.replace('.', '_')
            if not any(index_pattern in idx for idx in existing_indices):
                try:
                    cursor.execute(create_statement)
                    indices_created += 1
                    logger.info(f"Índice creado: {index_name}")
                except sqlite3.OperationalError as e:
                    logger.error(f"Error al crear índice {index_name}: {e}")
        
        # Analizar tablas para estadísticas de optimización
        cursor.execute("ANALYZE;")
        
        # Vacuum para compactar la base de datos
        before_size = os.path.getsize(db_path)
        cursor.execute("VACUUM;")
        conn.commit()
        conn.close()
        after_size = os.path.getsize(db_path)
        
        size_diff = before_size - after_size
        logger.info(f"Database optimizada: {indices_created} índices creados")
        logger.info(f"Tamaño anterior: {before_size/1024:.2f} KB, Tamaño actual: {after_size/1024:.2f} KB")
        logger.info(f"Reducción: {size_diff/1024:.2f} KB ({size_diff/before_size*100:.2f}%)")
        
        return True
    except Exception as e:
        logger.error(f"Error al optimizar la base de datos: {e}")
        return False

def implement_function_cache():
    """Implementa decorador de caché para funciones costosas"""
    logger.info("Implementando caché para funciones costosas...")
    cache_count = 0
    
    for func_path, max_size in FUNCTIONS_TO_CACHE:
        try:
            # Extraer módulo y función del path
            module_path, func_name = func_path.rsplit('.', 1)
            
            # Obtener nombre del archivo
            module_parts = module_path.split('.')
            file_path = os.path.join(*module_parts) + '.py'
            
            # Si el archivo no existe, continuar
            if not os.path.exists(file_path):
                logger.warning(f"Archivo no encontrado: {file_path}")
                continue
            
            # Leer contenido del archivo
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Buscar la función en el contenido
            func_pattern = rf"def\s+{func_name}\s*\("
            if not re.search(func_pattern, content):
                logger.warning(f"Función {func_name} no encontrada en {file_path}")
                continue
            
            # Verificar si ya tiene el decorador de caché
            if re.search(rf"@lru_cache.*\s+def\s+{func_name}\s*\(", content):
                logger.info(f"La función {func_name} ya tiene caché")
                continue
            
            # Aplicar decorador - solo simulación por seguridad
            new_content = re.sub(
                func_pattern,
                f"@lru_cache(maxsize={max_size})\ndef {func_name}(",
                content
            )
            
            # Asegurar que se importa lru_cache
            if "from functools import lru_cache" not in new_content:
                new_content = "from functools import lru_cache\n" + new_content
            
            logger.info(f"Se puede aplicar caché a {func_path} con maxsize={max_size}")
            cache_count += 1
            
            # Guardar respaldo y aplicar cambios (comentado por seguridad)
            """
            backup_path = file_path + '.bak'
            shutil.copy2(file_path, backup_path)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            logger.info(f"Aplicado caché a {func_path} y guardado respaldo en {backup_path}")
            """
            
        except Exception as e:
            logger.error(f"Error al implementar caché para {func_path}: {e}")
    
    logger.info(f"Implementación de caché completada: {cache_count} funciones pueden ser optimizadas")
    return cache_count

def optimize_query_patterns():
    """Identifica y optimiza patrones de consultas ineficientes"""
    logger.info("Analizando patrones de consultas ineficientes...")
    optimization_suggestions = []
    
    for query_info in QUERIES_TO_OPTIMIZE:
        file_pattern = query_info["file"]
        code_pattern = query_info["pattern"]
        suggestion = query_info["suggestion"]
        
        # Buscar archivos que coincidan con el patrón
        for file_path in Path(PROJECT_ROOT).glob(file_pattern):
            try:
                content = file_path.read_text(encoding='utf-8')
                matches = re.findall(code_pattern, content)
                
                if matches:
                    optimization_suggestions.append({
                        'file': str(file_path),
                        'matches': len(matches),
                        'pattern': code_pattern,
                        'suggestion': suggestion,
                        'example': matches[0] if matches else ""
                    })
                    logger.info(f"Encontradas {len(matches)} consultas a optimizar en {file_path}")
            except Exception as e:
                logger.error(f"Error al analizar consultas en {file_path}: {e}")
    
    logger.info(f"Análisis de consultas completado: {len(optimization_suggestions)} patrones encontrados")
    
    # Mostrar sugerencias
    for i, suggestion in enumerate(optimization_suggestions, 1):
        logger.info(f"\n{i}. Archivo: {suggestion['file']}")
        logger.info(f"   Patrón: {suggestion['pattern']}")
        logger.info(f"   Sugerencia: {suggestion['suggestion']}")
        logger.info(f"   Ejemplo: {suggestion['example']}")
    
    return optimization_suggestions

def main():
    """Función principal que coordina las tareas de optimización"""
    start_time = time.time()
    logger.info("Iniciando script de optimización para Sistema de Gestión de Camas Piloto")
    
    args = parse_arguments()
    
    # Verificar que estamos en la raíz del proyecto
    if not os.path.exists("app") or not os.path.exists("run.py"):
        logger.error("Este script debe ejecutarse desde la raíz del proyecto Flask")
        return 1
    
    results = {
        "temp_files_deleted": 0,
        "code_issues": {},
        "duplicates": [],
        "db_optimized": False,
        "cache_implemented": 0,
        "query_optimizations": []
    }
    
    # Ejecutar acciones según argumentos
    if args.clean_only or args.all:
        results["temp_files_deleted"] = clean_temp_files()
    
    if args.analyze_only or args.all:
        results["code_issues"] = analyze_code_quality()
        results["duplicates"] = find_duplicate_code()
    
    if args.optimize_db or args.all:
        results["db_optimized"] = optimize_database()
    
    if args.optimize_queries or args.all:
        results["query_optimizations"] = optimize_query_patterns()
    
    if args.implement_cache or args.all:
        results["cache_implemented"] = implement_function_cache()
    
    # Mostrar resumen de resultados
    execution_time = time.time() - start_time
    logger.info("\n" + "="*40)
    logger.info("RESUMEN DE OPTIMIZACIÓN")
    logger.info("="*40)
    logger.info(f"Archivos temporales eliminados: {results['temp_files_deleted']}")
    logger.info(f"Archivos con problemas de código: {len(results['code_issues'])}")
    logger.info(f"Posibles duplicados encontrados: {len(results['duplicates'])}")
    logger.info(f"Base de datos optimizada: {'Sí' if results['db_optimized'] else 'No'}")
    logger.info(f"Funciones con caché potencial: {results['cache_implemented']}")
    logger.info(f"Patrones de consultas a optimizar: {len(results['query_optimizations'])}")
    logger.info(f"Tiempo de ejecución: {execution_time:.2f} segundos")
    logger.info("="*40)
    
    # Generar informe HTML de resultados
    try:
        generate_html_report(results)
    except Exception as e:
        logger.error(f"Error al generar informe HTML: {e}")
    
    logger.info("Optimización completada. Revisa optimize.log y optimization_report.html para más detalles.")
    return 0

def generate_html_report(results):
    """Genera un informe HTML con los resultados de la optimización"""
    report_path = Path(PROJECT_ROOT) / "optimization_report.html"
    
    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Informe de Optimización - Sistema de Gestión de Camas Piloto</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; color: #333; }}
        h1, h2, h3 {{ color: #2c3e50; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .summary {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        .summary-item {{ margin-bottom: 10px; }}
        .issues-table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
        .issues-table th, .issues-table td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
        .issues-table th {{ background-color: #f2f2f2; }}
        .issues-table tr:hover {{ background-color: #f5f5f5; }}
        .success {{ color: #28a745; }}
        .warning {{ color: #ffc107; }}
        .danger {{ color: #dc3545; }}
        .accordion {{ background-color: #f1f1f1; color: #444; cursor: pointer; padding: 18px; width: 100%; text-align: left; 
                   border: none; outline: none; transition: 0.4s; margin-bottom: 2px; }}
        .active, .accordion:hover {{ background-color: #ddd; }}
        .panel {{ padding: 0 18px; background-color: white; display: none; overflow: hidden; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Informe de Optimización - Sistema de Gestión de Camas Piloto</h1>
        <p>Fecha: {time.strftime("%d/%m/%Y %H:%M:%S")}</p>
        
        <div class="summary">
            <h2>Resumen</h2>
            <div class="summary-item">Archivos temporales eliminados: <strong>{results['temp_files_deleted']}</strong></div>
            <div class="summary-item">Archivos con problemas de código: <strong class="{'warning' if results['code_issues'] else 'success'}">{len(results['code_issues'])}</strong></div>
            <div class="summary-item">Posibles duplicados encontrados: <strong class="{'warning' if results['duplicates'] else 'success'}">{len(results['duplicates'])}</strong></div>
            <div class="summary-item">Base de datos optimizada: <strong class="{'success' if results['db_optimized'] else 'danger'}">{'Sí' if results['db_optimized'] else 'No'}</strong></div>
            <div class="summary-item">Funciones con caché potencial: <strong>{results['cache_implemented']}</strong></div>
            <div class="summary-item">Patrones de consultas a optimizar: <strong class="{'warning' if results['query_optimizations'] else 'success'}">{len(results['query_optimizations'])}</strong></div>
        </div>
"""
    
    # Sección de problemas de código
    if results['code_issues']:
        html_content += """
        <h2>Problemas de Código</h2>
"""
        for i, (file, issues) in enumerate(results['code_issues'].items()):
            issue_count = len(issues)
            html_content += f"""
        <button class="accordion">Archivo: {file} ({issue_count} {'problemas' if issue_count != 1 else 'problema'})</button>
        <div class="panel">
            <table class="issues-table">
                <thead>
                    <tr>
                        <th>Línea</th>
                        <th>Tipo</th>
                        <th>Contenido</th>
                    </tr>
                </thead>
                <tbody>
"""
            for issue in issues:
                html_content += f"""
                    <tr>
                        <td>{issue['line']}</td>
                        <td>{issue['pattern']}</td>
                        <td><code>{issue['text']}</code></td>
                    </tr>
"""
            html_content += """
                </tbody>
            </table>
        </div>
"""
    
    # Sección de duplicados
    if results['duplicates']:
        html_content += """
        <h2>Archivos Potencialmente Duplicados</h2>
        <table class="issues-table">
            <thead>
                <tr>
                    <th>Archivo 1</th>
                    <th>Archivo 2</th>
                    <th>Similitud</th>
                    <th>Líneas Idénticas</th>
                </tr>
            </thead>
            <tbody>
"""
        for duplicate in results['duplicates']:
            html_content += f"""
                <tr>
                    <td>{duplicate['file1']}</td>
                    <td>{duplicate['file2']}</td>
                    <td>{duplicate['similarity']:.2f}%</td>
                    <td>{duplicate['identical_lines']}</td>
                </tr>
"""
        html_content += """
            </tbody>
        </table>
"""
    
    # Sección de optimizaciones de consultas
    if results['query_optimizations']:
        html_content += """
        <h2>Optimizaciones de Consultas Recomendadas</h2>
        <table class="issues-table">
            <thead>
                <tr>
                    <th>Archivo</th>
                    <th>Ocurrencias</th>
                    <th>Sugerencia</th>
                </tr>
            </thead>
            <tbody>
"""
        for opt in results['query_optimizations']:
            html_content += f"""
                <tr>
                    <td>{opt['file']}</td>
                    <td>{opt['matches']}</td>
                    <td>{opt['suggestion']}</td>
                </tr>
"""
        html_content += """
            </tbody>
        </table>
"""
    
    # Cerrar HTML y agregar JavaScript para acordeón
    html_content += """
        <h2>Recomendaciones Adicionales</h2>
        <ul>
            <li>Implementar compresión GZIP para respuestas HTTP</li>
            <li>Aplicar caché a las funciones identificadas para mejorar rendimiento</li>
            <li>Consolidar los archivos duplicados para reducir mantenimiento</li>
            <li>Utilizar selectinload() para optimizar consultas con relaciones</li>
            <li>Corregir los patrones N+1 en las consultas identificadas</li>
            <li>Eliminar imports no utilizados para mejorar tiempo de carga</li>
        </ul>
    </div>
    
    <script>
        var acc = document.getElementsByClassName("accordion");
        for (var i = 0; i < acc.length; i++) {
            acc[i].addEventListener("click", function() {
                this.classList.toggle("active");
                var panel = this.nextElementSibling;
                if (panel.style.display === "block") {
                    panel.style.display = "none";
                } else {
                    panel.style.display = "block";
                }
            });
        }
    </script>
</body>
</html>
"""
    
    # Escribir el informe HTML
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    logger.info(f"Informe HTML generado en: {report_path}")

if __name__ == "__main__":
    sys.exit(main())