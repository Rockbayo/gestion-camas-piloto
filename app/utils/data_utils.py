# -*- coding: utf-8 -*-
"""
Utilidades para manejo consistente de tipos de datos y cálculos numéricos
"""
from decimal import Decimal, getcontext, ROUND_HALF_UP
import numpy as np

# Configurar precisión para operaciones con Decimal
getcontext().prec = 10  # 10 dígitos de precisión
getcontext().rounding = ROUND_HALF_UP  # Redondeo estándar

def safe_decimal(value, default=Decimal('0.0')):
    """Convierte un valor a Decimal de manera segura"""
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
    """Convierte un valor a entero de manera segura"""
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
    """Convierte un valor a float de manera segura"""
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
    """
    Calcula el índice de aprovechamiento (tallos/plantas en porcentaje)
    con manejo de errores y tipos de datos.
    
    Args:
        tallos: Cantidad de tallos cosechados
        plantas: Cantidad de plantas sembradas
        
    Returns:
        Valor decimal del índice (porcentaje)
    """
    tallos_dec = safe_decimal(tallos)
    plantas_dec = safe_decimal(plantas)
    
    if plantas_dec <= Decimal('0'):
        return Decimal('0')
        
    indice = (tallos_dec / plantas_dec) * Decimal('100')
    # Redondear a 2 decimales
    return indice.quantize(Decimal('0.01'))

def calc_plantas_totales(area, densidad):
    """
    Calcula total de plantas según área y densidad
    con manejo consistente de tipos de datos.
    
    Args:
        area: Área en metros cuadrados
        densidad: Densidad en plantas por m²
        
    Returns:
        Cantidad de plantas (entero)
    """
    area_dec = safe_decimal(area)
    densidad_dec = safe_decimal(densidad)
    
    plantas = area_dec * densidad_dec
    return safe_int(plantas)

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