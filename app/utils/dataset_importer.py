"""
Módulo unificado para la importación de datasets en la aplicación.

Mejoras:
- Importación directa en lugar de dinámica para evitar errores
- Mejor manejo de errores
- Documentación más clara
"""

import os
from typing import Dict, Tuple
from flask import current_app
from app.utils.base_importer import BaseImporter

# Configuración
TEMP_DIR = os.path.join('uploads', 'temp')
os.makedirs(TEMP_DIR, exist_ok=True)

class DatasetImporter:
    """
    Clase orquestadora para la importación de datasets.
    Utiliza importación directa para evitar problemas con importación dinámica.
    """
    
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
            # Importar los módulos directamente
            if dataset_type == 'variedades':
                from app.utils.variedades_importer import VariedadesImporter
                return VariedadesImporter.import_variedades(
                    file_path=file_path,
                    column_mapping=column_mapping,
                    validate_only=validate_only,
                    skip_first_row=skip_first_row
                )
            
            elif dataset_type == 'bloques':
                from app.utils.bloques_importer import BloquesImporter
                return BloquesImporter.import_bloques_camas(
                    file_path=file_path,
                    column_mapping=column_mapping,
                    validate_only=validate_only,
                    skip_first_row=skip_first_row
                )
            
            else:
                return False, f"Tipo de dataset no soportado: {dataset_type}", {}
            
        except ImportError as e:
            current_app.logger.error(f"Error al importar módulo para {dataset_type}: {str(e)}", exc_info=True)
            return False, f"Error al cargar el importador para {dataset_type}: {str(e)}", {}
        
        except Exception as e:
            current_app.logger.error(f"Error en DatasetImporter: {str(e)}", exc_info=True)
            return False, f"Error inesperado durante la importación: {str(e)}", {}