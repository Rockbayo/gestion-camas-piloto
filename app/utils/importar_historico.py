import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Union
from sqlalchemy.exc import IntegrityError
from app import db
from app.models import (
    Variedad, FlorColor, Flor, Color, Siembra, Corte, BloqueCamaLado,
    Bloque, Cama, Lado, Area, Densidad, Usuario, CausaPerdida, Perdida
)
from app.utils.data_utils import safe_int, safe_float
import logging

# Configurar logging
logger = logging.getLogger(__name__)

class HistoricalImporterComplete:
    """
    Importador completo para datos históricos del CPC.
    Maneja siembras, cortes y pérdidas con estructura completa.
    """
    
    # Mapeo de columnas del archivo Excel
    COLUMN_MAPPING = {
        'BLOQUE': 0,
        'CAMA': 1,
        'FLOR': 2,
        'COLOR': 3,
        'VARIEDAD': 4,
        'FECHA_SIEMBRA': 5,
        'PERIODO': 6,
        'PLANTAS': 7,
        'DENSIDAD': 8,
        'DESBOTONE': 9,
        'FECHA_INICIO_CORTE': 10,
        'FECHA_FIN_CORTE': 11,
        'CICLO_TOTAL': 12,
        'CORTES_START': 13,  # Columnas 1-15 (índices 13-27)
        'CORTES_END': 27,
        'TALLOS_TOTAL': 28,
        'PERDIDAS_START': 29,  # Desde DELGADOS hasta OTROS
        'PERDIDAS_END': 43,
        'FIN': 44
    }
    
    # Mapeo de causas de pérdida
    CAUSAS_PERDIDA = [
        'DELGADOS', 'TORCIDOS', 'TRES PUNTOS', 'RAMIFICADO', 'D. MECANICO',
        'CORTO', 'VEGETATIVO', 'ACAROS', 'TRIPS', 'PSEUDOMONAS',
        'FLOR CENTRO AMARILLO', 'DEFORMIDAD', 'BABOSA', 'FLOR ABIERTA', 'OTROS'
    ]
    
    DEFAULT_USER_ID = 1
    
    @classmethod
    def importar_historico_completo(cls, file_path: str) -> Dict[str, Any]:
        """
        Importa datos históricos completos desde archivo Excel.
        
        Args:
            file_path: Ruta al archivo Excel
            
        Returns:
            Dict con estadísticas de la importación
        """
        if not os.path.exists(file_path):
            return {"error": f"El archivo {file_path} no existe."}
        
        try:
            # Cargar el archivo Excel
            df = pd.read_excel(file_path, dtype=str)
            logger.info(f"Archivo cargado: {len(df)} filas encontradas.")
            
            # Preparar estadísticas
            stats = {
                "siembras_creadas": 0,
                "siembras_actualizadas": 0,
                "cortes_creados": 0,
                "cortes_actualizados": 0,
                "perdidas_creadas": 0,
                "causas_perdida_creadas": 0,
                "densidades_creadas": 0,
                "errores": 0,
                "detalles_errores": []
            }
            
            # Procesar los datos en transacción
            with db.session.begin_nested():
                # Asegurar usuario para registro
                usuario_id = cls._obtener_usuario_admin()
                if not usuario_id:
                    return {"error": "No se pudo obtener un usuario válido para el registro."}
                
                # Procesar cada fila
                for index, row in df.iterrows():
                    try:
                        cls._procesar_fila_completa(row, usuario_id, stats, index)
                    except Exception as e:
                        stats["errores"] += 1
                        stats["detalles_errores"].append({
                            "fila": index + 2,
                            "error": str(e),
                            "datos": cls._extract_row_summary(row)
                        })
                        logger.error(f"Error en fila {index+2}: {str(e)}")
                        continue
                
                # Verificar si hubo demasiados errores
                if stats["errores"] > len(df) * 0.5:
                    db.session.rollback()
                    return {
                        "error": f"Demasiados errores ({stats['errores']} de {len(df)} filas). "
                                f"Revise el formato del archivo e intente nuevamente.",
                        **stats
                    }
                
                # Confirmar la transacción
                db.session.commit()
                logger.info(f"Importación exitosa: {stats}")
                return stats
                
        except Exception as e:
            db.session.rollback()
            logger.exception("Error durante la importación")
            return {"error": f"Error durante la importación: {str(e)}"}
    
    @classmethod
    def _obtener_usuario_admin(cls) -> int:
        """Obtiene el ID del usuario administrador."""
        admin = Usuario.query.filter_by(username='admin').first()
        if admin:
            return admin.usuario_id
        return cls.DEFAULT_USER_ID
    
    @classmethod
    def _procesar_fila_completa(cls, row: pd.Series, usuario_id: int, stats: Dict, index: int) -> None:
        """
        Procesa una fila completa del archivo histórico.
        
        Args:
            row: Fila de datos del DataFrame
            usuario_id: ID del usuario para registro
            stats: Diccionario de estadísticas
            index: Índice de la fila
        """
        # Extraer datos básicos
        bloque_nombre = str(row.iloc[cls.COLUMN_MAPPING['BLOQUE']]).strip()
        cama_nombre = str(row.iloc[cls.COLUMN_MAPPING['CAMA']]).strip()
        flor_nombre = str(row.iloc[cls.COLUMN_MAPPING['FLOR']]).strip().upper()
        color_nombre = str(row.iloc[cls.COLUMN_MAPPING['COLOR']]).strip().upper()
        variedad_nombre = str(row.iloc[cls.COLUMN_MAPPING['VARIEDAD']]).strip().upper()
        
        # Validar datos básicos
        if not all([bloque_nombre, cama_nombre, flor_nombre, color_nombre, variedad_nombre]):
            raise ValueError("Faltan datos básicos requeridos")
        
        # Procesar fechas
        fecha_siembra = cls._procesar_fecha(row.iloc[cls.COLUMN_MAPPING['FECHA_SIEMBRA']])
        fecha_inicio_corte = cls._procesar_fecha(row.iloc[cls.COLUMN_MAPPING['FECHA_INICIO_CORTE']])
        fecha_fin_corte = cls._procesar_fecha(row.iloc[cls.COLUMN_MAPPING['FECHA_FIN_CORTE']])
        
        if not fecha_siembra:
            raise ValueError("Fecha de siembra inválida")
        
        # Procesar datos de siembra
        plantas = safe_int(row.iloc[cls.COLUMN_MAPPING['PLANTAS']])
        densidad_nombre = str(row.iloc[cls.COLUMN_MAPPING['DENSIDAD']]).strip()
        
        if plantas <= 0:
            raise ValueError(f"Cantidad de plantas inválida: {plantas}")
        
        # Crear/obtener entidades
        variedad = cls._procesar_variedad(flor_nombre, color_nombre, variedad_nombre)
        densidad = cls._procesar_densidad_texto(densidad_nombre, plantas, stats)
        area = cls._procesar_area_desde_plantas(plantas, densidad.valor)
        bloque_cama = cls._procesar_ubicacion(bloque_nombre, cama_nombre)
        
        # Crear siembra
        siembra = cls._procesar_siembra_completa(
            bloque_cama, variedad, area, densidad, fecha_siembra,
            fecha_inicio_corte, fecha_fin_corte, usuario_id, stats
        )
        
        # Procesar cortes
        cls._procesar_cortes_completos(row, siembra, fecha_inicio_corte, usuario_id, stats)
        
        # Procesar pérdidas
        cls._procesar_perdidas_completas(row, siembra, usuario_id, stats)
    
    @classmethod
    def _procesar_fecha(cls, fecha_valor) -> Optional[datetime.date]:
        """Procesa diferentes formatos de fecha."""
        if pd.isna(fecha_valor) or fecha_valor is None:
            return None
        
        try:
            if isinstance(fecha_valor, (datetime, pd.Timestamp)):
                return fecha_valor.date()
            
            if isinstance(fecha_valor, str):
                # Intentar varios formatos de fecha
                for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%d %H:%M:%S']:
                    try:
                        return datetime.strptime(fecha_valor, fmt).date()
                    except ValueError:
                        continue
            
            # Si es un número (fecha de Excel)
            if isinstance(fecha_valor, (int, float)):
                # Convertir número de serie de Excel a fecha
                if fecha_valor > 25569:  # Fecha mínima válida en Excel (1970-01-01)
                    return pd.to_datetime(fecha_valor, origin='1899-12-30', unit='D').date()
            
            return pd.to_datetime(fecha_valor).date()
        except:
            return None
    
    @classmethod
    def _procesar_variedad(cls, flor: str, color: str, variedad: str) -> Variedad:
        """Procesa o crea variedad completa."""
        # Obtener o crear flor
        flor_obj = Flor.query.filter_by(flor=flor).first()
        if not flor_obj:
            flor_obj = Flor(flor=flor, flor_abrev=flor[:10])
            db.session.add(flor_obj)
            db.session.flush()
        
        # Obtener o crear color
        color_obj = Color.query.filter_by(color=color).first()
        if not color_obj:
            color_obj = Color(color=color, color_abrev=color[:10])
            db.session.add(color_obj)
            db.session.flush()
        
        # Obtener o crear flor_color
        flor_color = FlorColor.query.filter_by(
            flor_id=flor_obj.flor_id, 
            color_id=color_obj.color_id
        ).first()
        
        if not flor_color:
            flor_color = FlorColor(
                flor_id=flor_obj.flor_id,
                color_id=color_obj.color_id
            )
            db.session.add(flor_color)
            db.session.flush()
        
        # Obtener o crear variedad
        variedad_obj = Variedad.query.filter_by(variedad=variedad).first()
        if not variedad_obj:
            variedad_obj = Variedad(
                variedad=variedad,
                flor_color_id=flor_color.flor_color_id
            )
            db.session.add(variedad_obj)
            db.session.flush()
        
        return variedad_obj
    
    @classmethod
    def _procesar_densidad_texto(cls, densidad_texto: str, plantas: int, stats: Dict) -> Densidad:
        """Procesa densidad desde texto descriptivo."""
        # Mapear nombres de densidad a valores aproximados
        densidad_map = {
            'BAJA': 60.0,
            'NORMAL': 70.0,
            'MEDIA': 70.0,
            'ALTA': 80.0,
            'MUY ALTA': 90.0
        }
        
        densidad_valor = densidad_map.get(densidad_texto.upper(), 70.0)
        
        # Buscar densidad existente
        densidad = Densidad.query.filter_by(densidad=densidad_texto).first()
        
        if not densidad:
            densidad = Densidad(
                densidad=densidad_texto,
                valor=densidad_valor
            )
            db.session.add(densidad)
            db.session.flush()
            stats['densidades_creadas'] += 1
        
        return densidad
    
    @classmethod
    def _procesar_area_desde_plantas(cls, plantas: int, densidad_valor: float) -> Area:
        """Calcula y crea área desde plantas y densidad."""
        area_calculada = round(plantas / densidad_valor, 2)
        area_nombre = f"ÁREA {area_calculada}m²"
        
        # Buscar área aproximada
        area = Area.query.filter(
            Area.area.between(area_calculada * 0.95, area_calculada * 1.05)
        ).first()
        
        if not area:
            area = Area(siembra=area_nombre, area=area_calculada)
            db.session.add(area)
            db.session.flush()
        
        return area
    
    @classmethod
    def _procesar_ubicacion(cls, bloque: str, cama: str) -> BloqueCamaLado:
        """Procesa ubicación completa."""
        # Extraer lado de la cama (ej: "55A" -> lado "A")
        lado = "A"  # Valor por defecto
        if cama and len(cama) > 1 and cama[-1].isalpha():
            lado = cama[-1]
            cama_limpia = cama[:-1]
        else:
            cama_limpia = cama
        
        # Obtener o crear entidades
        bloque_obj = Bloque.query.filter_by(bloque=bloque).first()
        if not bloque_obj:
            bloque_obj = Bloque(bloque=bloque)
            db.session.add(bloque_obj)
            db.session.flush()
        
        cama_obj = Cama.query.filter_by(cama=cama).first()  # Usar cama completa
        if not cama_obj:
            cama_obj = Cama(cama=cama)
            db.session.add(cama_obj)
            db.session.flush()
        
        lado_obj = Lado.query.filter_by(lado=lado).first()
        if not lado_obj:
            lado_obj = Lado(lado=lado)
            db.session.add(lado_obj)
            db.session.flush()
        
        # Crear relación
        bloque_cama = BloqueCamaLado.query.filter_by(
            bloque_id=bloque_obj.bloque_id,
            cama_id=cama_obj.cama_id,
            lado_id=lado_obj.lado_id
        ).first()
        
        if not bloque_cama:
            bloque_cama = BloqueCamaLado(
                bloque_id=bloque_obj.bloque_id,
                cama_id=cama_obj.cama_id,
                lado_id=lado_obj.lado_id
            )
            db.session.add(bloque_cama)
            db.session.flush()
        
        return bloque_cama
    
    @classmethod
    def _procesar_siembra_completa(
        cls, bloque_cama: BloqueCamaLado, variedad: Variedad, area: Area,
        densidad: Densidad, fecha_siembra: datetime.date,
        fecha_inicio_corte: Optional[datetime.date],
        fecha_fin_corte: Optional[datetime.date],
        usuario_id: int, stats: Dict
    ) -> Siembra:
        """Crea siembra completa con todas las fechas."""
        
        # Buscar siembra existente
        siembra = Siembra.query.filter_by(
            bloque_cama_id=bloque_cama.bloque_cama_id,
            variedad_id=variedad.variedad_id,
            fecha_siembra=fecha_siembra
        ).first()
        
        if not siembra:
            siembra = Siembra(
                bloque_cama_id=bloque_cama.bloque_cama_id,
                variedad_id=variedad.variedad_id,
                area_id=area.area_id,
                densidad_id=densidad.densidad_id,
                fecha_siembra=fecha_siembra,
                fecha_inicio_corte=fecha_inicio_corte,
                fecha_fin_corte=fecha_fin_corte,
                usuario_id=usuario_id,
                estado='Finalizada',
                fecha_registro=datetime.now()
            )
            db.session.add(siembra)
            db.session.flush()
            stats["siembras_creadas"] += 1
        else:
            # Actualizar fechas si están disponibles
            if fecha_inicio_corte and not siembra.fecha_inicio_corte:
                siembra.fecha_inicio_corte = fecha_inicio_corte
            if fecha_fin_corte and not siembra.fecha_fin_corte:
                siembra.fecha_fin_corte = fecha_fin_corte
            stats["siembras_actualizadas"] += 1
        
        return siembra
    
    @classmethod
    def _procesar_cortes_completos(
        cls, row: pd.Series, siembra: Siembra,
        fecha_inicio_corte: Optional[datetime.date], usuario_id: int, stats: Dict
    ) -> None:
        """Procesa todos los cortes de la fila."""
        
        # Procesar cortes numerados (columnas 1-15)
        for num_corte in range(1, 16):
            col_index = cls.COLUMN_MAPPING['CORTES_START'] + num_corte - 1
            
            if col_index < len(row):
                tallos = safe_int(row.iloc[col_index])
                
                if tallos > 0:
                    # Calcular fecha estimada del corte
                    fecha_corte = cls._calcular_fecha_corte(
                        siembra.fecha_siembra, fecha_inicio_corte, num_corte
                    )
                    
                    cls._crear_corte(
                        siembra.siembra_id, num_corte, fecha_corte, tallos, usuario_id, stats
                    )
    
    @classmethod
    def _calcular_fecha_corte(
        cls, fecha_siembra: datetime.date,
        fecha_inicio_corte: Optional[datetime.date], num_corte: int
    ) -> datetime.date:
        """Calcula fecha estimada de corte."""
        if fecha_inicio_corte:
            # Usar fecha real de inicio + días estimados entre cortes
            dias_entre_cortes = 7  # Una semana entre cortes
            return fecha_inicio_corte + timedelta(days=(num_corte - 1) * dias_entre_cortes)
        else:
            # Estimar desde fecha de siembra
            dias_hasta_primer_corte = 65  # ~2 meses hasta primer corte
            dias_entre_cortes = 7
            total_dias = dias_hasta_primer_corte + (num_corte - 1) * dias_entre_cortes
            return fecha_siembra + timedelta(days=total_dias)
    
    @classmethod
    def _crear_corte(
        cls, siembra_id: int, num_corte: int, fecha_corte: datetime.date,
        cantidad_tallos: int, usuario_id: int, stats: Dict
    ) -> None:
        """Crea un registro de corte."""
        corte = Corte.query.filter_by(
            siembra_id=siembra_id,
            num_corte=num_corte
        ).first()
        
        if not corte:
            corte = Corte(
                siembra_id=siembra_id,
                num_corte=num_corte,
                fecha_corte=fecha_corte,
                cantidad_tallos=cantidad_tallos,
                usuario_id=usuario_id,
                fecha_registro=datetime.now()
            )
            db.session.add(corte)
            stats["cortes_creados"] += 1
        else:
            corte.fecha_corte = fecha_corte
            corte.cantidad_tallos = cantidad_tallos
            stats["cortes_actualizados"] += 1
    
    @classmethod
    def _procesar_perdidas_completas(
        cls, row: pd.Series, siembra: Siembra, usuario_id: int, stats: Dict
    ) -> None:
        """Procesa todas las pérdidas de la fila."""
        
        for i, causa_nombre in enumerate(cls.CAUSAS_PERDIDA):
            col_index = cls.COLUMN_MAPPING['PERDIDAS_START'] + i
            
            if col_index < len(row):
                cantidad = safe_int(row.iloc[col_index])
                
                if cantidad > 0:
                    # Obtener o crear causa
                    causa = cls._obtener_causa_perdida(causa_nombre, stats)
                    
                    # Estimar fecha de pérdida
                    fecha_perdida = cls._estimar_fecha_perdida(siembra, i)
                    
                    cls._crear_perdida(
                        siembra.siembra_id, causa.causa_id, cantidad,
                        fecha_perdida, usuario_id, stats
                    )
    
    @classmethod
    def _obtener_causa_perdida(cls, nombre: str, stats: Dict) -> CausaPerdida:
        """Obtiene o crea causa de pérdida."""
        causa = CausaPerdida.query.filter(
            CausaPerdida.nombre.ilike(nombre.replace('D. MECANICO', 'DAÑO MECÁNICO'))
        ).first()
        
        if not causa:
            causa = CausaPerdida(
                nombre=nombre.replace('D. MECANICO', 'DAÑO MECÁNICO'),
                descripcion=f"Causa importada: {nombre}",
                es_predefinida=True
            )
            db.session.add(causa)
            db.session.flush()
            stats["causas_perdida_creadas"] += 1
        
        return causa
    
    @classmethod
    def _estimar_fecha_perdida(cls, siembra: Siembra, causa_index: int) -> datetime.date:
        """Estima fecha de pérdida según el tipo de causa."""
        if siembra.fecha_inicio_corte:
            # Distribuir pérdidas durante el ciclo productivo
            dias_offset = causa_index * 5  # 5 días entre cada tipo de pérdida
            return siembra.fecha_inicio_corte + timedelta(days=dias_offset)
        else:
            # Estimar desde siembra
            dias_base = 45 + causa_index * 5  # Pérdidas después de 45 días
            return siembra.fecha_siembra + timedelta(days=dias_base)
    
    @classmethod
    def _crear_perdida(
        cls, siembra_id: int, causa_id: int, cantidad: int,
        fecha_perdida: datetime.date, usuario_id: int, stats: Dict
    ) -> None:
        """Crea registro de pérdida."""
        perdida_existente = Perdida.query.filter_by(
            siembra_id=siembra_id,
            causa_id=causa_id,
            fecha_perdida=fecha_perdida
        ).first()
        
        if not perdida_existente:
            perdida = Perdida(
                siembra_id=siembra_id,
                causa_id=causa_id,
                cantidad=cantidad,
                fecha_perdida=fecha_perdida,
                observaciones="Importado desde históricos",
                usuario_id=usuario_id,
                fecha_registro=datetime.now()
            )
            db.session.add(perdida)
            stats["perdidas_creadas"] += 1
    
    @classmethod
    def _extract_row_summary(cls, row: pd.Series) -> str:
        """Extrae resumen de la fila para errores."""
        try:
            return f"Bloque: {row.iloc[0]}, Cama: {row.iloc[1]}, Variedad: {row.iloc[4]}"
        except:
            return "Datos no disponibles"