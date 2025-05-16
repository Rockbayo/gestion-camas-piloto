"""
Módulo para calcular estadísticas y métricas relevantes para curvas de producción

Este módulo proporciona funciones optimizadas para calcular índices, filtrar valores
atípicos y generar estadísticas reutilizables en diferentes partes de la aplicación.
"""
import numpy as np
from datetime import datetime, timedelta

def calcular_indice_produccion(cantidad_tallos, area, densidad):
    """
    Calcula el índice de producción a partir de cantidad de tallos y plantas
    
    Args:
        cantidad_tallos: Cantidad de tallos cortados
        area: Área en metros cuadrados
        densidad: Densidad de siembra (plantas/m²)
        
    Returns:
        Índice de producción en porcentaje
    """
    plantas_totales = area * densidad
    if plantas_totales <= 0:
        return 0
    return (cantidad_tallos / plantas_totales) * 100

def filtrar_outliers_iqr(valores, factor=1.5):
    """
    Filtra valores atípicos usando el método del rango intercuartil (IQR)
    
    Args:
        valores: Lista de valores numéricos
        factor: Factor de multiplicación para el IQR (por defecto 1.5)
        
    Returns:
        Lista de valores filtrados sin los valores atípicos
    """
    if not valores or len(valores) < 5:  # Necesitamos suficientes datos
        return valores
        
    # Crear un array numpy para cálculos más eficientes
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

def analizar_ciclos_variedad(siembras):
    """
    Analiza los ciclos vegetativo y productivo para una lista de siembras
    
    Args:
        siembras: Lista de objetos Siembra con cortes
        
    Returns:
        Diccionario con los ciclos vegetativo y total promedio,
        además de estadísticas adicionales
    """
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
            if 30 <= ciclo_vegetativo <= 110:  # Filtrar valores atípicos
                datos_ciclo_vegetativo.append(ciclo_vegetativo)
            
            # Ciclo total: días hasta el último corte
            ultimo_corte = cortes_ordenados[-1]
            ciclo_total = (ultimo_corte.fecha_corte - siembra.fecha_siembra).days
            if 45 <= ciclo_total <= 150:  # Filtrar valores atípicos
                datos_ciclo_total.append(ciclo_total)
            
            # Número de cortes
            datos_num_cortes.append(len(cortes_ordenados))
    
    # Filtrar datos atípicos usando IQR
    datos_ciclo_vegetativo = filtrar_outliers_iqr(datos_ciclo_vegetativo)
    datos_ciclo_total = filtrar_outliers_iqr(datos_ciclo_total)
    
    # Calcular promedios
    ciclo_vegetativo_promedio = (
        sum(datos_ciclo_vegetativo) / len(datos_ciclo_vegetativo) 
        if datos_ciclo_vegetativo else 65  # Valor por defecto
    )
    
    ciclo_total_promedio = (
        sum(datos_ciclo_total) / len(datos_ciclo_total)
        if datos_ciclo_total else 90  # Valor por defecto
    )
    
    cortes_promedio = (
        sum(datos_num_cortes) / len(datos_num_cortes)
        if datos_num_cortes else 0
    )
    
    # Asegurar que el ciclo vegetativo sea menor que el ciclo total
    if ciclo_vegetativo_promedio >= ciclo_total_promedio:
        ciclo_vegetativo_promedio = ciclo_total_promedio * 0.7  # Ajuste razonable
    
    # Valores finales redondeados a enteros para días
    return {
        'ciclo_vegetativo': int(round(ciclo_vegetativo_promedio)),
        'ciclo_total': int(round(ciclo_total_promedio)),
        'ciclo_productivo': int(round(ciclo_total_promedio - ciclo_vegetativo_promedio)),
        'cortes_promedio': round(cortes_promedio, 1),
        'num_siembras': len(siembras),
        'siembras_con_datos': len([s for s in siembras if s.cortes])
    }

def agrupar_puntos_curva(cortes, siembras, dias_max=93):
    """
    Agrupa los puntos para la curva de producción por días desde siembra
    
    Args:
        cortes: Lista de objetos Corte
        siembras: Lista de objetos Siembra
        dias_max: Días máximos a considerar
        
    Returns:
        Lista de puntos {dia, indice_promedio, min_indice, max_indice, num_datos}
    """
    # Crear diccionario para agrupar índices por día
    datos_por_dia = {}
    
    # Crear diccionario para consulta eficiente de siembras
    siembras_dict = {s.siembra_id: s for s in siembras}
    
    # Procesar cada corte
    for corte in cortes:
        # Obtener la siembra asociada
        siembra = siembras_dict.get(corte.siembra_id)
        if not siembra or not siembra.fecha_siembra:
            continue
            
        # Calcular días desde siembra
        dias_desde_siembra = (corte.fecha_corte - siembra.fecha_siembra).days
        
        # Limitar a los días máximos
        if dias_desde_siembra > dias_max:
            continue
            
        # Calcular índice de producción
        if not siembra.area or not siembra.densidad or not siembra.densidad.valor:
            continue
            
        plantas_totales = siembra.area.area * siembra.densidad.valor
        if plantas_totales <= 0:
            continue
            
        indice = (corte.cantidad_tallos / plantas_totales) * 100
        
        # Agrupar por día
        if dias_desde_siembra not in datos_por_dia:
            datos_por_dia[dias_desde_siembra] = []
        
        datos_por_dia[dias_desde_siembra].append(indice)
    
    # Procesar los datos agrupados
    puntos_curva = []
    
    # Añadir punto inicial (día 0, índice 0)
    puntos_curva.append({
        'dia': 0,
        'indice_promedio': 0,
        'min_indice': 0,
        'max_indice': 0,
        'num_datos': len(siembras)
    })
    
    # Procesar cada día con datos
    for dia, indices in sorted(datos_por_dia.items()):
        # Filtrar valores atípicos
        indices_filtrados = filtrar_outliers_iqr(indices) if len(indices) >= 5 else indices
        
        if indices_filtrados:
            indice_promedio = sum(indices_filtrados) / len(indices_filtrados)
            indice_min = min(indices_filtrados)
            indice_max = max(indices_filtrados)
            
            puntos_curva.append({
                'dia': dia,
                'indice_promedio': round(indice_promedio, 2),
                'min_indice': round(indice_min, 2),
                'max_indice': round(indice_max, 2),
                'num_datos': len(indices)
            })
    
    # Ordenar puntos por día
    puntos_curva.sort(key=lambda p: p['dia'])
    
    return puntos_curva