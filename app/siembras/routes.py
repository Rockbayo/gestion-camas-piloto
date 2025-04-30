from flask import render_template, flash, redirect, url_for, request
from flask_login import login_required, current_user
from app import db
from app.siembras import siembras
from app.siembras.forms import SiembraForm, InicioCorteForm
from app.models import Siembra, BloqueCamaLado, Bloque, Cama, Lado

@siembras.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    siembras_list = Siembra.query.order_by(Siembra.fecha_siembra.desc()).paginate(
        page=page, per_page=10)
    return render_template('siembras/index.html', title='Siembras', siembras=siembras_list)

@siembras.route('/crear', methods=['GET', 'POST'])
@login_required
def crear():
    form = SiembraForm()
    if form.validate_on_submit():
        # Buscar o crear bloque_cama_lado
        bloque_cama = BloqueCamaLado.query.filter_by(
            bloque_id=form.bloque_id.data,
            cama_id=form.cama_id.data,
            lado_id=form.lado_id.data
        ).first()
        
        if not bloque_cama:
            bloque_cama = BloqueCamaLado(
                bloque_id=form.bloque_id.data,
                cama_id=form.cama_id.data,
                lado_id=form.lado_id.data
            )
            db.session.add(bloque_cama)
            db.session.commit()
        
        siembra = Siembra(
            bloque_cama_id=bloque_cama.bloque_cama_id,
            variedad_id=form.variedad_id.data,
            area_id=form.area_id.data,
            densidad_id=form.densidad_id.data,
            fecha_siembra=form.fecha_siembra.data,
            usuario_id=current_user.usuario_id)
        db.session.add(siembra)
        db.session.commit()
        flash('La siembra ha sido registrada exitosamente!')
        return redirect(url_for('siembras.index'))
    
    return render_template('siembras/crear.html', title='Nueva Siembra', form=form)

@siembras.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar(id):
    siembra = Siembra.query.get_or_404(id)
    form = SiembraForm()
    
    if form.validate_on_submit():
        # Buscar o crear bloque_cama_lado
        bloque_cama = BloqueCamaLado.query.filter_by(
            bloque_id=form.bloque_id.data,
            cama_id=form.cama_id.data,
            lado_id=form.lado_id.data
        ).first()
        
        if not bloque_cama:
            bloque_cama = BloqueCamaLado(
                bloque_id=form.bloque_id.data,
                cama_id=form.cama_id.data,
                lado_id=form.lado_id.data
            )
            db.session.add(bloque_cama)
            db.session.commit()
        
        siembra.bloque_cama_id = bloque_cama.bloque_cama_id
        siembra.variedad_id = form.variedad_id.data
        siembra.area_id = form.area_id.data
        siembra.densidad_id = form.densidad_id.data
        siembra.fecha_siembra = form.fecha_siembra.data
        
        db.session.commit()
        flash('La siembra ha sido actualizada exitosamente!')
        return redirect(url_for('siembras.index'))
    
    # Prellenar el formulario con los datos existentes
    if request.method == 'GET':
        bloque_cama = BloqueCamaLado.query.get(siembra.bloque_cama_id)
        form.bloque_id.data = bloque_cama.bloque_id
        form.cama_id.data = bloque_cama.cama_id
        form.lado_id.data = bloque_cama.lado_id
        form.variedad_id.data = siembra.variedad_id
        form.area_id.data = siembra.area_id
        form.densidad_id.data = siembra.densidad_id
        form.fecha_siembra.data = siembra.fecha_siembra
    
    return render_template('siembras/editar.html', title='Editar Siembra', form=form, siembra=siembra)

@siembras.route('/inicio-corte/<int:id>', methods=['GET', 'POST'])
@login_required
def inicio_corte(id):
    siembra = Siembra.query.get_or_404(id)
    form = InicioCorteForm()
    
    if form.validate_on_submit():
        siembra.fecha_inicio_corte = form.fecha_inicio_corte.data
        db.session.commit()
        flash('Fecha de inicio de corte registrada con éxito!')
        return redirect(url_for('siembras.index'))
    
    return render_template('siembras/inicio_corte.html', title='Registrar Inicio de Corte', form=form, siembra=siembra)

@siembras.route('/finalizar/<int:id>')
@login_required
def finalizar(id):
    siembra = Siembra.query.get_or_404(id)
    siembra.estado = 'Finalizada'
    db.session.commit()
    flash('La siembra ha sido finalizada con éxito!')
    return redirect(url_for('siembras.index'))

@siembras.route('/detalles/<int:id>')
@login_required
def detalles(id):
    siembra = Siembra.query.get_or_404(id)
    return render_template('siembras/detalles.html', title='Detalles de Siembra', siembra=siembra)