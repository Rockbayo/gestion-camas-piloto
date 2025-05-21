from flask import render_template, flash, redirect, url_for, request, session
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.admin import bp
from app.admin.forms import (
    ImportDatasetForm, MappingVariedadesForm, MappingBloquesForm, DensidadForm
)
from app.models import (
    Variedad, FlorColor, Flor, Color, Bloque, Cama, Lado, BloqueCamaLado,
    Densidad, Siembra
)
from app.utils import DatasetImporter
import os
import json
import uuid

# Configuración
TEMP_DIR = os.path.join('uploads', 'temp')
os.makedirs(TEMP_DIR, exist_ok=True)

def _clean_session_file():
    """Limpia archivos temporales de sesiones anteriores"""
    if 'temp_file' in session:
        temp_file = session.pop('temp_file')
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except OSError:
                pass

def _check_permission():
    """Verifica permisos del usuario"""
    if not current_user.has_permission('importar_datos'):
        flash('No tienes permiso para esta acción', 'danger')
        return False
    return True

def _get_filtered_query(model, filters, join_models=None):
    """Crea una consulta filtrada"""
    query = model.query
    if join_models:
        for join_model in join_models:
            query = query.join(join_model)
    
    for field, value in filters.items():
        if value:
            query = query.filter(getattr(model, field).ilike(f'%{value}%'))
    return query

# Vistas principales
@bp.route('/datasets', methods=['GET', 'POST'])
@login_required
def datasets():
    """Gestión de datasets"""
    _clean_session_file()
    form = ImportDatasetForm()
    
    if form.validate_on_submit():
        temp_path = DatasetImporter.save_temp_file(form.excel_file.data)
        session.update({
            'temp_file': temp_path,
            'dataset_type': form.dataset_type.data,
            'original_filename': secure_filename(form.excel_file.data.filename)
        })
        flash('Archivo cargado correctamente.', 'success')
        return redirect(url_for('admin.preview_dataset', dataset_type=form.dataset_type.data))
    
    return render_template('admin/datasets.html', title='Gestión de Datasets', form=form)

@bp.route('/datasets/preview/<dataset_type>', methods=['GET', 'POST'])
@login_required
def preview_dataset(dataset_type):
    """Previsualización de datasets"""
    if not _check_permission():
        return redirect(url_for('main.index'))
    
    temp_file = session.get('temp_file')
    if not temp_file or not os.path.exists(temp_file):
        flash('Sesión de importación inválida', 'warning')
        return redirect(url_for('admin.datasets'))
    
    preview = DatasetImporter.preview_dataset(temp_file)
    columns = preview.get('columns', [])
    column_choices = [(col, col) for col in columns] or [('', 'No hay columnas disponibles')]
    
    # Selección de formulario según tipo
    form_class = {
        'variedades': MappingVariedadesForm,
        'bloques': MappingBloquesForm
    }.get(dataset_type)
    
    if not form_class:
        flash('Tipo de dataset no soportado', 'danger')
        return redirect(url_for('admin.datasets'))
    
    form = form_class(temp_file_path=temp_file)
    
    # Configurar opciones de columnas
    for field in form:
        if hasattr(field, 'choices'):
            field.choices = column_choices
    
    # Autodetección de columnas
    if request.method == 'GET':
        column_mapping = {
            'variedades': {
                'flor_column': 'FLOR',
                'color_column': 'COLOR',
                'variedad_column': 'VARIEDAD'
            },
            'bloques': {
                'bloque_column': 'BLOQUE',
                'cama_column': 'CAMA',
                'lado_column': 'LADO'
            }
        }
        
        for field, pattern in column_mapping.get(dataset_type, {}).items():
            col = next((c for c in columns if pattern in c.upper()), None)
            if col and hasattr(form, field):
                getattr(form, field).data = col
    
    if form.validate_on_submit():
        # Procesamiento del dataset
        column_mapping = {
            form.bloque_column.data: 'BLOQUE',
            form.cama_column.data: 'CAMA'
        } if dataset_type == 'bloques' else {
            form.flor_column.data: 'FLOR',
            form.color_column.data: 'COLOR',
            form.variedad_column.data: 'VARIEDAD'
        }
        
        if dataset_type == 'bloques' and form.lado_column.data:
            column_mapping[form.lado_column.data] = 'LADO'
        
        success, message, stats = DatasetImporter.process_dataset(
            temp_file,
            dataset_type=dataset_type,
            column_mapping=column_mapping,
            validate_only=form.validate_only.data,
            skip_first_row=form.skip_first_row.data
        )
        
        session['import_stats'] = json.dumps(stats)
        session['import_errors'] = json.dumps(stats.get('error_details', []))
        
        flash(message, 'success' if success else 'danger')
        
        if success and not form.validate_only.data:
            os.remove(temp_file)
            return redirect(url_for(f'admin.{dataset_type}'))
        
        if form.validate_only.data or form.back.data:
            return redirect(url_for('admin.preview_dataset', dataset_type=dataset_type))
    
    return render_template('admin/preview_generic.html',
                         title=f'Previsualizar {dataset_type}',
                         form=form,
                         preview=preview,
                         dataset_type=dataset_type,
                         import_stats=json.loads(session.pop('import_stats', '{}')),
                         import_errors=json.loads(session.pop('import_errors', '[]')))

# Vistas de listados
@bp.route('/variedades', methods=['GET'])
@login_required
def variedades():
    """Listado de variedades"""
    page = request.args.get('page', 1, type=int)
    filters = {
        'flor': request.args.get('flor', ''),
        'color': request.args.get('color', ''),
        'variedad': request.args.get('variedad', '')
    }
    
    query = _get_filtered_query(Variedad, filters, [Variedad.flor_color, FlorColor.flor, FlorColor.color])
    variedades = query.order_by(Variedad.variedad).paginate(page=page, per_page=20)

    flores = Flor.query.order_by(Flor.flor).all()
    colores = Color.query.order_by(Color.color).all()

    flores_opciones = [{'value': f.flor, 'text': f.flor} for f in flores]
    colores_opciones = [{'value': c.color, 'text': c.color} for c in colores]
    
    # Define una función para generar URLs de paginación
    def pagina_url(p):
        return url_for('admin.variedades', page=p, flor=filters['flor'], color=filters['color'], variedad=filters['variedad'])
    
    # También puedes definir las URLs prev y next directamente
    prev_url = url_for('admin.variedades', page=variedades.prev_num, flor=filters['flor'], color=filters['color'], variedad=filters['variedad']) if variedades.has_prev else None
    
    next_url = url_for('admin.variedades', page=variedades.next_num, flor=filters['flor'], color=filters['color'], variedad=filters['variedad']) if variedades.has_next else None
    
    return render_template('admin/variedades.html',
                         title='Gestión de Variedades',
                         flores=flores,
                         colores=colores,
                         variedades=variedades,
                         flor_filter=filters['flor'],
                         color_filter=filters['color'],
                         variedad_filter=filters['variedad'],
                         flores_opciones=flores_opciones,
                         colores_opciones=colores_opciones,
                         pagina_url=pagina_url,  # Pasar la función de URL
                         prev_url=prev_url,      # Pasar URLs prev/next directamente
                         next_url=next_url
                         )


@bp.route('/bloques', methods=['GET'])
@login_required
def bloques():
    """Listado de bloques y camas"""
    page = request.args.get('page', 1, type=int)
    filters = {
        'bloque': request.args.get('bloque', ''),
        'cama': request.args.get('cama', ''),
        'lado': request.args.get('lado', '')
    }
    
    query = _get_filtered_query(BloqueCamaLado, filters, 
                              [BloqueCamaLado.bloque, BloqueCamaLado.cama, BloqueCamaLado.lado])
    bloques_camas = query.order_by(Bloque.bloque, Cama.cama, Lado.lado).paginate(page=page, per_page=20)
    
    # Obtener las listas para los filtros
    bloques_lista = Bloque.query.order_by(Bloque.bloque).all()
    camas_lista = Cama.query.order_by(Cama.cama).all()
    lados_lista = Lado.query.order_by(Lado.lado).all()
    
    # Preparar opciones para los filtros
    bloques_opciones = [{'value': b.bloque, 'text': b.bloque} for b in bloques_lista]
    camas_opciones = [{'value': c.cama, 'text': c.cama} for c in camas_lista]
    lados_opciones = [{'value': l.lado, 'text': l.lado} for l in lados_lista]
    
    # Función para generar URLs de paginación
    def pagina_url(page):
        return url_for('admin.bloques', page=page, 
                     bloque=filters['bloque'], 
                     cama=filters['cama'], 
                     lado=filters['lado'])
    
    return render_template('admin/bloques.html', 
                         title='Gestión de Bloques y Camas',
                         bloques_camas=bloques_camas,
                         bloques=bloques_lista,
                         camas=camas_lista,
                         lados=lados_lista,
                         bloques_opciones=bloques_opciones,
                         camas_opciones=camas_opciones,
                         lados_opciones=lados_opciones,
                         pagina_url=pagina_url,
                         bloque=filters['bloque'],
                         cama=filters['cama'],
                         lado=filters['lado'])

# Vistas de densidades
@bp.route('/densidades', methods=['GET'])
@login_required
def densidades():
    """Gestión de densidades"""
    return render_template('admin/densidades.html',
                         title='Gestión de Densidades',
                         densidades=Densidad.query.order_by(Densidad.densidad).all(),
                         form=DensidadForm())

@bp.route('/densidades/crear', methods=['POST'])
@login_required
def crear_densidad():
    """Crear densidad"""
    if not _check_permission():
        return redirect(url_for('admin.densidades'))
    
    form = DensidadForm()
    if form.validate_on_submit():
        nombre = form.densidad.data.strip()
        if Densidad.query.filter(Densidad.densidad.ilike(nombre)).first():
            flash(f'Ya existe una densidad con el nombre "{nombre}".', 'danger')
            return redirect(url_for('admin.densidades'))
        
        densidad = Densidad(densidad=nombre, valor=form.valor.data)
        db.session.add(densidad)
        
        try:
            db.session.commit()
            flash(f'Densidad "{nombre}" creada exitosamente.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear la densidad: {str(e)}', 'danger')
    
    return redirect(url_for('admin.densidades'))

@bp.route('/densidades/editar', methods=['POST'])
@login_required
def editar_densidad():
    """Editar densidad"""
    if not _check_permission():
        return redirect(url_for('admin.densidades'))
    
    form = DensidadForm()
    densidad_id = request.form.get('densidad_id', type=int)
    
    if form.validate_on_submit() and densidad_id:
        densidad = Densidad.query.get(densidad_id)
        if not densidad:
            flash('Densidad no encontrada.', 'danger')
            return redirect(url_for('admin.densidades'))
        
        nombre = form.densidad.data.strip()
        if Densidad.query.filter(Densidad.densidad.ilike(nombre), Densidad.densidad_id != densidad_id).first():
            flash(f'Ya existe otra densidad con el nombre "{nombre}".', 'danger')
            return redirect(url_for('admin.densidades'))
        
        densidad.densidad = nombre
        densidad.valor = form.valor.data
        
        try:
            db.session.commit()
            flash(f'Densidad "{nombre}" actualizada exitosamente.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar la densidad: {str(e)}', 'danger')
    
    return redirect(url_for('admin.densidades'))

@bp.route('/densidades/eliminar', methods=['POST'])
@login_required
def eliminar_densidad():
    """Eliminar densidad"""
    if not _check_permission():
        return redirect(url_for('admin.densidades'))
    
    densidad_id = request.form.get('densidad_id', type=int)
    if not densidad_id:
        flash('Densidad no especificada.', 'danger')
        return redirect(url_for('admin.densidades'))
    
    densidad = Densidad.query.get(densidad_id)
    if not densidad:
        flash('Densidad no encontrada.', 'danger')
        return redirect(url_for('admin.densidades'))
    
    if Siembra.query.filter_by(densidad_id=densidad_id).count() > 0:
        flash(f'No se puede eliminar la densidad "{densidad.densidad}" porque está en uso.', 'danger')
        return redirect(url_for('admin.densidades'))
    
    try:
        nombre = densidad.densidad
        db.session.delete(densidad)
        db.session.commit()
        flash(f'Densidad "{nombre}" eliminada exitosamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar la densidad: {str(e)}', 'danger')
    
    return redirect(url_for('admin.densidades'))

# Vistas de importación histórica
@bp.route('/importar-historico', methods=['GET', 'POST'])
@login_required
def importar_historico():
    """Importación de datos históricos incluyendo pérdidas"""
    if not _check_permission():
        return redirect(url_for('main.index'))
    
    # Variable para mostrar resultados
    import_results = None
    
    if request.method == 'POST':
        if 'excel_file' not in request.files:
            flash('No se seleccionó ningún archivo', 'danger')
            return redirect(request.url)
        
        file = request.files['excel_file']
        if not file or file.filename == '':
            flash('No se seleccionó ningún archivo', 'danger')
            return redirect(request.url)
        
        if file.filename.endswith(('.xlsx', '.xls')):
            filename = secure_filename(file.filename)
            temp_path = os.path.join(TEMP_DIR, f"{uuid.uuid4()}_{filename}")
            file.save(temp_path)
            
            try:
                # Usar el importador optimizado
                from app.utils import HistoricalImporter
                import_results = HistoricalImporter.importar_historico(temp_path)
                
                if 'error' in import_results:
                    flash(f'Error durante la importación: {import_results["error"]}', 'danger')
                else:
                    # Mostrar un mensaje de éxito detallado
                    success_msg = (
                        f'Datos históricos importados correctamente. '
                        f'Siembras: {import_results.get("siembras_creadas", 0)} creadas, '
                        f'Cortes: {import_results.get("cortes_creados", 0)} creados, '
                        f'Pérdidas: {import_results.get("perdidas_creadas", 0)} creadas'
                    )
                    flash(success_msg, 'success')
            except Exception as e:
                flash(f'Error durante la importación: {str(e)}', 'danger')
            finally:
                # Limpiar archivo temporal
                if os.path.exists(temp_path):
                    os.remove(temp_path)
        else:
            flash('Formato de archivo no permitido. Use archivos Excel (.xlsx, .xls)', 'danger')
    
    return render_template('admin/importar_historico.html', 
                          title='Importar Datos Históricos',
                          import_results=import_results)