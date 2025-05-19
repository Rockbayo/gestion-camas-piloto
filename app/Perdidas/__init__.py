from flask import Blueprint

bp = Blueprint('perdidas', __name__, url_prefix='/perdidas')

from app.perdidas import routes