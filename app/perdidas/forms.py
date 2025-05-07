# Formulario para gestionar las pérdidas
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, DateField, SubmitField, HiddenField, TextAreaField, SelectField
from wtforms.validators import DataRequired, NumberRange, ValidationError
from app.models import Causa, Siembra
from datetime import datetime

# En app/perdidas/forms.py
class PerdidaForm(FlaskForm):
    siembra_id = HiddenField('ID Siembra', validators=[DataRequired()])
    causa_id = SelectField('Causa de Pérdida', coerce=int, validators=[DataRequired()])
    # Eliminamos el campo fecha_perdida
    cantidad = IntegerField('Cantidad', validators=[DataRequired(), NumberRange(min=1, message="La cantidad debe ser mayor a 0")])
    observaciones = TextAreaField('Observaciones')
    submit = SubmitField('Registrar Pérdida')
    
    def __init__(self, *args, **kwargs):
        super(PerdidaForm, self).__init__(*args, **kwargs)
        self.causa_id.choices = [(c.causa_id, c.causa) for c in Causa.query.order_by(Causa.causa).all()]
    
    def validate_fecha_perdida(self, fecha_perdida):
        if fecha_perdida.data > datetime.now().date():
            raise ValidationError('La fecha de pérdida no puede ser posterior a hoy')
        
        # Verificar que la fecha de pérdida no sea anterior a la fecha de siembra
        if self.siembra_id.data:
            siembra = Siembra.query.get(self.siembra_id.data)
            if siembra and fecha_perdida.data < siembra.fecha_siembra:
                raise ValidationError('La fecha de pérdida no puede ser anterior a la fecha de siembra')