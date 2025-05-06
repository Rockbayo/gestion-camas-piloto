# app/admin/forms.py
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import SubmitField, SelectField, BooleanField, StringField, HiddenField
from wtforms.validators import DataRequired, Optional

class ImportVariedadesForm(FlaskForm):
    """Formulario básico para cargar archivo Excel de variedades"""
    excel_file = FileField('Archivo Excel', validators=[
        FileRequired(),
        FileAllowed(['xlsx', 'xls'], 'Solo se permiten archivos Excel')
    ])
    submit = SubmitField('Cargar archivo')

class MappingVariedadesForm(FlaskForm):
    """Formulario para mapear columnas del Excel"""
    # Campo oculto para guardar la ruta temporal del archivo
    temp_file_path = HiddenField('Ruta del archivo', validators=[DataRequired()])
    
    # Selección de columnas para mapeo
    flor_column = SelectField('Columna para Flor', choices=[('', 'Seleccione...')], validators=[DataRequired()])
    color_column = SelectField('Columna para Color', choices=[('', 'Seleccione...')], validators=[DataRequired()])
    variedad_column = SelectField('Columna para Variedad', choices=[('', 'Seleccione...')], validators=[DataRequired()])
    
    # Opciones adicionales
    skip_first_row = BooleanField('Omitir primera fila (encabezados)', default=True)
    validate_only = BooleanField('Solo validar (sin importar)', default=False)
    
    submit = SubmitField('Importar Datos')
    back = SubmitField('Volver')

class ImportDatasetForm(FlaskForm):
    """Formulario general para importar cualquier tipo de dataset"""
    excel_file = FileField('Archivo Excel', validators=[
        FileRequired(),
        FileAllowed(['xlsx', 'xls'], 'Solo se permiten archivos Excel')
    ])
    dataset_type = SelectField('Tipo de Datos', choices=[
        ('variedades', 'Variedades'),
        ('bloques', 'Bloques y Camas'),
        ('areas', 'Áreas'),
        ('densidades', 'Densidades')
    ], validators=[DataRequired()])
    submit = SubmitField('Cargar archivo')