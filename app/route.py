from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import (
    Bloque, Cama, Lado, BloqueCamaLado, Flor, Color, FlorColor, Variedad,
    Area, Densidad, Siembra, Corte, Causa, Perdida
)
from sqlalchemy import func
from datetime import datetime, timedelta

# Crear blueprint para las rutas principales
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Página de inicio."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Panel de control principal."""
    # Estadísticas para el dashboard
    stats = {
        'siembras_activas': Siembra.query.filter_by(estado='Activa').count(),
        'total_siembras': Siembra.query.count(),
        'total_cortes': Corte.query.count(),
        'total_variedades': Variedad.query.count()
    }
    
    # Últimas 5 siembras
    ultimas_siembras = Siembra.query.order_by(Siembra.fecha_registro.desc()).limit(5).all()
    
    # Últimos 5 cortes
    ultimos_cortes = Corte.query.order_by(Corte.fecha_registro.desc()).limit(5).all()
    
    # Producción total por variedad (top 5)
    top_variedades = db.session.query(
        Variedad.variedad, 
        func.sum(Corte.cantidad_tallos).label('total')
    ).join(Siembra, Siembra.variedad_id == Variedad.variedad_id
    ).join(Corte, Corte.siembra_id == Siembra.siembra_id
    ).group_by(Variedad.variedad
    ).order_by(func.sum(Corte.cantidad_tallos).desc()
    ).limit(5).all()
    
    # Calcular producción de los últimos 7 días
    fecha_inicio = datetime.now().date() - timedelta(days=7)
    produccion_reciente = db.session.query(
        func.date(Corte.fecha_corte).label('fecha'),
        func.sum(Corte.cantidad_tallos).label('total')
    ).filter(Corte.fecha_corte >= fecha_inicio
    ).group_by(func.date(Corte.fecha_corte)
    ).order_by(func.date(Corte.fecha_corte)).all()
    
    # Formatear los datos para las gráficas
    labels_variedades = [v[0] for v in top_variedades]
    datos_variedades = [v[1] for v in top_variedades]
    
    labels_dias = [d[0].strftime('%d/%m') for d in produccion_reciente]
    datos_dias = [d[1] for d in produccion_reciente]
    
    return render_template('dashboard.html', 
                           stats=stats,
                           ultimas_siembras=ultimas_siembras,
                           ultimos_cortes=ultimos_cortes,
                           labels_variedades=labels_variedades,
                           datos_variedades=datos_variedades,
                           labels_dias=labels_dias,
                           datos_dias=datos_dias)

@main_bp.route('/configuracion')
@login_required
def configuracion():
    """Página de configuración del sistema."""
    # Verificar si el usuario es administrador
    if not current_user.is_admin:
        flash('No tienes permisos para acceder a esta página.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    return render_template('configuracion.html')

@main_bp.route('/ubicaciones', methods=['GET', 'POST'])
@login_required
def ubicaciones():
    """Gestión de ubicaciones (bloques, camas, lados)."""
    # Verificar si el usuario es administrador
    if not current_user.is_admin:
        flash('No tienes permisos para acceder a esta página.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Obtener datos para mostrar en la página
    bloques = Bloque.query.all()
    camas = Cama.query.all()
    lados = Lado.query.all()
    
    # Obtener las combinaciones existentes de bloque-cama-lado
    combinaciones = BloqueCamaLado.query.all()
    
    return render_template('ubicaciones.html', 
                           bloques=bloques,
                           camas=camas,
                           lados=lados,
                           combinaciones=combinaciones)

@main_bp.route('/api/crear_ubicacion', methods=['POST'])
@login_required
def crear_ubicacion():
    """API para crear una nueva combinación de bloque-cama-lado."""
    # Verificar si el usuario es administrador
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'No tienes permisos suficientes'}), 403
    
    try:
        data = request.json
        bloque_id = data.get('bloque_id')
        cama_id = data.get('cama_id')
        lado_id = data.get('lado_id')
        
        # Verificar que no exista la combinación
        existente = BloqueCamaLado.query.filter_by(
            bloque_id=bloque_id, 
            cama_id=cama_id, 
            lado_id=lado_id
        ).first()
        
        if existente:
            return jsonify({'success': False, 'error': 'Esta ubicación ya existe'}), 400
        
        # Crear nueva combinación
        nueva_ubicacion = BloqueCamaLado(
            bloque_id=bloque_id,
            cama_id=cama_id,
            lado_id=lado_id
        )
        
        db.session.add(nueva_ubicacion)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Ubicación creada correctamente',
            'id': nueva_ubicacion.bloque_cama_id,
            'ubicacion': str(nueva_ubicacion)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@main_bp.route('/api/eliminar_ubicacion/<int:id>', methods=['DELETE'])
@login_required
def eliminar_ubicacion(id):
    """API para eliminar una combinación de bloque-cama-lado."""
    # Verificar si el usuario es administrador
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'No tienes permisos suficientes'}), 403
    
    try:
        # Verificar si la ubicación tiene siembras asociadas
        siembras = Siembra.query.filter_by(bloque_cama_id=id).first()
        if siembras:
            return jsonify({
                'success': False, 
                'error': 'No se puede eliminar la ubicación porque tiene siembras asociadas'
            }), 400
        
        # Eliminar la ubicación
        ubicacion = BloqueCamaLado.query.get_or_404(id)
        ubicacion_str = str(ubicacion)  # Guardar para el mensaje
        
        db.session.delete(ubicacion)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Ubicación {ubicacion_str} eliminada correctamente'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@main_bp.route('/variedades', methods=['GET'])
@login_required
def variedades():
    """Gestión de variedades."""
    # Verificar si el usuario es administrador
    if not current_user.is_admin:
        flash('No tienes permisos para acceder a esta página.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Obtener todas las variedades con sus relaciones
    variedades = Variedad.query.join(
        FlorColor, Variedad.flor_color_id == FlorColor.flor_color_id
    ).join(
        Flor, FlorColor.flor_id == Flor.flor_id
    ).join(
        Color, FlorColor.color_id == Color.color_id
    ).add_columns(
        Variedad.variedad_id,
        Variedad.variedad,
        Flor.flor,
        Color.color
    ).all()
    
    # Obtener flores y colores para el formulario de nueva variedad
    flores = Flor.query.all()
    colores = Color.query.all()
    
    # Obtener todas las combinaciones flor-color existentes
    flor_colores = FlorColor.query.all()
    
    return render_template('variedades.html',
                           variedades=variedades,
                           flores=flores,
                           colores=colores,
                           flor_colores=flor_colores)

@main_bp.route('/api/flor_colores/<int:flor_id>', methods=['GET'])
@login_required
def get_colores_por_flor(flor_id):
    """API para obtener los colores disponibles para una flor específica."""
    try:
        # Obtener las combinaciones flor-color para la flor seleccionada
        flor_colores = FlorColor.query.filter_by(flor_id=flor_id).join(
            Color, FlorColor.color_id == Color.color_id
        ).add_columns(
            FlorColor.flor_color_id,
            Color.color
        ).all()
        
        return jsonify({
            'success': True,
            'flor_colores': [
                {'id': fc.flor_color_id, 'color': fc.color} 
                for fc in flor_colores
            ]
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500