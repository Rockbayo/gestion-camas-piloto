"""
Módulo base para importación de datos desde archivos Excel/CSV.

Mejoras:
- Mejor manejo de tipos de archivo
- Validación más robusta
- Documentación más clara
- Métodos más modulares
"""

import os
import pandas as pd
import uuid
from typing import Tuple, Dict, Any, Optional
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage

class BaseImporter:
    """
    Clase base para importadores de datos con funcionalidades comunes.
    """
    
    # Configuración de directorio temporal
    TEMP_DIR = os.path.join('uploads', 'temp')
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    @staticmethod
    def save_temp_file(file_obj: FileStorage) -> str:
        """
        Guarda un archivo temporalmente con nombre seguro.
        
        Args:
            file_obj: Objeto FileStorage de Flask/Werkzeug
            
        Returns:
            Ruta completa del archivo guardado
        """
        try:
            filename = secure_filename(file_obj.filename)
            temp_filename = f"{uuid.uuid4().hex}_{filename}"
            temp_path = os.path.join(BaseImporter.TEMP_DIR, temp_filename)
            file_obj.save(temp_path)
            return temp_path
        except Exception as e:
            raise IOError(f"Error al guardar archivo temporal: {str(e)}")
    
    @staticmethod
    def prepare_dataframe(
        file_path: str,
        column_mapping: Optional[Dict[str, str]] = None,
        skip_first_row: bool = True,
        required_columns: Optional[list] = None
    ) -> Tuple[pd.DataFrame, str, bool]:
        """
        Prepara un DataFrame desde un archivo con validación básica.
        
        Args:
            file_path: Ruta del archivo a importar
            column_mapping: Diccionario para renombrar columnas
            skip_first_row: Si True, omite la primera fila
            required_columns: Columnas obligatorias
            
        Returns:
            Tuple: (DataFrame, mensaje, éxito)
        """
        try:
            # Leer archivo según extensión
            df = BaseImporter._read_file(file_path)
            
            # Aplicar transformaciones básicas
            df = BaseImporter._transform_dataframe(df, column_mapping, skip_first_row)
            
            # Validar columnas requeridas
            if required_columns:
                missing = BaseImporter._validate_columns(df, required_columns)
                if missing:
                    return None, f"Columnas requeridas faltantes: {', '.join(missing)}", False
            
            return df, "DataFrame preparado correctamente", True
            
        except Exception as e:
            return None, f"Error al preparar DataFrame: {str(e)}", False
    
    @staticmethod
    def preview_dataset(file_path: str, rows: int = 10) -> Dict[str, Any]:
        """
        Genera una vista previa del dataset con información básica.
        
        Args:
            file_path: Ruta del archivo
            rows: Número de filas para la vista previa
            
        Returns:
            Dict con información del dataset
        """
        try:
            df = BaseImporter._read_file(file_path)
            
            preview_data = [
                {col: row[col] for col in df.columns}
                for _, row in df.head(rows).iterrows()
            ]
            
            validation = BaseImporter._validate_dataset(df)
            
            return {
                "total_rows": len(df),
                "columns": df.columns.tolist(),
                "preview_data": preview_data,
                "validation": validation
            }
            
        except Exception as e:
            return {
                "total_rows": 0,
                "columns": [],
                "preview_data": [],
                "validation": {
                    "is_valid": False,
                    "message": f"Error al procesar archivo: {str(e)}"
                }
            }
    
    @classmethod
    def _read_file(cls, file_path: str) -> pd.DataFrame:
        """Lee un archivo según su extensión."""
        if file_path.endswith('.csv'):
            return pd.read_csv(file_path)
        return pd.read_excel(file_path)
    
    @classmethod
    def _transform_dataframe(
        cls,
        df: pd.DataFrame,
        column_mapping: Optional[Dict[str, str]] = None,
        skip_first_row: bool = True
    ) -> pd.DataFrame:
        """Aplica transformaciones básicas al DataFrame."""
        if column_mapping:
            df = df.rename(columns=column_mapping)
        if skip_first_row:
            df = df.iloc[1:].reset_index(drop=True)
        return df
    
    @classmethod
    def _validate_columns(cls, df: pd.DataFrame, required_columns: list) -> list:
        """Valida que estén presentes las columnas requeridas."""
        return [col for col in required_columns if col not in df.columns]
    
    @classmethod
    def _validate_dataset(cls, df: pd.DataFrame) -> Dict[str, Any]:
        """Realiza validaciones básicas del dataset."""
        if len(df) == 0:
            return {
                "is_valid": False,
                "message": "El dataset está vacío"
            }
        return {
            "is_valid": True,
            "message": "Dataset válido"
        }