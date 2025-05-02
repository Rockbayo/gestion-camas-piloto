from app import create_app, db
from app.models import Rol, Permiso, Usuario, Documento
from sqlalchemy import text

def init_database():
    app = create_app()
    with app.app_context():
        # Crear roles y permisos
        crear_roles_permisos()
        
        # Crear usuario administrador
        crear_usuario_admin()

def crear_roles_permisos():
    """Crear roles y permisos iniciales"""
    app = create_app()
    with app.app_context():
        # Limpiar tablas de roles y permisos
        db.session.execute(text('SET FOREIGN_KEY_CHECKS=0;'))
        db.session.execute(text('TRUNCATE TABLE roles_permisos;'))
        db.session.execute(text('TRUNCATE TABLE permisos;'))
        db.session.execute(text('TRUNCATE TABLE roles;'))
        db.session.execute(text('SET FOREIGN_KEY_CHECKS=1;'))
        db.session.commit()
        
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
            rol = Rol(nombre=nombre, descripcion=descripcion)
            rol.permisos = permisos_rol
            db.session.add(rol)
        
        db.session.commit()
        print("Roles creados exitosamente")

def crear_usuario_admin():
    """Crear usuario administrador"""
    app = create_app()
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
            admin.rol_id = admin_rol.rol_id if admin_rol else None
            db.session.commit()
            print("Usuario administrador actualizado exitosamente")

if __name__ == "__main__":
    init_database()