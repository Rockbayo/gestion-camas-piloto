from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DateField, SelectField, SubmitField, IntegerField, HiddenField
from wtforms.validators import DataRequired, Optional, Length, NumberRange, ValidationError
from datetime import datetime

class CausaPerdidaForm(FlaskForm):
    """Formulario para crear y editar causas de pérdida"""
    nombre = StringField('Nombre', validators=[DataRequired(), Length(max=50)])
    descripcion = TextAreaField('Descripción', validators=[Optional(), Length(max=255)])
    es_predefinida = SelectField('Tipo', choices=[
        ('1', 'Predefinida'),
        ('0', 'Personalizada')
    ], validators=[DataRequired()])
    submit = SubmitField('Guardar')

class PerdidaForm(FlaskForm):
    """Formulario para registrar pérdidas"""
    siembra_id = HiddenField('ID Siembra', validators=[DataRequired()])
    causa_id = SelectField('Causa de Pérdida', coerce=int, validators=[DataRequired()])
    cantidad = IntegerField('Cantidad', validators=[
        DataRequired(), 
        NumberRange(min=1, message="La cantidad debe ser mayor a 0")
    ])
    fecha_perdida = DateField('Fecha de Pérdida', format='%Y-%m-%d', validators=[DataRequired()])
    observaciones = TextAreaField('Observaciones', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Registrar Pérdida')

    def validate_fecha_perdida(self, fecha_perdida):
        # No permitir fechas futuras
        if fecha_perdida.data > datetime.now().date():
            raise ValidationError('La fecha de pérdida no puede ser posterior a hoy')
    
    def validate_cantidad(self, cantidad):
        # Validación adicional para cantidad
        if hasattr(self, 'max_disponible') and self.max_disponible is not None:
            if cantidad.data > self.max_disponible:
                raise ValidationError(f'La cantidad no puede superar el máximo disponible ({self.max_disponible})')