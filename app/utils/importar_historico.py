# app/utils/importar_historico.py
import pandas as pd
from datetime import datetime, timedelta
import re
import os
from app import db, create_app
from app.models import Variedad, FlorColor, Flor, Color, Siembra, Corte, BloqueCamaLado
from app.models import Bloque, Cama, Lado, Area, Densidad, Usuario
from werkzeug.security import generate_password_hash
from flask import current_app
import logging

def importar_historico(archivo_excel):
    """Importa datos históricos de variedades, siembras y cortes desde el formato específico."""
    print(f"Iniciando importación desde archivo: {archivo_excel}")
    
    if not os.path.exists(archivo_excel):
        print(f"Error: El archivo {archivo_excel} no existe.")
        return {"error": f"El archivo {archivo_excel} no existe."}
    
    try:
        # Cargar el archivo Excel
        df = pd.read_excel(archivo_excel)
        print(f"Archivo cargado exitosamente. {len(df)} filas encontradas.")
        
        # Mostrar las columnas encontradas para diagnóstico
        print(f"Columnas encontradas: {df.columns.tolist()}")
        
        # Verificar si hay columnas mínimas necesarias
        columnas_necesarias = ['BLOQUE', 'CAMA', 'FLOR', 'COLOR', 'VARIEDAD', 'FECHA SIEMBRA']
        columnas_faltantes = [col for col in columnas_necesarias if not any(col.upper() in str(c).upper() for c in df.columns)]
        
        if columnas_faltantes:
            error_msg = f"Faltan columnas necesarias en el archivo: {', '.join(columnas_faltantes)}"
            print(error_msg)
            return {"error": error_msg}
        
        # Mostrar primeras filas para diagnóstico
        print("Primeras filas del archivo:")
        print(df.head())
        
    except Exception as e:
        print(f"Error al cargar el archivo Excel: {e}")
        return {"error": f"Error al cargar el archivo Excel: {str(e)}"}
    
    # Estadísticas de importación
    stats = {
        "siembras_creadas": 0,
        "siembras_actualizadas": 0,
        "cortes_creados": 0,
        "cortes_actualizados": 0,
        "variedades_creadas": 0,
        "errores": 0,
        "detalles_errores": []
    }
    
    # Crear la aplicación y contexto
    app = create_app()
    with app.app_context():
        # El resto del código de importación sigue igual...
        
        # Cuando se procese cada fila, añade registros detallados:
        for index, row in df.iterrows():
            try:
                # Código existente...
                
                # Si hay error, registrar detalles:
                if error:
                    stats["detalles_errores"].append({
                        "fila": index + 2,  # +2 porque Excel cuenta desde 1 y tiene encabezado
                        "datos": f"Bloque: {bloque_nombre}, Cama: {cama_nombre}, Variedad: {variedad_nombre}",
                        "error": str(error)
                    })
            except Exception as e:
                stats["errores"] += 1
                stats["detalles_errores"].append({
                    "fila": index + 2,
                    "error": str(e)
                })
                continue
                
    # Al final, devolver estadísticas detalladas
    return stats