# Guarda como check_variedades.py
from app import create_app, db
from app.models import Variedad, FlorColor, Flor, Color

def check_variedades():
    app = create_app()
    with app.app_context():
        # Verificar si hay variedades
        variedades = Variedad.query.all()
        print(f"Total de variedades: {len(variedades)}")
        
        # Si no hay variedades, verificar si hay flor_color
        if not variedades:
            flor_colors = FlorColor.query.all()
            print(f"Total de flor_color: {len(flor_colors)}")
            
            # Verificar flores y colores
            flores = Flor.query.all()
            colores = Color.query.all()
            print(f"Total de flores: {len(flores)}")
            print(f"Total de colores: {len(colores)}")
            
            # Si hay flor_color pero no hay variedades, podemos crear algunas
            if flor_colors:
                print("Creando variedades de ejemplo...")
                for fc in flor_colors:
                    variedad = Variedad(
                        variedad=f"{fc.flor.flor} {fc.color.color} 1",
                        flor_color_id=fc.flor_color_id
                    )
                    db.session.add(variedad)
                
                try:
                    db.session.commit()
                    print("Variedades creadas exitosamente")
                except Exception as e:
                    db.session.rollback()
                    print(f"Error al crear variedades: {str(e)}")
            
            # Si no hay flor_color, verificar si podemos crear algunos
            elif flores and colores:
                print("Creando combinaciones flor_color...")
                # Crear combinaciones
                for flor in flores:
                    for color in colores:
                        # Verificar si ya existe esta combinación
                        existing = FlorColor.query.filter_by(
                            flor_id=flor.flor_id, 
                            color_id=color.color_id
                        ).first()
                        
                        if not existing:
                            fc = FlorColor(
                                flor_id=flor.flor_id,
                                color_id=color.color_id
                            )
                            db.session.add(fc)
                
                try:
                    db.session.commit()
                    print("Combinaciones flor_color creadas exitosamente")
                    
                    # Ahora crear variedades
                    flor_colors = FlorColor.query.all()
                    for fc in flor_colors:
                        variedad = Variedad(
                            variedad=f"{fc.flor.flor} {fc.color.color} 1",
                            flor_color_id=fc.flor_color_id
                        )
                        db.session.add(variedad)
                    
                    db.session.commit()
                    print("Variedades creadas exitosamente")
                except Exception as e:
                    db.session.rollback()
                    print(f"Error al crear combinaciones: {str(e)}")
        else:
            # Si hay variedades, listarlas
            print("Variedades disponibles:")
            for v in variedades:
                print(f"ID: {v.variedad_id}, Variedad: {v.variedad}")

if __name__ == "__main__":
    check_variedades()