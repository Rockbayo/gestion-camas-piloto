#!/usr/bin/env python3
"""
Script para establecer la fecha_fin_corte en siembras ya finalizadas.
"""
import os
import sys
import click
from sqlalchemy import text

# Ajustar la ruta para importar la aplicación
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app, db
from app.models import Siembra, Corte

def establecer_fechas_fin_corte():
    """Establece la fecha_fin_corte para siembras finalizadas"""
    app = create_app()
    
    with app.app_context():
        # Obtener siembras finalizadas sin fecha_fin_corte
        siembras = Siembra.query.filter_by(estado='Finalizada').filter(Siembra.fecha_fin_corte == None).all()
        
        if not siembras:
            click.echo("No hay siembras finalizadas sin fecha de fin de corte.")
            return
        
        click.echo(f"Encontradas {len(siembras)} siembras finalizadas sin fecha de fin de corte.")
        
        actualizadas = 0
        for siembra in siembras:
            # Si hay cortes, usar la fecha del último corte
            if siembra.cortes:
                ultima_fecha = max([corte.fecha_corte for corte in siembra.cortes])
                siembra.fecha_fin_corte = ultima_fecha
                actualizadas += 1
            # Si no hay cortes y es histórica, usar fecha fin calculada desde fecha inicio + 180 días
            elif siembra.fecha_inicio_corte:
                from datetime import timedelta
                siembra.fecha_fin_corte = siembra.fecha_inicio_corte + timedelta(days=180)
                actualizadas += 1
        
        db.session.commit()
        click.echo(f"Se actualizaron {actualizadas} siembras con fecha de fin de corte.")

if __name__ == "__main__":
    establecer_fechas_fin_corte()