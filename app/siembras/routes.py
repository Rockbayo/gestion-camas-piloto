# Rutas para la gestión de siembras
from flask import render_template, flash, redirect, url_for, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.siembras import bp
from app.siembras.forms import SiembraForm, InicioCorteForm
from app.models import Siembra, BloqueCamaLado, Variedad, Area, Densidad, Flor, Color, FlorColor, Bloque, Cama, Lado
from datetime import datetime
from sqlalchemy import and_
from sqlalchemy import func


@bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    siembras_list = Siembra.query.order_by(Siembra.fecha_siembra.desc()).paginate(
        page=page, per_page=10)
    return render_template('siembras/index.html', title='Siembras', siembras=siembras_list)

@bp.route('/crear', methods=['GET', 'POST'])
@login_required
def crear():
    form = SiembraForm()
    
    # Si se envía un filtro de flor o color vía AJAX
    if request.method == 'GET' and request.args.get('filter') == 'true':
        flor_id = request.args.get('flor_id', type=int)
        color_id = request.args.get('color_id', type=int)
        
        # Construir consulta para filtrar variedades
        query = Variedad.query
        
        if flor_id and flor_id > 0:
            query = query.join(Variedad.flor_color).join(FlorColor.flor).filter(Flor.flor_id == flor_id)
        
        if color_id and color_id > 0:
            query = query.join(Variedad.flor_color).join(FlorColor.color).filter(Color.color_id == color_id)
        
        # Obtener las variedades filtradas
        variedades = query.order_by(Variedad.variedad).all()
        
        # Devolver como JSON para actualizar el select
        return jsonify([{'id': v.variedad_id, 'text': v.variedad} for v in variedades])
    
    # Si se solicita calcular el área vía AJAX
    if request.method == 'GET' and request.args.get('calculate') == 'true':
        cantidad_plantas = request.args.get('cantidad_plantas', type=int)
        densidad_id = request.args.get('densidad_id', type=int)
        
        if cantidad_plantas and densidad_id:
            try:
                # Obtener la densidad (plantas por metro cuadrado)
                densidad = Densidad.query.get(densidad_id)
                if not densidad:
                    return jsonify({'error': f'No se encontró la densidad con ID: {densidad_id}'})
                
                # Verificar que el valor de densidad sea mayor que cero
                if not densidad.valor or densidad.valor <= 0:
                    return jsonify({'error': f'La densidad {densidad.densidad} tiene un valor inválido: {densidad.valor}'})
                
                # Calcular el área = cantidad de plantas / densidad (plantas/m²)
                area_calculada = round(cantidad_plantas / densidad.valor, 2)
                
                # Generar un nombre para el área si no existe
                area_nombre = f"ÁREA {area_calculada}m²"
                
                # Ampliar el margen de búsqueda para encontrar más coincidencias
                # O simplificar para buscar áreas con valores exactos o muy cercanos
                from sqlalchemy import func  # Asegúrate de importar func de SQLAlchemy
                area = Area.query.filter(
                    func.abs(Area.area - area_calculada) < 0.1  # Diferencia menor a 0.1 m²
                ).first()
                
                # Si no se encuentra un área similar, crear una nueva descripción 
                # pero no guardarla todavía (se creará al guardar la siembra)
                if area:
                    area_id = area.area_id
                    area_nombre = area.siembra
                else:
                    area_id = None
                    # Convertir a un formato más legible
                    area_nombre = f"ÁREA {area_calculada:.2f}m²"
                
                return jsonify({
                    'area_calculada': area_calculada,
                    'area_id': area_id,
                    'area_nombre': area_nombre
                })
            except Exception as e:
                print(f"Error al calcular área: {str(e)}")
                return jsonify({'error': f'Error al calcular área: {str(e)}'})
        
        return jsonify({'error': 'No se pudo calcular el área'})
    
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
            
        # Calcular y buscar el área según la cantidad de plantas y densidad
        densidad = Densidad.query.get(form.densidad_id.data)
        area_calculada = form.cantidad_plantas.data / densidad.valor if densidad else 0
        
        # Buscar un área existente o crear una nueva
        area = None
        if form.area_id.data:
            area = Area.query.get(form.area_id.data)
        
        if not area:
            # Crear una descripción para el área
            area_nombre = f"ÁREA {area_calculada:.2f}m²"
            
            # Buscar si ya existe un área con este nombre
            area = Area.query.filter_by(siembra=area_nombre).first()
            
            # Si no existe, crear una nueva
            if not area:
                area = Area(siembra=area_nombre, area=area_calculada)
                db.session.add(area)
                db.session.flush()  # Obtener el ID
        
        # Crear la siembra
        siembra = Siembra(
            bloque_cama_id=bloque_cama.bloque_cama_id,
            variedad_id=form.variedad_id.data,
            area_id=area.area_id,
            densidad_id=form.densidad_id.data,
            fecha_siembra=form.fecha_siembra.data,
            usuario_id=current_user.usuario_id
        )
        
        db.session.add(siembra)
        db.session.commit()
        
        flash('La siembra ha sido registrada exitosamente!', 'success')
        return redirect(url_for('siembras.index'))
    
    return render_template('siembras/crear.html', title='Nueva Siembra', form=form)

@bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar(id):
    # Obtener la siembra existente
    siembra = Siembra.query.get_or_404(id)
    
    # Verificar que la siembra esté activa
    if siembra.estado != 'Activa':
        flash('No se pueden editar siembras finalizadas', 'warning')
        return redirect(url_for('siembras.index'))
    
    # Obtener el bloque_cama_lado actual
    bloque_cama = BloqueCamaLado.query.get(siembra.bloque_cama_id)
    if not bloque_cama:
        flash('Error: No se encontró la ubicación de la siembra', 'danger')
        return redirect(url_for('siembras.index'))
    
    # Inicializar el formulario
    form = SiembraForm()
    
    # Si se envía el formulario y pasa la validación
    if form.validate_on_submit():
        try:
            # Buscar si ya existe la combinación bloque-cama-lado solicitada
            nueva_ubicacion = BloqueCamaLado.query.filter_by(
                bloque_id=form.bloque_id.data,
                cama_id=form.cama_id.data,
                lado_id=form.lado_id.data
            ).first()
            
            # Si no existe, crear una nueva
            if not nueva_ubicacion:
                nueva_ubicacion = BloqueCamaLado(
                    bloque_id=form.bloque_id.data,
                    cama_id=form.cama_id.data,
                    lado_id=form.lado_id.data
                )
                db.session.add(nueva_ubicacion)
                db.session.flush()  # Para obtener el ID generado
            
            # Actualizar la siembra con los nuevos datos
            siembra.bloque_cama_id = nueva_ubicacion.bloque_cama_id
            siembra.variedad_id = form.variedad_id.data
            siembra.densidad_id = form.densidad_id.data
            siembra.fecha_siembra = form.fecha_siembra.data
            
            # Si se proporciona un nuevo área_id, actualizarlo
            if form.area_id.data:
                siembra.area_id = form.area_id.data
            
            # Guardar los cambios
            db.session.commit()
            
            flash('La siembra ha sido actualizada exitosamente!', 'success')
            return redirect(url_for('siembras.detalles', id=siembra.siembra_id))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar la siembra: {str(e)}', 'danger')
    
    # Si es una solicitud GET o si hay errores en el formulario
    # Prellenar el formulario con los datos existentes
    if request.method == 'GET':
        form.bloque_id.data = bloque_cama.bloque_id
        form.cama_id.data = bloque_cama.cama_id
        form.lado_id.data = bloque_cama.lado_id
        form.variedad_id.data = siembra.variedad_id
        form.densidad_id.data = siembra.densidad_id
        form.fecha_siembra.data = siembra.fecha_siembra
        form.area_id.data = siembra.area_id
        
        # Obtener la cantidad de plantas basada en el área y densidad
        try:
            area = Area.query.get(siembra.area_id)
            densidad = Densidad.query.get(siembra.densidad_id)
            if area and densidad and densidad.valor > 0:
                cantidad_plantas = calc_plantas_totales(area.area, densidad.valor)
                form.cantidad_plantas.data = cantidad_plantas
            else:
                form.cantidad_plantas.data = 0
        except Exception as e:
            form.cantidad_plantas.data = 0
    
    return render_template('siembras/editar.html', title='Editar Siembra', form=form, siembra=siembra)
@bp.route('/inicio-corte/<int:id>', methods=['GET', 'POST'])
@login_required
def inicio_corte(id):
    siembra = Siembra.query.get_or_404(id)
    
    # Verificar que la siembra esté activa
    if siembra.estado != 'Activa':
        flash('No se puede registrar inicio de corte en una siembra finalizada', 'warning')
        return redirect(url_for('siembras.index'))
    
    # Verificar que no tenga ya una fecha de inicio de corte
    if siembra.fecha_inicio_corte:
        flash('Esta siembra ya tiene una fecha de inicio de corte registrada', 'warning')
        return redirect(url_for('siembras.detalles', id=id))
    
    form = InicioCorteForm()
    
    if form.validate_on_submit():
        # Verificar que la fecha de inicio de corte no sea anterior a la fecha de siembra
        if form.fecha_inicio_corte.data < siembra.fecha_siembra:
            flash('La fecha de inicio de corte no puede ser anterior a la fecha de siembra', 'danger')
            return redirect(url_for('siembras.inicio_corte', id=id))
        
        # Asignar fecha de inicio de corte y guardar
        siembra.fecha_inicio_corte = form.fecha_inicio_corte.data
        try:
            db.session.commit()
            flash('Fecha de inicio de corte registrada con éxito!', 'success')
            return redirect(url_for('siembras.detalles', id=id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al registrar inicio de corte: {str(e)}', 'danger')
    
    return render_template('siembras/inicio_corte.html', title='Registrar Inicio de Corte', form=form, siembra=siembra)

@bp.route('/finalizar/<int:id>')
@login_required
def finalizar(id):
    siembra = Siembra.query.get_or_404(id)
    
    # Verificar que la siembra esté activa
    if siembra.estado != 'Activa':
        flash('Esta siembra ya ha sido finalizada', 'warning')
        return redirect(url_for('siembras.index'))
    
    # Establecer la fecha de fin de corte si no está establecida
    if not siembra.fecha_fin_corte:
        # Si hay cortes, usar la fecha del último corte
        if siembra.cortes:
            ultima_fecha = max([corte.fecha_corte for corte in siembra.cortes])
            siembra.fecha_fin_corte = ultima_fecha
        else:
            # Si no hay cortes, usar la fecha actual
            siembra.fecha_fin_corte = datetime.now().date()
    
    siembra.estado = 'Finalizada'
    db.session.commit()
    flash('La siembra ha sido finalizada con éxito!', 'success')
    return redirect(url_for('siembras.index'))

@bp.route('/detalles/<int:id>')
@login_required
def detalles(id):
    siembra = Siembra.query.get_or_404(id)
    return render_template('siembras/detalles.html', title='Detalles de Siembra', siembra=siembra)

