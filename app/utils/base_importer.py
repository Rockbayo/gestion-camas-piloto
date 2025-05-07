"""
Módulo para la importación de bloques, camas y lados desde archivos Excel.
"""
import pandas as pd
from app import db
from app.models import Bloque, Cama, Lado, BloqueCamaLado
from app.utils.base_importer import BaseImporter

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