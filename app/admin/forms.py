# app/admin/forms.py
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import SubmitField

class ImportVariedadesForm(FlaskForm):
    excel_file = FileField('Archivo Excel', validators=[
        FileRequired(),
        FileAllowed(['xlsx', 'xls'], 'Solo se permiten archivos Excel')
    ])
    submit = SubmitField('Importar')