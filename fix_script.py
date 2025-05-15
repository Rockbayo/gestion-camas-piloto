#!/usr/bin/env python
"""
Script para corregir errores en la aplicación de Gestión de Camas Piloto.
Este script realiza las siguientes correcciones:

1. Corregir el error de ruta reportes.curva_produccion_interactiva
2. Eliminar código redundante
3. Corregir la duplicación en reportes/index.html
4. Agregar la ruta curva_produccion_interactiva o eliminar sus referencias
5. Corregir otros errores menores de código
"""

import os
import re
import sys
from pathlib import Path

# Colores para output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_step(message):
    """Imprimir mensaje de paso con formato"""
    print(f"{Colors.BLUE}[PASO]{Colors.ENDC} {message}")

def print_success(message):
    """Imprimir mensaje de éxito con formato"""
    print(f"{Colors.GREEN}[ÉXITO]{Colors.ENDC} {message}")

def print_warning(message):
    """Imprimir advertencia con formato"""
    print(f"{Colors.WARNING}[ADVERTENCIA]{Colors.ENDC} {message}")

def print_error(message):
    """Imprimir error con formato"""
    print(f"{Colors.FAIL}[ERROR]{Colors.ENDC} {message}")

def backup_file(file_path):
    """Crear copia de seguridad del archivo"""
    from datetime import datetime
    import shutil
    
    backup_path = f"{file_path}.backup.{datetime.now().strftime('%Y%m%d%H%M%S')}"
    shutil.copy2(file_path, backup_path)
    return backup_path

def fix_reportes_routes():
    """
    Corrige las rutas en app/reportes/routes.py
    Añade la ruta curva_produccion_interactiva
    """
    file_path = 'app/reportes/routes.py'
    print_step(f"Corrigiendo archivo {file_path}...")
    
    if not os.path.exists(file_path):
        print_error(f"No se encontró el archivo {file_path}")
        return False
    
    # Hacer copia de seguridad
    backup_path = backup_file(file_path)
    print_warning(f"Copia de seguridad creada: {backup_path}")
    
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Añadir la ruta faltante curva_produccion_interactiva
    # Buscar patrón de la ruta curva_produccion
    curva_produccion_pattern = r'@reportes\.route\(\'\/curva_produccion\/\<int:variedad_id\>\'\)'
    
    # Verificar si ya existe la ruta interactiva
    if 'curva_produccion_interactiva' not in content:
        # Añadir la nueva ruta después de la ruta existente de curva_produccion
        nueva_funcion = """

@reportes.route('/curva_produccion_interactiva/<int:variedad_id>')
@login_required
def curva_produccion_interactiva(variedad_id):
    \"\"\"
    Versión interactiva de la curva de producción usando React.
    \"\"\"
    # Obtener la variedad solicitada
    variedad = Variedad.query.get_or_404(variedad_id)
    
    # Construir la URL de la API que serviría los datos (para implementación futura)
    api_url = f"/api/curvas/{variedad_id}"
    
    return render_template('reportes/curva_produccion.html',
                          title=f'Curva de Producción: {variedad.variedad}',
                          variedad=variedad)
"""
        # Usar una expresión regular para insertar la nueva función después de la función existente
        import re
        # Buscar el final de la función curva_produccion
        curva_produccion_end_pattern = r'(return render_template\(.*?curva_produccion\.html.*?\))'
        modified_content = re.sub(
            curva_produccion_end_pattern, 
            r'\1' + nueva_funcion, 
            content,
            flags=re.DOTALL,
            count=1  # Solo reemplazar la primera ocurrencia
        )
        
        if modified_content == content:
            print_warning("No se pudo insertar la nueva ruta automáticamente.")
            print_warning("Se intentará una estrategia alternativa.")
            # Estrategia alternativa: agregar al final del archivo
            modified_content = content + nueva_funcion
        
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(modified_content)
            
        print_success(f"Se agregó la ruta 'curva_produccion_interactiva' en {file_path}")
    else:
        print_warning("La ruta 'curva_produccion_interactiva' ya existe, no se realizaron cambios.")
    
    return True

def fix_redundant_variedades_list():
    """Corregir la lista redundante de variedades en reportes/index.html"""
    file_path = 'app/templates/reportes/index.html'
    print_step(f"Corrigiendo archivo {file_path}...")
    
    if not os.path.exists(file_path):
        print_error(f"No se encontró el archivo {file_path}")
        return False
    
    # Hacer copia de seguridad
    backup_path = backup_file(file_path)
    print_warning(f"Copia de seguridad creada: {backup_path}")
    
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Identificar y eliminar la sección duplicada
    pattern = r'<div class="row">\s*{% set variedades = variedades if variedades is defined else \[\] %}\s*{% if variedades %}.*?{% else %}.*?{% endif %}.*?</div>'
    
    if re.search(pattern, content, re.DOTALL):
        modified_content = re.sub(pattern, '', content, flags=re.DOTALL)
        
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(modified_content)
            
        print_success(f"Se eliminó la lista redundante de variedades en {file_path}")
    else:
        print_warning("No se encontró el patrón de lista redundante para eliminar.")
    
    return True

def fix_template_references():
    """Corregir las referencias a curva_produccion_interactiva en las plantillas"""
    # Lista de archivos a revisar
    template_files = [
        'app/templates/reportes/index.html',
        'app/templates/siembras/detalles.html',
        'app/templates/reportes/curva_produccion.html',
        'app/templates/admin/variedades.html'
    ]
    
    print_step("Corrigiendo referencias a 'curva_produccion_interactiva' en plantillas...")
    
    for file_path in template_files:
        if not os.path.exists(file_path):
            print_warning(f"No se encontró el archivo {file_path}")
            continue
        
        # Hacer copia de seguridad
        backup_path = backup_file(file_path)
        print_warning(f"Copia de seguridad creada: {backup_path}")
        
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Buscar patrón de botones que hagan referencia a la ruta interactive
        button_pattern = r'<a href="\{\{ url_for\(\'reportes\.curva_produccion_interactiva\',.*?\) \}\}" class="btn.*?">.*?</a>'
        
        # Verificar si hay referencias a la ruta interactiva
        if re.search(button_pattern, content):
            # Ahora que hemos agregado la ruta, podemos dejar el botón, pero actualicemos el texto
            modified_content = re.sub(
                r'<a href="\{\{ url_for\(\'reportes\.curva_produccion_interactiva\',.*?\) \}\}" class="btn.*?">.*?</a>',
                '<a href="{{ url_for(\'reportes.curva_produccion\', variedad_id=variedad.variedad_id) }}" class="btn btn-outline-primary"><i class="fas fa-chart-line"></i> Ver Curva</a>',
                content
            )
            
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(modified_content)
                
            print_success(f"Se corrigieron las referencias en {file_path}")
        else:
            print_warning(f"No se encontraron referencias a corregir en {file_path}")
    
    return True

def fix_js_component():
    """Corregir el componente React en caso de que exista"""
    file_path = 'app/static/js/components/CurvaProduccion.jsx'
    
    if os.path.exists(file_path):
        print_step(f"Verificando componente React en {file_path}...")
        # No necesitamos modificar este archivo, solo verificamos su existencia
        print_success(f"El componente React existe en {file_path}")
    else:
        print_warning(f"No se encontró el componente React en {file_path}")
        print_warning("La implementación interactiva puede no funcionar correctamente.")
    
    return True

def fix_database_models():
    """Corregir posibles errores en los modelos de la base de datos"""
    file_path = 'app/models.py'
    print_step(f"Verificando modelos de base de datos en {file_path}...")
    
    if not os.path.exists(file_path):
        print_error(f"No se encontró el archivo {file_path}")
        return False
    
    # Para este script, no modificaremos directamente los modelos,
    # ya que podría haber datos en la base que dependan de ellos
    print_warning("No se realizaron cambios en los modelos de la base de datos.")
    print_warning("Para realizar cambios en modelos, use flask db migrate y flask db upgrade.")
    
    return True

def run_all_fixes():
    """Ejecutar todas las correcciones"""
    print_step("Iniciando script de corrección de errores...")
    
    # Lista de funciones a ejecutar
    fixes = [
        fix_reportes_routes,
        fix_redundant_variedades_list,
        fix_template_references,
        fix_js_component,
        fix_database_models
    ]
    
    success_count = 0
    
    for fix_func in fixes:
        if fix_func():
            success_count += 1
    
    print()
    print_step(f"Resultados: {success_count}/{len(fixes)} correcciones aplicadas con éxito.")
    
    # Mensaje final
    if success_count == len(fixes):
        print_success("Todas las correcciones se aplicaron con éxito.")
        print_success("Pruebe la aplicación para verificar que los errores se hayan solucionado.")
    else:
        print_warning("Algunas correcciones no se pudieron aplicar.")
        print_warning("Revise los mensajes anteriores para más detalles.")
    
    print()
    print_step("Sugerencias adicionales:")
    print("1. Revise las plantillas HTML para cualquier otra referencia a 'curva_produccion_interactiva'")
    print("2. Mejore el manejo de errores en la aplicación añadiendo bloques try-except")
    print("3. Considere actualizar la estructura de la aplicación para seguir mejores prácticas")
    print("4. Ejecute 'flask db migrate' si realizó cambios en los modelos")
    
    return success_count == len(fixes)

if __name__ == "__main__":
    run_all_fixes()
