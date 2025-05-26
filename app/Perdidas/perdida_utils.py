from sqlalchemy import func
from app import db
from app.models import Siembra, Perdida, CausaPerdida, Variedad, Corte

def get_filtered_losses(filters):
    """Obtiene pérdidas filtradas según parámetros"""
    query = Perdida.query
    
    if filters.get('siembra_id'):
        query = query.filter(Perdida.siembra_id == filters['siembra_id'])
    
    if filters.get('causa_id'):
        query = query.filter(Perdida.causa_id == filters['causa_id'])
    
    if filters.get('fecha_desde'):
        try:
            fecha = datetime.strptime(filters['fecha_desde'], '%Y-%m-%d').date()
            query = query.filter(Perdida.fecha_perdida >= fecha)
        except ValueError:
            pass
    
    if filters.get('fecha_hasta'):
        try:
            fecha = datetime.strptime(filters['fecha_hasta'], '%Y-%m-%d').date()
            query = query.filter(Perdida.fecha_perdida <= fecha)
        except ValueError:
            pass
    
    return query

def calculate_available_plants(siembra, exclude_loss_id=None, full_stats=False):
    """Calcula plantas disponibles y estadísticas relacionadas"""
    if not (siembra.area and siembra.densidad):
        return None if not full_stats else {
            'total_plantas': 0,
            'total_tallos': 0,
            'total_perdidas': 0,
            'disponible': 0,
            'perdidas_por_causa': []
        }
    
    total_plantas = int(siembra.area.area * siembra.densidad.valor)
    
    # Corregir: usar int() para evitar problemas de tipos
    total_tallos = int(db.session.query(func.sum(Corte.cantidad_tallos))\
                    .filter(Corte.siembra_id == siembra.siembra_id).scalar() or 0)
    
    query = db.session.query(func.sum(Perdida.cantidad))\
           .filter(Perdida.siembra_id == siembra.siembra_id)
    
    if exclude_loss_id:
        query = query.filter(Perdida.perdida_id != exclude_loss_id)
    
    total_perdidas = int(query.scalar() or 0)
    disponible = max(0, total_plantas - total_tallos - total_perdidas)
    
    if not full_stats:
        return disponible
    
    # Estadísticas adicionales para vista detallada
    perdidas_por_causa = db.session.query(
        CausaPerdida.nombre,
        func.sum(Perdida.cantidad).label('total')
    ).join(Perdida)\
     .filter(Perdida.siembra_id == siembra.siembra_id)\
     .group_by(CausaPerdida.nombre).all()
    
    return {
        'total_plantas': total_plantas,
        'total_tallos': total_tallos,
        'total_perdidas': total_perdidas,
        'disponible': disponible,
        'perdidas_por_causa': perdidas_por_causa
    }

def get_loss_summary():
    """Obtiene resumen global de pérdidas por causa"""
    return db.session.query(
        CausaPerdida.nombre,
        func.sum(Perdida.cantidad).label('total')
    ).join(Perdida)\
     .group_by(CausaPerdida.nombre)\
     .order_by(func.sum(Perdida.cantidad).desc()).all()

def get_variety_loss_summary():
    """Obtiene resumen de pérdidas por variedad y causa"""
    results = db.session.query(
        Variedad.variedad,
        CausaPerdida.nombre,
        func.sum(Perdida.cantidad).label('total')
    ).join(Perdida.siembra)\
     .join(Siembra.variedad)\
     .join(Perdida.causa)\
     .group_by(Variedad.variedad, CausaPerdida.nombre)\
     .order_by(Variedad.variedad, func.sum(Perdida.cantidad).desc()).all()
    
    # Agrupar por variedad
    grouped = {}
    for variedad, causa, total in results:
        if variedad not in grouped:
            grouped[variedad] = []
        grouped[variedad].append((causa, total))
    
    return grouped