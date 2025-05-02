# app/utils/import_data.py
import pandas as pd
import os
from app import db
from app.models import Flor, Color, FlorColor, Variedad

def import_variedades_from_excel(file_path):
    """
    Importa variedades desde un archivo Excel.
    
    El archivo debe tener las columnas: FLOR, COLOR, VARIEDAD
    """
    try:
        # Cargar archivo Excel
        df = pd.read_excel(file_path)
        
        # Verificar que las columnas requeridas existan
        required_columns = ['FLOR', 'COLOR', 'VARIEDAD']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            return False, f"Faltan columnas requeridas: {', '.join(missing_columns)}"
        
        # Contadores para estadísticas
        stats = {
            'flores_nuevas': 0,
            'colores_nuevos': 0,
            'combinaciones_nuevas': 0,
            'variedades_nuevas': 0
        }
        
        # Procesar cada fila
        for index, row in df.iterrows():
            flor_nombre = row['FLOR'].strip()
            color_nombre = row['COLOR'].strip()
            variedad_nombre = row['VARIEDAD'].strip()
            
            # Verificar que todos los campos tengan valores
            if not all([flor_nombre, color_nombre, variedad_nombre]):
                continue
            
            # Buscar o crear flor
            flor = Flor.query.filter_by(flor=flor_nombre).first()
            if not flor:
                flor = Flor(flor=flor_nombre, flor_abrev=flor_nombre[:5])
                db.session.add(flor)
                db.session.flush()  # Para obtener el ID
                stats['flores_nuevas'] += 1
            
            # Buscar o crear color
            color = Color.query.filter_by(color=color_nombre).first()
            if not color:
                color = Color(color=color_nombre, color_abrev=color_nombre[:5])
                db.session.add(color)
                db.session.flush()  # Para obtener el ID
                stats['colores_nuevos'] += 1
            
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
            
            # Buscar o crear variedad
            variedad = Variedad.query.filter_by(variedad=variedad_nombre).first()
            if not variedad:
                variedad = Variedad(
                    variedad=variedad_nombre,
                    flor_color_id=flor_color.flor_color_id
                )
                db.session.add(variedad)
                stats['variedades_nuevas'] += 1
        
        # Confirmar cambios
        db.session.commit()
        
        message = (
            f"Importación exitosa: {stats['flores_nuevas']} flores nuevas, "
            f"{stats['colores_nuevos']} colores nuevos, "
            f"{stats['combinaciones_nuevas']} combinaciones nuevas, "
            f"{stats['variedades_nuevas']} variedades nuevas."
        )
        
        return True, message
    
    except Exception as e:
        db.session.rollback()
        return False, f"Error durante la importación: {str(e)}"