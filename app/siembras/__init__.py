# Inicializar el módulo de siembras
from flask import Blueprint

bp = Blueprint('siembras', __name__)

from app.siembras import routes