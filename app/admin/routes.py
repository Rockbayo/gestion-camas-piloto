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
    Densidad, Siembra, Corte, Area, Usuario
)
from app.utils.optimizado import DatasetImporter
import os
import pandas as pd
import uuid
import json
from flask_wtf import CSRFProtect

# Configuración de directorios
TEMP_DIR = os.path.join('uploads', 'temp')
os.makedirs(TEMP_DIR, exist_ok=True)

def allowed_file(filename):
    """Verifica extensiones permitidas"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'xlsx', 'xls', 'csv'}

# Vista principal de gestión de datasets
@bp.route('/datasets', methods=['GET', 'POST'])
@login_required
def datasets():
    """Vista principal para gestión de datasets"""
    # Limpiar sesión de importaciones anteriores
    if 'temp_file' in session:
        temp_file = session.pop('temp_file')
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass
    
    form = ImportDatasetForm()
    
    if form.validate_on_submit():
        # Guardar archivo temporalmente
        temp_path = DatasetImporter.save_temp_file(form.excel_file.data)
        
        # Guardar información en la sesión
        session['temp_file'] = temp_path
        session['dataset_type'] = form.dataset_type.data
        session['original_filename'] = secure_filename(form.excel_file.data.filename)
        
        # Redirigir a la vista de previsualización
        flash(f'Archivo cargado correctamente.', 'success')
        return redirect(url_for('admin.preview_dataset', dataset_type=form.dataset_type.data))
    
    return render_template('admin/datasets.html',
                          title='Gestión de Datasets',
                          form=form)

@bp.route('/importar_dataset', methods=['GET', 'POST'])
@login_required
def importar_dataset():
    """Vista para seleccionar el tipo de dataset a importar"""
    # Crear directorio temp si no existe
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    form = ImportDatasetForm()
    
    if form.validate_on_submit():
        # Guardar archivo temporalmente con un nombre único
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

# Manejador unificado para previsualización
@bp.route('/datasets/preview/<dataset_type>', methods=['GET', 'POST'])
@login_required
def preview_dataset(dataset_type):
    # Verificar permisos
    if not current_user.has_permission('importar_datos'):
        flash('No tienes permiso para importar datos', 'danger')
        print(f"Usuario {current_user.username} intentó importar datos sin permiso")
        return redirect(url_for('main.index'))
    
    # Validar datos en sesión
    temp_file = session.get('temp_file')
    if not temp_file or not os.path.exists(temp_file):
        flash('Sesión de importación inválida o archivo no encontrado', 'warning')
        return redirect(url_for('admin.importar_dataset'))
    
    # Obtener vista previa usando la utilidad unificada
    preview = DatasetImporter.preview_dataset(temp_file)
    columns = preview.get('columns', [])
    
    # Crear el formulario apropiado según el tipo de dataset
    if dataset_type == 'variedades':
        form = MappingVariedadesForm()
    elif dataset_type == 'bloques':
        form = MappingBloquesForm()
    else:
        flash(f'Tipo de dataset no soportado: {dataset_type}', 'danger')
        return redirect(url_for('admin.datasets'))
    
    form.temp_file_path.data = temp_file
    
    # Siempre configurar las opciones de los campos de selección
    column_choices = [(col, col) for col in columns] or [('', 'No hay columnas disponibles')]
    
    # Configurar campos específicos según el tipo de dataset
    if dataset_type == 'variedades':
        form.flor_column.choices = column_choices
        form.color_column.choices = column_choices
        form.variedad_column.choices = column_choices
        
        # Autodetectar columnas
        if request.method == 'GET':
            flor_col = next((col for col in columns if 'FLOR' in col.upper()), None)
            color_col = next((col for col in columns if 'COLOR' in col.upper()), None)
            variedad_col = next((col for col in columns if 'VARIEDAD' in col.upper()), None)
            
            if flor_col:
                form.flor_column.data = flor_col
            if color_col:
                form.color_column.data = color_col
            if variedad_col:
                form.variedad_column.data = variedad_col
    
    elif dataset_type == 'bloques':
        form.bloque_column.choices = column_choices
        form.cama_column.choices = column_choices
        form.lado_column.choices = column_choices
        
        # Autodetectar columnas
        if request.method == 'GET':
            bloque_col = next((col for col in columns if 'BLOQUE' in col.upper()), None)
            cama_col = next((col for col in columns if 'CAMA' in col.upper()), None)
            lado_col = next((col for col in columns if 'LADO' in col.upper()), None)
            
            if bloque_col:
                form.bloque_column.data = bloque_col
            if cama_col:
                form.cama_column.data = cama_col
            if lado_col:
                form.lado_column.data = lado_col
    
    if form.validate_on_submit():
        # Preparar mapeo de columnas
        column_mapping = {}
        
        if dataset_type == 'variedades':
            column_mapping = {
                form.flor_column.data: 'FLOR',
                form.color_column.data: 'COLOR',
                form.variedad_column.data: 'VARIEDAD'
            }
        elif dataset_type == 'bloques':
            column_mapping = {
                form.bloque_column.data: 'BLOQUE',
                form.cama_column.data: 'CAMA'
            }
            # Agregar lado solo si se seleccionó una columna
            if form.lado_column.data:
                column_mapping[form.lado_column.data] = 'LADO'
        
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
            return redirect(url_for('admin.variedades' if dataset_type == 'variedades' else 'admin.bloques'))
            
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


@bp.route('/bloques', methods=['GET'])
@login_required
def bloques():
    """Vista para mostrar listado de bloques, camas y lados importados"""
    page = request.args.get('page', 1, type=int)
    bloque_filter = request.args.get('bloque', '')
    cama_filter = request.args.get('cama', '')
    lado_filter = request.args.get('lado', '')
    
    # Consulta de bloques_camas_lado con posibles filtros
    query = BloqueCamaLado.query
    
    if bloque_filter:
        query = query.join(BloqueCamaLado.bloque).filter(Bloque.bloque.ilike(f'%{bloque_filter}%'))
    if cama_filter:
        query = query.join(BloqueCamaLado.cama).filter(Cama.cama.ilike(f'%{cama_filter}%'))
    if lado_filter:
        query = query.join(BloqueCamaLado.lado).filter(Lado.lado.ilike(f'%{lado_filter}%'))
    
    # Ordenar resultados primero por bloque, luego por cama, finalmente por lado
    query = query.join(BloqueCamaLado.bloque).join(BloqueCamaLado.cama).join(BloqueCamaLado.lado)
    query = query.order_by(Bloque.bloque, Cama.cama, Lado.lado)
    
    # Paginar resultados
    bloques_camas = query.paginate(page=page, per_page=20)
    
    # Obtener listas para los filtros desplegables
    bloques = Bloque.query.order_by(Bloque.bloque).all()
    camas = Cama.query.order_by(Cama.cama).all()
    lados = Lado.query.order_by(Lado.lado).all()
    
    return render_template('admin/bloques.html', 
                          title='Gestión de Bloques y Camas',
                          bloques_camas=bloques_camas,
                          bloques=bloques,
                          camas=camas,
                          lados=lados,
                          bloque_filter=bloque_filter,
                          cama_filter=cama_filter,
                          lado_filter=lado_filter)

# Añadir al archivo app/admin/routes.py

@bp.route('/densidades', methods=['GET'])
@login_required
def densidades():
    """Vista para administrar densidades"""
    densidades = Densidad.query.order_by(Densidad.densidad).all()
    form = DensidadForm()  # Inicializa el formulario
    return render_template('admin/densidades.html',
                           title='Gestión de Densidades',
                           densidades=densidades,
                           form=form)  # Asegúrate de pasar 'form' aquí

@bp.route('/densidades/crear', methods=['POST'])
@login_required
def crear_densidad():
    """Ruta para crear una nueva densidad"""
    if not current_user.has_permission('importar_datos'):
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('admin.densidades'))

    form = DensidadForm()
    if form.validate_on_submit():
        nombre = form.densidad.data.strip()
        valor = form.valor.data

        # Verificar si ya existe una densidad con el mismo nombre
        if Densidad.query.filter(Densidad.densidad.ilike(nombre)).first():
            flash(f'Ya existe una densidad con el nombre "{nombre}".', 'danger')
            return redirect(url_for('admin.densidades'))

        # Crear la densidad
        densidad = Densidad(densidad=nombre, valor=valor)
        db.session.add(densidad)

        try:
            db.session.commit()
            flash(f'Densidad "{nombre}" creada exitosamente.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear la densidad: {str(e)}', 'danger')
        return redirect(url_for('admin.densidades'))
    else:
        flash('Error en el formulario. Por favor, revise los campos.', 'danger')
        return redirect(url_for('admin.densidades'))

@bp.route('/densidades/editar', methods=['POST'])
@login_required
def editar_densidad():
    """Ruta para editar una densidad existente"""
    if not current_user.has_permission('importar_datos'):
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('admin.densidades'))

    form = DensidadForm()
    if form.validate_on_submit():
        densidad_id = request.form.get('densidad_id', type=int)
        nombre = form.densidad.data.strip()
        valor = form.valor.data

        if not densidad_id:
            flash('Densidad no especificada.', 'danger')
            return redirect(url_for('admin.densidades'))

        # Buscar la densidad
        densidad = Densidad.query.get(densidad_id)
        if not densidad:
            flash('Densidad no encontrada.', 'danger')
            return redirect(url_for('admin.densidades'))

        # Verificar si el nuevo nombre ya está en uso por otra densidad
        densidad_existente = Densidad.query.filter(
            Densidad.densidad.ilike(nombre),
            Densidad.densidad_id != densidad_id
        ).first()

        if densidad_existente:
            flash(f'Ya existe otra densidad con el nombre "{nombre}".', 'danger')
            return redirect(url_for('admin.densidades'))

        # Actualizar la densidad
        densidad.densidad = nombre
        densidad.valor = valor
        try:
            db.session.commit()
            flash(f'Densidad "{nombre}" actualizada exitosamente.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar la densidad: {str(e)}', 'danger')
        return redirect(url_for('admin.densidades'))
    else:
        flash('Error en el formulario. Por favor, revise los campos.', 'danger')
        return redirect(url_for('admin.densidades'))
    

@bp.route('/densidades/eliminar', methods=['POST'])
@login_required
def eliminar_densidad():
    """Ruta para eliminar una densidad existente"""
    if not current_user.has_permission('importar_datos'):
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('admin.densidades'))

    densidad_id = request.form.get('densidad_id', type=int)
    if not densidad_id:
        flash('Densidad no especificada.', 'danger')
        return redirect(url_for('admin.densidades'))

    # Buscar la densidad
    densidad = Densidad.query.get(densidad_id)
    if not densidad:
        flash('Densidad no encontrada.', 'danger')
        return redirect(url_for('admin.densidades'))

    # Verificar si hay siembras que usan esta densidad
    siembras_asociadas = Siembra.query.filter_by(densidad_id=densidad_id).count()
    if siembras_asociadas > 0:
        flash(f'No se puede eliminar la densidad "{densidad.densidad}" porque está siendo utilizada en {siembras_asociadas} siembras.', 'danger')
        return redirect(url_for('admin.densidades'))

    try:
        nombre = densidad.densidad  # Guardar el nombre para usarlo en el mensaje
        db.session.delete(densidad)
        db.session.commit()
        flash(f'Densidad "{nombre}" eliminada exitosamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar la densidad: {str(e)}', 'danger')
    
    return redirect(url_for('admin.densidades'))

@bp.route('/importar-historico', methods=['GET', 'POST'])
@login_required
def importar_historico():
    """Vista para importar datos históricos desde un archivo Excel"""
    # Verificar permisos
    if not current_user.has_permission('importar_datos'):
        flash('No tienes permiso para importar datos', 'danger')
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        # Verificar si se subió un archivo
        if 'excel_file' not in request.files:
            flash('No se seleccionó ningún archivo', 'danger')
            return redirect(request.url)
        
        file = request.files['excel_file']
        if file.filename == '':
            flash('No se seleccionó ningún archivo', 'danger')
            return redirect(request.url)
        
        if file and file.filename.endswith(('.xlsx', '.xls')):
            # Guardar el archivo temporalmente
            filename = secure_filename(file.filename)
            temp_path = os.path.join(TEMP_DIR, f"{uuid.uuid4()}_{filename}")
            file.save(temp_path)
            
            try:
                # Importar datos históricos usando la utilidad
                from app.utils.optimizado import importar_historico
                importar_historico(temp_path)
                
                flash('Datos históricos importados correctamente', 'success')
                return redirect(url_for('admin.datasets'))
                
            except Exception as e:
                flash(f'Error durante la importación: {str(e)}', 'danger')
                return redirect(request.url)
            finally:
                # Eliminar archivo temporal
                if os.path.exists(temp_path):
                    os.remove(temp_path)
        else:
            flash('Formato de archivo no permitido. Use Excel (.xlsx, .xls)', 'danger')
            return redirect(request.url)
    
    return render_template('admin/importar_historico.html', title='Importar Datos Históricos')

@bp.route('/reimportar_historico', methods=['GET'])
@login_required
def reimportar_historico():
    """Elimina los datos históricos actuales y fuerza una nueva importación"""
    # Verificar permisos
    if not current_user.has_permission('importar_datos'):
        flash('No tienes permiso para importar datos', 'danger')
        return redirect(url_for('main.index'))
    
    # Eliminar datos existentes (opcional)
    # Esta es una operación peligrosa - podría eliminar también datos no históricos
    # Por lo que necesitarías implementar una lógica para identificar solo datos históricos
    
    # Redirigir a la página de importación
    flash('Por favor, seleccione el archivo histórico para reimportar', 'warning')
    return redirect(url_for('admin.importar_historico'))

def generar_grafico_curva_mejorado(puntos_curva, variedad_info, ciclo_vegetativo_promedio, ciclo_total_promedio):
    """
    Genera un gráfico mejorado para la curva de producción con interpolación y suavizado.
    """
    import matplotlib.pyplot as plt
    import numpy as np
    from scipy.interpolate import make_interp_spline, splrep, splev
    from io import BytesIO
    import base64
    
    # 1. PREPROCESAMIENTO DE DATOS
    # Verifica que haya suficientes datos
    if not puntos_curva or len(puntos_curva) < 3:
        # Crear un gráfico con mensaje de error si no hay suficientes datos
        plt.figure(figsize=(10, 6))
        plt.text(0.5, 0.5, "Datos insuficientes para generar curva", 
                ha='center', va='center', fontsize=14)
        plt.tight_layout()
        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        grafico_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        plt.close()
        return grafico_base64
    
    # Extraer datos y ordenarlos
    dias = []
    indices = []
    
    for punto in sorted(puntos_curva, key=lambda p: p['dia']):
        dias.append(punto['dia'])
        indices.append(punto['indice_promedio'])
    
    # 2. AÑADIR PUNTOS SINTÉTICOS para mejorar la curva
    # Punto inicial (siembra, día 0)
    if min(dias) > 0:
        dias.insert(0, 0)
        indices.insert(0, 0)
    
    # Punto para el ciclo vegetativo (si no hay datos cercanos)
    if ciclo_vegetativo_promedio > 0:
        # Verificar si ya hay un punto cercano
        tiene_punto_cercano = any(abs(d - ciclo_vegetativo_promedio) < 5 for d in dias)
        if not tiene_punto_cercano:
            # Calcular un valor razonable para el inicio de producción (5-10% del promedio)
            promedio_indices = sum(indices) / len(indices) if indices else 0
            valor_inicio = max(0.5, promedio_indices * 0.08)  # 8% del promedio o 0.5 mínimo
            
            # Encontrar dónde insertar
            pos = 0
            while pos < len(dias) and dias[pos] < ciclo_vegetativo_promedio:
                pos += 1
            
            dias.insert(pos, ciclo_vegetativo_promedio)
            indices.insert(pos, valor_inicio)
    
    # Reordenar datos después de añadir puntos
    puntos_ordenados = sorted(zip(dias, indices))
    dias = [p[0] for p in puntos_ordenados]
    indices = [p[1] for p in puntos_ordenados]
    
    # 3. CREAR FIGURA
    plt.figure(figsize=(10, 6))
    
    # Gráfico de dispersión (puntos reales)
    plt.scatter(dias, indices, color='blue', s=50, alpha=0.7, label='Datos históricos')
    
    # 4. GENERAR CURVA SUAVIZADA
    # Solo intentar curva suavizada si hay suficientes puntos
    if len(dias) >= 4:
        try:
            # Crear una malla más densa para el suavizado
            dias_suavizados = np.linspace(0, ciclo_total_promedio, 100)
            
            # Usar splines con suavizado controlado
            # El parámetro s controla el suavizado (mayor s = más suavizado)
            tck = splrep(dias, indices, s=len(dias)/2)
            indices_suavizados = splev(dias_suavizados, tck)
            
            # Asegurarse de que los valores tengan sentido (no negativos, sin picos extremos)
            indices_suavizados = np.maximum(indices_suavizados, 0)  # No valores negativos
            
            # Limitar picos extremos
            max_indice = max(indices) * 1.2  # Permitir hasta 20% más que el máximo observado
            indices_suavizados = np.minimum(indices_suavizados, max_indice)
            
            # Curva suavizada
            plt.plot(dias_suavizados, indices_suavizados, 'r--', 
                    linewidth=2, label='Tendencia (suavizado natural)')
        except Exception as e:
            print(f"Error al generar curva suavizada: {e}")
            # Si falla el suavizado, conectar los puntos con líneas simples
            plt.plot(dias, indices, 'r--', linewidth=1.5, 
                   label='Tendencia (interpolación lineal)')
    
    # 5. CONFIGURACIÓN DEL GRÁFICO
    plt.xlabel('Días desde siembra')
    plt.ylabel('Índice promedio (%)')
    plt.title(f'Curva de producción: {variedad_info}')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # Establecer límites eje Y
    max_value = max(indices) if indices else 20
    plt.ylim(0, min(50, max_value * 1.2))  # Limitar a 50% o 1.2 veces el máximo
    
    # Establecer límites eje X - todo el ciclo
    plt.xlim(0, ciclo_total_promedio)
    
    # 6. AÑADIR LÍNEAS VERTICALES para mostrar los ciclos
    if ciclo_vegetativo_promedio > 0:
        plt.axvline(x=ciclo_vegetativo_promedio, color='g', linestyle='--', alpha=0.7,
                   label=f'Fin ciclo vegetativo ({ciclo_vegetativo_promedio} días)')
    
    if ciclo_total_promedio > 0:
        plt.axvline(x=ciclo_total_promedio, color='r', linestyle='--', alpha=0.7,
                   label=f'Fin ciclo total ({ciclo_total_promedio} días)')
    
    # 7. AÑADIR ANOTACIONES
    for dia, indice in zip(dias, indices):
        plt.annotate(f'{indice:.2f}%', (dia, indice), 
                    textcoords="offset points", xytext=(0,10), ha='center')
    
    # 8. AÑADIR NOTA EXPLICATIVA
    plt.figtext(0.5, 0.01, 
               "Nota: La línea punteada roja representa la tendencia de producción ajustada.", 
               ha='center', fontsize=9)
    
    # 9. GUARDAR GRÁFICO
    plt.tight_layout(rect=[0, 0.03, 1, 0.97])  # Dejar espacio para la nota
    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=100)
    buffer.seek(0)
    grafico_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close()
    
    return grafico_base64