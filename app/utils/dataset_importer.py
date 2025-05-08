"""
Módulo unificado para la importación de datasets en la aplicación.
Actúa como orquestador entre los diferentes importadores específicos.
"""
import os
from flask import session

# Importar los importadores específicos
from app.utils.base_importer import BaseImporter
from app.utils.variedades_importer import VariedadesImporter
from app.utils.bloques_importer import BloquesImporter

# Configurar directorio temporal
TEMP_DIR = os.path.join('uploads', 'temp')
os.makedirs(TEMP_DIR, exist_ok=True)

class DatasetImporter:
    """
    Clase orquestadora para manejar la importación de diferentes tipos de datasets.
    Delega la importación a clases específicas según el tipo de dataset.
    """
    
    @staticmethod
    def save_temp_file(file_obj):
        """Delega la función a BaseImporter"""
        return BaseImporter.save_temp_file(file_obj)
    
    @staticmethod
    def preview_dataset(file_path, rows=10):
        """Delega la función a BaseImporter"""
        return BaseImporter.preview_dataset(file_path, rows)
    
    @staticmethod
    def process_dataset(file_path, dataset_type, column_mapping=None, validate_only=False, skip_first_row=True):
        """
        Procesa un dataset según su tipo, delegando a los importadores específicos.
        
        Args:
            - file_path: Ruta del archivo Excel
            - dataset_type: Tipo de dataset ('variedades', 'bloques')
            - column_mapping: Diccionario para mapear columnas personalizadas
            - validate_only: Si es True, sólo valida el dataset sin importar
            - skip_first_row: Si es True, omite la primera fila (encabezados)
            
        Returns:
            - (bool, str, dict): Tupla con estado, mensaje y estadísticas
        """
        # Mapeo de tipos de dataset a los métodos específicos de importación
        importers = {
            'variedades': VariedadesImporter.import_variedades,
            'bloques': BloquesImporter.import_bloques_camas
        }
        
        # Verificar si el tipo de dataset está soportado
        if dataset_type not in importers:
            return False, f"Tipo de dataset no soportado: {dataset_type}", {}
        
        # Delegar la importación al método correspondiente
        return importers[dataset_type](
            file_path, 
            column_mapping, 
            validate_only, 
            skip_first_row
        )