"""
Script para inicializar la base de datos con datos iniciales.
Ejecutar después de crear las tablas y antes de usar la aplicación.
"""

from app import create_app, db
from app.models import (
    Bloque, Cama, Lado, BloqueCamaLado, Flor, Color, FlorColor, 
    Area, Densidad, Causa, Documento
)

app = create_app()

def init_bloques():
    """Inicializar los bloques."""
    print("Inicializando bloques...")
    
    # Verificar si ya existen bloques
    if Bloque.query.first():
        print("Ya existen bloques en la base de datos.")
        return
    
    # Crear bloques del 01 al 07
    for i in range(1, 8):
        bloque = Bloque(bloque=f"{i:02d}")
        db.session.add(bloque)
    
    db.session.commit()
    print("Bloques inicializados correctamente.")

def init_camas():
    """Inicializar las camas."""
    print("Inicializando camas...")
    
    # Verificar si ya existen camas
    if Cama.query.first():
        print("Ya existen camas en la base de datos.")
        return
    
    # Crear camas del 1 al 250
    for i in range(1, 251):
        cama = Cama(cama=str(i))
        db.session.add(cama)
    
    db.session.commit()
    print("Camas inicializadas correctamente.")

def init_lados():
    """Inicializar los lados."""
    print("Inicializando lados...")
    
    # Verificar si ya existen lados
    if Lado.query.first():
        print("Ya existen lados en la base de datos.")
        return
    
    # Crear lados A y B
    lado_a = Lado(lado="A")
    lado_b = Lado(lado="B")
    
    db.session.add(lado_a)
    db.session.add(lado_b)
    
    db.session.commit()
    print("Lados inicializados correctamente.")

def init_flores_colores():
    """Inicializar flores y colores."""
    print("Inicializando flores y colores...")
    
    # Verificar si ya existen flores y colores
    if Flor.query.first() and Color.query.first():
        print("Ya existen flores y colores en la base de datos.")
        return
    
    # Crear flores
    flores = [
        {"flor": "CUSHION", "flor_abrev": "CU"},
        {"flor": "DAISY", "flor_abrev": "DA"},
        {"flor": "NOVELTY", "flor_abrev": "NV"}
    ]
    
    for f in flores:
        flor = Flor(flor=f["flor"], flor_abrev=f["flor_abrev"])
        db.session.add(flor)
    
    # Crear colores
    colores = [
        {"color": "RED", "color_abrev": "RD"},
        {"color": "WHITE", "color_abrev": "WH"},
        {"color": "LAVANDER", "color_abrev": "LV"},
        {"color": "GREEN", "color_abrev": "GR"},
        {"color": "YELLOW", "color_abrev": "YW"},
        {"color": "PURPLE", "color_abrev": "PU"},
        {"color": "PINK", "color_abrev": "PK"},
        {"color": "PEACH", "color_abrev": "PC"},
        {"color": "BRONZE", "color_abrev": "BZ"},
        {"color": "LIGHT BRONZE", "color_abrev": "Q5"},
        {"color": "DARK BRONZE", "color_abrev": "Q6"},
        {"color": "PURPLE BI COLOR", "color_abrev": "PUB"},
        {"color": "BRONZR BI COLOR", "color_abrev": "BZB"},
        {"color": "ORANGE", "color_abrev": "OR"},
        {"color": "DARK PINK", "color_abrev": "DP"}
    ]
    
    for c in colores:
        color = Color(color=c["color"], color_abrev=c["color_abrev"])
        db.session.add(color)
    
    db.session.commit()
    print("Flores y colores inicializados correctamente.")

def init_areas_densidades():
    """Inicializar áreas y densidades."""
    print("Inicializando áreas y densidades...")
    
    # Verificar si ya existen áreas
    if Area.query.first():
        print("Ya existen áreas en la base de datos.")
    else:
        # Crear áreas
        areas = [
            {"siembra": "Cama", "area": 57.0},
            {"siembra": "Media Cama", "area": 28.5}
        ]
        
        for a in areas:
            area = Area(siembra=a["siembra"], area=a["area"])
            db.session.add(area)
        
        db.session.commit()
        print("Áreas inicializadas correctamente.")
    
    # Verificar si ya existen densidades
    if Densidad.query.first():
        print("Ya existen densidades en la base de datos.")
    else:
        # Crear densidades
        densidades = ["ALTA", "NORMAL", "BAJA"]
        
        for d in densidades:
            densidad = Densidad(densidad=d)
            db.session.add(densidad)
        
        db.session.commit()
        print("Densidades inicializadas correctamente.")

def init_causas():
    """Inicializar causas de pérdida."""
    print("Inicializando causas de pérdida...")
    
    # Verificar si ya existen causas
    if Causa.query.first():
        print("Ya existen causas en la base de datos.")
        return
    
    # Crear causas de pérdida
    causas = [
        "Enfermedad",
        "Plaga",
        "Clima",
        "Daño mecánico",
        "Desnutrición",
        "Otro"
    ]
    
    for c in causas:
        causa = Causa(causa=c)
        db.session.add(causa)
    
    db.session.commit()
    print("Causas de pérdida inicializadas correctamente.")

def init_documentos():
    """Inicializar tipos de documento."""
    print("Inicializando tipos de documento...")
    
    # Verificar si ya existen documentos
    if Documento.query.first():
        print("Ya existen documentos en la base de datos.")
        return
    
    # Crear tipos de documento
    documentos = [
        "Cedula de Ciudadania",
        "Pasaporte",
        "Tarjeta de Identidad",
        "Cedula de Extranjeria"
    ]
    
    for d in documentos:
        documento = Documento(documento=d)
        db.session.add(documento)
    
    db.session.commit()
    print("Tipos de documento inicializados correctamente.")

def init_flor_color():
    """Inicializar combinaciones flor-color."""
    print("Inicializando combinaciones flor-color...")
    
    # Verificar si ya existen combinaciones
    if FlorColor.query.first():
        print("Ya existen combinaciones flor-color en la base de datos.")
        return
    
    # Crear todas las combinaciones posibles de flor y color
    flores = Flor.query.all()
    colores = Color.query.all()
    
    for flor in flores:
        for color in colores:
            # Verificar si la combinación ya existe
            combinacion = FlorColor.query.filter_by(flor_id=flor.flor_id, color_id=color.color_id).first()
            if not combinacion:
                flor_color = FlorColor(flor_id=flor.flor_id, color_id=color.color_id)
                db.session.add(flor_color)
    
    db.session.commit()
    print("Combinaciones flor-color inicializadas correctamente.")

def main():
    """Inicializar la base de datos con datos básicos."""
    with app.app_context():
        print("=== INICIALIZACIÓN DE DATOS BÁSICOS ===")
        
        # Inicializar tablas básicas
        init_bloques()
        init_camas()
        init_lados()
        init_flores_colores()
        init_areas_densidades()
        init_causas()
        init_documentos()
        init_flor_color()
        
        print("\n¡Inicialización completada con éxito!")
        print("Ahora puede ejecutar 'python create_admin.py' para crear un usuario administrador.")

if __name__ == "__main__":
    main()