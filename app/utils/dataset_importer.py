"""
Módulo unificado para la importación de datasets en la aplicación.

Mejoras:
- Patrón de diseño Factory para los importadores
- Mejor manejo de errores
- Documentación más clara
"""

import os
from typing import Dict, Tuple, Callable
from flask import current_app
from app.utils.base_importer import BaseImporter

# Configuración
TEMP_DIR = os.path.join('uploads', 'temp')
os.makedirs(TEMP_DIR, exist_ok=True)

class DatasetImporter:
    """
    Clase orquestadora para la importación de datasets.
    Implementa el patrón Factory para delegar a importadores específicos.
    """
    
    # Registro de importadores disponibles
    _IMPORTERS: Dict[str, Callable] = {
        'variedades': 'app.utils.variedades_importer.VariedadesImporter.import_variedades',
        'bloques': 'app.utils.bloques_importer.BloquesImporter.import_bloques_camas'
    }
    
    @staticmethod
    def save_temp_file(file_obj):
        """Guarda un archivo temporal delegando a BaseImporter."""
        return BaseImporter.save_temp_file(file_obj)
    
    @staticmethod
    def preview_dataset(file_path, rows=10):
        """Previsualiza un dataset delegando a BaseImporter."""
        return BaseImporter.preview_dataset(file_path, rows)
    
    @staticmethod
    def process_dataset(
        file_path: str, 
        dataset_type: str, 
        column_mapping: Dict[str, str] = None, 
        validate_only: bool = False, 
        skip_first_row: bool = True
    ) -> Tuple[bool, str, Dict]:
        """
        Procesa un dataset según su tipo.
        
        Args:
            file_path: Ruta del archivo a importar
            dataset_type: Tipo de dataset ('variedades', 'bloques')
            column_mapping: Mapeo de columnas personalizado
            validate_only: Solo validar sin importar
            skip_first_row: Saltar primera fila (encabezados)
            
        Returns:
            Tuple: (success, message, stats)
        """
        try:
            # Obtener el importador específico
            importer_path = DatasetImporter._IMPORTERS.get(dataset_type)
            if not importer_path:
                return False, f"Tipo de dataset no soportado: {dataset_type}", {}
            
            # Importar dinámicamente el método
            module_path, method_name = importer_path.rsplit('.', 1)
            module = __import__(module_path, fromlist=[method_name])
            importer_method = getattr(module, method_name)
            
            # Ejecutar el importador
            return importer_method(
                file_path=file_path,
                column_mapping=column_mapping,
                validate_only=validate_only,
                skip_first_row=skip_first_row
            )
            
        except Exception as e:
            current_app.logger.error(f"Error en DatasetImporter: {str(e)}", exc_info=True)
            return False, f"Error inesperado durante la importación: {str(e)}", {}