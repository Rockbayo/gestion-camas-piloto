# app/utils/causas_importer.py
import os
import pandas as pd
import uuid
from werkzeug.utils import secure_filename
from app import db
from app.models import Causa

class CausasImporter:
    """Módulo dedicado exclusivamente a la importación de causas de pérdida"""
    
    TEMP_DIR = os.path.join('uploads', 'temp')
    
    @classmethod
    def importar(cls, archivo, omitir_primera_fila=True):
        """
        Importa causas desde un archivo Excel
        
        Args:
            archivo: Objeto archivo de Flask
            omitir_primera_fila: Si debe omitir la primera fila como encabezado
            
        Returns:
            dict: Resultados de la importación
        """
        # Preparar directorio temporal
        os.makedirs(cls.TEMP_DIR, exist_ok=True)
        
        # Guardar archivo con nombre único
        filename = f"{uuid.uuid4()}_{secure_filename(archivo.filename)}"
        filepath = os.path.join(cls.TEMP_DIR, filename)
        archivo.save(filepath)
        
        # Resultados de la operación
        resultados = {
            'exito': False,
            'mensaje': '',
            'nuevas': 0,
            'existentes': 0,
            'errores': 0
        }
        
        try:
            # Cargar archivo Excel
            df = pd.read_excel(filepath, header=0 if omitir_primera_fila else None)
            
            # Determinar la columna de causas
            columna_causa = cls._identificar_columna_causa(df)
            
            if not columna_causa:
                resultados['mensaje'] = "No se pudo identificar una columna de causas en el archivo"
                return resultados
            
            # Procesamiento de los datos
            df[columna_causa] = df[columna_causa].astype(str).str.strip().str.upper()
            df = df[df[columna_causa].str.len() > 0]
            
            # Importar causas
            for _, row in df.iterrows():
                try:
                    nombre_causa = row[columna_causa]
                    
                    # Verificar si ya existe (case insensitive)
                    causa_existente = Causa.query.filter(Causa.causa.ilike(nombre_causa)).first()
                    
                    if causa_existente:
                        resultados['existentes'] += 1
                    else:
                        # Crear nueva causa
                        nueva_causa = Causa(causa=nombre_causa)
                        db.session.add(nueva_causa)
                        resultados['nuevas'] += 1
                
                except Exception:
                    resultados['errores'] += 1
            
            # Confirmar cambios si hay causas nuevas
            if resultados['nuevas'] > 0:
                db.session.commit()
                resultados['exito'] = True
                resultados['mensaje'] = f"Se importaron {resultados['nuevas']} nuevas causas"
                if resultados['existentes'] > 0:
                    resultados['mensaje'] += f" (se ignoraron {resultados['existentes']} ya existentes)"
            else:
                if resultados['existentes'] > 0 and resultados['errores'] == 0:
                    resultados['exito'] = True
                    resultados['mensaje'] = f"No se importaron nuevas causas. Las {resultados['existentes']} causas del archivo ya existen en el sistema."
                else:
                    resultados['mensaje'] = "No se pudieron importar causas"
            
        except Exception as e:
            db.session.rollback()
            resultados['mensaje'] = f"Error durante la importación: {str(e)}"
        
        finally:
            # Limpiar archivo temporal
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except:
                    pass
        
        return resultados
    
    @staticmethod
    def _identificar_columna_causa(df):
        """Identifica la columna que contiene las causas en el DataFrame"""
        # Buscar columna con términos relevantes
        for col in df.columns:
            col_str = str(col).lower()
            if 'causa' in col_str or 'perdida' in col_str or 'pérdida' in col_str:
                return col
        
        # Si no encontró, usar la primera columna
        if len(df.columns) > 0:
            return df.columns[0]
        
        return None