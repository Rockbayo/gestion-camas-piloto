# test_import_causas.py
from app import create_app, db
from app.utils.dataset_importer import DatasetImporter
from app.models import Causa
import pandas as pd
import os
import traceback

def test_import():
    """Prueba la importación de causas con diferentes escenarios"""
    app = create_app()
    with app.app_context():
        # Contar causas existentes para la prueba
        try:
            print("Verificando causas existentes...")
            causas_antes = Causa.query.count()
            print(f"Causas antes de la prueba: {causas_antes}")
        except Exception as e:
            print(f"Error al verificar causas existentes: {str(e)}")
        
        # Crear un archivo Excel de prueba
        test_data = pd.DataFrame({
            'CAUSA': ['Cortos', 'Tallo Delgado', 'Prueba Causa']
        })
        
        # Guardar archivo temporal
        temp_file = 'test_causas.xlsx'
        test_data.to_excel(temp_file, index=False)
        
        try:
            print("\n*** Prueba 1: Importación normal ***")
            # Intentar importar con mapeo correcto
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
            
            # Verificar resultados en la base de datos
            causas_despues = Causa.query.count()
            print(f"Causas después de la importación: {causas_despues}")
            print(f"Nuevas causas añadidas: {causas_despues - causas_antes}")
            
            # Listar las causas
            causas = Causa.query.all()
            for causa in causas:
                print(f" - {causa.causa_id}: {causa.causa}")
        
        except Exception as e:
            print(f"Error en la prueba 1: {str(e)}")
            print(traceback.format_exc())
        
        # Limpiar
        if os.path.exists(temp_file):
            os.remove(temp_file)

if __name__ == "__main__":
    test_import()