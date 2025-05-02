# Inicilizar el modulo perdidas
from flask import Blueprint

bp = Blueprint('perdidas', __name__)

from app.perdidas import routes