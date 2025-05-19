# app/auth/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from app.models import Usuario, Documento

class BaseAuthForm(FlaskForm):
    """Formulario base para autenticación con campos comunes"""
    username = StringField('Usuario', validators=[DataRequired(), Length(min=4, max=20)])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    submit = SubmitField('Enviar')

class LoginForm(BaseAuthForm):
    """Formulario de inicio de sesión"""
    remember_me = BooleanField('Recordarme')
    submit = SubmitField('Iniciar Sesión')

class RegistrationForm(BaseAuthForm):
    """Formulario de registro de usuarios"""
    nombre_1 = StringField('Primer Nombre', validators=[DataRequired(), Length(max=20)])
    nombre_2 = StringField('Segundo Nombre', validators=[Length(max=20)])
    apellido_1 = StringField('Primer Apellido', validators=[DataRequired(), Length(max=20)])
    apellido_2 = StringField('Segundo Apellido', validators=[Length(max=20)])
    cargo = StringField('Cargo', validators=[DataRequired(), Length(max=30)])
    num_doc = StringField('Número de Documento', validators=[DataRequired()])
    documento_id = SelectField('Tipo de Documento', coerce=int, validators=[DataRequired()])
    password2 = PasswordField('Confirmar Contraseña', 
                            validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Registrar')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._load_document_types()
    
    def validate_username(self, username):
        """Valida que el nombre de usuario sea único"""
        if Usuario.query.filter_by(username=username.data).first():
            raise ValidationError('Por favor, usa un nombre de usuario diferente.')
    
    def _load_document_types(self):
        """Carga los tipos de documento disponibles"""
        self.documento_id.choices = [(d.doc_id, d.documento) for d in Documento.query.order_by(Documento.documento).all()]