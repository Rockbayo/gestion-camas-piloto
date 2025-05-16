# app/utils/number_utils.py

"""
Utilidades para estandarizar el manejo de números en toda la aplicación.
Proporciona funciones para conversión, validación y operaciones numéricas consistentes.
"""

from decimal import Decimal, getcontext, ROUND_HALF_UP
import re

# Configurar precisión para operaciones con Decimal
getcontext().prec = 10  # 10 dígitos de precisión
getcontext().rounding = ROUND_HALF_UP  # Redondeo estándar

def normalize_number_string(value):
    """
    Normaliza una cadena numérica para su conversión a Decimal.
    Maneja formatos con comas y puntos de manera consistente.
    
    Args:
        value: Cadena de texto a normalizar
        
    Returns:
        Cadena normalizada lista para conversión a Decimal
    """
    if not isinstance(value, str):
        return str(value)
    
    # Eliminar espacios en blanco
    value = value.strip()
    
    # Detectar formato de número (español o inglés)
    # Si contiene coma como separador decimal y puntos como separador de miles
    if re.search(r'\d+\.\d+,\d+', value) or re.search(r'\d{1,3}(?:\.\d{3})+,\d+', value):
        # Formato español: eliminar puntos y reemplazar coma por punto
        value = value.replace('.', '')
        value = value.replace(',', '.')
    else:
        # Formato inglés o simple: reemplazar coma por punto
        value = value.replace(',', '.')
    
    return value

def to_decimal(value, default=None, precision=2):
    """
    Convierte un valor a Decimal de manera segura con precisión controlada.
    
    Args:
        value: Valor a convertir (str, int, float, Decimal)
        default: Valor por defecto si la conversión falla
        precision: Número de decimales para redondeo
        
    Returns:
        Decimal con la precisión especificada
    """
    if default is None:
        default = Decimal('0.0')
        
    if value is None:
        return default
    
    try:
        # Si es string, normalizarlo primero
        if isinstance(value, str):
            value = normalize_number_string(value)
        
        # Convertir a Decimal y redondear
        result = Decimal(str(value))
        if precision is not None:
            result = result.quantize(Decimal(f'0.{"0" * precision}'))
        return result
    except (ValueError, TypeError, ArithmeticError):
        return default

def to_int(value, default=0):
    """
    Convierte un valor a entero de manera segura.
    
    Args:
        value: Valor a convertir
        default: Valor por defecto si la conversión falla
        
    Returns:
        Valor entero
    """
    if value is None:
        return default
    
    try:
        # Para valores Decimal o float, redondear primero
        if isinstance(value, Decimal) or isinstance(value, float):
            return int(round(float(value)))
        
        # Para strings, normalizar primero
        if isinstance(value, str):
            value = normalize_number_string(value)
            # Si tiene decimales, redondear
            if '.' in value:
                return int(round(float(value)))
        
        return int(value)
    except (ValueError, TypeError):
        return default

def to_float(value, default=0.0, precision=2):
    """
    Convierte un valor a float de manera segura.
    
    Args:
        value: Valor a convertir
        default: Valor por defecto si la conversión falla
        precision: Número de decimales para redondeo
        
    Returns:
        Valor float
    """
    if value is None:
        return default
    
    try:
        # Convertir primero a Decimal para precisión y luego a float
        result = float(to_decimal(value, Decimal(str(default)), precision))
        return round(result, precision) if precision is not None else result
    except (ValueError, TypeError):
        return default

def calc_percentage(numerator, denominator, default=None, precision=2):
    """
    Calcula un porcentaje de forma segura.
    
    Args:
        numerator: Valor del numerador
        denominator: Valor del denominador
        default: Valor por defecto si el cálculo falla
        precision: Número de decimales para redondeo
        
    Returns:
        Porcentaje como Decimal con la precisión especificada
    """
    if default is None:
        default = Decimal('0.0')
        
    try:
        num = to_decimal(numerator)
        den = to_decimal(denominator)
        
        if den == 0:
            return default
        
        result = (num / den) * Decimal('100')
        return result.quantize(Decimal(f'0.{"0" * precision}')) if precision is not None else result
    except Exception:
        return default

def format_decimal(value, precision=2, as_string=True):
    """
    Formatea un valor decimal para visualización.
    
    Args:
        value: Valor a formatear
        precision: Número de decimales a mostrar
        as_string: Si es True, devuelve un string; si es False, un Decimal
        
    Returns:
        Valor formateado como string o Decimal según as_string
    """
    try:
        decimal_value = to_decimal(value, precision=precision)
        if as_string:
            # Formato con separador de miles y decimales
            return f"{decimal_value:,}".replace(',', ' ').replace('.', ',')
        return decimal_value
    except Exception:
        return "0,00" if as_string else Decimal('0.0')

def calc_area_from_plants_and_density(plants, density):
    """
    Calcula el área a partir de plantas y densidad.
    
    Args:
        plants: Número de plantas
        density: Densidad (plantas/m²)
        
    Returns:
        Área calculada en m²
    """
    try:
        plants_dec = to_decimal(plants)
        density_dec = to_decimal(density)
        
        if density_dec <= 0:
            return Decimal('0.0')
        
        return (plants_dec / density_dec).quantize(Decimal('0.01'))
    except Exception:
        return Decimal('0.0')

def calc_plants_from_area_and_density(area, density):
    """
    Calcula el número de plantas a partir de área y densidad.
    
    Args:
        area: Área en m²
        density: Densidad (plantas/m²)
        
    Returns:
        Número de plantas (entero)
    """
    try:
        area_dec = to_decimal(area)
        density_dec = to_decimal(density)
        
        plants = area_dec * density_dec
        return to_int(plants)
    except Exception:
        return 0