"""
Módulo base para la importación de datasets.
Contiene funciones y utilidades comunes para todos los importadores.
"""
import os
import json
import pandas as pd
from werkzeug.utils import secure_filename
import uuid
from flask import session

# Configuración de directorios
TEMP_DIR = os.path.join('uploads', 'temp')
os.makedirs(TEMP_DIR, exist_ok=True)

class BaseImporter:
    """Clase base con funcionalidades comunes para todos los importadores."""
    
    @staticmethod
    def save_temp_file(file_obj, session_data=True):
        """
        Guarda un archivo temporalmente y configura la sesión si es necesario.
        
        Args:
            file_obj: Objeto de archivo de Flask
            session_data: Si True, guarda información en la sesión
            
        Returns:
            path: Ruta del archivo temporal
        """
        filename = secure_filename(file_obj.filename)
        file_id = str(uuid.uuid4())
        temp_path = os.path.join(TEMP_DIR, f"{file_id}_{filename}")
        
        # Crear directorio si no existe
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        
        # Guardar archivo
        file_obj.save(temp_path)
        
        # Guardar información en la sesión si es necesario
        if session_data:
            session['temp_file'] = temp_path
            session['original_filename'] = filename
        
        return temp_path
    
    @staticmethod
    def preview_dataset(file_path, rows=10):
        """
        Genera una vista previa del dataset para mostrar en la interfaz de usuario.
        
        Args:
            file_path: Ruta del archivo Excel
            rows: Número de filas para la vista previa
            
        Returns:
            dict: Datos de la vista previa
        """
        try:
            df = pd.read_excel(file_path)
            
            # Verificar que el dataset tenga datos
            if df.empty:
                return {
                    "error": "El archivo no contiene datos.",
                    "total_rows": 0,
                    "columns": [],
                    "preview_data": [],
                    "validation": {
                        "is_valid": False,
                        "message": "El archivo está vacío."
                    }
                }
            
            # Obtener información general del dataset
            preview = {
                "total_rows": len(df),
                "columns": list(df.columns),
                "preview_data": df.head(rows).to_dict(orient='records'),
            }
            
            # Validación básica
            preview["validation"] = {
                "is_valid": True,
                "message": "El dataset parece válido para importación."
            }
            
            return preview
            
        except Exception as e:
            return {
                "error": str(e),
                "total_rows": 0,
                "columns": [],
                "preview_data": [],
                "validation": {
                    "is_valid": False,
                    "message": f"Error al procesar el archivo: {str(e)}"
                }
            }
    
    @staticmethod
    def prepare_dataframe(file_path, column_mapping=None, skip_first_row=True, required_columns=None):
        """
        Prepara un DataFrame para su procesamiento.
        
        Args:
            file_path: Ruta del archivo Excel
            column_mapping: Diccionario para mapear columnas
            skip_first_row: Si es True, omite la primera fila (encabezados)
            required_columns: Lista de columnas requeridas
            
        Returns:
            tuple: (df, message, success), donde df es el DataFrame, 
                  message es un mensaje de error si lo hay, y 
                  success es un booleano que indica si la operación fue exitosa
        """
        try:
            # Cargar archivo Excel
            df = pd.read_excel(file_path, header=0 if skip_first_row else None)
            
            # Aplicar mapeo de columnas si se proporciona
            if column_mapping and isinstance(column_mapping, dict):
                df = df.rename(columns=column_mapping)
            
            # Verificar que las columnas requeridas existan
            if required_columns:
                # Convertir columnas a mayúsculas
                df.columns = [col.upper() for col in df.columns]
                
                missing_columns = [col for col in required_columns if col not in df.columns]
                
                if missing_columns:
                    return None, f"Faltan columnas requeridas: {', '.join(missing_columns)}", False
            
            return df, "DataFrame preparado correctamente", True
            
        except Exception as e:
            return None, f"Error al preparar el DataFrame: {str(e)}", False