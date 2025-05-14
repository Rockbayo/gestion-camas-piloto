#!/usr/bin/env python3
"""
Script mejorado para importar datos históricos desde un archivo Excel.
Maneja automáticamente problemas comunes con archivos de Excel y rutas.

Uso: python importar_mejorado.py [ruta_al_archivo.xlsx]
"""

import os
import sys
import re
import click
import pandas as pd
from datetime import datetime, timedelta
import traceback
import unicodedata

# Ajustar la ruta para importar la aplicación
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Crear función para limpiar rutas de caracteres problemáticos
def limpiar_ruta(ruta):
    """Elimina caracteres Unicode invisibles y especiales de una ruta"""
    # Eliminar caracteres de control y Unicode invisibles
    ruta_limpia = re.sub(r'[\u0000-\u001F\u007F\u2000-\u200F\u2028-\u202F]', '', ruta)
    # Normalizar Unicode para manejar acentos y caracteres especiales
    return unicodedata.normalize('NFC', ruta_limpia)

def mostrar_instrucciones_importacion():
    """Muestra instrucciones de uso del script"""
    click.echo("\n===== INSTRUCCIONES DE IMPORTACIÓN =====")
    click.echo("\nEste script importa datos históricos desde un archivo Excel.")
    click.echo("\nEl archivo Excel debe contener al menos las siguientes columnas:")
    click.echo("- BLOQUE: Identificador del bloque")
    click.echo("- CAMA: Número de cama (ej: '55A')")
    click.echo("- FLOR: Tipo de flor")
    click.echo("- COLOR: Color de la flor")
    click.echo("- VARIEDAD: Nombre de la variedad")
    click.echo("- FECHA SIEMBRA: Fecha en que se realizó la siembra")
    click.echo("- FECHA INICIO CORTE: (opcional) Fecha del primer corte")
    click.echo("- Columnas numéricas (1, 2, 3...) para los tallos cortados")
    click.echo("\nEjemplo de uso:")
    click.echo("  python importar_mejorado.py MiArchivoHistorico.xlsx")
    click.echo("\n======================================")

def obtener_archivo_excel():
    """Obtiene la ruta del archivo Excel de argumentos o solicita al usuario"""
    if len(sys.argv) > 1:
        # Si se proporcionó como argumento, limpiar la ruta
        ruta = limpiar_ruta(sys.argv[1])
        if os.path.exists(ruta):
            return ruta
        else:
            click.echo(f"ERROR: No se encuentra el archivo: {ruta}")
            click.echo(f"Ruta original: {sys.argv[1]}")
    
    # Si no se proporcionó argumento o la ruta no existe, buscar en el directorio actual
    archivos_excel = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.xls'))]
    
    if not archivos_excel:
        click.echo("No se encontraron archivos Excel en el directorio actual.")
        return None
    
    if len(archivos_excel) == 1:
        click.echo(f"Se encontró un archivo Excel: {archivos_excel[0]}")
        if click.confirm("¿Desea usar este archivo?", default=True):
            return archivos_excel[0]
    else:
        click.echo("Archivos Excel disponibles:")
        for idx, archivo in enumerate(archivos_excel, 1):
            click.echo(f"{idx}. {archivo}")
        
        idx = click.prompt("Seleccione el número del archivo a importar", type=int, default=1)
        if 1 <= idx <= len(archivos_excel):
            return archivos_excel[idx-1]
    
    return None

def analizar_estructura_excel(archivo):
    """Analiza la estructura del archivo Excel y sugiere mapeos de columnas"""
    try:
        # Intentar cargar el archivo
        df = pd.read_excel(archivo, nrows=5)
        
        # Mostrar información básica
        click.echo(f"\nAnálisis del archivo: {archivo}")
        click.echo(f"Total de columnas: {len(df.columns)}")
        click.echo(f"Primeras columnas: {', '.join(str(col) for col in df.columns[:8])}")
        
        # Verificar y sugerir mapeos para columnas requeridas
        columnas_requeridas = ['BLOQUE', 'CAMA', 'FLOR', 'COLOR', 'VARIEDAD', 'FECHA SIEMBRA']
        mapeo_sugerido = {}
        
        for col_req in columnas_requeridas:
            # Buscar coincidencias exactas primero
            coincidencias = [col for col in df.columns if str(col).upper() == col_req]
            
            # Si no hay coincidencias exactas, buscar coincidencias parciales
            if not coincidencias:
                coincidencias = [col for col in df.columns if col_req in str(col).upper()]
            
            if coincidencias:
                mapeo_sugerido[col_req] = coincidencias[0]
        
        # Buscar columnas de cortes (numéricas)
        cols_cortes = [col for col in df.columns if isinstance(col, int) or (isinstance(col, str) and col.isdigit())]
        
        # Mostrar resultados
        if mapeo_sugerido:
            click.echo("\nMapeo sugerido de columnas:")
            for col_req, col_encontrada in mapeo_sugerido.items():
                click.echo(f"- {col_req}: {col_encontrada}")
            
            if cols_cortes:
                click.echo(f"\nColumnas de cortes detectadas: {', '.join(str(col) for col in cols_cortes[:5])}{'...' if len(cols_cortes) > 5 else ''}")
                click.echo(f"Total de columnas de cortes: {len(cols_cortes)}")
            
            return True
        else:
            click.echo("\nNo se pudieron detectar las columnas requeridas.")
            click.echo("Por favor, asegúrese de que el archivo contiene las columnas necesarias.")
            return False
            
    except Exception as e:
        click.echo(f"Error al analizar el archivo: {str(e)}")
        traceback.print_exc()
        return False

def importar_historico_mejorado(archivo_excel):
    """Versión mejorada para importar histórico manejando errores comunes"""
    try:
        from app import create_app, db
        from app.models import (
            Variedad, FlorColor, Flor, Color, Siembra, Corte, BloqueCamaLado,
            Bloque, Cama, Lado, Area, Densidad, Usuario
        )
        
        app = create_app()
        
        click.echo(f"Iniciando importación desde archivo: {archivo_excel}")
        
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
            # Encontrar el usuario admin para asignar como creador
            usuario = Usuario.query.filter_by(username='admin').first()
            if not usuario:
                usuario_id = 1  # ID por defecto
            else:
                usuario_id = usuario.usuario_id
            
            # Cargar el archivo Excel con manejo de errores mejorado
            try:
                df = pd.read_excel(archivo_excel)
                click.echo(f"Archivo cargado exitosamente. {len(df)} filas encontradas.")
            except Exception as e:
                click.echo(f"Error al cargar el archivo Excel: {str(e)}")
                click.echo("Intentando con parámetros alternativos...")
                try:
                    df = pd.read_excel(archivo_excel, engine='openpyxl')
                    click.echo(f"Archivo cargado con engine=openpyxl. {len(df)} filas encontradas.")
                except Exception as e2:
                    click.echo(f"Error secundario: {str(e2)}")
                    return {"error": f"No se pudo cargar el archivo: {str(e2)}"}
            
            # Mostrar las columnas encontradas para diagnóstico
            click.echo(f"Columnas encontradas: {df.columns.tolist()}")
            
            # Normalizar nombres de columnas (convertir a mayúsculas)
            df.columns = [str(col).upper() if isinstance(col, str) else col for col in df.columns]
            
            # Verificar columnas mínimas necesarias con mayor flexibilidad
            columnas_necesarias = ['BLOQUE', 'CAMA', 'FLOR', 'COLOR', 'VARIEDAD', 'FECHA SIEMBRA']
            columnas_presentes = [col for col in columnas_necesarias if col in df.columns]
            columnas_faltantes = [col for col in columnas_necesarias if col not in df.columns]
            
            if columnas_faltantes:
                # Intentar buscar columnas similares
                for col_faltante in columnas_faltantes.copy():
                    posibles_matches = [col for col in df.columns if col_faltante in str(col)]
                    if posibles_matches:
                        click.echo(f"Columna '{col_faltante}' no encontrada exactamente, pero se encontró '{posibles_matches[0]}'")
                        # Renombrar columna
                        df = df.rename(columns={posibles_matches[0]: col_faltante})
                        columnas_faltantes.remove(col_faltante)
                        columnas_presentes.append(col_faltante)
            
            if columnas_faltantes:
                error_msg = f"Faltan columnas necesarias: {', '.join(columnas_faltantes)}"
                click.echo(error_msg)
                return {"error": error_msg}
            
            # Procesar cada fila con mejor manejo de errores
            total_filas = len(df)
            for index, row in df.iterrows():
                try:
                    # Mostrar progreso
                    if index % 10 == 0 or index == total_filas - 1:
                        click.echo(f"Procesando fila {index+1}/{total_filas}...")
                    
                    # 1. Obtener o crear FLOR y COLOR
                    flor_nombre = str(row['FLOR']).strip().upper()
                    color_nombre = str(row['COLOR']).strip().upper()
                    
                    # Validar datos
                    if not flor_nombre or pd.isna(flor_nombre) or flor_nombre.lower() == 'nan':
                        raise ValueError("Nombre de flor vacío o inválido")
                    if not color_nombre or pd.isna(color_nombre) or color_nombre.lower() == 'nan':
                        raise ValueError("Nombre de color vacío o inválido")
                    
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
                    if not variedad_nombre or pd.isna(variedad_nombre) or variedad_nombre.lower() == 'nan':
                        raise ValueError("Nombre de variedad vacío o inválido")
                        
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
                    
                    if not bloque_nombre or pd.isna(bloque_nombre) or bloque_nombre.lower() == 'nan':
                        raise ValueError("Nombre de bloque vacío o inválido")
                    if not cama_nombre or pd.isna(cama_nombre) or cama_nombre.lower() == 'nan':
                        raise ValueError("Nombre de cama vacío o inválido")
                    
                    # Manejar extracción de lado desde cama si es necesario
                    lado_nombre = "ÚNICO"
                    # Si la cama tiene formato como "55A", extraer el lado
                    if len(cama_nombre) > 1 and cama_nombre[-1].isalpha():
                        lado_nombre = cama_nombre[-1]
                        cama_nombre = cama_nombre[:-1]
                    
                    # Verificar si existe columna LADO explícita
                    if 'LADO' in row.index and pd.notna(row['LADO']):
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
                    area_cols = ['AREA', 'ÁREA', 'AREA M2', 'ÁREA M2']
                    for col in area_cols:
                        if col in row.index and pd.notna(row[col]):
                            try:
                                area_valor = float(row[col])
                                break
                            except:
                                continue
                    
                    # Si no se encontró área, usar valor predeterminado
                    if area_valor is None:
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
                    densidad_cols = ['DENSIDAD', 'DENS', 'DENSIDAD PLTS']
                    for col in densidad_cols:
                        if col in row.index and pd.notna(row[col]):
                            try:
                                densidad_valor = float(row[col])
                                break
                            except:
                                continue
                    
                    # Si no se encontró densidad pero hay plantas, calcular
                    if densidad_valor is None and 'PLANTAS' in row.index and pd.notna(row['PLANTAS']) and area_valor > 0:
                        try:
                            densidad_valor = float(row['PLANTAS']) / area_valor
                        except:
                            densidad_valor = 1.0  # Valor por defecto
                    elif densidad_valor is None:
                        densidad_valor = 1.0  # Valor por defecto
                    
                    densidad_nombre = f"DENSIDAD {densidad_valor:.2f}"
                    densidad = Densidad.query.filter(Densidad.densidad.ilike(densidad_nombre)).first()
                    
                    if not densidad:
                        densidad = Densidad(densidad=densidad_nombre, valor=densidad_valor)
                        db.session.add(densidad)
                        db.session.flush()
                        stats["densidades_creadas"] += 1
                    
                    # 8. Crear SIEMBRA
                    try:
                        fecha_siembra = pd.to_datetime(row['FECHA SIEMBRA']).date()
                    except:
                        # Si hay error, intentar diferentes formatos
                        try:
                            fecha_str = str(row['FECHA SIEMBRA'])
                            for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%m/%d/%Y', '%d-%m-%Y']:
                                try:
                                    fecha_siembra = datetime.strptime(fecha_str, fmt).date()
                                    break
                                except:
                                    continue
                            if 'fecha_siembra' not in locals():
                                raise ValueError(f"No se pudo interpretar la fecha: {fecha_str}")
                        except:
                            # Si todo falla, usar una fecha por defecto
                            fecha_siembra = datetime(2023, 1, 1).date()
                    
                    # Obtener fecha inicio corte
                    fecha_inicio_corte = None
                    fecha_cols = ['FECHA INICIO CORTE', 'INICIO CORTE', 'FECHA CORTE']
                    for col in fecha_cols:
                        if col in row.index and pd.notna(row[col]):
                            try:
                                fecha_inicio_corte = pd.to_datetime(row[col]).date()
                                break
                            except:
                                continue
                    
                    # Estado siembra (por defecto finalizada para históricos)
                    estado = 'Finalizada'
                    if 'ESTADO' in row.index and pd.notna(row['ESTADO']):
                        estado_str = str(row['ESTADO']).strip().capitalize()
                        if estado_str in ['Activa', 'Finalizada']:
                            estado = estado_str
                    
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
                    columnas_cortes = [col for col in row.index if 
                                      (isinstance(col, int) and col > 0) or 
                                      (isinstance(col, str) and col.isdigit() and int(col) > 0)]
                    
                    for num_corte_col in sorted(columnas_cortes, key=lambda x: int(x) if isinstance(x, str) else x):
                        if pd.notna(row[num_corte_col]) and float(row[num_corte_col]) > 0:
                            # Convertir a entero asegurándonos de que es un valor positivo
                            try:
                                cantidad = int(float(row[num_corte_col]))
                                if cantidad <= 0:
                                    continue
                            except:
                                continue
                                
                            # Calcular número de corte (puede ser diferente al índice de columna)
                            if isinstance(num_corte_col, int):
                                num_corte = num_corte_col
                            else:
                                num_corte = int(num_corte_col)
                            
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
                                cantidad_tallos=cantidad,
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
                    
            # Resumen final
            click.echo("\n===== RESUMEN DE IMPORTACIÓN =====")
            click.echo(f"- Siembras creadas: {stats['siembras_creadas']}")
            click.echo(f"- Cortes creados: {stats['cortes_creados']}")
            click.echo(f"- Variedades creadas/actualizadas: {stats['variedades_creadas']}")
            click.echo(f"- Bloques creados: {stats['bloques_creados']}")
            click.echo(f"- Camas creadas: {stats['camas_creadas']}")
            click.echo(f"- Áreas creadas: {stats['areas_creadas']}")
            click.echo(f"- Densidades creadas: {stats['densidades_creadas']}")
            click.echo(f"- Errores: {stats['errores']}")
            click.echo("=================================")
            
            if stats["errores"] > 0:
                click.echo("\nDetalles de errores encontrados:")
                for i, error in enumerate(stats["detalles_errores"][:10], 1):
                    click.echo(f"  {i}. Fila {error['fila']}: {error['error']}")
                if len(stats["detalles_errores"]) > 10:
                    click.echo(f"  ... y {len(stats['detalles_errores']) - 10} errores más.")
            
            return stats
            
    except Exception as e:
        error_general = f"Error general: {str(e)}"
        click.echo(error_general)
        traceback.print_exc()
        return {"error_general": error_general}

if __name__ == "__main__":
    # Mostrar encabezado
    click.echo("===== IMPORTADOR MEJORADO DE DATOS HISTÓRICOS =====")
    
    # Verificar argumentos y mostrar instrucciones si es necesario
    if len(sys.argv) == 1 or '-h' in sys.argv or '--help' in sys.argv:
        mostrar_instrucciones_importacion()
        
    # Obtener archivo Excel
    archivo_excel = obtener_archivo_excel()
    
    if not archivo_excel:
        click.echo("No se seleccionó ningún archivo Excel. Terminando programa.")
        sys.exit(1)
    
    # Analizar estructura del archivo
    if not analizar_estructura_excel(archivo_excel):
        if not click.confirm("¿Desea continuar con la importación de todos modos?", default=False):
            click.echo("Importación cancelada por el usuario.")
            sys.exit(1)
    
    # Confirmación final
    if click.confirm(f"¿Desea importar datos desde {archivo_excel}?", default=True):
        stats = importar_historico_mejorado(archivo_excel)
        
        if "error" in stats:
            click.echo(f"Error: {stats['error']}")
            sys.exit(1)
        
        if "error_general" in stats:
            click.echo(f"Error general: {stats['error_general']}")
            sys.exit(1)
        
        if stats.get("siembras_creadas", 0) > 0:
            click.echo("\n¡Importación completada correctamente!")
            sys.exit(0)
        else:
            click.echo("No se importaron siembras. Revise los errores reportados.")
            sys.exit(1)
    else:
        click.echo("Importación cancelada por el usuario.")
        sys.exit(0)