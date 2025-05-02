from flask import Blueprint

bp = Blueprint('cortes', __name__)

from app.cortes import routes