# Formulario para la gestión de siembras|
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DateField, SubmitField
from wtforms.validators import DataRequired, ValidationError
from app.models import Bloque, Cama, Lado, Variedad, Area, Densidad
from sqlalchemy import asc
from datetime import datetime

class SiembraForm(FlaskForm):
    bloque_id = SelectField('Bloque', coerce=int, validators=[DataRequired()])
    cama_id = SelectField('Cama', coerce=int, validators=[DataRequired()])
    lado_id = SelectField('Lado', coerce=int, validators=[DataRequired()])
    variedad_id = SelectField('Variedad', coerce=int, validators=[DataRequired()])
    area_id = SelectField('Área', coerce=int, validators=[DataRequired()])
    densidad_id = SelectField('Densidad', coerce=int, validators=[DataRequired()])
    fecha_siembra = DateField('Fecha de Siembra', format='%Y-%m-%d', validators=[DataRequired()])
    submit = SubmitField('Registrar Siembra')
    
    def __init__(self, *args, **kwargs):
        super(SiembraForm, self).__init__(*args, **kwargs)
        
        # Bloques ordenados numéricamente
        self.bloque_id.choices = [(b.bloque_id, b.bloque) for b in Bloque.query.order_by(asc(Bloque.bloque)).all()]
        
        # Camas ordenadas numéricamente (convertir a entero para ordenar correctamente)
        camas = Cama.query.all()
        # Ordenar numéricamente en lugar de alfabéticamente
        camas_ordenadas = sorted(camas, key=lambda c: int(c.cama))
        self.cama_id.choices = [(c.cama_id, c.cama) for c in camas_ordenadas]
        
        # Lados ordenados alfabéticamente
        self.lado_id.choices = [(l.lado_id, l.lado) for l in Lado.query.order_by(asc(Lado.lado)).all()]
        
        # Variedades ordenadas alfabéticamente - solo mostrando el nombre de la variedad
        self.variedad_id.choices = [(v.variedad_id, v.variedad) for v in Variedad.query.order_by(Variedad.variedad).all()]
        
        # Áreas ordenadas
        self.area_id.choices = [(a.area_id, a.siembra) for a in Area.query.order_by(Area.siembra).all()]
        
        # Densidades ordenadas
        self.densidad_id.choices = [(d.densidad_id, d.densidad) for d in Densidad.query.order_by(Densidad.densidad).all()]
    
    def validate_fecha_siembra(self, fecha_siembra):
        if fecha_siembra.data > datetime.now().date():
            raise ValidationError('La fecha de siembra no puede ser posterior a hoy')

class InicioCorteForm(FlaskForm):
    fecha_inicio_corte = DateField('Fecha de Inicio de Corte', format='%Y-%m-%d', validators=[DataRequired()])
    submit = SubmitField('Registrar Inicio de Corte')
    
    def validate_fecha_inicio_corte(self, fecha_inicio_corte):
        if fecha_inicio_corte.data > datetime.now().date():
            raise ValidationError('La fecha de inicio de corte no puede ser posterior a hoy')