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
from app.utils.data_utils import calc_indice_aprovechamiento, safe_int, safe_float, to_float, calc_percentage
from app.models import (
    Siembra, Corte, Variedad, Flor, Color, FlorColor, 
    BloqueCamaLado, Bloque, Area, Densidad
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
    
    # Consulta para obtener datos básicos
    query = db.session.query(
        Siembra.siembra_id,
        Siembra.fecha_siembra,
        Siembra.estado,
        Variedad.variedad_id,
        Variedad.variedad,
        Flor.flor_id,
        Flor.flor,
        Color.color_id,
        Color.color,
        Bloque.bloque_id,
        Bloque.bloque,
        func.count(Corte.corte_id).label('total_cortes'),
        func.sum(Corte.cantidad_tallos).label('total_tallos'),
        Area.area,
        Densidad.valor.label('densidad'),
        func.count(func.distinct(Siembra.siembra_id)).label('total_siembras')
    ).join(
        Siembra.variedad
    ).join(
        Variedad.flor_color
    ).join(
        FlorColor.flor
    ).join(
        FlorColor.color
    ).join(
        Siembra.bloque_cama
    ).join(
        BloqueCamaLado.bloque
    ).join(
        Siembra.area
    ).join(
        Siembra.densidad
    ).outerjoin(
        Corte, Siembra.siembra_id == Corte.siembra_id
    )
    
    # Aplicar filtros según los parámetros
    if filtro_variedad:
        query = query.filter(Variedad.variedad_id == filtro_variedad)
        variedad_seleccionada = Variedad.query.get(filtro_variedad)
    else:
        variedad_seleccionada = None
    
    # Aplicar filtros de tiempo
    if filtro_tiempo == 'anio':
        query = query.filter(extract('year', Siembra.fecha_siembra) == filtro_anio)
    elif filtro_tiempo == 'mes':
        query = query.filter(
            and_(
                extract('year', Siembra.fecha_siembra) == filtro_anio,
                extract('month', Siembra.fecha_siembra) == filtro_mes
            )
        )
    elif filtro_tiempo == 'semana' and filtro_semana:
        # Filtrar por semana requiere un cálculo más complejo
        fecha_inicio = datetime.strptime(f'{filtro_anio}-W{filtro_semana}-1', '%Y-W%W-%w')
        fecha_fin = fecha_inicio + timedelta(days=6)
        query = query.filter(Siembra.fecha_siembra.between(fecha_inicio, fecha_fin))
    
    # Agrupar y ordenar los resultados
    query = query.group_by(
        Siembra.siembra_id,
        Siembra.fecha_siembra,
        Siembra.estado,
        Variedad.variedad_id,
        Variedad.variedad,
        Flor.flor_id,
        Flor.flor,
        Color.color_id,
        Color.color,
        Bloque.bloque_id,
        Bloque.bloque,
        Area.area,
        Densidad.valor
    ).order_by(desc('total_tallos'))
    
    # Ejecutar la consulta
    datos_brutos = query.all()
    
    # Cálculos iniciales de estadísticas
    siembras_activas = Siembra.query.filter_by(estado='Activa').count()
    siembras_historicas = Siembra.query.filter_by(estado='Finalizada').count()
    total_siembras = siembras_activas + siembras_historicas
    total_variedades = Variedad.query.count()
    
    # Calcular promedio de cortes por siembra
    if total_siembras > 0:
        total_cortes = Corte.query.count()
        promedio_cortes = round(total_cortes / total_siembras, 1)
    else:
        promedio_cortes = 0
    
    # 1. Obtener total de tallos cortados - con los mismos filtros
    total_tallos_query = db.session.query(func.sum(Corte.cantidad_tallos)).select_from(Corte).\
        join(Siembra, Corte.siembra_id == Siembra.siembra_id)
    
    # Aplicar los filtros a la consulta de tallos
    if filtro_variedad:
        total_tallos_query = total_tallos_query.filter(Siembra.variedad_id == filtro_variedad)
    
    if filtro_tiempo == 'anio':
        total_tallos_query = total_tallos_query.filter(extract('year', Siembra.fecha_siembra) == filtro_anio)
    elif filtro_tiempo == 'mes':
        total_tallos_query = total_tallos_query.filter(
            and_(
                extract('year', Siembra.fecha_siembra) == filtro_anio,
                extract('month', Siembra.fecha_siembra) == filtro_mes
            )
        )
    elif filtro_tiempo == 'semana' and filtro_semana:
        fecha_inicio = datetime.strptime(f'{filtro_anio}-W{filtro_semana}-1', '%Y-W%W-%w')
        fecha_fin = fecha_inicio + timedelta(days=6)
        total_tallos_query = total_tallos_query.filter(Siembra.fecha_siembra.between(fecha_inicio, fecha_fin))
    
    # Ejecutar la consulta para obtener el total de tallos
    total_tallos = total_tallos_query.scalar() or 0
    
    # 2. Calcular total de plantas de manera más precisa
    # Consulta para calcular total de plantas sembradas
    total_plantas_query = db.session.query(
        func.sum(Area.area * Densidad.valor).label('total_plantas')
    ).select_from(Siembra).\
        join(Area, Siembra.area_id == Area.area_id).\
        join(Densidad, Siembra.densidad_id == Densidad.densidad_id)
    
    # Aplicar los mismos filtros que se aplicaron a la consulta principal
    if filtro_variedad:
        total_plantas_query = total_plantas_query.filter(Siembra.variedad_id == filtro_variedad)
    
    if filtro_tiempo == 'anio':
        total_plantas_query = total_plantas_query.filter(extract('year', Siembra.fecha_siembra) == filtro_anio)
    elif filtro_tiempo == 'mes':
        total_plantas_query = total_plantas_query.filter(
            and_(
                extract('year', Siembra.fecha_siembra) == filtro_anio,
                extract('month', Siembra.fecha_siembra) == filtro_mes
            )
        )
    elif filtro_tiempo == 'semana' and filtro_semana:
        fecha_inicio = datetime.strptime(f'{filtro_anio}-W{filtro_semana}-1', '%Y-W%W-%w')
        fecha_fin = fecha_inicio + timedelta(days=6)
        total_plantas_query = total_plantas_query.filter(Siembra.fecha_siembra.between(fecha_inicio, fecha_fin))
    
    # Ejecutar la consulta para calcular el total de plantas
    total_plantas = total_plantas_query.scalar() or 0
    
    # 3. Calcular el índice de aprovechamiento
    # Asegurarse de manejar el caso cuando total_plantas sea cero
    if total_plantas > 0:
        indice_aprovechamiento = round((total_tallos / total_plantas) * 100, 2)
    else:
        indice_aprovechamiento = 0
    
    # 3. CALCULAR DATOS PARA GRÁFICO DE APROVECHAMIENTO POR VARIEDAD
    # Agrupar datos por variedad con manejo consistente de tipos numéricos
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
        
        # Usar safe_int en lugar de to_int
        datos_por_variedad[d.variedad_id]['total_tallos'] += safe_int(d.total_tallos)
        # Usar safe_float en lugar de to_float
        plantas_calculadas = safe_float(d.area) * safe_float(d.densidad) if d.area and d.densidad else 0
        datos_por_variedad[d.variedad_id]['total_plantas'] += plantas_calculadas
        datos_por_variedad[d.variedad_id]['total_siembras'] += safe_int(d.total_siembras)
    
    # Calcular índices para cada variedad de manera consistente
    datos_variedades = []
    for var_id, datos in datos_por_variedad.items():
        if datos['total_plantas'] > 0:
            # Usar calc_indice_aprovechamiento que ya está importado
            indice = float(calc_indice_aprovechamiento(datos['total_tallos'], datos['total_plantas']))
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
        
        # Usar safe_int y safe_float
        datos_por_flor[d.flor_id]['total_tallos'] += safe_int(d.total_tallos)
        plantas_calculadas = safe_float(d.area) * safe_float(d.densidad) if d.area and d.densidad else 0
        datos_por_flor[d.flor_id]['total_plantas'] += plantas_calculadas
        datos_por_flor[d.flor_id]['total_siembras'] += safe_int(d.total_siembras)
    
    # Calcular índices para cada tipo de flor
    datos_flores = []
    for flor_id, datos in datos_por_flor.items():
        if datos['total_plantas'] > 0:
            indice = to_float(calc_percentage(datos['total_tallos'], datos['total_plantas']))
            datos_flores.append({
                'flor_id': datos['flor_id'],
                'flor': datos['flor'],
                'indice_aprovechamiento': round(indice, 2),
                'total_tallos': datos['total_tallos'],
                'total_plantas': datos['total_plantas'],
                'total_siembras': datos['total_siembras']
            })
    
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
        
        # Usar safe_int y safe_float
        datos_por_bloque[d.bloque_id]['total_tallos'] += safe_int(d.total_tallos)
        plantas_calculadas = safe_float(d.area) * safe_float(d.densidad) if d.area and d.densidad else 0
        datos_por_bloque[d.bloque_id]['total_plantas'] += plantas_calculadas
        datos_por_bloque[d.bloque_id]['total_siembras'] += safe_int(d.total_siembras)
    
    # Calcular índices para cada bloque
    datos_bloques = []
    for bloque_id, datos in datos_por_bloque.items():
        if datos['total_plantas'] > 0:
            indice = to_float(calc_percentage(datos['total_tallos'], datos['total_plantas']))
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
    
    # 6. GENERAR GRÁFICOS
    # Mantener la generación de gráficos igual, pero usando los datos con tipos 
    # coherentes calculados arriba
    
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

class Perdida(db.Model):
    __tablename__ = 'perdidas'
    perdida_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    siembra_id = db.Column(db.Integer, db.ForeignKey('siembras.siembra_id'), nullable=False)
    fecha_perdida = db.Column(db.Date, nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    motivo = db.Column(db.String(255))
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.usuario_id'), nullable=False)
    fecha_registro = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relaciones
    siembra = db.relationship('Siembra', backref='perdidas')
    usuario = db.relationship('Usuario', backref='perdidas_registradas')
    
    def __repr__(self):
        return f'<Perdida {self.perdida_id}>'

# Endpoint para limpiar base de datos
@bp.route('/limpiar-db', methods=['POST'])
@login_required
def limpiar_db():
    # Verificar que el usuario tenga permisos de administrador
    if not current_user.has_role('admin') and not current_user.has_permission('importar_datos'):
        flash('No tienes permisos para realizar esta acción', 'danger')
        return redirect(url_for('main.dashboard'))
    
    try:
        # Primero eliminar los registros de la tabla perdidas
        db.session.query(Perdida).delete()
        
        # Luego eliminar los cortes (tienen dependencias)
        db.session.query(Corte).delete()
        
        # Finalmente eliminar las siembras
        db.session.query(Siembra).delete()
        
        # Confirmar cambios
        db.session.commit()
        
        flash('Base de datos limpiada correctamente. Se han eliminado todos los cortes, pérdidas y siembras.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al limpiar la base de datos: {str(e)}', 'danger')
    
    return redirect(url_for('main.dashboard'))