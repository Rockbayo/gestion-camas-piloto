# app/utils/base_importer.py
"""
Módulo base para importación de datos desde archivos Excel.
Proporciona funcionalidades comunes a todos los importadores específicos.
"""
import os
import pandas as pd
import uuid
from werkzeug.utils import secure_filename

# Configurar directorio temporal
TEMP_DIR = os.path.join('uploads', 'temp')
os.makedirs(TEMP_DIR, exist_ok=True)

class BaseImporter:
    """Clase base para importadores de datos."""
    
    @staticmethod
    def save_temp_file(file_obj):
        """
        Guarda un archivo temporalmente y devuelve la ruta.
        
        Args:
            file_obj: Objeto de archivo subido (FileStorage)
            
        Returns:
            Ruta del archivo temporal
        """
        filename = secure_filename(file_obj.filename)
        temp_filename = f"{uuid.uuid4()}_{filename}"
        temp_path = os.path.join(TEMP_DIR, temp_filename)
        file_obj.save(temp_path)
        return temp_path
    
    @staticmethod
    def prepare_dataframe(file_path, column_mapping=None, skip_first_row=True, required_columns=None):
        """
        Prepara un DataFrame desde un archivo Excel con opciones de mapeo.
        
        Args:
            file_path: Ruta del archivo Excel
            column_mapping: Diccionario para mapear columnas
            skip_first_row: Si es True, omite la primera fila (encabezados)
            required_columns: Lista de columnas requeridas
            
        Returns:
            Tupla (df, message, success) con el DataFrame, mensaje y estado
        """
        try:
            # Determinar tipo de archivo y leer
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)
            
            # Aplicar mapeo de columnas si se proporciona
            if column_mapping:
                df = df.rename(columns=column_mapping)
            
            # Omitir primera fila si se indica
            if skip_first_row:
                df = df.iloc[1:].reset_index(drop=True)
            
            # Verificar columnas requeridas
            if required_columns:
                missing_columns = [col for col in required_columns if col not in df.columns]
                if missing_columns:
                    return None, f"Faltan columnas requeridas: {', '.join(missing_columns)}", False
            
            return df, "DataFrame preparado correctamente", True
        
        except Exception as e:
            return None, f"Error al preparar DataFrame: {str(e)}", False
    
    @staticmethod
    def preview_dataset(file_path, rows=10):
        """
        Genera una vista previa de un archivo Excel o CSV.
        
        Args:
            file_path: Ruta del archivo
            rows: Número de filas a incluir en la vista previa
            
        Returns:
            Diccionario con información del dataset
        """
        try:
            # Determinar tipo de archivo y leer
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)
            
            # Obtener información básica
            total_rows = len(df)
            columns = df.columns.tolist()
            
            # Crear vista previa
            preview_data = []
            for i, row in df.head(rows).iterrows():
                preview_data.append({col: row[col] for col in columns})
            
            # Verificar validez básica
            validation = {
                "is_valid": True,
                "message": "Dataset válido"
            }
            
            if total_rows == 0:
                validation["is_valid"] = False
                validation["message"] = "El dataset está vacío"
                
            return {
                "total_rows": total_rows,
                "columns": columns,
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
                    "message": f"Error al procesar el archivo: {str(e)}"
                }
            }