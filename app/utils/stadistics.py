"""
Módulo para cálculo de estadísticas y métricas de producción.

Mejoras:
- Mejor organización del código
- Funciones más modulares
- Documentación más clara
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any
from decimal import Decimal
import numpy as np
from app.utils.number_utils import to_decimal, to_int
from app.utils.data_utils import calc_indice_aprovechamiento, calc_plantas_totales

class ProductionStatistics:
    """
    Clase para cálculo de estadísticas de producción.
    """
    
    @staticmethod
    def calcular_indice_produccion(cantidad_tallos, area, densidad) -> Decimal:
        """
        Calcula el índice de producción (tallos/plantas en porcentaje).
        """
        plantas_totales = to_decimal(area) * to_decimal(densidad)
        if plantas_totales <= 0:
            return Decimal('0.0')
        return (to_decimal(cantidad_tallos) / plantas_totales) * Decimal('100')
    
    @staticmethod
    def analizar_ciclos_variedad(siembras: List) -> Dict[str, Any]:
        """
        Analiza los ciclos vegetativo y productivo para una lista de siembras.
        
        Returns:
            Dict con ciclos vegetativo, total, productivo y estadísticas
        """
        datos = {
            'ciclo_vegetativo': [],
            'ciclo_total': [],
            'num_cortes': []
        }
        
        for siembra in siembras:
            if not siembra.cortes:
                continue
                
            cortes_ordenados = sorted(siembra.cortes, key=lambda c: c.fecha_corte)
            primer_corte = cortes_ordenados[0]
            ultimo_corte = cortes_ordenados[-1]
            
            # Ciclo vegetativo (días hasta primer corte)
            ciclo_veg = (primer_corte.fecha_corte - siembra.fecha_siembra).days
            if 30 <= ciclo_veg <= 110:
                datos['ciclo_vegetativo'].append(ciclo_veg)
            
            # Ciclo total (días hasta último corte)
            ciclo_total = (ultimo_corte.fecha_corte - siembra.fecha_siembra).days
            if 45 <= ciclo_total <= 150:
                datos['ciclo_total'].append(ciclo_total)
            
            # Número de cortes
            datos['num_cortes'].append(len(cortes_ordenados))
        
        # Filtrar outliers
        datos['ciclo_vegetativo'] = ProductionStatistics._filtrar_outliers(datos['ciclo_vegetativo'])
        datos['ciclo_total'] = ProductionStatistics._filtrar_outliers(datos['ciclo_total'])
        
        # Calcular promedios
        ciclo_veg_prom = np.mean(datos['ciclo_vegetativo']) if datos['ciclo_vegetativo'] else 65
        ciclo_total_prom = np.mean(datos['ciclo_total']) if datos['ciclo_total'] else 90
        cortes_prom = np.mean(datos['num_cortes']) if datos['num_cortes'] else 0
        
        # Asegurar relación lógica entre ciclos
        if ciclo_veg_prom >= ciclo_total_prom:
            ciclo_veg_prom = ciclo_total_prom * 0.7
        
        return {
            'ciclo_vegetativo': to_int(ciclo_veg_prom),
            'ciclo_total': to_int(ciclo_total_prom),
            'ciclo_productivo': to_int(ciclo_total_prom - ciclo_veg_prom),
            'cortes_promedio': round(cortes_prom, 1),
            'num_siembras': len(siembras),
            'siembras_con_datos': len([s for s in siembras if s.cortes])
        }
    
    @staticmethod
    def agrupar_puntos_curva(cortes: List, siembras: List, dias_max: int = 93) -> List[Dict]:
        """
        Agrupa puntos para curva de producción por días desde siembra.
        
        Returns:
            Lista de puntos con índice promedio, min, max y conteo
        """
        siembras_dict = {s.siembra_id: s for s in siembras}
        datos_por_dia = {}
        
        for corte in cortes:
            siembra = siembras_dict.get(corte.siembra_id)
            if not siembra or not siembra.fecha_siembra:
                continue
                
            dias = (corte.fecha_corte - siembra.fecha_siembra).days
            if dias > dias_max:
                continue
                
            plantas = calc_plantas_totales(siembra.area.area, siembra.densidad.valor)
            if plantas <= 0:
                continue
                
            indice = float(calc_indice_aprovechamiento(corte.cantidad_tallos, plantas))
            
            if dias not in datos_por_dia:
                datos_por_dia[dias] = []
            datos_por_dia[dias].append(indice)
        
        # Procesar datos agrupados
        puntos = [{
            'dia': 0,
            'indice_promedio': 0,
            'min_indice': 0,
            'max_indice': 0,
            'num_datos': len(siembras)
        }]
        
        for dia, indices in sorted(datos_por_dia.items()):
            indices_filtrados = ProductionStatistics._filtrar_outliers(indices) if len(indices) >= 5 else indices
            
            if indices_filtrados:
                puntos.append({
                    'dia': dia,
                    'indice_promedio': round(np.mean(indices_filtrados), 2),
                    'min_indice': round(min(indices_filtrados), 2),
                    'max_indice': round(max(indices_filtrados), 2),
                    'num_datos': len(indices)
                })
        
        return sorted(puntos, key=lambda p: p['dia'])
    
    @staticmethod
    def _filtrar_outliers(valores: List[float], factor: float = 1.5) -> List[float]:
        """Filtra outliers usando el método IQR."""
        if not valores or len(valores) < 5:
            return valores
            
        arr = np.array(valores)
        q1, q3 = np.percentile(arr, [25, 75])
        iqr = q3 - q1
        
        if iqr == 0:
            return valores
            
        lower = q1 - (factor * iqr)
        upper = q3 + (factor * iqr)
        return arr[(arr >= lower) & (arr <= upper)].tolist()