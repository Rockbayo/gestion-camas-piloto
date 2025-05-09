# Formulario para registrar cortes de siembra
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, DateField, SubmitField, HiddenField
from wtforms.validators import DataRequired, NumberRange
from datetime import datetime
from wtforms import validators


class CorteForm(FlaskForm):
    siembra_id = HiddenField('ID Siembra', validators=[DataRequired()])
    num_corte = IntegerField('Número de Corte', validators=[DataRequired(), NumberRange(min=1, message="El número de corte debe ser mayor a 0")])
    fecha_corte = DateField('Fecha de Corte', format='%Y-%m-%d', validators=[DataRequired()])
    cantidad_tallos = IntegerField('Cantidad de Tallos', validators=[DataRequired(), NumberRange(min=1, message="La cantidad debe ser mayor a 0")])
    submit = SubmitField('Registrar Corte')

    def validate_fecha_corte(self, fecha_corte):
        # No permitir fechas futuras
        if fecha_corte.data > datetime.now().date():
            raise validators.ValidationError('La fecha de corte no puede ser posterior a hoy')