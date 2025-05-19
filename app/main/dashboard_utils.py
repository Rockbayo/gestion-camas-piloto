from sqlalchemy import func, extract, and_, desc
from datetime import datetime, timedelta
from app import db
from app.models import Siembra, Corte, Variedad, Area, Densidad, Flor, Color, Bloque, BloqueCamaLado, FlorColor

def get_filtered_data(filters):
    """Obtiene datos filtrados según los parámetros"""
    query = db.session.query(
        Siembra.siembra_id,
        Siembra.fecha_siembra,
        Siembra.estado,
        Variedad.variedad_id,
        Variedad.variedad,
        Flor.flor,
        Color.color,
        Bloque.bloque,
        func.count(Corte.corte_id).label('total_cortes'),
        func.sum(Corte.cantidad_tallos).label('total_tallos'),
        Area.area,
        Densidad.valor.label('densidad')
    ).join(
        Variedad, Siembra.variedad_id == Variedad.variedad_id
    ).join(
        Variedad.flor_color
    ).join(
        FlorColor.flor
    ).join(
        FlorColor.color
    ).join(
        BloqueCamaLado, Siembra.bloque_cama_id == BloqueCamaLado.bloque_cama_id
    ).join(
        Bloque, BloqueCamaLado.bloque_id == Bloque.bloque_id
    ).join(
        Area, Siembra.area_id == Area.area_id
    ).join(
        Densidad, Siembra.densidad_id == Densidad.densidad_id
    ).outerjoin(
        Corte, Siembra.siembra_id == Corte.siembra_id
    )
    
    # Aplicar filtros
    if filters['variety_id']:
        query = query.filter(Variedad.variedad_id == filters['variety_id'])
    
    if filters['time'] == 'year':
        query = query.filter(extract('year', Siembra.fecha_siembra) == filters['year'])
    elif filters['time'] == 'month':
        query = query.filter(
            and_(
                extract('year', Siembra.fecha_siembra) == filters['year'],
                extract('month', Siembra.fecha_siembra) == filters['month']
            )
        )
    elif filters['time'] == 'week' and filters['week']:
        start_date = datetime.strptime(f"{filters['year']}-W{filters['week']}-1", '%Y-W%W-%w')
        end_date = start_date + timedelta(days=6)
        query = query.filter(Siembra.fecha_siembra.between(start_date, end_date))
    
    query = query.group_by(
        Siembra.siembra_id, Variedad.variedad_id, Flor.flor_id, 
        Color.color_id, Bloque.bloque_id, Area.area_id, Densidad.densidad_id
    ).order_by(desc('total_tallos'))
    
    selected_variety = Variedad.query.get(filters['variety_id']) if filters['variety_id'] else None
    return query.all(), selected_variety

def calculate_statistics(filters, raw_data, selected_variety):
    """Calcula las estadísticas principales del dashboard"""
    # Consultas básicas
    active_plantings = Siembra.query.filter_by(estado='Activa').count()
    historical_plantings = Siembra.query.filter_by(estado='Finalizada').count()
    total_plantings = active_plantings + historical_plantings
    total_varieties = Variedad.query.count()
    
    # Calcular promedio de cortes
    total_cuts = Corte.query.count()
    avg_cuts = round(total_cuts / total_plantings, 1) if total_plantings > 0 else 0
    
    # Calcular tallos totales
    total_stems = sum(safe_int(row.total_tallos) for row in raw_data)
    
    # Calcular plantas totales
    total_plants = sum(safe_float(row.area) * safe_float(row.densidad) for row in raw_data if row.area and row.densidad)
    
    # Calcular índice de aprovechamiento
    utilization_index = round((total_stems / total_plants) * 100, 2) if total_plants > 0 else 0
    
    return {
        'active_plantings': active_plantings,
        'historical_plantings': historical_plantings,
        'total_plantings': total_plantings,
        'total_varieties': total_varieties,
        'avg_cuts': avg_cuts,
        'utilization_index': utilization_index,
        'total_stems': total_stems,
        'filters': filters,
        'selected_variety': selected_variety
    }

def generate_variety_chart(raw_data, selected_variety):
    """Genera el gráfico de aprovechamiento por variedad"""
    # Procesamiento de datos y generación de gráfico
    # (Implementación similar a la original pero más modular)
    pass

def generate_block_chart(raw_data, selected_variety):
    """Genera el gráfico de aprovechamiento por bloque"""
    # Procesamiento de datos y generación de gráfico
    pass

def generate_flower_chart(raw_data, selected_variety):
    """Genera el gráfico de aprovechamiento por tipo de flor"""
    # Procesamiento de datos y generación de gráfico
    pass