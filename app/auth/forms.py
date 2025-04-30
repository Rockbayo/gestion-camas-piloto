from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError
from app.models import Usuario

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
    cargo = StringField('Cargo', validators=[DataRequired(), Length(max=20)])
    num_doc = StringField('Número de Documento', validators=[DataRequired()])
    documento_id = StringField('Tipo de Documento', validators=[DataRequired()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    password2 = PasswordField('Confirmar Contraseña', 
                              validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Registrar')
    
    def validate_username(self, username):
        user = Usuario.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Por favor, usa un nombre de usuario diferente.')