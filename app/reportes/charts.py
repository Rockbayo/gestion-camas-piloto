import matplotlib
matplotlib.use('Agg')  # Configurar backend no interactivo
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO
import base64
from scipy.interpolate import splrep, splev, interp1d
from flask import current_app
from .utils import get_config_value

MAXIMO_CICLO_ABSOLUTO = get_config_value('MAXIMO_CICLO_ABSOLUTO', 93)
SUAVIZADO_MINIMO_PUNTOS = get_config_value('SUAVIZADO_MINIMO_PUNTOS', 4)

def generar_grafico_error(mensaje):
    """Genera un gráfico de error con el mensaje especificado"""
    plt.figure(figsize=(10, 6))
    plt.text(0.5, 0.5, mensaje, ha='center', va='center', fontsize=14)
    plt.tight_layout()
    return guardar_grafico_a_base64()

def guardar_grafico_a_base64():
    """Guarda el gráfico actual en un buffer y lo convierte a base64"""
    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=100)
    buffer.seek(0)
    grafico_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close()
    return grafico_base64

def generar_grafico_curva(puntos_curva, variedad_info, ciclo_vegetativo_promedio, ciclo_total_maximo):
    """
    Genera un gráfico para la curva de producción con mejoras en el suavizado.
    
    Args:
        puntos_curva: Lista de puntos {dia, indice_promedio, ...}
        variedad_info: Nombre de la variedad para el título
        ciclo_vegetativo_promedio: Días promedio del ciclo vegetativo
        ciclo_total_maximo: Días promedio del ciclo total
        
    Returns:
        Imagen codificada en base64 del gráfico generado
    """
    try:
        # Verificar datos mínimos
        if not puntos_curva or len(puntos_curva) < 3:
            return generar_grafico_error("Datos insuficientes para generar curva")
        
        # Extraer datos
        dias = np.array([p['dia'] for p in puntos_curva])
        indices = np.array([p['indice_promedio'] for p in puntos_curva])
        
        # Configurar figura
        plt.figure(figsize=(10, 6))
        
        # Gráfico de dispersión
        plt.scatter(dias, indices, color='blue', s=50, alpha=0.7, label='Datos históricos')
        
        # Suavizado condicional
        if len(dias) >= SUAVIZADO_MINIMO_PUNTOS:
            try:
                dias_suavizados = np.linspace(0, ciclo_total_maximo, 200)
                s_factor = len(dias) / 3  # Factor de suavizado adaptativo
                
                tck = splrep(dias, indices, s=s_factor)
                indices_suavizados = splev(dias_suavizados, tck)
                
                # Asegurar valores razonables
                indices_suavizados = np.clip(indices_suavizados, 0, max(indices) * 1.2)
                
                plt.plot(dias_suavizados, indices_suavizados, 'r--', linewidth=2, 
                        label='Tendencia (suavizado natural)')
            except Exception as e:
                current_app.logger.warning(f"Error en suavizado: {str(e)}")
                # Fallback a interpolación lineal
                f = interp1d(dias, indices, kind='linear', fill_value="extrapolate")
                dias_suavizados = np.linspace(0, ciclo_total_maximo, 100)
                plt.plot(dias_suavizados, f(dias_suavizados), 'r--', linewidth=1.5, 
                         label='Tendencia (interpolación lineal)')
        
        # Configuración del gráfico
        plt.xlabel('Días desde siembra')
        plt.ylabel('Índice promedio (%)')
        plt.title(f'Curva de producción: {variedad_info[:50]}')
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        # Límites de ejes
        max_y = min(50, max(indices) * 1.2) if indices else 20
        plt.ylim(0, max_y)
        plt.xlim(0, ciclo_total_maximo)
        
        # Líneas de ciclo
        plt.axvline(x=ciclo_vegetativo_promedio, color='g', linestyle='--', alpha=0.7,
                   label=f'Fin ciclo vegetativo ({ciclo_vegetativo_promedio} días)')
        plt.axvline(x=ciclo_total_maximo, color='r', linestyle='--', alpha=0.7,
                   label=f'Fin ciclo total ({ciclo_total_maximo} días)')
        
        # Nota al pie
        plt.figtext(0.5, 0.01, 
                   "Nota: La línea punteada roja representa la tendencia de producción ajustada.", 
                   ha='center', fontsize=9)
        
        return guardar_grafico_a_base64()
        
    except Exception as e:
        current_app.logger.error(f"Error generando gráfico: {str(e)}")
        return generar_grafico_error("Error al generar el gráfico")