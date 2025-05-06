from flask import render_template, flash, redirect, url_for, request, jsonify, session, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.admin.forms import ImportDatasetForm, MappingVariedadesForm
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

def datasets():
    """Vista principal de gestión de datasets"""
    return render_template('admin/datasets.html',
                          title='Gestión de Datasets')

def importar_dataset():
    """Vista para seleccionar el tipo de dataset a importar"""
    # Crear directorio temp si no existe
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

def preview_dataset(dataset_type):
    """Manejador unificado para previsualización"""
    if not current_user.has_permission('importar_datos'):
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('main.index'))
    
    # Validar datos en sesión
    temp_file = session.get('temp_file')
    if not temp_file or not os.path.exists(temp_file):
        flash('Sesión de importación inválida o archivo no encontrado', 'warning')
        return redirect(url_for('admin.importar_dataset'))
    
    # Cargar datos
    try:
        df = pd.read_excel(temp_file)
        preview = {
            'total_rows': len(df),
            'columns': list(df.columns),
            'preview_data': df.head(10).to_dict(orient='records')
        }
        
        # Verificar columnas requeridas
        required_columns = {
            'variedades': ['FLOR', 'COLOR', 'VARIEDAD'],
            'bloques': ['BLOQUE', 'CAMA'],
            'areas': ['SIEMBRA', 'AREA'],
            'densidades': ['DENSIDAD']
        }.get(dataset_type, [])
        
        missing_columns = [col for col in required_columns if col not in 
                          [c.upper() for c in df.columns]]
        
        preview['validation'] = {
            'is_valid': len(missing_columns) == 0,
            'message': "El dataset es válido para importación." if len(missing_columns) == 0 else 
                      f"Faltan columnas requeridas: {', '.join(missing_columns)}"
        }
        
        form = MappingVariedadesForm()
        form.temp_file_path.data = temp_file
        
        # Configuración del formulario
        if request.method == 'GET':
            columns = preview.get('columns', [])
            
            if dataset_type == 'variedades':
                # Detectar columnas automáticamente
                flor_col = next((col for col in columns if 'FLOR' in col.upper()), '')
                color_col = next((col for col in columns if 'COLOR' in col.upper()), '')
                variedad_col = next((col for col in columns if 'VARIEDAD' in col.upper()), '')
                
                # Configurar opciones en los SelectField
                form.flor_column.choices = [(col, col) for col in columns]
                form.color_column.choices = [(col, col) for col in columns]
                form.variedad_column.choices = [(col, col) for col in columns]
                
                # Preseleccionar columnas detectadas
                if flor_col:
                    form.flor_column.data = flor_col
                if color_col:
                    form.color_column.data = color_col
                if variedad_col:
                    form.variedad_column.data = variedad_col
        
        if form.validate_on_submit():
            # Implementación simple - solo mostrar mensaje
            flash('Función de importación en desarrollo', 'info')
            if os.path.exists(temp_file):
                os.remove(temp_file)
            return redirect(url_for('admin.datasets'))
            
    except Exception as e:
        flash(f'Error al procesar el dataset: {str(e)}', 'danger')
        return redirect(url_for('admin.importar_dataset'))
    
    return render_template('admin/preview_generic.html',
                         title=f'Previsualizar {dataset_type}',
                         form=form,
                         preview=preview,
                         dataset_type=dataset_type,
                         import_stats=json.loads(session.pop('import_stats', '{}')),
                         import_errors=json.loads(session.pop('import_errors', '[]')))