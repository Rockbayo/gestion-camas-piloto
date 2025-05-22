from flask import render_template, flash, redirect, url_for, request
from flask_login import login_required, current_user
from sqlalchemy import func
from app import db
from app.perdidas import bp
from app.perdidas.forms import CausaPerdidaForm, PerdidaForm
from app.models import Siembra, Perdida, CausaPerdida, Variedad, Corte
from app.utils.data_utils import calc_plantas_totales
from datetime import datetime
from .perdida_utils import (
    get_filtered_losses,
    calculate_available_plants,
    get_loss_summary,
    get_variety_loss_summary
)

@bp.route('/')
@login_required
def index():
    """Listado de pérdidas con filtros"""
    losses_query = get_filtered_losses(request.args)
    page = request.args.get('page', 1, type=int)
    losses = losses_query.order_by(Perdida.fecha_perdida.desc()).paginate(page=page, per_page=10)
    
    return render_template('perdidas/index.html',
                         title='Registro de Pérdidas',
                         perdidas=losses,
                         causas=CausaPerdida.query.order_by(CausaPerdida.nombre).all(),
                         **request.args)

# CRUD para Causas de Pérdida
@bp.route('/causas')
@login_required
def causas():
    """Gestión de causas de pérdida"""
    return render_template('perdidas/causas.html',
                         title='Causas de Pérdida',
                         causas=CausaPerdida.query.order_by(CausaPerdida.nombre).all())

@bp.route('/causas/crear', methods=['GET', 'POST'])
@login_required
def crear_causa():
    """Crear nueva causa de pérdida"""
    if not current_user.has_permission('importar_datos'):
        flash('No tienes permiso para realizar esta acción', 'danger')
        return redirect(url_for('perdidas.causas'))
    
    form = CausaPerdidaForm()
    
    if form.validate_on_submit():
        causa = CausaPerdida(
            nombre=form.nombre.data,
            descripcion=form.descripcion.data,
            es_predefinida=form.es_predefinida.data
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
    """Editar causa de pérdida existente"""
    if not current_user.has_permission('importar_datos'):
        flash('No tienes permiso para realizar esta acción', 'danger')
        return redirect(url_for('perdidas.causas'))
    
    causa = CausaPerdida.query.get_or_404(id)
    form = CausaPerdidaForm(obj=causa)
    
    if form.validate_on_submit():
        form.populate_obj(causa)
        try:
            db.session.commit()
            flash(f'Causa de pérdida "{causa.nombre}" actualizada exitosamente', 'success')
            return redirect(url_for('perdidas.causas'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar causa de pérdida: {str(e)}', 'danger')
    
    return render_template('perdidas/editar_causa.html',
                         title='Editar Causa de Pérdida',
                         form=form,
                         causa=causa)

@bp.route('/causas/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_causa(id):
    """Eliminar causa de pérdida"""
    if not current_user.has_permission('importar_datos'):
        flash('No tienes permiso para realizar esta acción', 'danger')
        return redirect(url_for('perdidas.causas'))
    
    causa = CausaPerdida.query.get_or_404(id)
    
    if Perdida.query.filter_by(causa_id=id).count() > 0:
        flash(f'No se puede eliminar la causa "{causa.nombre}" porque tiene registros asociados', 'danger')
        return redirect(url_for('perdidas.causas'))
    
    try:
        db.session.delete(causa)
        db.session.commit()
        flash(f'Causa de pérdida "{causa.nombre}" eliminada exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar causa de pérdida: {str(e)}', 'danger')
    
    return redirect(url_for('perdidas.causas'))

# CRUD para Pérdidas
@bp.route('/registrar/<int:siembra_id>', methods=['GET', 'POST'])
@login_required
def registrar(siembra_id):
    """Registrar nueva pérdida"""
    siembra = Siembra.query.get_or_404(siembra_id)
    
    if siembra.estado != 'Activa':
        flash('No se pueden registrar pérdidas para una siembra finalizada', 'warning')
        return redirect(url_for('siembras.detalles', id=siembra_id))
    
    form = PerdidaForm()
    form.siembra_id.data = siembra_id
    form.causa_id.choices = [(c.causa_id, c.nombre) for c in CausaPerdida.query.order_by(CausaPerdida.nombre).all()]
    
    # Calcular plantas disponibles
    available = calculate_available_plants(siembra)
    form.max_disponible = available
    
    if form.validate_on_submit():
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
                         disponible=available)

@bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar(id):
    """Editar pérdida existente"""
    perdida = Perdida.query.get_or_404(id)
    siembra = perdida.siembra
    
    if siembra.estado != 'Activa':
        flash('No se pueden editar pérdidas de una siembra finalizada', 'warning')
        return redirect(url_for('siembras.detalles', id=siembra.siembra_id))
    
    form = PerdidaForm(obj=perdida)
    form.siembra_id.data = siembra.siembra_id
    form.causa_id.choices = [(c.causa_id, c.nombre) for c in CausaPerdida.query.order_by(CausaPerdida.nombre).all()]
    
    # Calcular plantas disponibles (incluyendo la cantidad actual)
    available = calculate_available_plants(siembra, exclude_loss_id=id)
    form.max_disponible = available + perdida.cantidad if available is not None else None
    
    if form.validate_on_submit():
        form.populate_obj(perdida)
        try:
            db.session.commit()
            flash('Pérdida actualizada exitosamente', 'success')
            return redirect(url_for('siembras.detalles', id=siembra.siembra_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar pérdida: {str(e)}', 'danger')
    
    return render_template('perdidas/editar.html',
                         title='Editar Pérdida',
                         form=form,
                         perdida=perdida,
                         siembra=siembra,
                         disponible=available)

@bp.route('/eliminar/<int:id>')
@login_required
def eliminar(id):
    """Eliminar pérdida"""
    perdida = Perdida.query.get_or_404(id)
    siembra_id = perdida.siembra_id
    
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

# Reportes y resúmenes
@bp.route('/por_siembra/<int:siembra_id>')
@login_required
def por_siembra(siembra_id):
    """Pérdidas por siembra específica"""
    siembra = Siembra.query.get_or_404(siembra_id)
    stats = calculate_available_plants(siembra, full_stats=True)
    
    return render_template('perdidas/por_siembra.html',
                         title=f'Pérdidas - Siembra #{siembra_id}',
                         siembra=siembra,
                         perdidas=Perdida.query.filter_by(siembra_id=siembra_id)
                                              .order_by(Perdida.fecha_perdida.desc()).all(),
                         **stats)

@bp.route('/resumen')
@login_required
def resumen():
    """Resumen general de pérdidas"""
    resumen_global_raw = get_loss_summary()
    perdidas_variedad_raw = get_variety_loss_summary()
    
    # Procesar datos para el template
    resumen_global_processed = []
    total_global = sum(item.total for item in resumen_global_raw) if resumen_global_raw else 0
    
    if resumen_global_raw and total_global > 0:
        for item in resumen_global_raw:
            percentage = round((item.total / total_global * 100), 1)
            resumen_global_processed.append({
                'cells': [
                    item.nombre,
                    item.total,
                    f"{percentage}%",
                    percentage
                ]
            })
    
    return render_template('perdidas/resumen.html',
                         title='Resumen de Pérdidas',
                         resumen_global=resumen_global_raw,
                         resumen_global_processed=resumen_global_processed,
                         total_global=total_global,
                         perdidas_variedad=perdidas_variedad_raw)