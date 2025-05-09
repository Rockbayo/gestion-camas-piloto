def add_date_filter(app):
    """
    Configura un filtro personalizado para formatear fechas en la aplicación Flask.
    Este filtro maneja correctamente las fechas nulas.
    """
    @app.template_filter('dateformat')
    def dateformat_filter(date, format='%d-%m-%Y'):
        """
        Formatea una fecha o devuelve un texto predeterminado si la fecha es None.
        """
        if date is None:
            return '<span class="badge bg-warning">Estado Vegetativo</span>'
        return date.strftime(format)
    
    @app.template_filter('dateonly')
    def dateonly_filter(date, format='%d-%m-%Y'):
        """
        Similar a dateformat pero devuelve solo texto sin HTML.
        """
        if date is None:
            return "Estado Vegetativo"
        return date.strftime(format)
    
    return app