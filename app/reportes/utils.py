from datetime import datetime
import numpy as np
from flask import current_app
from sqlalchemy import func

def get_config_value(key, default):
    """Obtiene valores de configuración de forma segura"""
    try:
        return current_app.config.get(key, default)
    except RuntimeError:  # Para cuando no hay contexto de aplicación
        return default

def calc_plantas_totales(area, densidad):
    """Calcula el número total de plantas basado en área y densidad"""
    return area * densidad if area and densidad else 0

def calc_indice_aprovechamiento(tallos, plantas):
    """Calcula el índice de aprovechamiento en porcentaje"""
    return (tallos / plantas * 100) if plantas > 0 else 0

def filtrar_outliers_iqr(valores, factor=1.5):
    """Filtra valores atípicos usando el rango intercuartil (IQR)"""
    if not valores or len(valores) < 5:
        return valores
        
    valores_arr = np.array(valores)
    q1 = np.percentile(valores_arr, 25)
    q3 = np.percentile(valores_arr, 75)
    iqr = q3 - q1
    
    if iqr == 0:
        return valores
        
    limite_inferior = q1 - (factor * iqr)
    limite_superior = q3 + (factor * iqr)
    
    return valores_arr[(valores_arr >= limite_inferior) & (valores_arr <= limite_superior)].tolist()