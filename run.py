from app import create_app, db
from app.models import (Usuario, Documento, Bloque, Cama, Lado, 
                        BloqueCamaLado, Flor, Color, FlorColor, 
                        Variedad, Area, Densidad, Siembra, Corte)

app = create_app()

@app.context_processor
def utility_processor():
    def now(format_string='%Y'):
        from datetime import datetime
        return datetime.now().strftime(format_string)
    return {'now': now}

if __name__ == '__main__':
    app.run(debug=True)