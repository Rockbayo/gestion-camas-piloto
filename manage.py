#!/usr/bin/env python3
"""
Script principal de administración para la aplicación de Gestión de Cultivos.
Proporciona comandos para gestionar la aplicación, la base de datos y los datos.
"""
import os
import click
import shutil
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash
from sqlalchemy import text, inspect

from app import create_app, db
from app.models import (
    Documento, Usuario, Rol, Permiso, Flor, Color, FlorColor, Variedad,
    Bloque, Cama, Lado, BloqueCamaLado, Area, Densidad, Siembra, Corte
)

# Crear la aplicación
app = create_app()


@click.group()
def cli():
    """Herramienta de administración para la aplicación de Gestión de Cultivos."""
    pass


@cli.command()
@click.option('--debug', is_flag=True, help='Ejecutar en modo debug')
@click.option('--host', default='127.0.0.1', help='Host para el servidor')
@click.option('--port', default=5000, help='Puerto para el servidor')
def run(debug, host, port):
    """Ejecutar el servidor de desarrollo."""
    app.run(debug=debug, host=host, port=port)


@cli.command()
@click.confirmation_option(prompt='¿Está seguro de limpiar TODA la base de datos?')
@with_appcontext
def clean_db():
    """Limpiar todos los datos de la base de datos."""
    with app.app_context():
        # Desactivar restricciones de clave foránea temporalmente
        db.session.execute(text('SET FOREIGN_KEY_CHECKS=0;'))
        
        # Obtener todas las tablas
        tables = db.engine.table_names()
        
        # Eliminar datos de todas las tablas
        for table in tables:
            click.echo(f"Limpiando tabla: {table}")
            db.session.execute(text(f'TRUNCATE TABLE {table};'))
        
        # Reactivar restricciones de clave foránea
        db.session.execute(text('SET FOREIGN_KEY_CHECKS=1;'))
        db.session.commit()
        click.echo("Base de datos limpiada exitosamente")


@cli.command()
@with_appcontext
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
                    click.echo("Campo password_hash modificado a VARCHAR(255)")
        
        # Verificar y añadir la columna rol_id a la tabla usuarios
        if 'usuarios' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('usuarios')]
            if 'rol_id' not in columns:
                db.session.execute(text("ALTER TABLE usuarios ADD COLUMN rol_id INTEGER"))
                db.session.execute(text("ALTER TABLE usuarios ADD FOREIGN KEY (rol_id) REFERENCES roles(rol_id)"))
                click.echo("Columna rol_id añadida a la tabla usuarios")
        
        # Confirmar cambios
        db.session.commit()
        click.echo("Estructura de la base de datos actualizada correctamente")


@cli.command()
@with_appcontext
def init_roles():
    """Inicializar roles y permisos."""
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
        click.echo("Permisos creados exitosamente")
        
        # Crear roles
        roles_data = [
            ('Administrador', 'Control total del sistema', list(permisos.values())),
            ('Supervisor', 'Gestión de siembras y cortes', [
                permisos['ver_siembras'], permisos['ver_cortes'],
                permisos['ver_dashboard'], permisos['crear_siembra'], permisos['editar_siembra'], 
                permisos['finalizar_siembra'], permisos['crear_corte'], permisos['editar_corte']
            ]),
            ('Operador', 'Registro de cortes', [
                permisos['ver_siembras'], permisos['ver_cortes'],
                permisos['crear_corte']
            ]),
            ('Visitante', 'Solo lectura', [
                permisos['ver_siembras'], permisos['ver_cortes'], 
                permisos['ver_dashboard']
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
        click.echo("Roles creados exitosamente")


@cli.command()
@with_appcontext
def init_admin():
    """Crear usuario administrador."""
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
            click.echo("Usuario administrador creado exitosamente")
        else:
            # Actualizar el rol del usuario admin existente
            admin_rol = Rol.query.filter_by(nombre='Administrador').first()
            if admin_rol and admin.rol_id != admin_rol.rol_id:
                admin.rol_id = admin_rol.rol_id
                db.session.commit()
                click.echo("Usuario administrador actualizado exitosamente")
            else:
                click.echo("Usuario administrador ya existe y está actualizado")


@cli.command()
@click.option('--clean', is_flag=True, help='Limpiar la base de datos antes de inicializar')
@with_appcontext
def init_db(clean):
    """Inicializar la base de datos con datos básicos."""
    with app.app_context():
        if clean:
            if click.confirm('¿Está seguro de limpiar la base de datos antes de inicializar?', default=False):
                clean_db()
        
        setup_database()
        init_roles()
        init_admin()
        check_variedades()
        click.echo("Base de datos inicializada correctamente")


@cli.command()
@with_appcontext
def check_db():
    """Verificar la integridad de la base de datos."""
    with app.app_context():
        # Verificar usuarios
        usuarios = Usuario.query.all()
        click.echo(f"Total de usuarios: {len(usuarios)}")
        
        # Verificar roles
        roles = Rol.query.all()
        click.echo(f"Total de roles: {len(roles)}")
        
        # Verificar variedades
        variedades = Variedad.query.all()
        click.echo(f"Total de variedades: {len(variedades)}")
        
        # Verificar flor_color
        flor_colors = FlorColor.query.all()
        click.echo(f"Total de combinaciones flor-color: {len(flor_colors)}")
        
        # Verificar bloques, camas y lados
        bloques = Bloque.query.all()
        camas = Cama.query.all()
        lados = Lado.query.all()
        click.echo(f"Total de bloques: {len(bloques)}")
        click.echo(f"Total de camas: {len(camas)}")
        click.echo(f"Total de lados: {len(lados)}")
        
        # Verificar ubicaciones (bloque_cama_lado)
        ubicaciones = BloqueCamaLado.query.all()
        click.echo(f"Total de ubicaciones: {len(ubicaciones)}")
        
        # Verificar áreas y densidades
        areas = Area.query.all()
        densidades = Densidad.query.all()
        click.echo(f"Total de áreas: {len(areas)}")
        click.echo(f"Total de densidades: {len(densidades)}")
        
        # Verificar siembras y cortes
        siembras = Siembra.query.all()
        cortes = Corte.query.all()
        click.echo(f"Total de siembras: {len(siembras)}")
        click.echo(f"Total de cortes: {len(cortes)}")


@cli.command()
@click.option('--username', prompt=True, help='Nombre de usuario')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='Contraseña')
@with_appcontext
def reset_password(username, password):
    """Resetear la contraseña de un usuario."""
    with app.app_context():
        user = Usuario.query.filter_by(username=username).first()
        if user:
            user.set_password(password)
            db.session.commit()
            click.echo(f"Contraseña de {username} actualizada correctamente")
        else:
            click.echo(f"Usuario {username} no encontrado")


@cli.command()
@click.option('--nombre-1', prompt=True, help='Primer nombre')
@click.option('--apellido-1', prompt=True, help='Primer apellido')
@click.option('--username', prompt=True, help='Nombre de usuario')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='Contraseña')
@click.option('--rol', type=click.Choice(['Administrador', 'Supervisor', 'Operador', 'Visitante']), default='Operador', prompt=True, help='Rol del usuario')
@with_appcontext
def create_user(nombre_1, apellido_1, username, password, rol):
    """Crear un nuevo usuario."""
    with app.app_context():
        # Verificar si el usuario ya existe
        if Usuario.query.filter_by(username=username).first():
            click.echo(f"El usuario {username} ya existe")
            return
        
        # Obtener el documento (cédula)
        doc = Documento.query.filter_by(documento='Cedula de Ciudadania').first()
        if not doc:
            doc = Documento(documento='Cedula de Ciudadania')
            db.session.add(doc)
            db.session.commit()
        
        # Obtener el rol
        rol_obj = Rol.query.filter_by(nombre=rol).first()
        if not rol_obj:
            click.echo(f"El rol {rol} no existe. Ejecute 'python manage.py init_roles' para crear los roles")
            return
        
        # Crear el usuario
        user = Usuario(
            nombre_1=nombre_1,
            apellido_1=apellido_1,
            cargo=rol,
            num_doc=0,  # Valor por defecto
            documento_id=doc.doc_id,
            username=username,
            rol_id=rol_obj.rol_id
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Usuario {username} creado exitosamente con rol {rol}")


@cli.command()
@with_appcontext
def check_variedades():
    """Verificar y crear variedades de muestra si es necesario."""
    with app.app_context():
        # Verificar si hay variedades
        variedades = Variedad.query.all()
        click.echo(f"Total de variedades: {len(variedades)}")
        
        # Si no hay variedades, verificar si hay flor_color
        if not variedades:
            flor_colors = FlorColor.query.all()
            click.echo(f"Total de flor_color: {len(flor_colors)}")
            
            # Verificar flores y colores
            flores = Flor.query.all()
            colores = Color.query.all()
            click.echo(f"Total de flores: {len(flores)}")
            click.echo(f"Total de colores: {len(colores)}")
            
            # Si hay flor_color pero no hay variedades, podemos crear algunas
            if flor_colors:
                click.echo("Creando variedades de ejemplo...")
                for fc in flor_colors:
                    variedad = Variedad(
                        variedad=f"{fc.flor.flor} {fc.color.color} 1",
                        flor_color_id=fc.flor_color_id
                    )
                    db.session.add(variedad)
                
                try:
                    db.session.commit()
                    click.echo("Variedades creadas exitosamente")
                except Exception as e:
                    db.session.rollback()
                    click.echo(f"Error al crear variedades: {str(e)}")
            
            # Si no hay flor_color, verificar si podemos crear algunos
            elif flores and colores:
                click.echo("Creando combinaciones flor_color...")
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
                    click.echo("Combinaciones flor_color creadas exitosamente")
                    
                    # Ahora crear variedades
                    flor_colors = FlorColor.query.all()
                    for fc in flor_colors:
                        variedad = Variedad(
                            variedad=f"{fc.flor.flor} {fc.color.color} 1",
                            flor_color_id=fc.flor_color_id
                        )
                        db.session.add(variedad)
                    
                    db.session.commit()
                    click.echo("Variedades creadas exitosamente")
                except Exception as e:
                    db.session.rollback()
                    click.echo(f"Error al crear combinaciones: {str(e)}")


@cli.command()
@click.confirmation_option(prompt='¿Está seguro de eliminar archivos obsoletos? Esto no puede deshacerse.')
def cleanup_obsolete():
    """Eliminar archivos y directorios relacionados con módulos no utilizados."""
    # Lista de archivos a eliminar
    files_to_delete = [
        # Módulo de pérdidas
        "app/perdidas/__init__.py",
        "app/perdidas/forms.py",
        "app/perdidas/routes.py",
        
        # Plantillas de pérdidas
        "app/templates/perdidas/crear.html",
        "app/templates/perdidas/editar.html",
        "app/templates/perdidas/index.html",
        
        # Plantillas de administración de causas
        "app/templates/admin/causas.html",
        "app/templates/admin/importar_causas.html",
        "app/templates/admin/importar_causas_directo.html",
        
        # Utilidades para importación de causas
        "app/utils/causas_importer.py",
        
        # Scripts redundantes
        "init_database.py",
        "reset_database.py",
        "run_migrations.py",
        "update_models.py",
        "update_users.py",
        "cleanup.py",
        
        # README duplicado
        "README2.md",
    ]
    
    # Directorios a eliminar
    dirs_to_delete = [
        "app/perdidas",
        "app/templates/perdidas"
    ]
    
    # Eliminar archivos
    deleted_files = 0
    for file_path in files_to_delete:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                click.echo(f"Archivo eliminado: {file_path}")
                deleted_files += 1
            except Exception as e:
                click.echo(f"Error al eliminar archivo {file_path}: {str(e)}")
    
    # Eliminar directorios (solo si están vacíos)
    deleted_dirs = 0
    for dir_path in dirs_to_delete:
        if os.path.exists(dir_path) and not os.listdir(dir_path):
            try:
                shutil.rmtree(dir_path)
                click.echo(f"Directorio eliminado: {dir_path}")
                deleted_dirs += 1
            except Exception as e:
                click.echo(f"Error al eliminar directorio {dir_path}: {str(e)}")
    
    # Búsqueda y eliminación de archivos .pyc compilados relacionados
    pyc_count = 0
    for root, dirs, files in os.walk("app"):
        for file in files:
            if file.endswith(".pyc") and ("perdidas" in file or "causas" in file):
                pyc_path = os.path.join(root, file)
                try:
                    os.remove(pyc_path)
                    click.echo(f"Archivo .pyc eliminado: {pyc_path}")
                    pyc_count += 1
                except Exception as e:
                    click.echo(f"Error al eliminar archivo {pyc_path}: {str(e)}")
    
    # Resumen de limpieza
    click.echo("\nResumen de limpieza:")
    click.echo(f"- Archivos eliminados: {deleted_files}/{len(files_to_delete)}")
    click.echo(f"- Directorios eliminados: {deleted_dirs}/{len(dirs_to_delete)}")
    click.echo(f"- Archivos .pyc eliminados: {pyc_count}")
    
    # Instrucciones adicionales
    click.echo("\nLimpieza completada. Para completar el proceso:")
    click.echo("1. Verifique que no quedan referencias a 'causas' o 'perdidas' en la base de datos:")
    click.echo("   python manage.py check_db")
    click.echo("2. Actualice la documentación del proyecto si es necesario")


@cli.command()
@click.option('--densidad', required=True, help='Nombre de la densidad')
@click.option('--valor', required=True, type=float, help='Valor de plantas por metro cuadrado')
@with_appcontext
def add_densidad(densidad, valor):
    """Añadir una nueva densidad de siembra."""
    with app.app_context():
        # Verificar si ya existe esta densidad
        existing = Densidad.query.filter_by(densidad=densidad).first()
        if existing:
            click.echo(f"Ya existe una densidad con el nombre '{densidad}'")
            if click.confirm('¿Desea actualizar su valor?'):
                existing.valor = valor
                db.session.commit()
                click.echo(f"Densidad '{densidad}' actualizada con valor {valor}")
            return
        
        # Crear nueva densidad
        nueva_densidad = Densidad(densidad=densidad, valor=valor)
        db.session.add(nueva_densidad)
        db.session.commit()
        click.echo(f"Densidad '{densidad}' creada exitosamente con valor {valor}")


@cli.command()
@with_appcontext
def update_indexes():
    """Actualizar índices de la base de datos para optimizar rendimiento."""
    with app.app_context():
        try:
            # Función para verificar si un índice existe
            def index_exists(table, index_name):
                inspector = inspect(db.engine)
                indexes = inspector.get_indexes(table)
                return any(idx['name'] == index_name for idx in indexes)
            
            # Función para crear un índice si no existe
            def create_index_if_not_exists(table, index_name, columns):
                if not index_exists(table, index_name):
                    db.session.execute(text(f"CREATE INDEX {index_name} ON {table}({columns})"))
                    click.echo(f"Índice {index_name} creado en {table}")
                else:
                    click.echo(f"Índice {index_name} ya existe en {table}")
            
            # Añadir índices a la tabla siembras
            create_index_if_not_exists('siembras', 'idx_fecha_siembra', 'fecha_siembra')
            create_index_if_not_exists('siembras', 'idx_fecha_inicio_corte', 'fecha_inicio_corte')
            create_index_if_not_exists('siembras', 'idx_estado', 'estado')
            
            # Añadir índices a la tabla cortes
            create_index_if_not_exists('cortes', 'idx_fecha_corte', 'fecha_corte')
            
            db.session.commit()
            click.echo("Índices actualizados correctamente")
        except Exception as e:
            db.session.rollback()
            click.echo(f"Error al actualizar índices: {str(e)}")