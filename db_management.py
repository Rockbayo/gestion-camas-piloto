"""
Módulo de gestión de base de datos para la aplicación de Gestión de Camas.
Consolida todas las operaciones de mantenimiento de la base de datos en un solo archivo.
"""
import os
import pandas as pd
from werkzeug.security import generate_password_hash
from sqlalchemy import text, inspect

from app import create_app, db
from app.models import (
    Documento, Usuario, Rol, Permiso, Flor, Color, FlorColor, Variedad,
    Bloque, Cama, Lado, BloqueCamaLado, Area, Densidad
)

# Configuración de entorno de aplicación
app = create_app()


def setup_database():
    """Configura la estructura inicial de la base de datos con tablas y columnas esenciales."""
    with app.app_context():
        inspector = inspect(db.engine)
        
        # Verificar y modificar la tabla usuarios para password_hash
        if 'usuarios' in inspector.get_table_names():
            columns = {col['name']: col for col in inspector.get_columns('usuarios')}
            if 'password_hash' in columns:
                current_type = columns['password_hash']['type']
                if 'VARCHAR(255)' not in str(current_type).upper():
                    db.session.execute(text("ALTER TABLE usuarios MODIFY COLUMN password_hash VARCHAR(255)"))
                    print("Campo password_hash modificado a VARCHAR(255)")
        
        # Verificar y añadir la columna rol_id a la tabla usuarios
        if 'usuarios' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('usuarios')]
            if 'rol_id' not in columns:
                db.session.execute(text("ALTER TABLE usuarios ADD COLUMN rol_id INTEGER"))
                db.session.execute(text("ALTER TABLE usuarios ADD FOREIGN KEY (rol_id) REFERENCES roles(rol_id)"))
                print("Columna rol_id añadida a la tabla usuarios")
        
        # Confirmar cambios
        db.session.commit()
        print("Estructura de la base de datos actualizada correctamente")


def clean_database():
    """Limpia todos los datos de la base de datos manteniendo la estructura."""
    with app.app_context():
        # Desactivar restricciones de clave foránea temporalmente
        db.session.execute(text('SET FOREIGN_KEY_CHECKS=0;'))
        
        # Obtener todas las tablas
        inspector = inspect(db.engine)
        table_names = inspector.get_table_names()
        
        # Eliminar datos de todas las tablas
        for table in table_names:
            print(f"Limpiando tabla: {table}")
            db.session.execute(text(f'TRUNCATE TABLE {table};'))
        
        # Reactivar restricciones de clave foránea
        db.session.execute(text('SET FOREIGN_KEY_CHECKS=1;'))
        db.session.commit()
        print("Base de datos limpiada exitosamente")


def create_roles_permissions():
    """Crea los roles y permisos iniciales para el sistema."""
    with app.app_context():
        # Crear permisos
        permisos_data = [
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
        
        permisos = {}
        for codigo, descripcion in permisos_data:
            permiso = Permiso.query.filter_by(codigo=codigo).first()
            if not permiso:
                permiso = Permiso(codigo=codigo, descripcion=descripcion)
                db.session.add(permiso)
            permisos[codigo] = permiso
        
        db.session.commit()
        print("Permisos creados exitosamente")
        
        # Crear roles
        roles_data = [
            ('Administrador', 'Control total del sistema', list(permisos.values())),
            ('Supervisor', 'Gestión de siembras, cortes y pérdidas', [
                permisos['ver_siembras'], permisos['ver_cortes'], permisos['ver_perdidas'], 
                permisos['ver_dashboard'], permisos['crear_siembra'], permisos['editar_siembra'], 
                permisos['finalizar_siembra'], permisos['crear_corte'], permisos['editar_corte'], 
                permisos['crear_perdida'], permisos['editar_perdida']
            ]),
            ('Operador', 'Registro de cortes y pérdidas', [
                permisos['ver_siembras'], permisos['ver_cortes'], permisos['ver_perdidas'],
                permisos['crear_corte'], permisos['crear_perdida']
            ]),
            ('Visitante', 'Solo lectura', [
                permisos['ver_siembras'], permisos['ver_cortes'], 
                permisos['ver_perdidas'], permisos['ver_dashboard']
            ])
        ]
        
        for nombre, descripcion, permisos_rol in roles_data:
            rol = Rol.query.filter_by(nombre=nombre).first()
            if not rol:
                rol = Rol(nombre=nombre, descripcion=descripcion)
                db.session.add(rol)
                db.session.flush()  # Para obtener el ID del rol
                rol.permisos = permisos_rol
            else:
                rol.permisos = permisos_rol
        
        db.session.commit()
        print("Roles creados exitosamente")


def create_admin_user():
    """Crea el usuario administrador por defecto."""
    with app.app_context():
        # Verificar si existe un usuario admin
        admin = Usuario.query.filter_by(username='admin').first()
        
        if not admin:
            # Verificar si existe el tipo de documento cédula
            doc = Documento.query.filter_by(documento='Cedula de Ciudadania').first()
            if not doc:
                doc = Documento(documento='Cedula de Ciudadania')
                db.session.add(doc)
                db.session.commit()
            
            # Obtener el rol administrador
            admin_rol = Rol.query.filter_by(nombre='Administrador').first()
            
            # Crear el usuario administrador
            admin = Usuario(
                nombre_1='Administrador',
                apellido_1='Sistema',
                cargo='Administrador',
                num_doc=999999,
                documento_id=doc.doc_id,
                username='admin',
                rol_id=admin_rol.rol_id if admin_rol else None
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("Usuario administrador creado exitosamente")
        else:
            # Actualizar el rol del usuario admin existente
            admin_rol = Rol.query.filter_by(nombre='Administrador').first()
            if admin_rol and admin.rol_id != admin_rol.rol_id:
                admin.rol_id = admin_rol.rol_id
                db.session.commit()
                print("Usuario administrador actualizado exitosamente")
            else:
                print("Usuario administrador ya existe y está actualizado")


def check_variedades():
    """Verifica y crea variedades de muestra si es necesario."""
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


def init_database(clean=False):
    """Inicializa la base de datos con todos los datos esenciales."""
    with app.app_context():
        if clean:
            clean_database()
        
        setup_database()
        create_roles_permissions()
        create_admin_user()
        check_variedades()
        print("Base de datos inicializada exitosamente")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Herramienta de gestión de base de datos')
    parser.add_argument('--clean', action='store_true', help='Limpiar todos los datos de la base de datos')
    parser.add_argument('--setup', action='store_true', help='Configurar estructura de la base de datos')
    parser.add_argument('--roles', action='store_true', help='Crear roles y permisos')
    parser.add_argument('--admin', action='store_true', help='Crear usuario administrador')
    parser.add_argument('--variedades', action='store_true', help='Verificar y crear variedades de muestra')
    parser.add_argument('--init', action='store_true', help='Inicializar base de datos completa')
    
    args = parser.parse_args()
    
    if args.clean:
        clean_database()
    if args.setup:
        setup_database()
    if args.roles:
        create_roles_permissions()
    if args.admin:
        create_admin_user()
    if args.variedades:
        check_variedades()
    if args.init:
        init_database(clean=False)
    
    # Si no se proporcionaron argumentos, mostrar ayuda
    if not any(vars(args).values()):
        parser.print_help()