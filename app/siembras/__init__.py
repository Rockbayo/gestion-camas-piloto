from flask import Blueprint

siembras = Blueprint('siembras', __name__, url_prefix='/siembras')

from app.siembras import routes