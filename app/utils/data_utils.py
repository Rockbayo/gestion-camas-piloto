# -*- coding: utf-8 -*-
"""
Utilidades para manejo consistente de tipos de datos y cálculos numéricos
"""
from decimal import Decimal, getcontext, ROUND_HALF_UP
from app.utils.number_utils import to_decimal, to_int, to_float, calc_percentage
import numpy as np

# Configurar precisión para operaciones con Decimal
getcontext().prec = 10  # 10 dígitos de precisión
getcontext().rounding = ROUND_HALF_UP  # Redondeo estándar

def safe_decimal(value, default=None):
    """Alias de to_decimal para mantener compatibilidad"""
    if default is None:
        from decimal import Decimal
        default = Decimal('0.0')
    return to_decimal(value, default)

def safe_int(value, default=0):
    """Alias de to_int para mantener compatibilidad"""
    return to_int(value, default)

def safe_float(value, default=0.0):
    """Alias de to_float para mantener compatibilidad"""
    return to_float(value, default)

def calc_indice_aprovechamiento(tallos, plantas):
    """
    Calcula el índice de aprovechamiento (tallos/plantas en porcentaje)
    usando las nuevas funciones de cálculo de porcentaje.
    
    Args:
        tallos: Cantidad de tallos cosechados
        plantas: Cantidad de plantas sembradas
        
    Returns:
        Valor decimal del índice (porcentaje)
    """
    return calc_percentage(tallos, plantas, precision=2)

def calc_plantas_totales(area, densidad):
    """
    Calcula total de plantas según área y densidad.
    Delegando a la nueva implementación.
    
    Args:
        area: Área en metros cuadrados
        densidad: Densidad en plantas por m²
        
    Returns:
        Cantidad de plantas (entero)
    """
    from app.utils.number_utils import calc_plants_from_area_and_density
    return calc_plants_from_area_and_density(area, densidad)

# Mantener la función original sin cambios
def filtrar_outliers_iqr(valores, factor=1.5):
    """
    Filtra valores atípicos usando el método del rango intercuartil (IQR)
    con manejo consistente de tipos de datos.
    
    Args:
        valores: Lista de valores numéricos
        factor: Factor de multiplicación para el IQR (default 1.5)
        
    Returns:
        Lista de valores filtrados
    """
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