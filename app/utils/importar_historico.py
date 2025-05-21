import os
import pandas as pd
import numpy as np
from datetime import datetime
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

class HistoricalImporter:
    """
    Clase mejorada para importar datos históricos incluyendo pérdidas.
    """
    
    REQUIRED_COLUMNS = ['BLOQUE', 'CAMA', 'FLOR', 'COLOR', 'VARIEDAD', 'FECHA SIEMBRA']
    CORTE_COLUMNS_PREFIX = ['CORTE', 'TALLOS']
    PERDIDAS_COLUMNS_PREFIX = ['PERDIDA', 'CAUSA']
    DEFAULT_USER_ID = 1  # ID del usuario administrador por defecto
    
    @classmethod
    def importar_historico(cls, file_path: str) -> Dict[str, Any]:
        """
        Importa datos históricos desde un archivo Excel incluyendo pérdidas.
        
        Args:
            file_path: Ruta al archivo Excel
            
        Returns:
            Dict con estadísticas de la importación
        """
        if not os.path.exists(file_path):
            return {"error": f"El archivo {file_path} no existe."}
        
        try:
            # Cargar el archivo
            df = pd.read_excel(file_path)
            logger.info(f"Archivo cargado: {len(df)} filas encontradas.")
            
            # Verificar columnas requeridas
            missing_cols = [col for col in cls.REQUIRED_COLUMNS 
                           if not any(col.upper() in str(c).upper() for c in df.columns)]
            if missing_cols:
                return {"error": f"Faltan columnas requeridas: {', '.join(missing_cols)}"}
            
            # Preparar estadísticas
            stats = {
                "siembras_creadas": 0,
                "siembras_actualizadas": 0,
                "cortes_creados": 0,
                "cortes_actualizados": 0,
                "perdidas_creadas": 0,
                "causas_perdida_creadas": 0,
                "errores": 0,
                "detalles_errores": []
            }
            
            # Procesar los datos en una transacción
            with db.session.begin_nested():
                # Asegurar usuario para registro
                usuario_id = cls._obtener_usuario_admin()
                if not usuario_id:
                    return {"error": "No se pudo obtener un usuario válido para el registro."}
                
                # Procesar cada fila
                for index, row in df.iterrows():
                    try:
                        cls._procesar_fila(row, usuario_id, stats)
                    except Exception as e:
                        stats["errores"] += 1
                        stats["detalles_errores"].append({
                            "fila": index + 2,  # +2 para compensar por encabezado y base-1
                            "error": str(e),
                            "datos": str(row.to_dict())
                        })
                        logger.error(f"Error en fila {index+2}: {str(e)}")
                        continue
                
                # Verificar si hubo demasiados errores
                if stats["errores"] > len(df) * 0.5:  # Si más del 50% son errores
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
    def _procesar_fila(cls, row: pd.Series, usuario_id: int, stats: Dict) -> None:
        """
        Procesa una fila del archivo de importación.
        
        Args:
            row: Fila de datos
            usuario_id: ID del usuario para registro
            stats: Diccionario de estadísticas a actualizar
        """
        # Normalizar datos básicos
        bloque_nombre = str(row.get('BLOQUE', '')).strip()
        cama_nombre = str(row.get('CAMA', '')).strip()
        flor_nombre = str(row.get('FLOR', '')).strip().upper()
        color_nombre = str(row.get('COLOR', '')).strip().upper()
        variedad_nombre = str(row.get('VARIEDAD', '')).strip().upper()
        
        # Validar datos básicos
        if not all([bloque_nombre, cama_nombre, flor_nombre, color_nombre, variedad_nombre]):
            raise ValueError("Faltan datos básicos requeridos (bloque, cama, flor, color o variedad)")
        
        # Procesar fecha de siembra
        fecha_siembra = cls._obtener_fecha(row, 'FECHA SIEMBRA')
        if not fecha_siembra:
            raise ValueError("Fecha de siembra inválida o faltante")
        
        # Obtener o crear variedad
        variedad = cls._procesar_variedad(flor_nombre, color_nombre, variedad_nombre)
        
        # Obtener datos de área y densidad
        area_valor = safe_float(row.get('Area', 0))
        densidad_valor = safe_float(row.get('DENSIDAD', 0))
        
        # Verificar valores mínimos
        if area_valor <= 0 or densidad_valor <= 0:
            raise ValueError(f"Valores de área ({area_valor}) o densidad ({densidad_valor}) inválidos")
        
        # Procesar área y densidad
        area = cls._procesar_area(area_valor)
        densidad = cls._procesar_densidad(densidad_valor)
        
        # Obtener ubicación (bloque-cama-lado)
        lado_nombre = cls._extraer_lado_desde_cama(cama_nombre)
        bloque_cama = cls._procesar_ubicacion(bloque_nombre, cama_nombre, lado_nombre)
        
        # Crear o actualizar siembra
        siembra = cls._procesar_siembra(
            bloque_cama, variedad, area, densidad, fecha_siembra, usuario_id, stats
        )
        
        # Procesar cortes si existen
        cls._procesar_cortes(row, siembra, usuario_id, stats)
        
        # Procesar pérdidas si existen
        cls._procesar_perdidas(row, siembra, usuario_id, stats)
    
    @classmethod
    def _extraer_lado_desde_cama(cls, cama_nombre: str) -> str:
        """
        Extrae el lado desde el nombre de la cama si está en formato "NUM-LADO".
        Ejemplo: "55A" -> "A"
        """
        # Buscar un patrón donde el último carácter es una letra
        if cama_nombre and len(cama_nombre) > 1 and cama_nombre[-1].isalpha():
            return cama_nombre[-1]
        return "ÚNICO"  # Valor por defecto
    
    @classmethod
    def _obtener_fecha(cls, row: pd.Series, columna: str) -> Optional[datetime.date]:
        """
        Obtiene y convierte un valor de fecha desde una fila.
        Maneja diferentes formatos y representaciones.
        """
        valor = row.get(columna)
        if pd.isna(valor):
            return None
        
        try:
            # Si ya es datetime, obtener la fecha
            if isinstance(valor, (datetime, pd.Timestamp)):
                return valor.date()
            
            # Si es cadena, intentar convertir
            if isinstance(valor, str):
                fecha = pd.to_datetime(valor).date()
                return fecha
            
            # Otros casos - convertir a Timestamp
            return pd.Timestamp(valor).date()
        except:
            return None
    
    @classmethod
    def _procesar_variedad(cls, flor: str, color: str, variedad: str) -> Variedad:
        """
        Procesa o crea una variedad completa (flor, color, variedad).
        
        Returns:
            Objeto Variedad
        """
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
    def _procesar_area(cls, area_valor: float) -> Area:
        """
        Obtiene o crea un registro de área.
        
        Returns:
            Objeto Area
        """
        # Crear nombre estandarizado para el área
        area_nombre = f"ÁREA {area_valor:.2f}m²"
        
        # Buscar área aproximada (con margen de error)
        area = Area.query.filter(
            (Area.area >= area_valor * 0.99) & 
            (Area.area <= area_valor * 1.01)
        ).first()
        
        if not area:
            area = Area(siembra=area_nombre, area=area_valor)
            db.session.add(area)
            db.session.flush()
        
        return area
    
    @classmethod
    def _procesar_densidad(cls, densidad_valor: float) -> Densidad:
        """
        Obtiene o crea un registro de densidad.
        
        Returns:
            Objeto Densidad
        """
        # Crear nombre estandarizado para la densidad
        densidad_nombre = f"DENSIDAD {densidad_valor:.2f} p/m²"
        
        # Buscar densidad aproximada (con margen de error)
        densidad = Densidad.query.filter(
            (Densidad.valor >= densidad_valor * 0.99) & 
            (Densidad.valor <= densidad_valor * 1.01)
        ).first()
        
        if not densidad:
            densidad = Densidad(densidad=densidad_nombre, valor=densidad_valor)
            db.session.add(densidad)
            db.session.flush()
        
        return densidad
    
    @classmethod
    def _procesar_ubicacion(cls, bloque: str, cama: str, lado: str) -> BloqueCamaLado:
        """
        Obtiene o crea una ubicación (bloque-cama-lado).
        
        Returns:
            Objeto BloqueCamaLado
        """
        # Limpiar caracteres no deseados
        cama_limpia = ''.join(c for c in cama if c.isalnum())
        
        # Obtener o crear bloque
        bloque_obj = Bloque.query.filter_by(bloque=bloque).first()
        if not bloque_obj:
            bloque_obj = Bloque(bloque=bloque)
            db.session.add(bloque_obj)
            db.session.flush()
        
        # Obtener o crear cama
        cama_obj = Cama.query.filter_by(cama=cama_limpia).first()
        if not cama_obj:
            cama_obj = Cama(cama=cama_limpia)
            db.session.add(cama_obj)
            db.session.flush()
        
        # Obtener o crear lado
        lado_obj = Lado.query.filter_by(lado=lado).first()
        if not lado_obj:
            lado_obj = Lado(lado=lado)
            db.session.add(lado_obj)
            db.session.flush()
        
        # Obtener o crear relación bloque-cama-lado
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
    def _procesar_siembra(
        cls, 
        bloque_cama: BloqueCamaLado, 
        variedad: Variedad, 
        area: Area, 
        densidad: Densidad, 
        fecha_siembra: datetime.date, 
        usuario_id: int,
        stats: Dict
    ) -> Siembra:
        """
        Crea o actualiza un registro de siembra.
        
        Returns:
            Objeto Siembra
        """
        # Buscar si ya existe una siembra similar
        siembra = Siembra.query.filter_by(
            bloque_cama_id=bloque_cama.bloque_cama_id,
            variedad_id=variedad.variedad_id,
            fecha_siembra=fecha_siembra
        ).first()
        
        if not siembra:
            # Crear nueva siembra
            siembra = Siembra(
                bloque_cama_id=bloque_cama.bloque_cama_id,
                variedad_id=variedad.variedad_id,
                area_id=area.area_id,
                densidad_id=densidad.densidad_id,
                fecha_siembra=fecha_siembra,
                usuario_id=usuario_id,
                estado='Finalizada',  # Datos históricos generalmente están finalizados
                fecha_registro=datetime.now()
            )
            db.session.add(siembra)
            stats["siembras_creadas"] += 1
        else:
            # Actualizar siembra existente
            siembra.area_id = area.area_id
            siembra.densidad_id = densidad.densidad_id
            stats["siembras_actualizadas"] += 1
        
        db.session.flush()
        return siembra
    
    @classmethod
    def _procesar_cortes(cls, row: pd.Series, siembra: Siembra, usuario_id: int, stats: Dict) -> None:
        """
        Procesa los cortes de una siembra desde una fila.
        
        Args:
            row: Fila de datos
            siembra: Objeto Siembra
            usuario_id: ID del usuario para registro
            stats: Diccionario de estadísticas a actualizar
        """
        # Extraer campos de fecha inicio corte y fin de corte
        fecha_inicio_corte = cls._obtener_fecha(row, 'FECHA INICIO CORTE')
        fecha_fin_corte = cls._obtener_fecha(row, 'FECHA FIN CORTE')
        
        # Actualizar siembra con fechas de corte si existen
        if fecha_inicio_corte:
            siembra.fecha_inicio_corte = fecha_inicio_corte
        if fecha_fin_corte:
            siembra.fecha_fin_corte = fecha_fin_corte
        
        # Cortes en formato estándar (columnas numeradas)
        cls._procesar_cortes_estandar(row, siembra, usuario_id, stats)
        
        # Cortes en formato alternativo (columnas "CORTE X", "TALLOS X")
        cls._procesar_cortes_alternativo(row, siembra, usuario_id, stats)
    
    @classmethod
    def _procesar_cortes_estandar(cls, row: pd.Series, siembra: Siembra, usuario_id: int, stats: Dict) -> None:
        """
        Procesa cortes en formato estándar con columnas numeradas.
        Formato esperado: Columnas numeradas del 1 al 15 o "TALLOS"
        """
        # Intentar procesar el total de tallos
        total_tallos = safe_int(row.get('TALLOS', 0))
        
        # Buscar columnas numéricas (del 1 al 15)
        cortes_procesados = 0
        for i in range(1, 16):
            # Verificar si existe la columna
            if i not in row or pd.isna(row[i]):
                continue
            
            # Intentar obtener la cantidad de tallos
            tallos = safe_int(row[i])
            if tallos <= 0:
                continue
            
            # Calcular la fecha aproximada del corte
            if fecha_inicio_corte := siembra.fecha_inicio_corte:
                # Estimar añadiendo días según el número de corte
                dias_estimados = (i - 1) * 7  # Una semana entre cortes
                fecha_corte = fecha_inicio_corte + pd.Timedelta(days=dias_estimados)
            else:
                # Si no hay fecha de inicio, estimar desde la siembra
                dias_estimados = 60 + (i - 1) * 7  # ~60 días para primer corte
                fecha_corte = siembra.fecha_siembra + pd.Timedelta(days=dias_estimados)
            
            # Crear o actualizar el corte
            cls._crear_actualizar_corte(siembra.siembra_id, i, fecha_corte.date(), tallos, usuario_id, stats)
            cortes_procesados += 1
        
        # Si no se procesaron cortes pero hay un total de tallos, crear un corte único
        if cortes_procesados == 0 and total_tallos > 0 and siembra.fecha_inicio_corte:
            cls._crear_actualizar_corte(
                siembra.siembra_id, 1, siembra.fecha_inicio_corte, total_tallos, usuario_id, stats
            )
    
    @classmethod
    def _procesar_cortes_alternativo(cls, row: pd.Series, siembra: Siembra, usuario_id: int, stats: Dict) -> None:
        """
        Procesa cortes en formato alternativo con columnas "CORTE X" y "TALLOS X".
        """
        # Buscar pares de columnas en formato "CORTE X" y "TALLOS X"
        for i in range(1, 16):
            col_fecha = f"CORTE {i}"
            col_tallos = f"TALLOS {i}"
            
            # Verificar si existen ambas columnas
            if col_fecha not in row or col_tallos not in row:
                continue
            
            # Obtener fecha y tallos
            fecha_corte = cls._obtener_fecha(row, col_fecha)
            tallos = safe_int(row.get(col_tallos, 0))
            
            # Validar datos
            if not fecha_corte or tallos <= 0:
                continue
            
            # Crear o actualizar el corte
            cls._crear_actualizar_corte(siembra.siembra_id, i, fecha_corte, tallos, usuario_id, stats)
    
    @classmethod
    def _crear_actualizar_corte(
        cls, 
        siembra_id: int, 
        num_corte: int, 
        fecha_corte: datetime.date, 
        cantidad_tallos: int, 
        usuario_id: int,
        stats: Dict
    ) -> None:
        """
        Crea o actualiza un registro de corte.
        """
        # Buscar si ya existe un corte similar
        corte = Corte.query.filter_by(
            siembra_id=siembra_id,
            num_corte=num_corte
        ).first()
        
        if not corte:
            # Crear nuevo corte
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
            # Actualizar corte existente
            corte.fecha_corte = fecha_corte
            corte.cantidad_tallos = cantidad_tallos
            stats["cortes_actualizados"] += 1
    
    @classmethod
    def _procesar_perdidas(cls, row: pd.Series, siembra: Siembra, usuario_id: int, stats: Dict) -> None:
        """
        Procesa las pérdidas de una siembra desde una fila.
        
        Args:
            row: Fila de datos
            siembra: Objeto Siembra
            usuario_id: ID del usuario para registro
            stats: Diccionario de estadísticas a actualizar
        """
        # Procesar pérdidas en formato estándar (columnas "PERDIDA X", "CAUSA X")
        for i in range(1, 6):  # Asumimos máximo 5 registros de pérdidas por siembra
            col_cantidad = f"PERDIDA {i}"
            col_causa = f"CAUSA {i}"
            col_fecha = f"FECHA PERDIDA {i}"
            
            # Verificar si existen las columnas necesarias
            if col_cantidad not in row or col_causa not in row:
                continue
            
            # Obtener datos
            cantidad = safe_int(row.get(col_cantidad, 0))
            causa_nombre = str(row.get(col_causa, "")).strip().upper()
            
            # Validar datos
            if cantidad <= 0 or not causa_nombre:
                continue
            
            # Obtener fecha (opcional)
            fecha_perdida = cls._obtener_fecha(row, col_fecha)
            if not fecha_perdida:
                # Si no hay fecha específica, usar fecha de siembra + 30 días
                fecha_perdida = siembra.fecha_siembra + pd.Timedelta(days=30 * i)
            
            # Procesar causa
            causa = cls._procesar_causa_perdida(causa_nombre, stats)
            
            # Crear pérdida
            cls._crear_perdida(siembra.siembra_id, causa.causa_id, cantidad, fecha_perdida.date(), usuario_id, stats)
    
    @classmethod
    def _procesar_causa_perdida(cls, nombre: str, stats: Dict) -> CausaPerdida:
        """
        Obtiene o crea una causa de pérdida.
        
        Returns:
            Objeto CausaPerdida
        """
        # Buscar causa existente
        causa = CausaPerdida.query.filter(CausaPerdida.nombre.ilike(nombre)).first()
        
        if not causa:
            # Crear nueva causa
            causa = CausaPerdida(
                nombre=nombre,
                descripcion=f"Causa importada: {nombre}",
                es_predefinida=True
            )
            db.session.add(causa)
            db.session.flush()
            stats["causas_perdida_creadas"] += 1
        
        return causa
    
    @classmethod
    def _crear_perdida(
        cls, 
        siembra_id: int, 
        causa_id: int, 
        cantidad: int, 
        fecha_perdida: datetime.date, 
        usuario_id: int,
        stats: Dict
    ) -> None:
        """
        Crea un registro de pérdida.
        """
        # Verificar si ya existe una pérdida similar
        perdida_existente = Perdida.query.filter_by(
            siembra_id=siembra_id,
            causa_id=causa_id,
            fecha_perdida=fecha_perdida
        ).first()
        
        if not perdida_existente:
            # Crear nueva pérdida
            perdida = Perdida(
                siembra_id=siembra_id,
                causa_id=causa_id,
                cantidad=cantidad,
                fecha_perdida=fecha_perdida,
                observaciones="Importado automáticamente",
                usuario_id=usuario_id,
                fecha_registro=datetime.now()
            )
            db.session.add(perdida)
            stats["perdidas_creadas"] += 1