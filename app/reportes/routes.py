# Primero configurar el backend antes de importar pyplot
import matplotlib
matplotlib.use('Agg')  # Configurar backend no interactivo

# Resto de las importaciones
from flask import jsonify, render_template, request, send_file, url_for, current_app
import json
from flask_login import login_required
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from sqlalchemy import func, desc
import numpy as np
from io import BytesIO
import base64
import matplotlib.pyplot as plt
from app import db
from app.reportes import reportes
from app.models import Siembra, Corte, Variedad, Flor, Color, FlorColor, BloqueCamaLado, Bloque, Cama, Lado, Area, Densidad
from datetime import datetime, timedelta

def generar_grafico_curva(puntos_curva, variedad_info, ciclo_vegetativo_promedio, ciclo_total_promedio):
    """
    Genera un gráfico mejorado para la curva de producción con suavizado adaptativo.
    
    Args:
        puntos_curva: Lista de puntos de datos para la curva
        variedad_info: Información de la variedad
        ciclo_vegetativo_promedio: Promedio del ciclo vegetativo en días
        ciclo_total_promedio: Promedio del ciclo total en días
        
    Returns:
        String en base64 con el gráfico generado
    """
    import matplotlib.pyplot as plt
    import numpy as np
    from io import BytesIO
    import base64
    from scipy.interpolate import make_interp_spline, BSpline
    
    # Extraer datos de puntos
    dias = [punto['dia'] for punto in puntos_curva]
    indices = [punto['indice_promedio'] for punto in puntos_curva]
    
    # Si hay muy pocos puntos, no intentar generar curva suavizada
    if len(dias) < 4:
        generate_smooth = False
    else:
        generate_smooth = True
    
    # Crear figura
    plt.figure(figsize=(10, 6))
    
    # Gráfico de dispersión de los puntos reales
    plt.scatter(dias, indices, color='blue', s=50, alpha=0.7, label='Datos históricos')
    
    # Añadir línea que conecta los puntos (línea base)
    plt.plot(dias, indices, 'b-', alpha=0.3)
    
    # Añadir línea suavizada si hay suficientes datos
    if generate_smooth:
        # Ordenar los puntos por día (importante para la interpolación)
        sorted_points = sorted(zip(dias, indices))
        sorted_dias = [p[0] for p in sorted_points]
        sorted_indices = [p[1] for p in sorted_points]
        
        # Verificar si hay puntos duplicados y eliminarlos
        unique_dias = []
        unique_indices = []
        last_dia = None
        
        for dia, indice in sorted_points:
            if dia != last_dia:
                unique_dias.append(dia)
                unique_indices.append(indice)
                last_dia = dia
        
        if len(unique_dias) >= 4:
            # Usar spline cúbico natural para suavizado (menos agresivo que el polinómico)
            try:
                # Crear una malla más densa para el suavizado
                dias_suavizados = np.linspace(min(unique_dias), max(unique_dias), 100)
                
                # Determinar el factor de suavizado basado en la cantidad de puntos
                # Menos puntos = menos suavizado para evitar overfitting
                k = min(3, len(unique_dias) - 1)  # k debe ser menor que el número de puntos
                
                # Crear el spline
                spl = make_interp_spline(unique_dias, unique_indices, k=k)
                indices_suavizados = spl(dias_suavizados)
                
                # Filtrar valores negativos (que no tienen sentido en índices)
                indices_suavizados = np.maximum(indices_suavizados, 0)
                
                # Limitar el máximo a un valor razonable (150% es un máximo práctico)
                max_sensible = max(indices) * 1.3
                indices_suavizados = np.minimum(indices_suavizados, max_sensible)
                
                # Plotear línea suavizada
                plt.plot(dias_suavizados, indices_suavizados, 'r--', linewidth=2, 
                         label='Tendencia (suavizado natural)')
            except Exception as e:
                # Si hay algún problema con el spline, usar un método más robusto
                try:
                    # Ajuste polinómico con grado adaptativo
                    poly_degree = min(2, len(dias) - 1)
                    z = np.polyfit(dias, indices, poly_degree)
                    p = np.poly1d(z)
                    
                    dias_suavizados = np.linspace(min(dias), max(dias), 100)
                    indices_suavizados = p(dias_suavizados)
                    
                    plt.plot(dias_suavizados, indices_suavizados, 'r--', linewidth=2, 
                            label=f'Tendencia (grado {poly_degree})')
                except:
                    print(f"Error al generar curva suavizada: {str(e)}")
    
    # Configurar gráfico
    plt.xlabel('Días desde siembra')
    plt.ylabel('Índice promedio (%)')
    plt.title(f'Curva de producción: {variedad_info}')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # Limitar el rango del eje Y para visualización más clara
    max_value = max(indices) if indices else 20
    plt.ylim(0, min(50, max_value * 1.2))  # Limitar a 50% o 1.2 veces el máximo
    
    # Limitar el eje X al ciclo total promedio calculado
    plt.xlim(0, min(ciclo_total_promedio * 1.1, 180))  # Agregar un 10% de margen, máximo 180 días
    
    # Dibujar líneas verticales para mostrar los ciclos
    if ciclo_vegetativo_promedio > 0:
        plt.axvline(x=ciclo_vegetativo_promedio, color='g', linestyle='--', alpha=0.7, 
                   label=f'Fin ciclo vegetativo ({ciclo_vegetativo_promedio} días)')
    
    if ciclo_total_promedio > 0:
        plt.axvline(x=ciclo_total_promedio, color='r', linestyle='--', alpha=0.7,
                   label=f'Fin ciclo total ({ciclo_total_promedio} días)')
    
    # Añadir anotaciones con los índices en cada punto
    for i, (dia, indice) in enumerate(zip(dias, indices)):
        plt.annotate(f'{indice}%', (dia, indice), 
                    textcoords="offset points", 
                    xytext=(0,10), 
                    ha='center')
    
    # Guardar gráfico en formato base64
    buffer = BytesIO()
    plt.tight_layout()
    plt.savefig(buffer, format='png', dpi=100)
    buffer.seek(0)
    grafico_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close()
    
    return grafico_base64

@reportes.route('/')
@login_required
def index():
    # Obtener solo las variedades que tienen siembras registradas
    variedades_con_siembras = db.session.query(Variedad)\
        .join(Siembra, Variedad.variedad_id == Siembra.variedad_id)\
        .group_by(Variedad.variedad_id)\
        .order_by(Variedad.variedad)\
        .all()
    
    return render_template('reportes/index.html', 
                          title='Reportes', 
                          variedades=variedades_con_siembras)

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

# Curva de producción por variedad

@reportes.route('/curva_produccion/<int:variedad_id>')
@login_required
def curva_produccion(variedad_id):
    """
    Genera y muestra la curva de producción específica para una variedad,
    utilizando datos históricos para determinar su ciclo natural.
    """
    # Obtener la variedad solicitada
    variedad = Variedad.query.get_or_404(variedad_id)
    
    # Obtener todas las siembras de esta variedad con sus cortes
    siembras = Siembra.query.filter_by(variedad_id=variedad_id).all()
    
    # Variables para almacenar los totales y datos acumulados
    total_siembras = 0
    siembras_con_datos = 0
    total_plantas = 0
    total_tallos = 0
    datos_curva = {}  # {día: [índices...]}
    ciclos_vegetativos = []
    ciclos_totales = []
    
    # Procesar cada siembra para extraer información
    for siembra in siembras:
        if not siembra.fecha_siembra:
            continue
            
        total_siembras += 1
        
        # Verificar que tenga cortes
        if not siembra.cortes:
            continue
            
        # Calcular total de plantas para esta siembra
        plantas_siembra = 0
        if siembra.area and siembra.densidad:
            plantas_siembra = int(siembra.area.area * siembra.densidad.valor)
            
        if plantas_siembra <= 0:
            continue  # No se puede calcular índices sin plantas
        
        siembras_con_datos += 1
        total_plantas += plantas_siembra
        
        # Determinar fechas críticas para calcular ciclos
        fecha_primer_corte = min([c.fecha_corte for c in siembra.cortes])
        fecha_ultimo_corte = max([c.fecha_corte for c in siembra.cortes])
        
        # Calcular ciclos en días
        ciclo_vegetativo = (fecha_primer_corte - siembra.fecha_siembra).days
        ciclo_total = (fecha_ultimo_corte - siembra.fecha_siembra).days
        
        # Guardar ciclos si tienen valores razonables (evitar datos extremos)
        if 40 <= ciclo_vegetativo <= 110:
            ciclos_vegetativos.append(ciclo_vegetativo)
        
        if 60 <= ciclo_total <= 150:
            ciclos_totales.append(ciclo_total)
        
        # Procesar cortes para obtener índices por día
        for corte in siembra.cortes:
            # Calcular días desde siembra y porcentaje de tallos
            dias_desde_siembra = (corte.fecha_corte - siembra.fecha_siembra).days
            indice_porcentaje = (corte.cantidad_tallos / plantas_siembra) * 100
            total_tallos += corte.cantidad_tallos
            
            # Agrupar índices por día
            if dias_desde_siembra not in datos_curva:
                datos_curva[dias_desde_siembra] = []
            
            datos_curva[dias_desde_siembra].append(indice_porcentaje)
    
    # Función para filtrar valores atípicos utilizando el método IQR
    def filtrar_outliers_iqr(valores, factor=1.5):
        """Filtra valores atípicos usando el rango intercuartil (IQR)"""
        if not valores or len(valores) < 5:  # Necesitamos suficientes datos
            return valores
            
        # Ordenar los valores para calcular cuartiles
        valores_ordenados = sorted(valores)
        n = len(valores_ordenados)
        
        # Calcular posiciones de cuartiles (Q1 = 25%, Q3 = 75%)
        q1_idx = int(n * 0.25)
        q3_idx = int(n * 0.75)
        
        # Obtener valores de cuartiles
        q1 = valores_ordenados[q1_idx]
        q3 = valores_ordenados[q3_idx]
        
        # Calcular IQR y límites para filtrado
        iqr = q3 - q1
        limite_inferior = q1 - (factor * iqr)
        limite_superior = q3 + (factor * iqr)
        
        # Filtrar valores dentro de los límites
        return [v for v in valores if limite_inferior <= v <= limite_superior]
    
    # Calcular ciclos promedio con valores filtrados
    ciclos_vegetativos_filtrados = filtrar_outliers_iqr(ciclos_vegetativos)
    ciclos_totales_filtrados = filtrar_outliers_iqr(ciclos_totales)
    
    # Determinar ciclos promedio (con valores predeterminados si no hay datos suficientes)
    if ciclos_vegetativos_filtrados:
        ciclo_vegetativo_promedio = int(sum(ciclos_vegetativos_filtrados) / len(ciclos_vegetativos_filtrados))
    else:
        # Valor predeterminado basado en análisis global
        ciclo_vegetativo_promedio = 75
    
    if ciclos_totales_filtrados:
        ciclo_total_promedio = int(sum(ciclos_totales_filtrados) / len(ciclos_totales_filtrados))
    else:
        # Valor predeterminado basado en análisis global
        ciclo_total_promedio = 84
    
    # IMPORTANTE: Nunca permitir que el ciclo total sea mayor al máximo observado
    # En el análisis se vio que el máximo es 93 días
    MAXIMO_CICLO_ABSOLUTO = 93
    ciclo_total_promedio = min(ciclo_total_promedio, MAXIMO_CICLO_ABSOLUTO)
    
    # Validar coherencia entre los ciclos
    if ciclo_vegetativo_promedio >= ciclo_total_promedio:
        # Ajustar ciclo vegetativo para mantener coherencia
        ciclo_vegetativo_promedio = max(45, ciclo_total_promedio - 10)
    
    # Calcular ciclo productivo
    ciclo_productivo_promedio = ciclo_total_promedio - ciclo_vegetativo_promedio
    
    # IMPORTANTE: Filtrar puntos del análisis que excedan el ciclo real
    # Eliminar puntos más allá del ciclo total + un pequeño margen
    margen_extension = int(ciclo_total_promedio * 0.1)  # 10% de margen adicional
    dias_permitidos = {dia: indices for dia, indices in datos_curva.items() 
                     if dia <= ciclo_total_promedio + margen_extension}
    datos_curva = dias_permitidos
    
    # Generar puntos para la curva filtrando valores atípicos por día
    puntos_curva = []
    
    # Punto inicial (día 0, valor 0)
    puntos_curva.append({
        'dia': 0,
        'indice_promedio': 0,
        'num_datos': siembras_con_datos,
        'min_indice': 0,
        'max_indice': 0
    })
    
    # Procesar días con datos
    for dia, indices in sorted(datos_curva.items()):
        # Filtrar valores extremos para cada día
        indices_filtrados = filtrar_outliers_iqr(indices) if len(indices) >= 5 else indices
        
        if indices_filtrados:
            indice_promedio = sum(indices_filtrados) / len(indices_filtrados)
            
            puntos_curva.append({
                'dia': dia,
                'indice_promedio': round(indice_promedio, 2),
                'num_datos': len(indices),
                'min_indice': round(min(indices_filtrados), 2) if indices_filtrados else 0,
                'max_indice': round(max(indices_filtrados), 2) if indices_filtrados else 0
            })
    
    # Ordenar puntos por día para asegurar continuidad
    puntos_curva.sort(key=lambda x: x['dia'])
    
    # Verificar si tenemos un punto final cerca del ciclo total
    tiene_punto_final = any(p['dia'] > ciclo_total_promedio * 0.85 for p in puntos_curva)

    # Si no tenemos puntos cercanos al final, añadir un solo punto para el ciclo total
    if not tiene_punto_final:
        # Factor de reducción proporcional a la distancia
        factor_reduccion = 0.3 + (distancia_porcentual * 0.5)
        valor_final = ultimo_punto['indice_promedio'] * (1 - factor_reduccion)
        
        # Añadir el punto final exactamente en el ciclo total
        puntos_curva.append({
            'dia': ciclo_total_promedio,
            'indice_promedio': round(valor_final, 2),
            'num_datos': 1,
            'min_indice': round(valor_final * 0.9, 2),
            'max_indice': round(valor_final * 1.1, 2)
        })
        
        # Encontrar la posición de inserción
        idx = 0
        while idx < len(puntos_curva) and puntos_curva[idx]['dia'] < ciclo_vegetativo_promedio:
            idx += 1
            
        puntos_curva.insert(idx, nuevo_punto)
    
    # Verificar si tenemos un punto para el ciclo total, añadirlo si no existe o está lejos
    tiene_punto_ciclo_total = any(abs(p['dia'] - ciclo_total_promedio) < 7 for p in puntos_curva)
    
    if not tiene_punto_ciclo_total:
        # Para el punto de fin de ciclo, usar una tendencia descendente
        # MEJORA: Ajustar el valor basado en puntos cercanos para que sea más realista
        puntos_relevantes = sorted([p for p in puntos_curva if p['dia'] > ciclo_total_promedio * 0.7], 
                                 key=lambda x: x['dia'])
        
        # Si tenemos puntos cercanos, usar su tendencia
        if puntos_relevantes:
            # Tomar el último punto relevante
            ultimo_indice = puntos_relevantes[-1]['indice_promedio']
            dias_hasta_fin = ciclo_total_promedio - puntos_relevantes[-1]['dia']
            
            # Calcular tasa de descenso basada en la tendencia de los últimos puntos
            if len(puntos_relevantes) >= 2 and dias_hasta_fin > 0:
                tasa_descenso = (puntos_relevantes[-2]['indice_promedio'] - ultimo_indice) / \
                               (puntos_relevantes[-1]['dia'] - puntos_relevantes[-2]['dia'])
                
                # Proyectar valor final
                valor_final = max(0.5, ultimo_indice - (tasa_descenso * dias_hasta_fin))
            else:
                # Si no hay suficientes puntos para calcular tendencia
                valor_final = ultimo_indice * 0.5  # 50% del último valor conocido
        else:
            # Si no hay puntos cercanos, usar un valor estimado bajo
            promedio_global = sum(p['indice_promedio'] for p in puntos_curva) / len(puntos_curva)
            valor_final = promedio_global * 0.3  # 30% del promedio global
        
        puntos_curva.append({
            'dia': ciclo_total_promedio,
            'indice_promedio': round(valor_final, 2),
            'num_datos': 1,  # Indicar que es un punto sintético
            'min_indice': round(valor_final * 0.9, 2),
            'max_indice': round(valor_final * 1.1, 2)
        })
    
    # IMPORTANTE: Realizar una última verificación para remover puntos más allá del ciclo total
    # Esto garantiza que el gráfico nunca muestre datos más allá del ciclo real
    puntos_curva = [p for p in puntos_curva if p['dia'] <= ciclo_total_promedio + margen_extension]
    
    # Generar el gráfico optimizado
    grafico_curva = None
    if puntos_curva:
        grafico_curva = generar_grafico_curva_mejorado(
            puntos_curva,
            variedad.variedad,
            ciclo_vegetativo_promedio,
            ciclo_total_promedio
        )
    
    # Datos para mostrar en la plantilla
    datos_adicionales = {
        'total_siembras': total_siembras,
        'siembras_con_datos': siembras_con_datos,
        'total_plantas': total_plantas,
        'total_tallos': total_tallos,
        'promedio_produccion': round((total_tallos / total_plantas * 100), 2) if total_plantas > 0 else 0,
        'ciclo_vegetativo': ciclo_vegetativo_promedio,
        'ciclo_productivo': ciclo_productivo_promedio,
        'ciclo_total': ciclo_total_promedio
    }
    
    return render_template('reportes/curva_produccion.html',
                          title=f'Curva de Producción: {variedad.variedad}',
                          variedad=variedad,
                          puntos_curva=puntos_curva,
                          grafico_curva=grafico_curva,
                          datos_adicionales=datos_adicionales)

def generar_grafico_curva_mejorado(puntos_curva, variedad_info, ciclo_vegetativo_promedio, ciclo_total_promedio):
    """
    Genera un gráfico mejorado para la curva de producción con interpolación y suavizado adaptativo.
    
    Args:
        puntos_curva: Lista de puntos {dia, indice_promedio, ...}
        variedad_info: Nombre de la variedad para el título
        ciclo_vegetativo_promedio: Días promedio del ciclo vegetativo
        ciclo_total_promedio: Días promedio del ciclo total
        
    Returns:
        Imagen codificada en base64 del gráfico generado
    """
    import matplotlib.pyplot as plt
    import numpy as np
    from scipy.interpolate import make_interp_spline, splrep, splev
    from io import BytesIO
    import base64
    
    # Verificar que tengamos datos suficientes
    if not puntos_curva or len(puntos_curva) < 3:
        # Crear un gráfico con mensaje informativo
        plt.figure(figsize=(10, 6))
        plt.text(0.5, 0.5, "Datos insuficientes para generar curva", 
                ha='center', va='center', fontsize=14)
        plt.tight_layout()
        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        grafico_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        plt.close()
        return grafico_base64
    
    # Extraer datos para el gráfico
    dias = [p['dia'] for p in puntos_curva]
    indices = [p['indice_promedio'] for p in puntos_curva]
    
    # Crear figura
    plt.figure(figsize=(10, 6))
    
    # Gráfico de dispersión con los puntos reales
    plt.scatter(dias, indices, color='blue', s=50, alpha=0.7, label='Datos históricos')
    
    # Generar curva suavizada si hay suficientes puntos
    if len(dias) >= 4:
        try:
            # Crear una malla más densa para el suavizado
            dias_suavizados = np.linspace(min(dias), max(dias), 100)
            
            # Factor de suavizado adaptativo basado en el número de puntos
            # Menos puntos = menos suavizado para evitar overfitting
            s_factor = len(dias) / 3  # Ajustado según análisis de datos
            
            # Usar el grado k del spline según la cantidad de puntos disponibles
            tck = splrep(dias_ordenados, indices_ordenados, s=s_factor, k=min(3, n_points-1))
            indices_suavizados = splev(dias_suavizados, tck)
            
            # Asegurar que los valores tengan sentido (no negativos, sin picos extremos)
            indices_suavizados = np.maximum(indices_suavizados, 0)  # No valores negativos
            
            # Limitar picos extremos
            max_indice = max(indices) * 1.2  # Hasta 20% más que el máximo observado
            indices_suavizados = np.minimum(indices_suavizados, max_indice)
            
            # Dibujar la curva suavizada
            plt.plot(dias_suavizados, indices_suavizados, 'r--', 
                    linewidth=2, label='Tendencia (suavizado natural)')
        except Exception as e:
            print(f"Error al generar curva suavizada: {e}")
            # Si falla el suavizado, conectar los puntos con líneas simples
            plt.plot(dias, indices, 'r--', linewidth=1.5, 
                   label='Tendencia (interpolación lineal)')
    
    # Configurar el gráfico
    plt.xlabel('Días desde siembra')
    plt.ylabel('Índice promedio (%)')
    plt.title(f'Curva de producción: {variedad_info}')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # Establecer límites en los ejes
    # Eje Y: limitar al máximo observado con un margen del 20%
    max_value = max(indices) if indices else 20
    plt.ylim(0, min(50, max_value * 1.2))  # Máximo 50% o 1.2 veces el valor máximo
    
    # Establecer límites del eje X exactamente desde 0 hasta el ciclo total
    plt.xlim(0, ciclo_total_promedio)
    
    # Añadir líneas verticales para los ciclos
    plt.axvline(x=ciclo_vegetativo_promedio, color='g', linestyle='--', alpha=0.7,
               label=f'Fin ciclo vegetativo ({ciclo_vegetativo_promedio} días)')
    
    plt.axvline(x=ciclo_total_promedio, color='r', linestyle='--', alpha=0.7,
               label=f'Fin ciclo total ({ciclo_total_promedio} días)')
    
    # Añadir anotaciones con los valores
    for dia, indice in zip(dias, indices):
        plt.annotate(f'{indice:.2f}%', (dia, indice), 
                    textcoords="offset points", xytext=(0,10), ha='center')
    
    # Añadir nota explicativa
    plt.figtext(0.5, 0.01, 
               "Nota: La línea punteada roja representa la tendencia de producción basada en datos históricos.", 
               ha='center', fontsize=9)
    
    # Guardar el gráfico como imagen
    plt.tight_layout(rect=[0, 0.03, 1, 0.97])  # Dejar espacio para la nota
    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=100)
    buffer.seek(0)
    grafico_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close()
    
    return grafico_base64

# Agrega esta nueva función para la API JSON
@reportes.route('/api/curva_produccion/<int:variedad_id>')
@login_required
def api_curva_produccion(variedad_id):
    """
    API para obtener datos de la curva de producción en formato JSON.
    """
    # Obtener la variedad
    variedad = Variedad.query.get_or_404(variedad_id)
    
    # Obtener todas las siembras de esta variedad con sus cortes
    siembras = Siembra.query.filter_by(variedad_id=variedad_id).all()
    
    # Datos para la estructura de la respuesta
    variedad_info = {
        "id": variedad.variedad_id,
        "nombre": variedad.variedad,
        "flor": variedad.flor_color.flor.flor,
        "color": variedad.flor_color.color.color
    }
    
    # Estadísticas
    estadisticas = {
        "siembras_con_datos": 0,
        "ciclo_vegetativo": 45,  # Valor predeterminado
        "ciclo_total": 150       # Valor predeterminado
    }
    
    # Puntos para la curva
    puntos_curva = []
    
    # Para calcular promedios de ciclos
    dias_ciclo_vegetativo = []
    
    # Si no hay siembras, devolver estructura básica
    if not siembras:
        return jsonify({
            "variedad": variedad_info,
            "estadisticas": estadisticas,
            "puntos_curva": []
        })
    
    # Procesar las siembras
    for siembra in siembras:
        if siembra.cortes:
            estadisticas["siembras_con_datos"] += 1
            
            # Calcular ciclo vegetativo (días hasta primer corte)
            if siembra.fecha_inicio_corte and siembra.fecha_siembra:
                dias = (siembra.fecha_inicio_corte - siembra.fecha_siembra).days
                dias_ciclo_vegetativo.append(dias)
    
    # Calcular ciclo vegetativo promedio
    if dias_ciclo_vegetativo:
        estadisticas["ciclo_vegetativo"] = int(sum(dias_ciclo_vegetativo) / len(dias_ciclo_vegetativo))
    
    # Calcular días de cada corte y su valor promedio
    cortes_por_dia = {}
    
    for siembra in siembras:
        if siembra.cortes:
            # Densidad y área para calcular índices
            densidad = siembra.densidad.valor if siembra.densidad else 1.0
            area = siembra.area.area if siembra.area else 1.0
            total_plantas = int(area * densidad)
            
            # Si no hay plantas, continuar con la siguiente siembra
            if total_plantas <= 0:
                continue
                
            for corte in siembra.cortes:
                # Calcular días desde siembra
                dias = (corte.fecha_corte - siembra.fecha_siembra).days
                
                # Calcular índice (tallos / plantas)
                indice = corte.cantidad_tallos / total_plantas
                
                # Agrupar por día
                if dias not in cortes_por_dia:
                    cortes_por_dia[dias] = {
                        "indices": [],
                        "num_corte": []
                    }
                
                cortes_por_dia[dias]["indices"].append(indice)
                cortes_por_dia[dias]["num_corte"].append(corte.num_corte)
    
    # Convertir datos agrupados a formato para la curva
    for dia, datos in sorted(cortes_por_dia.items()):
        indices = datos["indices"]
        num_cortes = datos["num_corte"]
        
        if indices:
            # Promedio de índices para este día
            promedio = sum(indices) / len(indices)
            # Moda del número de corte (el más frecuente)
            from collections import Counter
            contador = Counter(num_cortes)
            num_corte_comun = contador.most_common(1)[0][0]
            
            # Crear punto para la curva
            punto = {
                "dia": dia,
                "indice": max(indices),
                "promedio": promedio,
                "min": min(indices),
                "max": max(indices),
                "num_datos": len(indices),
                "corte": f"C{num_corte_comun}"
            }
            
            puntos_curva.append(punto)
    
    # Añadir punto inicial (siembra)
    if puntos_curva:
        puntos_curva.insert(0, {
            "dia": 0,
            "indice": 0,
            "promedio": 0,
            "min": 0,
            "max": 0,
            "num_datos": estadisticas["siembras_con_datos"],
            "corte": "Siembra"
        })
    
    # Calcular ciclo total
    if puntos_curva and len(puntos_curva) > 1:
        estadisticas["ciclo_total"] = puntos_curva[-1]["dia"]
    
    # Devolver resultado
    return jsonify({
        "variedad": variedad_info,
        "estadisticas": estadisticas,
        "puntos_curva": puntos_curva
    })

@reportes.route('/curva_produccion_interactiva/<int:variedad_id>')
@login_required
def curva_produccion_interactiva(variedad_id):
    """
    Vista para la curva de producción interactiva usando React
    """
    # Obtener la variedad
    variedad = Variedad.query.get_or_404(variedad_id)
    
    return render_template('reportes/curva_produccion_interactiva.html',
                          title=f'Curva de Producción (Interactiva): {variedad.variedad}',
                          variedad=variedad,
                          api_url=url_for('reportes.api_curva_produccion', variedad_id=variedad_id))

# Añadir a app/reportes/routes.py

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

def generar_grafico_curva_mejorado(puntos_curva, variedad_info, ciclo_vegetativo_promedio, ciclo_total_promedio):
    """
    Genera un gráfico optimizado para la curva de producción con límites ajustados al ciclo real.
    
    Args:
        puntos_curva: Lista de puntos {dia, indice_promedio, ...}
        variedad_info: Nombre de la variedad para el título
        ciclo_vegetativo_promedio: Días promedio del ciclo vegetativo
        ciclo_total_promedio: Días promedio del ciclo total
        
    Returns:
        Imagen codificada en base64 del gráfico generado
    """
    import matplotlib.pyplot as plt
    import numpy as np
    from scipy.interpolate import make_interp_spline, splrep, splev
    from io import BytesIO
    import base64
    
    # Verificar que tengamos datos suficientes
    if not puntos_curva or len(puntos_curva) < 3:
        plt.figure(figsize=(10, 6))
        plt.text(0.5, 0.5, "Datos insuficientes para generar curva", 
                ha='center', va='center', fontsize=14)
        plt.tight_layout()
        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        grafico_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        plt.close()
        return grafico_base64
    
    # IMPORTANTE: Filtrar puntos más allá del ciclo total real
    # Solo mantener puntos dentro del ciclo real + un pequeño margen
    margen_adicional = int(ciclo_total_promedio * 0.1)  # 10% de margen como máximo
    limite_maximo_dias = ciclo_total_promedio + margen_adicional
    
    # Filtrar puntos más allá del ciclo total real (ESTRICTO)
    puntos_filtrados = [p for p in puntos_curva if p['dia'] <= ciclo_total_promedio]
    
    # Extraer datos para el gráfico
    dias = [p['dia'] for p in puntos_filtrados]
    indices = [p['indice_promedio'] for p in puntos_filtrados]
    
    # Crear figura
    plt.figure(figsize=(10, 6))
    
    # Gráfico de dispersión con los puntos reales
    plt.scatter(dias, indices, color='blue', s=50, alpha=0.7, label='Datos históricos')
    
    # Generar curva suavizada si hay suficientes puntos
    if len(dias) >= 4:
        try:
            # Crear una malla más densa para el suavizado que cubra exactamente 
            # desde 0 hasta el ciclo total real (no más allá)
            dias_suavizados = np.linspace(0, ciclo_total_promedio, 100)
            
            # Factor de suavizado adaptativo basado en el número de puntos
            # Menos puntos = menos suavizado para evitar overfitting
            s_factor = len(dias) / 3  # Ajustado según análisis de datos
            
            # Generar la curva suavizada usando splines
            tck = splrep(dias, indices, s=s_factor)
            indices_suavizados = splev(dias_suavizados, tck)
            
            # Asegurar que los valores tengan sentido (no negativos, sin picos extremos)
            indices_suavizados = np.maximum(indices_suavizados, 0)  # No valores negativos
            
            # Limitar picos extremos
            max_indice = max(indices) * 1.2  # Hasta 20% más que el máximo observado
            indices_suavizados = np.minimum(indices_suavizados, max_indice)
            
            # Dibujar la curva suavizada
            plt.plot(dias_suavizados, indices_suavizados, 'r--', 
                    linewidth=2, label='Tendencia (suavizado natural)')
        except Exception as e:
            print(f"Error al generar curva suavizada: {e}")
            # Si falla el suavizado, conectar los puntos con líneas simples
            plt.plot(dias, indices, 'r--', linewidth=1.5, 
                   label='Tendencia (interpolación lineal)')
    
    # Configurar el gráfico
    plt.xlabel('Días desde siembra')
    plt.ylabel('Índice promedio (%)')
    plt.title(f'Curva de producción: {variedad_info}')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # Establecer límites en los ejes
    # Eje Y: limitar al máximo observado con un margen del 20%
    max_value = max(indices) if indices else 20
    plt.ylim(0, min(50, max_value * 1.2))  # Máximo 50% o 1.2 veces el valor máximo
    
    # Eje X: mostrar EXACTAMENTE desde 0 hasta el ciclo total real + pequeño margen
    # AQUÍ ESTÁ EL CAMBIO CLAVE: Limitar el eje X al ciclo total real + margen (5-10%)
    margen_grafico = ciclo_total_promedio * 0.08  # 8% de margen
    plt.xlim(0, ciclo_total_promedio + margen_grafico)
    
    # Añadir líneas verticales para los ciclos
    plt.axvline(x=ciclo_vegetativo_promedio, color='g', linestyle='--', alpha=0.7,
               label=f'Fin ciclo vegetativo ({ciclo_vegetativo_promedio} días)')
    
    plt.axvline(x=ciclo_total_promedio, color='r', linestyle='--', alpha=0.7,
               label=f'Fin ciclo total ({ciclo_total_promedio} días)')
    
    for p in puntos_filtrados:
    # Solo anotar puntos con datos reales (más de 1 registro)
        if p['num_datos'] > 1:
            plt.annotate(f'{p["indice_promedio"]:.2f}%', 
                        (p['dia'], p['indice_promedio']), 
                        textcoords="offset points", 
                        xytext=(0,10), 
                        ha='center')
    
    # Añadir nota explicativa
    plt.figtext(0.5, 0.01, 
               "Nota: La línea punteada roja representa la tendencia de producción ajustada.", 
               ha='center', fontsize=9)
    
    # Guardar el gráfico como imagen
    plt.tight_layout(rect=[0, 0.03, 1, 0.97])  # Dejar espacio para la nota
    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=100)
    buffer.seek(0)
    grafico_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close()
    
    return grafico_base64
