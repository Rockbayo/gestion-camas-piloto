# app/utils/import_data.py
import pandas as pd
import os
from app import db
from app.models import Flor, Color, FlorColor, Variedad

def validate_dataset(df):
    """
    Valida que el dataset tenga la estructura adecuada.
    
    Retorna:
        - (bool, str): Tupla con estado de validación y mensaje
    """
    # Verificar columnas requeridas
    required_columns = ['FLOR', 'COLOR', 'VARIEDAD']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        return False, f"Faltan columnas requeridas: {', '.join(missing_columns)}"
    
    # Verificar valores nulos
    null_counts = df[required_columns].isnull().sum()
    if null_counts.sum() > 0:
        null_details = ', '.join([f"{col}: {count}" for col, count in null_counts.items() if count > 0])
        return False, f"El dataset contiene valores nulos: {null_details}"
    
    # Verificar valores duplicados
    duplicates = df.duplicated(subset=['FLOR', 'COLOR', 'VARIEDAD']).sum()
    if duplicates > 0:
        return False, f"El dataset contiene {duplicates} registros duplicados."
    
    return True, "El dataset es válido para importación."

def preview_dataset(file_path, rows=10):
    """
    Genera una vista previa del dataset.
    
    Args:
        - file_path: Ruta del archivo Excel
        - rows: Número de filas para mostrar en la vista previa
    
    Retorna:
        - (bool, dict): Tupla con estado y datos de la vista previa
    """
    try:
        df = pd.read_excel(file_path)
        
        # Verificar que el dataset tenga datos
        if df.empty:
            return False, {"error": "El archivo no contiene datos."}
        
        # Obtener información general del dataset
        info = {
            "total_rows": len(df),
            "columns": list(df.columns),
            "preview_data": df.head(rows).to_dict(orient='records'),
        }
        
        # Validar el dataset
        is_valid, message = validate_dataset(df)
        info["validation"] = {
            "is_valid": is_valid,
            "message": message
        }
        
        return True, info
        
    except Exception as e:
        return False, {"error": str(e)}

def import_variedades_from_excel(file_path, column_mapping=None, validate_only=False):
    """
    Importa variedades desde un archivo Excel con más opciones.
    
    Args:
        - file_path: Ruta del archivo Excel
        - column_mapping: Diccionario para mapear columnas personalizadas a las requeridas
        - validate_only: Si es True, sólo valida el dataset sin importar
    
    Retorna:
        - (bool, str, dict): Tupla con estado, mensaje y estadísticas
    """
    try:
        # Cargar archivo Excel
        df = pd.read_excel(file_path)
        
        # Aplicar mapeo de columnas si se proporciona
        if column_mapping and isinstance(column_mapping, dict):
            df = df.rename(columns=column_mapping)
        
        # Validar estructura del dataset
        is_valid, message = validate_dataset(df)
        if not is_valid:
            return False, message, {}
        
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
                flor_nombre = row['FLOR'].strip()
                color_nombre = row['COLOR'].strip()
                variedad_nombre = row['VARIEDAD'].strip()
                
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
        
        # Confirmar cambios si no hay errores
        if stats['errores'] == 0:
            db.session.commit()
        else:
            # Si hay errores, decidir si hacer commit o rollback
            if stats['filas_procesadas'] > stats['errores']:
                db.session.commit()
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