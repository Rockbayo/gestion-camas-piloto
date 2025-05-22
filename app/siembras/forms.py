from flask_wtf import FlaskForm
from wtforms import SelectField, DateField, SubmitField, IntegerField, FloatField, HiddenField
from wtforms.validators import DataRequired, ValidationError, NumberRange, Optional
from app.models import Bloque, Cama, Lado, Variedad, Densidad, Flor, Color
from sqlalchemy import asc, func
from datetime import datetime

class BaseSiembraForm(FlaskForm):
    bloque_id = SelectField('Bloque', coerce=int, validators=[DataRequired()])
    cama_id = SelectField('Cama', coerce=int, validators=[DataRequired()])
    lado_id = SelectField('Lado', coerce=int, validators=[DataRequired()])
    flor_id = SelectField('Tipo de Flor', coerce=int, validators=[Optional()])
    color_id = SelectField('Color', coerce=int, validators=[Optional()])
    variedad_id = SelectField('Variedad', coerce=int, validators=[DataRequired()])
    fecha_siembra = DateField('Fecha de Siembra', format='%Y-%m-%d', validators=[DataRequired()])
    cantidad_plantas = IntegerField('Cantidad de Plantas', validators=[DataRequired(), NumberRange(min=1)])
    densidad_id = SelectField('Densidad (plantas/m²)', coerce=int, validators=[DataRequired()])
    area_calculada = FloatField('Área Calculada (m²)', validators=[Optional()])
    area_id = HiddenField('Área')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cargar_opciones()
    
    def _cargar_opciones(self):
        # Bloques: ordenar por longitud primero, luego alfabéticamente
        # Esto asegura que "01" aparezca antes que "10"
        bloques = Bloque.query.order_by(
            func.length(Bloque.bloque),
            Bloque.bloque
        ).all()
        self.bloque_id.choices = [(b.bloque_id, b.bloque) for b in bloques]
        
        # Camas: mismo ordenamiento para conservar "001", "002", etc.
        camas = Cama.query.order_by(
            func.length(Cama.cama),
            Cama.cama
        ).all()
        self.cama_id.choices = [(c.cama_id, c.cama) for c in camas]
        
        # Lados: ordenamiento alfabético simple
        lados = Lado.query.order_by(Lado.lado).all()
        self.lado_id.choices = [(l.lado_id, l.lado) for l in lados]
        
        # Flores: ordenamiento alfabético con opción "Todas"
        flores = Flor.query.order_by(Flor.flor).all()
        self.flor_id.choices = [(0, 'Todas las flores')] + [(f.flor_id, f.flor) for f in flores]
        
        # Colores: inicialmente todas las opciones - se filtrarán dinámicamente
        colores = Color.query.order_by(Color.color).all()
        self.color_id.choices = [(0, 'Todos los colores')] + [(c.color_id, c.color) for c in colores]
        
        # Variedades: mostrar solo el nombre de la variedad
        variedades = Variedad.query.order_by(Variedad.variedad).all()
        self.variedad_id.choices = [(0, '-- Seleccione una variedad --')] + [
            (v.variedad_id, v.variedad) 
            for v in variedades
        ]
        
        # Densidades: ordenamiento por valor numérico
        densidades = Densidad.query.order_by(Densidad.valor).all()
        self.densidad_id.choices = [(d.densidad_id, f"{d.densidad} ({d.valor} plantas/m²)") for d in densidades]
    
    def validate_fecha_siembra(self, field):
        if field.data > datetime.now().date():
            raise ValidationError('La fecha de siembra no puede ser posterior a hoy')
    
    def validate_cantidad_plantas(self, field):
        if field.data <= 0:
            raise ValidationError('La cantidad de plantas debe ser mayor a cero')
    
    def validate_variedad_id(self, field):
        if not field.data or field.data == 0:
            raise ValidationError('Debe seleccionar una variedad válida')

class SiembraForm(BaseSiembraForm):
    submit = SubmitField('Registrar Siembra')

class EditarSiembraForm(FlaskForm):
    """Formulario específico para editar siembras existentes."""
    bloque_id = SelectField('Bloque', coerce=int, validators=[DataRequired()])
    cama_id = SelectField('Cama', coerce=int, validators=[DataRequired()])
    lado_id = SelectField('Lado', coerce=int, validators=[DataRequired()])
    variedad_id = SelectField('Variedad', coerce=int, validators=[DataRequired()])
    fecha_siembra = DateField('Fecha de Siembra', format='%Y-%m-%d', validators=[DataRequired()])
    densidad_id = SelectField('Densidad', coerce=int, validators=[DataRequired()])
    cantidad_plantas = IntegerField('Cantidad de Plantas (calculado)', render_kw={'readonly': True})
    area_id = HiddenField('Área')
    submit = SubmitField('Actualizar Siembra')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cargar_opciones()
    
    def _cargar_opciones(self):
        # Mismo ordenamiento que en BaseSiembraForm
        bloques = Bloque.query.order_by(
            func.length(Bloque.bloque),
            Bloque.bloque
        ).all()
        self.bloque_id.choices = [(b.bloque_id, b.bloque) for b in bloques]
        
        camas = Cama.query.order_by(
            func.length(Cama.cama),
            Cama.cama
        ).all()
        self.cama_id.choices = [(c.cama_id, c.cama) for c in camas]
        
        lados = Lado.query.order_by(Lado.lado).all()
        self.lado_id.choices = [(l.lado_id, l.lado) for l in lados]
        
        variedades = Variedad.query.order_by(Variedad.variedad).all()
        self.variedad_id.choices = [
            (v.variedad_id, v.variedad) 
            for v in variedades
        ]
        
        densidades = Densidad.query.order_by(Densidad.valor).all()
        self.densidad_id.choices = [(d.densidad_id, d.descripcion_completa) for d in densidades]
    
    def validate_fecha_siembra(self, field):
        if field.data > datetime.now().date():
            raise ValidationError('La fecha de siembra no puede ser posterior a hoy')

class InicioCorteForm(FlaskForm):
    fecha_inicio_corte = DateField('Fecha de Inicio de Corte', format='%Y-%m-%d', validators=[DataRequired()])
    submit = SubmitField('Registrar Inicio de Corte')
    
    def validate_fecha_inicio_corte(self, field):
        if field.data > datetime.now().date():
            raise ValidationError('La fecha de inicio de corte no puede ser posterior a hoy')