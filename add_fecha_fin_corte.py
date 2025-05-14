#!/usr/bin/env python3
"""
Script para añadir la columna fecha_fin_corte a la tabla siembras.
"""
import os
import sys
from sqlalchemy import text

# Ajustar la ruta para importar la aplicación
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app, db

def migrate_add_fecha_fin_corte():
    """Añade la columna fecha_fin_corte a la tabla siembras"""
    app = create_app()
    
    with app.app_context():
        # Verificar si la columna ya existe
        try:
            result = db.session.execute(text("SHOW COLUMNS FROM siembras LIKE 'fecha_fin_corte'"))
            if result.fetchone() is None:
                # La columna no existe, crearla
                db.session.execute(text("ALTER TABLE siembras ADD COLUMN fecha_fin_corte DATE"))
                db.session.commit()
                print("Columna fecha_fin_corte añadida correctamente a la tabla siembras")
            else:
                print("La columna fecha_fin_corte ya existe en la tabla siembras")
        except Exception as e:
            db.session.rollback()
            print(f"Error al añadir columna: {str(e)}")

if __name__ == "__main__":
    migrate_add_fecha_fin_corte()