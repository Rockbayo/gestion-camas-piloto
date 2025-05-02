# reset_database.py
import os
import importlib

def run_script(script_name):
    """Ejecuta un script importándolo"""
    print(f"Ejecutando script: {script_name}")
    try:
        script = importlib.import_module(script_name)
        if hasattr(script, 'main'):
            script.main()
        print(f"Script {script_name} ejecutado correctamente")
    except Exception as e:
        print(f"Error al ejecutar script {script_name}: {str(e)}")

def main():
    """Ejecuta todos los scripts en orden"""
    # Limpiar base de datos
    run_script("clean_database")
    
    # Inicializar roles y permisos
    run_script("init_roles_permissions")
    
    print("Base de datos reiniciada y configurada exitosamente")

if __name__ == "__main__":
    main()