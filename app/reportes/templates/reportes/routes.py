from flask import render_template, request, jsonify, send_file
from flask_login import login_required
from app import db
from app.reportes import reportes_bp
from app.models import Siembra, Corte, Variedad, Flor, Color, FlorColor, BloqueCamaLado, Bloque
from sqlalchemy import func, desc, asc
from datetime import datetime, timedelta
import io
import csv

@reportes_bp.route('/reportes')
@login_required
def index():
    """Página principal de reportes."""
    return render_template('reportes/index.html', title='Reportes')

@reportes_bp.route('/reportes/produccion')
@login_required
def produccion():
    """Reporte de producción por variedad."""
    # Obtener datos agrupados por variedad
    resultados = db.session.query(
        Variedad.variedad,
        func.sum(Corte.cantidad_tallos).label('total_tallos')
    ).join(Siembra, Variedad.variedad_id == Siembra.variedad_id
    ).join(Corte, Siembra.siembra_id == Corte.siembra_id
    ).group_by(Variedad.variedad
    ).order_by(desc('total_tallos')).all()
    
    # Preparar datos para la vista
    labels = [r[0] for r in resultados]
    data = [r[1] for r in resultados]
    
    return render_template('reportes/produccion.html', 
                          title='Producción por Variedad',
                          labels=labels,
                          data=data,
                          resultados=resultados)

@reportes_bp.route('/reportes/produccion_mensual')
@login_required
def produccion_mensual():
    """Reporte de producción mensual."""
    # Obtener fecha de hace 12 meses
    fecha_inicio = datetime.now() - timedelta(days=365)
    
    # Datos agrupados por mes
    resultados = db.session.query(
        func.year(Corte.fecha_corte).label('año'),
        func.month(Corte.fecha_corte).label('mes'),
        func.sum(Corte.cantidad_tallos).label('total_tallos')
    ).filter(Corte.fecha_corte >= fecha_inicio
    ).group_by('año', 'mes'
    ).order_by('año', 'mes').all()
    
    # Formatear resultados
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    
    datos_formateados = []
    for r in resultados:
        datos_formateados.append({
            'periodo': f"{meses[r[1]-1]} {r[0]}",
            'total_tallos': r[2]
        })
    
    # Preparar datos para la gráfica
    labels = [d['periodo'] for d in datos_formateados]
    data = [d['total_tallos'] for d in datos_formateados]
    
    return render_template('reportes/produccion_mensual.html', 
                          title='Producción Mensual',
                          labels=labels,
                          data=data,
                          resultados=datos_formateados)

@reportes_bp.route('/reportes/productividad')
@login_required
def productividad():
    """Reporte de productividad (tallos por m²) por bloque."""
    # Obtener datos agrupados por bloque
    resultados = db.session.query(
        Bloque.bloque,
        func.sum(Corte.cantidad_tallos).label('total_tallos'),
        func.sum(Siembra.area_siembra.area).label('area_total')
    ).join(BloqueCamaLado, Bloque.bloque_id == BloqueCamaLado.bloque_id
    ).join(Siembra, BloqueCamaLado.bloque_cama_id == Siembra.bloque_cama_id
    ).join(Corte, Siembra.siembra_id == Corte.siembra_id
    ).group_by(Bloque.bloque).all()
    
    # Calcular productividad
    datos_productividad = []
    for r in resultados:
        if r[2] > 0:  # Evitar división por cero
            productividad = r[1] / r[2]
            datos_productividad.append({
                'bloque': r[0],
                'total_tallos': r[1],
                'area_total': r[2],
                'productividad': round(productividad, 2)
            })
    
    # Ordenar por productividad
    datos_productividad.sort(key=lambda x: x['productividad'], reverse=True)
    
    # Preparar datos para la gráfica
    labels = [d['bloque'] for d in datos_productividad]
    data = [d['productividad'] for d in datos_productividad]
    
    return render_template('reportes/productividad.html',
                          title='Productividad por Bloque',
                          labels=labels,
                          data=data,
                          resultados=datos_productividad)

@reportes_bp.route('/reportes/variedades')
@login_required
def variedades_flor_color():
    """Reporte de distribución de variedades por tipo y color."""
    # Obtener datos agrupados por flor y color
    resultados = db.session.query(
        Flor.flor,
        Color.color,
        func.count(Variedad.variedad_id).label('cantidad_variedades')
    ).join(FlorColor, Flor.flor_id == FlorColor.flor_id
    ).join(Color, FlorColor.color_id == Color.color_id
    ).join(Variedad, FlorColor.flor_color_id == Variedad.flor_color_id
    ).group_by(Flor.flor, Color.color
    ).order_by(Flor.flor, Color.color).all()
    
    # Organizar datos para la visualización
    flores = []
    colores = set()
    datos = {}
    
    for r in resultados:
        flor, color, cantidad = r
        if flor not in flores:
            flores.append(flor)
        colores.add(color)
        datos[(flor, color)] = cantidad
    
    colores = sorted(list(colores))
    
    # Crear matriz de datos para visualización
    matriz_datos = []
    for flor in flores:
        fila = {'flor': flor}
        for color in colores:
            fila[color] = datos.get((flor, color), 0)
        matriz_datos.append(fila)
    
    return render_template('reportes/variedades.html',
                          title='Distribución de Variedades',
                          flores=flores,
                          colores=colores,
                          matriz_datos=matriz_datos)

@reportes_bp.route('/reportes/ciclo_vida')
@login_required
def ciclo_vida():
    """Reporte de ciclo de vida de siembras."""
    # Obtener siembras finalizadas
    siembras = Siembra.query.filter_by(estado='Finalizada').all()
    
    # Calcular estadísticas
    datos_ciclo = []
    for s in siembras:
        primer_corte = Corte.query.filter_by(siembra_id=s.siembra_id, num_corte=1).first()
        ultimo_corte = Corte.query.filter_by(siembra_id=s.siembra_id).order_by(Corte.num_corte.desc()).first()
        
        if primer_corte and ultimo_corte:
            dias_hasta_primer_corte = (primer_corte.fecha_corte - s.fecha_siembra).days
            dias_ciclo_total = (ultimo_corte.fecha_corte - s.fecha_siembra).days
            
            datos_ciclo.append({
                'siembra_id': s.siembra_id,
                'variedad': s.variedad.variedad,
                'ubicacion': str(s.bloque_cama_lado),
                'fecha_siembra': s.fecha_siembra.strftime('%d/%m/%Y'),
                'fecha_primer_corte': primer_corte.fecha_corte.strftime('%d/%m/%Y'),
                'fecha_ultimo_corte': ultimo_corte.fecha_corte.strftime('%d/%m/%Y'),
                'dias_hasta_primer_corte': dias_hasta_primer_corte,
                'dias_ciclo_total': dias_ciclo_total,
                'total_cortes': s.cortes.count(),
                'total_tallos': s.total_tallos
            })
    
    # Calcular promedios
    if datos_ciclo:
        promedio_dias_primer_corte = sum(d['dias_hasta_primer_corte'] for d in datos_ciclo) / len(datos_ciclo)
        promedio_dias_ciclo = sum(d['dias_ciclo_total'] for d in datos_ciclo) / len(datos_ciclo)
        promedio_cortes = sum(d['total_cortes'] for d in datos_ciclo) / len(datos_ciclo)
    else:
        promedio_dias_primer_corte = 0
        promedio_dias_ciclo = 0
        promedio_cortes = 0
    
    # Ordenar por días de ciclo total
    datos_ciclo.sort(key=lambda x: x['dias_ciclo_total'], reverse=True)
    
    return render_template('reportes/ciclo_vida.html',
                          title='Ciclo de Vida de Siembras',
                          datos_ciclo=datos_ciclo,
                          promedio_dias_primer_corte=round(promedio_dias_primer_corte, 1),
                          promedio_dias_ciclo=round(promedio_dias_ciclo, 1),
                          promedio_cortes=round(promedio_cortes, 1))

@reportes_bp.route('/reportes/export/<tipo>')
@login_required
def exportar_reporte(tipo):
    """Exportar reportes a CSV."""
    # Crear un archivo CSV en memoria
    output = io.StringIO()
    writer = csv.writer(output)
    
    if tipo == 'produccion':
        # Exportar reporte de producción por variedad
        writer.writerow(['Variedad', 'Total Tallos'])
        
        resultados = db.session.query(
            Variedad.variedad,
            func.sum(Corte.cantidad_tallos).label('total_tallos')
        ).join(Siembra, Variedad.variedad_id == Siembra.variedad_id
        ).join(Corte, Siembra.siembra_id == Corte.siembra_id
        ).group_by(Variedad.variedad
        ).order_by(desc('total_tallos')).all()
        
        for r in resultados:
            writer.writerow([r[0], r[1]])
        
        filename = f"produccion_por_variedad_{datetime.now().strftime('%Y%m%d')}.csv"
    
    elif tipo == 'produccion_mensual':
        # Exportar reporte de producción mensual
        writer.writerow(['Año', 'Mes', 'Total Tallos'])
        
        # Datos agrupados por mes (últimos 12 meses)
        fecha_inicio = datetime.now() - timedelta(days=365)
        resultados = db.session.query(
            func.year(Corte.fecha_corte).label('año'),
            func.month(Corte.fecha_corte).label('mes'),
            func.sum(Corte.cantidad_tallos).label('total_tallos')
        ).filter(Corte.fecha_corte >= fecha_inicio
        ).group_by('año', 'mes'
        ).order_by('año', 'mes').all()
        
        for r in resultados:
            writer.writerow([r[0], r[1], r[2]])
        
        filename = f"produccion_mensual_{datetime.now().strftime('%Y%m%d')}.csv"
    
    elif tipo == 'ciclo_vida':
        # Exportar reporte de ciclo de vida
        writer.writerow([
            'ID Siembra', 'Variedad', 'Ubicación', 'Fecha Siembra', 
            'Fecha Primer Corte', 'Fecha Último Corte', 'Días Hasta Primer Corte',
            'Días Ciclo Total', 'Total Cortes', 'Total Tallos'
        ])
        
        siembras = Siembra.query.filter_by(estado='Finalizada').all()
        
        for s in siembras:
            primer_corte = Corte.query.filter_by(siembra_id=s.siembra_id, num_corte=1).first()
            ultimo_corte = Corte.query.filter_by(siembra_id=s.siembra_id).order_by(Corte.num_corte.desc()).first()
            
            if primer_corte and ultimo_corte:
                dias_hasta_primer_corte = (primer_corte.fecha_corte - s.fecha_siembra).days
                dias_ciclo_total = (ultimo_corte.fecha_corte - s.fecha_siembra).days
                
                writer.writerow([
                    s.siembra_id,
                    s.variedad.variedad,
                    str(s.bloque_cama_lado),
                    s.fecha_siembra.strftime('%d/%m/%Y'),
                    primer_corte.fecha_corte.strftime('%d/%m/%Y'),
                    ultimo_corte.fecha_corte.strftime('%d/%m/%Y'),
                    dias_hasta_primer_corte,
                    dias_ciclo_total,
                    s.cortes.count(),
                    s.total_tallos
                ])
        
        filename = f"ciclo_vida_siembras_{datetime.now().strftime('%Y%m%d')}.csv"
    
    else:
        # Tipo de reporte no válido
        return jsonify({"error": "Tipo de reporte no válido"}), 400
    
    # Preparar y enviar el archivo
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )