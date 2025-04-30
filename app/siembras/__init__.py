from flask import Blueprint

siembras_bp = Blueprint('siembras', __name__, template_folder='templates')

from app.siembras import routes