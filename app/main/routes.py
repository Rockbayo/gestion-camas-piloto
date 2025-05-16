# app/main/routes.py (versión mejorada)

import matplotlib
matplotlib.use('Agg')  # Configurar backend no interactivo

from flask import render_template, flash, redirect, url_for, request, current_app, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func, desc, extract, and_
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import numpy as np
from datetime import datetime, timedelta
from app import db
from app.main import bp
from app.models import (
    Siembra, Corte, Variedad, Flor, Color, FlorColor, 
    BloqueCamaLado, Bloque, Cama, Lado, Area, Densidad
)

@bp.route('/')
@login_required
def index():
    return render_template('index.html', title='Inicio')

@bp.route('/dashboard')
@login_required
def dashboard():
    # Obtener parámetros de filtro
    filtro_tiempo = request.args.get('filtro_tiempo', 'todo')
    filtro_anio = request.args.get('filtro_anio', datetime.now().year, type=int)
    filtro_mes = request.args.get('filtro_mes', datetime.now().month, type=int)
    filtro_semana = request.args.get('filtro_semana', None, type=int)
    
    # Construir las condiciones de filtro
    condiciones_filtro = []
    
    # Aplicar filtros de tiempo a las consultas
    if filtro_tiempo == 'anio':
        condiciones_filtro.append(extract('year', Corte.fecha_corte) == filtro_anio)
    elif filtro_tiempo == 'mes':
        condiciones_filtro.append(extract('year', Corte.fecha_corte) == filtro_anio)
        condiciones_filtro.append(extract('month', Corte.fecha_corte) == filtro_mes)
    elif filtro_tiempo == 'semana' and filtro_semana is not None:
        # Calcular fecha de inicio y fin de la semana seleccionada
        # La primera semana del año comienza el 1 de enero
        fecha_inicio_anio = datetime(filtro_anio, 1, 1)
        
        # Calcular el día de la semana del 1 de enero (0 = lunes, 6 = domingo)
        dia_semana_inicio = fecha_inicio_anio.weekday()
        
        # Ajustar al inicio de la semana (lunes)
        ajuste_inicio = timedelta(days=dia_semana_inicio)
        primer_lunes = fecha_inicio_anio - ajuste_inicio
        
        # Calcular inicio y fin de la semana solicitada
        inicio_semana = primer_lunes + timedelta(weeks=filtro_semana-1)
        fin_semana = inicio_semana + timedelta(days=6)
        
        condiciones_filtro.append(Corte.fecha_corte >= inicio_semana)
        condiciones_filtro.append(Corte.fecha_corte <= fin_semana)
    
    # Construir filtros combinados
    filtro_combinado = and_(*condiciones_filtro) if condiciones_filtro else True
    
    # Obtener estadísticas para el dashboard
    siembras_activas = Siembra.query.filter_by(estado='Activa').count()
    total_siembras = Siembra.query.count()
    siembras_historicas = total_siembras - siembras_activas
    
    # Calcular promedio de cortes por siembra (en lugar de total de cortes)
    promedio_cortes_query = db.session.query(
        func.count(Corte.corte_id) / func.count(func.distinct(Corte.siembra_id))
    ).filter(filtro_combinado).scalar()
    
    promedio_cortes = round(promedio_cortes_query, 2) if promedio_cortes_query else 0
    
    # Índice de aprovechamiento global
    # Este índice representa el porcentaje de tallos cortados respecto a las plantas sembradas
    # Es decir: (total_tallos_cortados / total_plantas_sembradas) * 100
    
    # Primero, obtenemos la sumatoria de tallos cortados
    total_tallos_cortados = db.session.query(func.sum(Corte.cantidad_tallos))\
        .filter(filtro_combinado).scalar() or 0
    
    # Luego, calculamos el total de plantas sembradas
    # Necesitamos obtener esta información de las siembras que tienen cortes
    query_plantas_sembradas = db.session.query(
        func.sum(Area.area * Densidad.valor)
    ).select_from(Siembra)\
      .join(Area, Siembra.area_id == Area.area_id)\
      .join(Densidad, Siembra.densidad_id == Densidad.densidad_id)\
      .join(Corte, Corte.siembra_id == Siembra.siembra_id)\
      .filter(filtro_combinado)
    
    total_plantas_sembradas = query_plantas_sembradas.scalar() or 0
    
    # Convertir ambos valores a float para evitar errores de tipos
    total_tallos_float = float(total_tallos_cortados) if total_tallos_cortados else 0
    total_plantas_float = float(total_plantas_sembradas) if total_plantas_sembradas else 0
    
    # Calculamos el índice global (porcentaje)
    # Este es el porcentaje de tallos cortados respecto a las plantas sembradas
    indice_aprovechamiento = round((total_tallos_float / total_plantas_float) * 100, 2) if total_plantas_float > 0 else 0
    
    # Cantidad total de variedades
    total_variedades = Variedad.query.count()
    
    # Agrupar todas las estadísticas
    stats = {
        'siembras_activas': siembras_activas,
        'total_siembras': total_siembras,
        'siembras_historicas': siembras_historicas,
        'promedio_cortes': promedio_cortes,
        'indice_aprovechamiento': indice_aprovechamiento,
        'total_variedades': total_variedades,
        'filtro_tiempo': filtro_tiempo,
        'filtro_anio': filtro_anio,
        'filtro_mes': filtro_mes,
        'filtro_semana': filtro_semana
    }
    
    # Últimos cortes (combinando nuevos e históricos)
    ultimos_cortes = Corte.query.order_by(Corte.fecha_corte.desc()).limit(5).all()
    
    # Últimas siembras (combinando nuevas e históricas)
    ultimas_siembras = Siembra.query.order_by(Siembra.fecha_siembra.desc()).limit(5).all()
    
    # GRÁFICO: Top 5 variedades por ÍNDICE de aprovechamiento
    # El índice de aprovechamiento es: (tallos_cortados / plantas_sembradas) * 100
    # Esto nos dice qué porcentaje de lo sembrado se aprovechó realmente
    top_variedades_query = db.session.query(
        Variedad.variedad_id,
        Variedad.variedad,
        Flor.flor,
        Color.color,
        (func.sum(Corte.cantidad_tallos) * 100.0 / 
         func.sum(Area.area * Densidad.valor)).label('indice_aprovechamiento'),
        func.sum(Corte.cantidad_tallos).label('total_tallos_cortados'),
        func.sum(Area.area * Densidad.valor).label('total_plantas_sembradas'),
        func.count(func.distinct(Siembra.siembra_id)).label('total_siembras')
    ).join(
        Siembra, Variedad.variedad_id == Siembra.variedad_id
    ).join(
        Corte, Corte.siembra_id == Siembra.siembra_id
    ).join(
        FlorColor, Variedad.flor_color_id == FlorColor.flor_color_id
    ).join(
        Flor, FlorColor.flor_id == Flor.flor_id
    ).join(
        Color, FlorColor.color_id == Color.color_id
    ).join(
        Area, Siembra.area_id == Area.area_id
    ).join(
        Densidad, Siembra.densidad_id == Densidad.densidad_id
    ).filter(filtro_combinado)\
     .group_by(
        Variedad.variedad_id,
        Variedad.variedad,
        Flor.flor,
        Color.color
    ).having(
        func.sum(Area.area * Densidad.valor) > 0
    ).order_by(
        desc('indice_aprovechamiento')
    ).limit(5).all()
    
    grafico_aprovechamiento_variedad = None
    if top_variedades_query:
        # Crear gráfico con matplotlib
        plt.figure(figsize=(10, 6))
        
        # Extraer datos para el gráfico
        variedades = [r.variedad for r in top_variedades_query]
        indices = [float(r.indice_aprovechamiento) if r.indice_aprovechamiento is not None else 0.0 for r in top_variedades_query]
        indices = [round(indice, 2) for indice in indices]  # Redondear a 2 decimales
        
        # Crear barras con colores gradientes según el aprovechamiento
        bars = plt.bar(variedades, indices, color=plt.cm.YlGn(np.array(indices)/100))
        
        # Añadir etiquetas en las barras
        for bar, indice in zip(bars, indices):
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height,
                    f'{indice}%',
                    ha='center', va='bottom', rotation=0, fontsize=10)
        
        plt.xlabel('Variedad')
        plt.ylabel('Índice de Aprovechamiento (%)')
        plt.title('Top 5 Variedades por Índice de Aprovechamiento')
        plt.xticks(rotation=45, ha='right')
        plt.ylim(0, max(indices) * 1.2 if indices else 100)  # Ajustar escala Y
        plt.tight_layout()
        
        # Guardar gráfico en formato base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        grafico_aprovechamiento_variedad = base64.b64encode(buffer.getvalue()).decode('utf-8')
        plt.close()
    
    # NUEVO GRÁFICO: Aprovechamiento por bloque
    # El índice de aprovechamiento es: (tallos_cortados / plantas_sembradas) * 100
    # Esto muestra qué porcentaje de lo sembrado se aprovechó en cada bloque
    aprovechamiento_bloque_query = db.session.query(
        Bloque.bloque_id,
        Bloque.bloque,
        (func.sum(Corte.cantidad_tallos) * 100.0 / 
         func.sum(Area.area * Densidad.valor)).label('indice_aprovechamiento'),
        func.sum(Corte.cantidad_tallos).label('total_tallos_cortados'),
        func.sum(Area.area * Densidad.valor).label('total_plantas_sembradas'),
        func.count(func.distinct(Siembra.siembra_id)).label('total_siembras')
    ).join(
        BloqueCamaLado, Bloque.bloque_id == BloqueCamaLado.bloque_id
    ).join(
        Siembra, BloqueCamaLado.bloque_cama_id == Siembra.bloque_cama_id
    ).join(
        Corte, Corte.siembra_id == Siembra.siembra_id
    ).join(
        Area, Siembra.area_id == Area.area_id
    ).join(
        Densidad, Siembra.densidad_id == Densidad.densidad_id
    ).filter(filtro_combinado)\
     .group_by(
        Bloque.bloque_id,
        Bloque.bloque
    ).having(
        func.sum(Area.area * Densidad.valor) > 0
    ).order_by(
        desc('indice_aprovechamiento')
    ).limit(8).all()  # Limitamos a 8 bloques para visualización
    
    grafico_aprovechamiento_bloque = None
    if aprovechamiento_bloque_query:
        # Crear gráfico con matplotlib
        plt.figure(figsize=(10, 6))
        
        # Extraer datos para el gráfico
        bloques = [r.bloque for r in aprovechamiento_bloque_query]
        indices = [float(r.indice_aprovechamiento) if r.indice_aprovechamiento is not None else 0.0 for r in aprovechamiento_bloque_query]
        indices = [round(indice, 2) for indice in indices]  # Redondear a 2 decimales
        
        # Crear barras horizontales para mejor visualización de múltiples bloques
        bars = plt.barh(bloques, indices, color=plt.cm.Blues(np.array(indices)/100))
        
        # Añadir etiquetas en las barras
        for bar, indice in zip(bars, indices):
            width = bar.get_width()
            plt.text(width + 2, bar.get_y() + bar.get_height()/2.,
                    f'{indice}%',
                    ha='left', va='center', fontsize=10)
        
        plt.xlabel('Índice de Aprovechamiento (%)')
        plt.ylabel('Bloque')
        plt.title('Aprovechamiento por Bloque')
        plt.xlim(0, max(indices) * 1.1 if indices else 100)  # Ajustar escala X
        plt.tight_layout()
        
        # Guardar gráfico en formato base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        grafico_aprovechamiento_bloque = base64.b64encode(buffer.getvalue()).decode('utf-8')
        plt.close()
    
    # NUEVO GRÁFICO: Aprovechamiento por tipo de flor
    # El índice de aprovechamiento es: (tallos_cortados / plantas_sembradas) * 100
    # Esto muestra qué porcentaje de lo sembrado se aprovechó para cada tipo de flor
    aprovechamiento_flor_query = db.session.query(
        Flor.flor_id,
        Flor.flor,
        (func.sum(Corte.cantidad_tallos) * 100.0 / 
         func.sum(Area.area * Densidad.valor)).label('indice_aprovechamiento'),
        func.sum(Corte.cantidad_tallos).label('total_tallos_cortados'),
        func.sum(Area.area * Densidad.valor).label('total_plantas_sembradas'),
        func.count(func.distinct(Siembra.siembra_id)).label('total_siembras')
    ).join(
        FlorColor, Flor.flor_id == FlorColor.flor_id
    ).join(
        Variedad, FlorColor.flor_color_id == Variedad.flor_color_id
    ).join(
        Siembra, Variedad.variedad_id == Siembra.variedad_id
    ).join(
        Corte, Corte.siembra_id == Siembra.siembra_id
    ).join(
        Area, Siembra.area_id == Area.area_id
    ).join(
        Densidad, Siembra.densidad_id == Densidad.densidad_id
    ).filter(filtro_combinado)\
     .group_by(
        Flor.flor_id,
        Flor.flor
    ).having(
        func.sum(Area.area * Densidad.valor) > 0
    ).order_by(
        desc('indice_aprovechamiento')
    ).all()
    
    grafico_aprovechamiento_flor = None
    if aprovechamiento_flor_query:
        # Crear gráfico circular con matplotlib
        plt.figure(figsize=(10, 8))
        
        # Extraer datos para el gráfico
        flores = [r.flor for r in aprovechamiento_flor_query]
        indices = [float(r.indice_aprovechamiento) if r.indice_aprovechamiento is not None else 0.0 for r in aprovechamiento_flor_query]
        indices = [round(indice, 2) for indice in indices]  # Redondear a 2 decimales
        
        # Asegurar que hay valores válidos para el gráfico circular
        if flores and all(indice > 0 for indice in indices):
            # Crear gráfico circular
            plt.pie(indices, labels=flores, autopct='%1.1f%%', 
                    startangle=90, shadow=False, 
                    wedgeprops={'edgecolor': 'w', 'linewidth': 1})
            
            plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
            plt.title('Aprovechamiento por Tipo de Flor')
            plt.tight_layout()
            
            # Guardar gráfico en formato base64
            buffer = BytesIO()
            plt.savefig(buffer, format='png')
            buffer.seek(0)
            grafico_aprovechamiento_flor = base64.b64encode(buffer.getvalue()).decode('utf-8')
            plt.close()
        else:
            plt.close()
            # No hay datos o hay valores negativos/cero que no funcionan en un gráfico circular
            grafico_aprovechamiento_flor = None
    
    return render_template('dashboard.html', 
                          title='Dashboard', 
                          stats=stats, 
                          ultimos_cortes=ultimos_cortes, 
                          ultimas_siembras=ultimas_siembras,
                          grafico_aprovechamiento_variedad=grafico_aprovechamiento_variedad,
                          grafico_aprovechamiento_bloque=grafico_aprovechamiento_bloque,
                          grafico_aprovechamiento_flor=grafico_aprovechamiento_flor)

# Endpoint para limpiar base de datos
@bp.route('/limpiar-db', methods=['POST'])
@login_required
def limpiar_db():
    # Verificar que el usuario tenga permisos de administrador
    if not current_user.has_role('admin') and not current_user.has_permission('importar_datos'):
        flash('No tienes permisos para realizar esta acción', 'danger')
        return redirect(url_for('main.dashboard'))
    
    try:
        # Primero eliminar los cortes (tienen dependencias)
        db.session.query(Corte).delete()
        
        # Luego eliminar las siembras
        db.session.query(Siembra).delete()
        
        # Confirmar cambios
        db.session.commit()
        
        flash('Base de datos limpiada correctamente. Se han eliminado todos los cortes y siembras.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al limpiar la base de datos: {str(e)}', 'danger')
    
    return redirect(url_for('main.dashboard'))