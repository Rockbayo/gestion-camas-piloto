"""
Script para crear un usuario administrador en la base de datos.
Ejecutar con Python después de haber configurado la base de datos.
"""

from app import create_app, db
from app.models import Usuario, Documento
from werkzeug.security import generate_password_hash

app = create_app()

def main():
    """Crear usuario administrador y documentos iniciales."""
    with app.app_context():
        # Verificar si existen documentos
        documento = Documento.query.first()
        if not documento:
            print("Creando tipos de documento base...")
            doc1 = Documento(documento="Cedula de Ciudadania")
            doc2 = Documento(documento="Pasaporte")
            db.session.add(doc1)
            db.session.add(doc2)
            db.session.commit()
            documento = doc1
            print("Tipos de documento creados!")
        
        # Verificar si existe algún usuario administrador
        admin = Usuario.query.filter_by(is_admin=True).first()
        if admin:
            print(f"Ya existe un usuario administrador: {admin.nombre_completo}")
            return
        
        # Solicitar datos para el nuevo administrador
        print("\n=== CREACIÓN DE USUARIO ADMINISTRADOR ===")
        print("Por favor ingrese los datos del administrador:")
        
        nombre_1 = input("Primer nombre: ")
        nombre_2 = input("Segundo nombre (opcional, presione Enter para omitir): ") or None
        apellido_1 = input("Primer apellido: ")
        apellido_2 = input("Segundo apellido (opcional, presione Enter para omitir): ") or None
        cargo = input("Cargo: ")
        num_doc = int(input("Número de documento: "))
        
        # Listar documentos disponibles
        documentos = Documento.query.all()
        print("\nTipos de documento disponibles:")
        for doc in documentos:
            print(f"{doc.doc_id}: {doc.documento}")
        
        documento_id = int(input("\nSeleccione el tipo de documento (número): "))
        
        # Solicitar contraseña
        password = input("Contraseña: ")
        
        # Crear usuario administrador
        admin = Usuario(
            nombre_1=nombre_1,
            nombre_2=nombre_2,
            apellido_1=apellido_1,
            apellido_2=apellido_2,
            cargo=cargo,
            num_doc=num_doc,
            documento_id=documento_id,
            password_hash=generate_password_hash(password),
            is_admin=True
        )
        
        db.session.add(admin)
        db.session.commit()
        
        print(f"\n¡Usuario administrador {admin.nombre_completo} creado con éxito!")
        print("Ahora puede iniciar sesión en el sistema.")

if __name__ == "__main__":
    main()