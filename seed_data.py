# Guarda este archivo como seed_data.py en la raíz del proyecto
from app import create_app, db
from app.models import Bloque, Cama, Lado, Flor, Color, FlorColor, Variedad, Area, Densidad, Documento

app = create_app()

with app.app_context():
    # Comprobar si ya existen datos
    if Bloque.query.count() == 0:
        # Crear bloques
        bloques = ['01', '02', '03', '04', '05', '06', '07']
        for b in bloques:
            bloque = Bloque(bloque=b)
            db.session.add(bloque)
        
        print("Bloques creados")
    
    # Crear camas si no existen
    if Cama.query.count() == 0:
        # Crear camas (1-250)
        for i in range(1, 251):
            cama = Cama(cama=str(i))
            db.session.add(cama)
        
        print("Camas creadas")
    
    # Crear lados si no existen
    if Lado.query.count() == 0:
        # Crear lados
        lados = ['A', 'B']
        for l in lados:
            lado = Lado(lado=l)
            db.session.add(lado)
        
        print("Lados creados")
    
    # Crear áreas si no existen
    if Area.query.count() == 0:
        # Crear áreas
        areas = [
            {'siembra': 'Cama', 'area': 57.0},
            {'siembra': 'Media Cama', 'area': 28.5}
        ]
        for a in areas:
            area = Area(siembra=a['siembra'], area=a['area'])
            db.session.add(area)
        
        print("Áreas creadas")
    
    # Crear densidades si no existen
    if Densidad.query.count() == 0:
        # Crear densidades
        densidades = ['ALTA', 'NORMAL', 'BAJA']
        for d in densidades:
            densidad = Densidad(densidad=d)
            db.session.add(densidad)
        
        print("Densidades creadas")
    
    # Crear flores si no existen
    if Flor.query.count() == 0:
        # Crear flores
        flores = [
            {'flor': 'CUSHION', 'flor_abrev': 'CU'},
            {'flor': 'DAISY', 'flor_abrev': 'DA'},
            {'flor': 'NOVELTY', 'flor_abrev': 'NV'}
        ]
        for f in flores:
            flor = Flor(flor=f['flor'], flor_abrev=f['flor_abrev'])
            db.session.add(flor)
        
        print("Flores creadas")
    
    # Crear colores si no existen
    if Color.query.count() == 0:
        # Crear colores
        colores = [
            {'color': 'RED', 'color_abrev': 'RD'},
            {'color': 'WHITE', 'color_abrev': 'WH'},
            {'color': 'LAVANDER', 'color_abrev': 'LV'},
            {'color': 'GREEN', 'color_abrev': 'GR'},
            {'color': 'YELLOW', 'color_abrev': 'YW'}
        ]
        for c in colores:
            color = Color(color=c['color'], color_abrev=c['color_abrev'])
            db.session.add(color)
        
        print("Colores creados")
    
    # Guardar cambios
    db.session.commit()
    
    # Crear relaciones flor_color si no existen
    if FlorColor.query.count() == 0:
        # Obtener flores y colores
        flores = Flor.query.all()
        colores = Color.query.all()
        
        # Crear combinaciones (para este ejemplo, cada flor con cada color)
        for flor in flores:
            for color in colores:
                flor_color = FlorColor(flor_id=flor.flor_id, color_id=color.color_id)
                db.session.add(flor_color)
        
        print("Relaciones Flor-Color creadas")
    
    # Crear variedades si no existen
    if Variedad.query.count() == 0:
        # Crear algunas variedades de ejemplo
        flor_colores = FlorColor.query.all()
        
        # Para cada combinación flor-color, crear algunas variedades
        for i, fc in enumerate(flor_colores):
            flor = Flor.query.get(fc.flor_id)
            color = Color.query.get(fc.color_id)
            
            # Crear 2 variedades por cada combinación
            for j in range(2):
                nombre = f"Variedad {flor.flor} {color.color} {j+1}"
                variedad = Variedad(variedad=nombre, flor_color_id=fc.flor_color_id)
                db.session.add(variedad)
        
        print("Variedades creadas")
    
    # Guardar todos los cambios
    db.session.commit()
    
    print("¡Datos iniciales cargados con éxito!")