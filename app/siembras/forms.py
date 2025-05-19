from flask_wtf import FlaskForm
from wtforms import SelectField, DateField, SubmitField, IntegerField, FloatField, HiddenField
from wtforms.validators import DataRequired, ValidationError, NumberRange, Optional
from app.models import Bloque, Cama, Lado, Variedad, Densidad, Flor, Color
from sqlalchemy import asc
from datetime import datetime

class BaseSiembraForm(FlaskForm):
    bloque_id = SelectField('Bloque', coerce=int, validators=[DataRequired()])
    cama_id = SelectField('Cama', coerce=int, validators=[DataRequired()])
    lado_id = SelectField('Lado', coerce=int, validators=[DataRequired()])
    flor_id = SelectField('Flor', coerce=int, validators=[Optional()])
    color_id = SelectField('Color', coerce=int, validators=[Optional()])
    variedad_id = SelectField('Variedad', coerce=int, validators=[DataRequired()])
    fecha_siembra = DateField('Fecha de Siembra', format='%Y-%m-%d', validators=[DataRequired()])
    cantidad_plantas = IntegerField('Cantidad de Plantas', validators=[DataRequired(), NumberRange(min=1)])
    densidad_id = SelectField('Densidad', coerce=int, validators=[DataRequired()])
    area_calculada = FloatField('Área Calculada (m²)', validators=[Optional()])
    area_id = HiddenField('Área')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cargar_opciones()
    
    def _cargar_opciones(self):
        self.bloque_id.choices = [(b.bloque_id, b.bloque) for b in Bloque.query.order_by(asc(Bloque.bloque)).all()]
        
        camas = sorted(Cama.query.all(), key=lambda c: str(c.cama) if c.cama.isdigit() else c.cama)
        self.cama_id.choices = [(c.cama_id, c.cama) for c in camas]
        
        self.lado_id.choices = [(l.lado_id, l.lado) for l in Lado.query.order_by(asc(Lado.lado)).all()]
        self.flor_id.choices = [(0, 'Todas las flores')] + [(f.flor_id, f.flor) for f in Flor.query.order_by(Flor.flor).all()]
        self.color_id.choices = [(0, 'Todos los colores')] + [(c.color_id, c.color) for c in Color.query.order_by(Color.color).all()]
        self.variedad_id.choices = [(v.variedad_id, v.variedad) for v in Variedad.query.order_by(Variedad.variedad).all()]
        self.densidad_id.choices = [(d.densidad_id, d.densidad) for d in Densidad.query.order_by(Densidad.densidad).all()]
    
    def validate_fecha_siembra(self, field):
        if field.data > datetime.now().date():
            raise ValidationError('La fecha de siembra no puede ser posterior a hoy')
    
    def validate_cantidad_plantas(self, field):
        if field.data <= 0:
            raise ValidationError('La cantidad de plantas debe ser mayor a cero')

class SiembraForm(BaseSiembraForm):
    submit = SubmitField('Registrar Siembra')

class InicioCorteForm(FlaskForm):
    fecha_inicio_corte = DateField('Fecha de Inicio de Corte', format='%Y-%m-%d', validators=[DataRequired()])
    submit = SubmitField('Registrar Inicio de Corte')
    
    def validate_fecha_inicio_corte(self, field):
        if field.data > datetime.now().date():
            raise ValidationError('La fecha de inicio de corte no puede ser posterior a hoy')