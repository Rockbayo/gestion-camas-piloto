from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.cortes import cortes_bp
from app.cortes.forms import CorteForm, EditarCorteForm, BusquedaCorteForm
from app.models import Corte, Siembra, BloqueCamaLado, Variedad
from datetime import datetime, date

@cortes_bp.route('/cortes')
@login_required
def index():
    """Lista todos los cortes."""
    page = request.args.get('page', 1, type=int)
    form = BusquedaCorteForm()
    
    # Cargar opciones para filtros
    siembras = Siembra.query.all()
    form.siembra_id.choices = [(0, 'Todas las siembras')]
    form.siembra_id.choices.extend([
        (s.siembra_id, f"Siembra {s.siembra_id}: {s.variedad.variedad} en {s.bloque_cama_lado}") 
        for s in siembras
    ])
    
    # Preparar consulta base
    query = Corte.query.join(
        Siembra, Corte.siembra_id == Siembra.siembra_id
    ).join(
        Variedad, Siembra.variedad_id == Variedad.variedad_id
    ).join(
        BloqueCamaLado, Siembra.bloque_cama_id == BloqueCamaLado.bloque_cama_id
    )
    
    # Aplicar filtros si existen
    if request.args.get('siembra_id') and int(request.args.get('siembra_id')) > 0:
        query = query.filter(Siembra.siembra_id == int(request.args.get('siembra_id')))
    
    if request.args.get('fecha_desde'):
        try:
            fecha_desde = datetime.strptime(request.args.get('fecha_desde'), '%Y-%m-%d').date()
            query = query.filter(Corte.fecha_corte >= fecha_desde)
        except ValueError:
            pass
    
    if request.args.get('fecha_hasta'):
        try:
            fecha_hasta = datetime.strptime(request.args.get('fecha_hasta'), '%Y-%m-%d').date()
            query = query.filter(Corte.fecha_corte <= fecha_hasta)
        except ValueError:
            pass
    
    # Ordenar por fecha de corte descendente
    query = query.order_by(Corte.fecha_corte.desc())
    
    # Paginar resultados
    cortes = query.paginate(page=page, per_page=15, error_out=False)
    
    return render_template('cortes/index.html', 
                          cortes=cortes, 
                          form=form)

@cortes_bp.route('/cortes/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_corte():
    """Registrar un nuevo corte."""
    form = CorteForm()
    
    # Cargar siembras activas para el formulario
    siembras_activas = Siembra.query.filter_by(estado='Activa').all()
    form.siembra_id.choices = [
        (s.siembra_id, f"Siembra {s.siembra_id}: {s.variedad.variedad} en {s.bloque_cama_lado}") 
        for s in siembras_activas
    ]
    
    if form.validate_on_submit():
        # Obtener la siembra seleccionada
        siembra = Siembra.query.get(form.siembra_id.data)
        
        # Determinar el número de corte
        ultimo_corte = Corte.query.filter_by(
            siembra_id=siembra.siembra_id
        ).order_by(Corte.num_corte.desc()).first()
        
        num_corte = 1 if not ultimo_corte else ultimo_corte.num_corte + 1
        
        # Si es el primer corte, actualizar la fecha de inicio de corte
        if num_corte == 1:
            siembra.fecha_inicio_corte = form.fecha_corte.data
        
        # Crear nuevo corte
        corte = Corte(
            siembra_id=siembra.siembra_id,
            num_corte=num_corte,
            fecha_corte=form.fecha_corte.data,
            cantidad_tallos=form.cantidad_tallos.data,
            usuario_id=current_user.usuario_id
        )
        
        db.session.add(corte)
        db.session.commit()
        
        flash('Corte registrado exitosamente', 'success')
        return redirect(url_for('cortes.index'))
    
    return render_template('cortes/form.html', 
                          form=form, 
                          title='Nuevo Corte')

@cortes_bp.route('/cortes/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_corte(id):
    """Editar un corte existente."""
    corte = Corte.query.get_or_404(id)
    siembra = Siembra.query.get(corte.siembra_id)
    
    # Solo se pueden editar cortes de siembras activas
    if siembra.estado != 'Activa':
        flash('No se puede editar cortes de siembras finalizadas', 'danger')
        return redirect(url_for('cortes.index'))
    
    form = EditarCorteForm(siembra=siembra)
    
    if request.method == 'GET':
        # Llenar el formulario con los datos actuales
        form.fecha_corte.data = corte.fecha_corte
        form.cantidad_tallos.data = corte.cantidad_tallos
    
    if form.validate_on_submit():
        # Actualizar corte
        corte.fecha_corte = form.fecha_corte.data
        corte.cantidad_tallos = form.cantidad_tallos.data
        
        # Si es el primer corte, actualizar la fecha de inicio de corte de la siembra
        if corte.num_corte == 1:
            siembra.fecha_inicio_corte = form.fecha_corte.data
        
        db.session.commit()
        
        flash('Corte actualizado exitosamente', 'success')
        return redirect(url_for('cortes.index'))
    
    return render_template('cortes/editar.html', 
                          form=form, 
                          corte=corte,
                          siembra=siembra,
                          title='Editar Corte')

@cortes_bp.route('/cortes/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_corte(id):
    """Eliminar un corte."""
    corte = Corte.query.get_or_404(id)
    siembra = Siembra.query.get(corte.siembra_id)
    
    # Solo se pueden eliminar cortes de siembras activas
    if siembra.estado != 'Activa':
        flash('No se puede eliminar cortes de siembras finalizadas', 'danger')
        return redirect(url_for('cortes.index'))
    
    # Si es el primer corte y existe un segundo corte, actualizar la fecha de inicio
    if corte.num_corte == 1:
        siguiente_corte = Corte.query.filter_by(
            siembra_id=siembra.siembra_id, 
            num_corte=2
        ).first()
        
        if siguiente_corte:
            # Si hay un segundo corte, ese pasa a ser el primer corte
            siembra.fecha_inicio_corte = siguiente_corte.fecha_corte
        else:
            # Si no hay más cortes, resetear la fecha de inicio
            siembra.fecha_inicio_corte = None
    
    # Eliminar el corte
    db.session.delete(corte)
    
    # Renumerar los cortes posteriores
    cortes_posteriores = Corte.query.filter(
        Corte.siembra_id == siembra.siembra_id,
        Corte.num_corte > corte.num_corte
    ).order_by(Corte.num_corte).all()
    
    for c in cortes_posteriores:
        c.num_corte -= 1
    
    db.session.commit()
    
    flash('Corte eliminado exitosamente', 'success')
    return redirect(url_for('cortes.index'))

@cortes_bp.route('/cortes/por_siembra/<int:siembra_id>')
@login_required
def cortes_por_siembra(siembra_id):
    """Ver todos los cortes de una siembra específica."""
    siembra = Siembra.query.get_or_404(siembra_id)
    cortes = Corte.query.filter_by(siembra_id=siembra_id).order_by(Corte.num_corte).all()
    
    return render_template('cortes/por_siembra.html',
                          siembra=siembra,
                          cortes=cortes)