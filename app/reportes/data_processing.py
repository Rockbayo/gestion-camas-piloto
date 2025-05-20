from datetime import datetime, timedelta
from sqlalchemy import func
from flask import current_app
from app.models import Siembra, Corte, Variedad
from .utils import filtrar_outliers_iqr, calc_plantas_totales, calc_indice_aprovechamiento

def obtener_datos_curva(variedad_id, bloque_id=None, periodo_filtro='completo', 
                       periodo_inicio=None, periodo_fin=None, ultimo_ciclo=False):
    """
    Procesa los datos para generar la curva de producción según los filtros aplicados.
    
    Returns:
        dict: Diccionario con los datos procesados para la curva
    """
    # Construir consulta base
    query = Siembra.query.filter(Siembra.variedad_id == variedad_id)
    
    if bloque_id:
        query = query.join(BloqueCamaLado).filter(BloqueCamaLado.bloque_id == bloque_id)
    
    if ultimo_ciclo:
        fecha_limite = datetime.now() - timedelta(days=90)
        query = query.filter(Siembra.fecha_siembra >= fecha_limite)
    
    # Procesar periodo en formato YYYYWW
    ano_inicio, semana_inicio, ano_fin, semana_fin = None, None, None, None
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
    
    # Variables para datos acumulados
    total_siembras = 0
    siembras_con_datos = 0
    total_plantas = 0
    total_tallos = 0
    datos_curva = {}
    ciclos_vegetativos = []
    ciclos_totales = []
    
    # Procesar cada siembra
    for siembra in query.all():
        if not siembra.fecha_siembra:
            continue
            
        total_siembras += 1
        
        if not siembra.cortes:
            continue
            
        # Calcular plantas
        plantas_siembra = calc_plantas_totales(siembra.area.area, siembra.densidad.valor) if siembra.area and siembra.densidad else 0
        if plantas_siembra <= 0:
            continue
            
        # Verificar periodo
        if periodo_filtro == 'customizado' and ano_inicio and semana_inicio and ano_fin and semana_fin:
            fecha_siembra = siembra.fecha_siembra
            ano_siembra = fecha_siembra.year
            semana_siembra = fecha_siembra.isocalendar()[1]
            periodo_siembra = ano_siembra * 100 + semana_siembra
            periodo_inicio_valor = ano_inicio * 100 + semana_inicio
            periodo_fin_valor = ano_fin * 100 + semana_fin
            
            if not (periodo_inicio_valor <= periodo_siembra <= periodo_fin_valor):
                continue
        
        siembras_con_datos += 1
        total_plantas += plantas_siembra
        
        # Calcular ciclos
        fecha_primer_corte = min(c.fecha_corte for c in siembra.cortes)
        fecha_ultimo_corte = max(c.fecha_corte for c in siembra.cortes)
        ciclo_vegetativo = (fecha_primer_corte - siembra.fecha_siembra).days
        ciclo_total = (fecha_ultimo_corte - siembra.fecha_siembra).days
        
        if 40 <= ciclo_vegetativo <= 110:
            ciclos_vegetativos.append(ciclo_vegetativo)
        if 60 <= ciclo_total <= 150:
            ciclos_totales.append(ciclo_total)
        
        # Procesar cortes
        for corte in siembra.cortes:
            dias_desde_siembra = (corte.fecha_corte - siembra.fecha_siembra).days
            indice = calc_indice_aprovechamiento(corte.cantidad_tallos, plantas_siembra)
            total_tallos += corte.cantidad_tallos
            
            if dias_desde_siembra not in datos_curva:
                datos_curva[dias_desde_siembra] = []
            datos_curva[dias_desde_siembra].append(indice)
    
    # Calcular ciclos promedio
    ciclos_vegetativos_filtrados = filtrar_outliers_iqr(ciclos_vegetativos)
    ciclos_totales_filtrados = filtrar_outliers_iqr(ciclos_totales)
    
    ciclo_vegetativo_promedio = int(sum(ciclos_vegetativos_filtrados)/len(ciclos_vegetativos_filtrados)) if ciclos_vegetativos_filtrados else 75
    ciclo_total_maximo_real = max(ciclos_totales) if ciclos_totales else 90
    ciclo_total_maximo = min(
        int(sum(ciclos_totales_filtrados)/len(ciclos_totales_filtrados)) if ciclos_totales_filtrados else 84,
        ciclo_total_maximo_real,
        MAXIMO_CICLO_ABSOLUTO
    )
    
    # Validar coherencia entre ciclos
    if ciclo_vegetativo_promedio >= ciclo_total_maximo:
        ciclo_vegetativo_promedio = max(45, ciclo_total_maximo - 10)
    
    # Filtrar y preparar puntos de la curva
    puntos_curva = [{'dia': 0, 'indice_promedio': 0, 'num_datos': siembras_con_datos, 'min_indice': 0, 'max_indice': 0}]
    
    for dia, indices in sorted((k, filtrar_outliers_iqr(v)) for k, v in datos_curva.items() if k <= ciclo_total_maximo):
        if indices:
            puntos_curva.append({
                'dia': dia,
                'indice_promedio': round(sum(indices)/len(indices), 2),
                'num_datos': len(indices),
                'min_indice': round(min(indices), 2),
                'max_indice': round(max(indices), 2)
            })
    
    puntos_curva.sort(key=lambda x: x['dia'])
    
    return {
        'puntos_curva': puntos_curva,
        'ciclo_vegetativo': ciclo_vegetativo_promedio,
        'ciclo_total': ciclo_total_maximo,
        'total_siembras': total_siembras,
        'siembras_con_datos': siembras_con_datos,
        'total_plantas': total_plantas,
        'total_tallos': total_tallos,
        'promedio_produccion': round((total_tallos / total_plantas * 100), 2) if total_plantas > 0 else 0
    }