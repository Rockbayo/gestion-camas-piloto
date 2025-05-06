#!/usr/bin/env python3
"""
Script principal de administración para la aplicación de Gestión de Camas.
Proporciona comandos para gestionar la aplicación, la base de datos y los datos.
"""
import os
import click
from app import create_app, db
from flask.cli import with_appcontext

# Importar modelos
from app.models import (
    Documento, Usuario, Rol, Permiso, Flor, Color, FlorColor, Variedad,
    Bloque, Cama, Lado, BloqueCamaLado, Area, Densidad, Siembra, Corte,
    Causa, Perdida
)

# Crear la aplicación
app = create_app()


@click.group()
def cli():
    """Herramienta de administración para la aplicación de Gestión de Camas."""
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
    from sqlalchemy import text
    
    with app.app_context():
        # Desactivar restricciones de clave foránea temporalmente
        db.session.execute(text('SET FOREIGN_KEY_CHECKS=0;'))
        
        # Obtener todas las tablas
        tables = db.engine.table_names()
        
        # Eliminar datos de todas las tablas
        for table in tables:
            print(f"Limpiando tabla: {table}")
            db.session.execute(text(f'TRUNCATE TABLE {table};'))
        
        # Reactivar restricciones de clave foránea
        db.session.execute(text('SET FOREIGN_KEY_CHECKS=1;'))
        db.session.commit()
        click.echo("Base de datos limpiada exitosamente")


@cli.command()
@with_appcontext
def init_roles():
    """Inicializar roles y permisos."""
    from db_management import create_roles_permissions
    create_roles_permissions()
    click.echo("Roles y permisos inicializados correctamente")


@cli.command()
@with_appcontext
def init_admin():
    """Crear usuario administrador."""
    from db_management import create_admin_user
    create_admin_user()
    click.echo("Usuario administrador creado correctamente")


@cli.command()
@click.option('--clean', is_flag=True, help='Limpiar la base de datos antes de inicializar')
@with_appcontext
def init_db(clean):
    """Inicializar la base de datos con datos básicos."""
    from db_management import init_database
    init_database(clean=clean)
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
        
        # Verificar siembras, cortes y pérdidas
        siembras = Siembra.query.all()
        cortes = Corte.query.all()
        perdidas = Perdida.query.all()
        click.echo(f"Total de siembras: {len(siembras)}")
        click.echo(f"Total de cortes: {len(cortes)}")
        click.echo(f"Total de pérdidas: {len(perdidas)}")


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
@click.option('--no-fixtures', is_flag=True, help='No cargar datos de ejemplo')
@with_appcontext
def check_variedades(no_fixtures):
    """Verificar y crear variedades de muestra si es necesario."""
    from db_management import check_variedades
    if no_fixtures:
        # Solo verificar
        with app.app_context():
            variedades = Variedad.query.all()
            click.echo(f"Total de variedades: {len(variedades)}")
    else:
        # Verificar y crear si es necesario
        check_variedades()
        click.echo("Verificación y creación de variedades completada")


if __name__ == '__main__':
    cli()