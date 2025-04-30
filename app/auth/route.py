from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from app import db
from app.auth import auth_bp
from app.auth.forms import LoginForm, RegisterUserForm, EditUserForm
from app.models import Usuario, Documento
from werkzeug.urls import url_parse

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Maneja el inicio de sesión de usuarios."""
    # Redireccionar si ya está autenticado
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        # Intentar autenticar al usuario
        user = Usuario.query.filter_by(num_doc=form.num_doc.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Número de documento o contraseña incorrectos', 'danger')
            return redirect(url_for('auth.login'))
        
        # Autenticar al usuario
        login_user(user, remember=form.remember_me.data)
        
        # Redireccionar a la página solicitada originalmente o al dashboard
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('main.dashboard')
        
        flash(f'¡Bienvenido(a), {user.nombre_completo}!', 'success')
        return redirect(next_page)
    
    return render_template('auth/login.html', title='Iniciar Sesión', form=form)

@auth_bp.route('/logout')
def logout():
    """Cierra la sesión del usuario actual."""
    logout_user()
    flash('Has cerrado sesión correctamente', 'info')
    return redirect(url_for('main.index'))

@auth_bp.route('/usuarios')
@login_required
def usuarios():
    """Lista todos los usuarios registrados (solo para administradores)."""
    # Verificar si el usuario es administrador
    if not current_user.is_admin:
        flash('No tienes permisos para acceder a esta página', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Obtener lista de usuarios
    users = Usuario.query.all()
    return render_template('auth/usuarios.html', title='Gestión de Usuarios', users=users)

@auth_bp.route('/usuarios/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_usuario():
    """Crea un nuevo usuario (solo para administradores)."""
    # Verificar si el usuario es administrador
    if not current_user.is_admin:
        flash('No tienes permisos para acceder a esta página', 'danger')
        return redirect(url_for('main.dashboard'))
    
    form = RegisterUserForm()
    
    # Cargar opciones de tipos de documento
    form.documento_id.choices = [(d.doc_id, d.documento) for d in Documento.query.all()]
    
    if form.validate_on_submit():
        # Crear nuevo usuario
        user = Usuario(
            nombre_1=form.nombre_1.data,
            nombre_2=form.nombre_2.data,
            apellido_1=form.apellido_1.data,
            apellido_2=form.apellido_2.data,
            cargo=form.cargo.data,
            num_doc=form.num_doc.data,
            documento_id=form.documento_id.data,
            is_admin=form.is_admin.data
        )
        user.set_password(form.password.data)
        
        # Guardar en la base de datos
        db.session.add(user)
        db.session.commit()
        
        flash(f'Usuario {user.nombre_completo} creado exitosamente', 'success')
        return redirect(url_for('auth.usuarios'))
    
    return render_template('auth/editar_usuario.html', title='Nuevo Usuario', form=form)

@auth_bp.route('/usuarios/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_usuario(id):
    """Edita la información de un usuario existente."""
    # Verificar si el usuario es administrador o es el propio usuario
    if not current_user.is_admin and current_user.usuario_id != id:
        flash('No tienes permisos para acceder a esta página', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Obtener el usuario a editar
    user = Usuario.query.get_or_404(id)
    
    form = EditUserForm(original_num_doc=user.num_doc)
    
    # Cargar opciones de tipos de documento
    form.documento_id.choices = [(d.doc_id, d.documento) for d in Documento.query.all()]
    
    if request.method == 'GET':
        # Llenar el formulario con los datos actuales
        form.nombre_1.data = user.nombre_1
        form.nombre_2.data = user.nombre_2
        form.apellido_1.data = user.apellido_1
        form.apellido_2.data = user.apellido_2
        form.cargo.data = user.cargo
        form.documento_id.data = user.documento_id
        form.num_doc.data = user.num_doc
        form.is_admin.data = user.is_admin
    
    if form.validate_on_submit():
        # Actualizar datos del usuario
        user.nombre_1 = form.nombre_1.data
        user.nombre_2 = form.nombre_2.data
        user.apellido_1 = form.apellido_1.data
        user.apellido_2 = form.apellido_2.data
        user.cargo = form.cargo.data
        user.num_doc = form.num_doc.data
        user.documento_id = form.documento_id.data
        
        # Solo cambiar rol si es admin
        if current_user.is_admin:
            user.is_admin = form.is_admin.data
        
        # Cambiar contraseña si se proporciona
        if form.password.data:
            user.set_password(form.password.data)
        
        # Guardar cambios
        db.session.commit()
        
        flash('Información de usuario actualizada', 'success')
        
        # Redireccionar según el rol
        if current_user.is_admin and current_user.usuario_id != id:
            return redirect(url_for('auth.usuarios'))
        else:
            return redirect(url_for('main.dashboard'))
    
    return render_template('auth/editar_usuario.html', title='Editar Usuario', form=form, user=user)

@auth_bp.route('/usuarios/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_usuario(id):
    """Elimina un usuario (solo para administradores)."""
    # Verificar si el usuario es administrador
    if not current_user.is_admin:
        flash('No tienes permisos para acceder a esta página', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # No permitir eliminar al usuario actual
    if current_user.usuario_id == id:
        flash('No puedes eliminar tu propio usuario', 'danger')
        return redirect(url_for('auth.usuarios'))
    
    # Obtener y eliminar usuario
    user = Usuario.query.get_or_404(id)
    nombre = user.nombre_completo
    
    db.session.delete(user)
    db.session.commit()
    
    flash(f'Usuario {nombre} eliminado exitosamente', 'success')
    return redirect(url_for('auth.usuarios'))