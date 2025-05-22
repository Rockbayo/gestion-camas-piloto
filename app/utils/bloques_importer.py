"""
Módulo para importación de bloques, camas y lados desde archivos Excel.

Mejoras:
- Conserva el formato numérico con ceros a la izquierda
- Mejor ordenamiento en consultas
- Manejo más robusto de transacciones
- Estadísticas más detalladas
"""

from typing import Dict, Tuple, Optional, Any
import pandas as pd
from app import db
from app.models import Bloque, Cama, Lado, BloqueCamaLado
from app.utils.base_importer import BaseImporter

class BloquesImporter(BaseImporter):
    """
    Importador específico para datos de bloques, camas y lados.
    Conserva formatos numéricos con ceros a la izquierda.
    """
    
    REQUIRED_COLUMNS = ['BLOQUE', 'CAMA']
    OPTIONAL_COLUMNS = ['LADO']
    DEFAULT_LADO = 'ÚNICO'
    
    @classmethod
    def import_bloques_camas(
        cls,
        file_path: str,
        column_mapping: Optional[Dict[str, str]] = None,
        validate_only: bool = False,
        skip_first_row: bool = True
    ) -> Tuple[bool, str, Dict]:
        """
        Importa datos de bloques, camas y lados desde un archivo.
        
        Args:
            file_path: Ruta del archivo a importar
            column_mapping: Mapeo de columnas personalizado
            validate_only: Solo validar sin importar
            skip_first_row: Saltar primera fila
            
        Returns:
            Tuple: (éxito, mensaje, estadísticas)
        """
        try:
            # Preparar DataFrame con manejo especial para formatos numéricos
            df, message, success = cls.prepare_dataframe_with_format_preservation(
                file_path=file_path,
                column_mapping=column_mapping,
                skip_first_row=skip_first_row,
                required_columns=cls.REQUIRED_COLUMNS
            )
            if not success:
                return False, message, {}
            
            # Limpiar y preparar datos conservando formatos
            df = cls.clean_dataframe_preserve_format(df)
            
            if validate_only:
                return True, "Dataset validado correctamente", {
                    "total_rows": len(df),
                    "valid_rows": len(df)
                }
            
            # Procesar importación
            stats = cls.initialize_stats()
            error_details = []
            
            with db.session.begin_nested():
                for index, row in df.iterrows():
                    try:
                        cls.process_row(row, stats)
                    except Exception as e:
                        error_details.append(cls.build_error_record(index, row, e))
                        stats['errores'] += 1
            
            # Confirmar o revertir según resultados
            return cls.finalize_import(stats, error_details)
            
        except Exception as e:
            db.session.rollback()
            return False, f"Error durante la importación: {str(e)}", {}
    
    @classmethod
    def prepare_dataframe_with_format_preservation(
        cls,
        file_path: str,
        column_mapping: Optional[Dict[str, str]] = None,
        skip_first_row: bool = True,
        required_columns: Optional[list] = None
    ) -> Tuple[pd.DataFrame, str, bool]:
        """
        Prepara un DataFrame conservando el formato de texto de las columnas numéricas.
        """
        try:
            # Leer archivo preservando el formato como texto
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path, dtype=str)
            else:
                # Para Excel, leer como string para preservar ceros a la izquierda
                df = pd.read_excel(file_path, dtype=str)
            
            # Aplicar transformaciones básicas
            if column_mapping:
                df = df.rename(columns=column_mapping)
            if skip_first_row and len(df) > 1:
                df = df.iloc[1:].reset_index(drop=True)
            
            # Validar columnas requeridas
            if required_columns:
                missing = [col for col in required_columns if col not in df.columns]
                if missing:
                    return None, f"Columnas requeridas faltantes: {', '.join(missing)}", False
            
            return df, "DataFrame preparado correctamente conservando formatos", True
            
        except Exception as e:
            return None, f"Error al preparar DataFrame: {str(e)}", False
    
    @classmethod
    def clean_dataframe_preserve_format(cls, df: pd.DataFrame) -> pd.DataFrame:
        """
        Limpia el DataFrame conservando el formato numérico con ceros a la izquierda.
        """
        # Manejar valores nulos
        df = df.dropna(subset=cls.REQUIRED_COLUMNS)
        
        # Asegurar columna LADO
        if 'LADO' not in df.columns:
            df['LADO'] = cls.DEFAULT_LADO
        
        # Limpiar strings pero conservar formato numérico
        for col in cls.REQUIRED_COLUMNS + cls.OPTIONAL_COLUMNS:
            if col in df.columns:
                # Para BLOQUE y CAMA, conservar el formato pero limpiar espacios
                if col in ['BLOQUE', 'CAMA']:
                    df[col] = df[col].astype(str).str.strip()
                else:
                    # Para otros campos (como LADO), aplicar mayúsculas
                    df[col] = df[col].astype(str).str.strip().str.upper()
        
        return df
    
    @classmethod
    def initialize_stats(cls) -> Dict[str, Any]:
        """Inicializa el diccionario de estadísticas."""
        return {
            'bloques': {'nuevos': 0, 'existentes': 0},
            'camas': {'nuevas': 0, 'existentes': 0},
            'lados': {'nuevos': 0, 'existentes': 0},
            'combinaciones': {'nuevas': 0, 'existentes': 0},
            'errores': 0,
            'filas_procesadas': 0
        }
    
    @classmethod
    def process_row(cls, row: pd.Series, stats: Dict[str, Any]) -> None:
        """Procesa una fila individual del dataset."""
        stats['filas_procesadas'] += 1
        
        bloque = cls.get_or_create_bloque(row['BLOQUE'], stats)
        cama = cls.get_or_create_cama(row['CAMA'], stats)
        lado = cls.get_or_create_lado(row['LADO'], stats)
        
        cls.create_block_bed_side_relation(bloque, cama, lado, stats)
    
    @classmethod
    def get_or_create_bloque(cls, nombre: str, stats: Dict[str, Any]) -> Bloque:
        """Obtiene o crea un bloque conservando el formato numérico."""
        bloque = Bloque.query.filter_by(bloque=nombre).first()
        if not bloque:
            bloque = Bloque(bloque=nombre)
            db.session.add(bloque)
            stats['bloques']['nuevos'] += 1
        else:
            stats['bloques']['existentes'] += 1
        return bloque
    
    @classmethod
    def get_or_create_cama(cls, nombre: str, stats: Dict[str, Any]) -> Cama:
        """Obtiene o crea una cama conservando el formato numérico."""
        cama = Cama.query.filter_by(cama=nombre).first()
        if not cama:
            cama = Cama(cama=nombre)
            db.session.add(cama)
            stats['camas']['nuevas'] += 1
        else:
            stats['camas']['existentes'] += 1
        return cama
    
    @classmethod
    def get_or_create_lado(cls, nombre: str, stats: Dict[str, Any]) -> Lado:
        """Obtiene o crea un lado."""
        lado = Lado.query.filter_by(lado=nombre).first()
        if not lado:
            lado = Lado(lado=nombre)
            db.session.add(lado)
            stats['lados']['nuevos'] += 1
        else:
            stats['lados']['existentes'] += 1
        return lado
    
    @classmethod
    def create_block_bed_side_relation(
        cls,
        bloque: Bloque,
        cama: Cama,
        lado: Lado,
        stats: Dict[str, Any]
    ) -> None:
        """Crea la relación bloque-cama-lado si no existe."""
        relation = BloqueCamaLado.query.filter_by(
            bloque_id=bloque.bloque_id,
            cama_id=cama.cama_id,
            lado_id=lado.lado_id
        ).first()
        
        if not relation:
            relation = BloqueCamaLado(
                bloque_id=bloque.bloque_id,
                cama_id=cama.cama_id,
                lado_id=lado.lado_id
            )
            db.session.add(relation)
            stats['combinaciones']['nuevas'] += 1
        else:
            stats['combinaciones']['existentes'] += 1
    
    @classmethod
    def build_error_record(cls, index: int, row: pd.Series, error: Exception) -> Dict:
        """Construye un registro de error detallado."""
        return {
            'row': index + 2,  # +2 para compensar encabezado y base 1
            'error': str(error),
            'data': {
                'bloque': row.get('BLOQUE'),
                'cama': row.get('CAMA'),
                'lado': row.get('LADO', cls.DEFAULT_LADO)
            }
        }
    
    @classmethod
    def finalize_import(cls, stats: Dict[str, Any], error_details: list) -> Tuple[bool, str, Dict]:
        """Finaliza el proceso de importación."""
        stats['error_details'] = error_details
        
        if stats['errores'] > 0 and stats['errores'] == stats['filas_procesadas']:
            db.session.rollback()
            return False, "Todos los registros tenían errores. No se importaron datos.", stats
        
        db.session.commit()
        
        message = cls.generate_summary_message(stats)
        return True, message, stats
    
    @classmethod
    def generate_summary_message(cls, stats: Dict[str, Any]) -> str:
        """Genera un mensaje de resumen de la importación."""
        parts = [
            f"Bloques nuevos: {stats['bloques']['nuevos']}",
            f"Camas nuevas: {stats['camas']['nuevas']}",
            f"Lados nuevos: {stats['lados']['nuevos']}",
            f"Combinaciones nuevas: {stats['combinaciones']['nuevas']}"
        ]
        
        if stats['errores'] > 0:
            parts.append(f"Errores: {stats['errores']}")
        
        return "Importación completada. " + ", ".join(parts) + "."