"""
Módulo unificado para la importación de datasets en la aplicación.
Proporciona utilidades para importar diferentes tipos de datos (variedades, bloques, áreas, densidades)
"""
import pandas as pd
import os
import json
from flask import current_app, session
from app import db  # Import the database object
from werkzeug.utils import secure_filename
import uuid

from app.models import (
    Flor, Color, FlorColor, Variedad,
    Bloque, Cama, Lado, BloqueCamaLado,
    Area, Densidad, Causa
)

# Configuración de directorios
TEMP_DIR = os.path.join('uploads', 'temp')
os.makedirs(TEMP_DIR, exist_ok=True)

class DatasetImporter:
    """Clase para manejar la importación de diferentes tipos de datasets"""
    
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
    def process_dataset(file_path, dataset_type, column_mapping=None, validate_only=False, skip_first_row=True):
        """
        Procesa un dataset según su tipo.
        
        Args:
            - file_path: Ruta del archivo Excel
            - dataset_type: Tipo de dataset ('variedades', 'bloques', 'areas', 'densidades', 'causas')
            - column_mapping: Diccionario para mapear columnas personalizadas
            - validate_only: Si es True, sólo valida el dataset sin importar
            - skip_first_row: Si es True, omite la primera fila (encabezados)
            
        Returns:
            - (bool, str, dict): Tupla con estado, mensaje y estadísticas
        """
        processors = {
            'variedades': DatasetImporter.import_variedades,
            'bloques': DatasetImporter.import_bloques_camas,
            'areas': DatasetImporter.import_areas,
            'densidades': DatasetImporter.import_densidades,
            'causas': DatasetImporter.import_causas
        }
        
        processors = {
        'variedades': DatasetImporter.import_variedades,
        'bloques': DatasetImporter.import_bloques_camas,
        'areas': DatasetImporter.import_areas,
        'densidades': DatasetImporter.import_densidades,
        'causas': DatasetImporter.import_causas
    }
    
        if dataset_type in processors:
            if dataset_type == 'causas':
                print(f"Procesando dataset de causas con mapeo: {column_mapping}")
            return processors[dataset_type](
                file_path, column_mapping, validate_only, skip_first_row
            )
        else:
            return False, f"Tipo de dataset no soportado: {dataset_type}", {}
    
    @staticmethod
    def import_variedades(file_path, column_mapping=None, validate_only=False, skip_first_row=True):
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
            # Cargar archivo Excel
            df = pd.read_excel(file_path, header=0 if skip_first_row else None)
            
            # Aplicar mapeo de columnas si se proporciona
            if column_mapping and isinstance(column_mapping, dict):
                df = df.rename(columns=column_mapping)
            
            # Verificar que las columnas requeridas existan
            required_columns = ['FLOR', 'COLOR', 'VARIEDAD']
            
            # Si no tiene encabezados, asignar nombres predeterminados
            if not skip_first_row:
                if len(df.columns) >= 3:
                    df.columns = required_columns + [f'COL{i+4}' for i in range(len(df.columns)-3)]
                else:
                    return False, "El archivo no tiene suficientes columnas", {}
            
            # Convertir columnas a mayúsculas
            df.columns = [col.upper() for col in df.columns]
            
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                return False, f"Faltan columnas requeridas: {', '.join(missing_columns)}", {}
            
            # Verificar valores nulos
            for col in required_columns:
                df[col] = df[col].astype(str).str.strip()
            
            df = df.dropna(subset=required_columns)
            
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
                    print(f"Cambios confirmados: {stats['causas_nuevas']} causas nuevas creadas")
                except Exception as e:
                    db.session.rollback()
                    print(f"Error al confirmar cambios: {str(e)}")
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
    
    @staticmethod
    def import_bloques_camas(file_path, column_mapping=None, validate_only=False, skip_first_row=True):
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
            # Cargar archivo Excel
            df = pd.read_excel(file_path, header=0 if skip_first_row else None)
            
            # Aplicar mapeo de columnas si se proporciona
            if column_mapping and isinstance(column_mapping, dict):
                df = df.rename(columns=column_mapping)
            
            # Verificar que las columnas requeridas existan
            required_columns = ['BLOQUE', 'CAMA']
            optional_columns = ['LADO']
            
            # Si no tiene encabezados, asignar nombres predeterminados
            if not skip_first_row:
                if len(df.columns) >= 2:
                    if len(df.columns) >= 3:
                        df.columns = required_columns + optional_columns + [f'COL{i+4}' for i in range(len(df.columns)-3)]
                    else:
                        df.columns = required_columns + [f'COL{i+3}' for i in range(len(df.columns)-2)]
                else:
                    return False, "El archivo no tiene suficientes columnas", {}
            
            # Convertir columnas a mayúsculas
            df.columns = [col.upper() for col in df.columns]
            
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                return False, f"Faltan columnas requeridas: {', '.join(missing_columns)}", {}
            
            # Verificar valores nulos en columnas requeridas
            df = df.dropna(subset=required_columns)
            
            # Si la columna LADO no existe, crear una con valor predeterminado
            if 'LADO' not in df.columns:
                df['LADO'] = 'ÚNICO'
            
            # Convertir a string y limpiar espacios
            for col in required_columns + optional_columns:
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
    
    @staticmethod
    def import_areas(file_path, column_mapping=None, validate_only=False, skip_first_row=True):
        """
        Importa datos de áreas desde un archivo Excel.
        
        Args:
            - file_path: Ruta del archivo Excel
            - column_mapping: Diccionario para mapear columnas personalizadas a las requeridas
            - validate_only: Si es True, sólo valida el dataset sin importar
            - skip_first_row: Si es True, omite la primera fila (encabezados)
        
        Returns:
            - (bool, str, dict): Tupla con estado, mensaje y estadísticas
        """
        try:
            # Cargar archivo Excel
            df = pd.read_excel(file_path, header=0 if skip_first_row else None)
            
            # Aplicar mapeo de columnas si se proporciona
            if column_mapping and isinstance(column_mapping, dict):
                df = df.rename(columns=column_mapping)
            
            # Verificar que las columnas requeridas existan
            required_columns = ['SIEMBRA', 'AREA']
            
            # Si no tiene encabezados, asignar nombres predeterminados
            if not skip_first_row:
                if len(df.columns) >= 2:
                    df.columns = required_columns + [f'COL{i+3}' for i in range(len(df.columns)-2)]
                else:
                    return False, "El archivo no tiene suficientes columnas", {}
            
            # Convertir columnas a mayúsculas
            df.columns = [col.upper() for col in df.columns]
            
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                return False, f"Faltan columnas requeridas: {', '.join(missing_columns)}", {}
            
            # Verificar valores nulos
            df = df.dropna(subset=required_columns)
            
            # Convertir columnas
            df['SIEMBRA'] = df['SIEMBRA'].astype(str).str.strip().str.upper()
            # Asegurar que la columna AREA sea numérica
            try:
                df['AREA'] = pd.to_numeric(df['AREA'])
            except:
                return False, "La columna AREA debe contener valores numéricos.", {}
            
            # Si es sólo validación, retornar aquí
            if validate_only:
                return True, "Dataset validado correctamente. Listo para importar.", {
                    "total_rows": len(df),
                    "valid_rows": len(df)
                }
            
            # Contadores para estadísticas
            stats = {
                'areas_nuevas': 0,
                'areas_actualizadas': 0,
                'errores': 0,
                'filas_procesadas': 0
            }
            
            # Listas para seguimiento de errores
            error_rows = []
            
            # Procesar cada fila
            for index, row in df.iterrows():
                try:
                    stats['filas_procesadas'] += 1
                    siembra_nombre = row['SIEMBRA']
                    area_valor = float(row['AREA'])
                    
                    # Verificar que el área sea mayor que cero
                    if area_valor <= 0:
                        error_rows.append({
                            'row': index + 2,
                            'error': 'El valor del área debe ser mayor que cero'
                        })
                        stats['errores'] += 1
                        continue
                    
                    # Buscar o crear área
                    area = Area.query.filter_by(siembra=siembra_nombre).first()
                    if not area:
                        area = Area(siembra=siembra_nombre, area=area_valor)
                        db.session.add(area)
                        stats['areas_nuevas'] += 1
                    else:
                        # Actualizar área existente
                        area.area = area_valor
                        stats['areas_actualizadas'] += 1
                    
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
                f"Importación completada: {stats['areas_nuevas']} áreas nuevas, "
                f"{stats['areas_actualizadas']} áreas actualizadas."
            )
            
            if stats['errores'] > 0:
                message += f" Se encontraron {stats['errores']} errores durante la importación."
            
            return True, message, stats
        
        except Exception as e:
            db.session.rollback()
            return False, f"Error durante la importación: {str(e)}", {}
    
    @staticmethod
    def import_densidades(file_path, column_mapping=None, validate_only=False, skip_first_row=True):
        """
        Importa datos de densidades desde un archivo Excel.
        
        Args:
            - file_path: Ruta del archivo Excel
            - column_mapping: Diccionario para mapear columnas personalizadas a las requeridas
            - validate_only: Si es True, sólo valida el dataset sin importar
            - skip_first_row: Si es True, omite la primera fila (encabezados)
        
        Returns:
            - (bool, str, dict): Tupla con estado, mensaje y estadísticas
        """
        try:
            # Cargar archivo Excel
            df = pd.read_excel(file_path, header=0 if skip_first_row else None)
            
            # Aplicar mapeo de columnas si se proporciona
            if column_mapping and isinstance(column_mapping, dict):
                df = df.rename(columns=column_mapping)
            
            # Verificar que las columnas requeridas existan
            required_columns = ['DENSIDAD']
            
            # Si no tiene encabezados, asignar nombres predeterminados
            if not skip_first_row:
                if len(df.columns) >= 1:
                    df.columns = required_columns + [f'COL{i+2}' for i in range(len(df.columns)-1)]
                else:
                    return False, "El archivo no tiene columnas", {}
            
            # Convertir columnas a mayúsculas
            df.columns = [col.upper() for col in df.columns]
            
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                return False, f"Faltan columnas requeridas: {', '.join(missing_columns)}", {}
            
            # Verificar valores nulos
            df = df.dropna(subset=required_columns)
            
            # Convertir columnas
            df['DENSIDAD'] = df['DENSIDAD'].astype(str).str.strip().str.upper()
            
            # Si es sólo validación, retornar aquí
            if validate_only:
                return True, "Dataset validado correctamente. Listo para importar.", {
                    "total_rows": len(df),
                    "valid_rows": len(df)
                }
            
            # Contadores para estadísticas
            stats = {
                'densidades_nuevas': 0,
                'densidades_existentes': 0,
                'errores': 0,
                'filas_procesadas': 0
            }
            
            # Listas para seguimiento de errores
            error_rows = []
            
            # Procesar cada fila
            for index, row in df.iterrows():
                try:
                    stats['filas_procesadas'] += 1
                    densidad_nombre = row['DENSIDAD']
                    
                    # Buscar o crear densidad
                    densidad = Densidad.query.filter_by(densidad=densidad_nombre).first()
                    if not densidad:
                        densidad = Densidad(densidad=densidad_nombre)
                        db.session.add(densidad)
                        stats['densidades_nuevas'] += 1
                    else:
                        stats['densidades_existentes'] += 1
                    
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
                f"Importación completada: {stats['densidades_nuevas']} densidades nuevas creadas."
            )
            
            if stats['errores'] > 0:
                message += f" Se encontraron {stats['errores']} errores durante la importación."
            
            return True, message, stats
        
        except Exception as e:
            db.session.rollback()
            return False, f"Error durante la importación: {str(e)}", {}
        
    @staticmethod
    def import_causas(file_path, column_mapping=None, validate_only=False, skip_first_row=True):
        """
        Importa datos de causas de pérdida desde un archivo Excel.
        
        Args:
            - file_path: Ruta del archivo Excel
            - column_mapping: Diccionario para mapear columnas personalizadas a las requeridas
            - validate_only: Si es True, sólo valida el dataset sin importar
            - skip_first_row: Si es True, omite la primera fila (encabezados)
        
        Returns:
            - (bool, str, dict): Tupla con estado, mensaje y estadísticas
        """
        try:
            # Cargar archivo Excel
            df = pd.read_excel(file_path, header=0 if skip_first_row else None)
            
            # Aplicar mapeo de columnas si se proporciona
            if column_mapping and isinstance(column_mapping, dict):
                df = df.rename(columns=column_mapping)
            
            # Verificar que las columnas requeridas existan
            required_columns = ['CAUSA']
            
            # Si no tiene encabezados, asignar nombres predeterminados
            if not skip_first_row:
                if len(df.columns) >= 1:
                    df.columns = required_columns + [f'COL{i+2}' for i in range(len(df.columns)-1)]
                else:
                    return False, "El archivo no tiene columnas", {}
            
            # Convertir columnas a mayúsculas
            df.columns = [col.upper() for col in df.columns]
            
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                return False, f"Faltan columnas requeridas: {', '.join(missing_columns)}", {}
            
            # Verificar valores nulos
            df = df.dropna(subset=required_columns)
            
            # Convertir columnas
            df['CAUSA'] = df['CAUSA'].astype(str).str.strip().str.upper()
            
            # Si es sólo validación, retornar aquí
            if validate_only:
                return True, "Dataset validado correctamente. Listo para importar.", {
                    "total_rows": len(df),
                    "valid_rows": len(df)
                }
            
            # Contadores para estadísticas
            stats = {
                'causas_nuevas': 0,
                'causas_existentes': 0,
                'errores': 0,
                'filas_procesadas': 0
            }
            
            # Listas para seguimiento de errores
            error_rows = []
            
            # Procesar cada fila
            for index, row in df.iterrows():
                try:
                    stats['filas_procesadas'] += 1
                    causa_nombre = row['CAUSA']
                    
                    # Añadir depuración
                    print(f"Procesando fila {index+2}: Causa='{causa_nombre}'")
                    
                    # Buscar o crear causa
                    causa = Causa.query.filter_by(causa=causa_nombre).first()
                    if not causa:
                        print(f"  -> Creando nueva causa: '{causa_nombre}'")
                    else:
                        print(f"  -> Causa ya existente: '{causa_nombre}'")
                    
                    if not causa:
                        causa = Causa(causa=causa_nombre)
                        db.session.add(causa)
                        stats['causas_nuevas'] += 1
                    else:
                        stats['causas_existentes'] += 1
                    
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
                    print(f"Cambios confirmados: {stats['causas_nuevas']} causas nuevas creadas")
                except Exception as e:
                    db.session.rollback()
                    print(f"Error al confirmar cambios: {str(e)}")
                    return False, f"Error al guardar en la base de datos: {str(e)}", stats
            else:
                db.session.rollback()
                return False, "Demasiados errores durante la importación. No se importaron datos.", stats
            
            # Añadir errores a las estadísticas
            stats['error_details'] = error_rows
            
            message = f"Importación completada: {stats['causas_nuevas']} causas nuevas creadas."
            
            if stats['errores'] > 0:
                message += f" Se encontraron {stats['errores']} errores durante la importación."
            
            return True, message, stats
            
        except Exception as e:
            return False, f"Error general durante la importación: {str(e)}", {}