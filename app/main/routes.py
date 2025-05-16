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

def calcular_indice_aprovechamiento(query_base, filtros=None, filtro_variedad=None, solo_finalizadas=True):
    """
    Función central para calcular el índice de aprovechamiento de forma consistente.
    
    Args:
        query_base: Query base de SQLAlchemy para filtrar cortes
        filtros: Condiciones de filtro adicionales para siembras
        filtro_variedad: ID de la variedad si se está filtrando por variedad
        solo_finalizadas: Si es True, solo considera siembras finalizadas
        
    Returns:
        tuple: (indice_aprovechamiento, total_tallos, total_plantas, mensaje_debug)
    """
    # Construir consulta base de siembras
    siembras_query = Siembra.query
    
    # Aplicar filtros
    if filtros:
        siembras_query = siembras_query.filter(filtros)
    
    # Filtrar por variedad si es necesario
    if filtro_variedad:
        siembras_query = siembras_query.filter(Siembra.variedad_id == filtro_variedad)
    
    # Filtrar por estado si se requiere
    if solo_finalizadas:
        siembras_query = siembras_query.filter(Siembra.estado == 'Finalizada')
    
    # Obtener lista de IDs de siembras que cumplen con los criterios
    siembras_ids = [s.siembra_id for s in siembras_query.all()]
    
    if not siembras_ids:
        return 0, 0, 0, "No hay siembras que cumplan con los criterios"
    
    # Calcular total de tallos cortados
    total_tallos_query = db.session.query(
        func.sum(Corte.cantidad_tallos)
    ).join(
        Siembra, Corte.siembra_id == Siembra.siembra_id
    ).filter(
        Siembra.siembra_id.in_(siembras_ids)
    )
    
    # Aplicar filtros adicionales a los cortes si es necesario
    if query_base:
        total_tallos_query = total_tallos_query.filter(query_base)
    
    total_tallos_cortados = total_tallos_query.scalar() or 0
    
    # Calcular total de plantas sembradas
    total_plantas_query = db.session.query(
        func.sum(Area.area * Densidad.valor)
    ).select_from(Siembra)\
    .join(Area, Siembra.area_id == Area.area_id)\
    .join(Densidad, Siembra.densidad_id == Densidad.densidad_id)\
    .filter(
        Siembra.siembra_id.in_(siembras_ids)
    )
    
    total_plantas_sembradas = total_plantas_query.scalar() or 0
    
    # Convertir a float y calcular el índice
    total_tallos_float = float(total_tallos_cortados) if total_tallos_cortados else 0
    total_plantas_float = float(total_plantas_sembradas) if total_plantas_sembradas else 0
    
    # Calcular el índice
    indice_aprovechamiento = 0
    if total_plantas_float > 0:
        indice_aprovechamiento = (total_tallos_float / total_plantas_float) * 100
        indice_aprovechamiento = round(indice_aprovechamiento, 2)
    
    mensaje_debug = f"Tallos: {total_tallos_float}, Plantas: {total_plantas_float}, Índice: {indice_aprovechamiento}%"
    return indice_aprovechamiento, total_tallos_float, total_plantas_float, mensaje_debug

@bp.route('/')
@login_required
def index():
    return render_template('index.html', title='Inicio')

# Código actualizado para app/main/routes.py con filtro por variedad añadido

@bp.route('/dashboard')
@login_required
def dashboard():
    # Obtener parámetros de filtro
    filtro_tiempo = request.args.get('filtro_tiempo', 'todo')
    filtro_anio = request.args.get('filtro_anio', datetime.now().year, type=int)
    filtro_mes = request.args.get('filtro_mes', datetime.now().month, type=int)
    filtro_semana = request.args.get('filtro_semana', None, type=int)
    filtro_variedad = request.args.get('variedad_id', None, type=int)  # Nuevo filtro por variedad
    
    # Construir las condiciones de filtro
    condiciones_filtro = []
    condiciones_siembras = []  # Para filtros específicos sobre siembras
    
    # Aplicar filtros de tiempo a las consultas
    if filtro_tiempo == 'anio':
        condiciones_filtro.append(extract('year', Corte.fecha_corte) == filtro_anio)
        condiciones_siembras.append(extract('year', Siembra.fecha_siembra) == filtro_anio)
    elif filtro_tiempo == 'mes':
        condiciones_filtro.append(extract('year', Corte.fecha_corte) == filtro_anio)
        condiciones_filtro.append(extract('month', Corte.fecha_corte) == filtro_mes)
        condiciones_siembras.append(extract('year', Siembra.fecha_siembra) == filtro_anio)
        condiciones_siembras.append(extract('month', Siembra.fecha_siembra) == filtro_mes)
    elif filtro_tiempo == 'semana' and filtro_semana is not None:
        # Calcular fecha de inicio y fin de la semana seleccionada
        fecha_inicio_anio = datetime(filtro_anio, 1, 1)
        dia_semana_inicio = fecha_inicio_anio.weekday()
        ajuste_inicio = timedelta(days=dia_semana_inicio)
        primer_lunes = fecha_inicio_anio - ajuste_inicio
        inicio_semana = primer_lunes + timedelta(weeks=filtro_semana-1)
        fin_semana = inicio_semana + timedelta(days=6)
        
        condiciones_filtro.append(Corte.fecha_corte >= inicio_semana)
        condiciones_filtro.append(Corte.fecha_corte <= fin_semana)
        condiciones_siembras.append(Siembra.fecha_siembra >= inicio_semana)
        condiciones_siembras.append(Siembra.fecha_siembra <= fin_semana)
    
    # Filtro por variedad
    if filtro_variedad:
        condiciones_siembras.append(Siembra.variedad_id == filtro_variedad)
    
    # Construir filtros combinados
    filtro_cortes = and_(*condiciones_cortes) if condiciones_cortes else True
    filtro_siembras = and_(*condiciones_siembras) if condiciones_siembras else True

    # Usar la función centralizada para calcular el índice de aprovechamiento
    indice_aprovechamiento, total_tallos, total_plantas, debug_msg = calcular_indice_aprovechamiento(
        filtro_cortes, 
        filtro_siembras, 
        filtro_variedad, 
        solo_finalizadas=True
    )

    print(f"DEBUG - Cálculo de índice global: {debug_msg}")
    
    # Obtener estadísticas para el dashboard
    # Para el filtro de variedad, ajustamos las consultas de siembras
    if filtro_variedad:
        siembras_query = Siembra.query.filter(Siembra.variedad_id == filtro_variedad)
    else:
        siembras_query = Siembra.query
    
    # Aplicar los filtros temporales a siembras si hay alguno
    if condiciones_siembras:
        siembras_query = siembras_query.filter(filtro_siembras)
    
    siembras_activas = siembras_query.filter_by(estado='Activa').count()
    total_siembras = siembras_query.count()
    siembras_historicas = total_siembras - siembras_activas
    
    # Calcular promedio de cortes por siembra (en lugar de total de cortes)
    # Modificar para incluir el filtro de variedad si está presente
    cortes_query = db.session.query(
        func.count(Corte.corte_id),
        func.count(func.distinct(Corte.siembra_id))
    ).filter(filtro_cortes)
    
    if filtro_variedad:
        cortes_query = cortes_query.join(Siembra, Corte.siembra_id == Siembra.siembra_id)\
                                  .filter(Siembra.variedad_id == filtro_variedad)
    
    total_cortes, total_siembras_con_cortes = cortes_query.first()
    
    promedio_cortes = round(total_cortes / total_siembras_con_cortes, 2) if total_siembras_con_cortes else 0
    
    # Índice de aprovechamiento global
    # Primero, obtener solo las siembras finalizadas para un cálculo más preciso
    siembras_finalizadas = siembras_query.filter_by(estado='Finalizada')
    
    # Luego, calculamos el total de tallos cortados para estas siembras
    total_tallos_query = db.session.query(
        func.sum(Corte.cantidad_tallos)
    ).join(
        Siembra, Corte.siembra_id == Siembra.siembra_id
    ).filter(
        Siembra.siembra_id.in_([s.siembra_id for s in siembras_finalizadas])
    )
    
    if filtro_cortes is not True:
        total_tallos_query = total_tallos_query.filter(filtro_cortes)
    
    total_tallos_cortados = total_tallos_query.scalar() or 0
    
    # Y calculamos el total de plantas sembradas para las mismas siembras
    query_plantas_sembradas = db.session.query(
        func.sum(Area.area * Densidad.valor)
    ).select_from(Siembra)\
    .join(Area, Siembra.area_id == Area.area_id)\
    .join(Densidad, Siembra.densidad_id == Densidad.densidad_id)\
    .filter(
        Siembra.siembra_id.in_([s.siembra_id for s in siembras_finalizadas])
    )
    
    total_plantas_sembradas = query_plantas_sembradas.scalar() or 0
    
    # Convertir a float para evitar problemas de tipos
    total_tallos_float = float(total_tallos_cortados) if total_tallos_cortados else 0
    total_plantas_float = float(total_plantas_sembradas) if total_plantas_sembradas else 0
    
    # Calcular el índice - asegurando que sea el porcentaje correcto
    indice_aprovechamiento = 0
    if total_plantas_float > 0:
        indice_aprovechamiento = (total_tallos_float / total_plantas_float) * 100
        # Redondear a 2 decimales
        indice_aprovechamiento = round(indice_aprovechamiento, 2)
    
    # Para visualizar datos de depuración en el log
    print(f"DEBUG - Filtro variedad: {filtro_variedad}")
    print(f"DEBUG - Total tallos: {total_tallos_float}")
    print(f"DEBUG - Total plantas: {total_plantas_float}")
    print(f"DEBUG - Índice calculado: {indice_aprovechamiento}%")
    
    # Cantidad total de variedades
    total_variedades = Variedad.query.count()
    
    # Obtener la variedad seleccionada si hay filtro
    variedad_seleccionada = None
    if filtro_variedad:
        variedad_seleccionada = Variedad.query.get(filtro_variedad)
    
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
        'filtro_semana': filtro_semana,
        'filtro_variedad': filtro_variedad,
        'variedad_seleccionada': variedad_seleccionada
    }
    
    # Últimos cortes (combinando nuevos e históricos)
    # Aplicar filtro de variedad si existe
    ultimos_cortes_query = Corte.query.order_by(Corte.fecha_corte.desc())
    if filtro_variedad:
        ultimos_cortes_query = ultimos_cortes_query.join(Siembra).filter(Siembra.variedad_id == filtro_variedad)
    ultimos_cortes = ultimos_cortes_query.limit(5).all()
    
    # Últimas siembras (combinando nuevas e históricas)
    # Aplicar filtro de variedad si existe
    ultimas_siembras_query = Siembra.query.order_by(Siembra.fecha_siembra.desc())
    if filtro_variedad:
        ultimas_siembras_query = ultimas_siembras_query.filter(Siembra.variedad_id == filtro_variedad)
    ultimas_siembras = ultimas_siembras_query.limit(5).all()
    
    # GRÁFICO: Top 5 variedades por ÍNDICE de aprovechamiento
    # Si hay filtro de variedad, solo se mostrará esa variedad
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
    ).filter(
        # Importante: Solo considerar siembras finalizadas para calcular aprovechamiento real
        Siembra.estado == 'Finalizada',
        # Aplicar filtros temporales como antes
        filtro_cortes
    )
    
    # Si hay filtro de variedad, aplicarlo
    if filtro_variedad:
        top_variedades_query = top_variedades_query.filter(Variedad.variedad_id == filtro_variedad)
    
    top_variedades_query = top_variedades_query.group_by(
        Variedad.variedad_id,
        Variedad.variedad,
        Flor.flor,
        Color.color
    ).having(
        func.sum(Area.area * Densidad.valor) > 0,
        # Agregar un filtro de datos mínimos para evitar valores atípicos
        func.count(func.distinct(Siembra.siembra_id)) >= 2  # Al menos 2 siembras para estadísticas confiables
    ).order_by(
        desc('indice_aprovechamiento')
    ).limit(5).all()
    
    grafico_aprovechamiento_variedad = None
    if top_variedades_query:
        # Crear gráfico con matplotlib - MODIFICADO para escalar correctamente los valores
        plt.figure(figsize=(10, 6))
        
        # Extraer datos para el gráfico
        variedades = [r.variedad for r in top_variedades_query]
        indices = [float(r.indice_aprovechamiento) if r.indice_aprovechamiento is not None else 0.0 for r in top_variedades_query]
        indices = [round(indice, 2) for indice in indices]  # Redondear a 2 decimales
        
        # DEBUG: Imprimir valores para verificación
        print("DEBUG - Índices de aprovechamiento por variedad:")
        for v, i in zip(variedades, indices):
            print(f"{v}: {i}%")
        
        # Crear barras con colores gradientes según el aprovechamiento
        # Usar un rango de colores adecuado para valores que pueden llegar a 100%
        bars = plt.bar(variedades, indices, color=plt.cm.YlGn(np.array(indices)/100))
        
        # Añadir etiquetas en las barras
        for bar, indice in zip(bars, indices):
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height,
                    f'{indice}%',
                    ha='center', va='bottom', rotation=0, fontsize=10)
        
        plt.xlabel('Variedad')
        plt.ylabel('Índice de Aprovechamiento (%)')
        
        # Ajustar el título según si hay filtro de variedad
        if filtro_variedad and variedad_seleccionada:
            plt.title(f'Índice de Aprovechamiento: {variedad_seleccionada.variedad}')
        else:
            plt.title('Top 5 Variedades por Índice de Aprovechamiento')
            
        plt.xticks(rotation=45, ha='right')
        
        # Ajustar escala Y para acomodar valores mayores (hasta 100%)
        y_max = max(100, max(indices) * 1.1) if indices else 100
        plt.ylim(0, min(y_max, 100))  # Limitar a un máximo de 100%
        
        plt.tight_layout()
        
        # Guardar gráfico en formato base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        grafico_aprovechamiento_variedad = base64.b64encode(buffer.getvalue()).decode('utf-8')
        plt.close()
    
    # NUEVO GRÁFICO: Aprovechamiento por bloque
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
    ).filter(
        # Solo siembras finalizadas
        Siembra.estado == 'Finalizada',
        # Filtros temporales
        filtro_cortes
    )
    
    # Si hay filtro de variedad, aplicarlo
    if filtro_variedad:
        aprovechamiento_bloque_query = aprovechamiento_bloque_query.filter(Siembra.variedad_id == filtro_variedad)
    
    aprovechamiento_bloque_query = aprovechamiento_bloque_query.group_by(
        Bloque.bloque_id,
        Bloque.bloque
    ).having(
        func.sum(Area.area * Densidad.valor) > 0,
        # Asegurar datos mínimos
        func.count(func.distinct(Siembra.siembra_id)) >= 2
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
        
        # DEBUG: Imprimir valores para verificación
        print("DEBUG - Índices de aprovechamiento por bloque:")
        for b, i in zip(bloques, indices):
            print(f"{b}: {i}%")
        
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
        
        # Ajustar título si hay filtro de variedad
        if filtro_variedad and variedad_seleccionada:
            plt.title(f'Aprovechamiento por Bloque: {variedad_seleccionada.variedad}')
        else:
            plt.title('Aprovechamiento por Bloque')
        
        # Ajustar escala X para acomodar valores mayores (hasta 100%)
        x_max = max(100, max(indices) * 1.1) if indices else 100
        plt.xlim(0, min(x_max, 100))  # Limitar a un máximo de 100%
        
        plt.tight_layout()
        
        # Guardar gráfico en formato base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        grafico_aprovechamiento_bloque = base64.b64encode(buffer.getvalue()).decode('utf-8')
        plt.close()
    
    # NUEVO GRÁFICO: Aprovechamiento por tipo de flor
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
    ).filter(
        # Solo siembras finalizadas para cálculos reales
        Siembra.estado == 'Finalizada',
        # Aplicar filtros temporales como antes
        filtro_cortes
    )
    
    # Si hay filtro de variedad, aplicarlo
    if filtro_variedad:
        aprovechamiento_flor_query = aprovechamiento_flor_query.filter(Siembra.variedad_id == filtro_variedad)
    
    aprovechamiento_flor_query = aprovechamiento_flor_query.group_by(
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
        
        # DEBUG: Imprimir valores para verificación
        print("DEBUG - Índices de aprovechamiento por tipo de flor:")
        for f, i in zip(flores, indices):
            print(f"{f}: {i}%")
        
        # Asegurar que hay valores válidos para el gráfico circular
        if flores and all(indice > 0 for indice in indices):
            # Crear gráfico circular
            plt.pie(indices, labels=flores, autopct='%1.1f%%', 
                    startangle=90, shadow=False, 
                    wedgeprops={'edgecolor': 'w', 'linewidth': 1})
            
            plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
            
            # Ajustar título si hay filtro de variedad
            if filtro_variedad and variedad_seleccionada:
                plt.title(f'Aprovechamiento por Tipo de Flor: {variedad_seleccionada.variedad}')
            else:
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
    
    # Obtener lista de variedades para el selector
    variedades_list = Variedad.query.order_by(Variedad.variedad).all()
    
    return render_template('dashboard.html', 
                          title='Dashboard', 
                          stats=stats, 
                          ultimos_cortes=ultimos_cortes, 
                          ultimas_siembras=ultimas_siembras,
                          grafico_aprovechamiento_variedad=grafico_aprovechamiento_variedad,
                          grafico_aprovechamiento_bloque=grafico_aprovechamiento_bloque,
                          grafico_aprovechamiento_flor=grafico_aprovechamiento_flor,
                          variedades=variedades_list)

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