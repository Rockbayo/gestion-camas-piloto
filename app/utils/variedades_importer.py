"""
Módulo para la importación de variedades desde archivos Excel.
"""
import pandas as pd
from app import db
from app.models import Flor, Color, FlorColor, Variedad
from app.utils.base_importer import BaseImporter

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