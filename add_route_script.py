"""
Script para añadir la ruta curva_produccion_interactiva al archivo routes.py
Este script modificará directamente el archivo routes.py de forma segura
"""

import os
import re
from pathlib import Path

def add_interactive_curve_route():
    """Añade la ruta curva_produccion_interactiva al archivo routes.py"""
    
    # Ruta del archivo
    file_path = 'app/reportes/routes.py'
    
    # Verificar que existe el archivo
    if not os.path.exists(file_path):
        print(f"Error: No se encontró el archivo {file_path}")
        return False
    
    # Leer el contenido del archivo
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Verificar si la ruta ya existe
    if 'def curva_produccion_interactiva' in content:
        print("La ruta curva_produccion_interactiva ya existe en el archivo")
        return True
    
    # Nueva función a añadir
    new_route = """@reportes.route('/curva_produccion_interactiva/<int:variedad_id>')
@login_required
def curva_produccion_interactiva(variedad_id):
    \"\"\"
    Versión interactiva de la curva de producción que usa la misma plantilla
    que la versión estática pero es un punto de entrada separado para facilitar
    la implementación futura de funcionalidades interactivas.
    \"\"\"
    # Obtener la variedad solicitada
    variedad = Variedad.query.get_or_404(variedad_id)
    
    # Para esta implementación inicial, usamos la misma plantilla que la versión estática
    return render_template('reportes/curva_produccion.html',
                          title=f'Curva de Producción: {variedad.variedad}',
                          variedad=variedad,
                          puntos_curva=[],  # Sin puntos para evitar errores
                          grafico_curva=None,  # Sin gráfico para evitar errores  
                          datos_adicionales={
                              'total_siembras': 0,
                              'siembras_con_datos': 0,
                              'total_plantas': 0,
                              'total_tallos': 0,
                              'promedio_produccion': 0,
                              'ciclo_vegetativo': 0,
                              'ciclo_productivo': 0,
                              'ciclo_total': 0,
                              'max_ciclo_historico': 0
                          })"""

    # Buscar la posición ideal para insertar (después de la función curva_produccion)
    pattern = r'@reportes\.route\(\'/curva_produccion\/<int:variedad_id\>\'\)[\s\S]*?def curva_produccion[\s\S]*?return render_template[\s\S]*?\)'
    
    # Buscar la coincidencia
    match = re.search(pattern, content)
    
    if not match:
        print("No se pudo encontrar la función curva_produccion en el archivo")
        print("Intentando añadir la nueva ruta al final del archivo")
        
        # Añadir al final del archivo
        with open(file_path, 'a', encoding='utf-8') as file:
            file.write("\n\n" + new_route)
        
        print("Ruta añadida al final del archivo")
        return True
    
    # Posición donde termina la función curva_produccion
    end_pos = match.end()
    
    # Insertar la nueva función después de la función curva_produccion
    modified_content = content[:end_pos] + "\n\n" + new_route + content[end_pos:]
    
    # Guardar el archivo modificado
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(modified_content)
    
    print(f"Ruta curva_produccion_interactiva añadida correctamente a {file_path}")
    return True

if __name__ == "__main__":
    add_interactive_curve_route()