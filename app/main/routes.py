# Implementación completa de app/main/routes.py
# Solución unificada para el cálculo de índices de aprovechamiento

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
from decimal import Decimal
from app import db
from app.main import bp
from app.models import (
    Siembra, Corte, Variedad, Flor, Color, FlorColor, 
    BloqueCamaLado, Bloque, Cama, Lado, Area, Densidad
)

@bp.route('/')
@login_required
def index():
    """Vista principal del sistema."""
    return render_template('index.html', title='Inicio')

@bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard con estadísticas y visualizaciones."""
    # Obtener parámetros de filtro
    filtro_tiempo = request.args.get('filtro_tiempo', 'todo')
    filtro_anio = request.args.get('filtro_anio', datetime.now().year, type=int)
    filtro_mes = request.args.get('filtro_mes', datetime.now().month, type=int)
    filtro_semana = request.args.get('filtro_semana', None, type=int)
    filtro_variedad = request.args.get('variedad_id', None, type=int)
    
    # Construir condiciones de filtro
    condiciones_filtro = []
    condiciones_siembras = []
    
    # Aplicar filtros de tiempo
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
    
    # Filtro por variedad si es necesario
    if filtro_variedad:
        condiciones_siembras.append(Siembra.variedad_id == filtro_variedad)
    
    # Construir filtros combinados
    filtro_cortes = and_(*condiciones_filtro) if condiciones_filtro else True
    filtro_siembras = and_(*condiciones_siembras) if condiciones_siembras else True
    
    # Obtener datos brutos con una sola consulta para todos los cálculos
    # Esto garantiza consistencia en todos los cálculos
    datos_brutos = db.session.query(
        Variedad.variedad_id,
        Variedad.variedad,
        Flor.flor_id,
        Flor.flor,
        Color.color_id,
        Color.color,
        Bloque.bloque_id,
        Bloque.bloque,
        func.sum(Corte.cantidad_tallos).label('total_tallos'),
        func.sum(Area.area * Densidad.valor).label('total_plantas'),
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
        BloqueCamaLado, Siembra.bloque_cama_id == BloqueCamaLado.bloque_cama_id
    ).join(
        Bloque, BloqueCamaLado.bloque_id == Bloque.bloque_id
    ).join(
        Area, Siembra.area_id == Area.area_id
    ).join(
        Densidad, Siembra.densidad_id == Densidad.densidad_id
    ).filter(
        Siembra.estado == 'Finalizada'
    )
    
    # Aplicar filtros
    if condiciones_filtro:
        datos_brutos = datos_brutos.filter(filtro_cortes)
    if condiciones_siembras:
        datos_brutos = datos_brutos.filter(filtro_siembras)
    if filtro_variedad:
        datos_brutos = datos_brutos.filter(Siembra.variedad_id == filtro_variedad)
    
    # Agrupar por los campos relevantes
    datos_brutos = datos_brutos.group_by(
        Variedad.variedad_id,
        Variedad.variedad,
        Flor.flor_id,
        Flor.flor,
        Color.color_id,
        Color.color,
        Bloque.bloque_id,
        Bloque.bloque
    ).all()
    
    # 1. CALCULAR ESTADÍSTICAS GLOBALES
    total_tallos_global = sum(d.total_tallos for d in datos_brutos)
    total_plantas_global = sum(d.total_plantas for d in datos_brutos)
    
    # Calcular índice de aprovechamiento global
    indice_aprovechamiento = 0
    if total_plantas_global > 0:
        indice_aprovechamiento = round((Decimal(total_tallos_global) / Decimal(total_plantas_global)) * Decimal('100'), 2)
    
    print(f"DEBUG - Índice global: {indice_aprovechamiento}% (Tallos: {total_tallos_global}, Plantas: {total_plantas_global})")
    
    # 2. ESTADÍSTICAS GENERALES PARA EL DASHBOARD
    siembras_query = Siembra.query
    if filtro_variedad:
        siembras_query = siembras_query.filter(Siembra.variedad_id == filtro_variedad)
    if condiciones_siembras:
        siembras_query = siembras_query.filter(filtro_siembras)
    
    siembras_activas = siembras_query.filter_by(estado='Activa').count()
    total_siembras = siembras_query.count()
    siembras_historicas = total_siembras - siembras_activas
    
    # Calcular promedio de cortes por siembra
    cortes_query = db.session.query(
        func.count(Corte.corte_id),
        func.count(func.distinct(Corte.siembra_id))
    ).filter(filtro_cortes)
    
    if filtro_variedad:
        cortes_query = cortes_query.join(Siembra, Corte.siembra_id == Siembra.siembra_id).\
                            filter(Siembra.variedad_id == filtro_variedad)
    
    total_cortes, total_siembras_con_cortes = cortes_query.first()
    promedio_cortes = round(total_cortes / total_siembras_con_cortes, 2) if total_siembras_con_cortes else 0
    
    # Cantidad total de variedades
    total_variedades = Variedad.query.count()
    
    # Obtener la variedad seleccionada si hay filtro
    variedad_seleccionada = None
    if filtro_variedad:
        variedad_seleccionada = Variedad.query.get(filtro_variedad)
    
    # 3. CALCULAR DATOS PARA GRÁFICO DE APROVECHAMIENTO POR VARIEDAD
    # Agrupar datos por variedad
    datos_por_variedad = {}
    for d in datos_brutos:
        if d.variedad_id not in datos_por_variedad:
            datos_por_variedad[d.variedad_id] = {
                'variedad_id': d.variedad_id,
                'variedad': d.variedad,
                'flor': d.flor,
                'color': d.color,
                'total_tallos': 0,
                'total_plantas': 0,
                'total_siembras': 0
            }
        
        datos_por_variedad[d.variedad_id]['total_tallos'] += d.total_tallos
        datos_por_variedad[d.variedad_id]['total_plantas'] += d.total_plantas
        datos_por_variedad[d.variedad_id]['total_siembras'] += d.total_siembras
    
    # Calcular índices para cada variedad de manera consistente
    datos_variedades = []
    for var_id, datos in datos_por_variedad.items():
        if datos['total_plantas'] > 0:
            indice = (Decimal(datos['total_tallos']) / Decimal(datos['total_plantas'])) * Decimal('100')
            datos_variedades.append({
                'variedad_id': datos['variedad_id'],
                'variedad': datos['variedad'],
                'flor': datos['flor'],
                'color': datos['color'],
                'indice_aprovechamiento': round(indice, 2),
                'total_tallos': datos['total_tallos'],
                'total_plantas': datos['total_plantas'],
                'total_siembras': datos['total_siembras']
            })
    
    # Ordenar por índice y limitar a top 5
    datos_variedades.sort(key=lambda x: x['indice_aprovechamiento'], reverse=True)
    top_variedades = datos_variedades[:5]
    
    # Para depuración
    print("DEBUG - Índices de aprovechamiento por variedad:")
    for v in top_variedades:
        print(f"{v['variedad']}: {v['indice_aprovechamiento']}% (Tallos: {v['total_tallos']}, Plantas: {v['total_plantas']})")
    
    # 4. CALCULAR DATOS PARA GRÁFICO DE APROVECHAMIENTO POR TIPO DE FLOR
    datos_por_flor = {}
    for d in datos_brutos:
        if d.flor_id not in datos_por_flor:
            datos_por_flor[d.flor_id] = {
                'flor_id': d.flor_id,
                'flor': d.flor,
                'total_tallos': 0,
                'total_plantas': 0,
                'total_siembras': 0
            }
        
        datos_por_flor[d.flor_id]['total_tallos'] += d.total_tallos
        datos_por_flor[d.flor_id]['total_plantas'] += d.total_plantas
        datos_por_flor[d.flor_id]['total_siembras'] += d.total_siembras
    
    # Calcular índices para cada tipo de flor
    datos_flores = []
    for flor_id, datos in datos_por_flor.items():
        if datos['total_plantas'] > 0:
            indice = (Decimal(datos['total_tallos']) / Decimal(datos['total_plantas'])) * Decimal('100')
            datos_flores.append({
                'flor_id': datos['flor_id'],
                'flor': datos['flor'],
                'indice_aprovechamiento': round(indice, 2),
                'total_tallos': datos['total_tallos'],
                'total_plantas': datos['total_plantas'],
                'total_siembras': datos['total_siembras']
            })
    
    # Para depuración
    print("DEBUG - Índices de aprovechamiento por tipo de flor:")
    for f in datos_flores:
        print(f"{f['flor']}: {f['indice_aprovechamiento']}% (Tallos: {f['total_tallos']}, Plantas: {f['total_plantas']})")
    
    # 5. CALCULAR DATOS PARA GRÁFICO DE APROVECHAMIENTO POR BLOQUE
    datos_por_bloque = {}
    for d in datos_brutos:
        if d.bloque_id not in datos_por_bloque:
            datos_por_bloque[d.bloque_id] = {
                'bloque_id': d.bloque_id,
                'bloque': d.bloque,
                'total_tallos': 0,
                'total_plantas': 0,
                'total_siembras': 0
            }
        
        datos_por_bloque[d.bloque_id]['total_tallos'] += d.total_tallos
        datos_por_bloque[d.bloque_id]['total_plantas'] += d.total_plantas
        datos_por_bloque[d.bloque_id]['total_siembras'] += d.total_siembras
    
    # Calcular índices para cada bloque
    datos_bloques = []
    for bloque_id, datos in datos_por_bloque.items():
        if datos['total_plantas'] > 0:
            indice = (Decimal(datos['total_tallos'])) / (Decimal(datos['total_plantas'])) * 100
            datos_bloques.append({
                'bloque_id': datos['bloque_id'],
                'bloque': datos['bloque'],
                'indice_aprovechamiento': round(indice, 2),
                'total_tallos': datos['total_tallos'],
                'total_plantas': datos['total_plantas'],
                'total_siembras': datos['total_siembras']
            })
    
    # Ordenar por índice y limitar a top 8
    datos_bloques.sort(key=lambda x: x['indice_aprovechamiento'], reverse=True)
    top_bloques = datos_bloques[:8]
    
    # Para depuración
    print("DEBUG - Índices de aprovechamiento por bloque:")
    for b in top_bloques:
        print(f"{b['bloque']}: {b['indice_aprovechamiento']}% (Tallos: {b['total_tallos']}, Plantas: {b['total_plantas']})")
    
    # 6. GENERAR GRÁFICOS
    
    # Gráfico de aprovechamiento por variedad
    grafico_aprovechamiento_variedad = None
    if top_variedades:
        plt.figure(figsize=(10, 6))
        variedades = [v['variedad'] for v in top_variedades]
        indices = [v['indice_aprovechamiento'] for v in top_variedades]
        
        # Crear barras con colores gradientes según el aprovechamiento
        bars = plt.bar(variedades, indices, color=plt.cm.YlGn(np.array(indices)/100))
        
        # Añadir etiquetas
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
        
        # Ajustar escala Y
        y_max = max(100, max(indices) * 1.1) if indices else 100
        plt.ylim(0, min(y_max, 100))  # Limitar a un máximo de 100%
        
        plt.tight_layout()
        
        # Guardar gráfico en formato base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        grafico_aprovechamiento_variedad = base64.b64encode(buffer.getvalue()).decode('utf-8')
        plt.close()
    
    # Gráfico de aprovechamiento por bloque
    grafico_aprovechamiento_bloque = None
    if top_bloques:
        plt.figure(figsize=(10, 6))
        bloques = [b['bloque'] for b in top_bloques]
        indices = [b['indice_aprovechamiento'] for b in top_bloques]
        
        # Crear barras horizontales
        bars = plt.barh(bloques, indices, color=plt.cm.Blues(np.array(indices)/100))
        
        # Añadir etiquetas
        for bar, indice in zip(bars, indices):
            width = bar.get_width()
            plt.text(width + 2, bar.get_y() + bar.get_height()/2.,
                    f'{indice}%',
                    ha='left', va='center', fontsize=10)
        
        plt.xlabel('Índice de Aprovechamiento (%)')
        plt.ylabel('Bloque')
        
        # Ajustar título con variedad si está filtrado
        if filtro_variedad and variedad_seleccionada:
            plt.title(f'Aprovechamiento por Bloque: {variedad_seleccionada.variedad}')
        else:
            plt.title('Aprovechamiento por Bloque')
        
        # Ajustar escala X
        x_max = max(100, max(indices) * 1.1) if indices else 100
        plt.xlim(0, min(x_max, 100))
        
        plt.tight_layout()
        
        # Guardar gráfico en formato base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        grafico_aprovechamiento_bloque = base64.b64encode(buffer.getvalue()).decode('utf-8')
        plt.close()
    
    # Gráfico de aprovechamiento por tipo de flor
    grafico_aprovechamiento_flor = None
    if datos_flores:
        plt.figure(figsize=(10, 8))
        flores = [f['flor'] for f in datos_flores]
        indices = [f['indice_aprovechamiento'] for f in datos_flores]
        
        # Verificar que hay valores válidos para el gráfico circular
        if flores and all(indice > 0 for indice in indices):
            plt.pie(indices, labels=flores, autopct='%1.1f%%', 
                    startangle=90, shadow=False, 
                    wedgeprops={'edgecolor': 'w', 'linewidth': 1})
            
            plt.axis('equal')
            
            # Ajustar título según variedad filtrada
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
    
    # Últimos cortes y siembras
    ultimos_cortes_query = Corte.query.order_by(Corte.fecha_corte.desc())
    ultimas_siembras_query = Siembra.query.order_by(Siembra.fecha_siembra.desc())
    
    if filtro_variedad:
        ultimos_cortes_query = ultimos_cortes_query.join(Siembra).filter(Siembra.variedad_id == filtro_variedad)
        ultimas_siembras_query = ultimas_siembras_query.filter(Siembra.variedad_id == filtro_variedad)
        
    ultimos_cortes = ultimos_cortes_query.limit(5).all()
    ultimas_siembras = ultimas_siembras_query.limit(5).all()
    
    # Obtener lista de variedades para el selector
    variedades_list = Variedad.query.order_by(Variedad.variedad).all()
    
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