# app/admin/forms.py
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import SubmitField, SelectField, BooleanField, StringField, HiddenField, FloatField
from wtforms.validators import DataRequired, Optional, NumberRange

class BaseForm(FlaskForm):
    """Clase base para formularios con campos comunes"""
    submit = SubmitField('Guardar')
    back = SubmitField('Volver')

class ImportDatasetForm(BaseForm):
    """Formulario para importar datasets"""
    excel_file = FileField('Archivo Excel', validators=[
        FileRequired(),
        FileAllowed(['xlsx', 'xls'], 'Solo se permiten archivos Excel')
    ])
    dataset_type = SelectField('Tipo de Datos', choices=[
        ('variedades', 'Variedades'),
        ('bloques', 'Bloques y Camas')
    ], validators=[DataRequired()])

class BaseMappingForm(BaseForm):
    """Formulario base para mapeo de columnas"""
    temp_file_path = HiddenField('Ruta del archivo', validators=[DataRequired()])
    skip_first_row = BooleanField('Omitir primera fila (encabezados)', default=True)
    validate_only = BooleanField('Solo validar (sin importar)', default=False)

class MappingVariedadesForm(BaseMappingForm):
    """Mapeo para variedades"""
    flor_column = SelectField('Columna para Flor', choices=[], validators=[DataRequired()])
    color_column = SelectField('Columna para Color', choices=[], validators=[DataRequired()])
    variedad_column = SelectField('Columna para Variedad', choices=[], validators=[DataRequired()])

class MappingBloquesForm(BaseMappingForm):
    """Mapeo para bloques y camas"""
    bloque_column = SelectField('Columna para Bloque', choices=[], validators=[DataRequired()])
    cama_column = SelectField('Columna para Cama', choices=[], validators=[DataRequired()])
    lado_column = SelectField('Columna para Lado', choices=[], validators=[Optional()])

class DensidadForm(BaseForm):
    """Formulario para densidades"""
    densidad = StringField('Nombre', validators=[DataRequired()])
    valor = FloatField('Valor (plantas/m²)', validators=[DataRequired(), NumberRange(min=0.1)])