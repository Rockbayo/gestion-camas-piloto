# -*- coding: utf-8 -*-
"""
Utilidades para manejo consistente de tipos de datos y cálculos numéricos

Este módulo ahora actúa como interfaz para las funciones en number_utils.py,
eliminando redundancias y manteniendo compatibilidad.
"""

from decimal import Decimal
from app.utils.number_utils import (
    to_decimal as _to_decimal,
    to_int as _to_int,
    to_float as _to_float,
    calc_percentage,
    calc_plants_from_area_and_density,
    filtrar_outliers_iqr as _filtrar_outliers_iqr
)

def safe_decimal(value, default=None):
    """Alias de to_decimal para mantener compatibilidad"""
    return _to_decimal(value, default=default)

def safe_int(value, default=0):
    """Alias de to_int para mantener compatibilidad"""
    return _to_int(value, default)

def safe_float(value, default=0.0):
    """Alias de to_float para mantener compatibilidad"""
    return _to_float(value, default)

def calc_indice_aprovechamiento(tallos, plantas):
    """
    Calcula el índice de aprovechamiento (tallos/plantas en porcentaje)
    
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
    
    Args:
        area: Área en metros cuadrados
        densidad: Densidad en plantas por m²
        
    Returns:
        Cantidad de plantas (entero)
    """
    return calc_plants_from_area_and_density(area, densidad)

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
    return _filtrar_outliers_iqr(valores, factor)