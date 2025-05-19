from flask import render_template, flash, redirect, url_for, request
from flask_login import login_required, current_user
from sqlalchemy import func, desc, extract, and_
from datetime import datetime, timedelta
from app import db
from app.main import bp
from app.utils.data_utils import calc_indice_aprovechamiento, safe_int, safe_float
from app.models import Siembra, Corte, Variedad, Flor, Color, FlorColor, BloqueCamaLado, Bloque, Area, Densidad, Perdida
from .dashboard_utils import (
    get_filtered_data,
    calculate_statistics,
    generate_variety_chart,
    generate_block_chart,
    generate_flower_chart
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
    filters = {
        'time': request.args.get('filtro_tiempo', 'todo'),
        'year': request.args.get('filtro_anio', datetime.now().year, type=int),
        'month': request.args.get('filtro_mes', datetime.now().month, type=int),
        'week': request.args.get('filtro_semana', None, type=int),
        'variety_id': request.args.get('variedad_id', None, type=int)
    }

    # Obtener datos filtrados
    raw_data, selected_variety = get_filtered_data(filters)
    
    # Calcular estadísticas
    stats = calculate_statistics(filters, raw_data, selected_variety)
    
    # Generar gráficos
    variety_chart = generate_variety_chart(raw_data, selected_variety)
    block_chart = generate_block_chart(raw_data, selected_variety)
    flower_chart = generate_flower_chart(raw_data, selected_variety)
    
    # Obtener registros recientes
    recent_data = {
        'cuts': get_recent_cuts(filters),
        'plantings': get_recent_plantings(filters)
    }
    
    # Obtener lista de variedades para el selector
    varieties = Variedad.query.order_by(Variedad.variedad).all()
    
    return render_template('dashboard.html', 
                         title='Dashboard',
                         stats=stats,
                         recent_data=recent_data,
                         varieties=varieties,
                         variety_chart=variety_chart,
                         block_chart=block_chart,
                         flower_chart=flower_chart)

def get_recent_cuts(filters):
    """Obtiene los últimos cortes registrados"""
    query = Corte.query.order_by(Corte.fecha_corte.desc())
    if filters['variety_id']:
        query = query.join(Siembra).filter(Siembra.variedad_id == filters['variety_id'])
    return query.limit(5).all()

def get_recent_plantings(filters):
    """Obtiene las últimas siembras registradas"""
    query = Siembra.query.order_by(Siembra.fecha_siembra.desc())
    if filters['variety_id']:
        query = query.filter(Siembra.variedad_id == filters['variety_id'])
    return query.limit(5).all()

@bp.route('/limpiar-db', methods=['POST'])
@login_required
def limpiar_db():
    """Endpoint para limpiar la base de datos"""
    if not current_user.has_role('admin') and not current_user.has_permission('importar_datos'):
        flash('No tienes permisos para realizar esta acción', 'danger')
        return redirect(url_for('main.dashboard'))
    
    try:
        # Eliminar en orden correcto por dependencias
        db.session.query(Perdida).delete()
        db.session.query(Corte).delete()
        db.session.query(Siembra).delete()
        db.session.commit()
        flash('Base de datos limpiada correctamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al limpiar la base de datos: {str(e)}', 'danger')
    
    return redirect(url_for('main.dashboard'))