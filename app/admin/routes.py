from flask import render_template, flash, redirect, url_for, request, jsonify, session, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.admin import bp
from app.admin.forms import ImportDatasetForm, MappingVariedadesForm
from app.models import Variedad, FlorColor, Flor, Color
from app.utils.dataset_importer import DatasetImporter
import os
import pandas as pd
import uuid
import json

# Configuración de directorios
TEMP_DIR = os.path.join('uploads', 'temp')
os.makedirs(TEMP_DIR, exist_ok=True)

def allowed_file(filename):
    """Verifica extensiones permitidas"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'xlsx', 'xls', 'csv'}

# Vista principal de gestión de datasets
@bp.route('/datasets', methods=['GET'])
@login_required
def datasets():
    return render_template('admin/datasets.html',
                          title='Gestión de Datasets')

# Vista para seleccionar el tipo de dataset a importar
@bp.route('/datasets/importar', methods=['GET', 'POST'])
@login_required
def importar_dataset():
    # Crear directorio temp si no existe
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    form = ImportDatasetForm()
    
    if form.validate_on_submit():
        # Guardar archivo temporalmente con un nombre único usando la nueva utilidad
        temp_path = DatasetImporter.save_temp_file(form.excel_file.data)
        
        # Guardar información en la sesión
        session['temp_file'] = temp_path
        session['dataset_type'] = form.dataset_type.data
        
        # Obtener el nombre del archivo original
        original_filename = secure_filename(form.excel_file.data.filename)
        session['original_filename'] = original_filename
        
        # Redirigir a la vista de previsualización
        flash(f'Archivo {original_filename} cargado correctamente.', 'success')
        return redirect(url_for('admin.preview_dataset', dataset_type=form.dataset_type.data))
    
    return render_template('admin/importar_dataset.html',
                          title='Importar Dataset',
                          form=form)

@bp.route('/importar_variedades', methods=['GET', 'POST'])
@login_required
def importar_variedades():
    # Puedes redirigir a la vista genérica de importación con el tipo predefinido
    return redirect(url_for('admin.importar_dataset', dataset_type='variedades'))

# Manejador unificado para previsualización
@bp.route('/datasets/preview/<dataset_type>', methods=['GET', 'POST'])
@login_required
def preview_dataset(dataset_type):
    if not current_user.has_permission('importar_datos'):
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('main.index'))
    
    # Validar datos en sesión
    temp_file = session.get('temp_file')
    if not temp_file or not os.path.exists(temp_file):
        flash('Sesión de importación inválida o archivo no encontrado', 'warning')
        return redirect(url_for('admin.importar_dataset'))
    
    # Obtener vista previa usando la utilidad unificada
    preview = DatasetImporter.preview_dataset(temp_file)
    columns = preview.get('columns', [])
    
    # Crear el formulario y configurarlo con las columnas disponibles
    form = MappingVariedadesForm()
    form.temp_file_path.data = temp_file
    
    # Siempre configurar las opciones de los campos de selección
    # para evitar el error "Choices cannot be None"
    form.flor_column.choices = [(col, col) for col in columns] or [('', 'No hay columnas disponibles')]
    form.color_column.choices = [(col, col) for col in columns] or [('', 'No hay columnas disponibles')]
    form.variedad_column.choices = [(col, col) for col in columns] or [('', 'No hay columnas disponibles')]
    
    # Configuración adicional del formulario para el método GET
    if request.method == 'GET':
        if dataset_type == 'variedades':
            # Detectar columnas automáticamente
            flor_col = next((col for col in columns if 'FLOR' in col.upper()), None)
            color_col = next((col for col in columns if 'COLOR' in col.upper()), None)
            variedad_col = next((col for col in columns if 'VARIEDAD' in col.upper()), None)
            
            # Preseleccionar columnas detectadas
            if flor_col:
                form.flor_column.data = flor_col
            if color_col:
                form.color_column.data = color_col
            if variedad_col:
                form.variedad_column.data = variedad_col
    
    if form.validate_on_submit():
        # Preparar mapeo de columnas
        column_mapping = {}
        if dataset_type == 'variedades':
            column_mapping = {
                form.flor_column.data: 'FLOR',
                form.color_column.data: 'COLOR',
                form.variedad_column.data: 'VARIEDAD'
            }
        
        # Realizar la importación o validación
        success, message, stats = DatasetImporter.process_dataset(
            temp_file,
            dataset_type=dataset_type,
            column_mapping=column_mapping,
            validate_only=form.validate_only.data,
            skip_first_row=form.skip_first_row.data
        )
        
        # Guardar estadísticas en la sesión para mostrarlas
        session['import_stats'] = json.dumps(stats)
        
        # Guardar errores en la sesión si los hay
        error_details = stats.get('error_details', [])
        session['import_errors'] = json.dumps(error_details)
        
        # Mostrar mensaje al usuario
        flash_type = 'success' if success else 'danger'
        flash(message, flash_type)
        
        # Si fue solo validación, redirigir de nuevo a la vista de previsualización
        if form.validate_only.data:
            return redirect(url_for('admin.preview_dataset', dataset_type=dataset_type))
        
        # Si fue importación exitosa, eliminar archivo temporal y redirigir
        if success and not form.validate_only.data:
            if os.path.exists(temp_file):
                os.remove(temp_file)
            return redirect(url_for('admin.datasets'))
            
        # Si el formulario se envía pero hay un error en la validación
        if hasattr(form, 'back') and form.back.data:
            return redirect(url_for('admin.importar_dataset'))
    
    # Importar estadísticas e información de errores desde la sesión
    import_stats = json.loads(session.pop('import_stats', '{}'))
    import_errors = json.loads(session.pop('import_errors', '[]'))
    
    return render_template('admin/preview_generic.html',
                         title=f'Previsualizar {dataset_type}',
                         form=form,
                         preview=preview,
                         dataset_type=dataset_type,
                         import_stats=import_stats,
                         import_errors=import_errors)

@bp.route('/variedades', methods=['GET'])
@login_required
def variedades():
    # Puedes adaptar aquí la lógica del otro método que ya tienes
    # basado en lo que veo en el código proporcionado
    page = request.args.get('page', 1, type=int)
    flor_filter = request.args.get('flor', '')
    color_filter = request.args.get('color', '')
    variedad_filter = request.args.get('variedad', '')
    
    # Consulta de variedades con posibles filtros
    query = Variedad.query
    
    if flor_filter:
        query = query.join(Variedad.flor_color).join(FlorColor.flor).filter(Flor.flor.ilike(f'%{flor_filter}%'))
    if color_filter:
        query = query.join(Variedad.flor_color).join(FlorColor.color).filter(Color.color.ilike(f'%{color_filter}%'))
    if variedad_filter:
        query = query.filter(Variedad.variedad.ilike(f'%{variedad_filter}%'))
    
    variedades = query.order_by(Variedad.variedad).paginate(
        page=page, per_page=20)
    
    # Obtener listas para los filtros desplegables
    flores = Flor.query.order_by(Flor.flor).all()
    colores = Color.query.order_by(Color.color).all()
    
    return render_template('admin/variedades.html', 
                          title='Gestión de Variedades',
                          variedades=variedades,
                          flores=flores,
                          colores=colores,
                          flor_filter=flor_filter,
                          color_filter=color_filter,
                          variedad_filter=variedad_filter)