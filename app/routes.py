from flask import render_template, redirect, url_for
from flask_login import login_required, current_user
from app import db

# Ruta principal
@login_required
def index():
    return render_template('index.html')

# Ruta del dashboard
@login_required
def dashboard():
    return render_template('dashboard.html')