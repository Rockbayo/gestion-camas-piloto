#!/usr/bin/env python3
"""
Script para ajustar los días de ciclo de las variedades a valores realistas.
Este script modifica el cálculo de días de ciclo y actualiza las visualizaciones.

Uso: python ajustar_dias_ciclo.py [dias_max_ciclo]
"""

import os
import sys
import click
from datetime import datetime, timedelta
from sqlalchemy import text, func

# Ajustar la ruta para importar la aplicación
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Valor por defecto para días máximos de ciclo
DIAS_MAX_CICLO_DEFAULT = 180  # 6 meses como máximo por defecto

def obtener_dias_max_ciclo():
    """Obtiene el número máximo de días de ciclo desde los argumentos o usa el valor por defecto"""
    if len(sys.argv) > 1:
        try:
            return int(sys.argv[1])
        except ValueError:
            click.echo(f"Valor inválido para días máximos: {sys.argv[1]}")
            click.echo(f"Se usará el valor por defecto: {DIAS_MAX_CICLO_DEFAULT}")
    return DIAS_MAX_CICLO_DEFAULT

def modificar_calculo_dias_ciclo(dias_max_ciclo):
    """
    Modifica la vista que calcula los días de ciclo para limitar a un valor máximo.
    Esto afecta directamente a la visualización de las curvas de producción.
    """
    from app import create_app, db
    
    app = create_app()
    
    with app.app_context():
        try:
            # Eliminar vista existente si existe
            db.session.execute(text("DROP VIEW IF EXISTS vista_produccion_por_dia"))
            
            # Crear vista con límite de días de ciclo
            sql_vista = f"""
            CREATE VIEW vista_produccion_por_dia AS
            SELECT 
                v.variedad_id,
                LEAST(DATEDIFF(c.fecha_corte, s.fecha_siembra), {dias_max_ciclo}) AS dias_desde_siembra,
                v.variedad,
                f.flor,
                cl.color,
                AVG(c.cantidad_tallos / (a.area * d.valor) * 100) AS promedio_tallos
            FROM 
                cortes c
                JOIN siembras s ON c.siembra_id = s.siembra_id
                JOIN variedades v ON s.variedad_id = v.variedad_id
                JOIN flor_color fc ON v.flor_color_id = fc.flor_color_id
                JOIN flores f ON fc.flor_id = f.flor_id
                JOIN colores cl ON fc.color_id = cl.color_id
                JOIN areas a ON s.area_id = a.area_id
                JOIN densidades d ON s.densidad_id = d.densidad_id
            WHERE 
                DATEDIFF(c.fecha_corte, s.fecha_siembra) <= {dias_max_ciclo}
            GROUP BY 
                v.variedad_id, 
                dias_desde_siembra,
                v.variedad,
                f.flor,
                cl.color;
            """
            
            db.session.execute(text(sql_vista))
            db.session.commit()
            
            click.echo(f"Vista actualizada exitosamente con límite de {dias_max_ciclo} días")
            return True
        except Exception as e:
            click.echo(f"Error al actualizar vista: {str(e)}")
            return False

def ajustar_fecha_corte_existentes(dias_max_ciclo):
    """
    Revisa los cortes existentes y ajusta las fechas que exceden el máximo de días de ciclo.
    Esto modifica los datos históricos para que sean más realistas.
    """
    from app import create_app, db
    from app.models import Siembra, Corte
    
    app = create_app()
    
    with app.app_context():
        try:
            # Obtener todos los cortes que exceden el máximo de días
            cortes_excesivos = db.session.query(Corte, Siembra)\
                .join(Siembra, Corte.siembra_id == Siembra.siembra_id)\
                .filter(func.datediff(Corte.fecha_corte, Siembra.fecha_siembra) > dias_max_ciclo)\
                .all()
            
            total_cortes = len(cortes_excesivos)
            if total_cortes == 0:
                click.echo("No se encontraron cortes que excedan el límite de días")
                return True
                
            click.echo(f"Se encontraron {total_cortes} cortes que exceden el límite de {dias_max_ciclo} días")
            
            # Preguntar si se desea ajustar las fechas
            if not click.confirm("¿Desea ajustar las fechas de estos cortes?", default=True):
                click.echo("No se realizaron cambios")
                return False
            
            # Ajustar fechas
            cortes_ajustados = 0
            for corte, siembra in cortes_excesivos:
                fecha_limite = siembra.fecha_siembra + timedelta(days=dias_max_ciclo)
                corte.fecha_corte = fecha_limite
                cortes_ajustados += 1
                
                # Mostrar progreso cada 10 cortes
                if cortes_ajustados % 10 == 0 or cortes_ajustados == total_cortes:
                    click.echo(f"Ajustados {cortes_ajustados}/{total_cortes} cortes...")
            
            db.session.commit()
            click.echo(f"Se ajustaron {cortes_ajustados} cortes exitosamente")
            return True
            
        except Exception as e:
            db.session.rollback()
            click.echo(f"Error al ajustar fechas de cortes: {str(e)}")
            return False

def modificar_funcion_dias_ciclo():
    """
    Modifica el método dias_ciclo en el modelo Siembra para limitar los días a un valor realista.
    Añade validación para evitar que las nuevas siembras muestren valores excesivos.
    """
    from app import create_app, db
    
    app = create_app()
    
    with app.app_context():
        try:
            # Esta modificación requiere cambios en el archivo app/models.py
            # No se puede hacer directamente con SQL, mostraremos las instrucciones
            click.echo("\nPara completar la mejora, debe modificar manualmente el archivo app/models.py:")
            click.echo("\n1. Busque el método 'dias_ciclo' en la clase Siembra")
            click.echo("\n2. Reemplace el método actual por:")
            
            codigo_nuevo = """
    @hybrid_property
    def dias_ciclo(self):
        \"\"\"Calcula días desde la siembra hasta hoy o hasta el último corte, con límite máximo\"\"\"
        if self.cortes:
            ultima_fecha = max([corte.fecha_corte for corte in self.cortes])
            # Obtener la diferencia en días con límite máximo
            dias = (ultima_fecha - self.fecha_siembra).days
            # Limitar a un máximo de 180 días (aproximadamente 6 meses)
            return min(dias, 180)
        else:
            # Si no hay cortes, usar la fecha actual pero limitada
            dias = (datetime.now().date() - self.fecha_siembra).days
            return min(dias, 180)
            """
            
            click.echo(codigo_nuevo)
            return True
        except Exception as e:
            click.echo(f"Error: {str(e)}")
            return False

def modificar_generador_curvas():
    """
    Proporciona instrucciones para modificar la generación de curvas de producción
    para que no muestren valores irreales.
    """
    click.echo("\nPara mejorar la generación de curvas de producción, debe modificar app/reportes/routes.py:")
    click.echo("\n1. Busque la función 'curva_produccion'")
    click.echo("\n2. Modifique la configuración de gráficos para limitar los días mostrados:")
    
    codigo_nuevo = """
    # Al generar el gráfico, limitar el rango del eje X a días realistas
    plt.figure(figsize=(10, 6))
    plt.scatter(dias, indices, color='blue', s=50, alpha=0.7, label='Datos históricos')
    plt.plot(dias, indices, 'b-', alpha=0.5)
    
    # Limitar el eje X a un máximo de días razonable
    max_dias = min(max(dias) if dias else 180, 180)  # No mostrar más de 180 días
    plt.xlim(0, max_dias)
        
    # Configurar gráfico
    plt.xlabel('Días desde siembra')
    plt.ylabel('Índice promedio (%)')
    """
    
    click.echo(codigo_nuevo)
    return True

def main():
    """Función principal"""
    click.echo("===== AJUSTE DE DÍAS DE CICLO =====")
    
    # Obtener el valor de días máximos
    dias_max_ciclo = obtener_dias_max_ciclo()
    click.echo(f"Se utilizará un máximo de {dias_max_ciclo} días para el ciclo de cultivo")
    
    # Ajustar la vista de producción por día
    click.echo("\n1. Ajustando vista de producción por día...")
    if not modificar_calculo_dias_ciclo(dias_max_ciclo):
        if not click.confirm("Hubo un error al ajustar la vista. ¿Desea continuar?", default=False):
            return
    
    # Ajustar fechas de cortes existentes
    click.echo("\n2. Revisando cortes con fechas excesivas...")
    ajustar_fecha_corte_existentes(dias_max_ciclo)
    
    # Instrucciones para modificar el modelo
    click.echo("\n3. Instrucciones para modificar el cálculo de días de ciclo...")
    modificar_funcion_dias_ciclo()
    
    # Instrucciones para modificar la generación de curvas
    click.echo("\n4. Instrucciones para mejorar la visualización de curvas...")
    modificar_generador_curvas()
    
    click.echo("\n===== AJUSTES COMPLETADOS =====")
    click.echo("\nRecuerde reiniciar la aplicación después de realizar estos cambios.")

if __name__ == "__main__":
    main()