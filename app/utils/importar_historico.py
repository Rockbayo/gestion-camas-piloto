"""
Módulo para importación de datos históricos desde archivos Excel.

Mejoras:
- Mejor manejo de errores
- Progreso más detallado
- Transacciones más seguras
"""

import os
import pandas as pd
from datetime import datetime
from typing import Dict, Any
from app import db, create_app
from app.models import Variedad, FlorColor, Flor, Color, Siembra, Corte, BloqueCamaLado
from app.models import Bloque, Cama, Lado, Area, Densidad, Usuario
from werkzeug.security import generate_password_hash
import logging

class HistoricalImporter:
    """
    Clase para manejar la importación de datos históricos.
    """
    
    REQUIRED_COLUMNS = ['BLOQUE', 'CAMA', 'FLOR', 'COLOR', 'VARIEDAD', 'FECHA SIEMBRA']
    
    @classmethod
    def import_historical_data(cls, file_path: str) -> Dict[str, Any]:
        """
        Importa datos históricos desde un archivo Excel.
        
        Returns:
            Dict con estadísticas de la importación
        """
        # Validar archivo
        if not os.path.exists(file_path):
            return {"error": f"El archivo {file_path} no existe."}
        
        try:
            df = pd.read_excel(file_path)
            logging.info(f"Archivo cargado: {len(df)} filas encontradas.")
            
            # Verificar columnas requeridas
            missing_cols = cls._check_required_columns(df)
            if missing_cols:
                return {"error": f"Faltan columnas requeridas: {', '.join(missing_cols)}"}
            
            # Preparar estadísticas
            stats = {
                "siembras": {"creadas": 0, "actualizadas": 0},
                "cortes": {"creados": 0, "actualizados": 0},
                "variedades": {"creadas": 0, "existentes": 0},
                "errores": 0,
                "error_details": []
            }
            
            # Crear contexto de aplicación
            app = create_app()
            with app.app_context():
                for index, row in df.iterrows():
                    try:
                        cls._process_row(row, stats)
                    except Exception as e:
                        stats["errores"] += 1
                        stats["error_details"].append({
                            "fila": index + 2,
                            "error": str(e),
                            "data": row.to_dict()
                        })
                        continue
                
                # Confirmar cambios si hay datos válidos
                if stats["siembras"]["creadas"] + stats["cortes"]["creadas"] > 0:
                    db.session.commit()
                else:
                    db.session.rollback()
            
            return stats
            
        except Exception as e:
            logging.error(f"Error en importación histórica: {str(e)}", exc_info=True)
            return {"error": f"Error durante la importación: {str(e)}"}
    
    @classmethod
    def _check_required_columns(cls, df: pd.DataFrame) -> List[str]:
        """Verifica las columnas requeridas en el DataFrame."""
        return [
            col for col in cls.REQUIRED_COLUMNS 
            if not any(col.upper() in str(c).upper() for c in df.columns)
        ]
    
    @classmethod
    def _process_row(cls, row: pd.Series, stats: Dict[str, Any]) -> None:
        """Procesa una fila individual del archivo."""
        # Normalizar datos
        bloque_nombre = str(row['BLOQUE']).strip()
        cama_nombre = str(row['CAMA']).strip()
        flor_nombre = str(row['FLOR']).strip().upper()
        color_nombre = str(row['COLOR']).strip().upper()
        variedad_nombre = str(row['VARIEDAD']).strip().upper()
        fecha_siembra = row['FECHA SIEMBRA']
        
        # Validar campos obligatorios
        if not all([bloque_nombre, cama_nombre, flor_nombre, color_nombre, variedad_nombre]):
            raise ValueError("Campos obligatorios faltantes")
        
        # Procesar variedad
        variedad = cls._process_variedad(flor_nombre, color_nombre, variedad_nombre, stats)
        
        # Procesar siembra
        siembra = cls._process_siembra(bloque_nombre, cama_nombre, variedad, fecha_siembra, stats)
        
        # Procesar cortes si existen
        if 'FECHA CORTE' in row and 'TALLOS' in row:
            cls._process_corte(row, siembra, stats)
    
    @classmethod
    def _process_variedad(cls, flor_nombre: str, color_nombre: str, variedad_nombre: str, stats: Dict) -> Variedad:
        """Procesa una variedad, creándola si no existe."""
        flor = Flor.query.filter_by(flor=flor_nombre).first()
        if not flor:
            flor = Flor(flor=flor_nombre, flor_abrev=flor_nombre[:10])
            db.session.add(flor)
        
        color = Color.query.filter_by(color=color_nombre).first()
        if not color:
            color = Color(color=color_nombre, color_abrev=color_nombre[:10])
            db.session.add(color)
        
        flor_color = FlorColor.query.filter_by(flor_id=flor.flor_id, color_id=color.color_id).first()
        if not flor_color:
            flor_color = FlorColor(flor_id=flor.flor_id, color_id=color.color_id)
            db.session.add(flor_color)
        
        variedad = Variedad.query.filter_by(variedad=variedad_nombre).first()
        if not variedad:
            variedad = Variedad(variedad=variedad_nombre, flor_color_id=flor_color.flor_color_id)
            db.session.add(variedad)
            stats["variedades"]["creadas"] += 1
        else:
            stats["variedades"]["existentes"] += 1
        
        return variedad
    
    @classmethod
    def _process_siembra(cls, bloque_nombre: str, cama_nombre: str, variedad: Variedad, fecha_siembra: Any, stats: Dict) -> Siembra:
        """Procesa una siembra, creándola si no existe."""
        # Implementación similar a _process_variedad pero para siembras
        pass
    
    @classmethod
    def _process_corte(cls, row: pd.Series, siembra: Siembra, stats: Dict) -> None:
        """Procesa un corte, creándolo si no existe."""
        # Implementación similar a _process_variedad pero para cortes
        pass