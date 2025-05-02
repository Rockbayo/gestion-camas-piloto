from app import create_app, db
from sqlalchemy import text, inspect
from flask_sqlalchemy import SQLAlchemy

def alter_table_usuarios():
    """Altera la tabla usuarios para añadir una columna de rol_id"""
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        
        # Verificar si la columna rol_id ya existe
        columns = [col['name'] for col in inspector.get_columns('usuarios')]
        if 'rol_id' not in columns:
            print("Añadiendo columna rol_id a la tabla usuarios")
            db.session.execute(text("ALTER TABLE usuarios ADD COLUMN rol_id INTEGER;"))
            db.session.commit()
            print("Columna rol_id añadida correctamente")
        else:
            print("La columna rol_id ya existe en la tabla usuarios")
        
        # Modificar la longitud del campo password_hash
        db.session.execute(text("ALTER TABLE usuarios MODIFY COLUMN password_hash VARCHAR(255);"))
        db.session.commit()
        print("Campo password_hash modificado a VARCHAR(255)")

def create_roles_tables():
    """Crea las tablas para roles y permisos"""
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        
        # Verificar si las tablas ya existen
        tables = inspector.get_table_names()
        
        if 'roles' not in tables:
            print("Creando tabla roles")
            db.session.execute(text("""
                CREATE TABLE roles (
                    rol_id INTEGER PRIMARY KEY AUTO_INCREMENT,
                    nombre VARCHAR(50) NOT NULL UNIQUE,
                    descripcion VARCHAR(200)
                );
            """))
            db.session.commit()
            print("Tabla roles creada correctamente")
        else:
            print("La tabla roles ya existe")
        
        if 'permisos' not in tables:
            print("Creando tabla permisos")
            db.session.execute(text("""
                CREATE TABLE permisos (
                    permiso_id INTEGER PRIMARY KEY AUTO_INCREMENT,
                    codigo VARCHAR(50) NOT NULL UNIQUE,
                    descripcion VARCHAR(200)
                );
            """))
            db.session.commit()
            print("Tabla permisos creada correctamente")
        else:
            print("La tabla permisos ya existe")
        
        if 'roles_permisos' not in tables:
            print("Creando tabla roles_permisos")
            db.session.execute(text("""
                CREATE TABLE roles_permisos (
                    rol_id INTEGER NOT NULL,
                    permiso_id INTEGER NOT NULL,
                    PRIMARY KEY (rol_id, permiso_id),
                    FOREIGN KEY (rol_id) REFERENCES roles(rol_id),
                    FOREIGN KEY (permiso_id) REFERENCES permisos(permiso_id)
                );
            """))
            db.session.commit()
            print("Tabla roles_permisos creada correctamente")
        else:
            print("La tabla roles_permisos ya existe")

if __name__ == "__main__":
    alter_table_usuarios()
    create_roles_tables()