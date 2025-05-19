from flask import render_template, flash, redirect, url_for, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.perdidas import bp
from app.perdidas.forms import CausaPerdidaForm, PerdidaForm
from app.models import Siembra, Perdida, CausaPerdida, Flor, FlorColor, Variedad, Area, Densidad, Corte
from app.utils.data_utils import calc_plantas_totales
from datetime import datetime
from sqlalchemy import func

@bp.route('/')
@login_required
def index():
    """Vista principal del módulo de pérdidas"""
    # Obtener parámetros de filtrado
    siembra_id = request.args.get('siembra_id', type=int)
    causa_id = request.args.get('causa_id', type=int)
    fecha_desde = request.args.get('fecha_desde', type=str)
    fecha_hasta = request.args.get('fecha_hasta', type=str)
    
    # Construir consulta base
    query = Perdida.query
    
    # Aplicar filtros
    if siembra_id:
        query = query.filter(Perdida.siembra_id == siembra_id)
    
    if causa_id:
        query = query.filter(Perdida.causa_id == causa_id)
    
    if fecha_desde:
        try:
            fecha_desde_obj = datetime.strptime(fecha_desde, '%Y-%m-%d').date()
            query = query.filter(Perdida.fecha_perdida >= fecha_desde_obj)
        except ValueError:
            flash('Formato de fecha inválido', 'danger')
    
    if fecha_hasta:
        try:
            fecha_hasta_obj = datetime.strptime(fecha_hasta, '%Y-%m-%d').date()
            query = query.filter(Perdida.fecha_perdida <= fecha_hasta_obj)
        except ValueError:
            flash('Formato de fecha inválido', 'danger')
    
    # Ejecutar consulta paginada
    page = request.args.get('page', 1, type=int)
    perdidas = query.order_by(Perdida.fecha_perdida.desc()).paginate(page=page, per_page=10)
    
    # Obtener lista de causas para filtrado
    causas = CausaPerdida.query.order_by(CausaPerdida.nombre).all()
    
    return render_template('perdidas/index.html',
                           title='Registro de Pérdidas',
                           perdidas=perdidas,
                           causas=causas,
                           siembra_id=siembra_id,
                           causa_id=causa_id,
                           fecha_desde=fecha_desde,
                           fecha_hasta=fecha_hasta)

@bp.route('/causas')
@login_required
def causas():
    """Vista para gestionar causas de pérdida"""
    causas = CausaPerdida.query.order_by(CausaPerdida.nombre).all()
    return render_template('perdidas/causas.html',
                           title='Causas de Pérdida',
                           causas=causas)

@bp.route('/causas/crear', methods=['GET', 'POST'])
@login_required
def crear_causa():
    """Vista para crear una nueva causa de pérdida"""
    # Verificar permisos
    if not current_user.has_permission('importar_datos'):
        flash('No tienes permiso para realizar esta acción', 'danger')
        return redirect(url_for('perdidas.causas'))
    
    form = CausaPerdidaForm()
    
    if form.validate_on_submit():
        # Crear nueva causa
        causa = CausaPerdida(
            nombre=form.nombre.data,
            descripcion=form.descripcion.data,
            es_predefinida=(form.es_predefinida.data == '1')
        )
        
        db.session.add(causa)
        try:
            db.session.commit()
            flash(f'Causa de pérdida "{form.nombre.data}" creada exitosamente', 'success')
            return redirect(url_for('perdidas.causas'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear causa de pérdida: {str(e)}', 'danger')
    
    return render_template('perdidas/crear_causa.html',
                           title='Crear Causa de Pérdida',
                           form=form)

@bp.route('/causas/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_causa(id):
    """Vista para editar una causa de pérdida existente"""
    # Verificar permisos
    if not current_user.has_permission('importar_datos'):
        flash('No tienes permiso para realizar esta acción', 'danger')
        return redirect(url_for('perdidas.causas'))
    
    causa = CausaPerdida.query.get_or_404(id)
    form = CausaPerdidaForm()
    
    if form.validate_on_submit():
        causa.nombre = form.nombre.data
        causa.descripcion = form.descripcion.data
        causa.es_predefinida = (form.es_predefinida.data == '1')
        
        try:
            db.session.commit()
            flash(f'Causa de pérdida "{causa.nombre}" actualizada exitosamente', 'success')
            return redirect(url_for('perdidas.causas'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar causa de pérdida: {str(e)}', 'danger')
    
    # Prellenar el formulario con los datos existentes
    if request.method == 'GET':
        form.nombre.data = causa.nombre
        form.descripcion.data = causa.descripcion
        form.es_predefinida.data = '1' if causa.es_predefinida else '0'
    
    return render_template('perdidas/editar_causa.html',
                           title='Editar Causa de Pérdida',
                           form=form,
                           causa=causa)

@bp.route('/causas/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_causa(id):
    """Vista para eliminar una causa de pérdida"""
    # Verificar permisos
    if not current_user.has_permission('importar_datos'):
        flash('No tienes permiso para realizar esta acción', 'danger')
        return redirect(url_for('perdidas.causas'))
    
    causa = CausaPerdida.query.get_or_404(id)
    
    # Verificar si hay pérdidas asociadas a esta causa
    perdidas_asociadas = Perdida.query.filter_by(causa_id=id).count()
    if perdidas_asociadas > 0:
        flash(f'No se puede eliminar la causa "{causa.nombre}" porque tiene {perdidas_asociadas} registros asociados', 'danger')
        return redirect(url_for('perdidas.causas'))
    
    try:
        db.session.delete(causa)
        db.session.commit()
        flash(f'Causa de pérdida "{causa.nombre}" eliminada exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar causa de pérdida: {str(e)}', 'danger')
    
    return redirect(url_for('perdidas.causas'))

@bp.route('/registrar/<int:siembra_id>', methods=['GET', 'POST'])
@login_required
def registrar(siembra_id):
    """Vista para registrar una nueva pérdida"""
    # Obtener la siembra
    siembra = Siembra.query.get_or_404(siembra_id)
    
    # Verificar que la siembra esté activa
    if siembra.estado != 'Activa':
        flash('No se pueden registrar pérdidas para una siembra finalizada', 'warning')
        return redirect(url_for('siembras.detalles', id=siembra_id))
    
    form = PerdidaForm()
    form.siembra_id.data = siembra_id
    
    # Cargar opciones de causas de pérdida
    causas = CausaPerdida.query.order_by(CausaPerdida.nombre).all()
    form.causa_id.choices = [(c.causa_id, c.nombre) for c in causas]
    
    # Calcular el máximo disponible para validación
    if siembra.area and siembra.densidad and siembra.densidad.valor:
        # Obtener total de plantas sembradas
        total_plantas = calc_plantas_totales(siembra.area.area, siembra.densidad.valor)
        
        # Sumar cortes
        total_tallos = db.session.query(func.sum(Corte.cantidad_tallos)).\
            filter(Corte.siembra_id == siembra_id).scalar() or 0
        
        # Sumar pérdidas existentes
        total_perdidas = db.session.query(func.sum(Perdida.cantidad)).\
            filter(Perdida.siembra_id == siembra_id).scalar() or 0
        
        # Calcular disponible
        disponible = total_plantas - total_tallos - total_perdidas
        if disponible < 0:
            disponible = 0
        
        # Pasar el valor al formulario para validación
        form.max_disponible = disponible
    else:
        disponible = None
        form.max_disponible = None
    
    if form.validate_on_submit():
        # Crear nueva pérdida
        perdida = Perdida(
            siembra_id=siembra_id,
            causa_id=form.causa_id.data,
            cantidad=form.cantidad.data,
            fecha_perdida=form.fecha_perdida.data,
            observaciones=form.observaciones.data,
            usuario_id=current_user.usuario_id
        )
        
        db.session.add(perdida)
        try:
            db.session.commit()
            flash('Pérdida registrada exitosamente', 'success')
            return redirect(url_for('siembras.detalles', id=siembra_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al registrar pérdida: {str(e)}', 'danger')
    
    return render_template('perdidas/registrar.html',
                           title='Registrar Pérdida',
                           form=form,
                           siembra=siembra,
                           disponible=disponible)

@bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar(id):
    """Vista para editar una pérdida"""
    perdida = Perdida.query.get_or_404(id)
    siembra = perdida.siembra
    
    # Verificar que la siembra esté activa
    if siembra.estado != 'Activa':
        flash('No se pueden editar pérdidas de una siembra finalizada', 'warning')
        return redirect(url_for('siembras.detalles', id=siembra.siembra_id))
    
    form = PerdidaForm()
    
    # Cargar opciones de causas de pérdida
    causas = CausaPerdida.query.order_by(CausaPerdida.nombre).all()
    form.causa_id.choices = [(c.causa_id, c.nombre) for c in causas]
    
    # Calcular el máximo disponible para validación
    if siembra.area and siembra.densidad:
        # Obtener total de plantas sembradas
        total_plantas = calc_plantas_totales(siembra.area.area, siembra.densidad.valor)
        
        # Sumar cortes
        total_tallos = db.session.query(func.sum(Corte.cantidad_tallos)).\
            filter(Corte.siembra_id == siembra.siembra_id).scalar() or 0
        
        # Sumar pérdidas existentes (excluyendo la actual)
        total_perdidas = db.session.query(func.sum(Perdida.cantidad)).\
            filter(Perdida.siembra_id == siembra.siembra_id).\
            filter(Perdida.perdida_id != id).scalar() or 0
        
        # Calcular disponible
        disponible = total_plantas - total_tallos - total_perdidas
        if disponible < 0:
            disponible = 0
        
        # Pasar el valor al formulario para validación (sumando la cantidad actual)
        form.max_disponible = disponible + perdida.cantidad
    else:
        disponible = None
        form.max_disponible = None
    
    if form.validate_on_submit():
        perdida.causa_id = form.causa_id.data
        perdida.cantidad = form.cantidad.data
        perdida.fecha_perdida = form.fecha_perdida.data
        perdida.observaciones = form.observaciones.data
        
        try:
            db.session.commit()
            flash('Pérdida actualizada exitosamente', 'success')
            return redirect(url_for('siembras.detalles', id=siembra.siembra_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar pérdida: {str(e)}', 'danger')
    
    # Prellenar el formulario con los datos existentes
    if request.method == 'GET':
        form.siembra_id.data = siembra.siembra_id
        form.causa_id.data = perdida.causa_id
        form.cantidad.data = perdida.cantidad
        form.fecha_perdida.data = perdida.fecha_perdida
        form.observaciones.data = perdida.observaciones
    
    return render_template('perdidas/editar.html',
                           title='Editar Pérdida',
                           form=form,
                           perdida=perdida,
                           siembra=siembra,
                           disponible=disponible)

@bp.route('/eliminar/<int:id>')
@login_required
def eliminar(id):
    """Vista para eliminar una pérdida"""
    perdida = Perdida.query.get_or_404(id)
    siembra_id = perdida.siembra_id
    
    # Verificar que la siembra esté activa
    if perdida.siembra.estado != 'Activa':
        flash('No se pueden eliminar pérdidas de una siembra finalizada', 'warning')
        return redirect(url_for('siembras.detalles', id=siembra_id))
    
    try:
        db.session.delete(perdida)
        db.session.commit()
        flash('Pérdida eliminada exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar pérdida: {str(e)}', 'danger')
    
    return redirect(url_for('siembras.detalles', id=siembra_id))

@bp.route('/por_siembra/<int:siembra_id>')
@login_required
def por_siembra(siembra_id):
    """Vista para listar pérdidas de una siembra específica"""
    siembra = Siembra.query.get_or_404(siembra_id)
    perdidas = Perdida.query.filter_by(siembra_id=siembra_id).order_by(Perdida.fecha_perdida.desc()).all()
    
    # Calcular estadísticas
    total_plantas = 0
    if siembra.area and siembra.densidad:
        total_plantas = calc_plantas_totales(siembra.area.area, siembra.densidad.valor)
    
    total_tallos = db.session.query(func.sum(Corte.cantidad_tallos)).\
        filter(Corte.siembra_id == siembra_id).scalar() or 0
    
    total_perdidas = db.session.query(func.sum(Perdida.cantidad)).\
        filter(Perdida.siembra_id == siembra_id).scalar() or 0
    
    disponible = max(0, total_plantas - total_tallos - total_perdidas)
    
    # Agrupar por causa para estadísticas
    perdidas_por_causa = db.session.query(
        CausaPerdida.nombre,
        func.sum(Perdida.cantidad).label('total')
    ).join(Perdida).filter(
        Perdida.siembra_id == siembra_id
    ).group_by(CausaPerdida.nombre).all()
    
    return render_template('perdidas/por_siembra.html',
                           title=f'Pérdidas - Siembra #{siembra_id}',
                           siembra=siembra,
                           perdidas=perdidas,
                           total_plantas=total_plantas,
                           total_tallos=total_tallos,
                           total_perdidas=total_perdidas,
                           disponible=disponible,
                           perdidas_por_causa=perdidas_por_causa)

@bp.route('/resumen')
@login_required
def resumen():
    """Vista para mostrar resumen de pérdidas por causa"""
    # Resumen global por causa
    resumen_global = db.session.query(
        CausaPerdida.nombre,
        func.sum(Perdida.cantidad).label('total')
    ).join(Perdida).group_by(CausaPerdida.nombre).order_by(func.sum(Perdida.cantidad).desc()).all()
    
    # Resumen por variedad
    resumen_variedad = db.session.query(
        Variedad.variedad,
        CausaPerdida.nombre,
        func.sum(Perdida.cantidad).label('total')
    ).join(Perdida.siembra).join(
        Siembra.variedad
    ).join(Perdida.causa).group_by(
        Variedad.variedad, CausaPerdida.nombre
    ).order_by(
        Variedad.variedad, func.sum(Perdida.cantidad).desc()
    ).all()
    
    # Agrupar por variedad para facilitar vista en plantilla
    perdidas_variedad = {}
    for variedad, causa, total in resumen_variedad:
        if variedad not in perdidas_variedad:
            perdidas_variedad[variedad] = []
        perdidas_variedad[variedad].append((causa, total))
    
    return render_template('perdidas/resumen.html',
                           title='Resumen de Pérdidas',
                           resumen_global=resumen_global,
                           perdidas_variedad=perdidas_variedad)