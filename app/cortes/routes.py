from flask import render_template, flash, redirect, url_for, request
from flask_login import login_required, current_user
from sqlalchemy import func
from app import db
from app.cortes import bp
from app.cortes.forms import CorteForm
from app.models import Corte, Siembra
from app.utils.data_utils import calc_plantas_totales

def _get_corte_data(siembra_id, exclude_corte_id=None):
    """Obtiene datos calculados para los cortes de una siembra"""
    query = db.session.query(func.sum(Corte.cantidad_tallos)).filter(
        Corte.siembra_id == siembra_id
    )
    
    if exclude_corte_id:
        query = query.filter(Corte.corte_id != exclude_corte_id)
    
    total_tallos = query.scalar() or 0
    return total_tallos

def _validate_corte(form, siembra, total_tallos_otros, total_plantas, corte_id=None):
    """Realiza validaciones comunes para crear/editar cortes"""
    # Verificar número de corte único
    query = Corte.query.filter_by(
        siembra_id=siembra.siembra_id, 
        num_corte=form.num_corte.data
    )
    
    if corte_id:
        query = query.filter(Corte.corte_id != corte_id)
    
    if query.first():
        flash(f'Ya existe un corte con el número {form.num_corte.data} para esta siembra', 'danger')
        return False
    
    # Validar fecha para cortes posteriores al primero
    if form.num_corte.data > 1 and siembra.fecha_inicio_corte and form.fecha_corte.data < siembra.fecha_inicio_corte:
        flash(f'Error: La fecha del corte no puede ser anterior a la fecha de inicio de corte ({siembra.fecha_inicio_corte.strftime("%d-%m-%Y")})', 'danger')
        return False
    
    # Validar total de tallos
    nuevo_total = total_tallos_otros + form.cantidad_tallos.data
    if nuevo_total > total_plantas:
        flash(f'Error: El total de tallos cortados ({nuevo_total}) no puede superar el total de plantas sembradas ({total_plantas})', 'danger')
        return False
    
    return True

@bp.route('/')
@login_required
def index():
    """Listado de cortes paginados"""
    page = request.args.get('page', 1, type=int)
    cortes = Corte.query.order_by(Corte.fecha_corte.desc()).paginate(page=page, per_page=10)
    return render_template('cortes/index.html', title='Cortes', cortes=cortes)

@bp.route('/crear/<int:siembra_id>', methods=['GET', 'POST'])
@login_required
def crear(siembra_id):
    """Crear un nuevo corte para una siembra"""
    siembra = Siembra.query.get_or_404(siembra_id)
    
    if siembra.estado != 'Activa':
        flash('No se pueden registrar cortes para una siembra finalizada', 'warning')
        return redirect(url_for('siembras.detalles', id=siembra_id))
    
    # Configurar formulario
    ultimo_corte = Corte.query.filter_by(siembra_id=siembra_id).order_by(Corte.num_corte.desc()).first()
    proximo_num = 1 if not ultimo_corte else ultimo_corte.num_corte + 1
    
    form = CorteForm()
    form.siembra_id.data = siembra_id
    form.num_corte.data = proximo_num
    
    # Calcular datos
    total_tallos = _get_corte_data(siembra_id)
    total_plantas = calc_plantas_totales(siembra.area.area, siembra.densidad.valor) if siembra.area and siembra.densidad else 0
    tallos_disponibles = total_plantas - total_tallos
    
    if form.validate_on_submit():
        if not _validate_corte(form, siembra, total_tallos, total_plantas):
            return render_template('cortes/crear.html', 
                                title='Registrar Corte', 
                                form=form, 
                                siembra=siembra,
                                total_tallos_actuales=total_tallos,
                                total_plantas_sembradas=total_plantas,
                                tallos_disponibles=tallos_disponibles)
        
        # Crear corte
        corte = Corte(
            siembra_id=siembra_id,
            num_corte=form.num_corte.data,
            fecha_corte=form.fecha_corte.data,
            cantidad_tallos=form.cantidad_tallos.data,
            usuario_id=current_user.usuario_id
        )
        
        # Actualizar fecha inicio si es primer corte
        if form.num_corte.data == 1:
            siembra.fecha_inicio_corte = form.fecha_corte.data
        
        db.session.add(corte)
        db.session.commit()
        
        flash('Corte registrado exitosamente!', 'success')
        return redirect(url_for('siembras.detalles', id=siembra_id))
    
    return render_template('cortes/crear.html', 
                         title='Registrar Corte', 
                         form=form, 
                         siembra=siembra,
                         total_tallos_actuales=total_tallos,
                         total_plantas_sembradas=total_plantas,
                         tallos_disponibles=tallos_disponibles)

@bp.route('/editar/<int:corte_id>', methods=['GET', 'POST'])
@login_required
def editar(corte_id):
    """Editar un corte existente"""
    corte = Corte.query.get_or_404(corte_id)
    siembra = Siembra.query.get_or_404(corte.siembra_id)
    
    if siembra.estado != 'Activa':
        flash('No se pueden editar cortes de una siembra finalizada', 'warning')
        return redirect(url_for('cortes.index'))
    
    form = CorteForm()
    
    # Calcular datos
    total_tallos_otros = _get_corte_data(siembra.siembra_id, corte_id)
    total_plantas = calc_plantas_totales(siembra.area.area, siembra.densidad.valor) if siembra.area and siembra.densidad else 0
    tallos_disponibles = total_plantas - total_tallos_otros
    
    if form.validate_on_submit():
        if not _validate_corte(form, siembra, total_tallos_otros, total_plantas, corte_id):
            return render_template('cortes/editar.html', 
                                title='Editar Corte', 
                                form=form, 
                                corte=corte, 
                                siembra=siembra,
                                total_tallos_otros_cortes=total_tallos_otros,
                                total_plantas_sembradas=total_plantas,
                                tallos_disponibles=tallos_disponibles)
        
        # Actualizar corte
        corte.num_corte = form.num_corte.data
        corte.fecha_corte = form.fecha_corte.data
        corte.cantidad_tallos = form.cantidad_tallos.data
        
        # Actualizar fecha inicio si es primer corte
        if form.num_corte.data == 1:
            siembra.fecha_inicio_corte = form.fecha_corte.data
        
        db.session.commit()
        flash('Corte actualizado exitosamente!', 'success')
        return redirect(url_for('siembras.detalles', id=siembra.siembra_id))
    
    # Prellenar formulario
    if request.method == 'GET':
        form.siembra_id.data = corte.siembra_id
        form.num_corte.data = corte.num_corte
        form.fecha_corte.data = corte.fecha_corte
        form.cantidad_tallos.data = corte.cantidad_tallos
    
    return render_template('cortes/editar.html', 
                         title='Editar Corte', 
                         form=form, 
                         corte=corte, 
                         siembra=siembra,
                         total_tallos_otros_cortes=total_tallos_otros,
                         total_plantas_sembradas=total_plantas,
                         tallos_disponibles=tallos_disponibles)

@bp.route('/eliminar/<int:corte_id>')
@login_required
def eliminar(corte_id):
    """Eliminar un corte"""
    corte = Corte.query.get_or_404(corte_id)
    siembra_id = corte.siembra_id
    
    if corte.siembra.estado != 'Activa':
        flash('No se pueden eliminar cortes de una siembra finalizada', 'warning')
        return redirect(url_for('cortes.index'))
    
    db.session.delete(corte)
    db.session.commit()
    flash('Corte eliminado exitosamente!', 'success')
    return redirect(url_for('siembras.detalles', id=siembra_id))