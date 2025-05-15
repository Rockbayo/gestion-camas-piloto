#!/usr/bin/env python3
"""
Script para aplicar mejoras al algoritmo de generación de curvas de producción.
Este script modifica el archivo routes.py para implementar todas las mejoras solicitadas.

Autor: Claude
Fecha: 14 de mayo de 2025
"""

import os
import sys
import re
import shutil
from datetime import datetime

# Constantes
NUEVA_FUNCION = '''def generar_grafico_curva_mejorado(puntos_curva, variedad_info, ciclo_vegetativo_promedio, ciclo_total_promedio):
    """
    Genera un gráfico mejorado para la curva de producción con interpolación y suavizado.
    """
    import matplotlib.pyplot as plt
    import numpy as np
    from scipy.interpolate import make_interp_spline, splrep, splev
    from io import BytesIO
    import base64
    
    # 1. PREPROCESAMIENTO DE DATOS
    # Verifica que haya suficientes datos
    if not puntos_curva or len(puntos_curva) < 3:
        # Crear un gráfico con mensaje de error si no hay suficientes datos
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
    
    # Extraer datos y ordenarlos
    dias = []
    indices = []
    
    for punto in sorted(puntos_curva, key=lambda p: p['dia']):
        dias.append(punto['dia'])
        indices.append(punto['indice_promedio'])
    
    # 2. AÑADIR PUNTOS SINTÉTICOS para mejorar la curva
    # Punto inicial (siembra, día 0)
    if min(dias) > 0:
        dias.insert(0, 0)
        indices.insert(0, 0)
    
    # Punto para el ciclo vegetativo (si no hay datos cercanos)
    if ciclo_vegetativo_promedio > 0:
        # Verificar si ya hay un punto cercano
        tiene_punto_cercano = any(abs(d - ciclo_vegetativo_promedio) < 5 for d in dias)
        if not tiene_punto_cercano:
            # Calcular un valor razonable para el inicio de producción (5-10% del promedio)
            promedio_indices = sum(indices) / len(indices) if indices else 0
            valor_inicio = max(0.5, promedio_indices * 0.08)  # 8% del promedio o 0.5 mínimo
            
            # Encontrar dónde insertar
            pos = 0
            while pos < len(dias) and dias[pos] < ciclo_vegetativo_promedio:
                pos += 1
            
            dias.insert(pos, ciclo_vegetativo_promedio)
            indices.insert(pos, valor_inicio)
    
    # Reordenar datos después de añadir puntos
    puntos_ordenados = sorted(zip(dias, indices))
    dias = [p[0] for p in puntos_ordenados]
    indices = [p[1] for p in puntos_ordenados]
    
    # 3. CREAR FIGURA
    plt.figure(figsize=(10, 6))
    
    # Gráfico de dispersión (puntos reales)
    plt.scatter(dias, indices, color='blue', s=50, alpha=0.7, label='Datos históricos')
    
    # 4. GENERAR CURVA SUAVIZADA
    # Solo intentar curva suavizada si hay suficientes puntos
    if len(dias) >= 4:
        try:
            # Crear una malla más densa para el suavizado
            dias_suavizados = np.linspace(0, ciclo_total_promedio, 100)
            
            # Usar splines con suavizado controlado
            # El parámetro s controla el suavizado (mayor s = más suavizado)
            tck = splrep(dias, indices, s=len(dias)/2)
            indices_suavizados = splev(dias_suavizados, tck)
            
            # Asegurarse de que los valores tengan sentido (no negativos, sin picos extremos)
            indices_suavizados = np.maximum(indices_suavizados, 0)  # No valores negativos
            
            # Limitar picos extremos
            max_indice = max(indices) * 1.2  # Permitir hasta 20% más que el máximo observado
            indices_suavizados = np.minimum(indices_suavizados, max_indice)
            
            # Curva suavizada
            plt.plot(dias_suavizados, indices_suavizados, 'r--', 
                    linewidth=2, label='Tendencia (suavizado natural)')
        except Exception as e:
            print(f"Error al generar curva suavizada: {e}")
            # Si falla el suavizado, conectar los puntos con líneas simples
            plt.plot(dias, indices, 'r--', linewidth=1.5, 
                   label='Tendencia (interpolación lineal)')
    
    # 5. CONFIGURACIÓN DEL GRÁFICO
    plt.xlabel('Días desde siembra')
    plt.ylabel('Índice promedio (%)')
    plt.title(f'Curva de producción: {variedad_info}')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # Establecer límites eje Y
    max_value = max(indices) if indices else 20
    plt.ylim(0, min(50, max_value * 1.2))  # Limitar a 50% o 1.2 veces el máximo
    
    # Establecer límites eje X - todo el ciclo
    plt.xlim(0, ciclo_total_promedio)
    
    # 6. AÑADIR LÍNEAS VERTICALES para mostrar los ciclos
    if ciclo_vegetativo_promedio > 0:
        plt.axvline(x=ciclo_vegetativo_promedio, color='g', linestyle='--', alpha=0.7,
                   label=f'Fin ciclo vegetativo ({ciclo_vegetativo_promedio} días)')
    
    if ciclo_total_promedio > 0:
        plt.axvline(x=ciclo_total_promedio, color='r', linestyle='--', alpha=0.7,
                   label=f'Fin ciclo total ({ciclo_total_promedio} días)')
    
    # 7. AÑADIR ANOTACIONES
    for dia, indice in zip(dias, indices):
        plt.annotate(f'{indice:.2f}%', (dia, indice), 
                    textcoords="offset points", xytext=(0,10), ha='center')
    
    # 8. AÑADIR NOTA EXPLICATIVA
    plt.figtext(0.5, 0.01, 
               "Nota: La línea punteada roja representa la tendencia de producción ajustada.", 
               ha='center', fontsize=9)
    
    # 9. GUARDAR GRÁFICO
    plt.tight_layout(rect=[0, 0.03, 1, 0.97])  # Dejar espacio para la nota
    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=100)
    buffer.seek(0)
    grafico_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close()
    
    return grafico_base64'''

# Funciones auxiliares
def color_text(text, color_code):
    """Colorea texto para terminal"""
    return f"\033[{color_code}m{text}\033[0m"

def print_header(text):
    """Imprime un encabezado en la terminal"""
    print("\n" + color_text(text, "1;36"))  # Cyan bold

def print_success(text):
    """Imprime un mensaje de éxito"""
    print(color_text("✓ " + text, "32"))  # Green

def print_warning(text):
    """Imprime una advertencia"""
    print(color_text("! " + text, "33"))  # Yellow

def print_error(text):
    """Imprime un error"""
    print(color_text("✗ " + text, "31"))  # Red

def crear_backup(filepath):
    """Crea una copia de seguridad del archivo"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    backup_path = f"{filepath}.backup.{timestamp}"
    shutil.copy2(filepath, backup_path)
    return backup_path

def encontrar_archivo(nombre, directorio="."):
    """Encuentra un archivo en el directorio y sus subdirectorios"""
    for root, _, files in os.walk(directorio):
        if nombre in files:
            return os.path.join(root, nombre)
    return None

def validar_archivo(filepath):
    """Valida que el archivo sea el correcto (contiene la función buscada)"""
    with open(filepath, 'r', encoding='utf-8') as f:
        contenido = f.read()
        return "@reportes.route('/curva_produccion/<int:variedad_id>')" in contenido

def modificar_archivo(filepath):
    """Aplica todas las modificaciones al archivo"""
    with open(filepath, 'r', encoding='utf-8') as f:
        contenido_original = f.read()
    
    contenido = contenido_original
    cambios = []
    
    # 1. Añadir o reemplazar función generar_grafico_curva_mejorado
    if re.search(r'def generar_grafico_curva_mejorado\(.*?\):', contenido):
        # Reemplazar la función existente
        patron = re.compile(r'def generar_grafico_curva_mejorado\(.*?return grafico_base64', re.DOTALL)
        contenido = re.sub(patron, NUEVA_FUNCION, contenido)
        cambios.append("Reemplazada función generar_grafico_curva_mejorado existente")
    else:
        # Añadir la función al final del archivo
        contenido += "\n\n" + NUEVA_FUNCION
        cambios.append("Añadida nueva función generar_grafico_curva_mejorado")
    
    # 2. Añadir inicialización temprana de variables
    estadisticas_match = re.search(r'# Estadísticas adicionales\s+total_plantas = 0\s+total_tallos = 0', contenido)
    if estadisticas_match:
        indice = estadisticas_match.end()
        inicializacion = '''

    # Inicialización temprana de variables
    ciclo_vegetativo_promedio = 45  # Valor predeterminado
    ciclo_productivo_promedio = 60  # Valor predeterminado
    ciclo_total_promedio = 120      # Valor predeterminado'''
        
        if "# Inicialización temprana de variables" not in contenido:
            contenido = contenido[:indice] + inicializacion + contenido[indice:]
            cambios.append("Añadida inicialización temprana de variables")
    else:
        print_warning("No se encontró el punto para añadir inicialización de variables")
    
    # 3. Modificar procesamiento de cortes
    procesamiento_match = re.search(r'# Procesamos cada corte', contenido)
    if procesamiento_match:
        # Añadir lista para recopilar todos los cortes
        indice = procesamiento_match.start()
        lista_cortes = '''    # Lista para recopilar todos los cortes inicialmente, sin filtrado
    cortes_todas_fechas = []
    
'''
        if "cortes_todas_fechas = []" not in contenido:
            contenido = contenido[:indice] + lista_cortes + contenido[indice:]
            cambios.append("Añadida lista para recopilar todos los cortes sin filtrado")
        
        # Modificar procesamiento dentro del bucle
        patron_proceso = re.compile(r'dias_desde_siembra = \(corte\.fecha_corte - siembra\.fecha_siembra\)\.days.*?total_tallos \+= corte\.cantidad_tallos', re.DOTALL)
        nuevo_proceso = '''            # Calcular días desde siembra
            dias_desde_siembra = (corte.fecha_corte - siembra.fecha_siembra).days
            
            # Calcular índice para este corte
            indice = (corte.cantidad_tallos / plantas_siembra) * 100
            
            # Guardar todos los cortes inicialmente sin filtrar por ciclo
            cortes_todas_fechas.append({
                'dias_desde_siembra': dias_desde_siembra,
                'indice': indice,
                'fecha_corte': corte.fecha_corte
            })
            
            total_tallos += corte.cantidad_tallos'''
        
        if re.search(patron_proceso, contenido):
            contenido = re.sub(patron_proceso, nuevo_proceso, contenido)
            cambios.append("Modificado procesamiento de cortes para no filtrar prematuramente")
    else:
        print_warning("No se encontró el punto para modificar procesamiento de cortes")
    
    # 4. Añadir análisis preliminar
    ciclos_match = re.search(r'# Calcular ciclos promedio con filtrado de valores atípicos', contenido)
    if ciclos_match:
        indice = ciclos_match.start()
        analisis_preliminar = '''    # Añadir paso de análisis preliminar
    if cortes_todas_fechas:
        min_dias = min(c['dias_desde_siembra'] for c in cortes_todas_fechas)
        max_dias = max(c['dias_desde_siembra'] for c in cortes_todas_fechas)
        
        # Ajustar ciclo total si es necesario
        if max_dias > 0 and (ciclo_total_promedio < max_dias * 0.8 or ciclo_total_promedio > max_dias * 2.0):
            ciclo_total_promedio = min(180, int(max_dias * 1.1))
            
        # Ajustar ciclo vegetativo si no hay datos al inicio
        if min_dias > 20 and ciclo_vegetativo_promedio < min_dias * 0.8:
            ciclo_vegetativo_promedio = max(30, int(min_dias * 0.9))
    
    # Ahora agrupamos los cortes por día, usando posiblemente un límite adaptativo
    for corte in cortes_todas_fechas:
        dias_desde_siembra = corte['dias_desde_siembra']
        indice = corte['indice']
        
        # Usar un límite adaptativo basado en el ciclo total calculado
        limite_dias = min(ciclo_total_promedio * 1.2, 180)  
        if dias_desde_siembra > limite_dias:
            continue
        
        # Agrupamos por día desde siembra
        if dias_desde_siembra not in datos_curva:
            datos_curva[dias_desde_siembra] = []
            
        datos_curva[dias_desde_siembra].append(indice)

'''
        
        if "# Añadir paso de análisis preliminar" not in contenido:
            contenido = contenido[:indice] + analisis_preliminar + contenido[indice:]
            cambios.append("Añadido análisis preliminar para ajustar ciclos")
    else:
        print_warning("No se encontró el punto para añadir análisis preliminar")
    
    # 5. Agregar verificación para fase vegetativa
    promedios_match = re.search(r'# Calculamos los promedios para cada día', contenido)
    if promedios_match:
        indice = promedios_match.start()
        verificacion_vegetativa = '''    # Verificar si hay datos para la fase vegetativa
    tiene_datos_vegetativos = any(dia < ciclo_vegetativo_promedio for dia in datos_curva.keys())

    if not tiene_datos_vegetativos:
        # Añadir punto en día 0 (siembra)
        datos_curva[0] = []
        # Añadir un punto en medio del ciclo vegetativo
        punto_medio = ciclo_vegetativo_promedio // 2
        if punto_medio > 0:
            datos_curva[punto_medio] = []
            
        # Añadir un valor pequeño para estos puntos
        indices_todos = [indice for indices in datos_curva.values() for indice in indices if indices]
        if indices_todos:
            promedio_global = sum(indices_todos) / len(indices_todos)
            valor_inicial = promedio_global * 0.05  # 5% del promedio global
        else:
            valor_inicial = 0.5  # Valor predeterminado si no hay datos
        
        datos_curva[0] = [0]  # Día 0 siempre vale 0
        if punto_medio > 0:
            datos_curva[punto_medio] = [valor_inicial]

'''
        
        if "# Verificar si hay datos para la fase vegetativa" not in contenido:
            contenido = contenido[:indice] + verificacion_vegetativa + contenido[indice:]
            cambios.append("Añadida verificación de datos para fase vegetativa")
    else:
        print_warning("No se encontró el punto para añadir verificación de fase vegetativa")
    
    # 6. Actualizar la llamada a la función generar_grafico_curva
    if "generar_grafico_curva(" in contenido:
        contenido = contenido.replace("generar_grafico_curva(", "generar_grafico_curva_mejorado(")
        cambios.append("Actualizada la llamada a la función de generación de gráficos")
    
    # Solo guardar cambios si se realizaron modificaciones
    if contenido != contenido_original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(contenido)
        return cambios
    else:
        return ["No se realizaron cambios (posiblemente ya estaban aplicados)"]

def main():
    """Función principal"""
    print_header("===== SCRIPT DE ACTUALIZACIÓN DE ALGORITMO DE CURVAS =====")
    print("Este script aplicará las mejoras al algoritmo de generación de curvas")
    print("Asegúrate de ejecutarlo desde el directorio raíz de tu proyecto Flask")
    
    # Buscar archivo routes.py
    routes_path = encontrar_archivo("routes.py")
    if not routes_path:
        print_error("No se encontró el archivo routes.py")
        print("Por favor, ejecuta este script desde el directorio raíz de tu proyecto Flask")
        sys.exit(1)
    
    # Validar que sea el archivo correcto
    if not validar_archivo(routes_path):
        print_warning(f"El archivo encontrado ({routes_path}) no parece contener la función curva_produccion")
        respuesta = input("¿Deseas continuar de todos modos? (s/n): ").lower()
        if respuesta not in ['s', 'si', 'sí', 'y', 'yes']:
            print("Operación cancelada.")
            sys.exit(0)
    
    print(f"Archivo routes.py encontrado en: {routes_path}")
    
    # Crear copia de seguridad
    backup_path = crear_backup(routes_path)
    print_success(f"Copia de seguridad creada en: {backup_path}")
    
    # Modificar archivo
    print("\nAplicando mejoras al algoritmo de generación de curvas...")
    cambios = modificar_archivo(routes_path)
    
    # Mostrar resultados
    print("\nCambios realizados:")
    for cambio in cambios:
        print_success(cambio)
    
    # Instrucciones finales
    print_header("\nPasos adicionales:")
    print("1. Reinicia tu aplicación Flask para aplicar los cambios")
    print("2. Verifica que las curvas de producción se muestren correctamente")
    print("3. Si encuentras problemas, puedes restaurar la copia de seguridad desde:")
    print(f"   {backup_path}")
    
    print_header("===== FIN DEL SCRIPT =====")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nOperación cancelada por el usuario.")
        sys.exit(130)
    except Exception as e:
        print_error(f"Error inesperado: {str(e)}")
        sys.exit(1)
