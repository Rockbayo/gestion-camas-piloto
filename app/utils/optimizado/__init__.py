"""
Módulo de utilidades optimizado para CPC (Gestión de Camas Piloto)
"""
import os
import pandas as pd
import uuid
import numpy as np
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from app import db
from app.models import *

# BaseImporter - Funcionalidad consolidada
class BaseImporter:
    @staticmethod
    def save_temp_file(file_obj):
        """Guarda un archivo temporalmente y devuelve la ruta"""
        TEMP_DIR = os.path.join('uploads', 'temp')
        os.makedirs(TEMP_DIR, exist_ok=True)
        filename = secure_filename(file_obj.filename)
        temp_filename = f"{uuid.uuid4()}_{filename}"
        temp_path = os.path.join(TEMP_DIR, temp_filename)
        file_obj.save(temp_path)
        return temp_path
    
    @staticmethod
    def preview_dataset(file_path, rows=10):
        """Vista previa de un dataset"""
        try:
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)
            
            total_rows = len(df)
            columns = df.columns.tolist()
            
            preview_data = []
            for i, row in df.head(rows).iterrows():
                preview_data.append({col: row[col] for col in columns})
            
            return {
                "total_rows": total_rows,
                "columns": columns,
                "preview_data": preview_data,
                "validation": {"is_valid": True, "message": "Dataset válido"}
            }
        except Exception as e:
            return {
                "total_rows": 0,
                "columns": [],
                "preview_data": [],
                "validation": {"is_valid": False, "message": f"Error: {str(e)}"}
            }

# DatasetImporter - Funcionalidad consolidada
class DatasetImporter:
    @staticmethod
    def save_temp_file(file_obj):
        """Delega a BaseImporter"""
        return BaseImporter.save_temp_file(file_obj)
    
    @staticmethod
    def preview_dataset(file_path, rows=10):
        """Delega a BaseImporter"""
        return BaseImporter.preview_dataset(file_path, rows)
    
    @staticmethod
    def process_dataset(file_path, dataset_type, column_mapping=None, validate_only=False, skip_first_row=True):
        """Procesa un dataset según su tipo"""
        # Código simplificado para procesar dataset
        try:
            df = pd.read_excel(file_path) if not file_path.endswith('.csv') else pd.read_csv(file_path)
            
            if skip_first_row:
                df = df.iloc[1:].reset_index(drop=True)
            
            if column_mapping:
                df = df.rename(columns=column_mapping)
            
            # Validación básica
            if dataset_type == 'variedades':
                required_cols = ['FLOR', 'COLOR', 'VARIEDAD']
            elif dataset_type == 'bloques':
                required_cols = ['BLOQUE', 'CAMA']
            else:
                return False, f"Tipo de dataset no soportado: {dataset_type}", {}
            
            for col in required_cols:
                if col not in df.columns:
                    return False, f"Falta columna requerida: {col}", {}
            
            if validate_only:
                return True, "Dataset validado correctamente", {"total_rows": len(df), "valid_rows": len(df)}
            
            # Procesamiento real (simplificado)
            stats = {"nuevos": 0, "existentes": 0, "errores": 0}
            
            # Procesamiento por tipo
            if dataset_type == 'variedades':
                # Procesar variedades
                for _, row in df.iterrows():
                    try:
                        flor_nombre = str(row['FLOR']).strip().upper()
                        color_nombre = str(row['COLOR']).strip().upper()
                        variedad_nombre = str(row['VARIEDAD']).strip().upper()
                        
                        # Solo simulamos la importación para este script
                        stats["nuevos"] += 1
                    except Exception as e:
                        stats["errores"] += 1
            
            elif dataset_type == 'bloques':
                # Procesar bloques y camas
                for _, row in df.iterrows():
                    try:
                        bloque_nombre = str(row['BLOQUE']).strip().upper()
                        cama_nombre = str(row['CAMA']).strip().upper()
                        lado_nombre = str(row['LADO']).strip().upper() if 'LADO' in row else 'ÚNICO'
                        
                        # Solo simulamos la importación para este script
                        stats["nuevos"] += 1
                    except Exception as e:
                        stats["errores"] += 1
            
            return True, f"Procesamiento simulado. {stats['nuevos']} nuevos, {stats['errores']} errores.", stats
            
        except Exception as e:
            return False, f"Error en el procesamiento: {str(e)}", {}

# Funciones estadísticas
def filtrar_outliers_iqr(valores, factor=1.5):
    """Filtra valores atípicos usando IQR"""
    if not valores or len(valores) < 5:
        return valores
    
    valores_arr = np.array(valores)
    q1 = np.percentile(valores_arr, 25)
    q3 = np.percentile(valores_arr, 75)
    iqr = q3 - q1
    
    if iqr == 0:
        return valores
    
    limite_inferior = q1 - (factor * iqr)
    limite_superior = q3 + (factor * iqr)
    
    return valores_arr[(valores_arr >= limite_inferior) & (valores_arr <= limite_superior)].tolist()

def calcular_indice_produccion(cantidad_tallos, area, densidad):
    """Calcula índice de producción"""
    plantas_totales = area * densidad
    if plantas_totales <= 0:
        return 0
    return (cantidad_tallos / plantas_totales) * 100

# Filtro de fecha
def add_date_filter(app):
    """Configura filtros de fecha para la aplicación"""
    @app.template_filter('dateformat')
    def dateformat_filter(date, format='%d-%m-%Y'):
        if date is None:
            return '<span class="badge bg-warning">No disponible</span>'
        return date.strftime(format)
    
    @app.template_filter('dateonly')
    def dateonly_filter(date, format='%d-%m-%Y'):
        if date is None:
            return "No disponible"
        return date.strftime(format)
    
    @app.template_filter('tojson')
    def tojson_filter(obj):
        import json
        
        class DateTimeEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, datetime):
                    return obj.strftime('%Y-%m-%d')
                return super().default(obj)
        
        return json.dumps(obj, cls=DateTimeEncoder, ensure_ascii=False)
    
    return app
