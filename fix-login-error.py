#!/usr/bin/env python3
"""
Script para corregir el error de importación de 'login' en models.py

Este script hace lo siguiente:
1. Comprueba y corrige app/__init__.py para definir correctamente login_manager y exportar login
2. Si es necesario, modifica app/models.py para ajustar la importación
"""

import os
import sys
import re
import shutil
from datetime import datetime

# Colores para la terminal
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'

def print_color(text, color):
    """Imprime texto con color"""
    print(f"{color}{text}{Colors.ENDC}")

def success(msg):
    """Imprime mensaje de éxito"""
    print_color(f"✓ {msg}", Colors.GREEN)

def warning(msg):
    """Imprime advertencia"""
    print_color(f"! {msg}", Colors.YELLOW)

def error(msg):
    """Imprime error"""
    print_color(f"✗ {msg}", Colors.RED)

def info(msg):
    """Imprime información"""
    print_color(f"ℹ {msg}", Colors.BLUE)

def backup_file(file_path):
    """Crea una copia de seguridad del archivo"""
    if not os.path.exists(file_path):
        error(f"El archivo {file_path} no existe")
        return None
    
    backup_dir = "backups"
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(backup_dir, f"{os.path.basename(file_path)}.{timestamp}")
    
    try:
        shutil.copy2(file_path, backup_file)
        success(f"Creada copia de seguridad: {backup_file}")
        return backup_file
    except Exception as e:
        error(f"Error al crear copia de seguridad: {str(e)}")
        return None

def fix_init_file():
    """Corrige el archivo __init__.py para definir login_manager y exportar login"""
    init_file = "app/__init__.py"
    
    if not os.path.exists(init_file):
        error(f"El archivo {init_file} no existe")
        return False
    
    # Crear copia de seguridad
    backup_file(init_file)
    
    # Leer contenido actual
    with open(init_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verificar si ya existe login_manager
    has_login_manager = "login_manager = LoginManager()" in content
    
    # Verificar importaciones necesarias
    has_login_manager_import = "from flask_login import LoginManager" in content
    
    # Preparar nuevas líneas según sea necesario
    new_lines = []
    
    if not has_login_manager_import:
        new_lines.append("from flask_login import LoginManager")
    
    # Verificar si se exporta login
    exports_login = "\nlogin = login_manager\n" in content or ", login" in content or "login," in content
    
    if not has_login_manager:
        new_lines.append("\n# Configuración de login")
        new_lines.append("login_manager = LoginManager()")
        new_lines.append("login_manager.login_view = 'auth.login'")
        new_lines.append("login_manager.login_message = 'Por favor inicie sesión para acceder a esta página'")
        new_lines.append("login_manager.login_message_category = 'info'")
    
    if not exports_login:
        new_lines.append("\n# Exportar login para compatibility con modelos")
        new_lines.append("login = login_manager\n")
    
    # Si no hay cambios que hacer, terminar
    if not new_lines:
        info("El archivo __init__.py ya está correcto")
        return True
    
    # Aplicar cambios
    try:
        # Encontrar el mejor lugar para insertar (después de importaciones o al final)
        if "import" in content:
            # Buscar la última importación
            import_matches = list(re.finditer(r'^from .+import .+$|^import .+$', content, re.MULTILINE))
            if import_matches:
                last_import = import_matches[-1]
                insertion_point = last_import.end()
                new_content = content[:insertion_point] + "\n" + "\n".join(new_lines) + content[insertion_point:]
            else:
                # No hay importaciones, añadir al principio
                new_content = "\n".join(new_lines) + "\n" + content
        else:
            # Archivo vacío o sin importaciones, añadir al principio
            new_content = "\n".join(new_lines) + "\n" + content
        
        # Verificar que login = login_manager esté presente
        if "login = login_manager" not in new_content:
            # Añadir al final si no se añadió antes
            new_content += "\n# Exportar login para models.py\nlogin = login_manager\n"
        
        # Guardar cambios
        with open(init_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        success(f"Se ha actualizado {init_file} correctamente")
        return True
    except Exception as e:
        error(f"Error al actualizar {init_file}: {str(e)}")
        return False

def fix_models_file():
    """Verifica y corrige el archivo models.py si es necesario"""
    models_file = "app/models.py"
    
    if not os.path.exists(models_file):
        error(f"El archivo {models_file} no existe")
        return False
    
    # Crear copia de seguridad
    backup_file(models_file)
    
    # Leer contenido actual
    with open(models_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verificar importación de login
    login_import_match = re.search(r'from app import ([^,\n]*,\s*)*login', content)
    
    if login_import_match:
        info("El archivo models.py ya importa login correctamente")
        return True
    
    # Buscar importación desde app
    app_import_match = re.search(r'from app import ([^\n]+)', content)
    
    if app_import_match:
        # Añadir login a la importación existente
        imports = app_import_match.group(1)
        if "db" in imports and "login" not in imports:
            new_imports = imports + ", login"
            new_content = content.replace(imports, new_imports)
            
            # Guardar cambios
            with open(models_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            success(f"Se ha actualizado la importación en {models_file}")
            return True
    
    # Si no se encontró importación desde app con db
    warning(f"No se encontró una importación adecuada en {models_file}")
    warning("El archivo puede necesitar una revisión manual")
    return False

def check_flask_login_installed():
    """Verifica si flask-login está instalado"""
    try:
        import flask_login
        success("flask-login está instalado")
        return True
    except ImportError:
        error("flask-login no está instalado")
        info("Instalando flask-login...")
        
        try:
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "flask-login"])
            success("flask-login instalado correctamente")
            return True
        except Exception as e:
            error(f"Error al instalar flask-login: {str(e)}")
            info("Por favor, instale flask-login manualmente: pip install flask-login")
            return False

def main():
    """Función principal"""
    print("\n===== CORRECCIÓN DE ERROR DE IMPORTACIÓN DE LOGIN =====\n")
    
    # Verificar que estamos en el directorio correcto
    if not os.path.exists("app") or not os.path.exists("run.py"):
        error("Este script debe ejecutarse desde el directorio raíz del proyecto")
        return 1
    
    # Verificar si flask-login está instalado
    check_flask_login_installed()
    
    # Corregir __init__.py
    if not fix_init_file():
        warning("No se pudo corregir app/__init__.py")
    
    # Corregir models.py
    if not fix_models_file():
        warning("No se pudo corregir app/models.py")
    
    print("\n===== CORRECCIONES COMPLETADAS =====\n")
    info("Intente ejecutar la aplicación nuevamente: python run.py")
    info("Si aún hay problemas, revise manualmente los archivos:")
    info("- app/__init__.py - Debe definir y exportar 'login'")
    info("- app/models.py - Debe importar 'login' desde app")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())