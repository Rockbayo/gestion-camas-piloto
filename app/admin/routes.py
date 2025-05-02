# app/admin/routes.py
from flask import render_template, flash, redirect, url_for, request
from flask_login import login_required, current_user
from app import db
from app.admin import bp
from app.admin.forms import ImportVariedadesForm
from app.utils.import_data import import_variedades_from_excel
from app.models import Variedad, FlorColor, Flor, Color, Usuario, Rol
import os
from werkzeug.utils import secure_filename

@bp.route('/variedades', methods=['GET'])
@login_required
def variedades():
    # Verificar permiso
    if not current_user.has_permission('importar_datos'):
        flash('No tienes permisos para acceder a esta página', 'danger')
        return redirect(url_for('main.index'))
    
    # Obtener variedades actuales
    variedades = Variedad.query.all()
    
    return render_template('admin/variedades.html', 
                          title='Gestión de Variedades',
                          variedades=variedades)

@bp.route('/importar-variedades', methods=['GET', 'POST'])
@login_required
def importar_variedades():
    # Verificar permiso
    if not current_user.has_permission('importar_datos'):
        flash('No tienes permisos para acceder a esta página', 'danger')
        return redirect(url_for('main.index'))
    
    form = ImportVariedadesForm()
    
    if form.validate_on_submit():
        # Guardar archivo temporalmente
        f = form.excel_file.data
        filename = secure_filename(f.filename)
        filepath = os.path.join('uploads', filename)
        
        # Asegurar que exista el directorio
        os.makedirs('uploads', exist_ok=True)
        
        f.save(filepath)
        
        # Procesar archivo
        success, message = import_variedades_from_excel(filepath)
        
        # Eliminar archivo temporal
        os.remove(filepath)
        
        if success:
            flash(message, 'success')
        else:
            flash(message, 'danger')
        
        return redirect(url_for('admin.variedades'))
    
    return render_template('admin/importar_variedades.html',
                          title='Importar Variedades',
                          form=form)

@bp.route('/usuarios', methods=['GET'])
@login_required
def usuarios():
    # Verificar permiso
    if not current_user.has_permission('administrar_usuarios'):
        flash('No tienes permisos para acceder a esta página', 'danger')
        return redirect(url_for('main.index'))
    
    # Obtener usuarios
    usuarios = Usuario.query.all()
    roles = Rol.query.all()
    
    return render_template('admin/usuarios.html',
                          title='Gestión de Usuarios',
                          usuarios=usuarios,
                          roles=roles)

@bp.route('/roles', methods=['GET'])
@login_required
def roles():
    # Verificar permiso
    if not current_user.has_permission('administrar_roles'):
        flash('No tienes permisos para acceder a esta página', 'danger')
        return redirect(url_for('main.index'))
    
    # Obtener roles
    roles = Rol.query.all()
    
    return render_template('admin/roles.html',
                          title='Gestión de Roles',
                          roles=roles)