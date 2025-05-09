# Primero configurar el backend antes de importar pyplot
import matplotlib
matplotlib.use('Agg')  # Configurar backend no interactivo

# Resto de las importaciones
from flask import render_template, request, jsonify, send_file
from flask_login import login_required
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from sqlalchemy import func, desc
from app import db
from app.reportes import reportes
from app.models import Siembra, Corte, Variedad, Flor, Color, FlorColor, BloqueCamaLado, Bloque, Cama, Lado

# Resto del código...

@reportes.route('/')
@login_required
def index():
    return render_template('reportes/index.html', title='Reportes')

@reportes.route('/produccion_por_variedad')
@login_required
def produccion_por_variedad():
    # Consulta SQL para obtener la producción por variedad
    results = db.session.query(
        Variedad.variedad_id,
        Variedad.variedad,
        Flor.flor,
        Color.color,
        func.sum(Corte.cantidad_tallos).label('total_tallos')
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
    ).group_by(
        Variedad.variedad_id,
        Variedad.variedad,
        Flor.flor,
        Color.color
    ).order_by(
        desc('total_tallos')
    ).all()
    
    # Preparar los datos para la plantilla
    data = [
        {
            'variedad_id': r.variedad_id,
            'variedad': r.variedad,
            'flor': r.flor,
            'color': r.color,
            'total_tallos': r.total_tallos
        }
        for r in results
    ]
    
    # Preparar datos para la gráfica
    if data:
        # Limitamos a las 10 principales variedades para la gráfica
        top_variedades = data[:10]
        
        # Crear gráfico con matplotlib
        plt.figure(figsize=(10, 6))
        plt.bar([r['variedad'] for r in top_variedades], [r['total_tallos'] for r in top_variedades])
        plt.xlabel('Variedad')
        plt.ylabel('Total de Tallos')
        plt.title('Top 10 Variedades por Producción de Tallos')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        # Guardar gráfico en formato base64 para enviarlo a la plantilla
        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        grafico = base64.b64encode(buffer.getvalue()).decode('utf-8')
        plt.close()
    else:
        grafico = None
    
    return render_template('reportes/produccion_por_variedad.html', 
                          title='Producción por Variedad', 
                          data=data, 
                          grafico=grafico)

@reportes.route('/produccion_por_bloque')
@login_required
def produccion_por_bloque():
    # Consulta SQL para obtener la producción por bloque
    results = db.session.query(
        Bloque.bloque_id,
        Bloque.bloque,
        func.sum(Corte.cantidad_tallos).label('total_tallos'),
        func.count(func.distinct(Siembra.siembra_id)).label('total_siembras')
    ).join(
        Corte.siembra
    ).join(
        Siembra.bloque_cama
    ).join(
        BloqueCamaLado.bloque
    ).group_by(
        Bloque.bloque_id,
        Bloque.bloque
    ).order_by(
        Bloque.bloque
    ).all()
    
    # Preparar los datos para la plantilla
    data = [
        {
            'bloque_id': r.bloque_id,
            'bloque': r.bloque,
            'total_tallos': r.total_tallos,
            'total_siembras': r.total_siembras,
            'promedio_tallos': r.total_tallos / r.total_siembras if r.total_siembras > 0 else 0
        }
        for r in results
    ]
    
    # Preparar datos para la gráfica
    if data:
        # Crear gráfico con matplotlib
        plt.figure(figsize=(10, 6))
        plt.bar([r['bloque'] for r in data], [r['total_tallos'] for r in data])
        plt.xlabel('Bloque')
        plt.ylabel('Total de Tallos')
        plt.title('Producción por Bloque')
        plt.tight_layout()
        
        # Guardar gráfico en formato base64 para enviarlo a la plantilla
        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        grafico = base64.b64encode(buffer.getvalue()).decode('utf-8')
        plt.close()
    else:
        grafico = None
    
    return render_template('reportes/produccion_por_bloque.html', 
                          title='Producción por Bloque', 
                          data=data, 
                          grafico=grafico)

@reportes.route('/dias_produccion')
@login_required
def dias_produccion():
    # Consulta SQL para obtener días desde siembra hasta corte
    results = db.session.query(
        Variedad.variedad_id,
        Variedad.variedad,
        Flor.flor,
        Color.color,
        Corte.num_corte,
        func.avg(func.datediff(Corte.fecha_corte, Siembra.fecha_siembra)).label('dias_promedio'),
        func.min(func.datediff(Corte.fecha_corte, Siembra.fecha_siembra)).label('dias_minimo'),
        func.max(func.datediff(Corte.fecha_corte, Siembra.fecha_siembra)).label('dias_maximo'),
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
            'dias_promedio': round(r.dias_promedio, 1),
            'dias_minimo': r.dias_minimo,
            'dias_maximo': r.dias_maximo,
            'total_siembras': r.total_siembras
        })
    
    # Preparar gráficos
    if data_dict:
        graficos = {}
        
        for variedad, cortes in data_dict.items():
            # Limitar a los primeros 5 cortes para el gráfico
            cortes_datos = cortes[:5]
            
            # Crear gráfico con matplotlib
            plt.figure(figsize=(8, 5))
            plt.bar(
                [f"Corte {c['num_corte']}" for c in cortes_datos], 
                [c['dias_promedio'] for c in cortes_datos]
            )
            plt.xlabel('Número de Corte')
            plt.ylabel('Días Promedio')
            plt.title(f'Días Promedio por Corte: {variedad}')
            plt.tight_layout()
            
            # Guardar gráfico en formato base64
            buffer = BytesIO()
            plt.savefig(buffer, format='png')
            buffer.seek(0)
            graficos[variedad] = base64.b64encode(buffer.getvalue()).decode('utf-8')
            plt.close()
    else:
        graficos = None
    
    return render_template('reportes/dias_produccion.html', 
                          title='Días de Producción', 
                          data=data_dict, 
                          graficos=graficos)

@reportes.route('/exportar_datos')
@login_required
def exportar_datos():
    tipo_reporte = request.args.get('tipo', 'siembras')
    
    if tipo_reporte == 'siembras':
        # Consulta para obtener datos de siembras
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
        ).join(
            Siembra.bloque_cama
        ).join(
            BloqueCamaLado.bloque
        ).join(
            BloqueCamaLado.cama
        ).join(
            BloqueCamaLado.lado
        ).join(
            Siembra.variedad
        ).join(
            Variedad.flor_color
        ).join(
            FlorColor.flor
        ).join(
            FlorColor.color
        ).all()
        
        # Crear DataFrame
        df = pd.DataFrame([
            {
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
            }
            for r in results
        ])
        
        # Guardar DataFrame como Excel
        output = BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        df.to_excel(writer, sheet_name='Siembras', index=False)
        writer.close()
        output.seek(0)
        
        return send_file(
            output,
            as_attachment=True,
            download_name=f'siembras_{pd.Timestamp.now().strftime("%Y%m%d")}.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    
    elif tipo_reporte == 'cortes':
        # Consulta para obtener datos de cortes
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
        ).join(
            Corte.siembra
        ).join(
            Siembra.bloque_cama
        ).join(
            BloqueCamaLado.bloque
        ).join(
            BloqueCamaLado.cama
        ).join(
            BloqueCamaLado.lado
        ).join(
            Siembra.variedad
        ).order_by(
            Siembra.siembra_id,
            Corte.num_corte
        ).all()
        
        # Crear DataFrame
        df = pd.DataFrame([
            {
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
            }
            for r in results
        ])
        
        # Guardar DataFrame como Excel
        output = BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        df.to_excel(writer, sheet_name='Cortes', index=False)
        writer.close()
        output.seek(0)
        
        return send_file(
            output,
            as_attachment=True,
            download_name=f'cortes_{pd.Timestamp.now().strftime("%Y%m%d")}.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    
    return jsonify({'error': 'Tipo de reporte no válido'})