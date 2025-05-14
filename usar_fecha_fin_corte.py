#!/usr/bin/env python3
"""
Script mejorado para usar la fecha de fin de corte proporcionada en el archivo histórico.
Esta versión usa la fecha explícita de fin de corte para calcular el ciclo real de cada variedad.

Uso: python usar_fecha_fin_corte.py
"""

import os
import sys
import click
from datetime import datetime, timedelta
from sqlalchemy import text, func, update

# Ajustar la ruta para importar la aplicación
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def actualizar_modelo_siembra():
    """
    Proporciona instrucciones para modificar el modelo Siembra 
    para usar la fecha de fin de corte en el cálculo del ciclo.
    """
    click.echo("\nPara modificar el modelo Siembra y utilizar la fecha de fin de corte:")
    click.echo("\n1. Edite el archivo app/models.py")
    click.echo("\n2. Busque la clase Siembra y añada un campo para almacenar la fecha de fin de corte:")
    
    codigo_nuevo_campo = """
    # Añadir este campo a la clase Siembra
    fecha_fin_corte = db.Column(db.Date)  # Fecha explícita de fin de corte
    """
    
    click.echo(codigo_nuevo_campo)
    
    click.echo("\n3. Modifique el método dias_ciclo para usar la fecha de fin de corte cuando esté disponible:")
    
    codigo_nuevo_metodo = """
    @hybrid_property
    def dias_ciclo(self):
        \"\"\"
        Calcula días desde la siembra hasta la fecha de fin de corte si está disponible,
        de lo contrario usa el último corte o la fecha actual.
        \"\"\"
        if self.fecha_fin_corte:
            # Si tenemos fecha explícita de fin de corte, usarla
            return (self.fecha_fin_corte - self.fecha_siembra).days
        elif self.cortes:
            # Si no hay fecha fin pero hay cortes, usar el último corte
            ultima_fecha = max([corte.fecha_corte for corte in self.cortes])
            return (ultima_fecha - self.fecha_siembra).days
        else:
            # Si no hay cortes, usar la fecha actual
            return (datetime.now().date() - self.fecha_siembra).days
    """
    
    click.echo(codigo_nuevo_metodo)
    return True

def modificar_importador_historico():
    """
    Proporciona instrucciones para modificar el importador histórico
    para que capture la fecha de fin de corte.
    """
    click.echo("\nPara modificar el importador histórico para capturar la fecha de fin de corte:")
    click.echo("\n1. Edite el archivo importar_mejorado.py")
    click.echo("\n2. Busque la sección donde se procesa la fecha de inicio de corte y añada:")
    
    codigo_nuevo = """
    # Obtener fecha fin de corte
    fecha_fin_corte = None
    fecha_fin_cols = ['FECHA FIN CORTE', 'FIN CORTE', 'FECHA FINAL']
    for col in fecha_fin_cols:
        if col in row.index and pd.notna(row[col]):
            try:
                fecha_fin_corte = pd.to_datetime(row[col]).date()
                break
            except:
                continue
    
    # Crear siembra
    siembra = Siembra(
        bloque_cama_id=bloque_cama.bloque_cama_id,
        variedad_id=variedad.variedad_id,
        area_id=area.area_id,
        densidad_id=densidad.densidad_id,
        fecha_siembra=fecha_siembra,
        fecha_inicio_corte=fecha_inicio_corte,
        fecha_fin_corte=fecha_fin_corte,  # Añadir fecha de fin de corte
        estado=estado,
        usuario_id=usuario_id,
        fecha_registro=datetime.now()
    )
    """
    
    click.echo(codigo_nuevo)
    return True

def crear_script_migracion():
    """
    Crea un script de migración para añadir la columna fecha_fin_corte
    a la tabla siembras en la base de datos.
    """
    click.echo("\nCreando script de migración para añadir la columna fecha_fin_corte...")
    
    script_content = """#!/usr/bin/env python3
\"\"\"
Script para añadir la columna fecha_fin_corte a la tabla siembras.
\"\"\"

import os
import sys
from sqlalchemy import text

# Ajustar la ruta para importar la aplicación
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app, db

def migrate_add_fecha_fin_corte():
    \"\"\"Añade la columna fecha_fin_corte a la tabla siembras\"\"\"
    app = create_app()
    
    with app.app_context():
        # Verificar si la columna ya existe
        try:
            result = db.session.execute(text("SHOW COLUMNS FROM siembras LIKE 'fecha_fin_corte'"))
            if result.rowcount == 0:
                # La columna no existe, crearla
                db.session.execute(text("ALTER TABLE siembras ADD COLUMN fecha_fin_corte DATE"))
                db.session.commit()
                print("Columna fecha_fin_corte añadida correctamente a la tabla siembras")
            else:
                print("La columna fecha_fin_corte ya existe en la tabla siembras")
        except Exception as e:
            db.session.rollback()
            print(f"Error al añadir columna: {str(e)}")

if __name__ == "__main__":
    migrate_add_fecha_fin_corte()
"""
    
    # Escribir el script a un archivo
    script_filename = "migrate_add_fecha_fin_corte.py"
    try:
        with open(script_filename, 'w') as f:
            f.write(script_content)
        
        # Hacer el script ejecutable
        os.chmod(script_filename, 0o755)
        
        click.echo(f"Script de migración creado: {script_filename}")
        click.echo(f"Para ejecutarlo: python {script_filename}")
        return True
    except Exception as e:
        click.echo(f"Error al crear script de migración: {str(e)}")
        return False

def actualizar_reportes_para_usar_fecha_fin():
    """
    Proporciona instrucciones para modificar las vistas y reportes
    para usar la fecha de fin de corte en los análisis.
    """
    click.echo("\nPara actualizar las vistas y reportes para usar la fecha de fin de corte:")
    click.echo("\n1. Edite el archivo app/reportes/routes.py")
    click.echo("\n2. Modifique la consulta en la función 'curva_produccion' para considerar la fecha de fin:")
    
    codigo_consulta = """
    # Al calcular los días para las curvas de producción
    dias_ciclo = None
    if siembra.fecha_fin_corte:
        # Si hay fecha de fin explícita, úsela
        dias_ciclo = (siembra.fecha_fin_corte - siembra.fecha_siembra).days
    else:
        # Si no hay fecha de fin, use el último corte
        dias_ciclo = siembra.dias_ciclo  # Usará el hybrid_property que ya calculamos
    """
    
    click.echo(codigo_consulta)
    
    click.echo("\n3. Si hay una vista SQL para vista_produccion_acumulada, modifíquela para incluir fecha_fin_corte:")
    
    sql_vista = """
    CREATE OR REPLACE VIEW vista_produccion_acumulada AS
    SELECT 
        s.siembra_id,
        b.bloque,
        ca.cama,
        l.lado,
        v.variedad,
        f.flor,
        cl.color,
        s.fecha_siembra,
        s.fecha_inicio_corte,
        s.fecha_fin_corte,  -- Añadir fecha_fin_corte
        SUM(c.cantidad_tallos) AS total_tallos,
        COUNT(c.corte_id) AS total_cortes,
        CASE 
            WHEN s.fecha_fin_corte IS NOT NULL THEN DATEDIFF(s.fecha_fin_corte, s.fecha_siembra)
            ELSE DATEDIFF(IFNULL(MAX(c.fecha_corte), CURDATE()), s.fecha_siembra)
        END AS dias_ciclo  -- Modificar para usar fecha_fin_corte si está disponible
    FROM 
        siembras s
        LEFT JOIN cortes c ON s.siembra_id = c.siembra_id
        JOIN variedades v ON s.variedad_id = v.variedad_id
        JOIN bloques_camas_lado bcl ON s.bloque_cama_id = bcl.bloque_cama_id
        JOIN bloques b ON bcl.bloque_id = b.bloque_id
        JOIN camas ca ON bcl.cama_id = ca.cama_id
        JOIN lados l ON bcl.lado_id = l.lado_id
        JOIN flor_color fc ON v.flor_color_id = fc.flor_color_id
        JOIN flores f ON fc.flor_id = f.flor_id
        JOIN colores cl ON fc.color_id = cl.color_id
    GROUP BY 
        s.siembra_id, b.bloque, ca.cama, l.lado, v.variedad, f.flor, cl.color,
        s.fecha_siembra, s.fecha_inicio_corte, s.fecha_fin_corte;
    """
    
    click.echo(sql_vista)
    return True

def main():
    """Función principal"""
    click.echo("===== IMPLEMENTACIÓN DE FECHA FIN DE CORTE =====")
    
    # Crear script de migración
    click.echo("\n1. Preparando migración de base de datos...")
    crear_script_migracion()
    
    # Instrucciones para modificar el modelo
    click.echo("\n2. Instrucciones para modificar el modelo Siembra...")
    actualizar_modelo_siembra()
    
    # Instrucciones para modificar el importador
    click.echo("\n3. Instrucciones para capturar la fecha de fin de corte...")
    modificar_importador_historico()
    
    # Instrucciones para actualizar reportes
    click.echo("\n4. Instrucciones para actualizar reportes y vistas...")
    actualizar_reportes_para_usar_fecha_fin()
    
    click.echo("\n===== INSTRUCCIONES COMPLETADAS =====")
    click.echo("\nPasos a seguir:")
    click.echo("1. Ejecute el script de migración: python migrate_add_fecha_fin_corte.py")
    click.echo("2. Realice las modificaciones indicadas en los archivos mencionados")
    click.echo("3. Actualice su importador histórico para capturar la fecha de fin de corte")
    click.echo("4. Ejecute nuevamente la importación de datos históricos")
    click.echo("5. Verifique los reportes y curvas para confirmar que ahora usan la fecha de fin de corte")

if __name__ == "__main__":
    main()