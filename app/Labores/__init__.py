from flask import Blueprint

bp = Blueprint('labores', __name__, url_prefix='/labores')

from app.labores import routes