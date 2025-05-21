"""
Utilidades para estandarizar el manejo de números en toda la aplicación.

Mejoras:
- Eliminación de redundancias con data_utils.py
- Mejor documentación
- Manejo más robusto de errores
- Funciones más genéricas y reutilizables
"""

from decimal import Decimal, getcontext, ROUND_HALF_UP
import re
import numpy as np

# Configuración global para Decimal
getcontext().prec = 10
getcontext().rounding = ROUND_HALF_UP

def normalize_number_string(value):
    """
    Normaliza una cadena numérica para conversión consistente a Decimal.
    Maneja formatos internacionales (coma/punto como separadores).
    """
    if not isinstance(value, str):
        return str(value)
    
    value = value.strip()
    
    # Detectar formato español (1.000,00) vs inglés (1,000.00)
    if re.search(r'\d+\.\d+,\d+', value) or re.search(r'\d{1,3}(?:\.\d{3})+,\d+', value):
        value = value.replace('.', '').replace(',', '.')
    else:
        value = value.replace(',', '')
    
    return value

def to_decimal(value, default=None, precision=2):
    """
    Convierte cualquier valor a Decimal de forma segura.
    
    Args:
        value: Valor a convertir
        default: Valor por defecto si falla (None -> Decimal('0.0'))
        precision: Dígitos decimales para redondeo (None para no redondear)
    """
    if default is None:
        default = Decimal('0.0')
    if value is None:
        return default
    
    try:
        if isinstance(value, str):
            value = normalize_number_string(value)
        
        decimal_value = Decimal(str(value))
        if precision is not None:
            decimal_value = decimal_value.quantize(Decimal(f'0.{"0" * precision}'))
        return decimal_value
    except (ValueError, TypeError, ArithmeticError):
        return default

def to_int(value, default=0):
    """
    Convierte cualquier valor a entero de forma segura.
    """
    if value is None:
        return default
    
    try:
        decimal_value = to_decimal(value, precision=0)
        return int(decimal_value)
    except (ValueError, TypeError):
        return default

def to_float(value, default=0.0, precision=2):
    """
    Convierte cualquier valor a float de forma segura.
    """
    if value is None:
        return default
    
    try:
        decimal_value = to_decimal(value, precision=precision)
        return float(decimal_value)
    except (ValueError, TypeError):
        return default

def calc_percentage(numerator, denominator, default=None, precision=2):
    """
    Calcula un porcentaje de forma segura con manejo de división por cero.
    """
    if default is None:
        default = Decimal('0.0')
    
    num = to_decimal(numerator)
    den = to_decimal(denominator)
    
    if den == 0:
        return default
    
    result = (num / den) * Decimal('100')
    return result.quantize(Decimal(f'0.{"0" * precision}')) if precision is not None else result

def format_decimal(value, precision=2, as_string=True, thousands_sep=' ', decimal_sep=','):
    """
    Formatea un valor decimal para visualización.
    
    Args:
        value: Valor a formatear
        precision: Decimales a mostrar
        as_string: Si True devuelve string, si False Decimal
        thousands_sep: Separador de miles
        decimal_sep: Separador decimal
    """
    try:
        decimal_value = to_decimal(value, precision=precision)
        if not as_string:
            return decimal_value
            
        # Formatear con separadores
        parts = f"{decimal_value:,}".split('.')
        int_part = parts[0].replace(',', thousands_sep)
        dec_part = parts[1] if len(parts) > 1 else '0' * precision
        
        return f"{int_part}{decimal_sep}{dec_part[:precision]}"
    except Exception:
        return "0" + decimal_sep + "0" * precision if as_string else Decimal('0.0')

def calc_area_from_plants_and_density(plants, density):
    """
    Calcula el área necesaria para un número de plantas y densidad dada.
    """
    plants_dec = to_decimal(plants)
    density_dec = to_decimal(density)
    
    if density_dec <= 0:
        return Decimal('0.0')
    
    return (plants_dec / density_dec).quantize(Decimal('0.01'))

def calc_plants_from_area_and_density(area, density):
    """
    Calcula el número de plantas para un área y densidad dada.
    """
    area_dec = to_decimal(area)
    density_dec = to_decimal(density)
    
    return to_int(area_dec * density_dec)

def filtrar_outliers_iqr(valores, factor=1.5):
    """
    Filtra valores atípicos usando el método del rango intercuartil (IQR).
    
    Args:
        valores: Lista/array de valores numéricos
        factor: Multiplicador para determinar límites (típicamente 1.5)
        
    Returns:
        Lista de valores filtrados
    """
    if not valores or len(valores) < 5:
        return valores
        
    valores_arr = np.array(valores, dtype=np.float64)
    q1 = np.percentile(valores_arr, 25)
    q3 = np.percentile(valores_arr, 75)
    iqr = q3 - q1
    
    if iqr == 0:
        return valores
        
    lower_bound = q1 - (factor * iqr)
    upper_bound = q3 + (factor * iqr)
    
    filtered = valores_arr[(valores_arr >= lower_bound) & (valores_arr <= upper_bound)]
    return filtered.tolist()