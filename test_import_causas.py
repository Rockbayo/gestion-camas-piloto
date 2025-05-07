# test_import_causas.py
from app import create_app, db
from app.utils.dataset_importer import DatasetImporter
import pandas as pd
import os

def test_import():
    app = create_app()
    with app.app_context():
        # Crear un archivo CSV de prueba
        test_data = pd.DataFrame({
            'CAUSA': ['Cortos', 'Tallo Delgado', 'Prueba Causa']
        })
        
        # Guardar archivo temporal
        temp_file = 'test_causas.xlsx'
        test_data.to_excel(temp_file, index=False)
        
        # Intentar importar
        success, message, stats = DatasetImporter.import_causas(
            temp_file, 
            column_mapping={'CAUSA': 'CAUSA'}, 
            validate_only=False, 
            skip_first_row=True
        )
        
        # Mostrar resultados
        print(f"Éxito: {success}")
        print(f"Mensaje: {message}")
        print(f"Estadísticas: {stats}")
        
        # Limpiar
        if os.path.exists(temp_file):
            os.remove(temp_file)

if __name__ == "__main__":
    test_import()