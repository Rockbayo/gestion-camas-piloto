"""
M�dulo consolidado de importadores
"""
import os
import pandas as pd
import uuid
from werkzeug.utils import secure_filename
from app import db
from app.models import *

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

class VariedadesImporter(BaseImporter):
    """Clase para manejar la importación de variedades."""
    
    REQUIRED_COLUMNS = ['FLOR', 'COLOR', 'VARIEDAD']
    
    @classmethod
    def import_variedades(cls, file_path, column_mapping=None, validate_only=False, skip_first_row=True):
        """
        Importa variedades desde un archivo Excel.
        
        Args:
            - file_path: Ruta del archivo Excel
            - column_mapping: Diccionario para mapear columnas personalizadas a las requeridas
            - validate_only: Si es True, sólo valida el dataset sin importar
            - skip_first_row: Si es True, omite la primera fila (encabezados)
        
        Returns:
            - (bool, str, dict): Tupla con estado, mensaje y estadísticas
        """
        try:
            # Preparar DataFrame
            df, message, success = cls.prepare_dataframe(
                file_path, 
                column_mapping, 
                skip_first_row,
                cls.REQUIRED_COLUMNS
            )
            
            if not success:
                return False, message, {}
            
            # Verificar valores nulos
            for col in cls.REQUIRED_COLUMNS:
                df[col] = df[col].astype(str).str.strip()
            
            df = df.dropna(subset=cls.REQUIRED_COLUMNS)
            
            # Si es sólo validación, retornar aquí
            if validate_only:
                return True, "Dataset validado correctamente. Listo para importar.", {
                    "total_rows": len(df),
                    "valid_rows": len(df)
                }
            
            # Contadores para estadísticas
            stats = {
                'flores_nuevas': 0,
                'flores_existentes': 0,
                'colores_nuevos': 0,
                'colores_existentes': 0,
                'combinaciones_nuevas': 0,
                'combinaciones_existentes': 0,
                'variedades_nuevas': 0,
                'variedades_existentes': 0,
                'errores': 0,
                'filas_procesadas': 0
            }
            
            # Listas para seguimiento de errores
            error_rows = []
            
            # Procesar cada fila
            for index, row in df.iterrows():
                try:
                    stats['filas_procesadas'] += 1
                    flor_nombre = row['FLOR'].strip().upper()
                    color_nombre = row['COLOR'].strip().upper()
                    variedad_nombre = row['VARIEDAD'].strip().upper()
                    
                    # Verificar que todos los campos tengan valores
                    if not all([flor_nombre, color_nombre, variedad_nombre]):
                        error_rows.append({
                            'row': index + 2,  # +2 porque Excel comienza en 1 y tiene encabezados
                            'error': 'Valores faltantes en la fila'
                        })
                        stats['errores'] += 1
                        continue
                    
                    # Buscar o crear flor
                    flor = Flor.query.filter_by(flor=flor_nombre).first()
                    if not flor:
                        flor = Flor(flor=flor_nombre, flor_abrev=flor_nombre[:10])
                        db.session.add(flor)
                        db.session.flush()  # Para obtener el ID
                        stats['flores_nuevas'] += 1
                    else:
                        stats['flores_existentes'] += 1
                    
                    # Buscar o crear color
                    color = Color.query.filter_by(color=color_nombre).first()
                    if not color:
                        color = Color(color=color_nombre, color_abrev=color_nombre[:10])
                        db.session.add(color)
                        db.session.flush()  # Para obtener el ID
                        stats['colores_nuevos'] += 1
                    else:
                        stats['colores_existentes'] += 1
                    
                    # Buscar o crear combinación flor-color
                    flor_color = FlorColor.query.filter_by(
                        flor_id=flor.flor_id, 
                        color_id=color.color_id
                    ).first()
                    
                    if not flor_color:
                        flor_color = FlorColor(flor_id=flor.flor_id, color_id=color.color_id)
                        db.session.add(flor_color)
                        db.session.flush()  # Para obtener el ID
                        stats['combinaciones_nuevas'] += 1
                    else:
                        stats['combinaciones_existentes'] += 1
                    
                    # Buscar o crear variedad
                    variedad = Variedad.query.filter_by(variedad=variedad_nombre).first()
                    if not variedad:
                        variedad = Variedad(
                            variedad=variedad_nombre,
                            flor_color_id=flor_color.flor_color_id
                        )
                        db.session.add(variedad)
                        stats['variedades_nuevas'] += 1
                    else:
                        stats['variedades_existentes'] += 1
                
                except Exception as e:
                    error_rows.append({
                        'row': index + 2,
                        'error': str(e)
                    })
                    stats['errores'] += 1
                    continue
            
            # Confirmar cambios si no hay errores graves
            if stats['errores'] == 0 or stats['filas_procesadas'] > stats['errores']:
                try:
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    return False, f"Error al guardar en la base de datos: {str(e)}", stats
            else:
                db.session.rollback()
                return False, "Demasiados errores durante la importación. No se importaron datos.", stats
                        
            # Añadir errores a las estadísticas
            stats['error_details'] = error_rows
            
            message = (
                f"Importación completada: {stats['flores_nuevas']} flores nuevas, "
                f"{stats['colores_nuevos']} colores nuevos, "
                f"{stats['combinaciones_nuevas']} combinaciones nuevas, "
                f"{stats['variedades_nuevas']} variedades nuevas. "
            )
            
            if stats['errores'] > 0:
                message += f"Se encontraron {stats['errores']} errores durante la importación."
            
            return True, message, stats
        
        except Exception as e:
            db.session.rollback()
            return False, f"Error durante la importación: {str(e)}", {}

class BloquesImporter(BaseImporter):
    """Clase para manejar la importación de bloques, camas y lados."""
    
    REQUIRED_COLUMNS = ['BLOQUE', 'CAMA']
    OPTIONAL_COLUMNS = ['LADO']
    
    @classmethod
    def import_bloques_camas(cls, file_path, column_mapping=None, validate_only=False, skip_first_row=True):
        """
        Importa datos de bloques, camas y lados desde un archivo Excel.
        
        Args:
            - file_path: Ruta del archivo Excel
            - column_mapping: Diccionario para mapear columnas personalizadas a las requeridas
            - validate_only: Si es True, sólo valida el dataset sin importar
            - skip_first_row: Si es True, omite la primera fila (encabezados)
        
        Returns:
            - (bool, str, dict): Tupla con estado, mensaje y estadísticas
        """
        try:
            # Preparar DataFrame
            df, message, success = cls.prepare_dataframe(
                file_path, 
                column_mapping, 
                skip_first_row,
                cls.REQUIRED_COLUMNS
            )
            
            if not success:
                return False, message, {}
            
            # Verificar valores nulos en columnas requeridas
            df = df.dropna(subset=cls.REQUIRED_COLUMNS)
            
            # Si la columna LADO no existe, crear una con valor predeterminado
            if 'LADO' not in df.columns:
                df['LADO'] = 'ÚNICO'
            
            # Convertir a string y limpiar espacios
            for col in cls.REQUIRED_COLUMNS + cls.OPTIONAL_COLUMNS:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.strip().str.upper()
            
            # Si es sólo validación, retornar aquí
            if validate_only:
                return True, "Dataset validado correctamente. Listo para importar.", {
                    "total_rows": len(df),
                    "valid_rows": len(df)
                }
            
            # Contadores para estadísticas
            stats = {
                'bloques_nuevos': 0,
                'bloques_existentes': 0,
                'camas_nuevas': 0,
                'camas_existentes': 0,
                'lados_nuevos': 0,
                'lados_existentes': 0,
                'combinaciones_nuevas': 0,
                'combinaciones_existentes': 0,
                'errores': 0,
                'filas_procesadas': 0
            }
            
            # Listas para seguimiento de errores
            error_rows = []
            
            # Procesar cada fila
            for index, row in df.iterrows():
                try:
                    stats['filas_procesadas'] += 1
                    bloque_nombre = row['BLOQUE']
                    cama_nombre = row['CAMA']
                    lado_nombre = row['LADO']
                    
                    # Buscar o crear bloque
                    bloque = Bloque.query.filter_by(bloque=bloque_nombre).first()
                    if not bloque:
                        bloque = Bloque(bloque=bloque_nombre)
                        db.session.add(bloque)
                        db.session.flush()  # Para obtener el ID
                        stats['bloques_nuevos'] += 1
                    else:
                        stats['bloques_existentes'] += 1
                    
                    # Buscar o crear cama
                    cama = Cama.query.filter_by(cama=cama_nombre).first()
                    if not cama:
                        cama = Cama(cama=cama_nombre)
                        db.session.add(cama)
                        db.session.flush()  # Para obtener el ID
                        stats['camas_nuevas'] += 1
                    else:
                        stats['camas_existentes'] += 1
                    
                    # Buscar o crear lado
                    lado = Lado.query.filter_by(lado=lado_nombre).first()
                    if not lado:
                        lado = Lado(lado=lado_nombre)
                        db.session.add(lado)
                        db.session.flush()  # Para obtener el ID
                        stats['lados_nuevos'] += 1
                    else:
                        stats['lados_existentes'] += 1
                    
                    # Buscar o crear combinación bloque-cama-lado
                    bloque_cama_lado = BloqueCamaLado.query.filter_by(
                        bloque_id=bloque.bloque_id,
                        cama_id=cama.cama_id,
                        lado_id=lado.lado_id
                    ).first()
                    
                    if not bloque_cama_lado:
                        bloque_cama_lado = BloqueCamaLado(
                            bloque_id=bloque.bloque_id,
                            cama_id=cama.cama_id,
                            lado_id=lado.lado_id
                        )
                        db.session.add(bloque_cama_lado)
                        stats['combinaciones_nuevas'] += 1
                    else:
                        stats['combinaciones_existentes'] += 1
                    
                except Exception as e:
                    error_rows.append({
                        'row': index + 2,
                        'error': str(e)
                    })
                    stats['errores'] += 1
                    continue
            
            # Confirmar cambios si no hay errores graves
            if stats['errores'] == 0 or stats['filas_procesadas'] > stats['errores']:
                db.session.commit()
            else:
                db.session.rollback()
                return False, "Demasiados errores durante la importación. No se importaron datos.", stats
            
            # Añadir errores a las estadísticas
            stats['error_details'] = error_rows
            
            message = (
                f"Importación completada: {stats['bloques_nuevos']} bloques nuevos, "
                f"{stats['camas_nuevas']} camas nuevas, "
                f"{stats['lados_nuevos']} lados nuevos, "
                f"{stats['combinaciones_nuevas']} ubicaciones nuevas. "
            )
            
            if stats['errores'] > 0:
                message += f"Se encontraron {stats['errores']} errores durante la importación."
            
            return True, message, stats
        
        except Exception as e:
            db.session.rollback()
            return False, f"Error durante la importación: {str(e)}", {}

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

