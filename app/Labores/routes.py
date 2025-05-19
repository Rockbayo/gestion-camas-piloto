from flask import render_template, flash, redirect, url_for, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.labores import bp
from app.labores.forms import TipoLaborForm, LaborCulturalForm
from app.models import Siembra, LaborCultural, TipoLabor, Flor
from datetime import datetime

@bp.route('/')
@login_required
def index():
    """Vista principal del módulo de labores culturales"""
    # Obtener parámetros de filtrado
    siembra_id = request.args.get('siembra_id', type=int)
    flor_id = request.args.get('flor_id', type=int)
    fecha_desde = request.args.get('fecha_desde', type=str)
    fecha_hasta = request.args.get('fecha_hasta', type=str)
    
    # Construir consulta base
    query = LaborCultural.query
    
    # Aplicar filtros
    if siembra_id:
        query = query.filter(LaborCultural.siembra_id == siembra_id)
    
    if flor_id:
        query = query.join(Siembra).join(Siembra.variedad).join(
            Variedad.flor_color).join(FlorColor.flor).filter(Flor.flor_id == flor_id)
    
    if fecha_desde:
        try:
            fecha_desde_obj = datetime.strptime(fecha_desde, '%Y-%m-%d').date()
            query = query.filter(LaborCultural.fecha_labor >= fecha_desde_obj)
        except ValueError:
            flash('Formato de fecha inválido', 'danger')
    
    if fecha_hasta:
        try:
            fecha_hasta_obj = datetime.strptime(fecha_hasta, '%Y-%m-%d').date()
            query = query.filter(LaborCultural.fecha_labor <= fecha_hasta_obj)
        except ValueError:
            flash('Formato de fecha inválido', 'danger')
    
    # Ejecutar consulta paginada
    page = request.args.get('page', 1, type=int)
    labores = query.order_by(LaborCultural.fecha_labor.desc()).paginate(page=page, per_page=10)
    
    # Obtener lista de tipos de flores para filtrado
    flores = Flor.query.order_by(Flor.flor).all()
    
    return render_template('labores/index.html',
                           title='Labores Culturales',
                           labores=labores,
                           flores=flores,
                           siembra_id=siembra_id,
                           flor_id=flor_id,
                           fecha_desde=fecha_desde,
                           fecha_hasta=fecha_hasta)

@bp.route('/tipos')
@login_required
def tipos_labor():
    """Vista para gestionar tipos de labores culturales"""
    tipos = TipoLabor.query.order_by(TipoLabor.nombre).all()
    return render_template('labores/tipos.html',
                           title='Tipos de Labores Culturales',
                           tipos=tipos)

@bp.route('/tipos/crear', methods=['GET', 'POST'])
@login_required
def crear_tipo():
    """Vista para crear un nuevo tipo de labor cultural"""
    # Verificar permisos
    if not current_user.has_permission('importar_datos'):
        flash('No tienes permiso para realizar esta acción', 'danger')
        return redirect(url_for('labores.tipos_labor'))
    
    form = TipoLaborForm()
    
    # Cargar opciones para flor_id
    form.flor_id.choices = [(0, 'Todas las flores')] + [(f.flor_id, f.flor) for f in Flor.query.order_by(Flor.flor)]
    
    if form.validate_on_submit():
        # Procesar flor_id (si es 0, establecer como None)
        flor_id = form.flor_id.data if form.flor_id.data > 0 else None
        
        # Crear nuevo tipo
        tipo_labor = TipoLabor(
            nombre=form.nombre.data,
            descripcion=form.descripcion.data,
            flor_id=flor_id
        )
        
        db.session.add(tipo_labor)
        try:
            db.session.commit()
            flash(f'Tipo de labor "{form.nombre.data}" creado exitosamente', 'success')
            return redirect(url_for('labores.tipos_labor'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear tipo de labor: {str(e)}', 'danger')
    
    return render_template('labores/crear_tipo.html',
                           title='Crear Tipo de Labor',
                           form=form)

@bp.route('/tipos/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_tipo(id):
    """Vista para editar un tipo de labor cultural existente"""
    # Verificar permisos
    if not current_user.has_permission('importar_datos'):
        flash('No tienes permiso para realizar esta acción', 'danger')
        return redirect(url_for('labores.tipos_labor'))
    
    tipo = TipoLabor.query.get_or_404(id)
    form = TipoLaborForm()
    
    # Cargar opciones para flor_id
    form.flor_id.choices = [(0, 'Todas las flores')] + [(f.flor_id, f.flor) for f in Flor.query.order_by(Flor.flor)]
    
    if form.validate_on_submit():
        tipo.nombre = form.nombre.data
        tipo.descripcion = form.descripcion.data
        tipo.flor_id = form.flor_id.data if form.flor_id.data > 0 else None
        
        try:
            db.session.commit()
            flash(f'Tipo de labor "{tipo.nombre}" actualizado exitosamente', 'success')
            return redirect(url_for('labores.tipos_labor'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar tipo de labor: {str(e)}', 'danger')
    
    # Prellenar el formulario con los datos existentes
    if request.method == 'GET':
        form.nombre.data = tipo.nombre
        form.descripcion.data = tipo.descripcion
        form.flor_id.data = tipo.flor_id if tipo.flor_id else 0
    
    return render_template('labores/editar_tipo.html',
                           title='Editar Tipo de Labor',
                           form=form,
                           tipo=tipo)

@bp.route('/tipos/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_tipo(id):
    """Vista para eliminar un tipo de labor cultural"""
    # Verificar permisos
    if not current_user.has_permission('importar_datos'):
        flash('No tienes permiso para realizar esta acción', 'danger')
        return redirect(url_for('labores.tipos_labor'))
    
    tipo = TipoLabor.query.get_or_404(id)
    
    # Verificar si hay labores asociadas a este tipo
    labores_asociadas = LaborCultural.query.filter_by(tipo_labor_id=id).count()
    if labores_asociadas > 0:
        flash(f'No se puede eliminar el tipo de labor "{tipo.nombre}" porque tiene {labores_asociadas} labores asociadas', 'danger')
        return redirect(url_for('labores.tipos_labor'))
    
    try:
        db.session.delete(tipo)
        db.session.commit()
        flash(f'Tipo de labor "{tipo.nombre}" eliminado exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar tipo de labor: {str(e)}', 'danger')
    
    return redirect(url_for('labores.tipos_labor'))

@bp.route('/registrar/<int:siembra_id>', methods=['GET', 'POST'])
@login_required
def registrar(siembra_id):
    """Vista para registrar una nueva labor cultural"""
    # Obtener la siembra
    siembra = Siembra.query.get_or_404(siembra_id)
    
    # Verificar que la siembra esté activa
    if siembra.estado != 'Activa':
        flash('No se pueden registrar labores para una siembra finalizada', 'warning')
        return redirect(url_for('siembras.detalles', id=siembra_id))
    
    form = LaborCulturalForm()
    form.siembra_id.data = siembra_id
    
    # Obtener tipos de labor apropiados para esta variedad
    # Si la variedad tiene un tipo de flor específico, mostrar labores generales y específicas
    flor_id = siembra.variedad.flor_color.flor.flor_id
    
    # Buscar tipos de labor generales (flor_id=NULL) y específicos para esta flor
    tipos_labor = TipoLabor.query.filter(
        (TipoLabor.flor_id.is_(None)) | (TipoLabor.flor_id == flor_id)
    ).order_by(TipoLabor.nombre).all()
    
    # Cargar opciones de tipos de labor
    form.tipo_labor_id.choices = [(t.tipo_labor_id, t.nombre) for t in tipos_labor]
    
    if form.validate_on_submit():
        # Crear nueva labor cultural
        labor = LaborCultural(
            siembra_id=siembra_id,
            tipo_labor_id=form.tipo_labor_id.data,
            fecha_labor=form.fecha_labor.data,
            observaciones=form.observaciones.data,
            usuario_id=current_user.usuario_id
        )
        
        db.session.add(labor)
        try:
            db.session.commit()
            flash('Labor cultural registrada exitosamente', 'success')
            return redirect(url_for('siembras.detalles', id=siembra_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al registrar labor cultural: {str(e)}', 'danger')
    
    return render_template('labores/registrar.html',
                           title='Registrar Labor Cultural',
                           form=form,
                           siembra=siembra)

@bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar(id):
    """Vista para editar una labor cultural"""
    labor = LaborCultural.query.get_or_404(id)
    siembra = labor.siembra
    
    # Verificar que la siembra esté activa
    if siembra.estado != 'Activa':
        flash('No se pueden editar labores de una siembra finalizada', 'warning')
        return redirect(url_for('siembras.detalles', id=siembra.siembra_id))
    
    form = LaborCulturalForm()
    
    # Obtener tipos de labor apropiados para esta variedad
    flor_id = siembra.variedad.flor_color.flor.flor_id
    
    # Buscar tipos de labor generales (flor_id=NULL) y específicos para esta flor
    tipos_labor = TipoLabor.query.filter(
        (TipoLabor.flor_id.is_(None)) | (TipoLabor.flor_id == flor_id)
    ).order_by(TipoLabor.nombre).all()
    
    # Cargar opciones de tipos de labor
    form.tipo_labor_id.choices = [(t.tipo_labor_id, t.nombre) for t in tipos_labor]
    
    if form.validate_on_submit():
        labor.tipo_labor_id = form.tipo_labor_id.data
        labor.fecha_labor = form.fecha_labor.data
        labor.observaciones = form.observaciones.data
        
        try:
            db.session.commit()
            flash('Labor cultural actualizada exitosamente', 'success')
            return redirect(url_for('siembras.detalles', id=siembra.siembra_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar labor cultural: {str(e)}', 'danger')
    
    # Prellenar el formulario con los datos existentes
    if request.method == 'GET':
        form.siembra_id.data = siembra.siembra_id
        form.tipo_labor_id.data = labor.tipo_labor_id
        form.fecha_labor.data = labor.fecha_labor
        form.observaciones.data = labor.observaciones
    
    return render_template('labores/editar.html',
                           title='Editar Labor Cultural',
                           form=form,
                           labor=labor,
                           siembra=siembra)

@bp.route('/eliminar/<int:id>')
@login_required
def eliminar(id):
    """Vista para eliminar una labor cultural"""
    labor = LaborCultural.query.get_or_404(id)
    siembra_id = labor.siembra_id
    
    # Verificar que la siembra esté activa
    if labor.siembra.estado != 'Activa':
        flash('No se pueden eliminar labores de una siembra finalizada', 'warning')
        return redirect(url_for('siembras.detalles', id=siembra_id))
    
    try:
        db.session.delete(labor)
        db.session.commit()
        flash('Labor cultural eliminada exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar labor cultural: {str(e)}', 'danger')
    
    return redirect(url_for('siembras.detalles', id=siembra_id))

@bp.route('/por_siembra/<int:siembra_id>')
@login_required
def por_siembra(siembra_id):
    """Vista para listar labores culturales de una siembra específica"""
    siembra = Siembra.query.get_or_404(siembra_id)
    labores = LaborCultural.query.filter_by(siembra_id=siembra_id).order_by(LaborCultural.fecha_labor.desc()).all()
    
    return render_template('labores/por_siembra.html',
                           title=f'Labores Culturales - Siembra #{siembra_id}',
                           siembra=siembra,
                           labores=labores)