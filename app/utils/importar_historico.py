"""
Importador histórico mejorado que analiza la estructura del Excel automáticamente.
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from app import db
from app.models import (
    Siembra, Corte, Variedad, FlorColor, Flor, Color, BloqueCamaLado,
    Bloque, Cama, Lado, Area, Densidad, Usuario, CausaPerdida, Perdida
)
from app.utils.data_utils import safe_int, safe_float
import logging
import re

logger = logging.getLogger(__name__)

class HistoricalImporter:
    """Importador histórico adaptativo que analiza la estructura del Excel"""
    
    # Patrones para detectar columnas automáticamente
    COLUMN_PATTERNS = {
        'BLOQUE': r'(?i)^(bloque|block)$',
        'CAMA': r'(?i)^(cama|bed)$',
        'FLOR': r'(?i)^(flor|flower)$',
        'COLOR': r'(?i)^(color|colour)$',
        'VARIEDAD': r'(?i)^(variedad|variety)$',
        'FECHA_SIEMBRA': r'(?i)^(fecha.siembra|date.plant|planting.date)$',
        'AREA': r'(?i)^(area|área)$',
        'DENSIDAD': r'(?i)^(densidad|density)$',
        'FECHA_INICIO_CORTE': r'(?i)^(fecha.inicio.corte|inicio.corte|start.cut)$',
        'FECHA_FIN_CORTE': r'(?i)^(fecha.fin.corte|fin.corte|end.cut)$',
        'PLANTAS': r'(?i)^(plantas|plants)$',
        'TALLOS': r'(?i)^(tallos|stems)$'
    }
    
    # Patrones para detectar columnas de cortes
    CORTE_PATTERNS = [
        r'(?i)^(\d+)$',  # Solo números (1, 2, 3, ...)
        r'(?i)^(corte.?\d+|cut.?\d+)$',  # "CORTE 1", "CUT1", etc.
        r'(?i)^(c\d+)$',  # "C1", "C2", etc.
        r'(?i)^(tallos.?\d+|stems.?\d+)$'  # "TALLOS 1", "STEMS1", etc.
    ]
    
    # Patrones para detectar columnas de pérdidas
    PERDIDA_PATTERNS = [
        r'(?i)^(perdida.?\d+|loss.?\d+)$',  # "PERDIDA 1", "LOSS1", etc.
        r'(?i)^(causa.?\d+|cause.?\d+)$',   # "CAUSA 1", "CAUSE1", etc.
        r'(?i)^(fecha.perdida.?\d+|date.loss.?\d+)$'  # "FECHA PERDIDA 1", etc.
    ]
    
    @classmethod
    def importar_historico(cls, file_path: str) -> Dict[str, Any]:
        """
        Importa datos históricos con análisis automático de estructura.
        """
        stats = cls._init_stats()
        
        try:
            # Leer Excel y analizar estructura
            df = pd.read_excel(file_path, dtype=str, header=0)
            logger.info(f"Archivo cargado: {len(df)} filas, {len(df.columns)} columnas")
            
            # Analizar estructura del archivo
            structure = cls._analyze_file_structure(df)
            if not structure['valid']:
                return {"error": f"Estructura de archivo inválida: {structure['message']}", **stats}
            
            logger.info(f"Estructura detectada: {structure}")
            
            usuario_id = cls._get_admin_user()
            
            # Procesar cada fila
            for index, row in df.iterrows():
                if index == 0:  # Saltar header si es necesario
                    continue
                    
                try:
                    cls._process_row_with_transaction(row, usuario_id, stats, index, structure)
                except Exception as e:
                    stats['errores'] += 1
                    stats['detalles_errores'].append({
                        'fila': index + 1,
                        'error': str(e)
                    })
                    logger.error(f"Error fila {index+1}: {e}")
                    
                    # Si hay demasiados errores consecutivos, parar
                    if stats['errores'] > 10 and stats['errores'] == index:
                        raise Exception("Demasiados errores consecutivos, posible problema de estructura")
                    continue
            
            # Validar si la importación fue exitosa
            total_filas = len(df) - 1  # Excluir header
            if stats['errores'] > total_filas * 0.5:
                raise Exception(f"Demasiados errores: {stats['errores']} de {total_filas} filas")
            
            logger.info(f"Importación exitosa: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error importación: {e}")
            return {"error": str(e), **stats}
    
    @classmethod
    def _analyze_file_structure(cls, df: pd.DataFrame) -> Dict[str, Any]:
        """Analiza la estructura del archivo Excel para detectar columnas automáticamente"""
        
        structure = {
            'valid': False,
            'message': '',
            'columns': {},
            'cortes_columns': [],  # [(numero_corte, indice_columna), ...]
            'perdidas_columns': []  # [(numero_perdida, tipo, indice_columna), ...]
        }
        
        headers = [str(col).strip() for col in df.columns]
        logger.info(f"Headers detectados: {headers}")
        
        # Detectar columnas básicas
        for col_name, pattern in cls.COLUMN_PATTERNS.items():
            for i, header in enumerate(headers):
                if re.match(pattern, header):
                    structure['columns'][col_name] = i
                    break
        
        # Detectar columnas de cortes
        for i, header in enumerate(headers):
            for pattern in cls.CORTE_PATTERNS:
                match = re.match(pattern, header)
                if match:
                    # Extraer número de corte
                    corte_num = cls._extract_number_from_header(header)
                    if corte_num and 1 <= corte_num <= 20:
                        structure['cortes_columns'].append((corte_num, i))
                    break
        
        # Detectar columnas de pérdidas
        for i, header in enumerate(headers):
            for pattern in cls.PERDIDA_PATTERNS:
                match = re.match(pattern, header)
                if match:
                    perdida_num = cls._extract_number_from_header(header)
                    if perdida_num and 1 <= perdida_num <= 10:
                        if 'perdida' in header.lower() or 'loss' in header.lower():
                            structure['perdidas_columns'].append((perdida_num, 'cantidad', i))
                        elif 'causa' in header.lower() or 'cause' in header.lower():
                            structure['perdidas_columns'].append((perdida_num, 'causa', i))
                        elif 'fecha' in header.lower() or 'date' in header.lower():
                            structure['perdidas_columns'].append((perdida_num, 'fecha', i))
                    break
        
        # Ordenar columnas de cortes
        structure['cortes_columns'].sort(key=lambda x: x[0])
        
        # Validar estructura mínima
        required_columns = ['BLOQUE', 'CAMA', 'FLOR', 'COLOR', 'VARIEDAD', 'FECHA_SIEMBRA']
        missing_columns = [col for col in required_columns if col not in structure['columns']]
        
        if missing_columns:
            structure['message'] = f"Columnas obligatorias faltantes: {', '.join(missing_columns)}"
            return structure
        
        # Validar área y densidad (pueden estar como columnas separadas o calcularse)
        if 'AREA' not in structure['columns'] and 'PLANTAS' not in structure['columns']:
            structure['message'] = "Falta columna AREA o PLANTAS para calcular el total de plantas"
            return structure
        
        if 'DENSIDAD' not in structure['columns']:
            structure['message'] = "Falta columna DENSIDAD"
            return structure
        
        structure['valid'] = True
        structure['message'] = "Estructura válida"
        
        return structure
    
    @classmethod
    def _extract_number_from_header(cls, header: str) -> Optional[int]:
        """Extrae el número de un header (ej: 'CORTE 1' -> 1, '15' -> 15)"""
        numbers = re.findall(r'\d+', header)
        if numbers:
            return int(numbers[0])
        return None
    
    @classmethod
    def _process_row_with_transaction(cls, row: pd.Series, usuario_id: int, stats: Dict, index: int, structure: Dict):
        """Procesa una fila con su propia transacción"""
        try:
            cls._process_historical_row(row, usuario_id, stats, index, structure)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e
    
    @classmethod
    def _process_historical_row(cls, row: pd.Series, usuario_id: int, stats: Dict, index: int, structure: Dict):
        """Procesa una fila completa del histórico usando la estructura detectada"""
        
        cols = structure['columns']
        
        # 1. Extraer datos básicos
        bloque_nom = str(row.iloc[cols['BLOQUE']]).strip() if pd.notna(row.iloc[cols['BLOQUE']]) else ''
        cama_nom = str(row.iloc[cols['CAMA']]).strip() if pd.notna(row.iloc[cols['CAMA']]) else ''
        flor_nom = str(row.iloc[cols['FLOR']]).strip().upper() if pd.notna(row.iloc[cols['FLOR']]) else ''
        color_nom = str(row.iloc[cols['COLOR']]).strip().upper() if pd.notna(row.iloc[cols['COLOR']]) else ''
        variedad_nom = str(row.iloc[cols['VARIEDAD']]).strip().upper() if pd.notna(row.iloc[cols['VARIEDAD']]) else ''
        
        # Validar datos obligatorios
        if not all([bloque_nom, cama_nom, flor_nom, color_nom, variedad_nom]):
            raise ValueError(f"Datos básicos incompletos: bloque={bloque_nom}, cama={cama_nom}, flor={flor_nom}, color={color_nom}, variedad={variedad_nom}")
        
        # 2. Procesar fechas
        fecha_siembra = cls._parse_date(row.iloc[cols['FECHA_SIEMBRA']])
        fecha_inicio = cls._parse_date(row.iloc[cols['FECHA_INICIO_CORTE']]) if 'FECHA_INICIO_CORTE' in cols else None
        fecha_fin = cls._parse_date(row.iloc[cols['FECHA_FIN_CORTE']]) if 'FECHA_FIN_CORTE' in cols else None
        
        if not fecha_siembra:
            raise ValueError(f"Fecha siembra inválida: {row.iloc[cols['FECHA_SIEMBRA']]}")
        
        # 3. Procesar área y densidad
        area_val = 0.0
        densidad_val = 0.0
        plantas_val = 0.0
        
        if 'AREA' in cols:
            area_val = safe_float(row.iloc[cols['AREA']])
        
        if 'DENSIDAD' in cols:
            densidad_val = safe_float(row.iloc[cols['DENSIDAD']])
        
        if 'PLANTAS' in cols:
            plantas_val = safe_float(row.iloc[cols['PLANTAS']])
        
        # Calcular área si no está disponible pero tenemos plantas y densidad
        if area_val <= 0 and plantas_val > 0 and densidad_val > 0:
            area_val = plantas_val / densidad_val
        
        # Calcular plantas si no están disponibles pero tenemos área y densidad
        if plantas_val <= 0 and area_val > 0 and densidad_val > 0:
            plantas_val = area_val * densidad_val
        
        # Validar valores calculados
        if area_val <= 0:
            raise ValueError(f"Área inválida: {area_val} (plantas: {plantas_val}, densidad: {densidad_val})")
        
        if densidad_val <= 0:
            raise ValueError(f"Densidad inválida: {densidad_val}")
        
        # 4. Verificar si la siembra ya existe
        existing_check = cls._check_existing_siembra(bloque_nom, cama_nom, variedad_nom, fecha_siembra)
        if existing_check:
            logger.info(f"Siembra ya existe para {bloque_nom}-{cama_nom}, variedad {variedad_nom}, fecha {fecha_siembra}")
            return
        
        # 5. Crear entidades
        variedad = cls._get_or_create_variedad(flor_nom, color_nom, variedad_nom)
        area = cls._get_or_create_area(area_val)
        densidad = cls._get_or_create_densidad(densidad_val)
        ubicacion = cls._get_or_create_ubicacion(bloque_nom, cama_nom)
        
        # 6. Crear siembra
        siembra = cls._create_siembra(
            ubicacion, variedad, area, densidad, fecha_siembra,
            fecha_inicio, fecha_fin, usuario_id, stats
        )
        
        # 7. Procesar cortes usando la estructura detectada
        cls._process_cortes_from_structure(row, siembra, fecha_inicio, usuario_id, stats, structure)
        
        # 8. Procesar pérdidas usando la estructura detectada
        cls._process_perdidas_from_structure(row, siembra, usuario_id, stats, structure)
    
    @classmethod
    def _process_cortes_from_structure(cls, row, siembra, fecha_inicio, usuario_id, stats, structure):
        """Procesa cortes usando la estructura detectada"""
        
        for corte_num, col_idx in structure['cortes_columns']:
            if col_idx < len(row):
                tallos = safe_int(row.iloc[col_idx])
                
                if tallos > 0:
                    # Calcular fecha estimada
                    if fecha_inicio:
                        fecha_corte = fecha_inicio + timedelta(days=(corte_num-1)*7)
                    else:
                        fecha_corte = siembra.fecha_siembra + timedelta(days=65 + (corte_num-1)*7)
                    
                    # Verificar que no exista ya
                    existing_corte = Corte.query.filter_by(
                        siembra_id=siembra.siembra_id, num_corte=corte_num
                    ).first()
                    
                    if not existing_corte:
                        corte = Corte(
                            siembra_id=siembra.siembra_id,
                            num_corte=corte_num,
                            fecha_corte=fecha_corte,
                            cantidad_tallos=tallos,
                            usuario_id=usuario_id
                        )
                        db.session.add(corte)
                        stats['cortes_creados'] += 1
    
    @classmethod
    def _process_perdidas_from_structure(cls, row, siembra, usuario_id, stats, structure):
        """Procesa pérdidas usando la estructura detectada"""
        
        # Agrupar columnas de pérdidas por número
        perdidas_data = {}
        for perdida_num, tipo, col_idx in structure['perdidas_columns']:
            if perdida_num not in perdidas_data:
                perdidas_data[perdida_num] = {}
            perdidas_data[perdida_num][tipo] = row.iloc[col_idx] if col_idx < len(row) else None
        
        # Procesar cada pérdida
        for perdida_num, data in perdidas_data.items():
            cantidad = safe_int(data.get('cantidad', 0))
            causa_nombre = str(data.get('causa', '')).strip().upper() if data.get('causa') else None
            fecha_perdida = cls._parse_date(data.get('fecha')) if data.get('fecha') else None
            
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
                    fecha_perdida = siembra.fecha_siembra + timedelta(days=45 + perdida_num*10)
                
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
    
    # Resto de métodos auxiliares (sin cambios)
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
    def _check_existing_siembra(cls, bloque: str, cama: str, variedad: str, fecha_siembra) -> bool:
        """Verifica si ya existe una siembra similar"""
        # Buscar ubicación
        bloque_obj = Bloque.query.filter_by(bloque=bloque).first()
        if not bloque_obj:
            return False
        
        cama_obj = Cama.query.filter_by(cama=cama).first()
        if not cama_obj:
            return False
        
        # Buscar variedad
        variedad_obj = Variedad.query.filter_by(variedad=variedad).first()
        if not variedad_obj:
            return False
        
        # Buscar ubicación completa
        ubicacion = BloqueCamaLado.query.filter_by(
            bloque_id=bloque_obj.bloque_id,
            cama_id=cama_obj.cama_id
        ).first()
        
        if not ubicacion:
            return False
        
        # Buscar siembra existente
        existing = Siembra.query.filter_by(
            bloque_cama_id=ubicacion.bloque_cama_id,
            variedad_id=variedad_obj.variedad_id,
            fecha_siembra=fecha_siembra
        ).first()
        
        return existing is not None
    
    @classmethod
    def _parse_date(cls, date_val) -> Optional[datetime.date]:
        """Parsea fecha de diferentes formatos"""
        if pd.isna(date_val):
            return None
        
        try:
            if isinstance(date_val, (datetime, pd.Timestamp)):
                return date_val.date()
            
            if isinstance(date_val, str):
                for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y']:
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