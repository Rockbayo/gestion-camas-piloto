# Configuración de la aplicación Flask para la base de datos MySQL
import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'clave_por_defecto'
    
    # Mejora: Escape seguro de contraseña en la URL de la base de datos
    DB_USER = os.environ.get('DB_USER', 'root')
    DB_PASSWORD = quote_plus(os.environ.get('DB_PASSWORD', '101Windtalker#'))
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_NAME = os.environ.get('DB_NAME', 'cpc_optimized')
    
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}?charset=utf8mb4'
        
    # Configuración optimizada de SQLAlchemy
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': int(os.environ.get('DATABASE_POOL_SIZE', 10)),
        'pool_recycle': int(os.environ.get('DATABASE_POOL_RECYCLE', 3600)),
        'pool_pre_ping': True,
        'max_overflow': 20,  # Permite conexiones adicionales en picos de demanda
        'echo': False,        # Desactivar SQL echo en producción
        'echo_pool': False    # Desactivar echo de pool en producción
    }