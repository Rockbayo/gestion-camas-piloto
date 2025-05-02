#Verificar y corregir datos en la base de datos
from app import create_app, db
from app.models import Usuario, Documento, Variedad, FlorColor, Flor, Color

def check_database():
    app = create_app()
    with app.app_context():
        # Verificar usuarios
        usuarios = Usuario.query.all()
        print(f"Total de usuarios: {len(usuarios)}")
        for user in usuarios:
            print(f"ID: {user.usuario_id}, Usuario: {user.username}, Nombre: {user.nombre_1} {user.apellido_1}")
            # Asignar nombre de usuario si no tiene
            if user.username is None:
                user.username = f"{user.nombre_1.lower()}{user.apellido_1.lower()}".replace(" ", "")
                try:
                    db.session.commit()
                    print(f"Nombre de usuario asignado: {user.username}")
                except Exception as e:
                    db.session.rollback()
                    print(f"Error al asignar nombre de usuario: {str(e)}")
        
        # Verificar variedades
        variedades = Variedad.query.all()
        print(f"\nTotal de variedades: {len(variedades)}")
        if variedades:
            for v in variedades:
                print(f"ID: {v.variedad_id}, Variedad: {v.variedad}")
        else:
            # Verificar si hay flor_color
            flor_colors = FlorColor.query.all()
            print(f"Total de flor_color: {len(flor_colors)}")
            if flor_colors:
                # Crear variedades basadas en flor_color
                for fc in flor_colors:
                    try:
                        variedad_nombre = f"{fc.flor.flor} {fc.color.color} 1"
                        variedad = Variedad(variedad=variedad_nombre, flor_color_id=fc.flor_color_id)
                        db.session.add(variedad)
                        print(f"Creando variedad: {variedad_nombre}")
                    except Exception as e:
                        print(f"Error al crear variedad: {str(e)}")
                db.session.commit()

if __name__ == "__main__":
    check_database()