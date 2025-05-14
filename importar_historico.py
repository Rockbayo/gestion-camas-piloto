#!/usr/bin/env python3
"""
Script para importar datos históricos desde un archivo Excel.
Este script facilita la importación del histórico de siembras y cortes.

Uso: python importar_historico.py ruta_archivo.xlsx
"""

import os
import sys
import click
import pandas as pd
from datetime import datetime, timedelta

# Ajustar la ruta para importar la aplicación
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Importar la aplicación y modelos
from app import create_app, db
from app.models import (
    Variedad, FlorColor, Flor, Color, Siembra, Corte, BloqueCamaLado,
    Bloque, Cama, Lado, Area, Densidad, Usuario
)

def importar_historico(archivo_excel, usuario_id=1):
    """
    Importa datos históricos de siembras y cortes desde archivo Excel.
    
    Args:
        archivo_excel: Ruta al archivo Excel con datos históricos
        usuario_id: ID del usuario que registra los datos (default: 1 para admin)
    
    Returns:
        dict: Estadísticas de la importación
    """
    app = create_app()
    click.echo(f"Iniciando importación desde archivo: {archivo_excel}")
    
    if not os.path.exists(archivo_excel):
        click.echo(f"Error: El archivo {archivo_excel} no existe.")
        return {"error": f"El archivo {archivo_excel} no existe."}
    
    # Estadísticas de importación
    stats = {
        "siembras_creadas": 0,
        "cortes_creados": 0,
        "variedades_creadas": 0,
        "bloques_creados": 0,
        "camas_creadas": 0,
        "areas_creadas": 0,
        "densidades_creadas": 0,
        "errores": 0,
        "detalles_errores": []
    }
    
    with app.app_context():
        try:
            # Cargar el archivo Excel
            df = pd.read_excel(archivo_excel)
            click.echo(f"Archivo cargado exitosamente. {len(df)} filas encontradas.")
            
            # Mostrar las columnas encontradas para diagnóstico
            click.echo(f"Columnas encontradas: {df.columns.tolist()}")
            
            # Verificar columnas necesarias
            columnas_necesarias = [
                'BLOQUE', 'CAMA', 'FLOR', 'COLOR', 'VARIEDAD', 
                'FECHA SIEMBRA', 'FECHA INICIO CORTE'
            ]
            columnas_faltantes = [
                col for col in columnas_necesarias 
                if not any(col.upper() in str(c).upper() for c in df.columns)
            ]
            
            if columnas_faltantes:
                error_msg = f"Faltan columnas necesarias: {', '.join(columnas_faltantes)}"
                click.echo(error_msg)
                return {"error": error_msg}
            
            # Procesar cada fila
            for index, row in df.iterrows():
                try:
                    click.echo(f"Procesando fila {index+1} de {len(df)}...")
                    
                    # 1. Obtener o crear FLOR y COLOR
                    flor_nombre = str(row['FLOR']).strip().upper()
                    color_nombre = str(row['COLOR']).strip().upper()
                    
                    flor = Flor.query.filter(Flor.flor.ilike(flor_nombre)).first()
                    if not flor:
                        flor = Flor(flor=flor_nombre, flor_abrev=flor_nombre[:10])
                        db.session.add(flor)
                        db.session.flush()
                        stats["variedades_creadas"] += 1
                    
                    color = Color.query.filter(Color.color.ilike(color_nombre)).first()
                    if not color:
                        color = Color(color=color_nombre, color_abrev=color_nombre[:10])
                        db.session.add(color)
                        db.session.flush()
                        stats["variedades_creadas"] += 1
                    
                    # 2. Obtener o crear FLOR_COLOR
                    flor_color = FlorColor.query.filter_by(
                        flor_id=flor.flor_id, 
                        color_id=color.color_id
                    ).first()
                    
                    if not flor_color:
                        flor_color = FlorColor(flor_id=flor.flor_id, color_id=color.color_id)
                        db.session.add(flor_color)
                        db.session.flush()
                        stats["variedades_creadas"] += 1
                    
                    # 3. Obtener o crear VARIEDAD
                    variedad_nombre = str(row['VARIEDAD']).strip().upper()
                    variedad = Variedad.query.filter(Variedad.variedad.ilike(variedad_nombre)).first()
                    
                    if not variedad:
                        variedad = Variedad(
                            variedad=variedad_nombre,
                            flor_color_id=flor_color.flor_color_id
                        )
                        db.session.add(variedad)
                        db.session.flush()
                        stats["variedades_creadas"] += 1
                    
                    # 4. Obtener o crear BLOQUE, CAMA, LADO
                    bloque_nombre = str(row['BLOQUE']).strip().upper()
                    cama_nombre = str(row['CAMA']).strip().upper()
                    
                    # Manejar extracción de lado desde cama si es necesario
                    lado_nombre = "ÚNICO"
                    # Si la cama tiene formato como "55A", extraer el lado
                    if len(cama_nombre) > 1 and cama_nombre[-1].isalpha():
                        lado_nombre = cama_nombre[-1]
                        cama_nombre = cama_nombre[:-1]
                    
                    # Verificar si existe columna LADO explícita
                    if 'LADO' in row and pd.notna(row['LADO']):
                        lado_nombre = str(row['LADO']).strip().upper()
                    
                    # Obtener o crear objetos
                    bloque = Bloque.query.filter(Bloque.bloque.ilike(bloque_nombre)).first()
                    if not bloque:
                        bloque = Bloque(bloque=bloque_nombre)
                        db.session.add(bloque)
                        db.session.flush()
                        stats["bloques_creados"] += 1
                    
                    cama = Cama.query.filter(Cama.cama.ilike(cama_nombre)).first()
                    if not cama:
                        cama = Cama(cama=cama_nombre)
                        db.session.add(cama)
                        db.session.flush()
                        stats["camas_creadas"] += 1
                    
                    lado = Lado.query.filter(Lado.lado.ilike(lado_nombre)).first()
                    if not lado:
                        lado = Lado(lado=lado_nombre)
                        db.session.add(lado)
                        db.session.flush()
                    
                    # 5. Obtener o crear BLOQUE_CAMA_LADO
                    bloque_cama = BloqueCamaLado.query.filter_by(
                        bloque_id=bloque.bloque_id,
                        cama_id=cama.cama_id,
                        lado_id=lado.lado_id
                    ).first()
                    
                    if not bloque_cama:
                        bloque_cama = BloqueCamaLado(
                            bloque_id=bloque.bloque_id,
                            cama_id=cama.cama_id,
                            lado_id=lado.lado_id
                        )
                        db.session.add(bloque_cama)
                        db.session.flush()
                    
                    # 6. Obtener o crear AREA
                    area_valor = None
                    if 'Area' in row and pd.notna(row['Area']):
                        area_valor = float(row['Area'])
                    elif 'AREA' in row and pd.notna(row['AREA']):
                        area_valor = float(row['AREA'])
                    else:
                        area_valor = 10.0  # Valor por defecto
                    
                    area_nombre = f"ÁREA {area_valor:.2f}m²"
                    area = Area.query.filter(Area.siembra.ilike(area_nombre)).first()
                    
                    if not area:
                        area = Area(siembra=area_nombre, area=area_valor)
                        db.session.add(area)
                        db.session.flush()
                        stats["areas_creadas"] += 1
                    
                    # 7. Obtener o crear DENSIDAD
                    densidad_valor = None
                    if 'DENSIDAD' in row and pd.notna(row['DENSIDAD']):
                        densidad_valor = float(row['DENSIDAD'])
                    elif 'Densidad' in row and pd.notna(row['Densidad']):
                        densidad_valor = float(row['Densidad'])
                    else:
                        # Calcular densidad a partir de PLANTAS si existe
                        if 'PLANTAS' in row and pd.notna(row['PLANTAS']) and area_valor > 0:
                            densidad_valor = float(row['PLANTAS']) / area_valor
                        else:
                            densidad_valor = 1.0  # Valor por defecto
                    
                    densidad_nombre = f"DENSIDAD {densidad_valor:.2f}"
                    densidad = Densidad.query.filter(Densidad.densidad.ilike(densidad_nombre)).first()
                    
                    if not densidad:
                        densidad = Densidad(densidad=densidad_nombre, valor=densidad_valor)
                        db.session.add(densidad)
                        db.session.flush()
                        stats["densidades_creadas"] += 1
                    
                    # 8. Crear SIEMBRA
                    fecha_siembra = pd.to_datetime(row['FECHA SIEMBRA']).date()
                    
                    # Obtener fecha inicio corte
                    fecha_inicio_corte = None
                    if 'FECHA INICIO CORTE' in row and pd.notna(row['FECHA INICIO CORTE']):
                        fecha_inicio_corte = pd.to_datetime(row['FECHA INICIO CORTE']).date()
                    
                    # Estado siembra (por defecto finalizada para históricos)
                    estado = 'Finalizada'
                    if 'ESTADO' in row and pd.notna(row['ESTADO']):
                        estado = str(row['ESTADO']).strip().capitalize()
                        if estado not in ['Activa', 'Finalizada']:
                            estado = 'Finalizada'
                    
                    # Crear siembra
                    siembra = Siembra(
                        bloque_cama_id=bloque_cama.bloque_cama_id,
                        variedad_id=variedad.variedad_id,
                        area_id=area.area_id,
                        densidad_id=densidad.densidad_id,
                        fecha_siembra=fecha_siembra,
                        fecha_inicio_corte=fecha_inicio_corte,
                        estado=estado,
                        usuario_id=usuario_id,
                        fecha_registro=datetime.now()
                    )
                    
                    db.session.add(siembra)
                    db.session.flush()
                    stats["siembras_creadas"] += 1
                    
                    # 9. Crear CORTES (si existen)
                    # Columnas que contienen datos de cortes (1-15)
                    columnas_cortes = [col for col in df.columns if str(col).isdigit() or (isinstance(col, str) and col.isdigit())]
                    
                    for num_corte, col in enumerate(sorted(columnas_cortes), 1):
                        if pd.notna(row[col]) and row[col] > 0:
                            # Calcular fecha de corte (si no hay fecha inicio corte, usar fecha siembra + días)
                            if fecha_inicio_corte:
                                fecha_corte = fecha_inicio_corte + timedelta(days=(num_corte-1) * 7)
                            else:
                                fecha_corte = fecha_siembra + timedelta(days=60 + (num_corte-1) * 7)
                            
                            # Crear corte
                            corte = Corte(
                                siembra_id=siembra.siembra_id,
                                num_corte=num_corte,
                                fecha_corte=fecha_corte,
                                cantidad_tallos=int(row[col]),
                                usuario_id=usuario_id,
                                fecha_registro=datetime.now()
                            )
                            
                            db.session.add(corte)
                            stats["cortes_creados"] += 1
                    
                    # Confirmar cambios de esta fila
                    db.session.commit()
                    
                except Exception as e:
                    db.session.rollback()
                    error_mensaje = f"Error en fila {index+1}: {str(e)}"
                    click.echo(error_mensaje)
                    stats["errores"] += 1
                    stats["detalles_errores"].append({
                        "fila": index + 1,
                        "error": str(e)
                    })
                    
                # Mostrar progreso cada 10 filas
                if (index + 1) % 10 == 0:
                    click.echo(f"Procesadas {index + 1} filas...")
            
            # Resumen final
            click.echo("\nResumen de importación:")
            click.echo(f"- Siembras creadas: {stats['siembras_creadas']}")
            click.echo(f"- Cortes creados: {stats['cortes_creados']}")
            click.echo(f"- Variedades creadas/actualizadas: {stats['variedades_creadas']}")
            click.echo(f"- Bloques creados: {stats['bloques_creados']}")
            click.echo(f"- Camas creadas: {stats['camas_creadas']}")
            click.echo(f"- Errores: {stats['errores']}")
            
            return stats
            
        except Exception as e:
            db.session.rollback()
            error_general = f"Error general: {str(e)}"
            click.echo(error_general)
            stats["error_general"] = error_general
            return stats

@click.command()
@click.argument('archivo_excel', type=click.Path(exists=True))
@click.option('--usuario-id', type=int, default=1, help='ID del usuario que registra los datos')
def main(archivo_excel, usuario_id):
    """Importa datos históricos desde un archivo Excel."""
    click.echo("=== IMPORTADOR DE DATOS HISTÓRICOS ===")
    
    if click.confirm(f"¿Desea importar datos desde {archivo_excel}?", default=True):
        stats = importar_historico(archivo_excel, usuario_id)
        
        if "error" in stats:
            click.echo(f"Error: {stats['error']}")
            return 1
        
        if "error_general" in stats:
            click.echo(f"Error general: {stats['error_general']}")
            return 1
        
        if stats["errores"] > 0:
            click.echo(f"Importación completada con {stats['errores']} errores.")
            for error in stats["detalles_errores"]:
                click.echo(f"  - Fila {error['fila']}: {error['error']}")
        else:
            click.echo("Importación completada exitosamente.")
        
        return 0
    
    click.echo("Operación cancelada.")
    return 0

if __name__ == "__main__":
    main()