# Rutas para el módulo de pérdidas
from flask import render_template, flash, redirect, url_for, request
from flask_login import login_required, current_user
from app import db
from app.perdidas import bp
from app.perdidas.forms import PerdidaForm
from app.models import Perdida, Siembra, Causa
from datetime import datetime

@bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    perdidas_list = Perdida.query.order_by(Perdida.fecha_perdida.desc()).paginate(
        page=page, per_page=10)
    return render_template('perdidas/index.html', title='Pérdidas', perdidas=perdidas_list)

@bp.route('/crear/<int:siembra_id>', methods=['GET', 'POST'])
@login_required
def crear(siembra_id):
    siembra = Siembra.query.get_or_404(siembra_id)
    
    # Verificar que la siembra esté activa
    if siembra.estado != 'Activa':
        flash('No se pueden registrar pérdidas para una siembra finalizada', 'warning')
        return redirect(url_for('siembras.detalles', id=siembra_id))
    
    form = PerdidaForm()
    form.siembra_id.data = siembra_id
    
    if form.validate_on_submit():
        perdida = Perdida(
            siembra_id=siembra_id,
            causa_id=form.causa_id.data,
            fecha_perdida=form.fecha_perdida.data,
            cantidad=form.cantidad.data,
            observaciones=form.observaciones.data,
            usuario_id=current_user.usuario_id
        )
        
        db.session.add(perdida)
        db.session.commit()
        flash('Pérdida registrada exitosamente!', 'success')
        return redirect(url_for('siembras.detalles', id=siembra_id))
    
    return render_template('perdidas/crear.html', title='Registrar Pérdida', form=form, siembra=siembra)

@bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar(id):
    perdida = Perdida.query.get_or_404(id)
    siembra = Siembra.query.get_or_404(perdida.siembra_id)
    
    # Verificar que la siembra esté activa
    if siembra.estado != 'Activa':
        flash('No se pueden editar pérdidas de una siembra finalizada', 'warning')
        return redirect(url_for('perdidas.index'))
    
    form = PerdidaForm()
    
    if form.validate_on_submit():
        perdida.causa_id = form.causa_id.data
        perdida.fecha_perdida = form.fecha_perdida.data
        perdida.cantidad = form.cantidad.data
        perdida.observaciones = form.observaciones.data
        
        db.session.commit()
        flash('Pérdida actualizada exitosamente!', 'success')
        return redirect(url_for('siembras.detalles', id=perdida.siembra_id))
    
    # Prellenar el formulario con los datos existentes
    if request.method == 'GET':
        form.siembra_id.data = perdida.siembra_id
        form.causa_id.data = perdida.causa_id
        form.fecha_perdida.data = perdida.fecha_perdida
        form.cantidad.data = perdida.cantidad
        form.observaciones.data = perdida.observaciones
    
    return render_template('perdidas/editar.html', title='Editar Pérdida', form=form, perdida=perdida, siembra=siembra)

@bp.route('/eliminar/<int:id>')
@login_required
def eliminar(id):
    perdida = Perdida.query.get_or_404(id)
    siembra_id = perdida.siembra_id
    
    # Verificar que la siembra esté activa
    if perdida.siembra.estado != 'Activa':
        flash('No se pueden eliminar pérdidas de una siembra finalizada', 'warning')
        return redirect(url_for('perdidas.index'))
    
    db.session.delete(perdida)
    db.session.commit()
    flash('Pérdida eliminada exitosamente!', 'success')
    return redirect(url_for('siembras.detalles', id=siembra_id))