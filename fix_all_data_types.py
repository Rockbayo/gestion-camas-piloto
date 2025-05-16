"""
Script integral para corregir todos los problemas de tipos de datos y conversiones
en el sistema de gestión de camas piloto.

Este script:
1. Crea/corrige el archivo de utilidades para manejo de tipos de datos
2. Corrige los problemas de importación en main/routes.py
3. Revisa y corrige todos los archivos Python del proyecto para asegurar consistencia
4. Verifica y corrige valores en la base de datos
"""

import os
import sys
import re
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("data_types_fix_complete.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Directorio base de la aplicación
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def write_data_utils_file():
    """Crea o corrige el archivo data_utils.py con las funciones utilitarias"""
    data_utils_content = """
# -*- coding: utf-8 -*-
\"\"\"
Utilidades para manejo consistente de tipos de datos y cálculos numéricos
\"\"\"
from decimal import Decimal, getcontext, ROUND_HALF_UP
import numpy as np

# Configurar precisión para operaciones con Decimal
getcontext().prec = 10  # 10 dígitos de precisión
getcontext().rounding = ROUND_HALF_UP  # Redondeo estándar

def safe_decimal(value, default=Decimal('0.0')):
    \"\"\"Convierte un valor a Decimal de manera segura\"\"\"
    if value is None:
        return default
    try:
        # Si es string, limpiarlo primero
        if isinstance(value, str):
            value = value.strip().replace(',', '.')
        return Decimal(str(value))
    except (ValueError, TypeError, ArithmeticError):
        return default

def safe_int(value, default=0):
    \"\"\"Convierte un valor a entero de manera segura\"\"\"
    if value is None:
        return default
    try:
        # Para valores Decimal o float, redondear primero
        if isinstance(value, Decimal) or isinstance(value, float):
            return int(round(value))
        return int(value)
    except (ValueError, TypeError):
        return default

def safe_float(value, default=0.0):
    \"\"\"Convierte un valor a float de manera segura\"\"\"
    if value is None:
        return default
    try:
        # Si es string, limpiarlo primero
        if isinstance(value, str):
            value = value.strip().replace(',', '.')
        return float(value)
    except (ValueError, TypeError):
        return default

def calc_indice_aprovechamiento(tallos, plantas):
    \"\"\"
    Calcula el índice de aprovechamiento (tallos/plantas en porcentaje)
    con manejo de errores y tipos de datos.
    
    Args:
        tallos: Cantidad de tallos cosechados
        plantas: Cantidad de plantas sembradas
        
    Returns:
        Valor decimal del índice (porcentaje)
    \"\"\"
    tallos_dec = safe_decimal(tallos)
    plantas_dec = safe_decimal(plantas)
    
    if plantas_dec <= Decimal('0'):
        return Decimal('0')
        
    indice = (tallos_dec / plantas_dec) * Decimal('100')
    # Redondear a 2 decimales
    return indice.quantize(Decimal('0.01'))

def calc_plantas_totales(area, densidad):
    \"\"\"
    Calcula total de plantas según área y densidad
    con manejo consistente de tipos de datos.
    
    Args:
        area: Área en metros cuadrados
        densidad: Densidad en plantas por m²
        
    Returns:
        Cantidad de plantas (entero)
    \"\"\"
    area_dec = safe_decimal(area)
    densidad_dec = safe_decimal(densidad)
    
    plantas = area_dec * densidad_dec
    return safe_int(plantas)

def filtrar_outliers_iqr(valores, factor=1.5):
    \"\"\"
    Filtra valores atípicos usando el método del rango intercuartil (IQR)
    con manejo consistente de tipos de datos.
    
    Args:
        valores: Lista de valores numéricos
        factor: Factor de multiplicación para el IQR (default 1.5)
        
    Returns:
        Lista de valores filtrados
    \"\"\"
    if not valores or len(valores) < 5:  # Necesitamos suficientes datos
        return valores
    
    # Convertir todo a float para operaciones con numpy
    valores_float = [safe_float(v) for v in valores]
    valores_arr = np.array(valores_float)
    
    q1 = np.percentile(valores_arr, 25)
    q3 = np.percentile(valores_arr, 75)
    iqr = q3 - q1
    
    if iqr == 0:  # Si todos los valores son iguales
        return valores
        
    limite_inferior = q1 - (factor * iqr)
    limite_superior = q3 + (factor * iqr)
    
    # Filtrar valores dentro de los límites
    indices_validos = (valores_arr >= limite_inferior) & (valores_arr <= limite_superior)
    return [valores[i] for i, valid in enumerate(indices_validos) if valid]
"""
    
    try:
        # Asegurar que el directorio utils existe
        utils_dir = os.path.join(BASE_DIR, 'app', 'utils')
        os.makedirs(utils_dir, exist_ok=True)
        
        # Escribir el archivo data_utils.py
        file_path = os.path.join(utils_dir, 'data_utils.py')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(data_utils_content.strip())
        
        logger.info(f"Archivo data_utils.py creado/actualizado correctamente: {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error al crear/actualizar data_utils.py: {str(e)}")
        return False

def update_utils_init():
    """Actualiza el archivo __init__.py del módulo utils para incluir importaciones"""
    try:
        init_path = os.path.join(BASE_DIR, 'app', 'utils', '__init__.py')
        init_content = """# -*- coding: utf-8 -*-
# Importar utilidades para manejo de datos
from app.utils.data_utils import safe_decimal, safe_int, safe_float, calc_indice_aprovechamiento, calc_plantas_totales, filtrar_outliers_iqr
"""
        
        with open(init_path, 'w', encoding='utf-8') as f:
            f.write(init_content)
        
        logger.info(f"Archivo __init__.py actualizado correctamente: {init_path}")
        return True
    except Exception as e:
        logger.error(f"Error al actualizar __init__.py: {str(e)}")
        return False

def fix_main_routes():
    """Corrige el error específico en main/routes.py"""
    try:
        routes_file_path = os.path.join(BASE_DIR, 'app', 'main', 'routes.py')
        
        # Leer el archivo
        with open(routes_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 1. Añadir la importación necesaria si no existe
        if 'from app.utils.data_utils import' not in content:
            import_line = 'from app.utils.data_utils import safe_decimal, safe_int, safe_float, calc_indice_aprovechamiento, calc_plantas_totales\n'
            # Buscar un buen lugar para insertar
            import_section_end = content.find('from app import db')
            if import_section_end != -1:
                content = content[:import_section_end] + import_line + content[import_section_end:]
            else:
                # Si no encontramos un buen lugar, insertamos al principio
                content = import_line + content
        elif 'calc_indice_aprovechamiento' not in content:
            # La importación existe pero no incluye calc_indice_aprovechamiento
            content = content.replace(
                'from app.utils.data_utils import',
                'from app.utils.data_utils import calc_indice_aprovechamiento,'
            )
        
        # 2. Corregir la línea problemática del cálculo
        problematic_line = 'indice_aprovechamiento = round((total_tallos_global / total_plantas_global) * 100, 2)'
        if problematic_line in content:
            corrected_line = 'indice_aprovechamiento = float(calc_indice_aprovechamiento(total_tallos_global, total_plantas_global))'
            content = content.replace(problematic_line, corrected_line)
        else:
            # Buscar casos similares
            pattern = r'indice_aprovechamiento\s*=\s*round\(\(([^)]+)\s*/\s*([^)]+)\)\s*\*\s*100,\s*2\)'
            matches = re.findall(pattern, content)
            if matches:
                for tallos, plantas in matches:
                    old_calc = f"indice_aprovechamiento = round(({tallos} / {plantas}) * 100, 2)"
                    new_calc = f"indice_aprovechamiento = float(calc_indice_aprovechamiento({tallos}, {plantas}))"
                    content = content.replace(old_calc, new_calc)
        
        # 3. Guardar el archivo actualizado
        with open(routes_file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Archivo main/routes.py corregido: {routes_file_path}")
        return True
    except Exception as e:
        logger.error(f"Error al corregir main/routes.py: {str(e)}")
        return False

def fix_division_operations(file_path):
    """Corrige operaciones de división que podrían causar errores de tipo"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        changes_made = False
        
        # 1. Verificar si se necesitan importaciones
        uses_calc_indice = re.search(r'calc_indice_aprovechamiento\(', content)
        uses_calc_plantas = re.search(r'calc_plantas_totales\(', content)
        uses_safe_decimal = re.search(r'safe_decimal\(', content)
        uses_functions = any([uses_calc_indice, uses_calc_plantas, uses_safe_decimal])
        
        needs_import = uses_functions and 'from app.utils.data_utils import' not in content
        
        if needs_import:
            # Añadir importación
            import_line = 'from app.utils.data_utils import safe_decimal, safe_int, safe_float'
            if uses_calc_indice:
                import_line += ', calc_indice_aprovechamiento'
            if uses_calc_plantas:
                import_line += ', calc_plantas_totales'
            import_line += '\n'
            
            # Buscar lugar adecuado para la importación
            import_section = content.find('import')
            if import_section != -1:
                end_of_imports = re.search(r'(^|\n)\s*\n', content[import_section:])
                if end_of_imports:
                    position = import_section + end_of_imports.start() + 1
                    content = content[:position] + import_line + content[position:]
                else:
                    # No se encontró final claro de importaciones, añadir al principio
                    content = import_line + content
            else:
                # No hay importaciones, añadir al principio
                content = import_line + content
            
            changes_made = True
        
        # 2. Patrones de operaciones de división que podrían causar errores
        patterns = [
            # Patrón 1: Cálculo de índice de aprovechamiento
            (r'([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(?:round\s*\()?\s*\(\s*([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)\s*/\s*([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)\s*\)\s*\*\s*100(?:\s*,\s*[0-9]+\s*\))?',
             lambda m: f"{m.group(1)} = float(calc_indice_aprovechamiento({m.group(2)}, {m.group(3)}))"),
            
            # Patrón 2: Cálculo de plantas totales
            (r'([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(?:int\s*\()?\s*([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*\.area)\s*\*\s*([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*\.valor)(?:\s*\))?',
             lambda m: f"{m.group(1)} = calc_plantas_totales({m.group(2)}, {m.group(3)})")
        ]
        
        for pattern, replacement_func in patterns:
            for match in re.finditer(pattern, content):
                original = match.group(0)
                replacement = replacement_func(match)
                content = content.replace(original, replacement)
                changes_made = True
        
        # 3. Guardar el archivo si se hicieron cambios
        if changes_made:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Operaciones de división corregidas en: {file_path}")
        
        return changes_made
    except Exception as e:
        logger.error(f"Error al corregir operaciones de división en {file_path}: {str(e)}")
        return False

def fix_all_files():
    """Recorre todos los archivos Python del proyecto y corrige problemas de tipo"""
    try:
        app_dir = os.path.join(BASE_DIR, 'app')
        files_corrected = []
        
        for root, _, files in os.walk(app_dir):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    
                    # Excluir el archivo que acabamos de crear
                    if file == 'data_utils.py':
                        continue
                    
                    if fix_division_operations(file_path):
                        files_corrected.append(file_path)
        
        logger.info(f"Total de archivos corregidos: {len(files_corrected)}")
        if files_corrected:
            logger.info("Archivos corregidos:")
            for file in files_corrected:
                logger.info(f"  - {file}")
        
        return True
    except Exception as e:
        logger.error(f"Error al corregir todos los archivos: {str(e)}")
        return False

def create_app():
    """Crea una instancia de la aplicación Flask para usar su contexto"""
    try:
        from app import create_app as app_creator
        app = app_creator()
        return app
    except ImportError:
        logger.error("No se pudo importar la función create_app. Verificando estructura del proyecto.")
        return None

def fix_database_values(app):
    """Corrige valores en la base de datos para asegurar coherencia de tipos"""
    if not app:
        logger.warning("No se pudo crear la aplicación Flask, omitiendo corrección de base de datos.")
        return False
    
    try:
        with app.app_context():
            from app import db
            from app.models import Area, Densidad, Corte
            from decimal import Decimal
            
            # 1. Corregir valores de áreas a Decimal con 4 decimales
            areas = Area.query.all()
            areas_fixed = 0
            for area in areas:
                if area.area is not None:
                    old_value = area.area
                    # Convertir a Decimal con 4 decimales
                    try:
                        area.area = Decimal(str(area.area)).quantize(Decimal('0.0001'))
                        if area.area != old_value:
                            areas_fixed += 1
                    except Exception as e:
                        logger.warning(f"Error al convertir área {area.area_id}: {str(e)}")
            
            # 2. Corregir valores de densidades a Decimal con 4 decimales
            densidades = Densidad.query.all()
            densidades_fixed = 0
            for densidad in densidades:
                if densidad.valor is not None:
                    old_value = densidad.valor
                    try:
                        densidad.valor = Decimal(str(densidad.valor)).quantize(Decimal('0.0001'))
                        if densidad.valor != old_value:
                            densidades_fixed += 1
                    except Exception as e:
                        logger.warning(f"Error al convertir densidad {densidad.densidad_id}: {str(e)}")
            
            # 3. Corregir valores de tallos a enteros
            cortes = Corte.query.all()
            cortes_fixed = 0
            for corte in cortes:
                if corte.cantidad_tallos is not None:
                    old_value = corte.cantidad_tallos
                    try:
                        corte.cantidad_tallos = int(round(float(corte.cantidad_tallos)))
                        if corte.cantidad_tallos != old_value:
                            cortes_fixed += 1
                    except Exception as e:
                        logger.warning(f"Error al convertir tallos {corte.corte_id}: {str(e)}")
            
            # Guardar cambios
            if areas_fixed > 0 or densidades_fixed > 0 or cortes_fixed > 0:
                db.session.commit()
                logger.info(f"Valores corregidos en la base de datos: {areas_fixed} áreas, {densidades_fixed} densidades, {cortes_fixed} cortes")
                return True
            else:
                logger.info("No se encontraron valores que necesiten corrección en la base de datos")
                return True
    except Exception as e:
        logger.error(f"Error al corregir valores en la base de datos: {str(e)}")
        return False

def main():
    """Función principal que ejecuta todas las correcciones"""
    logger.info("=== Iniciando corrección integral de tipos de datos ===")
    
    # 1. Crear/actualizar archivo de utilidades
    logger.info("1. Creando/actualizando archivo de utilidades data_utils.py...")
    write_data_utils_file()
    
    # 2. Actualizar archivo __init__.py
    logger.info("2. Actualizando archivo __init__.py...")
    update_utils_init()
    
    # 3. Corregir error específico en main/routes.py
    logger.info("3. Corrigiendo error específico en main/routes.py...")
    fix_main_routes()
    
    # 4. Corregir todos los archivos del proyecto
    logger.info("4. Corrigiendo todos los archivos del proyecto...")
    fix_all_files()
    
    # 5. Corregir valores en la base de datos
    logger.info("5. Corrigiendo valores en la base de datos...")
    app = create_app()
    if app:
        fix_database_values(app)
    
    logger.info("=== Corrección integral completada ===")
    logger.info("Por favor, reinicia la aplicación para aplicar todos los cambios.")

if __name__ == "__main__":
    main()
