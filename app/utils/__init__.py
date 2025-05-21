"""
Módulo de inicialización para el paquete de utilidades.

Exporta las funciones y clases más importantes para uso en toda la aplicación.
"""

from app.utils.data_utils import (
    safe_decimal,
    safe_int,
    safe_float,
    calc_indice_aprovechamiento,
    calc_plantas_totales,
    filtrar_outliers_iqr
)

from app.utils.base_importer import BaseImporter
from app.utils.variedades_importer import VariedadesImporter
from app.utils.bloques_importer import BloquesImporter
from app.utils.stadistics import ProductionStatistics
from app.utils.date_filter import configure_date_filters
from app.utils.dataset_importer import DatasetImporter

# Exportar interfaces principales
__all__ = [
    'BaseImporter',
    'VariedadesImporter',
    'BloquesImporter',
    'ProductionStatistics',
    'DatasetImporter',
    'configure_date_filters',
    'safe_decimal',
    'safe_int',
    'safe_float',
    'calc_indice_aprovechamiento',
    'calc_plantas_totales',
    'filtrar_outliers_iqr'
]