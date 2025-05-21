# reset_database.py

import os
import sys
import subprocess
import time
import pymysql
from getpass import getpass
import pandas as pd
from io import StringIO

# Colores para la salida en consola
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}\n")

def print_step(text):
    print(f"{Colors.BLUE}>> {text}...{Colors.ENDC}")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.ENDC}")

def print_warning(text):
    print(f"{Colors.WARNING}! {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.FAIL}✗ ERROR: {text}{Colors.ENDC}")

def execute_command(command, success_message=None, error_message=None):
    """Ejecuta un comando y muestra mensajes de éxito o error."""
    try:
        result = subprocess.run(command, shell=True, check=True, 
                                capture_output=True, text=True)
        if success_message:
            print_success(success_message)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        if error_message:
            print_error(f"{error_message}: {e}")
            print(f"Salida: {e.stdout}")
            print(f"Error: {e.stderr}")
        return False, e.stderr
    except Exception as e:
        if error_message:
            print_error(f"{error_message}: {str(e)}")
        return False, str(e)

def get_db_config():
    """Obtiene la configuración de la base de datos desde config.py o entrada del usuario."""
    print_step("Configurando conexión a la base de datos")
    
    # Intentar leer desde config.py
    db_config = {
        'host': 'localhost',
        'user': 'root',
        'password': '',
        'db_name': 'cpc_optimized'
    }
    
    try:
        with open('config.py', 'r') as file:
            content = file.read()
            
            # Buscar DB_USER
            user_match = re.search(r"DB_USER\s*=\s*os\.environ\.get\('DB_USER',\s*'([^']*)'\)", content)
            if user_match:
                db_config['user'] = user_match.group(1)
            
            # Buscar DB_PASSWORD
            pass_match = re.search(r"DB_PASSWORD\s*=\s*(?:quote_plus\()?os\.environ\.get\('DB_PASSWORD',\s*'([^']*)'\)", content)
            if pass_match:
                db_config['password'] = pass_match.group(1)
            
            # Buscar DB_HOST
            host_match = re.search(r"DB_HOST\s*=\s*os\.environ\.get\('DB_HOST',\s*'([^']*)'\)", content)
            if host_match:
                db_config['host'] = host_match.group(1)
            
            # Buscar DB_NAME
            name_match = re.search(r"DB_NAME\s*=\s*os\.environ\.get\('DB_NAME',\s*'([^']*)'\)", content)
            if name_match:
                db_config['db_name'] = name_match.group(1)
        
        print_success(f"Configuración leída desde config.py: {db_config['user']}@{db_config['host']}/{db_config['db_name']}")
    except Exception as e:
        print_warning(f"No se pudo leer la configuración desde config.py: {str(e)}")
    
    # Confirmar o modificar la configuración
    print("\nConfirme o modifique la configuración de la base de datos:")
    db_config['host'] = input(f"Host [{db_config['host']}]: ") or db_config['host']
    db_config['user'] = input(f"Usuario [{db_config['user']}]: ") or db_config['user']
    db_config['password'] = getpass(f"Contraseña [Dejar vacío para usar '{db_config['password']}']: ") or db_config['password']
    db_config['db_name'] = input(f"Nombre de la base de datos [{db_config['db_name']}]: ") or db_config['db_name']
    
    return db_config

def reset_database(db_config):
    """Elimina y recrea la base de datos."""
    print_header("PASO 1: ELIMINAR Y RECREAR LA BASE DE DATOS")
    
    try:
        # Conectar a MySQL sin seleccionar una base de datos específica
        print_step("Conectando al servidor MySQL")
        conn = pymysql.connect(
            host=db_config['host'],
            user=db_config['user'],
            password=db_config['password']
        )
        cursor = conn.cursor()
        print_success("Conexión exitosa al servidor MySQL")
        
        # Eliminar la base de datos si existe
        print_step(f"Eliminando base de datos '{db_config['db_name']}' si existe")
        cursor.execute(f"DROP DATABASE IF EXISTS `{db_config['db_name']}`")
        print_success(f"Base de datos '{db_config['db_name']}' eliminada (si existía)")
        
        # Crear la nueva base de datos
        print_step(f"Creando nueva base de datos '{db_config['db_name']}'")
        cursor.execute(
            f"CREATE DATABASE `{db_config['db_name']}` "
            f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        print_success(f"Base de datos '{db_config['db_name']}' creada exitosamente")
        
        # Cerrar la conexión
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print_error(f"Error al resetear la base de datos: {str(e)}")
        return False

def setup_virtual_env():
    """Configura el entorno virtual si no está activado."""
    print_header("VERIFICANDO ENTORNO VIRTUAL")
    
    # Comprobar si el entorno virtual está activado
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print_success("Entorno virtual ya está activado")
        return True
    
    print_warning("Entorno virtual no detectado")
    
    # Verificar si existe el directorio venv
    if os.path.exists('venv'):
        venv_path = 'venv'
    elif os.path.exists('ENV'):
        venv_path = 'ENV'
    else:
        print_step("Creando un nuevo entorno virtual")
        success, _ = execute_command(
            "python -m venv venv", 
            "Entorno virtual creado exitosamente",
            "Error al crear el entorno virtual"
        )
        if not success:
            return False
        venv_path = 'venv'
    
    # Instruir al usuario para activar manualmente el entorno virtual
    print_warning("Por favor, active el entorno virtual manualmente y vuelva a ejecutar este script")
    
    if os.name == 'nt':  # Windows
        print(f"\nEjecute: {venv_path}\\Scripts\\activate\n")
    else:  # Unix/Linux/Mac
        print(f"\nEjecute: source {venv_path}/bin/activate\n")
    
    sys.exit(0)

def apply_migrations():
    """Aplica las migraciones de la base de datos."""
    print_header("PASO 2: APLICAR MIGRACIONES")
    
    print_step("Verificando dependencias de Flask")
    try:
        import flask
        import flask_migrate
        print_success("Dependencias de Flask encontradas")
    except ImportError as e:
        print_error(f"Dependencia faltante: {str(e)}")
        print_step("Instalando dependencias")
        execute_command(
            "pip install -r requirements.txt",
            "Dependencias instaladas correctamente",
            "Error al instalar dependencias"
        )
    
    print_step("Aplicando migraciones")
    success, _ = execute_command(
        "flask db upgrade", 
        "Migraciones aplicadas exitosamente",
        "Error al aplicar migraciones"
    )
    
    if not success:
        print_warning("Intentando reiniciar las migraciones...")
        execute_command("flask db stamp head", "Base de migraciones reseteada")
        execute_command("flask db migrate", "Migraciones generadas")
        success, _ = execute_command(
            "flask db upgrade", 
            "Migraciones aplicadas exitosamente",
            "Error al aplicar migraciones"
        )
    
    return success

def initialize_basic_data():
    """Inicializa los datos básicos del sistema."""
    print_header("PASO 3: INICIALIZAR DATOS BÁSICOS")
    
    print_step("Inicializando base de datos con datos esenciales")
    success, _ = execute_command(
        "flask init-db", 
        "Datos básicos inicializados correctamente",
        "Error al inicializar datos básicos"
    )
    
    if success:
        print_success("Usuario administrador creado:")
        print("  Username: admin")
        print("  Password: admin123")
    
    return success

def create_master_data():
    """Crea datos maestros esenciales."""
    print_header("PASO 4: CREAR DATOS MAESTROS ESENCIALES")
    
    # Crear datos de ejemplo para importar
    print_step("Generando datos maestros de ejemplo")
    
    # Crear directorio temporal para archivos
    os.makedirs('temp_data', exist_ok=True)
    
    # Crear archivo de variedades
    variedades_data = {
        'FLOR': ['DAISY', 'NOVELTY', 'NOVELTY', 'ALSTROEMERIA', 'CHRYSANTHEMUM'],
        'COLOR': ['RED', 'YELLOW', 'GREEN', 'ORANGE', 'WHITE'],
        'VARIEDAD': ['VALENTINO', 'ZIPPO', 'BOTANI', 'FANTASY', 'CLASSIC']
    }
    variedades_df = pd.DataFrame(variedades_data)
    variedades_df.to_excel('temp_data/variedades.xlsx', index=False)
    print_success("Archivo de variedades generado en temp_data/variedades.xlsx")
    
    # Crear archivo de bloques y camas
    bloques_data = []
    for bloque in range(1, 4):
        for cama in range(1, 6):
            for lado in ['A', 'B']:
                bloques_data.append({
                    'BLOQUE': str(bloque),
                    'CAMA': str(cama),
                    'LADO': lado
                })
    bloques_df = pd.DataFrame(bloques_data)
    bloques_df.to_excel('temp_data/bloques.xlsx', index=False)
    print_success("Archivo de bloques generado en temp_data/bloques.xlsx")
    
    # Crear densidades básicas
    print_step("Generando script SQL para densidades básicas")
    densidades_sql = """
    INSERT INTO densidades (densidad, valor) VALUES
    ('BAJA', 1.0),
    ('MEDIA', 1.5),
    ('ALTA', 2.0),
    ('MUY ALTA', 2.5);
    """
    
    with open('temp_data/densidades.sql', 'w') as f:
        f.write(densidades_sql)
    
    print_success("Script SQL para densidades generado en temp_data/densidades.sql")
    
    # Instruir al usuario sobre cómo importar estos datos
    print("\nPara importar estos datos maestros, tienes dos opciones:")
    print("\n1. A través de la interfaz web:")
    print("   - Inicia la aplicación con: python run.py")
    print("   - Accede a http://localhost:5000 e inicia sesión como admin/admin123")
    print("   - Ve a 'Datos Maestros' > 'Importar Datasets' para importar los archivos Excel")
    print("   - Ve a 'Datos Maestros' > 'Densidades' para crear las densidades manualmente")
    
    print("\n2. Importar directamente a la base de datos:")
    print_step("Importando densidades directamente a la base de datos")
    
    try:
        conn = pymysql.connect(
            host=db_config['host'],
            user=db_config['user'],
            password=db_config['password'],
            db=db_config['db_name']
        )
        cursor = conn.cursor()
        
        # Importar densidades
        with open('temp_data/densidades.sql', 'r') as f:
            sql = f.read()
            for statement in sql.split(';'):
                if statement.strip():
                    cursor.execute(statement)
        
        conn.commit()
        cursor.close()
        conn.close()
        print_success("Densidades importadas directamente a la base de datos")
        
        return True
    except Exception as e:
        print_error(f"Error al importar datos maestros directamente: {str(e)}")
        print_warning("Por favor, utiliza la opción de importación a través de la interfaz web")
        return False

def main():
    """Función principal que ejecuta todos los pasos del proceso."""
    print_header("REINICIO COMPLETO DE LA BASE DE DATOS")
    print_warning("ADVERTENCIA: Este proceso eliminará TODOS los datos existentes")
    
    confirmation = input("¿Está seguro de que desea continuar? (s/N): ").lower()
    if confirmation != 's':
        print("Operación cancelada.")
        return
    
    # Paso 0: Configurar entorno
    setup_virtual_env()
    
    # Paso 0.5: Obtener configuración de la base de datos
    global db_config
    db_config = get_db_config()
    
    # Paso 1: Resetear la base de datos
    if not reset_database(db_config):
        print_error("No se pudo resetear la base de datos. Abortando.")
        return
    
    # Paso 2: Aplicar migraciones
    if not apply_migrations():
        print_error("Error al aplicar migraciones. Abortando.")
        return
    
    # Paso 3: Inicializar datos básicos
    if not initialize_basic_data():
        print_error("Error al inicializar datos básicos. Abortando.")
        return
    
    # Paso 4: Crear datos maestros esenciales
    create_master_data()
    
    print_header("PROCESO COMPLETADO")
    print_success("La base de datos ha sido reiniciada exitosamente")
    print("\nPuedes iniciar la aplicación con:")
    print("  python run.py")
    print("\nE iniciar sesión con:")
    print("  Usuario: admin")
    print("  Contraseña: admin123")

if __name__ == "__main__":
    import re  # Importamos re para usar expresiones regulares en get_db_config
    main()