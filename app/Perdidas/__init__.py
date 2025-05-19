from flask import Blueprint

bp = Blueprint('perdidas', __name__, url_prefix='/perdidas')

# Importar las rutas después de crear el blueprint para evitar importaciones circulares
from app.perdidas import routes