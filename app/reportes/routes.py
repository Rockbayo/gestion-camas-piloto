# Configuración inicial (solo una vez al principio)
import matplotlib
matplotlib.use('Agg')  # Configurar backend no interactivo

# Standard library imports
from datetime import datetime, timedelta
from io import BytesIO
import base64
import json

# Third-party imports
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from flask import jsonify, render_template, request, send_file, url_for, current_app
from flask_login import login_required
from sqlalchemy import func, desc

# Local application imports
from app import db
from app.reportes import reportes
from app.models import Siembra, Corte, Variedad, Flor, Color, FlorColor, BloqueCamaLado, Bloque, Cama, Lado, Area, Densidad

# Intento de importación de scipy (solo una vez)
SCIPY_AVAILABLE = False
try:
    from scipy.interpolate import make_interp_spline, splrep, splev
    SCIPY_AVAILABLE = True
except ImportError:
    current_app.logger.warning("Scipy no está instalado. La generación de curvas suavizadas estará limitada.")

# Configuración
def get_config_value(key, default):
    """Obtiene valores de configuración de forma segura"""
    try:
        return current_app.config.get(key, default)
    except RuntimeError:  # Para cuando no hay contexto de aplicación
        return default

MAXIMO_CICLO_ABSOLUTO = get_config_value('MAXIMO_CICLO_ABSOLUTO', 93)
SUAVIZADO_MINIMO_PUNTOS = get_config_value('SUAVIZADO_MINIMO_PUNTOS', 4)

def generar_grafico_curva_optimizado(puntos_curva, variedad_info, ciclo_vegetativo_promedio, ciclo_total_maximo):
    """
    Versión optimizada de la función para generar gráficos de curva de producción.
    
    Args:
        puntos_curva: Lista de puntos {dia, indice_promedio, ...}
        variedad_info: Nombre de la variedad para el título
        ciclo_vegetativo_promedio: Días promedio del ciclo vegetativo
        ciclo_total_maximo: Días promedio del ciclo total
        
    Returns:
        Imagen codificada en base64 del gráfico generado o None si hay error
    """
    try:
        # Verificar datos mínimos
        if not puntos_curva or len(puntos_curva) < 3:
            return generar_grafico_error("Datos insuficientes para generar curva")
        
        # Filtrar puntos más allá del ciclo total
        puntos_filtrados = [p for p in puntos_curva if p['dia'] <= ciclo_total_maximo]
        if not puntos_filtrados:
            return generar_grafico_error("No hay datos dentro del ciclo de producción")
        
        # Extraer datos
        dias = np.array([p['dia'] for p in puntos_filtrados])
        indices = np.array([p['indice_promedio'] for p in puntos_filtrados])
        
        # Configurar figura
        plt.figure(figsize=(10, 6))
        
        # Gráfico de dispersión
        plt.scatter(dias, indices, color='blue', s=50, alpha=0.7, label='Datos históricos')
        
        # Suavizado condicional
        if len(dias) >= 4 and SCIPY_AVAILABLE:
            try:
                dias_suavizados = np.linspace(0, ciclo_total_maximo, 100)
                s_factor = len(dias) / 3  # Factor de suavizado adaptativo
                
                tck = splrep(dias, indices, s=s_factor)
                indices_suavizados = splev(dias_suavizados, tck)
                
                # Asegurar valores razonables
                indices_suavizados = np.clip(indices_suavizados, 0, max(indices) * 1.2)
                
                plt.plot(dias_suavizados, indices_suavizados, 'r--', linewidth=2, 
                        label='Tendencia (suavizado natural)')
            except Exception as e:
                current_app.logger.warning(f"Error en suavizado: {str(e)}")
                plt.plot(dias, indices, 'r--', linewidth=1.5, 
                         label='Tendencia (interpolación lineal)')
        
        # Configuración del gráfico
        plt.xlabel('Días desde siembra')
        plt.ylabel('Índice promedio (%)')
        plt.title(f'Curva de producción: {variedad_info[:50]}')  # Limitar longitud del título
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        # Límites de ejes
        max_y = min(50, max(indices) * 1.2) if indices else 20
        plt.ylim(0, max_y)
        plt.xlim(0, ciclo_total_maximo)
        
        # Líneas de ciclo
        plt.axvline(x=ciclo_vegetativo_promedio, color='g', linestyle='--', alpha=0.7,
                   label=f'Fin ciclo vegetativo ({ciclo_vegetativo_promedio} días)')
        plt.axvline(x=ciclo_total_maximo, color='r', linestyle='--', alpha=0.7,
                   label=f'Fin ciclo total ({ciclo_total_maximo} días)')
        
        # Anotaciones
        for p in puntos_filtrados:
            if p['num_datos'] > 1:
                plt.annotate(f'{p["indice_promedio"]:.2f}%', 
                            (p['dia'], p['indice_promedio']), 
                            textcoords="offset points", 
                            xytext=(0,10), 
                            ha='center')
        
        # Nota al pie
        plt.figtext(0.5, 0.01, 
                   "Nota: La línea punteada roja representa la tendencia de producción ajustada.", 
                   ha='center', fontsize=9)
        
        # Guardar y retornar
        return guardar_grafico_a_base64()
        
    except Exception as e:
        current_app.logger.error(f"Error generando gráfico: {str(e)}")
        return generar_grafico_error("Error al generar el gráfico")

def generar_grafico_error(mensaje):
    """Genera un gráfico de error con el mensaje especificado"""
    plt.figure(figsize=(10, 6))
    plt.text(0.5, 0.5, mensaje, ha='center', va='center', fontsize=14)
    plt.tight_layout()
    return guardar_grafico_a_base64()

def guardar_grafico_a_base64():
    """Guarda el gráfico actual en un buffer y lo convierte a base64"""
    buffer = BytesIO()
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
def obtener_datos_variedad(variedad_id):
    """Obtiene datos consolidados para una variedad específica"""
    # Consulta optimizada para obtener información de la variedad
    variedad = db.session.query(
        Variedad.variedad_id,
        Variedad.variedad,
        Flor.flor,
        Color.color
    ).join(
        FlorColor, Variedad.flor_color_id == FlorColor.flor_color_id
    ).join(
        Flor, FlorColor.flor_id == Flor.flor_id
    ).join(
        Color, FlorColor.color_id == Color.color_id
    ).filter(
        Variedad.variedad_id == variedad_id
    ).first()
    
    if not variedad:
        return None
    
    # Consulta para siembras y cortes de esta variedad
    siembras = db.session.query(
        Siembra.siembra_id,
        Siembra.fecha_siembra,
        Siembra.fecha_inicio_corte,
        func.count(Corte.corte_id).label('total_cortes'),
        func.min(Corte.fecha_corte).label('primer_corte'),
        func.max(Corte.fecha_corte).label('ultimo_corte'),
        Area.area,
        Densidad.valor.label('densidad')
    ).outerjoin(
        Corte, Siembra.siembra_id == Corte.siembra_id
    ).join(
        Area, Siembra.area_id == Area.area_id
    ).join(
        Densidad, Siembra.densidad_id == Densidad.densidad_id
    ).filter(
        Siembra.variedad_id == variedad_id,
        Siembra.fecha_siembra.isnot(None)
    ).group_by(
        Siembra.siembra_id,
        Area.area,
        Densidad.valor
    ).all()
    
    return {
        'variedad': variedad,
        'siembras': siembras
    }

@reportes.route('/produccion_por_variedad')
@login_required
def produccion_por_variedad():
    # Consulta optimizada con joins explícitos
    results = db.session.query(
        Variedad.variedad_id,
        Variedad.variedad,
        Flor.flor,
        Color.color,
        func.sum(Corte.cantidad_tallos).label('total_tallos')
    ).select_from(Corte)\
     .join(Siembra, Corte.siembra_id == Siembra.siembra_id)\
     .join(Variedad, Siembra.variedad_id == Variedad.variedad_id)\
     .join(FlorColor, Variedad.flor_color_id == FlorColor.flor_color_id)\
     .join(Flor, FlorColor.flor_id == Flor.flor_id)\
     .join(Color, FlorColor.color_id == Color.color_id)\
     .group_by(
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
    """Obtiene estadísticas de días desde siembra hasta corte por variedad y número de corte.
    
    Returns:
        Renderiza template con datos organizados por variedad y gráficos de tendencia.
    """
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
                    x = range(len(cortes_datos))
                    y = [c['dias_promedio'] for c in cortes_datos]
                    z = np.polyfit(x, y, 1)
                    p = np.poly1d(z)
                    plt.plot(x, p(x), "r--")
                
                plt.xlabel('Número de Corte')
                plt.ylabel('Días Promedio')
                plt.title(f'Días Promedio por Corte: {variedad[:50]}')  # Limitar longitud del título
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
        current_app.logger.error(f"Error en dias_produccion: {str(e)}")
        return render_template('error.html', 
                            message="Ocurrió un error al generar el reporte de días de producción"), 500

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
    # Obtener parámetros de filtro de la URL
    filtro_periodo = request.args.get('periodo', 'completo')
    periodo_inicio = request.args.get('periodo_inicio', None)
    periodo_fin = request.args.get('periodo_fin', None)
    
    # Variables para almacenar año y semana después de procesar
    ano_inicio = None
    semana_inicio = None
    ano_fin = None
    semana_fin = None
    
    # Procesar los periodos en formato YYYYWW
    if periodo_inicio and len(periodo_inicio) == 6:
        try:
            ano_inicio = int(periodo_inicio[:4])
            semana_inicio = int(periodo_inicio[4:])
        except ValueError:
            ano_inicio = None
            semana_inicio = None
    
    if periodo_fin and len(periodo_fin) == 6:
        try:
            ano_fin = int(periodo_fin[:4])
            semana_fin = int(periodo_fin[4:])
        except ValueError:
            ano_fin = None
            semana_fin = None
    
    # Código existente para obtener la variedad y sus siembras
    variedad = Variedad.query.get_or_404(variedad_id)
    siembras = Siembra.query.filter_by(variedad_id=variedad_id).all()
    
    # Variables para datos acumulados
    total_siembras = 0
    siembras_con_datos = 0
    total_plantas = 0
    total_tallos = 0
    datos_curva = {}
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
            plantas_siembra = calc_plantas_totales(siembra.area.area, siembra.densidad.valor)
            
        if plantas_siembra <= 0:
            continue  # No se puede calcular índices sin plantas
        
        # Verificar si la siembra está dentro del período seleccionado
        if filtro_periodo != 'completo' and filtro_periodo != 'none':
            # Obtener año y semana de la siembra
            fecha_siembra = siembra.fecha_siembra
            ano_siembra = fecha_siembra.year
            semana_siembra = fecha_siembra.isocalendar()[1]  # isocalendar() retorna (año, semana, día)
            
            # Crear el valor combinado en formato YYYYWW
            periodo_siembra = ano_siembra * 100 + semana_siembra
            
            # Crear valores combinados para los periodos de filtro
            periodo_inicio_valor = ano_inicio * 100 + semana_inicio if ano_inicio and semana_inicio else None
            periodo_fin_valor = ano_fin * 100 + semana_fin if ano_fin and semana_fin else None
            
            # Aplicar el filtro con los valores combinados
            if periodo_inicio_valor is not None and periodo_fin_valor is not None:
                # Para simplificar, consideramos solo rangos dentro del mismo año o consecutivos
                if not (periodo_inicio_valor <= periodo_siembra <= periodo_fin_valor):
                    continue
        
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
            indice_porcentaje = float(calc_indice_aprovechamiento(corte.cantidad_tallos, plantas_siembra))
            total_tallos += corte.cantidad_tallos
            
            # Agrupar índices por día
            if dias_desde_siembra not in datos_curva:
                datos_curva[dias_desde_siembra] = []
            
            datos_curva[dias_desde_siembra].append(indice_porcentaje)
    
    # Función para filtrar valores atípicos utilizando el método IQR mejorado
    def filtrar_outliers_iqr(valores, factor=1.5):
        """Filtra valores atípicos usando el rango intercuartil (IQR) con mejor manejo de casos límite"""
        if not valores or len(valores) < 5:  # Necesitamos suficientes datos
            return valores
            
        # Convertir a numpy array para operaciones vectorizadas
        valores_arr = np.array(valores)
        
        # Calcular cuartiles
        q1 = np.percentile(valores_arr, 25)
        q3 = np.percentile(valores_arr, 75)
        
        # Calcular IQR y límites
        iqr = q3 - q1
        if iqr == 0:  # Si todos los valores son iguales
            return valores
            
        limite_inferior = q1 - (factor * iqr)
        limite_superior = q3 + (factor * iqr)
        
        # Filtrar valores dentro de los límites
        return valores_arr[(valores_arr >= limite_inferior) & (valores_arr <= limite_superior)].tolist()
    
    # Calcular ciclos promedio con valores filtrados
    ciclos_vegetativos_filtrados = filtrar_outliers_iqr(ciclos_vegetativos)
    ciclos_totales_filtrados = filtrar_outliers_iqr(ciclos_totales)
    
    # Determinar ciclos promedio (con valores predeterminados si no hay datos suficientes)
    if ciclos_vegetativos_filtrados:
        ciclo_vegetativo_promedio = int(sum(ciclos_vegetativos_filtrados) / len(ciclos_vegetativos_filtrados))
    else:
        # Valor predeterminado basado en análisis global
        ciclo_vegetativo_promedio = 75
    
    # Obtener el ciclo total máximo REAL observado
    ciclo_total_maximo_real = max(ciclos_totales) if ciclos_totales else 90
    
    if ciclos_totales_filtrados:
        ciclo_total_maximo = int(sum(ciclos_totales_filtrados) / len(ciclos_totales_filtrados))
    else:
        # Valor predeterminado basado en análisis global
        ciclo_total_maximo = 84
    
    # Asegurar que el ciclo total nunca exceda el máximo real observado
    ciclo_total_maximo = min(ciclo_total_maximo, ciclo_total_maximo_real)
    
    # IMPORTANTE: Nunca permitir que el ciclo total sea mayor al máximo observado
    # En el análisis se vio que el máximo es 93 días (este valor debería ser dinámico)
    MAXIMO_CICLO_ABSOLUTO = 93
    ciclo_total_maximo = min(ciclo_total_maximo, MAXIMO_CICLO_ABSOLUTO)
    
    # Validar coherencia entre los ciclos
    if ciclo_vegetativo_promedio >= ciclo_total_maximo:
        # Ajustar ciclo vegetativo para mantener coherencia
        ciclo_vegetativo_promedio = max(45, ciclo_total_maximo - 10)
    
    # Calcular ciclo productivo
    ciclo_productivo_promedio = ciclo_total_maximo - ciclo_vegetativo_promedio
    
    # Filtrar siempre los datos de la curva al ciclo máximo real
    # Eliminar puntos más allá del ciclo total máximo (sin margen adicional)
    datos_curva_filtrados = {dia: indices for dia, indices in datos_curva.items() 
                           if dia <= ciclo_total_maximo}
    datos_curva = datos_curva_filtrados
    
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
    
    # Filtrar estrictamente los puntos de la curva al ciclo total máximo
    # Sin ningún margen adicional para que tabla y gráfica coincidan exactamente
    puntos_curva = [p for p in puntos_curva if p['dia'] <= ciclo_total_maximo]
    
    # Generar el gráfico optimizado con la función modificada
    grafico_curva = None
    if puntos_curva:
        grafico_curva = generar_grafico_curva_mejorada(
            puntos_curva,
            variedad.variedad,
            ciclo_vegetativo_promedio,
            ciclo_total_maximo
        )
    
    # Preparar lista de años-semanas para el selector
    # Obtener el rango de años disponibles (usar 5 años anteriores al actual hasta 2 años después)
    from datetime import datetime
    ano_actual = datetime.now().year
    anos_disponibles = list(range(ano_actual - 5, ano_actual + 3))
    semanas_por_ano = list(range(1, 53))  # Semanas 1-52
    
    # Crear lista de periodos en formato YYYYWW
    periodos_disponibles = []
    for ano in anos_disponibles:
        for semana in semanas_por_ano:
            periodos_disponibles.append({
                'valor': f"{ano}{semana:02d}",  # Formato YYYYWW con padding (ej: 202401)
                'texto': f"{ano}-S{semana:02d}"  # Formato legible (ej: 2024-S01)
            })
    
    # Datos para mostrar en la plantilla
    datos_adicionales = {
        'total_siembras': total_siembras,
        'siembras_con_datos': siembras_con_datos,
        'total_plantas': total_plantas,
        'total_tallos': total_tallos,
        'promedio_produccion': round((total_tallos / total_plantas * 100), 2) if total_plantas > 0 else 0,
        'ciclo_vegetativo': ciclo_vegetativo_promedio,
        'ciclo_productivo': max(0, ciclo_total_maximo - ciclo_vegetativo_promedio) if ciclo_total_maximo > 0 else 0,
        'ciclo_total': ciclo_total_maximo,
        'max_ciclo_historico': max(ciclos_totales) if ciclos_totales else ciclo_total_maximo,
        'filtro_periodo': filtro_periodo,
        'periodo_inicio': periodo_inicio,
        'periodo_fin': periodo_fin
    }
    
    return render_template('reportes/curva_produccion.html',
                          title=f'Curva de Producción: {variedad.variedad}',
                          variedad=variedad,
                          puntos_curva=puntos_curva,
                          grafico_curva=grafico_curva,
                          datos_adicionales=datos_adicionales,
                          periodos_disponibles=periodos_disponibles)

def generar_grafico_curva_mejorada(puntos_curva, variedad_info, ciclo_vegetativo_promedio, ciclo_total_maximo):
    """
    Genera un gráfico para la curva de producción con mejoras en el suavizado y sin etiquetas.
    
    Args:
        puntos_curva: Lista de puntos {dia, indice_promedio, ...}
        variedad_info: Nombre de la variedad para el título
        ciclo_vegetativo_promedio: Días promedio del ciclo vegetativo
        ciclo_total_maximo: Días promedio del ciclo total
        
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
    
    # Extraer datos para el gráfico
    dias = np.array([p['dia'] for p in puntos_curva])
    indices = np.array([p['indice_promedio'] for p in puntos_curva])
    
    # Crear figura
    plt.figure(figsize=(10, 6))
    
    # Gráfico de dispersión con los puntos reales
    plt.scatter(dias, indices, color='blue', s=50, alpha=0.7, label='Datos históricos')
    
    # Generar curva suavizada mejorada si hay suficientes puntos
    if len(dias) >= 4:
        try:
            # MEJORA 1: Usar una técnica de suavizado más robusta
            # Preparación de datos para suavizado
            # Asegurar que los días están ordenados ascendentemente
            indices_ordenados = indices[np.argsort(dias)]
            dias_ordenados = np.sort(dias)
            
            # MEJORA 2: Técnica de suavizado adaptativo basada en la densidad de puntos
            # Crear una malla más densa para el suavizado con más puntos en áreas críticas
            dias_suavizados = np.linspace(0, ciclo_total_maximo, 200)  # Aumentar resolución
            
            # MEJORA 3: Factor de suavizado adaptativo más inteligente
            # Calcular distancia media entre puntos para ajustar el suavizado
            if len(dias_ordenados) > 1:
                distancias = np.diff(dias_ordenados)
                distancia_media = np.mean(distancias)
                # Factor inversamente proporcional a la densidad de datos
                densidad_factor = max(1, min(5, 10 / distancia_media)) if distancia_media > 0 else 3
            else:
                densidad_factor = 3
            
            # Factor de suavizado ajustado según densidad y cantidad de puntos
            s_factor = max(0.1, len(dias_ordenados) / densidad_factor)
            
            # MEJORA 4: Generar curva suavizada con mejor tratamiento de valores atípicos
            # Usar splines con tratamiento especial para evitar oscilaciones extrañas
            tck = splrep(dias_ordenados, indices_ordenados, s=s_factor, k=min(3, len(dias_ordenados)-1))
            indices_suavizados = splev(dias_suavizados, tck)
            
            # MEJORA 5: Post-procesamiento para evitar comportamientos erráticos
            # Asegurar valores no negativos
            indices_suavizados = np.maximum(indices_suavizados, 0)
            
            # Identificar y corregir picos y valles extremos (oscilaciones)
            # Usar suavizado de ventana móvil para detectar oscilaciones
            if len(indices_suavizados) > 5:
                ventana = 5  # Tamaño de ventana para detectar oscilaciones
                for i in range(ventana, len(indices_suavizados) - ventana):
                    # Calcular promedio local en la ventana
                    promedio_local = np.mean(indices_suavizados[i-ventana:i+ventana+1])
                    # Si el punto actual es muy diferente al promedio local, ajustarlo
                    diff = abs(indices_suavizados[i] - promedio_local)
                    if diff > promedio_local * 0.5:  # Si difiere más del 50% del promedio local
                        # Ajustar gradualmente hacia el promedio (no bruscamente)
                        indices_suavizados[i] = indices_suavizados[i] * 0.3 + promedio_local * 0.7
            
            # Limitar valores máximos a un rango razonable
            max_observado = max(indices)
            indices_suavizados = np.minimum(indices_suavizados, max_observado * 1.2)
            
            # MEJORA 6: Asegurar que la curva de tendencia tenga sentido biológico
            # La producción no debería ser alta al inicio (primeros días desde siembra)
            for i in range(min(20, len(indices_suavizados))):  # Primeros 20 días
                factor_reduccion = i / 20.0  # Factor gradual que va de 0 a 1
                indices_suavizados[i] = indices_suavizados[i] * factor_reduccion
            
            # Dibujar la curva suavizada mejorada
            plt.plot(dias_suavizados, indices_suavizados, 'r--', 
                    linewidth=2, label='Tendencia (suavizado mejorado)')
        except Exception as e:
            print(f"Error al generar curva suavizada: {e}")
            # Si falla el suavizado avanzado, intentar un método más simple
            try:
                # Interpolación lineal simple como fallback
                from scipy.interpolate import interp1d
                # Solo usar si tenemos suficientes puntos
                if len(dias_ordenados) > 1:
                    # Crear función de interpolación lineal
                    f = interp1d(dias_ordenados, indices_ordenados, 
                                kind='linear', bounds_error=False, 
                                fill_value=(0, indices_ordenados[-1]))
                    # Generar puntos suavizados
                    dias_suavizados = np.linspace(0, ciclo_total_maximo, 100)
                    indices_suavizados = f(dias_suavizados)
                    # Dibujar tendencia
                    plt.plot(dias_suavizados, indices_suavizados, 'r--', linewidth=1.5, 
                           label='Tendencia (interpolación simple)')
                else:
                    # Si solo hay un punto, no podemos interpolar
                    plt.plot([0, dias_ordenados[0]], [0, indices_ordenados[0]], 'r--', 
                           linewidth=1.5, label='Tendencia (estimada)')
            except Exception as e2:
                print(f"Error en método alternativo: {e2}")
    
    # Configurar el gráfico
    plt.xlabel('Días desde siembra')
    plt.ylabel('Índice promedio (%)')
    plt.title(f'Curva de producción: {variedad_info}')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # Establecer límites en los ejes
    # Eje Y: limitar al máximo observado con un margen del 20%
    max_value = max(indices) if indices.size > 0 else 20
    plt.ylim(0, min(50, max_value * 1.2))  # Máximo 50% o 1.2 veces el valor máximo
    
    # Eje X: mostrar EXACTAMENTE desde 0 hasta el ciclo total máximo
    plt.xlim(0, ciclo_total_maximo)
    
    # Añadir líneas verticales para los ciclos
    plt.axvline(x=ciclo_vegetativo_promedio, color='g', linestyle='--', alpha=0.7,
               label=f'Fin ciclo vegetativo ({ciclo_vegetativo_promedio} días)')
    
    plt.axvline(x=ciclo_total_maximo, color='r', linestyle='--', alpha=0.7,
               label=f'Fin ciclo total ({ciclo_total_maximo} días)')
    
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

@reportes.route('/curva_produccion_interactiva/<int:variedad_id>')
@login_required
def curva_produccion_interactiva(variedad_id):
    """
    Versión interactiva de la curva de producción que usa la misma plantilla
    que la versión estática pero es un punto de entrada separado para facilitar
    la implementación futura de funcionalidades interactivas.
    """
    # Obtener la variedad solicitada
    variedad = Variedad.query.get_or_404(variedad_id)
    
    # Para esta implementación inicial, usamos la misma plantilla que la versión estática
    return render_template('reportes/curva_produccion.html',
                          title=f'Curva de Producción: {variedad.variedad}',
                          variedad=variedad,
                          puntos_curva=[],  # Sin puntos para evitar errores
                          grafico_curva=None,  # Sin gráfico para evitar errores  
                          datos_adicionales={
                              'total_siembras': 0,
                              'siembras_con_datos': 0,
                              'total_plantas': 0,
                              'total_tallos': 0,
                              'promedio_produccion': 0,
                              'ciclo_vegetativo': 0,
                              'ciclo_productivo': 0,
                              'ciclo_total': 0,
                              'max_ciclo_historico': 0
                          })


def generar_grafico_curva_mejorada(puntos_curva, variedad_info, ciclo_vegetativo_promedio, ciclo_total_maximo):
    """
    Genera un gráfico para la curva de producción con mejoras en el suavizado y sin etiquetas.
    
    Args:
        puntos_curva: Lista de puntos {dia, indice_promedio, ...}
        variedad_info: Nombre de la variedad para el título
        ciclo_vegetativo_promedio: Días promedio del ciclo vegetativo
        ciclo_total_maximo: Días promedio del ciclo total
        
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
    
    # Extraer datos para el gráfico
    dias = np.array([p['dia'] for p in puntos_curva])
    indices = np.array([p['indice_promedio'] for p in puntos_curva])
    
    # Crear figura
    plt.figure(figsize=(10, 6))
    
    # Gráfico de dispersión con los puntos reales
    plt.scatter(dias, indices, color='blue', s=50, alpha=0.7, label='Datos históricos')
    
    # Generar curva suavizada mejorada si hay suficientes puntos
    if len(dias) >= 4:
        try:
            # MEJORA 1: Usar una técnica de suavizado más robusta
            # Preparación de datos para suavizado
            # Asegurar que los días están ordenados ascendentemente
            indices_ordenados = indices[np.argsort(dias)]
            dias_ordenados = np.sort(dias)
            
            # MEJORA 2: Técnica de suavizado adaptativo basada en la densidad de puntos
            # Crear una malla más densa para el suavizado con más puntos en áreas críticas
            dias_suavizados = np.linspace(0, ciclo_total_maximo, 200)  # Aumentar resolución
            
            # MEJORA 3: Factor de suavizado adaptativo más inteligente
            # Calcular distancia media entre puntos para ajustar el suavizado
            if len(dias_ordenados) > 1:
                distancias = np.diff(dias_ordenados)
                distancia_media = np.mean(distancias)
                # Factor inversamente proporcional a la densidad de datos
                densidad_factor = max(1, min(5, 10 / distancia_media)) if distancia_media > 0 else 3
            else:
                densidad_factor = 3
            
            # Factor de suavizado ajustado según densidad y cantidad de puntos
            s_factor = max(0.1, len(dias_ordenados) / densidad_factor)
            
            # MEJORA 4: Generar curva suavizada con mejor tratamiento de valores atípicos
            # Usar splines con tratamiento especial para evitar oscilaciones extrañas
            tck = splrep(dias_ordenados, indices_ordenados, s=s_factor, k=min(3, len(dias_ordenados)-1))
            indices_suavizados = splev(dias_suavizados, tck)
            
            # MEJORA 5: Post-procesamiento para evitar comportamientos erráticos
            # Asegurar valores no negativos
            indices_suavizados = np.maximum(indices_suavizados, 0)
            
            # Identificar y corregir picos y valles extremos (oscilaciones)
            # Usar suavizado de ventana móvil para detectar oscilaciones
            if len(indices_suavizados) > 5:
                ventana = 5  # Tamaño de ventana para detectar oscilaciones
                for i in range(ventana, len(indices_suavizados) - ventana):
                    # Calcular promedio local en la ventana
                    promedio_local = np.mean(indices_suavizados[i-ventana:i+ventana+1])
                    # Si el punto actual es muy diferente al promedio local, ajustarlo
                    diff = abs(indices_suavizados[i] - promedio_local)
                    if diff > promedio_local * 0.5:  # Si difiere más del 50% del promedio local
                        # Ajustar gradualmente hacia el promedio (no bruscamente)
                        indices_suavizados[i] = indices_suavizados[i] * 0.3 + promedio_local * 0.7
            
            # Limitar valores máximos a un rango razonable
            max_observado = max(indices)
            indices_suavizados = np.minimum(indices_suavizados, max_observado * 1.2)
            
            # MEJORA 6: Asegurar que la curva de tendencia tenga sentido biológico
            # La producción no debería ser alta al inicio (primeros días desde siembra)
            for i in range(min(20, len(indices_suavizados))):  # Primeros 20 días
                factor_reduccion = i / 20.0  # Factor gradual que va de 0 a 1
                indices_suavizados[i] = indices_suavizados[i] * factor_reduccion
            
            # Dibujar la curva suavizada mejorada
            plt.plot(dias_suavizados, indices_suavizados, 'r--', 
                    linewidth=2, label='Tendencia (suavizado mejorado)')
        except Exception as e:
            print(f"Error al generar curva suavizada: {e}")
            # Si falla el suavizado avanzado, intentar un método más simple
            try:
                # Interpolación lineal simple como fallback
                from scipy.interpolate import interp1d
                # Solo usar si tenemos suficientes puntos
                if len(dias_ordenados) > 1:
                    # Crear función de interpolación lineal
                    f = interp1d(dias_ordenados, indices_ordenados, 
                                kind='linear', bounds_error=False, 
                                fill_value=(0, indices_ordenados[-1]))
                    # Generar puntos suavizados
                    dias_suavizados = np.linspace(0, ciclo_total_maximo, 100)
                    indices_suavizados = f(dias_suavizados)
                    # Dibujar tendencia
                    plt.plot(dias_suavizados, indices_suavizados, 'r--', linewidth=1.5, 
                           label='Tendencia (interpolación simple)')
                else:
                    # Si solo hay un punto, no podemos interpolar
                    plt.plot([0, dias_ordenados[0]], [0, indices_ordenados[0]], 'r--', 
                           linewidth=1.5, label='Tendencia (estimada)')
            except Exception as e2:
                print(f"Error en método alternativo: {e2}")
    
    # Configurar el gráfico
    plt.xlabel('Días desde siembra')
    plt.ylabel('Índice promedio (%)')
    plt.title(f'Curva de producción: {variedad_info}')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # Establecer límites en los ejes
    # Eje Y: limitar al máximo observado con un margen del 20%
    max_value = max(indices) if indices.size > 0 else 20
    plt.ylim(0, min(50, max_value * 1.2))  # Máximo 50% o 1.2 veces el valor máximo
    
    # Eje X: mostrar EXACTAMENTE desde 0 hasta el ciclo total máximo
    plt.xlim(0, ciclo_total_maximo)
    
    # Añadir líneas verticales para los ciclos
    plt.axvline(x=ciclo_vegetativo_promedio, color='g', linestyle='--', alpha=0.7,
               label=f'Fin ciclo vegetativo ({ciclo_vegetativo_promedio} días)')
    
    plt.axvline(x=ciclo_total_maximo, color='r', linestyle='--', alpha=0.7,
               label=f'Fin ciclo total ({ciclo_total_maximo} días)')
    
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

                          
@reportes.route('/curva_produccion_integrada')
@login_required
def curva_produccion_integrada():
    """
    Vista integrada que permite filtrar y comparar curvas de producción
    desde múltiples dimensiones: por flor, color, variedad, tiempo, y ubicación.
    """
    # Obtener parámetros de filtro
    tipo_filtro = request.args.get('tipo_filtro', 'variedad')
    flor_id = request.args.get('flor_id', None, type=int)
    color_id = request.args.get('color_id', None, type=int)
    variedad_id = request.args.get('variedad_id', None, type=int)
    bloque_id = request.args.get('bloque_id', None, type=int)
    periodo_filtro = request.args.get('periodo_filtro', 'completo')
    periodo_inicio = request.args.get('periodo_inicio', None)
    periodo_fin = request.args.get('periodo_fin', None)
    ultimo_ciclo = request.args.get('ultimo_ciclo', 'no') == 'si'
    
    # Obtener listas para los selectores de filtro
    flores = Flor.query.order_by(Flor.flor).all()
    colores = Color.query.order_by(Color.color).all()
    variedades = Variedad.query.order_by(Variedad.variedad).all()
    bloques = Bloque.query.order_by(Bloque.bloque).all()
    
    # Título dinámico basado en filtros
    titulo = "Curvas de Producción"
    subtitulo = ""
    
    # Variables para resultados
    resultados = []
    mensaje_filtro = ""
    
    # Construir la consulta base según el tipo de filtro
    if tipo_filtro == 'flor':
        # Filtrar por tipo de flor
        if flor_id:
            flor = Flor.query.get(flor_id)
            if flor:
                titulo = f"Curvas de Producción: {flor.flor}"
                subtitulo = "Agrupado por tipo de flor"
                mensaje_filtro = f"Mostrando datos para la flor: {flor.flor}"
                
                # Obtener todas las variedades de esta flor
                variedades_filtradas = db.session.query(Variedad).\
                    join(FlorColor, Variedad.flor_color_id == FlorColor.flor_color_id).\
                    filter(FlorColor.flor_id == flor_id).all()
                
                # Procesar cada variedad
                for variedad in variedades_filtradas:
                    datos_curva = procesar_datos_curva(
                        variedad_id=variedad.variedad_id,
                        bloque_id=bloque_id,
                        periodo_filtro=periodo_filtro,
                        periodo_inicio=periodo_inicio,
                        periodo_fin=periodo_fin,
                        ultimo_ciclo=ultimo_ciclo
                    )
                    
                    if datos_curva['puntos_curva']:
                        resultados.append({
                            'variedad': variedad,
                            'datos': datos_curva
                        })
    
    elif tipo_filtro == 'color':
        # Filtrar por color
        if color_id:
            color = Color.query.get(color_id)
            if color:
                titulo = f"Curvas de Producción: Color {color.color}"
                subtitulo = "Agrupado por color"
                mensaje_filtro = f"Mostrando datos para el color: {color.color}"
                
                # Obtener todas las variedades de este color
                variedades_filtradas = db.session.query(Variedad).\
                    join(FlorColor, Variedad.flor_color_id == FlorColor.flor_color_id).\
                    filter(FlorColor.color_id == color_id).all()
                
                # Procesar cada variedad
                for variedad in variedades_filtradas:
                    datos_curva = procesar_datos_curva(
                        variedad_id=variedad.variedad_id,
                        bloque_id=bloque_id,
                        periodo_filtro=periodo_filtro,
                        periodo_inicio=periodo_inicio,
                        periodo_fin=periodo_fin,
                        ultimo_ciclo=ultimo_ciclo
                    )
                    
                    if datos_curva['puntos_curva']:
                        resultados.append({
                            'variedad': variedad,
                            'datos': datos_curva
                        })
    
    elif tipo_filtro == 'bloque':
        # Filtrar por bloque
        if bloque_id:
            bloque = Bloque.query.get(bloque_id)
            if bloque:
                titulo = f"Curvas de Producción: Bloque {bloque.bloque}"
                subtitulo = "Agrupado por bloque"
                mensaje_filtro = f"Mostrando datos para el bloque: {bloque.bloque}"
                
                # Obtener variedades sembradas en este bloque
                variedades_filtradas = db.session.query(Variedad).\
                    join(Siembra, Variedad.variedad_id == Siembra.variedad_id).\
                    join(BloqueCamaLado, Siembra.bloque_cama_id == BloqueCamaLado.bloque_cama_id).\
                    filter(BloqueCamaLado.bloque_id == bloque_id).\
                    group_by(Variedad.variedad_id).all()
                
                # Procesar cada variedad
                for variedad in variedades_filtradas:
                    datos_curva = procesar_datos_curva(
                        variedad_id=variedad.variedad_id,
                        bloque_id=bloque_id,
                        periodo_filtro=periodo_filtro,
                        periodo_inicio=periodo_inicio,
                        periodo_fin=periodo_fin,
                        ultimo_ciclo=ultimo_ciclo
                    )
                    
                    if datos_curva['puntos_curva']:
                        resultados.append({
                            'variedad': variedad,
                            'datos': datos_curva
                        })
    
    else:  # tipo_filtro == 'variedad'
        # Filtrar por variedad específica
        if variedad_id:
            variedad = Variedad.query.get(variedad_id)
            if variedad:
                titulo = f"Curva de Producción: {variedad.variedad}"
                subtitulo = f"{variedad.flor_color.flor.flor} - {variedad.flor_color.color.color}"
                mensaje_filtro = f"Mostrando datos para la variedad: {variedad.variedad}"
                
                datos_curva = procesar_datos_curva(
                    variedad_id=variedad_id,
                    bloque_id=bloque_id,
                    periodo_filtro=periodo_filtro,
                    periodo_inicio=periodo_inicio,
                    periodo_fin=periodo_fin,
                    ultimo_ciclo=ultimo_ciclo
                )
                
                if datos_curva['puntos_curva']:
                    resultados.append({
                        'variedad': variedad,
                        'datos': datos_curva
                    })
    
    # Preparar lista de años-semanas para el selector
    # Obtener el rango de años disponibles
    from datetime import datetime
    ano_actual = datetime.now().year
    anos_disponibles = list(range(ano_actual - 5, ano_actual + 3))
    semanas_por_ano = list(range(1, 53))  # Semanas 1-52
    
    # Crear lista de periodos en formato YYYYWW
    periodos_disponibles = []
    for ano in anos_disponibles:
        for semana in semanas_por_ano:
            periodos_disponibles.append({
                'valor': f"{ano}{semana:02d}",  # Formato YYYYWW con padding (ej: 202401)
                'texto': f"{ano}-S{semana:02d}"  # Formato legible (ej: 2024-S01)
            })
    
    return render_template(
        'reportes/curva_produccion_integrada.html',
        title=titulo,
        subtitulo=subtitulo,
        tipo_filtro=tipo_filtro,
        flor_id=flor_id,
        color_id=color_id,
        variedad_id=variedad_id,
        bloque_id=bloque_id,
        periodo_filtro=periodo_filtro,
        periodo_inicio=periodo_inicio,
        periodo_fin=periodo_fin,
        ultimo_ciclo=ultimo_ciclo,
        flores=flores,
        colores=colores,
        variedades=variedades,
        bloques=bloques,
        resultados=resultados,
        mensaje_filtro=mensaje_filtro,
        periodos_disponibles=periodos_disponibles
    )

def procesar_datos_curva(variedad_id, bloque_id=None, periodo_filtro='completo', 
                         periodo_inicio=None, periodo_fin=None, ultimo_ciclo=False):
    """
    Procesa los datos para generar la curva de producción según los filtros aplicados.
    
    Args:
        variedad_id: ID de la variedad
        bloque_id: ID del bloque (opcional)
        periodo_filtro: Tipo de filtrado por periodo ('completo', 'customizado')
        periodo_inicio: Periodo inicial en formato YYYYWW
        periodo_fin: Periodo final en formato YYYYWW
        ultimo_ciclo: Si es True, solo considera datos de los últimos 3 meses
        
    Returns:
        Diccionario con datos procesados para generar la curva
    """
    # Obtener la variedad
    variedad = Variedad.query.get(variedad_id)
    if not variedad:
        return {
            'puntos_curva': [],
            'ciclo_vegetativo': 0,
            'ciclo_total': 0,
            'total_siembras': 0,
            'siembras_con_datos': 0,
            'total_plantas': 0,
            'total_tallos': 0,
            'promedio_produccion': 0
        }
    
    # Construir la consulta base de siembras
    query = Siembra.query.filter(Siembra.variedad_id == variedad_id)
    
    # Añadir filtro por bloque si se especifica
    if bloque_id:
        query = query.join(BloqueCamaLado, Siembra.bloque_cama_id == BloqueCamaLado.bloque_cama_id).\
                filter(BloqueCamaLado.bloque_id == bloque_id)
    
    # Filtrar por último ciclo (últimos 3 meses) si se solicita
    if ultimo_ciclo:
        from datetime import datetime, timedelta
        fecha_limite = datetime.now() - timedelta(days=90)  # 3 meses atrás
        query = query.filter(Siembra.fecha_siembra >= fecha_limite)
    
    # Obtener todas las siembras que cumplen con los criterios
    siembras = query.all()
    
    # Variables para datos acumulados
    total_siembras = 0
    siembras_con_datos = 0
    total_plantas = 0
    total_tallos = 0
    datos_curva = {}
    ciclos_vegetativos = []
    ciclos_totales = []
    
    # Procesar periodo en formato YYYYWW
    ano_inicio = None
    semana_inicio = None
    ano_fin = None
    semana_fin = None
    
    if periodo_filtro == 'customizado' and periodo_inicio and periodo_fin:
        try:
            if len(periodo_inicio) == 6:
                ano_inicio = int(periodo_inicio[:4])
                semana_inicio = int(periodo_inicio[4:])
            
            if len(periodo_fin) == 6:
                ano_fin = int(periodo_fin[:4])
                semana_fin = int(periodo_fin[4:])
        except ValueError:
            pass
    
    # Procesar cada siembra
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
            plantas_siembra = calc_plantas_totales(siembra.area.area, siembra.densidad.valor)
            
        if plantas_siembra <= 0:
            continue  # No se puede calcular índices sin plantas
        
        # Verificar si la siembra está dentro del período seleccionado
        if periodo_filtro == 'customizado' and ano_inicio and semana_inicio and ano_fin and semana_fin:
            # Obtener año y semana de la siembra
            fecha_siembra = siembra.fecha_siembra
            ano_siembra = fecha_siembra.year
            semana_siembra = fecha_siembra.isocalendar()[1]  # isocalendar() retorna (año, semana, día)
            
            # Crear valor combinado para comparar
            periodo_siembra = ano_siembra * 100 + semana_siembra
            periodo_inicio_valor = ano_inicio * 100 + semana_inicio
            periodo_fin_valor = ano_fin * 100 + semana_fin
            
            # Verificar si está dentro del rango
            if not (periodo_inicio_valor <= periodo_siembra <= periodo_fin_valor):
                continue
        
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
            indice_porcentaje = float(calc_indice_aprovechamiento(corte.cantidad_tallos, plantas_siembra))
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
            
        # Usar numpy para cálculos estadísticos
        import numpy as np
        valores_arr = np.array(valores)
        
        # Calcular cuartiles
        q1 = np.percentile(valores_arr, 25)
        q3 = np.percentile(valores_arr, 75)
        
        # Calcular IQR y límites
        iqr = q3 - q1
        if iqr == 0:  # Si todos los valores son iguales
            return valores
            
        limite_inferior = q1 - (factor * iqr)
        limite_superior = q3 + (factor * iqr)
        
        # Filtrar valores dentro de los límites
        return valores_arr[(valores_arr >= limite_inferior) & (valores_arr <= limite_superior)].tolist()
    
    # Calcular ciclos promedio con valores filtrados
    ciclos_vegetativos_filtrados = filtrar_outliers_iqr(ciclos_vegetativos)
    ciclos_totales_filtrados = filtrar_outliers_iqr(ciclos_totales)
    
    # Determinar ciclos promedio (con valores predeterminados si no hay datos suficientes)
    if ciclos_vegetativos_filtrados:
        ciclo_vegetativo_promedio = int(sum(ciclos_vegetativos_filtrados) / len(ciclos_vegetativos_filtrados))
    else:
        ciclo_vegetativo_promedio = 75  # Valor predeterminado
    
    # Obtener el ciclo total máximo REAL observado
    ciclo_total_maximo_real = max(ciclos_totales) if ciclos_totales else 90
    
    if ciclos_totales_filtrados:
        ciclo_total_maximo = int(sum(ciclos_totales_filtrados) / len(ciclos_totales_filtrados))
    else:
        ciclo_total_maximo = 84  # Valor predeterminado
    
    # Asegurar que el ciclo total nunca exceda el máximo real observado
    ciclo_total_maximo = min(ciclo_total_maximo, ciclo_total_maximo_real)
    
    # Nunca permitir que el ciclo total sea mayor al máximo absoluto
    MAXIMO_CICLO_ABSOLUTO = 93
    ciclo_total_maximo = min(ciclo_total_maximo, MAXIMO_CICLO_ABSOLUTO)
    
    # Validar coherencia entre los ciclos
    if ciclo_vegetativo_promedio >= ciclo_total_maximo:
        ciclo_vegetativo_promedio = max(45, ciclo_total_maximo - 10)
    
    # Filtrar datos de la curva al ciclo máximo
    datos_curva_filtrados = {dia: indices for dia, indices in datos_curva.items() 
                           if dia <= ciclo_total_maximo}
    datos_curva = datos_curva_filtrados
    
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
    
    # Filtrar estrictamente los puntos de la curva al ciclo total máximo
    puntos_curva = [p for p in puntos_curva if p['dia'] <= ciclo_total_maximo]
    
    # Generar la curva ajustada (mejorada para evitar comportamientos erráticos)
    grafico_curva = None
    if puntos_curva:
        grafico_curva = generar_grafico_curva_mejorada(
            puntos_curva,
            variedad.variedad,
            ciclo_vegetativo_promedio,
            ciclo_total_maximo
        )
    
    # Preparar los datos para retornar
    return {
        'puntos_curva': puntos_curva,
        'grafico_curva': grafico_curva,
        'ciclo_vegetativo': ciclo_vegetativo_promedio,
        'ciclo_productivo': max(0, ciclo_total_maximo - ciclo_vegetativo_promedio),
        'ciclo_total': ciclo_total_maximo,
        'max_ciclo_historico': max(ciclos_totales) if ciclos_totales else ciclo_total_maximo,
        'total_siembras': total_siembras,
        'siembras_con_datos': siembras_con_datos,
        'total_plantas': total_plantas,
        'total_tallos': total_tallos,
        'promedio_produccion': round((total_tallos / total_plantas * 100), 2) if total_plantas > 0 else 0
    }