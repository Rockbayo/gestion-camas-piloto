# app/admin/forms.py
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import SubmitField, SelectField, BooleanField, StringField, HiddenField, FloatField
from wtforms.validators import DataRequired, Optional, NumberRange

class ImportDatasetForm(FlaskForm):
    """Formulario general para importar cualquier tipo de dataset"""
    excel_file = FileField('Archivo Excel', validators=[
        FileRequired(),
        FileAllowed(['xlsx', 'xls'], 'Solo se permiten archivos Excel')
    ])
    dataset_type = SelectField('Tipo de Datos', choices=[
        ('variedades', 'Variedades'),
        ('bloques', 'Bloques y Camas'),
        ('causas', 'Causas de Pérdida')
    ], validators=[DataRequired()])
    submit = SubmitField('Cargar archivo')

class MappingForm(FlaskForm):
    """Formulario base para mapear columnas del Excel"""
    temp_file_path = HiddenField('Ruta del archivo', validators=[DataRequired()])
    skip_first_row = BooleanField('Omitir primera fila (encabezados)', default=True)
    validate_only = BooleanField('Solo validar (sin importar)', default=False)
    submit = SubmitField('Importar Datos')
    back = SubmitField('Volver')

class MappingVariedadesForm(MappingForm):
    """Formulario para mapear columnas del Excel de variedades"""
    flor_column = SelectField('Columna para Flor', choices=[('', 'Seleccione...')], validators=[DataRequired()])
    color_column = SelectField('Columna para Color', choices=[('', 'Seleccione...')], validators=[DataRequired()])
    variedad_column = SelectField('Columna para Variedad', choices=[('', 'Seleccione...')], validators=[DataRequired()])

class MappingBloquesForm(MappingForm):
    """Formulario para mapear columnas del Excel de bloques y camas"""
    bloque_column = SelectField('Columna para Bloque', choices=[('', 'Seleccione...')], validators=[DataRequired()])
    cama_column = SelectField('Columna para Cama', choices=[('', 'Seleccione...')], validators=[DataRequired()])
    lado_column = SelectField('Columna para Lado', choices=[('', 'Seleccione...')], validators=[Optional()])

class DensidadForm(FlaskForm):
    """Formulario para crear y editar densidades"""
    densidad = StringField('Nombre', validators=[DataRequired()])
    valor = FloatField('Valor (plantas/m²)', validators=[DataRequired(), NumberRange(min=0.1)])
    submit = SubmitField('Guardar')

class MappingCausasForm(MappingForm):
    """Formulario para mapear columnas del Excel de causas"""
    causa_column = SelectField('Columna para Causa', choices=[('', 'Seleccione...')], validators=[DataRequired()])