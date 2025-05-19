# app/auth/routes.py
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from urllib.parse import urlsplit
from app import db
from app.auth import bp
from app.auth.forms import LoginForm, RegistrationForm
from app.models import Usuario

def _get_redirect_target():
    """Obtiene el objetivo de redirección seguro"""
    next_page = request.args.get('next')
    return next_page if next_page and not urlsplit(next_page).netloc else None

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Maneja el inicio de sesión"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = Usuario.query.filter_by(username=form.username.data).first()
        
        if not user or not user.check_password(form.password.data):
            flash('Usuario o contraseña inválidos', 'danger')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=form.remember_me.data)
        return redirect(_get_redirect_target() or url_for('main.index'))
    
    return render_template('auth/login.html', title='Iniciar Sesión', form=form)

@bp.route('/logout')
def logout():
    """Maneja el cierre de sesión"""
    logout_user()
    return redirect(url_for('main.index'))

@bp.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    """Maneja el registro de nuevos usuarios"""
    form = RegistrationForm()
    
    if form.validate_on_submit():
        user = Usuario(
            username=form.username.data,
            nombre_1=form.nombre_1.data,
            nombre_2=form.nombre_2.data,
            apellido_1=form.apellido_1.data,
            apellido_2=form.apellido_2.data,
            cargo=form.cargo.data,
            num_doc=form.num_doc.data,
            documento_id=form.documento_id.data
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        try:
            db.session.commit()
            flash('Usuario registrado exitosamente', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al registrar usuario: {str(e)}', 'danger')
    
    return render_template('auth/register.html', title='Registro', form=form)