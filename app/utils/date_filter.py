"""
Filtros personalizados para manejo de fechas y formatos en plantillas Flask.

Mejoras:
- Mejor organización del código
- Manejo más consistente de errores
- Documentación más clara
"""

from datetime import datetime
import json
from markupsafe import Markup

class DateTimeEncoder(json.JSONEncoder):
    """Encoder personalizado para manejar objetos datetime en JSON."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

def configure_date_filters(app):
    """
    Configura los filtros de fecha personalizados en la aplicación Flask.
    
    Args:
        app: Instancia de la aplicación Flask
    """
    @app.template_filter('dateformat')
    def format_date(date, format='%d-%m-%Y', default_html=None):
        """
        Formatea una fecha con HTML opcional para valores nulos.
        
        Args:
            date: Objeto datetime o None
            format: Formato de strftime
            default_html: HTML para mostrar cuando date es None
        """
        if date is None:
            if default_html is None:
                default_html = '<span class="badge bg-warning">No disponible</span>'
            return Markup(default_html)
        return date.strftime(format)
    
    @app.template_filter('dateonly')
    def date_only(date, format='%d-%m-%Y', default_text="No disponible"):
        """
        Formatea una fecha sin HTML para valores nulos.
        """
        if date is None:
            return default_text
        return date.strftime(format)
    
    @app.template_filter('tojson')
    def to_json(obj, indent=None):
        """
        Convierte un objeto Python a JSON seguro para JavaScript.
        
        Args:
            obj: Objeto a serializar
            indent: Indentación del JSON resultante
        """
        return json.dumps(obj, cls=DateTimeEncoder, ensure_ascii=False, indent=indent)