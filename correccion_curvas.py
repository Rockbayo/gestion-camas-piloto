#!/usr/bin/env python3
"""
Script para corregir inconsistencias en las curvas de producción
Ajusta el cálculo del ciclo productivo para que refleje el comportamiento real
"""
import os
import sys
import click
import subprocess
from datetime import datetime, timedelta

# Ajustar la ruta para importar la aplicación
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app, db
from app.models import Variedad, Siembra, Corte
from sqlalchemy import func, desc

def calcular_ciclos_reales():
    """Calcula ciclos reales de producción basados en datos actuales"""
    app = create_app()
    
    with app.app_context():
        # Obtener todas las variedades con siembras y cortes
        variedades = Variedad.query.join(Siembra).join(Corte).group_by(Variedad.variedad_id).all()
        
        if not variedades:
            click.echo("No se encontraron variedades con datos suficientes")
            return False
            
        click.echo(f"Analizando ciclos de producción para {len(variedades)} variedades...")
        
        # Procesar cada variedad
        for variedad in variedades:
            # Obtener siembras con cortes para esta variedad
            siembras = Siembra.query.filter_by(variedad_id=variedad.variedad_id)\
                         .filter(Siembra.cortes.any())\
                         .all()
            
            if not siembras:
                continue
                
            # Datos para análisis estadístico
            datos_ciclo_vegetativo = []  # Días hasta primer corte
            datos_ciclo_total = []       # Días hasta último corte
            datos_num_cortes = []        # Número total de cortes
            
            # Recolectar datos reales
            for siembra in siembras:
                if not siembra.cortes:
                    continue
                    
                # Ordenar cortes por fecha
                cortes_ordenados = sorted(siembra.cortes, key=lambda c: c.fecha_corte)
                
                if cortes_ordenados:
                    # Ciclo vegetativo: días hasta el primer corte
                    primer_corte = cortes_ordenados[0]
                    ciclo_vegetativo = (primer_corte.fecha_corte - siembra.fecha_siembra).days
                    if 20 <= ciclo_vegetativo <= 90:  # Filtrar valores atípicos
                        datos_ciclo_vegetativo.append(ciclo_vegetativo)
                    
                    # Ciclo total: días hasta el último corte
                    ultimo_corte = cortes_ordenados[-1]
                    ciclo_total = (ultimo_corte.fecha_corte - siembra.fecha_siembra).days
                    if 30 <= ciclo_total <= 180:  # Filtrar valores atípicos
                        datos_ciclo_total.append(ciclo_total)
                    
                    # Número de cortes
                    datos_num_cortes.append(len(cortes_ordenados))
            
            # Calcular estadísticas
            if datos_ciclo_vegetativo and datos_ciclo_total and datos_num_cortes:
                ciclo_vegetativo_promedio = sum(datos_ciclo_vegetativo) / len(datos_ciclo_vegetativo)
                ciclo_total_promedio = sum(datos_ciclo_total) / len(datos_ciclo_total)
                num_cortes_promedio = sum(datos_num_cortes) / len(datos_num_cortes)
                
                # Rangos válidos para verificar consistencia
                ciclo_por_corte = ciclo_total_promedio / max(1, num_cortes_promedio - 1) if num_cortes_promedio > 1 else 0
                
                click.echo(f"\nVariedad: {variedad.variedad}")
                click.echo(f"  Ciclo vegetativo: {ciclo_vegetativo_promedio:.1f} días")
                click.echo(f"  Ciclo total: {ciclo_total_promedio:.1f} días")
                click.echo(f"  Número promedio de cortes: {num_cortes_promedio:.1f}")
                click.echo(f"  Intervalo entre cortes: {ciclo_por_corte:.1f} días")
                
                # Verificar consistencia
                ciclo_consistente = (
                    ciclo_vegetativo_promedio < ciclo_total_promedio and
                    20 <= ciclo_por_corte <= 30  # Valor típico entre cortes
                )
                
                if not ciclo_consistente:
                    click.echo("  ⚠️ INCONSISTENCIA DETECTADA - Revisar manualmente")
        
        return True

def corregir_vista_produccion():
    """Corrige la vista SQL de producción por día"""
    app = create_app()
    
    with app.app_context():
        if click.confirm("\n¿Desea actualizar la vista de producción por día?", default=True):
            # Definir un nuevo límite de ciclo más realista y adaptativo
            from sqlalchemy import text
            
            # Primero, intentamos calcular un mejor límite basado en datos reales
            result = db.session.execute(text("""
                SELECT AVG(cycle_length) as avg_cycle
                FROM (
                    SELECT s.siembra_id, DATEDIFF(MAX(c.fecha_corte), s.fecha_siembra) as cycle_length
                    FROM siembras s
                    JOIN cortes c ON s.siembra_id = c.siembra_id
                    GROUP BY s.siembra_id
                    HAVING COUNT(c.corte_id) >= 3
                ) as subconsulta
            """))
            
            row = result.fetchone()
            if row and row[0]:
                dias_max_ciclo = min(180, int(float(row[0]) * 1.2))  # Usar un 20% más que el promedio, con tope en 180
            else:
                dias_max_ciclo = 120  # Valor por defecto si no hay datos
                
            click.echo(f"Calculando vista con límite de {dias_max_ciclo} días para el ciclo máximo")
            
            # Crear script para actualizar la vista
            script_content = f"""
from app import create_app, db
from sqlalchemy import text

app = create_app()
DIAS_MAX_CICLO = {dias_max_ciclo}  # Establece un límite adaptativo para el ciclo

with app.app_context():
    # Eliminar vista existente si existe
    db.session.execute(text("DROP VIEW IF EXISTS vista_produccion_por_dia"))
    
    # Crear vista con límite de días de ciclo y fecha de fin de corte
    sql_vista = f\"\"\"
    CREATE VIEW vista_produccion_por_dia AS
    SELECT 
        v.variedad_id,
        LEAST(DATEDIFF(c.fecha_corte, s.fecha_siembra), {{DIAS_MAX_CICLO}}) AS dias_desde_siembra,
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
        DATEDIFF(c.fecha_corte, s.fecha_siembra) <= {{DIAS_MAX_CICLO}}
        AND (s.fecha_fin_corte IS NULL OR c.fecha_corte <= s.fecha_fin_corte)
    GROUP BY 
        v.variedad_id, 
        dias_desde_siembra,
        v.variedad,
        f.flor,
        cl.color;
    \"\"\"
    
    db.session.execute(text(sql_vista))
    db.session.commit()
    print(f"Vista actualizada exitosamente con límite de {{DIAS_MAX_CICLO}} días")
"""
            # Escribir a archivo
            script_file = "ajustar_dias_ciclo.py"
            with open(script_file, 'w') as f:
                f.write(script_content)
                
            click.echo(f"Script creado: {script_file}")
            
            # Ejecutar script si el usuario lo confirma
            if click.confirm("¿Desea ejecutar el script ahora?", default=True):
                try:
                    result = subprocess.run(["python", script_file], check=True)
                    if result.returncode == 0:
                        click.echo("Vista actualizada correctamente")
                    else:
                        click.echo("Error al actualizar vista")
                except Exception as e:
                    click.echo(f"Error: {e}")
        
        return True

def modificar_calculo_curva():
    """Modifica la función de curva de producción para mejor cálculo de ciclos"""
    click.echo("\nPara corregir el cálculo de curvas de producción:")
    click.echo("1. Edite el archivo app/reportes/routes.py")
    click.echo("2. Busque la función 'curva_produccion' y actualice el código de cálculo de ciclos:")
    
    codigo_modificado = """
    # Código para agregar dentro de la función curva_produccion
    
    # Función para filtrar valores atípicos usando el método IQR
    def filtrar_outliers_iqr(valores, factor=1.5):
        # No hay suficientes datos para aplicar IQR
        if not valores or len(valores) < 4:
            return valores  
            
        # Ordenar valores
        valores_ordenados = sorted(valores)
        q1_idx = len(valores) // 4
        q3_idx = (len(valores) * 3) // 4
        
        q1 = valores_ordenados[q1_idx]
        q3 = valores_ordenados[q3_idx]
        
        iqr = q3 - q1
        lower_bound = q1 - (factor * iqr)
        upper_bound = q3 + (factor * iqr)
        
        return [v for v in valores if lower_bound <= v <= upper_bound]
    
    # Calcular ciclos promedio con filtrado mejorado
    dias_ciclo_vegetativo_filtrados = filtrar_outliers_iqr(dias_ciclo_vegetativo)
    dias_ciclo_total_filtrados = filtrar_outliers_iqr(dias_ciclo_total)
    
    # Calcular promedios de los datos filtrados
    if dias_ciclo_vegetativo_filtrados:
        ciclo_vegetativo_promedio = int(sum(dias_ciclo_vegetativo_filtrados) / len(dias_ciclo_vegetativo_filtrados))
    else:
        ciclo_vegetativo_promedio = 45  # Valor por defecto
    
    if dias_ciclo_total_filtrados:
        ciclo_total_promedio = int(sum(dias_ciclo_total_filtrados) / len(dias_ciclo_total_filtrados))
    else:
        ciclo_total_promedio = 110  # Valor por defecto
    
    # Validar consistencia entre ciclos
    # El ciclo total debe ser al menos 30 días más que el vegetativo
    if ciclo_total_promedio < ciclo_vegetativo_promedio + 30:
        ciclo_total_promedio = ciclo_vegetativo_promedio + 30
    """
    
    click.echo(codigo_modificado)
    
    return True

def main():
    """Función principal"""
    click.echo("=== CORRECCIÓN DE INCONSISTENCIAS EN CURVAS DE PRODUCCIÓN ===\n")
    
    # Verificar directorio actual
    if not os.path.exists("app"):
        click.echo("Error: Este script debe ejecutarse desde el directorio raíz del proyecto")
        return 1
    
    # Paso 1: Analizar ciclos reales
    click.echo("PASO 1: Analizando ciclos reales de producción basados en datos actuales...")
    if not calcular_ciclos_reales():
        if not click.confirm("Error al analizar ciclos. ¿Desea continuar?", default=False):
            return 1
    
    # Paso 2: Corregir vista SQL
    click.echo("\nPASO 2: Corrigiendo vista SQL para producción por día...")
    if not corregir_vista_produccion():
        if not click.confirm("Error al corregir vista. ¿Desea continuar?", default=False):
            return 1
    
    # Paso 3: Actualizar cálculo en reportes
    click.echo("\nPASO 3: Actualizando cálculo en función de curva_produccion...")
    if not modificar_calculo_curva():
        if not click.confirm("Error al generar instrucciones. ¿Desea continuar?", default=False):
            return 1
    
    click.echo("\n=== CORRECCIÓN COMPLETADA ===")
    click.echo("\nRecomendaciones finales:")
    click.echo("1. Implemente las modificaciones en app/reportes/routes.py")
    click.echo("2. Asegúrese de probar las correcciones con diferentes variedades")
    click.echo("3. Verifique la consistencia entre días de ciclo y número de cortes")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())