from flask import render_template, flash, redirect, url_for, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from . import bp
from .forms import SiembraForm, InicioCorteForm
from .services import SiembraService
from app.models import Siembra, Area, Densidad, Color, Variedad, FlorColor
from app import db
from sqlalchemy import func

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
        # Filtrado de variedades (manteniendo compatibilidad con código existente)
        if request.args.get('filter') == 'true':
            variedades = SiembraService.filtrar_variedades(
                request.args.get('flor_id', type=int),
                request.args.get('color_id', type=int)
            )
            return jsonify([{'id': v.variedad_id, 'text': v.variedad} for v in variedades])
        
        # Cálculo de área (manteniendo compatibilidad con código existente)
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

@bp.route('/api/colores/<int:flor_id>')
@login_required
def get_colores_por_flor(flor_id):
    """
    API endpoint para obtener colores disponibles para una flor específica.
    """
    try:
        if flor_id == 0:  # "Todas las flores"
            colores = Color.query.order_by(Color.color).all()
        else:
            # Obtener colores que tienen combinación con esta flor
            colores = Color.query.join(FlorColor).filter(
                FlorColor.flor_id == flor_id
            ).order_by(Color.color).all()
        
        colores_data = [
            {'id': color.color_id, 'nombre': color.color}
            for color in colores
        ]
        
        return jsonify({
            'success': True,
            'colores': colores_data
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/variedades/<int:flor_id>/<int:color_id>')
@login_required
def get_variedades_por_flor_color(flor_id, color_id):
    """
    API endpoint para obtener variedades disponibles para una combinación flor-color.
    """
    try:
        query = Variedad.query.join(FlorColor)
        
        # Filtrar por flor si no es "Todas las flores"
        if flor_id != 0:
            query = query.filter(FlorColor.flor_id == flor_id)
        
        # Filtrar por color si no es "Todos los colores"
        if color_id != 0:
            query = query.filter(FlorColor.color_id == color_id)
        
        variedades = query.order_by(Variedad.variedad).all()
        
        variedades_data = [
            {
                'id': variedad.variedad_id,
                'nombre': variedad.variedad,
                'flor': variedad.flor_color.flor.flor,
                'color': variedad.flor_color.color.color,
                'nombre_completo': variedad.variedad  # Solo el nombre de la variedad
            }
            for variedad in variedades
        ]
        
        return jsonify({
            'success': True,
            'variedades': variedades_data
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/calcular-area')
@login_required
def calcular_area_ajax():
    """
    API endpoint para calcular área basada en cantidad de plantas y densidad.
    """
    try:
        cantidad_plantas = request.args.get('cantidad_plantas', type=int)
        densidad_id = request.args.get('densidad_id', type=int)
        
        if not cantidad_plantas or not densidad_id:
            return jsonify({
                'success': False,
                'error': 'Parámetros faltantes'
            }), 400
        
        # Obtener la densidad
        densidad = Densidad.query.get(densidad_id)
        if not densidad:
            return jsonify({
                'success': False,
                'error': 'Densidad no encontrada'
            }), 404
        
        # Calcular área
        area_calculada = round(float(cantidad_plantas) / float(densidad.valor), 2)
        
        # Buscar o crear área
        area_nombre = f"ÁREA {area_calculada}m²"
        area = Area.query.filter(
            Area.area.between(area_calculada * 0.99, area_calculada * 1.01)
        ).first()
        
        if not area:
            area = Area(siembra=area_nombre, area=area_calculada)
            db.session.add(area)
            db.session.flush()
            db.session.commit()
        
        return jsonify({
            'success': True,
            'area_calculada': area_calculada,
            'area_id': area.area_id,
            'area_nombre': area.siembra
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

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