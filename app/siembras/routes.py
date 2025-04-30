from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.siembras import siembras_bp
from app.siembras.forms import SiembraForm, FinalizarSiembraForm, BusquedaSiembraForm
from app.models import (
    Bloque, Cama, Lado, BloqueCamaLado, Variedad, FlorColor,
    Area, Densidad, Siembra, Flor, Color, Corte, Perdida
)
from datetime import datetime

@siembras_bp.route('/siembras')
@login_required
def index():
    """Lista todas las siembras."""
    page = request.args.get('page', 1, type=int)
    form = BusquedaSiembraForm()
    
    # Cargar opciones para filtros
    form.bloque_id.choices = [(0, 'Todos los bloques')]
    form.bloque_id.choices.extend([(b.bloque_id, b.bloque) for b in Bloque.query.all()])
    
    form.variedad_id.choices = [(0, 'Todas las variedades')]
    form.variedad_id.choices.extend([(v.variedad_id, v.variedad) for v in Variedad.query.all()])
    
    # Preparar consulta base
    query = Siembra.query.join(
        BloqueCamaLado, Siembra.bloque_cama_id == BloqueCamaLado.bloque_cama_id
    ).join(
        Bloque, BloqueCamaLado.bloque_id == Bloque.bloque_id
    ).join(
        Variedad, Siembra.variedad_id == Variedad.variedad_id
    )
    
    # Aplicar filtros si existen
    if request.args.get('estado'):
        query = query.filter(Siembra.estado == request.args.get('estado'))
    
    if request.args.get('bloque_id') and int(request.args.get('bloque_id')) > 0:
        query = query.filter(Bloque.bloque_id == int(request.args.get('bloque_id')))
    
    if request.args.get('variedad_id') and int(request.args.get('variedad_id')) > 0:
        query = query.filter(Variedad.variedad_id == int(request.args.get('variedad_id')))
    
    # Ordenar por fecha de siembra descendente
    query = query.order_by(Siembra.fecha_siembra.desc())
    
    # Paginar resultados
    siembras = query.paginate(page=page, per_page=15, error_out=False)
    
    return render_template('siembras/index.html', 
                           siembras=siembras, 
                           form=form)

@siembras_bp.route('/siembras/nueva', methods=['GET', 'POST'])
@login_required
def nueva_siembra():
    """Registrar una nueva siembra."""
    form = SiembraForm()
    
    # Cargar opciones para los campos de selección
    cargar_opciones_formulario(form)
    
    if form.validate_on_submit():
        # Crear nueva siembra
        siembra = Siembra(
            bloque_cama_id=form.bloque_cama_id.data,
            variedad_id=form.variedad_id.data,
            area_id=form.area_id.data,
            densidad_id=form.densidad_id.data,
            fecha_siembra=form.fecha_siembra.data,
            usuario_id=current_user.usuario_id
        )
        
        db.session.add(siembra)
        db.session.commit()
        
        flash('Siembra registrada exitosamente', 'success')
        return redirect(url_for('siembras.index'))
    
    return render_template('siembras/form.html', 
                          form=form, 
                          title='Nueva Siembra')

@siembras_bp.route('/siembras/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_siembra(id):
    """Editar una siembra existente."""
    siembra = Siembra.query.get_or_404(id)
    
    # Solo se pueden editar siembras activas
    if siembra.estado != 'Activa':
        flash('No se puede editar una siembra finalizada', 'danger')
        return redirect(url_for('siembras.ver_siembra', id=id))
    
    form = SiembraForm(original_siembra_id=id)
    
    # Cargar opciones para los campos de selección
    cargar_opciones_formulario(form)
    
    if request.method == 'GET':
        # Llenar el formulario con los datos actuales
        form.bloque_cama_id.data = siembra.bloque_cama_id
        form.variedad_id.data = siembra.variedad_id
        form.area_id.data = siembra.area_id
        form.densidad_id.data = siembra.densidad_id
        form.fecha_siembra.data = siembra.fecha_siembra
    
    if form.validate_on_submit():
        # Actualizar siembra
        siembra.bloque_cama_id = form.bloque_cama_id.data
        siembra.variedad_id = form.variedad_id.data
        siembra.area_id = form.area_id.data
        siembra.densidad_id = form.densidad_id.data
        siembra.fecha_siembra = form.fecha_siembra.data
        
        db.session.commit()
        
        flash('Siembra actualizada exitosamente', 'success')
        return redirect(url_for('siembras.ver_siembra', id=id))
    
    return render_template('siembras/form.html', 
                          form=form, 
                          title='Editar Siembra')

@siembras_bp.route('/siembras/ver/<int:id>')
@login_required
def ver_siembra(id):
    """Ver detalles de una siembra específica."""
    siembra = Siembra.query.get_or_404(id)
    
    # Obtener cortes asociados
    cortes = Corte.query.filter_by(siembra_id=id).order_by(Corte.num_corte).all()
    
    # Obtener pérdidas asociadas
    perdidas = Perdida.query.filter_by(siembra_id=id).order_by(Perdida.fecha_perdida).all()
    
    # Calcular indicadores
    total_tallos = siembra.total_tallos
    total_perdidas = siembra.total_perdidas
    dias_ciclo = siembra.dias_ciclo
    
    # Calcular productividad (tallos/m²)
    productividad = 0
    if siembra.area_siembra.area > 0:
        productividad = total_tallos / siembra.area_siembra.area
    
    return render_template('siembras/detalle.html',
                          siembra=siembra,
                          cortes=cortes,
                          perdidas=perdidas,
                          total_tallos=total_tallos,
                          total_perdidas=total_perdidas,
                          dias_ciclo=dias_ciclo,
                          productividad=productividad)

@siembras_bp.route('/siembras/finalizar/<int:id>', methods=['GET', 'POST'])
@login_required
def finalizar_siembra(id):
    """Finalizar una siembra activa."""
    siembra = Siembra.query.get_or_404(id)
    
    # Verificar que la siembra esté activa
    if siembra.estado != 'Activa':
        flash('Esta siembra ya está finalizada', 'warning')
        return redirect(url_for('siembras.ver_siembra', id=id))
    
    form = FinalizarSiembraForm()
    
    if form.validate_on_submit():
        # Actualizar estado
        siembra.estado = 'Finalizada'
        
        # Registrar observaciones si existen
        if form.observaciones.data:
            # Se podría implementar un modelo adicional para registrar observaciones
            pass
        
        db.session.commit()
        
        flash('Siembra finalizada exitosamente', 'success')
        return redirect(url_for('siembras.ver_siembra', id=id))
    
    return render_template('siembras/finalizar.html',
                          form=form,
                          siembra=siembra)

# Función auxiliar para cargar opciones en el formulario
def cargar_opciones_formulario(form):
    """Carga las opciones para los campos select del formulario."""
    # Cargar opciones para ubicaciones (bloque-cama-lado)
    # Sólo cargar ubicaciones que no tengan siembras activas
    ubicaciones_disponibles = db.session.query(
        BloqueCamaLado
    ).outerjoin(
        Siembra, db.and_(
            BloqueCamaLado.bloque_cama_id == Siembra.bloque_cama_id,
            Siembra.estado == 'Activa'
        )
    ).filter(
        Siembra.siembra_id.is_(None)
    ).all()
    
    # Si estamos editando, incluir la ubicación actual
    if hasattr(form, 'original_siembra_id') and form.original_siembra_id:
        siembra_actual = Siembra.query.get(form.original_siembra_id)
        if siembra_actual and siembra_actual.bloque_cama_id not in [u.bloque_cama_id for u in ubicaciones_disponibles]:
            ubicaciones_disponibles.append(siembra_actual.bloque_cama_lado)
    
    form.bloque_cama_id.choices = [(u.bloque_cama_id, str(u)) for u in ubicaciones_disponibles]
    
    # Cargar opciones para variedades
    variedades = Variedad.query.all()
    form.variedad_id.choices = [(v.variedad_id, v.variedad) for v in variedades]
    
    # Cargar opciones para áreas
    areas = Area.query.all()
    form.area_id.choices = [(a.area_id, str(a)) for a in areas]
    
    # Cargar opciones para densidades
    densidades = Densidad.query.all()
    form.densidad_id.choices = [(d.densidad_id, d.densidad) for d in densidades]