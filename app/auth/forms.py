from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, ValidationError
from app.models import Usuario

class LoginForm(FlaskForm):
    """Formulario de inicio de sesión."""
    num_doc = StringField('Número de Documento', validators=[DataRequired()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    remember_me = BooleanField('Recordarme')
    submit = SubmitField('Iniciar Sesión')

class RegisterUserForm(FlaskForm):
    """Formulario para registrar un nuevo usuario."""
    nombre_1 = StringField('Primer Nombre', validators=[DataRequired(), Length(max=20)])
    nombre_2 = StringField('Segundo Nombre', validators=[Optional(), Length(max=20)])
    apellido_1 = StringField('Primer Apellido', validators=[DataRequired(), Length(max=20)])
    apellido_2 = StringField('Segundo Apellido', validators=[Optional(), Length(max=20)])
    cargo = StringField('Cargo', validators=[DataRequired(), Length(max=20)])
    documento_id = SelectField('Tipo de Documento', coerce=int, validators=[DataRequired()])
    num_doc = StringField('Número de Documento', validators=[DataRequired()])
    password = PasswordField('Contraseña', validators=[
        DataRequired(),
        Length(min=6, message='La contraseña debe tener al menos 6 caracteres')
    ])
    confirm_password = PasswordField('Confirmar Contraseña', validators=[
        DataRequired(),
        EqualTo('password', message='Las contraseñas deben coincidir')
    ])
    is_admin = BooleanField('¿Es Administrador?')
    submit = SubmitField('Registrar Usuario')
    
    def validate_num_doc(self, num_doc):
        """Validar que el número de documento no esté ya registrado."""
        user = Usuario.query.filter_by(num_doc=num_doc.data).first()
        if user:
            raise ValidationError('Este número de documento ya está registrado.')

class EditUserForm(FlaskForm):
    """Formulario para editar información de usuario."""
    nombre_1 = StringField('Primer Nombre', validators=[DataRequired(), Length(max=20)])
    nombre_2 = StringField('Segundo Nombre', validators=[Optional(), Length(max=20)])
    apellido_1 = StringField('Primer Apellido', validators=[DataRequired(), Length(max=20)])
    apellido_2 = StringField('Segundo Apellido', validators=[Optional(), Length(max=20)])
    cargo = StringField('Cargo', validators=[DataRequired(), Length(max=20)])
    documento_id = SelectField('Tipo de Documento', coerce=int, validators=[DataRequired()])
    num_doc = StringField('Número de Documento', validators=[DataRequired()])
    password = PasswordField('Contraseña (dejar en blanco para no cambiar)', validators=[Optional(), Length(min=6)])
    confirm_password = PasswordField('Confirmar Contraseña', validators=[
        EqualTo('password', message='Las contraseñas deben coincidir')
    ])
    is_admin = BooleanField('¿Es Administrador?')
    submit = SubmitField('Guardar Cambios')
    
    def __init__(self, original_num_doc=None, *args, **kwargs):
        super(EditUserForm, self).__init__(*args, **kwargs)
        self.original_num_doc = original_num_doc
        
    def validate_num_doc(self, num_doc):
        """Validar que el número de documento no esté ya registrado por otro usuario."""
        if self.original_num_doc != num_doc.data:
            user = Usuario.query.filter_by(num_doc=num_doc.data).first()
            if user:
                raise ValidationError('Este número de documento ya está registrado.')