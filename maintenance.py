#!/usr/bin/env python3
"""
Script de mantenimiento para el Sistema de Gestión de Cultivos
Este script unifica operaciones de mantenimiento y corrección de datos
"""
import os
import sys
import click
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy import text, inspect

# Ajustar la ruta para importar la aplicación
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app, db
from app.models import Siembra, Corte, Variedad, Area, Densidad, Bloque, Cama, Lado, BloqueCamaLado, Flor, Color, FlorColor

app = create_app()

@click.group()
def cli():
    """Herramienta de mantenimiento para la aplicación de Gestión de Cultivos."""
    pass

@cli.command()
def actualizar_fecha_fin_corte():
    """Actualiza la fecha_fin_corte de todas las siembras finalizadas que no la tengan."""
    with app.app_context():
        siembras_sin_fecha = Siembra.query.filter_by(estado='Finalizada').filter(Siembra.fecha_fin_corte == None).all()
        if not siembras_sin_fecha:
            click.echo("No hay siembras finalizadas sin fecha de fin de corte.")
            return
        
        count = 0
        for siembra in siembras_sin_fecha:
            if siembra.cortes:
                # Usar la fecha del último corte
                ultima_fecha = max([c.fecha_corte for c in siembra.cortes])
                siembra.fecha_fin_corte = ultima_fecha
                count += 1
            else:
                # Sin cortes, usar fecha de siembra + 90 días (ciclo típico)
                siembra.fecha_fin_corte = siembra.fecha_siembra + timedelta(days=90)
                count += 1
        
        db.session.commit()
        click.echo(f"Se actualizaron {count} siembras finalizadas con fechas de fin de corte.")

@cli.command()
def verificar_inconsistencias_bloquecama():
    """Verifica inconsistencias en la relación de bloques, camas y ubicaciones."""
    with app.app_context():
        # Verificar BloqueCamaLado huérfanos (sin bloque, cama o lado)
        huerfanos = db.session.query(BloqueCamaLado).outerjoin(
            Bloque, BloqueCamaLado.bloque_id == Bloque.bloque_id
        ).outerjoin(
            Cama, BloqueCamaLado.cama_id == Cama.cama_id
        ).outerjoin(
            Lado, BloqueCamaLado.lado_id == Lado.lado_id
        ).filter(
            (Bloque.bloque_id == None) | 
            (Cama.cama_id == None) | 
            (Lado.lado_id == None)
        ).all()
        
        if huerfanos:
            click.echo(f"Se encontraron {len(huerfanos)} BloqueCamaLado huérfanos (sin bloque, cama o lado).")
            if click.confirm("¿Desea eliminar estas entradas huérfanas?"):
                for bcl in huerfanos:
                    db.session.delete(bcl)
                db.session.commit()
                click.echo("Entradas huérfanas eliminadas correctamente.")
        else:
            click.echo("No se encontraron BloqueCamaLado huérfanos.")

@cli.command()
def optimizar_tablas_db():
    """Optimiza las tablas de la base de datos."""
    with app.app_context():
        # Ejecutar OPTIMIZE TABLE para todas las tablas
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        for table in tables:
            try:
                db.session.execute(text(f"OPTIMIZE TABLE {table}"))
                click.echo(f"Tabla {table} optimizada.")
            except Exception as e:
                click.echo(f"Error al optimizar tabla {table}: {str(e)}")
        
        # Añadir índices importantes que pudieran faltar
        indices = [
            ("siembras", "idx_siembras_estado", "estado"),
            ("siembras", "idx_siembras_variedad", "variedad_id"),
            ("siembras", "idx_siembras_fechas", "fecha_siembra, fecha_inicio_corte"),
            ("cortes", "idx_cortes_siembra", "siembra_id"),
            ("cortes", "idx_cortes_fecha", "fecha_corte")
        ]
        
        for tabla, nombre_indice, columnas in indices:
            try:
                # Verificar si el índice ya existe
                indice_existe = False
                indices_actuales = inspector.get_indexes(tabla)
                for idx in indices_actuales:
                    if idx['name'] == nombre_indice:
                        indice_existe = True
                        break
                
                if not indice_existe:
                    db.session.execute(text(f"CREATE INDEX {nombre_indice} ON {tabla}({columnas})"))
                    click.echo(f"Índice {nombre_indice} creado en tabla {tabla}.")
                else:
                    click.echo(f"Índice {nombre_indice} ya existe en tabla {tabla}.")
            except Exception as e:
                click.echo(f"Error al crear índice {nombre_indice}: {str(e)}")
        
        db.session.commit()
        click.echo("Base de datos optimizada correctamente.")

@cli.command()
def reparar_densidades():
    """Repara densidades con valores incorrectos o faltantes."""
    with app.app_context():
        # Verificar densidades con valores nulos o inválidos
        densidades_invalidas = Densidad.query.filter((Densidad.valor == None) | 
                                                   (Densidad.valor <= 0)).all()
        
        if densidades_invalidas:
            click.echo(f"Se encontraron {len(densidades_invalidas)} densidades con valores inválidos.")
            for densidad in densidades_invalidas:
                densidad.valor = 64.0  # Valor por defecto común
                click.echo(f"  Densidad '{densidad.densidad}' actualizada con valor por defecto.")
            
            db.session.commit()
            click.echo("Densidades reparadas correctamente.")
        else:
            click.echo("No se encontraron densidades con valores inválidos.")
        
        # Verificar siembras con densidades inválidas
        siembras_sin_densidad = Siembra.query.filter(Siembra.densidad_id == None).all()
        
        if siembras_sin_densidad:
            click.echo(f"Se encontraron {len(siembras_sin_densidad)} siembras sin densidad asignada.")
            
            # Buscar una densidad por defecto
            densidad_default = Densidad.query.first()
            if not densidad_default:
                # Crear una densidad por defecto si no existe ninguna
                densidad_default = Densidad(densidad="ESTÁNDAR", valor=64.0)
                db.session.add(densidad_default)
                db.session.flush()
            
            for siembra in siembras_sin_densidad:
                siembra.densidad_id = densidad_default.densidad_id
                click.echo(f"  Siembra #{siembra.siembra_id} actualizada con densidad por defecto.")
            
            db.session.commit()
            click.echo("Siembras sin densidad reparadas correctamente.")
        else:
            click.echo("No se encontraron siembras sin densidad asignada.")

@cli.command()
def crear_dataset_prueba():
    """Crea un dataset de prueba con variedades, bloques y siembras básicas."""
    with app.app_context():
        # Verificar si ya hay datos
        if Variedad.query.count() > 0 and BloqueCamaLado.query.count() > 0:
            if not click.confirm("Ya existen datos en la base de datos. ¿Desear continuar?"):
                click.echo("Operación cancelada.")
                return
        
        # Crear flores básicas si no existen
        flores = ['NOVELTY', 'DAISY', 'CUSHION']
        flores_obj = {}
        for flor_nombre in flores:
            flor = Flor.query.filter_by(flor=flor_nombre).first()
            if not flor:
                flor = Flor(flor=flor_nombre, flor_abrev=flor_nombre[:5])
                db.session.add(flor)
                db.session.flush()
            flores_obj[flor_nombre] = flor
        
        # Crear colores básicos si no existen
        colores = ['RED', 'YELLOW', 'WHITE', 'PINK', 'PURPLE']
        colores_obj = {}
        for color_nombre in colores:
            color = Color.query.filter_by(color=color_nombre).first()
            if not color:
                color = Color(color=color_nombre, color_abrev=color_nombre[:5])
                db.session.add(color)
                db.session.flush()
            colores_obj[color_nombre] = color
        
        # Crear combinaciones flor-color y variedades
        click.echo("Creando variedades...")
        variedades_creadas = 0
        for flor_nombre, flor in flores_obj.items():
            for color_nombre, color in colores_obj.items():
                # Verificar si existe esta combinación
                flor_color = FlorColor.query.filter_by(
                    flor_id=flor.flor_id, 
                    color_id=color.color_id
                ).first()
                
                if not flor_color:
                    flor_color = FlorColor(flor_id=flor.flor_id, color_id=color.color_id)
                    db.session.add(flor_color)
                    db.session.flush()
                
                # Crear 1-2 variedades para esta combinación
                for i in range(1, 3):
                    variedad_nombre = f"{flor_nombre} {color_nombre} {i}"
                    if not Variedad.query.filter_by(variedad=variedad_nombre).first():
                        variedad = Variedad(variedad=variedad_nombre, flor_color_id=flor_color.flor_color_id)
                        db.session.add(variedad)
                        variedades_creadas += 1
        
        # Crear bloques y camas básicos
        click.echo("Creando bloques y camas...")
        ubicaciones_creadas = 0
        for bloque_num in range(1, 4):  # 3 bloques
            bloque_nombre = str(bloque_num)
            bloque = Bloque.query.filter_by(bloque=bloque_nombre).first()
            if not bloque:
                bloque = Bloque(bloque=bloque_nombre)
                db.session.add(bloque)
                db.session.flush()
            
            for cama_num in range(1, 6):  # 5 camas por bloque
                cama_nombre = str(cama_num)
                cama = Cama.query.filter_by(cama=cama_nombre).first()
                if not cama:
                    cama = Cama(cama=cama_nombre)
                    db.session.add(cama)
                    db.session.flush()
                
                for lado_letra in ['A', 'B']:  # 2 lados por cama
                    lado = Lado.query.filter_by(lado=lado_letra).first()
                    if not lado:
                        lado = Lado(lado=lado_letra)
                        db.session.add(lado)
                        db.session.flush()
                    
                    # Crear la ubicación
                    ubicacion = BloqueCamaLado.query.filter_by(
                        bloque_id=bloque.bloque_id,
                        cama_id=cama.cama_id,
                        lado_id=lado.lado_id
                    ).first()
                    
                    if not ubicacion:
                        ubicacion = BloqueCamaLado(
                            bloque_id=bloque.bloque_id,
                            cama_id=cama.cama_id,
                            lado_id=lado.lado_id
                        )
                        db.session.add(ubicacion)
                        ubicaciones_creadas += 1
        
        # Crear áreas y densidades básicas
        click.echo("Creando áreas y densidades...")
        areas_nombres = ['50m²', '75m²', '100m²']
        areas_valores = [50.0, 75.0, 100.0]
        areas_obj = {}
        
        for nombre, valor in zip(areas_nombres, areas_valores):
            area = Area.query.filter_by(siembra=nombre).first()
            if not area:
                area = Area(siembra=nombre, area=valor)
                db.session.add(area)
                db.session.flush()
            areas_obj[nombre] = area
        
        densidades_nombres = ['ESTÁNDAR', 'ALTA', 'BAJA']
        densidades_valores = [64.0, 76.0, 48.0]
        densidades_obj = {}
        
        for nombre, valor in zip(densidades_nombres, densidades_valores):
            densidad = Densidad.query.filter_by(densidad=nombre).first()
            if not densidad:
                densidad = Densidad(densidad=nombre, valor=valor)
                db.session.add(densidad)
                db.session.flush()
            densidades_obj[nombre] = densidad
        
        # Confirmar cambios
        db.session.commit()
        click.echo(f"Dataset de prueba creado exitosamente:")
        click.echo(f"  - {variedades_creadas} variedades creadas")
        click.echo(f"  - {ubicaciones_creadas} ubicaciones creadas")
        click.echo(f"  - {len(areas_obj)} áreas creadas")
        click.echo(f"  - {len(densidades_obj)} densidades creadas")

if __name__ == "__main__":
    cli()