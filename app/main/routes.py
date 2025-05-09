# Primero configurar el backend antes de importar pyplot
import matplotlib
matplotlib.use('Agg')  # Configurar backend no interactivo


# Importar las librerías necesarias
from flask import jsonify, render_template, request, send_file, url_for, current_app
import json
from flask_login import login_required
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from sqlalchemy import func, desc
import numpy as np
from io import BytesIO
import base64
import matplotlib.pyplot as plt
from app import db
from app.reportes import reportes
from app.models import Siembra, Corte, Variedad, Flor, Color, FlorColor, BloqueCamaLado, Bloque, Cama, Lado, Area, Densidad

@reportes.route('/')
@login_required
def index():
    return render_template('index.html', title='Inicio')

@reportes.route('/dashboard')
@login_required
def dashboard():
    # Obtener estadísticas para el dashboard
    siembras_activas = Siembra.query.filter_by(estado='Activa').count()
    total_siembras = Siembra.query.count()
    siembras_historicas = total_siembras - siembras_activas
    
    total_cortes = Corte.query.count()
    total_tallos = db.session.query(func.sum(Corte.cantidad_tallos)).scalar() or 0
    total_variedades = Variedad.query.count()
    
    # Calcular promedio de tallos por siembra
    promedio_tallos = 0
    if total_siembras > 0:
        promedio_tallos = round(total_tallos / total_siembras, 2)
    
    stats = {
        'siembras_activas': siembras_activas,
        'total_siembras': total_siembras,
        'siembras_historicas': siembras_historicas,
        'total_cortes': total_cortes,
        'total_tallos': total_tallos,
        'promedio_tallos': promedio_tallos,
        'total_variedades': total_variedades
    }
    
    # Obtener últimos cortes (combinando nuevos e históricos)
    ultimos_cortes = Corte.query.order_by(Corte.fecha_corte.desc()).limit(10).all()
    
    # Obtener últimas siembras (combinando nuevas e históricas)
    ultimas_siembras = Siembra.query.order_by(Siembra.fecha_siembra.desc()).limit(10).all()
    
    # Crear gráfico de producción por variedad para el dashboard
    produccion_por_variedad = db.session.query(
        Variedad.variedad,
        func.sum(Corte.cantidad_tallos).label('total_tallos')
    ).join(
        Corte.siembra
    ).join(
        Siembra.variedad
    ).group_by(
        Variedad.variedad
    ).order_by(
        desc('total_tallos')
    ).limit(5).all()
    
    grafico_produccion = None
    if produccion_por_variedad:
        # Crear gráfico con matplotlib
        plt.figure(figsize=(10, 6))
        plt.bar([r.variedad for r in produccion_por_variedad], 
               [r.total_tallos for r in produccion_por_variedad])
        plt.xlabel('Variedad')
        plt.ylabel('Total de Tallos')
        plt.title('Top 5 Variedades por Producción')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        # Guardar gráfico en formato base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        grafico_produccion = base64.b64encode(buffer.getvalue()).decode('utf-8')
        plt.close()
        
    # Crear gráfico de tendencias mensuales
    tendencia_mensual = None
    try:
        # Consulta para obtener datos de producción por mes
        datos_mensuales = db.session.query(
            func.year(Corte.fecha_corte).label('year'),
            func.month(Corte.fecha_corte).label('month'),
            func.sum(Corte.cantidad_tallos).label('total_tallos')
        ).group_by(
            'year', 'month'
        ).order_by(
            'year', 'month'
        ).all()
        
        if datos_mensuales:
            # Preparar datos para gráfico
            meses = [f"{r.year}-{r.month:02d}" for r in datos_mensuales]
            tallos = [r.total_tallos for r in datos_mensuales]
            
            # Crear gráfico de línea
            plt.figure(figsize=(10, 6))
            plt.plot(meses, tallos, marker='o', linestyle='-')
            plt.xlabel('Mes')
            plt.ylabel('Total de Tallos')
            plt.title('Tendencia de Producción Mensual (Históricos + Nuevos)')
            plt.xticks(rotation=45, ha='right')
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            
            # Guardar gráfico en formato base64
            buffer = BytesIO()
            plt.savefig(buffer, format='png')
            buffer.seek(0)
            tendencia_mensual = base64.b64encode(buffer.getvalue()).decode('utf-8')
            plt.close()
    except Exception as e:
        print(f"Error al generar gráfico de tendencia mensual: {str(e)}")
    
    return render_template('dashboard.html', 
                          title='Dashboard', 
                          stats=stats, 
                          ultimos_cortes=ultimos_cortes, 
                          ultimas_siembras=ultimas_siembras,
                          grafico_produccion=grafico_produccion,
                          tendencia_mensual=tendencia_mensual)