from flask import Blueprint

reportes_bp = Blueprint('reportes', __name__, template_folder='templates')

from app.reportes import routes