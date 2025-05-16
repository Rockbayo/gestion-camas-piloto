"""
Funciones para corregir errores específicos de tipos de datos en la aplicación
"""

def fix_dashboard_calculation_error():
    """
    Corrige el error específico de tipos en main/routes.py que produce:
    TypeError: unsupported operand type(s) for /: 'decimal.Decimal' and 'float'
    """
    import os
    
    # Obtener ruta al archivo routes.py
    routes_file_path = os.path.join('app', 'main', 'routes.py')
    
    # Leer el contenido actual
    with open(routes_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Buscar la línea problemática
    problematic_line = 'indice_aprovechamiento = round((total_tallos_global / total_plantas_global) * 100, 2)'
    
    # Reemplazar con la versión corregida usando nuestras funciones utilitarias
    corrected_line = 'indice_aprovechamiento = float(calc_indice_aprovechamiento(total_tallos_global, total_plantas_global))'
    
    # Aplicar la corrección
    if problematic_line in content:
        new_content = content.replace(problematic_line, corrected_line)
        
        # Guardar el archivo modificado
        with open(routes_file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return True, f"Corrección aplicada en {routes_file_path}"
    else:
        # Buscar líneas similares que puedan causar el mismo error
        similar_lines = []
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'total_tallos_global / total_plantas_global' in line:
                similar_lines.append((i+1, line))
        
        if similar_lines:
            # Reemplazar todas las líneas encontradas
            for _, line in similar_lines:
                corrected = line.replace(
                    'total_tallos_global / total_plantas_global', 
                    'float(safe_decimal(total_tallos_global) / safe_decimal(total_plantas_global))'
                )
                content = content.replace(line, corrected)
            
            # Guardar el archivo modificado
            with open(routes_file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True, f"Corrección aplicada en {len(similar_lines)} líneas en {routes_file_path}"
        
        return False, f"No se encontró la línea exacta en {routes_file_path}. Revisa manualmente el archivo."

def fix_all_division_errors():
    """
    Busca y corrige todos los posibles errores de división de tipos incompatibles
    """
    import os
    
    # Directorios a buscar
    directories = ['app/main', 'app/reportes', 'app/cortes', 'app/siembras']
    
    # Patrones de código que podrían causar el error
    patterns = [
        'total_tallos / total_plantas',
        'cantidad_tallos / plantas',
        '/ total_plantas',
        '/ plantas_',
        'tallos / area',
        'tallos_cortados / plantas_sembradas'
    ]
    
    fixes_applied = []
    
    for directory in directories:
        if not os.path.exists(directory):
            continue
            
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    
                    # Leer el contenido
                    with open(file_path, 'r', encoding='utf-8') as f:
                        try:
                            content = f.read()
                        except UnicodeDecodeError:
                            # Intentar con otra codificación
                            with open(file_path, 'r', encoding='latin-1') as f2:
                                content = f2.read()
                    
                    original_content = content
                    changes_made = False
                    
                    # Buscar líneas que contengan cálculos de división que podrían causar errores
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        for pattern in patterns:
                            if pattern in line and 'calc_indice_aprovechamiento' not in line and 'safe_decimal' not in line:
                                # Verificar si es una línea de cálculo
                                if ('=' in line or 'return' in line) and '/' in line:
                                    # Determinar la expresión a reemplazar
                                    parts = line.split('=', 1) if '=' in line else line.split('return', 1)
                                    if len(parts) > 1:
                                        expr = parts[1].strip()
                                        if '(' in expr and ')' in expr:
                                            # Extraer la expresión dentro de paréntesis
                                            start = expr.find('(')
                                            end = expr.rfind(')')
                                            if start < end:
                                                inner_expr = expr[start+1:end]
                                                if pattern in inner_expr and '*' in inner_expr and '100' in inner_expr:
                                                    # Este parece ser un cálculo de índice de aprovechamiento
                                                    # Extraer operandos: (a / b) * 100
                                                    division_parts = inner_expr.split('/')
                                                    if len(division_parts) == 2:
                                                        left_op = division_parts[0].strip()
                                                        right_op = division_parts[1].split('*')[0].strip()
                                                        
                                                        # Construir nuevo cálculo usando safe_decimal
                                                        new_expr = f"float(calc_indice_aprovechamiento({left_op}, {right_op}))"
                                                        
                                                        # Reemplazar en la línea original
                                                        new_line = line.replace(expr, expr.replace(inner_expr, new_expr))
                                                        lines[i] = new_line
                                                        changes_made = True
                                                        fixes_applied.append(f"Línea {i+1} en {file_path}")
                    
                    if changes_made:
                        # Guardar el archivo modificado
                        new_content = '\n'.join(lines)
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
    
    return fixes_applied

if __name__ == "__main__":
    # Corregir error específico en dashboard
    success, message = fix_dashboard_calculation_error()
    print(f"Resultado de corrección específica: {message}")
    
    # Corregir todos los errores potenciales de división
    fixes = fix_all_division_errors()
    if fixes:
        print(f"Correcciones aplicadas en {len(fixes)} lugares:")
        for fix in fixes:
            print(f"  - {fix}")
    else:
        print("No se encontraron problemas adicionales que corregir.")
        