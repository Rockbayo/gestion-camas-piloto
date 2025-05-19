from flask import render_template, flash, redirect, url_for, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from . import bp
from .forms import SiembraForm, InicioCorteForm
from .services import SiembraService
from app.models import Siembra, Area, Densidad

@bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    siembras = SiembraService.obtener_siembras_paginadas(page=page)
    return render_template('siembras/index.html', title='Siembras', siembras=siembras)

@bp.route('/crear', methods=['GET', 'POST'])
@login_required
def crear():
    form = SiembraForm()
    
    if request.method == 'GET':
        if request.args.get('filter') == 'true':
            variedades = SiembraService.filtrar_variedades(
                request.args.get('flor_id', type=int),
                request.args.get('color_id', type=int)
            )
            return jsonify([{'id': v.variedad_id, 'text': v.variedad} for v in variedades])
        
        if request.args.get('calculate') == 'true':
            resultado = SiembraService.calcular_area(
                request.args.get('cantidad_plantas', type=int),
                request.args.get('densidad_id', type=int)
            )
            return jsonify(resultado) if resultado else jsonify({'error': 'No se pudo calcular el área'})
    
    if form.validate_on_submit():
        try:
            siembra = SiembraService.crear_siembra({
                'bloque_id': form.bloque_id.data,
                'cama_id': form.cama_id.data,
                'lado_id': form.lado_id.data,
                'variedad_id': form.variedad_id.data,
                'fecha_siembra': form.fecha_siembra.data,
                'cantidad_plantas': form.cantidad_plantas.data,
                'densidad_id': form.densidad_id.data,
                'area_id': form.area_id.data
            }, current_user.usuario_id)
            
            flash('La siembra ha sido registrada exitosamente!', 'success')
            return redirect(url_for('siembras.index'))
        except Exception as e:
            flash(f'Error al registrar siembra: {str(e)}', 'danger')
    
    return render_template('siembras/crear.html', title='Nueva Siembra', form=form)

@bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar(id):
    siembra = Siembra.query.get_or_404(id)
    
    if siembra.estado != 'Activa':
        flash('No se pueden editar siembras finalizadas', 'warning')
        return redirect(url_for('siembras.index'))
    
    form = SiembraForm()
    
    if form.validate_on_submit():
        try:
            SiembraService.actualizar_siembra(id, {
                'bloque_id': form.bloque_id.data,
                'cama_id': form.cama_id.data,
                'lado_id': form.lado_id.data,
                'variedad_id': form.variedad_id.data,
                'fecha_siembra': form.fecha_siembra.data,
                'densidad_id': form.densidad_id.data,
                'area_id': form.area_id.data
            })
            
            flash('La siembra ha sido actualizada exitosamente!', 'success')
            return redirect(url_for('siembras.detalles', id=id))
        except Exception as e:
            flash(f'Error al actualizar la siembra: {str(e)}', 'danger')
    
    if request.method == 'GET':
        form.bloque_id.data = siembra.bloque_cama.bloque_id
        form.cama_id.data = siembra.bloque_cama.cama_id
        form.lado_id.data = siembra.bloque_cama.lado_id
        form.variedad_id.data = siembra.variedad_id
        form.densidad_id.data = siembra.densidad_id
        form.fecha_siembra.data = siembra.fecha_siembra
        form.area_id.data = siembra.area_id
        
        if siembra.area and siembra.densidad and siembra.densidad.valor > 0:
            form.cantidad_plantas.data = siembra.area.area * siembra.densidad.valor
    
    return render_template('siembras/editar.html', title='Editar Siembra', form=form, siembra=siembra)

@bp.route('/inicio-corte/<int:id>', methods=['GET', 'POST'])
@login_required
def inicio_corte(id):
    siembra = Siembra.query.get_or_404(id)
    
    if siembra.estado != 'Activa':
        flash('No se puede registrar inicio de corte en una siembra finalizada', 'warning')
        return redirect(url_for('siembras.index'))
    
    if siembra.fecha_inicio_corte:
        flash('Esta siembra ya tiene una fecha de inicio de corte registrada', 'warning')
        return redirect(url_for('siembras.detalles', id=id))
    
    form = InicioCorteForm()
    
    if form.validate_on_submit():
        if form.fecha_inicio_corte.data < siembra.fecha_siembra:
            flash('La fecha de inicio de corte no puede ser anterior a la fecha de siembra', 'danger')
        else:
            try:
                SiembraService.registrar_inicio_corte(id, form.fecha_inicio_corte.data)
                flash('Fecha de inicio de corte registrada con éxito!', 'success')
                return redirect(url_for('siembras.detalles', id=id))
            except Exception as e:
                flash(f'Error al registrar inicio de corte: {str(e)}', 'danger')
    
    return render_template('siembras/inicio_corte.html', title='Registrar Inicio de Corte', form=form, siembra=siembra)

@bp.route('/finalizar/<int:id>')
@login_required
def finalizar(id):
    siembra = Siembra.query.get_or_404(id)
    
    if siembra.estado != 'Activa':
        flash('Esta siembra ya ha sido finalizada', 'warning')
        return redirect(url_for('siembras.index'))
    
    try:
        SiembraService.finalizar_siembra(id)
        flash('La siembra ha sido finalizada con éxito!', 'success')
    except Exception as e:
        flash(f'Error al finalizar siembra: {str(e)}', 'danger')
    
    return redirect(url_for('siembras.index'))

@bp.route('/detalles/<int:id>')
@login_required
def detalles(id):
    siembra = Siembra.query.get_or_404(id)
    return render_template('siembras/detalles.html', title='Detalles de Siembra', siembra=siembra)