#!/usr/bin/env python3
"""
Script para Borrar Todos los Datos de Siembras - Sistema de Gestión de Camas Piloto

ADVERTENCIA: Este script elimina permanentemente TODOS los datos de siembras, cortes
y registros relacionados del sistema. La operación es IRREVERSIBLE.

Utilícelo solo en entornos donde sea absolutamente necesario eliminar 
todos los datos y comenzar desde cero.

Funcionalidades:
1. Elimina todos los registros de cortes
2. Elimina todos los registros de siembras
3. Opcionalmente puede reiniciar los contadores de autoincremento
4. Puede crear respaldo antes de eliminar (recomendado)
5. Verifica requisitos y pide confirmaciones de seguridad
"""

import os
import sys
import time
import sqlite3
import argparse
import logging
import shutil
from datetime import datetime
from pathlib import Path

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("reset_data.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("reset_siembras")

# Definir las tablas a vaciar (en orden para respetar restricciones de clave foránea)
TABLES_TO_EMPTY = [
    "cortes",           # Primero cortes porque dependen de siembras
    "siembras"          # Luego siembras
]

# Tablas relacionadas que pueden tener registros huérfanos (opcional)
RELATED_TABLES = [
    "areas",            # Áreas relacionadas con siembras
    "densidades"        # Densidades relacionadas con siembras
]

class DatabaseResetter:
    """Clase para manejar el reinicio de datos en la base de datos"""
    
    def __init__(self, db_path, backup=True, reset_autoincrement=False, reset_related=False):
        self.db_path = db_path
        self.backup = backup
        self.reset_autoincrement = reset_autoincrement
        self.reset_related = reset_related
        self.conn = None
        self.backup_path = None
    
    def create_backup(self):
        """Crea una copia de seguridad de la base de datos antes de modificarla"""
        if not self.backup:
            logger.info("Omitiendo creación de respaldo según las opciones seleccionadas.")
            return True
        
        try:
            # Crear nombre de respaldo con timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = Path("backups")
            backup_dir.mkdir(exist_ok=True)
            
            self.backup_path = backup_dir / f"app_db_backup_{timestamp}.db"
            
            # Crear copia de seguridad
            logger.info(f"Creando respaldo en: {self.backup_path}")
            shutil.copy2(self.db_path, self.backup_path)
            
            # Verificar que la copia se haya creado correctamente
            if not self.backup_path.exists():
                raise Exception("No se pudo crear el archivo de respaldo")
                
            logger.info(f"Respaldo creado correctamente: {self.backup_path}")
            return True
        except Exception as e:
            logger.error(f"Error al crear respaldo: {e}")
            return False
    
    def connect(self):
        """Establece la conexión a la base de datos"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            # Activar soporte de claves foráneas para garantizar integridad referencial
            self.conn.execute("PRAGMA foreign_keys = ON")
            return True
        except Exception as e:
            logger.error(f"Error al conectar a la base de datos: {e}")
            return False
    
    def get_table_counts(self):
        """Obtiene conteo de registros en las tablas relevantes"""
        counts = {}
        try:
            cursor = self.conn.cursor()
            for table in TABLES_TO_EMPTY + RELATED_TABLES:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                counts[table] = count
            return counts
        except Exception as e:
            logger.error(f"Error al obtener conteo de tablas: {e}")
            return {}
        
    def empty_tables(self):
        """Elimina los registros de las tablas especificadas"""
        try:
            cursor = self.conn.cursor()
            
            # Guardar conteo previo para reporte
            prev_counts = self.get_table_counts()
            
            # Eliminar registros de las tablas principales
            for table in TABLES_TO_EMPTY:
                logger.info(f"Eliminando registros de la tabla {table}...")
                cursor.execute(f"DELETE FROM {table}")
                logger.info(f"Eliminados {cursor.rowcount} registros de {table}")
            
            # Si está habilitado, también eliminar registros en tablas relacionadas
            if self.reset_related:
                for table in RELATED_TABLES:
                    logger.info(f"Eliminando registros de la tabla relacionada {table}...")
                    cursor.execute(f"DELETE FROM {table}")
                    logger.info(f"Eliminados {cursor.rowcount} registros de {table}")
            
            # Si está habilitado, reiniciar contadores de autoincremento
            if self.reset_autoincrement:
                for table in TABLES_TO_EMPTY + (RELATED_TABLES if self.reset_related else []):
                    # SQLite usa la siguiente sentencia para reiniciar el autoincremento
                    cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}'")
                    logger.info(f"Reiniciado autoincremento para tabla {table}")
            
            # Confirmar los cambios
            self.conn.commit()
            
            # Reportar resultado
            current_counts = self.get_table_counts()
            for table, prev_count in prev_counts.items():
                current = current_counts.get(table, 0)
                logger.info(f"Tabla {table}: {prev_count} registros antes, {current} registros después")
            
            return True
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error al vaciar tablas: {e}")
            return False
    
    def vacuum_database(self):
        """Ejecuta VACUUM para liberar espacio y optimizar la base de datos"""
        try:
            before_size = os.path.getsize(self.db_path)
            
            logger.info("Ejecutando VACUUM para optimizar la base de datos...")
            self.conn.execute("VACUUM")
            
            after_size = os.path.getsize(self.db_path)
            size_diff = before_size - after_size
            
            logger.info(f"Base de datos optimizada.")
            logger.info(f"Tamaño anterior: {before_size/1024:.2f} KB")
            logger.info(f"Tamaño actual: {after_size/1024:.2f} KB")
            if before_size > 0:
                logger.info(f"Espacio liberado: {size_diff/1024:.2f} KB ({size_diff/before_size*100:.2f}% reducción)")
            
            return True
        except Exception as e:
            logger.error(f"Error al ejecutar VACUUM: {e}")
            return False
    
    def close(self):
        """Cierra la conexión a la base de datos"""
        if self.conn:
            self.conn.close()
            logger.info("Conexión a la base de datos cerrada")

def parse_arguments():
    """Configura y parsea argumentos de línea de comandos"""
    parser = argparse.ArgumentParser(
        description='Elimina todos los datos de siembras y cortes del sistema.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
ADVERTENCIA: Este script eliminará permanentemente TODOS los datos de siembras y cortes.
Esta operación es IRREVERSIBLE y debe usarse con extrema precaución.
Se recomienda realizar un respaldo completo antes de ejecutar este script.
        """
    )
    parser.add_argument('--db-path', default='app.db', help='Ruta al archivo de base de datos (por defecto: app.db)')
    parser.add_argument('--no-backup', action='store_true', help='Omitir la creación de respaldo (NO RECOMENDADO)')
    parser.add_argument('--reset-autoincrement', action='store_true', help='Reiniciar contadores de autoincremento')
    parser.add_argument('--reset-related', action='store_true', help='También vaciar tablas relacionadas (areas, densidades)')
    parser.add_argument('--force', action='store_true', help='Omitir confirmaciones de seguridad (PELIGROSO)')
    
    return parser.parse_args()

def confirm_reset():
    """Solicita confirmación explícita del usuario antes de proceder"""
    print("\n" + "="*80)
    print("                     ¡¡¡ ADVERTENCIA DE SEGURIDAD !!!")
    print("="*80)
    print("\nEste script eliminará PERMANENTEMENTE los siguientes datos:")
    print("  - TODOS los registros de cortes")
    print("  - TODAS las siembras")
    if args.reset_related:
        print("  - TODAS las áreas y densidades")
    if args.reset_autoincrement:
        print("  - Reiniciará los contadores de autoincremento (IDs empezarán desde 1)")
    
    print("\nEsta operación NO SE PUEDE DESHACER.")
    
    # Corregido: Cambio de args.backup a no args.no_backup
    if args.no_backup:
        print("\n⚠️  NO se está creando respaldo según las opciones seleccionadas ⚠️")
    
    print("\nPara confirmar esta acción, escriba 'BORRAR TODO' (en mayúsculas):")
    confirmation = input("> ")
    
    if confirmation == "BORRAR TODO":
        print("\n✓ Confirmación recibida. Procediendo con el borrado...")
        return True
    else:
        print("\n✗ Confirmación incorrecta. Operación cancelada por seguridad.")
        return False

def main():
    """Función principal"""
    global args
    args = parse_arguments()
    
    # Verificar que estamos en la raíz del proyecto
    if not Path("app").exists() or not Path("run.py").exists():
        # Si no encontramos los archivos, podríamos estar en otra ubicación
        # Informamos al usuario pero continuamos (por si tiene una estructura diferente)
        logger.warning("No se encontraron los archivos típicos del proyecto Flask.")
        logger.warning("Asegúrese de ejecutar este script desde la raíz del proyecto.")
        
        # Preguntar si desea continuar a pesar de la advertencia
        print("\n⚠️ No se encontraron los archivos del proyecto Flask.")
        print("¿Desea continuar de todas formas? (s/n):")
        if input("> ").lower() != 's':
            return 1
    
    # Verificar existencia de la base de datos
    if not Path(args.db_path).exists():
        logger.error(f"No se encontró la base de datos en: {args.db_path}")
        # Preguntar por ruta alternativa
        print("\nIngrese la ruta correcta a la base de datos (o deje en blanco para cancelar):")
        alt_path = input("> ")
        if not alt_path or not Path(alt_path).exists():
            logger.error("Base de datos no encontrada. Operación cancelada.")
            return 1
        args.db_path = alt_path
    
    # Obtener confirmación del usuario (a menos que se use --force)
    if not args.force and not confirm_reset():
        return 1
    
    # Ejecutar el proceso de reinicio
    start_time = time.time()
    logger.info(f"Iniciando proceso de reinicio de datos en {args.db_path}")
    
    # Crear instancia de DatabaseResetter con las opciones especificadas
    resetter = DatabaseResetter(
        db_path=args.db_path,
        backup=not args.no_backup,
        reset_autoincrement=args.reset_autoincrement,
        reset_related=args.reset_related
    )
    
    # Crear respaldo si está habilitado
    if not args.no_backup:
        if not resetter.create_backup():
            logger.error("Error al crear respaldo. Abortando por seguridad.")
            return 1
    
    # Conectar a la base de datos
    if not resetter.connect():
        logger.error("Error al conectar a la base de datos. Operación abortada.")
        return 1
    
    # Mostrar conteo antes de reiniciar
    initial_counts = resetter.get_table_counts()
    logger.info("Conteo inicial de registros:")
    for table, count in initial_counts.items():
        logger.info(f"  - {table}: {count} registros")
    
    # Vaciar tablas
    success = resetter.empty_tables()
    if not success:
        logger.error("Error al vaciar tablas. Operación incompleta.")
        resetter.close()
        return 1
    
    # Ejecutar VACUUM para optimizar
    resetter.vacuum_database()
    
    # Cerrar conexión
    resetter.close()
    
    # Mostrar resumen final
    execution_time = time.time() - start_time
    logger.info("\n" + "="*50)
    logger.info("RESUMEN DE REINICIO DE DATOS")
    logger.info("="*50)
    for table, count in initial_counts.items():
        if table in TABLES_TO_EMPTY or (table in RELATED_TABLES and args.reset_related):
            logger.info(f"Tabla {table}: {count} registros eliminados")
    
    if not args.no_backup and resetter.backup_path:
        logger.info(f"Respaldo creado en: {resetter.backup_path}")
    
    logger.info(f"Autoincrement reiniciado: {'Sí' if args.reset_autoincrement else 'No'}")
    logger.info(f"Tiempo de ejecución: {execution_time:.2f} segundos")
    logger.info("="*50)
    
    print("\n✅ Operación completada con éxito.")
    print("Se han eliminado todos los datos de siembras y cortes del sistema.")
    print("El sistema está listo para comenzar desde cero.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())