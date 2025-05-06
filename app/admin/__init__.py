from flask import Blueprint

# Creación del Blueprint
bp = Blueprint('admin', __name__)

# Importar rutas al final para que estén disponibles al registrar el blueprint
from . import routes