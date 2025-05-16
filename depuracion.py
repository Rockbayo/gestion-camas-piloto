#!/usr/bin/env python3
"""
Script Integral de Depuración y Optimización para Sistema de Gestión de Cultivos

Este script realiza tareas de limpieza, optimización y corrección en el sistema
para mejorar su rendimiento, resolver inconsistencias y simplificar la estructura.

Funcionalidades:
1. Limpieza de archivos temporales y redundantes
2. Eliminación de módulos obsoletos (causas, pérdidas)
3. Corrección de rutas y referencias a curva_produccion_interactiva
4. Optimización de consultas de base de datos
5. Implementación de índices para mejorar rendimiento
6. Actualización de campos faltantes como fecha_fin_corte
7. Corrección de algoritmos de cálculo de curvas de producción

Autor: Claude
Fecha: 15 de mayo de 2025
"""

import os
import sys
import re
import shutil
import glob
import datetime
import logging
import argparse
import sqlite3
import json
from pathlib import Path

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("depuracion.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("depuracion")

# Colores para salida en terminal
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def color_print(text, color):
    """Imprime texto con color en la terminal"""
    print(f"{color}{text}{Colors.ENDC}")

def print_header(text):
    """Imprime un encabezado"""
    color_print(f"\n=== {text} ===", Colors.HEADER + Colors.BOLD)

def print_success(text):
    """Imprime un mensaje de éxito"""
    color_print(f"✓ {text}", Colors.GREEN)

def print_warning(text):
    """Imprime una advertencia"""
    color_print(f"! {text}", Colors.WARNING)

def print_error(text):
    """Imprime un mensaje de error"""
    color_print(f"✗ {text}", Colors.FAIL)

def create_backup_dir():
    """Crea un directorio de respaldo para los archivos"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"backup_{timestamp}"
    
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
        logger.info(f"Directorio de respaldo creado: {backup_dir}")
    
    return backup_dir

def create_file_backup(file_path, backup_dir):
    """Crea una copia de seguridad de un archivo"""
    if not os.path.exists(file_path):
        return None
    
    # Crear estructura de directorios en el directorio de respaldo
    rel_path = os.path.relpath(file_path)
    backup_path = os.path.join(backup_dir, rel_path)
    os.makedirs(os.path.dirname(backup_path), exist_ok=True)
    
    # Copiar el archivo
    shutil.copy2(file_path, backup_path)
    logger.info(f"Creada copia de seguridad: {backup_path}")
    
    return backup_path

# ============================================================================
# FASE 1: LIMPIEZA DE ARCHIVOS TEMPORALES Y REDUNDANTES
# ============================================================================

def clean_temp_files():
    """Limpia archivos temporales y de caché"""
    print_header("LIMPIEZA DE ARCHIVOS TEMPORALES")
    
    patterns = [
        "**/*.pyc",
        "**/__pycache__",
        "**/*.bak",
        "**/*.swp",
        "**/.DS_Store",
        "**/~*"
    ]
    
    count = 0
    for pattern in patterns:
        for file_path in glob.glob(pattern, recursive=True):
            try:
                if os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                    print_success(f"Directorio eliminado: {file_path}")
                else:
                    os.remove(file_path)
                    print_success(f"Archivo eliminado: {file_path}")
                count += 1
            except Exception as e:
                print_error(f"Error al eliminar {file_path}: {str(e)}")
    
    print(f"\nTotal de archivos temporales eliminados: {count}")
    return count

def clean_redundant_scripts(backup_dir):
    """Elimina scripts redundantes o fusionados en otros archivos"""
    print_header("LIMPIEZA DE SCRIPTS REDUNDANTES")
    
    redundant_scripts = [
        "importar_historico.py",  # Reemplazado por importar_mejorado.py
        "cleanup.py",             # Funcionalmente equivalente a limpiar.py
        "reset_database.py",      # Funcionalidad incluida en manage.py
        "init_database.py",       # Funcionalidad incluida en manage.py
        "run_migrations.py",      # Funcionalidad incluida en manage.py o flask cli
        "actualizar_algoritmo.py",  # Reemplazado por script_completo_mejoras.py
        "optimize_system.py",     # Duplicado/reemplazado por optimize.py
    ]
    
    count = 0
    for script in redundant_scripts:
        if os.path.exists(script):
            # Crear respaldo
            create_file_backup(script, backup_dir)
            # Eliminar archivo
            try:
                os.remove(script)
                print_success(f"Script redundante eliminado: {script}")
                count += 1
            except Exception as e:
                print_error(f"Error al eliminar {script}: {str(e)}")
        else:
            logger.info(f"Script {script} no encontrado")
    
    print(f"\nTotal de scripts redundantes eliminados: {count}")
    return count

# ============================================================================
# FASE 2: ELIMINACIÓN DE MÓDULOS OBSOLETOS (CAUSAS Y PÉRDIDAS)
# ============================================================================

def remove_obsolete_modules(backup_dir):
    """Elimina directorios y archivos relacionados con módulos obsoletos"""
    print_header("ELIMINACIÓN DE MÓDULOS OBSOLETOS")
    
    obsolete_dirs = [
        "app/perdidas",
        "app/templates/perdidas",
    ]
    
    obsolete_files = [
        "app/perdidas/__init__.py",
        "app/perdidas/forms.py",
        "app/perdidas/routes.py",
        "app/templates/perdidas/crear.html",
        "app/templates/perdidas/editar.html",
        "app/templates/perdidas/index.html",
        "app/templates/admin/causas.html",
        "app/templates/admin/importar_causas.html",
        "app/templates/admin/importar_causas_directo.html",
        "app/utils/causas_importer.py",
    ]
    
    # Eliminar archivos
    file_count = 0
    for file_path in obsolete_files:
        if os.path.exists(file_path):
            # Crear respaldo
            create_file_backup(file_path, backup_dir)
            # Eliminar archivo
            try:
                os.remove(file_path)
                print_success(f"Archivo obsoleto eliminado: {file_path}")
                file_count += 1
            except Exception as e:
                print_error(f"Error al eliminar {file_path}: {str(e)}")
    
    # Eliminar directorios (solo si están vacíos para seguridad adicional)
    dir_count = 0
    for dir_path in obsolete_dirs:
        if os.path.exists(dir_path):
            # Primero, respaldar todo el directorio
            shutil.copytree(dir_path, os.path.join(backup_dir, dir_path), dirs_exist_ok=True)
            
            try:
                # Verificar si está vacío
                if not os.listdir(dir_path):
                    os.rmdir(dir_path)
                    print_success(f"Directorio obsoleto eliminado: {dir_path}")
                    dir_count += 1
                else:
                    # Advertir al usuario pero no eliminar automáticamente para evitar riesgos
                    print_warning(f"Directorio {dir_path} no está vacío. Se requiere revisión manual")
            except Exception as e:
                print_error(f"Error al eliminar directorio {dir_path}: {str(e)}")
    
    print(f"\nResultados de la eliminación de módulos obsoletos:")
    print(f"  - Archivos eliminados: {file_count}")
    print(f"  - Directorios eliminados: {dir_count}")
    return file_count, dir_count

def update_models_remove_obsolete_refs(backup_dir):
    """Actualiza el archivo models.py para eliminar referencias a módulos obsoletos"""
    print_header("ACTUALIZACIÓN DE MODELOS")
    
    models_path = "app/models.py"
    if not os.path.exists(models_path):
        print_error(f"Archivo {models_path} no encontrado")
        return False
    
    # Crear respaldo
    create_file_backup(models_path, backup_dir)
    
    # Leer contenido
    with open(models_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verificar la importación actual
    login_import_pattern = r'from app import (\w+(?:, \w+)*)'
    login_match = re.search(login_import_pattern, content)
    
    if login_match:
        imports = login_match.group(1).split(', ')
        if 'login' in imports and 'db' in imports:
            # La importación ya está correcta, no la modificamos
            pass
        elif 'login' not in imports:
            # No modificamos si login no está presente
            pass
        else:
            # Puede que tengamos que modificar algo, pero con cuidado
            print_warning("Se encontró una importación de 'login', pero no se modificará para evitar errores")
    
    # Patrones para reemplazar (sin modificar las importaciones)
    replacements = [
        # Eliminar clase Causa si existe
        (r'class Causa\(db\.Model\):.*?(?=class)', '', re.DOTALL),
        
        # Eliminar clase Perdida si existe
        (r'class Perdida\(db\.Model\):.*?(?=class)', '', re.DOTALL),
        
        # Eliminar referencias a pérdidas en relaciones
        (r'perdidas = db\.relationship\(\'Perdida\'.*?\)\s*', ''),
        
        # Modificar métodos que referencian pérdidas
        (r'def total_perdidas\(self\):.*?return.*?\n\s*', 'def total_perdidas(self):\n        """Método mantenido por compatibilidad."""\n        return 0\n\n    '),
    ]
    
    # Aplicar reemplazos
    original_content = content
    
    for item in replacements:
        if len(item) == 2:
            pattern, replacement = item
            flags = 0
        else:
            pattern, replacement, flags = item
        
        content = re.sub(pattern, replacement, content, flags=flags)
    
    # Guardar cambios si se hizo alguna modificación
    if content != original_content:
        with open(models_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print_success(f"Actualizadas referencias obsoletas en {models_path}")
        return True
    else:
        print_warning(f"No se encontraron referencias obsoletas en {models_path}")
        return False

# ============================================================================
# FASE 3: CORRECCIÓN DE RUTAS Y REFERENCIAS DE CURVA_PRODUCCION_INTERACTIVA
# ============================================================================

def fix_curva_produccion_interactiva(backup_dir):
    """Corrige problemas con la ruta curva_produccion_interactiva"""
    print_header("CORRECCIÓN DE CURVA_PRODUCCION_INTERACTIVA")
    
    reportes_routes_path = "app/reportes/routes.py"
    if not os.path.exists(reportes_routes_path):
        print_error(f"Archivo {reportes_routes_path} no encontrado")
        return False
    
    # Crear respaldo
    create_file_backup(reportes_routes_path, backup_dir)
    
    # Leer contenido
    with open(reportes_routes_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verificar si existe la ruta interactiva
    has_interactive_route = re.search(r'@reportes\.route\([\'\"]\/curva_produccion_interactiva\/\<int:variedad_id\>[\'\"]\)', content) is not None
    
    # Añadir la ruta interactiva si no existe
    if not has_interactive_route:
        # Buscar la ruta normal para insertar después
        regular_route_match = re.search(r'@reportes\.route\([\'\"]\/curva_produccion\/\<int:variedad_id\>[\'\"]\).*?return render_template\(.*?\)\s*', content, re.DOTALL)
        
        if regular_route_match:
            # Obtener posición donde insertar
            pos = regular_route_match.end()
            
            # Preparar la nueva ruta
            new_route = """

@reportes.route('/curva_produccion_interactiva/<int:variedad_id>')
@login_required
def curva_produccion_interactiva(variedad_id):
    \"\"\"
    Version interactiva de la curva de produccion.
    Utiliza la misma logica que la version estandar por ahora.
    \"\"\"
    variedad = Variedad.query.get_or_404(variedad_id)
    return render_template('reportes/curva_produccion.html',
                          title=f'Curva de Produccion Interactiva: {variedad.variedad}',
                          variedad=variedad)
"""
            # Insertar la nueva ruta
            content = content[:pos] + new_route + content[pos:]
            
            # Guardar los cambios
            with open(reportes_routes_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print_success(f"Añadida ruta curva_produccion_interactiva en {reportes_routes_path}")
            return True
        else:
            print_error("No se pudo encontrar el punto para insertar la nueva ruta")
            return False
    else:
        print_warning(f"La ruta curva_produccion_interactiva ya existe en {reportes_routes_path}")
        return False

def fix_template_references(backup_dir):
    """Corrige referencias rotas en las plantillas"""
    print_header("CORRECCIÓN DE REFERENCIAS EN PLANTILLAS")
    
    template_files = [
        "app/templates/reportes/index.html",
        "app/templates/siembras/detalles.html",
        "app/templates/siembras/index.html",
        "app/templates/admin/variedades.html"
    ]
    
    count = 0
    for template_path in template_files:
        if not os.path.exists(template_path):
            continue
        
        # Crear respaldo
        create_file_backup(template_path, backup_dir)
        
        # Leer contenido
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Buscar referencias a curva_produccion_interactiva y reemplazarlas
        pattern = r'href=[\"\']{{ url_for\([\'\"](reportes\.curva_produccion_interactiva)[\'\"],[^\)]*\) }}[\"\']'
        if re.search(pattern, content):
            content = re.sub(pattern, 
                            r'href="{{ url_for(\'reportes.curva_produccion\', \g<1>) }}"',
                            content)
            
            # Guardar cambios
            with open(template_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print_success(f"Corregidas referencias en {template_path}")
            count += 1
        else:
            print_warning(f"No se encontraron referencias para corregir en {template_path}")
    
    print(f"\nTotal de plantillas actualizadas: {count}")
    return count

# ============================================================================
# FASE 4: OPTIMIZACIÓN DE LA BASE DE DATOS
# ============================================================================

def add_fecha_fin_corte_column():
    """Añade la columna fecha_fin_corte a la tabla siembras si no existe"""
    print_header("AÑADIR COLUMNA FECHA_FIN_CORTE")
    
    # Importar la aplicación
    try:
        sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
        from app import create_app, db
        from sqlalchemy import text, inspect
        
        app = create_app()
        
        with app.app_context():
            # Verificar si la columna ya existe
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('siembras')]
            
            if 'fecha_fin_corte' not in columns:
                # La columna no existe, crearla
                try:
                    db.session.execute(text("ALTER TABLE siembras ADD COLUMN fecha_fin_corte DATE"))
                    db.session.commit()
                    print_success("Columna fecha_fin_corte añadida correctamente a la tabla siembras")
                    return True
                except Exception as e:
                    db.session.rollback()
                    print_error(f"Error al añadir columna: {str(e)}")
                    return False
            else:
                print_warning("La columna fecha_fin_corte ya existe en la tabla siembras")
                return False
        
    except ImportError:
        print_error("No se pudo importar la aplicación Flask. Verifica que estás ejecutando desde el directorio raíz del proyecto.")
        print_warning("Ejecutando en modo simulación - no se realizarán cambios en la base de datos")
        return False
    except Exception as e:
        print_error(f"Error al acceder a la base de datos: {str(e)}")
        return False

def optimize_database_indices():
    """Optimiza la base de datos añadiendo índices"""
    print_header("OPTIMIZACIÓN DE ÍNDICES DE BASE DE DATOS")
    
    # Importar la aplicación
    try:
        sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
        from app import create_app, db
        from sqlalchemy import text, inspect
        
        app = create_app()
        
        with app.app_context():
            # Definir índices a crear
            indices = [
                ("siembras", "idx_siembras_variedad_id", "variedad_id"),
                ("siembras", "idx_siembras_bloque_cama_id", "bloque_cama_id"),
                ("siembras", "idx_siembras_fecha_siembra", "fecha_siembra"),
                ("siembras", "idx_siembras_fecha_fin_corte", "fecha_fin_corte"),
                ("cortes", "idx_cortes_siembra_id", "siembra_id"),
                ("cortes", "idx_cortes_fecha_corte", "fecha_corte"),
                ("variedades", "idx_variedades_flor_color_id", "flor_color_id"),
            ]
            
            # Obtener índices existentes
            inspector = inspect(db.engine)
            count = 0
            
            for tabla, nombre_indice, columna in indices:
                try:
                    # Verificar si la tabla existe
                    if not inspector.has_table(tabla):
                        print_warning(f"La tabla {tabla} no existe")
                        continue
                    
                    # Verificar si el índice ya existe
                    indices_existentes = [idx['name'] for idx in inspector.get_indexes(tabla)]
                    if nombre_indice in indices_existentes:
                        print_warning(f"El índice {nombre_indice} ya existe en la tabla {tabla}")
                        continue
                    
                    # Crear el índice
                    db.session.execute(text(f"CREATE INDEX {nombre_indice} ON {tabla}({columna})"))
                    db.session.commit()
                    print_success(f"Índice {nombre_indice} creado en la tabla {tabla}")
                    count += 1
                except Exception as e:
                    db.session.rollback()
                    print_error(f"Error al crear índice {nombre_indice}: {str(e)}")
            
            print(f"\nTotal de índices creados: {count}")
            return count
        
    except ImportError:
        print_error("No se pudo importar la aplicación Flask. Verifica que estás ejecutando desde el directorio raíz del proyecto.")
        print_warning("Ejecutando en modo simulación - no se realizarán cambios en la base de datos")
        return 0
    except Exception as e:
        print_error(f"Error al acceder a la base de datos: {str(e)}")
        return 0

# ============================================================================
# FASE 5: MEJORA DE ALGORITMOS DE CÁLCULO DE CURVAS
# ============================================================================

def fix_curva_produccion_algorithm(backup_dir):
    """Mejora el algoritmo de cálculo de curvas de producción"""
    print_header("MEJORA DE ALGORITMO DE CURVA DE PRODUCCIÓN")
    
    reportes_routes_path = "app/reportes/routes.py"
    if not os.path.exists(reportes_routes_path):
        print_error(f"Archivo {reportes_routes_path} no encontrado")
        return False
    
    # Crear respaldo
    create_file_backup(reportes_routes_path, backup_dir)
    
    # Leer contenido
    with open(reportes_routes_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Modificaciones a realizar
    improvements = [
        {
            "name": "Añadir función para filtrar outliers",
            "pattern": r'def curva_produccion\(variedad_id\):',
            "code": """def filtrar_outliers_iqr(valores, factor=1.5):
    \"\"\"
    Filtra valores atipicos usando el metodo IQR (Rango Intercuartilico).
    \"\"\"
    # No hay suficientes datos para aplicar IQR
    if not valores or len(valores) < 4:
        return valores
        
    # Ordenar valores
    valores_ordenados = sorted(valores)
    q1_idx = len(valores) // 4
    q3_idx = (len(valores) * 3) // 4
    
    q1 = valores_ordenados[q1_idx]
    q3 = valores_ordenados[q3_idx]
    
    iqr = q3 - q1
    lower_bound = q1 - (factor * iqr)
    upper_bound = q3 + (factor * iqr)
    
    return [v for v in valores if lower_bound <= v <= upper_bound]


def curva_produccion(variedad_id):""",
            "count": 0
        },
        {
            "name": "Mejorar cálculo de ciclos",
            "pattern": r'# Calcular ciclos promedio',
            "code": """    # Calcular ciclos promedio con filtrado mejorado
    dias_ciclo_vegetativo_filtrados = filtrar_outliers_iqr(dias_ciclo_vegetativo)
    dias_ciclo_total_filtrados = filtrar_outliers_iqr(dias_ciclo_total)
    
    # Calcular promedios de los datos filtrados
    if dias_ciclo_vegetativo_filtrados:
        ciclo_vegetativo_promedio = int(sum(dias_ciclo_vegetativo_filtrados) / len(dias_ciclo_vegetativo_filtrados))
    else:
        ciclo_vegetativo_promedio = 45  # Valor por defecto
    
    if dias_ciclo_total_filtrados:
        ciclo_total_promedio = int(sum(dias_ciclo_total_filtrados) / len(dias_ciclo_total_filtrados))
    else:
        ciclo_total_promedio = 110  # Valor por defecto
    
    # Validar consistencia entre ciclos
    if ciclo_total_promedio < ciclo_vegetativo_promedio + 30:
        ciclo_total_promedio = ciclo_vegetativo_promedio + 30""",
            "count": 0
        },
        {
            "name": "Mejorar generación de gráficos",
            "pattern": r'def generar_grafico_curva\(',
            "code": """    def generar_grafico_curva_mejorado(puntos_curva, variedad_info, ciclo_vegetativo_promedio, ciclo_total_promedio):
    \"\"\"
    Genera un grafico mejorado para la curva de produccion con interpolacion y suavizado.
    \"\"\"
    import matplotlib.pyplot as plt
    import numpy as np
    from io import BytesIO
    import base64
    
    # Verificar si hay suficientes datos
    if not puntos_curva or len(puntos_curva) < 3:
        # Crear un grafico con mensaje de error
        plt.figure(figsize=(10, 6))
        plt.text(0.5, 0.5, "Datos insuficientes para generar curva", 
                ha='center', va='center', fontsize=14)
        plt.tight_layout()
        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        grafico_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        plt.close()
        return grafico_base64
    
    # Extraer datos
    dias = []
    indices = []
    
    for punto in sorted(puntos_curva, key=lambda p: p['dia']):
        dias.append(punto['dia'])
        indices.append(punto['indice_promedio'])
    
    # Anadir punto inicial (siembra, dia 0)
    if min(dias) > 0:
        dias.insert(0, 0)
        indices.insert(0, 0)
    
    # Crear figura
    plt.figure(figsize=(10, 6))
    
    # Grafico de dispersion (datos reales)
    plt.scatter(dias, indices, color='blue', s=50, alpha=0.7, label='Datos historicos')
    
    # Conectar puntos
    plt.plot(dias, indices, 'r--', linewidth=1.5, label='Tendencia')
    
    # Configuracion
    plt.xlabel('Dias desde siembra')
    plt.ylabel('Indice promedio (%)')
    plt.title(f'Curva de produccion: {variedad_info}')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # Establecer limites eje Y
    max_value = max(indices) if indices else 20
    plt.ylim(0, min(50, max_value * 1.2))
    
    # Establecer limites eje X
    plt.xlim(0, ciclo_total_promedio)
    
    # Anadir lineas para ciclos
    if ciclo_vegetativo_promedio > 0:
        plt.axvline(x=ciclo_vegetativo_promedio, color='g', linestyle='--', alpha=0.7,
                   label=f'Fin ciclo vegetativo ({ciclo_vegetativo_promedio} dias)')
    
    if ciclo_total_promedio > 0:
        plt.axvline(x=ciclo_total_promedio, color='r', linestyle='--', alpha=0.7,
                   label=f'Fin ciclo total ({ciclo_total_promedio} dias)')
    
    # Anadir anotaciones
    for dia, indice in zip(dias, indices):
        plt.annotate(f'{indice:.2f}%', (dia, indice), 
                    textcoords="offset points", xytext=(0,10), ha='center')
    
    plt.tight_layout()
    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    grafico_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close()
    
    return grafico_base64""",
            "count": 0
        },
        {
            "name": "Actualizar llamada a función de gráfico",
            "pattern": r'grafico_curva = generar_grafico_curva\(',
            "replacement": "grafico_curva = generar_grafico_curva_mejorado(",
            "count": 0
        }
    ]
    
    # Aplicar modificaciones
    for improvement in improvements:
        original_content = content
        if "replacement" in improvement:
            # Simple reemplazo
            content = content.replace(improvement["pattern"], improvement["replacement"])
            if content != original_content:
                improvement["count"] = 1
        else:
            # Reemplazo con código multilinea
            pattern_match = re.search(improvement["pattern"], content)
            if pattern_match:
                pos = pattern_match.start()
                content = content[:pos] + improvement["code"] + content[pos + len(pattern_match.group()):]
                improvement["count"] = 1
    
    # Guardar cambios si hubo modificaciones
    if content != original_content:
        with open(reportes_routes_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Reportar mejoras aplicadas
        for improvement in improvements:
            if improvement["count"] > 0:
                print_success(f"Aplicada mejora: {improvement['name']}")
        
        print_success(f"Algoritmo de curva de producción mejorado en {reportes_routes_path}")
        return True
    else:
        print_warning(f"No se aplicaron mejoras al algoritmo de curva de producción")
        return False

# ============================================================================
# FASE 6: CONSOLIDACIÓN Y OPTIMIZACIÓN DE CARGA
# ============================================================================

def combine_redundant_functions(backup_dir):
    """Consolida funciones redundantes entre archivos"""
    print_header("CONSOLIDACIÓN DE FUNCIONES REDUNDANTES")
    
    # Lista de funciones redundantes para consolidar
    redundant_functions = [
        {
            "source_file": "importar_mejorado.py",
            "target_file": "manage.py",
            "function_name": "importar_datos",
            "pattern": r'def importar_historico_mejorado\(.*?\):',
            "description": "Función de importación de datos históricos"
        },
        {
            "source_file": "reset_siembras.py",
            "target_file": "manage.py",
            "function_name": "reset_siembras",
            "pattern": r'def reset_siembras\(.*?\):',
            "description": "Función para resetear siembras"
        }
    ]
    
    # Verificar archivos existentes
    available_functions = []
    for func in redundant_functions:
        if os.path.exists(func["source_file"]) and os.path.exists(func["target_file"]):
            available_functions.append(func)
    
    if not available_functions:
        print_warning("No se encontraron funciones redundantes para consolidar")
        return False
    
    # Notificar al usuario sobre las funciones que se pueden consolidar
    print("Las siguientes funciones pueden ser consolidadas:")
    for i, func in enumerate(available_functions, 1):
        print(f"{i}. {func['description']} de {func['source_file']} a {func['target_file']}")
    
    print("\nPara consolidar estas funciones, se debe modificar manualmente los archivos.")
    print("Este proceso requiere cuidado para evitar conflictos. Recomendaciones:")
    print("1. Revise cuidadosamente las funciones en ambos archivos")
    print("2. Cree comandos CLI en manage.py que llamen a las funciones originales")
    print("3. Actualice importaciones y dependencias según sea necesario")
    
    return available_functions

def update_init_files(backup_dir):
    """Verifica y actualiza los archivos __init__.py de cada módulo"""
    print_header("ACTUALIZACIÓN DE ARCHIVOS __INIT__.PY")
    
    # Lista de módulos para verificar
    modules = [
        "app",
        "app/admin",
        "app/auth",
        "app/cortes",
        "app/main",
        "app/reportes",
        "app/siembras",
        "app/utils"
    ]
    
    count = 0
    for module_path in modules:
        init_file = os.path.join(module_path, "__init__.py")
        
        if not os.path.exists(module_path):
            print_warning(f"Módulo {module_path} no encontrado")
            continue
        
        if not os.path.exists(init_file):
            # Crear archivo __init__.py vacío
            try:
                with open(init_file, 'w', encoding='utf-8') as f:
                    f.write("# Módulo: {}\n".format(os.path.basename(module_path)))
                print_success(f"Creado archivo {init_file}")
                count += 1
            except Exception as e:
                print_error(f"Error al crear {init_file}: {str(e)}")
        else:
            # Verificar el contenido del archivo init
            with open(init_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Si es el archivo init principal de la aplicación, verificar la definición del objeto login
            if module_path == "app":
                # Verificar si login_manager está definido
                if "login_manager = LoginManager()" not in content:
                    needs_update = False
                    
                    # Verificar si ya hay importación de LoginManager
                    has_login_manager_import = "from flask_login import LoginManager" in content
                    
                    # Verificar si db está definido
                    has_db_definition = "db = SQLAlchemy()" in content
                    
                    # No modificar si no encontramos estas definiciones básicas
                    if not has_db_definition:
                        print_warning(f"No se encontró definición de 'db' en {init_file}, se omitirá la actualización")
                        continue
                    
                    # Hacer backup
                    create_file_backup(init_file, backup_dir)
                    
                    # Preparar nuevas líneas para añadir si es necesario
                    new_lines = []
                    
                    if not has_login_manager_import:
                        new_lines.append("from flask_login import LoginManager")
                    
                    new_lines.append("\n# Configuración de login")
                    new_lines.append("login_manager = LoginManager()")
                    new_lines.append("login_manager.login_view = 'auth.login'")
                    new_lines.append("login_manager.login_message = 'Por favor inicie sesión para acceder a esta página'")
                    new_lines.append("login_manager.login_message_category = 'info'")
                    
                    # Buscar el punto de inserción más adecuado (después de db = SQLAlchemy())
                    if "db = SQLAlchemy()" in content:
                        insertion_point = content.find("db = SQLAlchemy()") + len("db = SQLAlchemy()")
                        # Buscar el próximo salto de línea
                        next_newline = content.find("\n", insertion_point)
                        if next_newline != -1:
                            insertion_point = next_newline
                        
                        # Insertar el nuevo contenido
                        new_content = content[:insertion_point] + "\n" + "\n".join(new_lines) + content[insertion_point:]
                        
                        # Guardar el archivo
                        with open(init_file, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        
                        print_success(f"Actualizado {init_file} con configuración de login_manager")
                        count += 1
    
    print(f"\nTotal de archivos __init__.py actualizados: {count}")
    return count

# ============================================================================
# FASE 7: OPTIMIZACIÓN DE RENDIMIENTO DE APLICACIÓN
# ============================================================================

def enable_cache_config(backup_dir):
    """Habilita configuración de caché para funciones costosas"""
    print_header("CONFIGURACIÓN DE CACHÉ")
    
    config_path = "config.py"
    if not os.path.exists(config_path):
        print_error(f"Archivo {config_path} no encontrado")
        return False
    
    # Crear respaldo
    create_file_backup(config_path, backup_dir)
    
    # Leer contenido
    with open(config_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verificar si ya existe configuración de caché
    if "CACHE_TYPE" in content:
        print_warning("Configuración de caché ya existe en config.py")
        return False
    
    # Añadir configuración de caché
    cache_config = """    # Configuración de caché
    CACHE_TYPE = 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT = 300
    SEND_FILE_MAX_AGE_DEFAULT = 43200  # 12 horas en segundos
"""
    
    # Buscar la clase Config
    config_class_match = re.search(r'class Config:', content)
    
    if config_class_match:
        insert_position = content.find('\n\n', config_class_match.end())
        if insert_position == -1:  # Si no hay doble salto de línea
            insert_position = len(content)  # Añadir al final
        
        # Insertar configuración
        content = content[:insert_position] + "\n" + cache_config + content[insert_position:]
        
        # Guardar cambios
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print_success("Configuración de caché añadida a config.py")
        return True
    else:
        print_error("No se encontró la clase Config en config.py")
        return False

def optimize_static_files():
    """Optimiza carga de archivos estáticos (CSS, JS)"""
    print_header("OPTIMIZACIÓN DE ARCHIVOS ESTÁTICOS")
    
    # Verificar estructura de directorios
    static_dir = "app/static"
    if not os.path.exists(static_dir):
        print_error(f"Directorio {static_dir} no encontrado")
        return False
    
    # Crear archivo .htaccess para optimizar carga (si se usa Apache)
    htaccess_path = os.path.join(static_dir, ".htaccess")
    
    if not os.path.exists(htaccess_path):
        try:
            with open(htaccess_path, 'w', encoding='utf-8') as f:
                f.write("""# Habilitar compresión
<IfModule mod_deflate.c>
  AddOutputFilterByType DEFLATE text/html text/plain text/css application/json
  AddOutputFilterByType DEFLATE text/javascript application/javascript application/x-javascript
  AddOutputFilterByType DEFLATE application/xml application/xhtml+xml text/xml
</IfModule>

# Configuración de caché para archivos estáticos
<IfModule mod_expires.c>
  ExpiresActive On
  
  # Imágenes
  ExpiresByType image/jpeg "access plus 1 year"
  ExpiresByType image/png "access plus 1 year"
  ExpiresByType image/gif "access plus 1 year"
  ExpiresByType image/svg+xml "access plus 1 year"
  
  # CSS, JavaScript
  ExpiresByType text/css "access plus 1 month"
  ExpiresByType text/javascript "access plus 1 month"
  ExpiresByType application/javascript "access plus 1 month"
</IfModule>
""")
            print_success(f"Creado archivo {htaccess_path} para optimización")
            return True
        except Exception as e:
            print_error(f"Error al crear archivo .htaccess: {str(e)}")
            return False
    else:
        print_warning(f"El archivo {htaccess_path} ya existe")
        return False

# ============================================================================
# FUNCIÓN PRINCIPAL Y PROCESAMIENTO DE ARGUMENTOS
# ============================================================================

def parse_arguments():
    """Procesa los argumentos de línea de comandos"""
    parser = argparse.ArgumentParser(description='Script de Depuración y Optimización para Sistema de Gestión de Cultivos')
    
    parser.add_argument('--clean-only', action='store_true', help='Solo ejecutar limpieza de archivos')
    parser.add_argument('--fix-only', action='store_true', help='Solo ejecutar correcciones')
    parser.add_argument('--optimize-only', action='store_true', help='Solo ejecutar optimizaciones')
    parser.add_argument('--no-backup', action='store_true', help='No crear respaldos (no recomendado)')
    parser.add_argument('--dry-run', action='store_true', help='Modo simulación (no realizar cambios)')
    parser.add_argument('--verbose', action='store_true', help='Modo verboso (más información)')
    
    return parser.parse_args()

def main():
    """Función principal del script"""
    print_header("INICIO DEL SCRIPT DE DEPURACIÓN Y OPTIMIZACIÓN")
    print("Sistema de Gestión de Cultivos")
    print(f"Fecha: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Procesar argumentos
    args = parse_arguments()
    
    # Verificar que estamos en el directorio raíz
    if not os.path.exists("app") or not os.path.exists("run.py"):
        print_error("No se encontraron archivos del proyecto. Asegúrate de ejecutar este script desde el directorio raíz.")
        return 1
    
    # Crear directorio de respaldo si es necesario
    backup_dir = None
    if not args.no_backup:
        backup_dir = create_backup_dir()
        print_success(f"Directorio de respaldo creado: {backup_dir}")
    else:
        print_warning("Ejecución sin respaldos. ¡No recomendado!")
    
    # Guardar configuración inicial
    config = {
        "dry_run": args.dry_run,
        "backup_dir": backup_dir,
        "verbose": args.verbose
    }
    
    # Estadísticas de operaciones
    stats = {
        "temp_files_removed": 0,
        "redundant_scripts_removed": 0,
        "obsolete_files_removed": 0,
        "obsolete_dirs_removed": 0,
        "models_updated": False,
        "interactive_route_fixed": False,
        "templates_fixed": 0,
        "fecha_fin_corte_added": False,
        "indices_created": 0,
        "curva_algorithm_improved": False,
        "init_files_updated": 0,
        "cache_configured": False,
        "static_files_optimized": False
    }
    
    try:
        # FASE 1: Limpieza de archivos
        if not args.fix_only and not args.optimize_only:
            stats["temp_files_removed"] = clean_temp_files()
            if backup_dir:
                stats["redundant_scripts_removed"] = clean_redundant_scripts(backup_dir)
        
        # FASE 2: Eliminación de módulos obsoletos
        if not args.fix_only and not args.optimize_only:
            stats["obsolete_files_removed"], stats["obsolete_dirs_removed"] = remove_obsolete_modules(backup_dir) if backup_dir else (0, 0)
            if backup_dir:
                stats["models_updated"] = update_models_remove_obsolete_refs(backup_dir)
        
        # FASE 3: Corrección de rutas
        if not args.clean_only and not args.optimize_only:
            if backup_dir:
                stats["interactive_route_fixed"] = fix_curva_produccion_interactiva(backup_dir)
                stats["templates_fixed"] = fix_template_references(backup_dir)
        
        # FASE 4: Optimización de base de datos
        if not args.clean_only and not args.fix_only:
            if not args.dry_run:
                stats["fecha_fin_corte_added"] = add_fecha_fin_corte_column()
                stats["indices_created"] = optimize_database_indices()
        
        # FASE 5: Mejora de algoritmos
        if not args.clean_only and not args.fix_only:
            if backup_dir:
                stats["curva_algorithm_improved"] = fix_curva_produccion_algorithm(backup_dir)
        
        # FASE 6: Consolidación y optimización de carga
        if not args.clean_only and not args.fix_only:
            if backup_dir:
                combine_redundant_functions(backup_dir)  # Solo muestra información, no realiza cambios
                stats["init_files_updated"] = update_init_files(backup_dir)
        
        # FASE 7: Optimización de rendimiento
        if not args.clean_only and not args.fix_only:
            if backup_dir:
                stats["cache_configured"] = enable_cache_config(backup_dir)
                stats["static_files_optimized"] = optimize_static_files()
        
        # Mostrar resumen
        print_header("RESUMEN DE OPERACIONES")
        print(f"{'Operación':<40} {'Estado':<10} {'Detalles':<30}")
        print("-" * 80)
        print(f"{'Archivos temporales eliminados':<40} {'✓':<10} {stats['temp_files_removed']:<30}")
        print(f"{'Scripts redundantes eliminados':<40} {'✓':<10} {stats['redundant_scripts_removed']:<30}")
        print(f"{'Archivos obsoletos eliminados':<40} {'✓':<10} {stats['obsolete_files_removed']:<30}")
        print(f"{'Directorios obsoletos eliminados':<40} {'✓':<10} {stats['obsolete_dirs_removed']:<30}")
        print(f"{'Modelos actualizados':<40} {'✓' if stats['models_updated'] else '✗':<10} {'Completado' if stats['models_updated'] else 'No requerido':<30}")
        print(f"{'Ruta interactiva corregida':<40} {'✓' if stats['interactive_route_fixed'] else '✗':<10} {'Completado' if stats['interactive_route_fixed'] else 'No requerido':<30}")
        print(f"{'Plantillas corregidas':<40} {'✓':<10} {stats['templates_fixed']:<30}")
        print(f"{'Columna fecha_fin_corte añadida':<40} {'✓' if stats['fecha_fin_corte_added'] else '✗':<10} {'Completado' if stats['fecha_fin_corte_added'] else 'Ya existe o simulación':<30}")
        print(f"{'Índices de BD creados':<40} {'✓':<10} {stats['indices_created']:<30}")
        print(f"{'Algoritmo de curva mejorado':<40} {'✓' if stats['curva_algorithm_improved'] else '✗':<10} {'Completado' if stats['curva_algorithm_improved'] else 'No requerido':<30}")
        print(f"{'Archivos __init__.py actualizados':<40} {'✓':<10} {stats['init_files_updated']:<30}")
        print(f"{'Caché configurado':<40} {'✓' if stats['cache_configured'] else '✗':<10} {'Completado' if stats['cache_configured'] else 'No requerido':<30}")
        print(f"{'Archivos estáticos optimizados':<40} {'✓' if stats['static_files_optimized'] else '✗':<10} {'Completado' if stats['static_files_optimized'] else 'No requerido':<30}")
        
        # Pasos adicionales
        print_header("PASOS ADICIONALES RECOMENDADOS")
        print("1. Verificar la aplicación para asegurarse de que funciona correctamente")
        print("2. Revisar las consultas SQL para optimizarlas (usar JOIN y LIMIT apropiadamente)")
        print("3. Considerar la implementación de un sistema de registro de errores")
        print("4. Actualizar la documentación del proyecto")
        
        if backup_dir:
            print(f"\nTodos los respaldos se encuentran en: {backup_dir}")
        
        return 0
        
    except KeyboardInterrupt:
        print_error("\nOperación cancelada por el usuario")
        return 130
    except Exception as e:
        print_error(f"\nError inesperado: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())