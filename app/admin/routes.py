from flask import (render_template, flash, redirect, url_for, 
                  request, jsonify, session, current_app)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.admin import bp
from app.admin.forms import ImportDatasetForm, MappingVariedadesForm
from app.utils.dataset_import import DatasetImporter
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

@bp.route('/datasets/importar', methods=['GET', 'POST'])
@login_required
def importar_dataset():
    """Controlador principal para importación de datasets"""
    if not current_user.has_permission('importar_datos'):
        flash('No tienes permisos para esta acción', 'danger')
        return redirect(url_for('main.index'))
    
    form = ImportDatasetForm()
    
    if form.validate_on_submit():
        if not allowed_file(form.excel_file.data.filename):
            flash('Formato de archivo no soportado', 'danger')
            return redirect(url_for('admin.importar_dataset'))
        
        try:
            # Procesamiento seguro del archivo
            file_obj = form.excel_file.data
            filename = secure_filename(file_obj.filename)
            file_id = uuid.uuid4().hex
            temp_path = os.path.join(TEMP_DIR, f"{file_id}_{filename}")
            
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            file_obj.save(temp_path)
            
            # Validación básica del archivo
            try:
                pd.read_excel(temp_path, nrows=1)
            except Exception as e:
                os.remove(temp_path)
                flash(f'Error al leer archivo: {str(e)}', 'danger')
                return redirect(url_for('admin.importar_dataset'))
            
            # Almacenamiento en sesión
            session['import_file'] = {
                'path': temp_path,
                'type': form.dataset_type.data,
                'original_name': filename
            }
            
            # Redirección según tipo
            return redirect(url_for(f'admin.preview_{form.dataset_type.data}'))
            
        except Exception as e:
            current_app.logger.error(f"Error en importación: {str(e)}", exc_info=True)
            flash('Error interno al procesar el archivo', 'danger')
            return redirect(url_for('admin.importar_dataset'))
    
    return render_template('admin/import_dataset.html',
                         title='Importar Dataset',
                         form=form)

# Manejadores de vista previa
@bp.route('/datasets/preview/<dataset_type>', methods=['GET', 'POST'])
@login_required
def preview_dataset(dataset_type):
    """Manejador unificado para previsualización"""
    if not current_user.has_permission('importar_datos'):
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('main.index'))
    
    # Validar datos en sesión
    file_data = session.get('import_file')
    if not file_data or file_data['type'] != dataset_type:
        flash('Sesión de importación inválida', 'warning')
        return redirect(url_for('admin.importar_dataset'))
    
    if not os.path.exists(file_data['path']):
        flash('Archivo no encontrado', 'danger')
        return redirect(url_for('admin.importar_dataset'))
    
    # Cargar datos
    try:
        df = pd.read_excel(file_data['path'])
        form = MappingVariedadesForm()
        
        # Configuración dinámica del formulario
        if request.method == 'GET':
            self._configure_form(form, df.columns, dataset_type)
        
        # Procesamiento del formulario
        if form.validate_on_submit():
            return self._process_import(form, df, file_data['path'], dataset_type)
            
        # Generar vista previa
        preview = self._generate_preview(df, dataset_type)
        
    except Exception as e:
        current_app.logger.error(f"Preview error: {str(e)}", exc_info=True)
        flash('Error al procesar el dataset', 'danger')
        return redirect(url_for('admin.importar_dataset'))
    
    return render_template(f'admin/preview_{dataset_type}.html',
                         title=f'Previsualizar {dataset_type}',
                         form=form,
                         preview=preview)

# Métodos auxiliares (podrían moverse a una clase helper)
def _configure_form(self, form, columns, dataset_type):
    """Configura dinámicamente los campos del formulario"""
    column_choices = [(col, col) for col in columns]
    
    if dataset_type == 'variedades':
        form.flor_column.choices = column_choices
        form.color_column.choices = column_choices
        form.variedad_column.choices = column_choices
        
        # Autodetección de columnas
        for field, pattern in [('flor_column', 'FLOR'), 
                              ('color_column', 'COLOR'),
                              ('variedad_column', 'VARIEDAD')]:
            match = next((c for c in columns if pattern in c.upper()), None)
            if match:
                getattr(form, field).data = match

def _generate_preview(self, df, dataset_type):
    """Genera datos para la vista previa"""
    required_columns = {
        'variedades': ['FLOR', 'COLOR', 'VARIEDAD'],
        'bloques': ['BLOQUE', 'CAMA', 'LADO'],
        'areas': ['AREA', 'SIEMBRA'],
        'densidades': ['DENSIDAD']
    }.get(dataset_type, [])
    
    missing = [col for col in required_columns 
              if col not in [c.upper() for c in df.columns]]
    
    return {
        'data': df.head(10).to_dict('records'),
        'columns': list(df.columns),
        'row_count': len(df),
        'validation': {
            'is_valid': not missing,
            'message': "OK" if not missing else f"Faltan: {', '.join(missing)}"
        }
    }

def _process_import(self, form, df, file_path, dataset_type):
    """Ejecuta la importación/validación"""
    try:
        # Mapeo de columnas
        column_map = {
            'variedades': {
                form.flor_column.data: 'FLOR',
                form.color_column.data: 'COLOR',
                form.variedad_column.data: 'VARIEDAD'
            }
        }.get(dataset_type, {})
        
        # Procesamiento real
        importer = DatasetImporter()
        result = importer.process(
            df=df,
            dataset_type=dataset_type,
            column_map=column_map,
            dry_run=form.validate_only.data
        )
        
        # Limpieza
        if os.path.exists(file_path):
            os.remove(file_path)
        
        if result['success']:
            flash(result['message'], 'success')
            if form.validate_only.data:
                session['preview_stats'] = json.dumps(result.get('stats', {}))
                return redirect(url_for(f'admin.preview_{dataset_type}'))
            return redirect(url_for('admin.datasets'))
        else:
            flash(result['message'], 'danger')
            session['import_errors'] = json.dumps(result.get('errors', []))
            return redirect(url_for(f'admin.preview_{dataset_type}'))
            
    except Exception as e:
        current_app.logger.error(f"Import error: {str(e)}", exc_info=True)
        flash('Error crítico durante la importación', 'danger')
        return redirect(url_for('admin.importar_dataset'))

@bp.route('/datasets', methods=['GET'])
@login_required
def datasets():
    """Vista principal de gestión de datasets"""
    return render_template('admin/datasets.html',
                          title='Gestión de Datasets')

@bp.route('/datasets/importar', methods=['GET', 'POST'])
@login_required
def importar_dataset():
    """Vista para seleccionar el tipo de dataset a importar"""
    from app.admin.forms import ImportDatasetForm
    import os
    import uuid
    
    # Crear directorio temp si no existe
    TEMP_DIR = 'uploads/temp'
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    form = ImportDatasetForm()
    
    if form.validate_on_submit():
        # Guardar archivo temporalmente con un nombre único
        f = form.excel_file.data
        filename = secure_filename(f.filename)
        file_id = str(uuid.uuid4())
        temp_path = os.path.join(TEMP_DIR, f"{file_id}_{filename}")
        
        # Guardar archivo
        f.save(temp_path)
        
        # Guardar información en la sesión
        session['temp_file'] = temp_path
        session['dataset_type'] = form.dataset_type.data
        session['original_filename'] = filename
        
        # Por ahora, simplemente mostrar un mensaje de éxito
        flash(f'Archivo {filename} cargado correctamente. La importación será implementada pronto.', 'success')
        return redirect(url_for('admin.datasets'))
    
    return render_template('admin/importar_dataset.html',
                          title='Importar Dataset',
                          form=form)       