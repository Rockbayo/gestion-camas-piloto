"""
Implementación completa del importador histórico para el sistema CPC.
Esta implementación maneja la estructura específica del archivo Excel histórico.
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from app import db
from app.models import (
    Siembra, Corte, Variedad, FlorColor, Flor, Color, BloqueCamaLado,
    Bloque, Cama, Lado, Area, Densidad, Usuario, CausaPerdida, Perdida
)
from app.utils.data_utils import safe_int, safe_float
import logging

logger = logging.getLogger(__name__)

class HistoricalImporter:
    """Importador optimizado para datos históricos del CPC"""
    
    # Columnas esperadas en el Excel (índices)
    COLUMNS = {
        'BLOQUE': 0, 'CAMA': 1, 'FLOR': 2, 'COLOR': 3, 'VARIEDAD': 4,
        'FECHA_SIEMBRA': 5, 'AREA': 6, 'DENSIDAD': 7, 'FECHA_INICIO_CORTE': 8,
        'FECHA_FIN_CORTE': 9, 'CORTES_START': 10, 'CORTES_END': 24,  # Cortes 1-15
        'PERDIDAS_START': 25  # Perdidas 1-5 (cantidad, causa, fecha)
    }
    
    CAUSAS_PERDIDA_DEFAULT = [
        'DELGADOS', 'TORCIDOS', 'TRES PUNTOS', 'RAMIFICADO', 'DAÑO MECÁNICO',
        'CORTO', 'ÁCAROS', 'TRIPS', 'PSEUDOMONAS', 'DEFORMIDAD', 'OTROS'
    ]
    
    @classmethod
    def importar_historico(cls, file_path: str) -> Dict[str, Any]:
        """
        Importa datos históricos desde Excel con estructura específica del CPC.
        
        Args:
            file_path: Ruta del archivo Excel
            
        Returns:
            Dict con estadísticas de importación
        """
        try:
            # Leer Excel preservando tipos
            df = pd.read_excel(file_path, dtype=str, header=0)
            logger.info(f"Archivo cargado: {len(df)} filas")
            
            stats = cls._init_stats()
            usuario_id = cls._get_admin_user()
            
            # Procesar en transacción
            with db.session.begin():
                for index, row in df.iterrows():
                    try:
                        cls._process_historical_row(row, usuario_id, stats, index)
                    except Exception as e:
                        stats['errores'] += 1
                        stats['detalles_errores'].append({
                            'fila': index + 2,
                            'error': str(e)
                        })
                        logger.error(f"Error fila {index+2}: {e}")
                        continue
                
                # Validar si continuar
                if stats['errores'] > len(df) * 0.3:  # Más del 30% errores
                    raise Exception(f"Demasiados errores: {stats['errores']}")
            
            logger.info(f"Importación exitosa: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error importación: {e}")
            return {"error": str(e), **stats}
    
    @classmethod
    def _init_stats(cls) -> Dict[str, Any]:
        """Inicializa estadísticas de importación"""
        return {
            'siembras_creadas': 0, 'cortes_creados': 0, 'perdidas_creadas': 0,
            'causas_perdida_creadas': 0, 'errores': 0, 'detalles_errores': []
        }
    
    @classmethod
    def _get_admin_user(cls) -> int:
        """Obtiene usuario admin para registros"""
        admin = Usuario.query.filter_by(username='admin').first()
        return admin.usuario_id if admin else 1
    
    @classmethod
    def _process_historical_row(cls, row: pd.Series, usuario_id: int, stats: Dict, index: int):
        """Procesa una fila completa del histórico"""
        
        # 1. Extraer datos básicos
        bloque_nom = str(row.iloc[cls.COLUMNS['BLOQUE']]).strip()
        cama_nom = str(row.iloc[cls.COLUMNS['CAMA']]).strip()
        flor_nom = str(row.iloc[cls.COLUMNS['FLOR']]).strip().upper()
        color_nom = str(row.iloc[cls.COLUMNS['COLOR']]).strip().upper()
        variedad_nom = str(row.iloc[cls.COLUMNS['VARIEDAD']]).strip().upper()
        
        # Validar datos obligatorios
        if not all([bloque_nom, cama_nom, flor_nom, color_nom, variedad_nom]):
            raise ValueError("Datos básicos incompletos")
        
        # 2. Procesar fechas
        fecha_siembra = cls._parse_date(row.iloc[cls.COLUMNS['FECHA_SIEMBRA']])
        fecha_inicio = cls._parse_date(row.iloc[cls.COLUMNS.get('FECHA_INICIO_CORTE', 8)])
        fecha_fin = cls._parse_date(row.iloc[cls.COLUMNS.get('FECHA_FIN_CORTE', 9)])
        
        if not fecha_siembra:
            raise ValueError("Fecha siembra inválida")
        
        # 3. Procesar área y densidad
        area_val = safe_float(row.iloc[cls.COLUMNS['AREA']])
        densidad_val = safe_float(row.iloc[cls.COLUMNS['DENSIDAD']])
        
        if area_val <= 0 or densidad_val <= 0:
            raise ValueError(f"Área o densidad inválidas: {area_val}, {densidad_val}")
        
        # 4. Crear entidades
        variedad = cls._get_or_create_variedad(flor_nom, color_nom, variedad_nom)
        area = cls._get_or_create_area(area_val)
        densidad = cls._get_or_create_densidad(densidad_val)
        ubicacion = cls._get_or_create_ubicacion(bloque_nom, cama_nom)
        
        # 5. Crear siembra
        siembra = cls._create_siembra(
            ubicacion, variedad, area, densidad, fecha_siembra,
            fecha_inicio, fecha_fin, usuario_id, stats
        )
        
        # 6. Procesar cortes
        cls._process_cortes(row, siembra, fecha_inicio, usuario_id, stats)
        
        # 7. Procesar pérdidas
        cls._process_perdidas(row, siembra, usuario_id, stats)
    
    @classmethod
    def _parse_date(cls, date_val) -> Optional[datetime.date]:
        """Parsea fecha de diferentes formatos"""
        if pd.isna(date_val):
            return None
        
        try:
            if isinstance(date_val, (datetime, pd.Timestamp)):
                return date_val.date()
            
            if isinstance(date_val, str):
                for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']:
                    try:
                        return datetime.strptime(date_val, fmt).date()
                    except ValueError:
                        continue
            
            # Número de Excel
            if isinstance(date_val, (int, float)) and date_val > 25569:
                return pd.to_datetime(date_val, origin='1899-12-30', unit='D').date()
            
            return pd.to_datetime(date_val).date()
        except:
            return None
    
    @classmethod
    def _get_or_create_variedad(cls, flor: str, color: str, variedad: str) -> Variedad:
        """Crea variedad completa con flor y color"""
        
        # Flor
        flor_obj = Flor.query.filter_by(flor=flor).first()
        if not flor_obj:
            flor_obj = Flor(flor=flor, flor_abrev=flor[:10])
            db.session.add(flor_obj)
            db.session.flush()
        
        # Color
        color_obj = Color.query.filter_by(color=color).first()
        if not color_obj:
            color_obj = Color(color=color, color_abrev=color[:10])
            db.session.add(color_obj)
            db.session.flush()
        
        # FlorColor
        flor_color = FlorColor.query.filter_by(
            flor_id=flor_obj.flor_id, color_id=color_obj.color_id
        ).first()
        if not flor_color:
            flor_color = FlorColor(flor_id=flor_obj.flor_id, color_id=color_obj.color_id)
            db.session.add(flor_color)
            db.session.flush()
        
        # Variedad
        variedad_obj = Variedad.query.filter_by(variedad=variedad).first()
        if not variedad_obj:
            variedad_obj = Variedad(variedad=variedad, flor_color_id=flor_color.flor_color_id)
            db.session.add(variedad_obj)
            db.session.flush()
        
        return variedad_obj
    
    @classmethod
    def _get_or_create_area(cls, area_val: float) -> Area:
        """Crea área"""
        area_nom = f"ÁREA {area_val:.2f}m²"
        area = Area.query.filter_by(siembra=area_nom).first()
        if not area:
            area = Area(siembra=area_nom, area=area_val)
            db.session.add(area)
            db.session.flush()
        return area
    
    @classmethod
    def _get_or_create_densidad(cls, densidad_val: float) -> Densidad:
        """Crea densidad"""
        densidad_nom = f"DENSIDAD {densidad_val:.1f}"
        densidad = Densidad.query.filter_by(densidad=densidad_nom).first()
        if not densidad:
            densidad = Densidad(densidad=densidad_nom, valor=densidad_val)
            db.session.add(densidad)
            db.session.flush()
        return densidad
    
    @classmethod
    def _get_or_create_ubicacion(cls, bloque: str, cama: str) -> BloqueCamaLado:
        """Crea ubicación completa"""
        
        # Extraer lado de cama (ej: "55A" -> lado "A")
        lado = "A"
        if cama and len(cama) > 1 and cama[-1].isalpha():
            lado = cama[-1]
        
        # Bloque
        bloque_obj = Bloque.query.filter_by(bloque=bloque).first()
        if not bloque_obj:
            bloque_obj = Bloque(bloque=bloque)
            db.session.add(bloque_obj)
            db.session.flush()
        
        # Cama
        cama_obj = Cama.query.filter_by(cama=cama).first()
        if not cama_obj:
            cama_obj = Cama(cama=cama)
            db.session.add(cama_obj)
            db.session.flush()
        
        # Lado
        lado_obj = Lado.query.filter_by(lado=lado).first()
        if not lado_obj:
            lado_obj = Lado(lado=lado)
            db.session.add(lado_obj)
            db.session.flush()
        
        # Relación
        ubicacion = BloqueCamaLado.query.filter_by(
            bloque_id=bloque_obj.bloque_id,
            cama_id=cama_obj.cama_id,
            lado_id=lado_obj.lado_id
        ).first()
        
        if not ubicacion:
            ubicacion = BloqueCamaLado(
                bloque_id=bloque_obj.bloque_id,
                cama_id=cama_obj.cama_id,
                lado_id=lado_obj.lado_id
            )
            db.session.add(ubicacion)
            db.session.flush()
        
        return ubicacion
    
    @classmethod
    def _create_siembra(cls, ubicacion, variedad, area, densidad, fecha_siembra,
                       fecha_inicio, fecha_fin, usuario_id, stats) -> Siembra:
        """Crea siembra"""
        
        siembra = Siembra.query.filter_by(
            bloque_cama_id=ubicacion.bloque_cama_id,
            variedad_id=variedad.variedad_id,
            fecha_siembra=fecha_siembra
        ).first()
        
        if not siembra:
            siembra = Siembra(
                bloque_cama_id=ubicacion.bloque_cama_id,
                variedad_id=variedad.variedad_id,
                area_id=area.area_id,
                densidad_id=densidad.densidad_id,
                fecha_siembra=fecha_siembra,
                fecha_inicio_corte=fecha_inicio,
                fecha_fin_corte=fecha_fin,
                estado='Finalizada',
                usuario_id=usuario_id
            )
            db.session.add(siembra)
            db.session.flush()
            stats['siembras_creadas'] += 1
        
        return siembra
    
    @classmethod
    def _process_cortes(cls, row, siembra, fecha_inicio, usuario_id, stats):
        """Procesa cortes de la fila"""
        
        for i in range(15):  # Cortes 1-15
            col_idx = cls.COLUMNS['CORTES_START'] + i
            if col_idx < len(row):
                tallos = safe_int(row.iloc[col_idx])
                
                if tallos > 0:
                    # Calcular fecha estimada
                    if fecha_inicio:
                        fecha_corte = fecha_inicio + timedelta(days=i*7)
                    else:
                        fecha_corte = siembra.fecha_siembra + timedelta(days=65 + i*7)
                    
                    # Crear corte
                    corte = Corte.query.filter_by(
                        siembra_id=siembra.siembra_id, num_corte=i+1
                    ).first()
                    
                    if not corte:
                        corte = Corte(
                            siembra_id=siembra.siembra_id,
                            num_corte=i+1,
                            fecha_corte=fecha_corte,
                            cantidad_tallos=tallos,
                            usuario_id=usuario_id
                        )
                        db.session.add(corte)
                        stats['cortes_creados'] += 1
    
    @classmethod
    def _process_perdidas(cls, row, siembra, usuario_id, stats):
        """Procesa pérdidas de la fila (formato: PERDIDA X, CAUSA X, FECHA PERDIDA X)"""
        
        start_idx = cls.COLUMNS['PERDIDAS_START']
        
        for i in range(5):  # Hasta 5 pérdidas
            perdida_idx = start_idx + i*3      # PERDIDA X
            causa_idx = start_idx + i*3 + 1    # CAUSA X  
            fecha_idx = start_idx + i*3 + 2    # FECHA PERDIDA X
            
            if perdida_idx < len(row):
                cantidad = safe_int(row.iloc[perdida_idx])
                causa_nombre = str(row.iloc[causa_idx]).strip().upper() if causa_idx < len(row) else None
                fecha_perdida = cls._parse_date(row.iloc[fecha_idx]) if fecha_idx < len(row) else None
                
                if cantidad > 0 and causa_nombre:
                    # Obtener/crear causa
                    causa = CausaPerdida.query.filter_by(nombre=causa_nombre).first()
                    if not causa:
                        causa = CausaPerdida(
                            nombre=causa_nombre,
                            descripcion=f"Causa importada: {causa_nombre}",
                            es_predefinida=True
                        )
                        db.session.add(causa)
                        db.session.flush()
                        stats['causas_perdida_creadas'] += 1
                    
                    # Estimar fecha si no se proporcionó
                    if not fecha_perdida:
                        fecha_perdida = siembra.fecha_siembra + timedelta(days=45 + i*10)
                    
                    # Crear pérdida
                    perdida = Perdida(
                        siembra_id=siembra.siembra_id,
                        causa_id=causa.causa_id,
                        cantidad=cantidad,
                        fecha_perdida=fecha_perdida,
                        observaciones="Importado desde históricos",
                        usuario_id=usuario_id
                    )
                    db.session.add(perdida)
                    stats['perdidas_creadas'] += 1