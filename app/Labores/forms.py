from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DateField, SelectField, SubmitField, IntegerField, HiddenField
from wtforms.validators import DataRequired, Optional, Length, NumberRange
from datetime import datetime

class TipoLaborForm(FlaskForm):
    """Formulario para crear y editar tipos de labores culturales"""
    nombre = StringField('Nombre', validators=[DataRequired(), Length(max=50)])
    descripcion = TextAreaField('Descripción', validators=[Optional(), Length(max=255)])
    flor_id = SelectField('Tipo de Flor (opcional)', coerce=int, validators=[Optional()])
    submit = SubmitField('Guardar')

class LaborCulturalForm(FlaskForm):
    """Formulario para registrar labores culturales"""
    siembra_id = HiddenField('ID Siembra', validators=[DataRequired()])
    tipo_labor_id = SelectField('Tipo de Labor', coerce=int, validators=[DataRequired()])
    fecha_labor = DateField('Fecha de Realización', format='%Y-%m-%d', validators=[DataRequired()])
    observaciones = TextAreaField('Observaciones', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Registrar Labor')

    def validate_fecha_labor(self, fecha_labor):
        # No permitir fechas futuras
        if fecha_labor.data > datetime.now().date():
            raise validators.ValidationError('La fecha de labor no puede ser posterior a hoy')