from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DateField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, ValidationError, Optional
from datetime import date
from app.models import Siembra, BloqueCamaLado

class SiembraForm(FlaskForm):
    """Formulario para crear o editar una siembra."""
    bloque_cama_id = SelectField('Ubicación (Bloque-Cama-Lado)', coerce=int, validators=[DataRequired()])
    variedad_id = SelectField('Variedad', coerce=int, validators=[DataRequired()])
    area_id = SelectField('Área', coerce=int, validators=[DataRequired()])
    densidad_id = SelectField('Densidad', coerce=int, validators=[DataRequired()])
    fecha_siembra = DateField('Fecha de Siembra', validators=[DataRequired()], default=date.today)
    submit = SubmitField('Guardar Siembra')
    
    def __init__(self, original_siembra_id=None, *args, **kwargs):
        super(SiembraForm, self).__init__(*args, **kwargs)
        self.original_siembra_id = original_siembra_id
    
    def validate_fecha_siembra(self, fecha_siembra):
        """Validar que la fecha de siembra no sea futura."""
        if fecha_siembra.data > date.today():
            raise ValidationError('La fecha de siembra no puede ser futura.')
    
    def validate_bloque_cama_id(self, bloque_cama_id):
        """Validar que la ubicación no esté ocupada por otra siembra activa."""
        if not self.original_siembra_id:  # Solo para nuevas siembras
            siembra_existente = Siembra.query.filter_by(
                bloque_cama_id=bloque_cama_id.data, 
                estado='Activa'
            ).first()
            
            if siembra_existente:
                ubicacion = str(BloqueCamaLado.query.get(bloque_cama_id.data))
                raise ValidationError(f'La ubicación {ubicacion} ya tiene una siembra activa.')

class FinalizarSiembraForm(FlaskForm):
    """Formulario para finalizar una siembra."""
    observaciones = TextAreaField('Observaciones', validators=[Optional()])
    submit = SubmitField('Finalizar Siembra')

class BusquedaSiembraForm(FlaskForm):
    """Formulario para buscar y filtrar siembras."""
    estado = SelectField('Estado', choices=[
        ('', 'Todos'),
        ('Activa', 'Activa'),
        ('Finalizada', 'Finalizada')
    ], default='')
    bloque_id = SelectField('Bloque', coerce=int)
    variedad_id = SelectField('Variedad', coerce=int)
    submit = SubmitField('Filtrar')
    
    def __init__(self, *args, **kwargs):
        super(BusquedaSiembraForm, self).__init__(*args, **kwargs)
        
        # Estos valores se llenarán dinámicamente en las rutas
        self.bloque_id.choices = [(0, 'Todos los bloques')]
        self.variedad_id.choices = [(0, 'Todas las variedades')]