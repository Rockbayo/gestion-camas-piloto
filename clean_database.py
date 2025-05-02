# clean_database.py
from app import create_app, db
from sqlalchemy import inspect, text

def drop_all_tables():
    app = create_app()
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

if __name__ == "__main__":
    drop_all_tables()