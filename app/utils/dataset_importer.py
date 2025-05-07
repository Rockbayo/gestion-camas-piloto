"""
Módulo unificado para la importación de datasets en la aplicación.
Actúa como orquestador entre los diferentes importadores específicos.
"""
import os
from werkzeug.utils import secure_filename
import uuid
from flask import session

# Importar los importadores específicos
from app.utils.base_importer import BaseImporter
from app.utils.variedades_importer import VariedadesImporter
from app.utils.bloques_importer import BloquesImporter
from app.utils.areas_importer import AreasImporter
from app.utils.densidades_importer import DensidadesImporter

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
            - file_