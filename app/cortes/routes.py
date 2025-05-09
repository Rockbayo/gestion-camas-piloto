# Rutas para la gestión de cortes
from flask import render_template, flash, redirect, url_for, request
from flask_login import login_required, current_user
from app import db
from app.cortes import bp
from app.cortes.forms import CorteForm
from app.models import Corte, Siembra
from datetime import datetime

@bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    cortes_list = Corte.query.order_by(Corte.fecha_corte.desc()).paginate(
        page=page, per_page=10)
    return render_template('cortes/index.html', title='Cortes', cortes=cortes_list)

@bp.route('/crear/<int:siembra_id>', methods=['GET', 'POST'])
@login_required
def crear(siembra_id):
    try:
        # Obtener la siembra
        siembra = Siembra.query.get_or_404(siembra_id)
        
        # Verificar que la siembra tenga fecha de inicio de corte
        if not siembra.fecha_inicio_corte:
            flash('Debe registrar una fecha de inicio de corte antes de registrar cortes', 'warning')
            return redirect(url_for('siembras.inicio_corte', id=siembra_id))
        
        # Verificar que la siembra esté activa
        if siembra.estado != 'Activa':
            flash('No se pueden registrar cortes para una siembra finalizada', 'warning')
            return redirect(url_for('siembras.detalles', id=siembra_id))
        
        # Obtener el último número de corte para esta siembra
        ultimo_corte = Corte.query.filter_by(siembra_id=siembra_id).order_by(Corte.num_corte.desc()).first()
        proximo_num_corte = 1 if not ultimo_corte else ultimo_corte.num_corte + 1
        
        form = CorteForm()
        form.siembra_id.data = siembra_id
        form.num_corte.data = proximo_num_corte
        
        if form.validate_on_submit():
            # Verificar que no exista un corte con el mismo número para esta siembra
            corte_existente = Corte.query.filter_by(
                siembra_id=siembra_id, 
                num_corte=form.num_corte.data
            ).first()
            
            if corte_existente:
                flash(f'Ya existe un corte con el número {form.num_corte.data} para esta siembra', 'danger')
                return redirect(url_for('cortes.crear', siembra_id=siembra_id))
            
            # Calcular el total actual de tallos cortados
            total_tallos_actuales = db.session.query(func.sum(Corte.cantidad_tallos)) \
                .filter(Corte.siembra_id == siembra_id) \
                .scalar() or 0
            
            # Calcular el total de plantas sembradas
            total_plantas_sembradas = 0
            if siembra.area and siembra.densidad:
                total_plantas_sembradas = int(siembra.area.area * siembra.densidad.valor)
            
            # Verificar que el nuevo total no exceda el número de plantas sembradas
            nuevo_total = total_tallos_actuales + form.cantidad_tallos.data
            if nuevo_total > total_plantas_sembradas:
                flash(f'Error: El total de tallos cortados ({nuevo_total}) no puede superar el total de plantas sembradas ({total_plantas_sembradas})', 'danger')
                return render_template('cortes/crear.html', title='Registrar Corte', form=form, siembra=siembra)
            
            # Crear el corte
            corte = Corte(
                siembra_id=siembra_id,
                num_corte=form.num_corte.data,
                fecha_corte=form.fecha_corte.data,
                cantidad_tallos=form.cantidad_tallos.data,
                usuario_id=current_user.usuario_id
            )
            
            db.session.add(corte)
            db.session.commit()
            flash('Corte registrado exitosamente!', 'success')
            return redirect(url_for('siembras.detalles', id=siembra_id))
        
        # Para el GET request, preparar información adicional
        total_tallos_actuales = db.session.query(func.sum(Corte.cantidad_tallos)) \
            .filter(Corte.siembra_id == siembra_id) \
            .scalar() or 0
        
        total_plantas_sembradas = 0
        if siembra.area and siembra.densidad:
            total_plantas_sembradas = int(siembra.area.area * siembra.densidad.valor)
        
        return render_template('cortes/crear.html', 
                              title='Registrar Corte', 
                              form=form, 
                              siembra=siembra,
                              total_tallos_actuales=total_tallos_actuales,
                              total_plantas_sembradas=total_plantas_sembradas,
                              tallos_disponibles=total_plantas_sembradas - total_tallos_actuales)
    except Exception as e:
        # Capturar cualquier error inesperado
        print(f"Error inesperado en crear corte: {str(e)}")
        flash(f"Ocurrió un error inesperado: {str(e)}", 'danger')
        return redirect(url_for('siembras.index'))

@bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar(id):
    try:
        corte = Corte.query.get_or_404(id)
        siembra = Siembra.query.get_or_404(corte.siembra_id)
        
        # Verificar que la siembra esté activa
        if siembra.estado != 'Activa':
            flash('No se pueden editar cortes de una siembra finalizada', 'warning')
            return redirect(url_for('cortes.index'))
        
        form = CorteForm()
        
        if form.validate_on_submit():
            # Verificar que no exista otro corte con el mismo número para esta siembra
            corte_existente = Corte.query.filter_by(
                siembra_id=corte.siembra_id, 
                num_corte=form.num_corte.data
            ).filter(Corte.corte_id != id).first()
            
            if corte_existente:
                flash(f'Ya existe un corte con el número {form.num_corte.data} para esta siembra', 'danger')
                return redirect(url_for('cortes.editar', id=id))
            
            # Calcular el total de tallos cortados (excluyendo el corte actual)
            total_tallos_otros_cortes = db.session.query(func.sum(Corte.cantidad_tallos)) \
                .filter(Corte.siembra_id == siembra.siembra_id) \
                .filter(Corte.corte_id != id) \
                .scalar() or 0
            
            # Calcular el total de plantas sembradas
            total_plantas_sembradas = 0
            if siembra.area and siembra.densidad:
                total_plantas_sembradas = int(siembra.area.area * siembra.densidad.valor)
            
            # Verificar que el nuevo total no exceda el número de plantas sembradas
            nuevo_total = total_tallos_otros_cortes + form.cantidad_tallos.data
            if nuevo_total > total_plantas_sembradas:
                flash(f'Error: El total de tallos cortados ({nuevo_total}) no puede superar el total de plantas sembradas ({total_plantas_sembradas})', 'danger')
                return render_template('cortes/editar.html', title='Editar Corte', form=form, corte=corte, siembra=siembra)
            
            # Actualizar el corte
            corte.num_corte = form.num_corte.data
            corte.fecha_corte = form.fecha_corte.data
            corte.cantidad_tallos = form.cantidad_tallos.data
            
            db.session.commit()
            flash('Corte actualizado exitosamente!', 'success')
            return redirect(url_for('siembras.detalles', id=corte.siembra_id))
        
        # Prellenar el formulario con los datos existentes
        if request.method == 'GET':
            form.siembra_id.data = corte.siembra_id
            form.num_corte.data = corte.num_corte
            form.fecha_corte.data = corte.fecha_corte
            form.cantidad_tallos.data = corte.cantidad_tallos
        
        # Preparar información adicional
        total_tallos_otros_cortes = db.session.query(func.sum(Corte.cantidad_tallos)) \
            .filter(Corte.siembra_id == siembra.siembra_id) \
            .filter(Corte.corte_id != id) \
            .scalar() or 0
        
        total_plantas_sembradas = 0
        if siembra.area and siembra.densidad:
            total_plantas_sembradas = int(siembra.area.area * siembra.densidad.valor)
        
        return render_template('cortes/editar.html', 
                              title='Editar Corte', 
                              form=form, 
                              corte=corte, 
                              siembra=siembra,
                              total_tallos_otros_cortes=total_tallos_otros_cortes,
                              total_plantas_sembradas=total_plantas_sembradas,
                              tallos_disponibles=total_plantas_sembradas - total_tallos_otros_cortes)
    except Exception as e:
        # Capturar cualquier error inesperado
        print(f"Error inesperado en editar corte: {str(e)}")
        flash(f"Ocurrió un error inesperado: {str(e)}", 'danger')
        return redirect(url_for('cortes.index'))

@bp.route('/eliminar/<int:id>')
@login_required
def eliminar(id):
    corte = Corte.query.get_or_404(id)
    siembra_id = corte.siembra_id
    
    # Verificar que la siembra esté activa
    if corte.siembra.estado != 'Activa':
        flash('No se pueden eliminar cortes de una siembra finalizada', 'warning')
        return redirect(url_for('cortes.index'))
    
    db.session.delete(corte)
    db.session.commit()
    flash('Corte eliminado exitosamente!', 'success')
    return redirect(url_for('siembras.detalles', id=siembra_id))