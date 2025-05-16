"""
Filtro personalizado para manejo de fechas y formatos en plantillas

Este módulo proporciona un filtro para Flask que permite formatear fechas
de manera consistente en toda la aplicación, controlando casos de valores nulos.
"""
from datetime import datetime
import json

def add_date_filter(app):
    """
    Configura filtros personalizados para la aplicación Flask.
    
    Args:
        app: La aplicación Flask
    
    Returns:
        La aplicación con los filtros configurados
    """
    @app.template_filter('dateformat')
    def dateformat_filter(date, format='%d-%m-%Y'):
        """
        Formatea una fecha o devuelve un texto predeterminado si la fecha es None.
        
        Args:
            date: Objeto datetime o None
            format: Formato de fecha deseado
            
        Returns:
            String formateado
        """
        if date is None:
            return '<span class="badge bg-warning">No disponible</span>'
        return date.strftime(format)
    
    @app.template_filter('dateonly')
    def dateonly_filter(date, format='%d-%m-%Y'):
        """
        Similar a dateformat pero devuelve solo texto sin HTML.
        
        Args:
            date: Objeto datetime o None
            format: Formato de fecha deseado
            
        Returns:
            String formateado
        """
        if date is None:
            return "No disponible"
        return date.strftime(format)
    
    @app.template_filter('tojson')
    def tojson_filter(obj):
        """
        Convierte un objeto Python a JSON seguro para usar en JavaScript.
        Maneja correctamente objetos datetime y None.
        
        Args:
            obj: Objeto Python a convertir
            
        Returns:
            String JSON
        """
        class DateTimeEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, datetime):
                    return obj.strftime('%Y-%m-%d')
                return super().default(obj)
        
        return json.dumps(obj, cls=DateTimeEncoder, ensure_ascii=False)
        
    return app