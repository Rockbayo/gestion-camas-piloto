"""
Módulo para la importación de variedades desde archivos Excel.

Mejoras:
- Mejor separación de responsabilidades
- Manejo más robusto de transacciones
- Mejor reporting de errores
"""

import pandas as pd
from typing import Tuple, Dict, List
from app import db
from app.models import Flor, Color, FlorColor, Variedad
from app.utils.base_importer import BaseImporter

class VariedadesImporter(BaseImporter):
    """
    Importador específico para datos de variedades de flores.
    """
    
    REQUIRED_COLUMNS = ['FLOR', 'COLOR', 'VARIEDAD']
    
    @classmethod
    def import_variedades(
        cls,
        file_path: str,
        column_mapping: Dict[str, str] = None,
        validate_only: bool = False,
        skip_first_row: bool = True
    ) -> Tuple[bool, str, Dict]:
        """
        Importa variedades desde un archivo Excel.
        
        Args:
            file_path: Ruta del archivo Excel
            column_mapping: Mapeo de columnas personalizado
            validate_only: Solo validar sin importar
            skip_first_row: Saltar primera fila
            
        Returns:
            Tuple: (success, message, stats)
        """
        # Preparar DataFrame
        df, message, success = cls.prepare_dataframe(
            file_path, column_mapping, skip_first_row, cls.REQUIRED_COLUMNS
        )
        if not success:
            return False, message, {}
        
        # Limpiar y validar datos
        df = cls.clean_dataframe(df)
        
        if validate_only:
            return True, "Dataset validado correctamente. Listo para importar.", {
                "total_rows": len(df),
                "valid_rows": len(df)
            }
        
        # Procesar importación
        stats = {
            'flores': {'nuevas': 0, 'existentes': 0},
            'colores': {'nuevas': 0, 'existentes': 0},
            'combinaciones': {'nuevas': 0, 'existentes': 0},
            'variedades': {'nuevas': 0, 'existentes': 0},
            'errores': 0,
            'filas_procesadas': 0,
            'error_details': []
        }
        
        try:
            for index, row in df.iterrows():
                stats['filas_procesadas'] += 1
                
                try:
                    flor_nombre = row['FLOR'].strip().upper()
                    color_nombre = row['COLOR'].strip().upper()
                    variedad_nombre = row['VARIEDAD'].strip().upper()
                    
                    if not all([flor_nombre, color_nombre, variedad_nombre]):
                        raise ValueError("Valores faltantes en la fila")
                    
                    # Procesar flor, color, combinación y variedad
                    flor = cls._process_flor(flor_nombre, stats)
                    color = cls._process_color(color_nombre, stats)
                    flor_color = cls._process_flor_color(flor, color, stats)
                    cls._process_variedad(variedad_nombre, flor_color, stats)
                    
                except Exception as e:
                    stats['errores'] += 1
                    stats['error_details'].append({
                        'row': index + 2,
                        'error': str(e),
                        'data': {
                            'flor': flor_nombre if 'flor_nombre' in locals() else None,
                            'color': color_nombre if 'color_nombre' in locals() else None,
                            'variedad': variedad_nombre if 'variedad_nombre' in locals() else None
                        }
                    })
                    continue
            
            # Confirmar cambios si hay datos válidos
            if stats['filas_procesadas'] > stats['errores']:
                db.session.commit()
            else:
                db.session.rollback()
                return False, "Demasiados errores. No se importaron datos.", stats
            
            # Generar mensaje de resumen
            message = cls._generate_summary_message(stats)
            return True, message, stats
            
        except Exception as e:
            db.session.rollback()
            return False, f"Error durante la importación: {str(e)}", stats
    
    @classmethod
    def clean_dataframe(cls, df: pd.DataFrame) -> pd.DataFrame:
        """Limpia y valida el DataFrame."""
        for col in cls.REQUIRED_COLUMNS:
            df[col] = df[col].astype(str).str.strip()
        return df.dropna(subset=cls.REQUIRED_COLUMNS)
    
    @classmethod
    def _process_flor(cls, nombre: str, stats: Dict) -> Flor:
        """Procesa una flor, creándola si no existe."""
        flor = Flor.query.filter_by(flor=nombre).first()
        if not flor:
            flor = Flor(flor=nombre, flor_abrev=nombre[:10])
            db.session.add(flor)
            db.session.flush()
            stats['flores']['nuevas'] += 1
        else:
            stats['flores']['existentes'] += 1
        return flor
    
    @classmethod
    def _process_color(cls, nombre: str, stats: Dict) -> Color:
        """Procesa un color, creándolo si no existe."""
        color = Color.query.filter_by(color=nombre).first()
        if not color:
            color = Color(color=nombre, color_abrev=nombre[:10])
            db.session.add(color)
            db.session.flush()
            stats['colores']['nuevas'] += 1
        else:
            stats['colores']['existentes'] += 1
        return color
    
    @classmethod
    def _process_flor_color(cls, flor: Flor, color: Color, stats: Dict) -> FlorColor:
        """Procesa una combinación flor-color, creándola si no existe."""
        flor_color = FlorColor.query.filter_by(
            flor_id=flor.flor_id, 
            color_id=color.color_id
        ).first()
        
        if not flor_color:
            flor_color = FlorColor(flor_id=flor.flor_id, color_id=color.color_id)
            db.session.add(flor_color)
            db.session.flush()
            stats['combinaciones']['nuevas'] += 1
        else:
            stats['combinaciones']['existentes'] += 1
        return flor_color
    
    @classmethod
    def _process_variedad(cls, nombre: str, flor_color: FlorColor, stats: Dict) -> Variedad:
        """Procesa una variedad, creándola si no existe."""
        variedad = Variedad.query.filter_by(variedad=nombre).first()
        if not variedad:
            variedad = Variedad(variedad=nombre, flor_color_id=flor_color.flor_color_id)
            db.session.add(variedad)
            stats['variedades']['nuevas'] += 1
        else:
            stats['variedades']['existentes'] += 1
        return variedad
    
    @classmethod
    def _generate_summary_message(cls, stats: Dict) -> str:
        """Genera un mensaje de resumen de la importación."""
        parts = [
            f"Flores nuevas: {stats['flores']['nuevas']}",
            f"Colores nuevos: {stats['colores']['nuevas']}",
            f"Combinaciones nuevas: {stats['combinaciones']['nuevas']}",
            f"Variedades nuevas: {stats['variedades']['nuevas']}"
        ]
        
        if stats['errores'] > 0:
            parts.append(f"Errores: {stats['errores']}")
        
        return "Importación completada. " + ", ".join(parts) + "."