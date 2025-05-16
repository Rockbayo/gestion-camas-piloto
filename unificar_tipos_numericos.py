# unificar_tipos_numericos.py (versión corregida)

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
import sys

# Importar la aplicación
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from app import create_app, db

# Crear aplicación con contexto
app = create_app()

def ejecutar_migracion():
    with app.app_context():
        print("Iniciando unificación de tipos numéricos en la base de datos...")
        
        # Conexión directa para ejecutar SQL raw
        connection = db.engine.connect()
        
        try:
            # 1. Modificar los tipos numéricos en las tablas principales
            
            # Tabla áreas: Cambiar campo 'area' a DECIMAL(10,4)
            print("Modificando tabla 'areas'...")
            connection.execute(text("""
                ALTER TABLE areas 
                MODIFY COLUMN area DECIMAL(10,4) NOT NULL COMMENT 'Área en metros cuadrados';
            """))
            connection.commit()
            
            # Tabla densidades: Cambiar campo 'valor' a DECIMAL(10,4)
            print("Modificando tabla 'densidades'...")
            connection.execute(text("""
                ALTER TABLE densidades 
                MODIFY COLUMN valor DECIMAL(10,4) NOT NULL COMMENT 'Plantas por metro cuadrado';
            """))
            connection.commit()
            
            # Tabla cortes: Cambiar campo 'cantidad_tallos' a INTEGER
            print("Modificando tabla 'cortes'...")
            connection.execute(text("""
                ALTER TABLE cortes 
                MODIFY COLUMN cantidad_tallos INTEGER NOT NULL COMMENT 'Cantidad de tallos cortados';
            """))
            connection.commit()
            
            # 2. Crear funciones en la base de datos para cálculos consistentes
            print("Creando funciones de base de datos para cálculos consistentes...")
            
            # Eliminar función existente si hay
            print("Eliminando función existente calcular_indice_aprovechamiento...")
            connection.execute(text("DROP FUNCTION IF EXISTS calcular_indice_aprovechamiento;"))
            connection.commit()
            
            # Crear función para calcular índice de aprovechamiento
            print("Creando función calcular_indice_aprovechamiento...")
            connection.execute(text("""
                CREATE FUNCTION calcular_indice_aprovechamiento(
                    tallos INTEGER, 
                    plantas DECIMAL(10,4)
                ) RETURNS DECIMAL(10,2)
                DETERMINISTIC
                BEGIN
                    DECLARE indice DECIMAL(10,2);
                    
                    IF plantas <= 0 THEN
                        SET indice = 0;
                    ELSE
                        SET indice = (tallos / plantas) * 100;
                    END IF;
                    
                    RETURN ROUND(indice, 2);
                END;
            """))
            connection.commit()
            
            # Eliminar función existente si hay
            print("Eliminando función existente calcular_plantas_totales...")
            connection.execute(text("DROP FUNCTION IF EXISTS calcular_plantas_totales;"))
            connection.commit()
            
            # Crear función para calcular plantas totales
            print("Creando función calcular_plantas_totales...")
            connection.execute(text("""
                CREATE FUNCTION calcular_plantas_totales(
                    area DECIMAL(10,4), 
                    densidad DECIMAL(10,4)
                ) RETURNS INTEGER
                DETERMINISTIC
                BEGIN
                    DECLARE plantas INTEGER;
                    
                    SET plantas = ROUND(area * densidad);
                    
                    RETURN plantas;
                END;
            """))
            connection.commit()
            
            # 3. Crear vistas para datos calculados
            print("Creando vistas para datos calculados con tipos consistentes...")
            
            # Eliminar vista existente si hay
            print("Eliminando vista existente vista_indices_aprovechamiento...")
            connection.execute(text("DROP VIEW IF EXISTS vista_indices_aprovechamiento;"))
            connection.commit()
            
            # Crear vista para índices de aprovechamiento
            print("Creando vista vista_indices_aprovechamiento...")
            connection.execute(text("""
                CREATE VIEW vista_indices_aprovechamiento AS
                SELECT 
                    s.siembra_id,
                    s.variedad_id,
                    v.variedad,
                    SUM(c.cantidad_tallos) AS total_tallos,
                    a.area,
                    d.valor AS densidad,
                    calcular_plantas_totales(a.area, d.valor) AS total_plantas,
                    calcular_indice_aprovechamiento(
                        SUM(c.cantidad_tallos), 
                        calcular_plantas_totales(a.area, d.valor)
                    ) AS indice_aprovechamiento
                FROM 
                    siembras s
                    JOIN cortes c ON s.siembra_id = c.siembra_id
                    JOIN areas a ON s.area_id = a.area_id
                    JOIN densidades d ON s.densidad_id = d.densidad_id
                    JOIN variedades v ON s.variedad_id = v.variedad_id
                GROUP BY 
                    s.siembra_id, s.variedad_id, v.variedad, a.area, d.valor;
            """))
            connection.commit()
            
            # 4. Actualizar procedimientos almacenados
            print("Actualizando procedimientos almacenados...")
            
            # Eliminar procedimiento existente si hay
            print("Eliminando procedimiento existente registrar_corte...")
            connection.execute(text("DROP PROCEDURE IF EXISTS registrar_corte;"))
            connection.commit()
            
            # Crear procedimiento para registrar corte
            print("Creando procedimiento registrar_corte...")
            connection.execute(text("""
                CREATE PROCEDURE registrar_corte(
                    IN p_siembra_id INTEGER,
                    IN p_num_corte INTEGER,
                    IN p_fecha_corte DATE,
                    IN p_cantidad_tallos INTEGER,
                    IN p_usuario_id INTEGER
                )
                BEGIN
                    DECLARE plantas_totales DECIMAL(10,4);
                    DECLARE tallos_actuales INTEGER;
                    DECLARE area_siembra DECIMAL(10,4);
                    DECLARE densidad_valor DECIMAL(10,4);
                    
                    -- Obtener área y densidad de la siembra
                    SELECT a.area, d.valor INTO area_siembra, densidad_valor
                    FROM siembras s
                    JOIN areas a ON s.area_id = a.area_id
                    JOIN densidades d ON s.densidad_id = d.densidad_id
                    WHERE s.siembra_id = p_siembra_id;
                    
                    -- Calcular plantas totales
                    SET plantas_totales = calcular_plantas_totales(area_siembra, densidad_valor);
                    
                    -- Obtener tallos actuales
                    SELECT IFNULL(SUM(cantidad_tallos), 0) INTO tallos_actuales
                    FROM cortes
                    WHERE siembra_id = p_siembra_id;
                    
                    -- Verificar que no exceda el total de plantas
                    IF (tallos_actuales + p_cantidad_tallos) > plantas_totales THEN
                        SIGNAL SQLSTATE '45000'
                        SET MESSAGE_TEXT = 'La cantidad de tallos excede el total de plantas sembradas';
                    END IF;
                    
                    -- Insertar el corte
                    INSERT INTO cortes (
                        siembra_id, num_corte, fecha_corte, 
                        cantidad_tallos, usuario_id, fecha_registro
                    )
                    VALUES (
                        p_siembra_id, p_num_corte, p_fecha_corte, 
                        p_cantidad_tallos, p_usuario_id, NOW()
                    );
                    
                    -- Si es el primer corte, actualizar fecha_inicio_corte en la siembra
                    IF p_num_corte = 1 THEN
                        UPDATE siembras 
                        SET fecha_inicio_corte = p_fecha_corte
                        WHERE siembra_id = p_siembra_id 
                        AND fecha_inicio_corte IS NULL;
                    END IF;
                END;
            """))
            connection.commit()
            
            print("Migración de tipos de datos completada con éxito")
            
        except Exception as e:
            # Revertir en caso de error
            print(f"Error durante la migración: {str(e)}")
            raise
        finally:
            connection.close()

if __name__ == "__main__":
    ejecutar_migracion()