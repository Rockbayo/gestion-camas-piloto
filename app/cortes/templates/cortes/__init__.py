from flask import Blueprint

cortes_bp = Blueprint('cortes', __name__, template_folder='templates')

from app.cortes import routes