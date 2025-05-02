# direct_db_update.py
import mysql.connector
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def get_db_connection():
    """Establece conexión directa con la base de datos MySQL"""
    db_config = {
        'host': os.environ.get('DB_HOST', '127.0.0.1'),
        'user': os.environ.get('DB_USER', 'root'),
        'password': os.environ.get('DB_PASSWORD', '101Windtalker#'),
        'database': os.environ.get('DB_NAME', 'cpc_optimized')
    }
    
    return mysql.connector.connect(**db_config)

def setup_database():
    """Configura la base de datos con las tablas necesarias"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 1. Modificar la tabla usuarios para cambiar password_hash
        print("Modificando campo password_hash en la tabla usuarios...")
        cursor.execute("SHOW COLUMNS FROM usuarios WHERE Field = 'password_hash'")
        column_info = cursor.fetchone()
        
        if column_info:
            current_type = column_info[1]
            print(f"Tipo actual de password_hash: {current_type}")
            
            if 'varchar(255)' not in current_type.lower():
                cursor.execute("ALTER TABLE usuarios MODIFY COLUMN password_hash VARCHAR(255)")
                print("Campo password_hash modificado a VARCHAR(255)")
            else:
                print("El campo password_hash ya es VARCHAR(255)")
        
        # 2. Crear tablas para roles y permisos
        print("\nCreando tablas para roles y permisos...")
        
        # Verificar si las tablas ya existen
        cursor.execute("SHOW TABLES LIKE 'roles'")
        if not cursor.fetchone():
            print("Creando tabla roles...")
            cursor.execute("""
                CREATE TABLE roles (
                    rol_id INT AUTO_INCREMENT PRIMARY KEY,
                    nombre VARCHAR(50) NOT NULL UNIQUE,
                    descripcion VARCHAR(200)
                )
            """)
            print("Tabla roles creada")
        else:
            print("La tabla roles ya existe")
        
        cursor.execute("SHOW TABLES LIKE 'permisos'")
        if not cursor.fetchone():
            print("Creando tabla permisos...")
            cursor.execute("""
                CREATE TABLE permisos (
                    permiso_id INT AUTO_INCREMENT PRIMARY KEY,
                    codigo VARCHAR(50) NOT NULL UNIQUE,
                    descripcion VARCHAR(200)
                )
            """)
            print("Tabla permisos creada")
        else:
            print("La tabla permisos ya existe")
        
        cursor.execute("SHOW TABLES LIKE 'roles_permisos'")
        if not cursor.fetchone():
            print("Creando tabla roles_permisos...")
            cursor.execute("""
                CREATE TABLE roles_permisos (
                    rol_id INT NOT NULL,
                    permiso_id INT NOT NULL,
                    PRIMARY KEY (rol_id, permiso_id),
                    FOREIGN KEY (rol_id) REFERENCES roles(rol_id),
                    FOREIGN KEY (permiso_id) REFERENCES permisos(permiso_id)
                )
            """)
            print("Tabla roles_permisos creada")
        else:
            print("La tabla roles_permisos ya existe")
        
        # 3. Verificar y añadir la columna rol_id a la tabla usuarios
        cursor.execute("SHOW COLUMNS FROM usuarios LIKE 'rol_id'")
        if not cursor.fetchone():
            print("Añadiendo columna rol_id a la tabla usuarios...")
            cursor.execute("ALTER TABLE usuarios ADD COLUMN rol_id INT")
            cursor.execute("ALTER TABLE usuarios ADD FOREIGN KEY (rol_id) REFERENCES roles(rol_id)")
            print("Columna rol_id añadida a la tabla usuarios")
        else:
            print("La columna rol_id ya existe en la tabla usuarios")
        
        # Confirmar cambios
        conn.commit()
        print("\nEstructura de la base de datos actualizada correctamente")
        
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def populate_roles_and_permissions():
    """Poblamos las tablas de roles y permisos con datos iniciales"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 1. Crear permisos
        print("\nCreando permisos iniciales...")
        permisos = [
            ('ver_siembras', 'Ver listado de siembras'),
            ('crear_siembra', 'Crear nuevas siembras'),
            ('editar_siembra', 'Editar siembras existentes'),
            ('finalizar_siembra', 'Finalizar siembras'),
            ('ver_cortes', 'Ver listado de cortes'),
            ('crear_corte', 'Registrar nuevos cortes'),
            ('editar_corte', 'Editar cortes existentes'),
            ('ver_perdidas', 'Ver listado de pérdidas'),
            ('crear_perdida', 'Registrar nuevas pérdidas'),
            ('editar_perdida', 'Editar pérdidas existentes'),
            ('ver_dashboard', 'Ver dashboard y estadísticas'),
            ('administrar_usuarios', 'Gestionar usuarios'),
            ('administrar_roles', 'Gestionar roles y permisos'),
            ('importar_datos', 'Importar datos desde archivos')
        ]
        
        # Limpiar tablas antes de insertar nuevos datos
        cursor.execute("SET FOREIGN_KEY_CHECKS=0")
        cursor.execute("TRUNCATE TABLE roles_permisos")
        cursor.execute("TRUNCATE TABLE permisos")
        cursor.execute("TRUNCATE TABLE roles")
        cursor.execute("SET FOREIGN_KEY_CHECKS=1")
        
        for codigo, descripcion in permisos:
            cursor.execute(
                "INSERT INTO permisos (codigo, descripcion) VALUES (%s, %s)",
                (codigo, descripcion)
            )
        
        conn.commit()
        print("Permisos creados correctamente")
        
        # Obtener IDs de permisos
        cursor.execute("SELECT permiso_id, codigo FROM permisos")
        permisos_ids = {codigo: permiso_id for permiso_id, codigo in cursor.fetchall()}
        
        # 2. Crear roles
        print("\nCreando roles iniciales...")
        roles = [
            ('Administrador', 'Control total del sistema', list(permisos_ids.values())),
            ('Supervisor', 'Gestión de siembras, cortes y pérdidas', [
                permisos_ids['ver_siembras'], permisos_ids['ver_cortes'], 
                permisos_ids['ver_perdidas'], permisos_ids['ver_dashboard'],
                permisos_ids['crear_siembra'], permisos_ids['editar_siembra'], 
                permisos_ids['finalizar_siembra'], permisos_ids['crear_corte'], 
                permisos_ids['editar_corte'], permisos_ids['crear_perdida'], 
                permisos_ids['editar_perdida']
            ]),
            ('Operador', 'Registro de cortes y pérdidas', [
                permisos_ids['ver_siembras'], permisos_ids['ver_cortes'], 
                permisos_ids['ver_perdidas'], permisos_ids['crear_corte'], 
                permisos_ids['crear_perdida']
            ]),
            ('Visitante', 'Solo lectura', [
                permisos_ids['ver_siembras'], permisos_ids['ver_cortes'], 
                permisos_ids['ver_perdidas'], permisos_ids['ver_dashboard']
            ])
        ]
        
        for nombre, descripcion, permisos_rol in roles:
            cursor.execute(
                "INSERT INTO roles (nombre, descripcion) VALUES (%s, %s)",
                (nombre, descripcion)
            )
            rol_id = cursor.lastrowid
            
            # Asignar permisos al rol
            for permiso_id in permisos_rol:
                cursor.execute(
                    "INSERT INTO roles_permisos (rol_id, permiso_id) VALUES (%s, %s)",
                    (rol_id, permiso_id)
                )
        
        conn.commit()
        print("Roles creados correctamente")
        
        # 3. Asignar rol administrador a usuarios existentes
        print("\nActualizando usuarios existentes...")
        cursor.execute("SELECT rol_id FROM roles WHERE nombre = 'Administrador'")
        admin_rol_id = cursor.fetchone()[0]
        
        # Actualizar usuarios existentes
        cursor.execute("UPDATE usuarios SET rol_id = %s WHERE rol_id IS NULL", (admin_rol_id,))
        affected_rows = cursor.rowcount
        conn.commit()
        print(f"Se actualizaron {affected_rows} usuarios con el rol de Administrador")
        
        # 4. Verificar si existe usuario admin, crearlo si no existe
        cursor.execute("SELECT username FROM usuarios WHERE username = 'admin'")
        if not cursor.fetchone():
            print("\nCreando usuario administrador...")
            
            # Verificar si existe documento tipo cédula
            cursor.execute("SELECT doc_id FROM documentos WHERE documento = 'Cedula de Ciudadania'")
            doc_result = cursor.fetchone()
            
            if doc_result:
                doc_id = doc_result[0]
            else:
                cursor.execute("INSERT INTO documentos (documento) VALUES ('Cedula de Ciudadania')")
                doc_id = cursor.lastrowid
            
            # Crear usuario admin
            from werkzeug.security import generate_password_hash
            password_hash = generate_password_hash('admin123')
            
            cursor.execute("""
                INSERT INTO usuarios 
                (nombre_1, apellido_1, cargo, num_doc, documento_id, username, password_hash, rol_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, ('Administrador', 'Sistema', 'Administrador', 999999, doc_id, 'admin', password_hash, admin_rol_id))
            
            conn.commit()
            print("Usuario administrador creado correctamente")
        else:
            print("El usuario administrador ya existe")
        
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    setup_database()
    populate_roles_and_permissions()