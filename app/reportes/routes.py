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

@reportes.route('/curva_produccion_interactiva')
@login_required
def curva_produccion_interactiva():
    """Vista interactiva de curvas de producción"""
    # Obtener parámetros de filtro
    filters = {
        'variedad_id': request.args.get('variedad_id', type=int),
        'bloque_id': request.args.get('bloque_id', type=int),
        'periodo': request.args.get('periodo', 'completo'),
        'periodo_inicio': request.args.get('periodo_inicio'),
        'periodo_fin': request.args.get('periodo_fin')
    }
    
    # Obtener listas para los filtros
    variedades = Variedad.query.order_by(Variedad.variedad).all()
    bloques = Bloque.query.order_by(Bloque.bloque).all()
    
    return render_template('reportes/curva_produccion_interactiva.html', 
                          title='Curvas de Producción Interactivas',
                          variedades=variedades,
                          bloques=bloques,
                          **filters)

@reportes.route('/dias_produccion')
@login_required
def dias_produccion():
    """Obtiene estadísticas de días desde siembra hasta corte por variedad y número de corte."""
    try:
        # Consulta SQL optimizada para obtener días desde siembra hasta corte
        results = db.session.query(
            Variedad.variedad_id,
            Variedad.variedad,
            Flor.flor,
            Color.color,
            Corte.num_corte,
            func.avg(
                func.datediff(
                    func.ifnull(Corte.fecha_corte, datetime.now()),
                    func.ifnull(Siembra.fecha_siembra, datetime.now())
                )
            ).label('dias_promedio'),
            func.min(
                func.datediff(Corte.fecha_corte, Siembra.fecha_siembra)
            ).label('dias_minimo'),
            func.max(
                func.datediff(Corte.fecha_corte, Siembra.fecha_siembra)
            ).label('dias_maximo'),
            func.count(func.distinct(Siembra.siembra_id)).label('total_siembras')
        ).join(
            Corte.siembra
        ).join(
            Siembra.variedad
        ).join(
            Variedad.flor_color
        ).join(
            FlorColor.flor
        ).join(
            FlorColor.color
        ).filter(
            Siembra.fecha_siembra.isnot(None),
            Corte.fecha_corte.isnot(None)
        ).group_by(
            Variedad.variedad_id,
            Variedad.variedad,
            Flor.flor,
            Color.color,
            Corte.num_corte
        ).order_by(
            Variedad.variedad,
            Corte.num_corte
        ).all()

        # Organizar datos por variedad y número de corte
        data_dict = {}
        for r in results:
            variedad_key = f"{r.variedad} ({r.flor} - {r.color})"
            if variedad_key not in data_dict:
                data_dict[variedad_key] = []
            
            data_dict[variedad_key].append({
                'num_corte': r.num_corte,
                'dias_promedio': round(r.dias_promedio, 1) if r.dias_promedio is not None else 0,
                'dias_minimo': r.dias_minimo if r.dias_minimo is not None else 0,
                'dias_maximo': r.dias_maximo if r.dias_maximo is not None else 0,
                'total_siembras': r.total_siembras if r.total_siembras is not None else 0
            })

        # Preparar gráficos solo si hay datos
        graficos = {}
        if data_dict:
            for variedad, cortes in data_dict.items():
                if not cortes:
                    continue
                    
                # Limitar a los primeros 10 cortes para el gráfico
                cortes_datos = cortes[:10]
                
                # Crear gráfico con matplotlib
                plt.figure(figsize=(10, 6))
                plt.bar(
                    [f"Corte {c['num_corte']}" for c in cortes_datos], 
                    [c['dias_promedio'] for c in cortes_datos],
                    color='skyblue'
                )
                
                # Añadir línea de tendencia
                if len(cortes_datos) > 1:
                    import numpy as np
                    x = range(len(cortes_datos))
                    y = [c['dias_promedio'] for c in cortes_datos]
                    z = np.polyfit(x, y, 1)
                    p = np.poly1d(z)
                    plt.plot(x, p(x), "r--")
                
                plt.xlabel('Número de Corte')
                plt.ylabel('Días Promedio')
                plt.title(f'Días Promedio por Corte: {variedad[:50]}')
                plt.xticks(rotation=45)
                plt.tight_layout()
                
                # Guardar gráfico en formato base64
                buffer = BytesIO()
                plt.savefig(buffer, format='png', dpi=100)
                buffer.seek(0)
                graficos[variedad] = base64.b64encode(buffer.getvalue()).decode('utf-8')
                plt.close()

        return render_template('reportes/dias_produccion.html', 
                            title='Días de Producción', 
                            data=data_dict, 
                            graficos=graficos)

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return render_template('error.html', 
                            message=f"Ocurrió un error al generar el reporte de días de producción: {str(e)}"), 500
    
@reportes.route('/diagnostico_importacion')
@login_required
def diagnostico_importacion():
    """
    Proporciona diagnóstico de los datos importados y ayuda a identificar problemas.
    """
    # Estadísticas generales
    stats = {
        'total_siembras': Siembra.query.count(),
        'total_cortes': Corte.query.count(),
        'total_variedades': Variedad.query.count(),
        'total_bloques': Bloque.query.count(),
        'total_camas': Cama.query.count()
    }
    
    # Verificar siembras sin cortes
    siembras_sin_cortes = Siembra.query.outerjoin(Corte).group_by(Siembra.siembra_id).having(func.count(Corte.corte_id) == 0).count()
    
    # Verificar cortes con valores de índice extremos
    cortes_indices_altos = db.session.query(Corte).join(Siembra).join(Area).join(Densidad).filter(
        (Corte.cantidad_tallos / (Area.area * Densidad.valor)) > 1.5  # Índice superior al 150%
    ).count()
    
    # Verificar variedades con siembras
    variedades_con_siembras = db.session.query(Variedad).join(Siembra).group_by(Variedad.variedad_id).count()
    
    # Obtener curvas de producción disponibles
    variedades_con_curvas = []
    for variedad in Variedad.query.all():
        # Verificar si la variedad tiene datos suficientes para una curva
        siembras = Siembra.query.filter_by(variedad_id=variedad.variedad_id).all()
        total_cortes = 0
        for siembra in siembras:
            total_cortes += len(siembra.cortes)
        
        if total_cortes > 0:
            variedades_con_curvas.append({
                'variedad_id': variedad.variedad_id,
                'variedad': variedad.variedad,
                'flor': variedad.flor_color.flor.flor if variedad.flor_color else "Desconocida",
                'color': variedad.flor_color.color.color if variedad.flor_color else "Desconocido",
                'siembras': len(siembras),
                'cortes': total_cortes
            })
    
    # Ordenar por número de cortes (más datos primero)
    variedades_con_curvas.sort(key=lambda x: x['cortes'], reverse=True)
    
    return render_template('reportes/diagnostico_importacion.html',
                          title='Diagnóstico de Importación',
                          stats=stats,
                          siembras_sin_cortes=siembras_sin_cortes,
                          cortes_indices_altos=cortes_indices_altos,
                          variedades_con_siembras=variedades_con_siembras,
                          variedades_con_curvas=variedades_con_curvas)

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