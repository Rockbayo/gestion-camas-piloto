# Formulario para registrar cortes de siembra
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, DateField, SubmitField, HiddenField
from wtforms.validators import DataRequired, NumberRange

class CorteForm(FlaskForm):
    siembra_id = HiddenField('ID Siembra', validators=[DataRequired()])
    num_corte = IntegerField('Número de Corte', validators=[DataRequired(), NumberRange(min=1, message="El número de corte debe ser mayor a 0")])
    fecha_corte = DateField('Fecha de Corte', format='%Y-%m-%d', validators=[DataRequired()])
    cantidad_tallos = IntegerField('Cantidad de Tallos', validators=[DataRequired(), NumberRange(min=1, message="La cantidad debe ser mayor a 0")])
    submit = SubmitField('Registrar Corte')