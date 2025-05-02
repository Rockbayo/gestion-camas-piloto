from app import create_app, db
from app.models import Usuario
from werkzeug.security import generate_password_hash

def update_users():
    app = create_app()
    with app.app_context():
        usuarios = Usuario.query.all()
        print("Usuarios registrados:")
        for usuario in usuarios:
            print(f"ID: {usuario.usuario_id}, Usuario: {usuario.username}, Nombre: {usuario.nombre_1} {usuario.apellido_1}")
        
        # Actualizar el primer usuario
        usuario = Usuario.query.get(1)
        if usuario:
            # Configurar un nombre de usuario si no tiene
            if not usuario.username:
                usuario.username = "admin"
            
            # Usar un método de hashing válido - 'pbkdf2:sha256' es compatible con Werkzeug actual
            usuario.password_hash = generate_password_hash("admin123", method='pbkdf2:sha256')
            
            try:
                db.session.commit()
                print(f"Usuario actualizado: ID={usuario.usuario_id}, Username={usuario.username}")
            except Exception as e:
                db.session.rollback()
                print(f"Error al actualizar usuario: {str(e)}")
                
                # Si falla por longitud, intentar con un hash más corto
                print("Intentando con un método alternativo...")
                try:
                    usuario.password_hash = generate_password_hash("admin123", method='md5')
                    db.session.commit()
                    print(f"Usuario actualizado con método alternativo: ID={usuario.usuario_id}, Username={usuario.username}")
                except Exception as e2:
                    db.session.rollback()
                    print(f"Error al actualizar usuario con método alternativo: {str(e2)}")
        else:
            print("No se encontró el usuario con ID 1")

if __name__ == "__main__":
    update_users()