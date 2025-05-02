# init_roles_permissions.py
from app import create_app, db
from app.models import Rol, Permiso, roles_permisos, Usuario, Documento

def init_roles_permissions():
    app = create_app()
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
        
        for codigo, descripcion in permisos_data:
            if not Permiso.query.filter_by(codigo=codigo).first():
                permiso = Permiso(codigo=codigo, descripcion=descripcion)
                db.session.add(permiso)
        
        db.session.commit()
        print("Permisos creados exitosamente")
        
        # Crear roles
        admin_permisos = Permiso.query.all()
        
        supervisor_permisos = Permiso.query.filter(
            Permiso.codigo.in_([
                'ver_siembras', 'ver_cortes', 'ver_perdidas', 'ver_dashboard',
                'crear_siembra', 'editar_siembra', 'finalizar_siembra',
                'crear_corte', 'editar_corte', 'crear_perdida', 'editar_perdida'
            ])
        ).all()
        
        operador_permisos = Permiso.query.filter(
            Permiso.codigo.in_([
                'ver_siembras', 'ver_cortes', 'ver_perdidas',
                'crear_corte', 'crear_perdida'
            ])
        ).all()
        
        visitante_permisos = Permiso.query.filter(
            Permiso.codigo.in_(['ver_siembras', 'ver_cortes', 'ver_perdidas', 'ver_dashboard'])
        ).all()
        
        roles_data = [
            ('Administrador', 'Control total del sistema', admin_permisos),
            ('Supervisor', 'Gestión de siembras, cortes y pérdidas', supervisor_permisos),
            ('Operador', 'Registro de cortes y pérdidas', operador_permisos),
            ('Visitante', 'Solo lectura', visitante_permisos)
        ]
        
        for nombre, descripcion, permisos in roles_data:
            rol = Rol.query.filter_by(nombre=nombre).first()
            if not rol:
                rol = Rol(nombre=nombre, descripcion=descripcion)
                db.session.add(rol)
                db.session.flush()  # Para obtener el ID del rol
            
            # Asignar permisos al rol
            rol.permisos = permisos
        
        db.session.commit()
        print("Roles creados exitosamente")
        
        # Crear usuario administrador
        if not Usuario.query.filter_by(username='admin').first():
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
                rol_id=admin_rol.rol_id
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("Usuario administrador creado exitosamente")

if __name__ == "__main__":
    init_roles_permissions()