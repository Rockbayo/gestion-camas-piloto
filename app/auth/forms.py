# Formularios para la autenticación de usuarios
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from app.models import Usuario, Documento

class LoginForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    remember_me = BooleanField('Recordarme')
    submit = SubmitField('Iniciar Sesión')

class RegistrationForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired(), Length(min=4, max=20)])
    nombre_1 = StringField('Primer Nombre', validators=[DataRequired(), Length(max=20)])
    nombre_2 = StringField('Segundo Nombre', validators=[Length(max=20)])
    apellido_1 = StringField('Primer Apellido', validators=[DataRequired(), Length(max=20)])
    apellido_2 = StringField('Segundo Apellido', validators=[Length(max=20)])
    cargo = StringField('Cargo', validators=[DataRequired(), Length(max=30)])
    num_doc = StringField('Número de Documento', validators=[DataRequired()])
    documento_id = SelectField('Tipo de Documento', coerce=int, validators=[DataRequired()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    password2 = PasswordField('Confirmar Contraseña', 
                            validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Registrar')
    
    def __init__(self, *args, **kwargs):
        super(RegistrationForm, self).__init__(*args, **kwargs)
        self.documento_id.choices = [(d.doc_id, d.documento) for d in Documento.query.all()]
    
    def validate_username(self, username):
        user = Usuario.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Por favor, usa un nombre de usuario diferente.')