from flask import render_template, request, jsonify, send_file
from flask_login import login_required
from sqlalchemy import func, desc
import pandas as pd
from io import BytesIO
from datetime import datetime
import matplotlib.pyplot as plt
import base64
from app import db
from . import reportes
from app.models import (
    Siembra, Corte, Variedad, Flor, Color, FlorColor, 
    BloqueCamaLado, Bloque, Cama, Lado, Area, Densidad
)
from .charts import generar_grafico_curva
from .data_processing import obtener_datos_curva
from .utils import calc_plantas_totales, calc_indice_aprovechamiento

# ================ VISTAS PRINCIPALES ================

@reportes.route('/')
@login_required
def index():
    variedades_con_siembras = db.session.query(Variedad)\
        .join(Siembra)\
        .group_by(Variedad.variedad_id)\
        .order_by(Variedad.variedad)\
        .all()
    return render_template('reportes/index.html', 
                         title='Reportes', 
                         variedades=variedades_con_siembras)

@reportes.route('/produccion_por_variedad')
@login_required
def produccion_por_variedad():
    results = db.session.query(
        Variedad.variedad_id,
        Variedad.variedad,
        Flor.flor,
        Color.color,
        func.sum(Corte.cantidad_tallos).label('total_tallos')
    ).select_from(Corte)\
     .join(Siembra)\
     .join(Variedad)\
     .join(FlorColor)\
     .join(Flor)\
     .join(Color)\
     .group_by(Variedad.variedad_id, Variedad.variedad, Flor.flor, Color.color)\
     .order_by(desc('total_tallos'))\
     .all()
    
    data = [{
        'variedad_id': r.variedad_id,
        'variedad': r.variedad,
        'flor': r.flor,
        'color': r.color,
        'total_tallos': r.total_tallos
    } for r in results]
    
    # Generar gráfico
    grafico = None
    if data:
        top_variedades = data[:10]
        plt.figure(figsize=(10, 6))
        plt.bar([r['variedad'] for r in top_variedades], [r['total_tallos'] for r in top_variedades])
        plt.xlabel('Variedad')
        plt.ylabel('Total de Tallos')
        plt.title('Top 10 Variedades por Producción de Tallos')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        grafico = base64.b64encode(buffer.getvalue()).decode('utf-8')
        plt.close()
    
    return render_template('reportes/produccion_por_variedad.html', 
                         title='Producción por Variedad', 
                         data=data, 
                         grafico=grafico)

@reportes.route('/produccion_por_bloque')
@login_required
def produccion_por_bloque():
    results = db.session.query(
        Bloque.bloque_id,
        Bloque.bloque,
        func.sum(Corte.cantidad_tallos).label('total_tallos'),
        func.count(func.distinct(Siembra.siembra_id)).label('total_siembras')
    ).join(Siembra)\
     .join(BloqueCamaLado)\
     .join(Bloque)\
     .group_by(Bloque.bloque_id, Bloque.bloque)\
     .order_by(Bloque.bloque)\
     .all()
    
    data = [{
        'bloque_id': r.bloque_id,
        'bloque': r.bloque,
        'total_tallos': r.total_tallos,
        'total_siembras': r.total_siembras,
        'promedio_tallos': r.total_tallos / r.total_siembras if r.total_siembras > 0 else 0
    } for r in results]
    
    # Generar gráfico
    grafico = None
    if data:
        plt.figure(figsize=(10, 6))
        plt.bar([r['bloque'] for r in data], [r['total_tallos'] for r in data])
        plt.xlabel('Bloque')
        plt.ylabel('Total de Tallos')
        plt.title('Producción por Bloque')
        plt.tight_layout()
        
        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        grafico = base64.b64encode(buffer.getvalue()).decode('utf-8')
        plt.close()
    
    return render_template('reportes/produccion_por_bloque.html', 
                         title='Producción por Bloque', 
                         data=data, 
                         grafico=grafico)

@reportes.route('/dias_produccion')
@login_required
def dias_produccion():
    """
    Genera un reporte que muestra los días de producción para diferentes variedades,
    incluyendo días promedio entre cortes, mínimos, máximos y visualización.
    """
    # Obtener variedades con suficientes datos para el análisis
    variedades_con_datos = db.session.query(Variedad)\
        .join(Siembra)\
        .join(Corte)\
        .group_by(Variedad.variedad_id)\
        .having(func.count(Corte.corte_id) > 5)\
        .order_by(Variedad.variedad)\
        .all()
    
    # Preparar estructura de datos para el reporte
    data = {}
    graficos = {}
    
    # Procesar datos para cada variedad
    for variedad in variedades_con_datos:
        # Obtener todas las siembras para esta variedad
        siembras = Siembra.query.filter_by(variedad_id=variedad.variedad_id).all()
        
        # Diccionario para almacenar datos por número de corte
        cortes_data = {}
        
        # Procesar cada siembra
        for siembra in siembras:
            if not siembra.cortes:
                continue
                
            # Obtener todos los cortes ordenados por número
            cortes = sorted(siembra.cortes, key=lambda c: c.num_corte)
            
            # Procesar cada corte
            for i, corte in enumerate(cortes):
                num_corte = corte.num_corte
                
                # Calcular días desde la siembra
                dias = (corte.fecha_corte - siembra.fecha_siembra).days
                
                # Almacenar en estructura cortes_data
                if num_corte not in cortes_data:
                    cortes_data[num_corte] = []
                
                # Solo considerar valores razonables (entre 30 y 150 días)
                if 30 <= dias <= 150:
                    cortes_data[num_corte].append(dias)
        
        # Crear datos resumidos para la variedad
        variedad_data = []
        for num_corte, dias_list in sorted(cortes_data.items()):
            # Aplicar filtro IQR para eliminar valores atípicos
            dias_filtrados = filtrar_outliers_iqr(dias_list)
            
            if dias_filtrados:
                variedad_data.append({
                    'num_corte': num_corte,
                    'dias_promedio': round(sum(dias_filtrados) / len(dias_filtrados)),
                    'dias_minimo': min(dias_filtrados),
                    'dias_maximo': max(dias_filtrados),
                    'total_siembras': len(dias_filtrados)
                })
        
        # Solo incluir variedades con al menos 2 cortes con datos
        if len(variedad_data) >= 2:
            data[variedad.variedad] = sorted(variedad_data, key=lambda x: x['num_corte'])
            
            # Generar gráfico para esta variedad
            try:
                import matplotlib.pyplot as plt
                import numpy as np
                import base64
                from io import BytesIO
                
                # Crear figura
                plt.figure(figsize=(8, 5))
                
                # Extraer datos para el gráfico
                cortes_nums = [d['num_corte'] for d in variedad_data]
                dias_promedio = [d['dias_promedio'] for d in variedad_data]
                dias_min = [d['dias_minimo'] for d in variedad_data]
                dias_max = [d['dias_maximo'] for d in variedad_data]
                
                # Graficar días promedio
                plt.plot(cortes_nums, dias_promedio, 'o-', color='blue', linewidth=2, 
                         label='Días promedio')
                
                # Mostrar rango min-max
                plt.fill_between(cortes_nums, dias_min, dias_max, color='blue', alpha=0.2, 
                                 label='Rango min-max')
                
                # Configurar gráfico
                plt.title(f'Días de Producción: {variedad.variedad}')
                plt.xlabel('Número de Corte')
                plt.ylabel('Días desde siembra')
                plt.xticks(cortes_nums)
                plt.grid(True, alpha=0.3)
                plt.legend()
                
                # Guardar gráfico en base64
                buffer = BytesIO()
                plt.savefig(buffer, format='png', dpi=80)
                buffer.seek(0)
                grafico_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                plt.close()
                
                # Guardar gráfico
                graficos[variedad.variedad] = grafico_base64
                
            except Exception as e:
                print(f"Error al generar gráfico para {variedad.variedad}: {str(e)}")
    
    return render_template('reportes/dias_produccion.html',
                           title='Reporte de Días de Producción',
                           data=data,
                           graficos=graficos)

# ================ CURVAS DE PRODUCCIÓN ================

@reportes.route('/curva_produccion/<int:variedad_id>')
@login_required
def curva_produccion(variedad_id):
    """Genera y muestra la curva de producción para una variedad"""
    variedad = Variedad.query.get_or_404(variedad_id)
    
    # Obtener parámetros de filtro
    filtro_periodo = request.args.get('periodo', 'completo')
    periodo_inicio = request.args.get('periodo_inicio', None)
    periodo_fin = request.args.get('periodo_fin', None)
    
    # Procesar datos
    datos = obtener_datos_curva(
        variedad_id=variedad_id,
        periodo_filtro=filtro_periodo,
        periodo_inicio=periodo_inicio,
        periodo_fin=periodo_fin
    )
    
    # Generar gráfico
    grafico_curva = None
    if datos['puntos_curva']:
        grafico_curva = generar_grafico_curva(
            datos['puntos_curva'],
            variedad.variedad,
            datos['ciclo_vegetativo'],
            datos['ciclo_total']
        )
    
    # Preparar datos para la plantilla
    datos_adicionales = {
        'total_siembras': datos['total_siembras'],
        'siembras_con_datos': datos['siembras_con_datos'],
        'total_plantas': datos['total_plantas'],
        'total_tallos': datos['total_tallos'],
        'promedio_produccion': datos['promedio_produccion'],
        'ciclo_vegetativo': datos['ciclo_vegetativo'],
        'ciclo_productivo': max(0, datos['ciclo_total'] - datos['ciclo_vegetativo']),
        'ciclo_total': datos['ciclo_total'],
        'filtro_periodo': filtro_periodo,
        'periodo_inicio': periodo_inicio,
        'periodo_fin': periodo_fin
    }
    
    return render_template('reportes/curva_produccion.html',
                         title=f'Curva de Producción: {variedad.variedad}',
                         variedad=variedad,
                         puntos_curva=datos['puntos_curva'],
                         grafico_curva=grafico_curva,
                         datos_adicionales=datos_adicionales)

# ================ OTRAS VISTAS ================

@reportes.route('/exportar_datos')
@login_required
def exportar_datos():
    tipo_reporte = request.args.get('tipo', 'siembras')
    
    if tipo_reporte == 'siembras':
        results = db.session.query(
            Siembra.siembra_id,
            Bloque.bloque,
            Cama.cama,
            Lado.lado,
            Variedad.variedad,
            Flor.flor,
            Color.color,
            Siembra.fecha_siembra,
            Siembra.fecha_inicio_corte,
            Siembra.estado
        ).join(BloqueCamaLado)\
         .join(Bloque)\
         .join(Cama)\
         .join(Lado)\
         .join(Variedad)\
         .join(FlorColor)\
         .join(Flor)\
         .join(Color)\
         .all()
        
        df = pd.DataFrame([{
            'ID Siembra': r.siembra_id,
            'Bloque': r.bloque,
            'Cama': r.cama,
            'Lado': r.lado,
            'Variedad': r.variedad,
            'Flor': r.flor,
            'Color': r.color,
            'Fecha Siembra': r.fecha_siembra.strftime('%d/%m/%Y'),
            'Fecha Inicio Corte': r.fecha_inicio_corte.strftime('%d/%m/%Y') if r.fecha_inicio_corte else '',
            'Estado': r.estado
        } for r in results])
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Siembras', index=False)
        output.seek(0)
        
        return send_file(
            output,
            as_attachment=True,
            download_name=f'siembras_{datetime.now().strftime("%Y%m%d")}.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    
    elif tipo_reporte == 'cortes':
        results = db.session.query(
            Corte.corte_id,
            Siembra.siembra_id,
            Bloque.bloque,
            Cama.cama,
            Lado.lado,
            Variedad.variedad,
            Corte.num_corte,
            Corte.fecha_corte,
            Corte.cantidad_tallos,
            Siembra.fecha_siembra,
            func.datediff(Corte.fecha_corte, Siembra.fecha_siembra).label('dias_desde_siembra')
        ).join(Siembra)\
         .join(BloqueCamaLado)\
         .join(Bloque)\
         .join(Cama)\
         .join(Lado)\
         .join(Variedad)\
         .order_by(Siembra.siembra_id, Corte.num_corte)\
         .all()
        
        df = pd.DataFrame([{
            'ID Corte': r.corte_id,
            'ID Siembra': r.siembra_id,
            'Bloque': r.bloque,
            'Cama': r.cama,
            'Lado': r.lado,
            'Variedad': r.variedad,
            'Corte #': r.num_corte,
            'Fecha Corte': r.fecha_corte.strftime('%d/%m/%Y'),
            'Cantidad Tallos': r.cantidad_tallos,
            'Fecha Siembra': r.fecha_siembra.strftime('%d/%m/%Y'),
            'Días desde Siembra': r.dias_desde_siembra
        } for r in results])
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Cortes', index=False)
        output.seek(0)
        
        return send_file(
            output,
            as_attachment=True,
            download_name=f'cortes_{datetime.now().strftime("%Y%m%d")}.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    
    return jsonify({'error': 'Tipo de reporte no válido'})

@reportes.route('/diagnostico_importacion')
@login_required
def diagnostico_importacion():
    """
    Genera un diagnóstico del estado de los datos importados en el sistema,
    mostrando estadísticas y posibles problemas con los datos.
    """
    # Estadísticas generales
    stats = {
        "total_siembras": Siembra.query.count(),
        "total_cortes": Corte.query.count(),
        "total_variedades": Variedad.query.count()
    }
    
    # Identificar siembras sin cortes (potencialmente incompletas)
    siembras_sin_cortes = db.session.query(func.count(Siembra.siembra_id))\
        .outerjoin(Corte)\
        .group_by(Siembra.siembra_id)\
        .having(func.count(Corte.corte_id) == 0)\
        .count()
    
    # Identificar cortes con índices extremadamente altos (posibles errores)
    cortes_indices_altos = 0
    for corte in Corte.query.all():
        siembra = Siembra.query.get(corte.siembra_id)
        if not siembra or not siembra.area or not siembra.densidad:
            continue
        
        # Calcular plantas totales
        plantas_totales = siembra.area.area * siembra.densidad.valor
        if plantas_totales <= 0:
            continue
        
        # Calcular índice
        indice = (corte.cantidad_tallos / plantas_totales) * 100
        
        # Comprobar si el índice es extremadamente alto (sobre 30%)
        if indice > 30:
            cortes_indices_altos += 1
    
    # Variedades con siembras registradas
    variedades_con_siembras = db.session.query(Variedad)\
        .join(Siembra)\
        .group_by(Variedad.variedad_id)\
        .count()
    
    # Variedades con suficientes datos para curvas de producción
    variedades_con_curvas = []
    for variedad in Variedad.query.all():
        siembras_query = Siembra.query.filter_by(variedad_id=variedad.variedad_id)
        siembras_count = siembras_query.count()
        
        if siembras_count >= 3:  # Mínimo 3 siembras para tener datos significativos
            cortes_count = db.session.query(func.count(Corte.corte_id))\
                .join(Siembra)\
                .filter(Siembra.variedad_id == variedad.variedad_id)\
                .scalar() or 0
            
            if cortes_count >= 10:  # Mínimo 10 cortes en total para tener suficientes datos
                variedades_con_curvas.append({
                    'variedad_id': variedad.variedad_id,
                    'variedad': variedad.variedad,
                    'flor': variedad.flor_color.flor.flor,
                    'color': variedad.flor_color.color.color,
                    'siembras': siembras_count,
                    'cortes': cortes_count
                })
    
    # Ordenar variedades por número de cortes (más cortes primero)
    variedades_con_curvas = sorted(variedades_con_curvas, key=lambda x: x['cortes'], reverse=True)
    
    return render_template('reportes/diagnostico_importacion.html',
                        title='Diagnóstico de Importación de Datos',
                        stats=stats,
                        siembras_sin_cortes=siembras_sin_cortes,
                        cortes_indices_altos=cortes_indices_altos,
                        variedades_con_siembras=variedades_con_siembras,
                        variedades_con_curvas=variedades_con_curvas)