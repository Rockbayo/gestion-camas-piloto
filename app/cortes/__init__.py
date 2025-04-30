from flask import Blueprint

cortes = Blueprint('cortes', __name__, url_prefix='/cortes')

from app.cortes import routes