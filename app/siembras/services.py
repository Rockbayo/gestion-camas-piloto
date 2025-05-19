from datetime import datetime
from app import db
from app.models import (
    Siembra, BloqueCamaLado, Variedad, Area, Densidad, 
    Flor, Color, FlorColor, Bloque, Cama, Lado
)
from sqlalchemy import asc, func

class SiembraService:
    @staticmethod
    def obtener_siembras_paginadas(page=1, per_page=10):
        return Siembra.query.order_by(Siembra.fecha_siembra.desc()).paginate(
            page=page, per_page=per_page)

    @staticmethod
    def filtrar_variedades(flor_id=None, color_id=None):
        query = Variedad.query
        if flor_id and flor_id > 0:
            query = query.join(Variedad.flor_color).join(FlorColor.flor).filter(Flor.flor_id == flor_id)
        if color_id and color_id > 0:
            query = query.join(Variedad.flor_color).join(FlorColor.color).filter(Color.color_id == color_id)
        return query.order_by(Variedad.variedad).all()

    @staticmethod
    def calcular_area(cantidad_plantas, densidad_id):
        densidad = Densidad.query.get(densidad_id)
        if not densidad or not densidad.valor or densidad.valor <= 0:
            return None
        
        area_calculada = round(cantidad_plantas / densidad.valor, 2)
        area = Area.query.filter(
            func.abs(Area.area - area_calculada) < 0.1
        ).first()
        
        return {
            'area_calculada': area_calculada,
            'area_id': area.area_id if area else None,
            'area_nombre': f"ÁREA {area_calculada:.2f}m²"
        }

    @staticmethod
    def crear_siembra(form_data, usuario_id):
        bloque_cama = BloqueCamaLado.query.filter_by(
            bloque_id=form_data['bloque_id'],
            cama_id=form_data['cama_id'],
            lado_id=form_data['lado_id']
        ).first() or BloqueCamaLado(
            bloque_id=form_data['bloque_id'],
            cama_id=form_data['cama_id'],
            lado_id=form_data['lado_id']
        )
        
        db.session.add(bloque_cama)
        db.session.flush()
        
        densidad = Densidad.query.get(form_data['densidad_id'])
        area_calculada = form_data['cantidad_plantas'] / densidad.valor
        
        area = Area.query.get(form_data['area_id']) if form_data['area_id'] else None
        if not area:
            area_nombre = f"ÁREA {area_calculada:.2f}m²"
            area = Area.query.filter_by(siembra=area_nombre).first() or Area(
                siembra=area_nombre, 
                area=area_calculada
            )
            db.session.add(area)
            db.session.flush()
        
        siembra = Siembra(
            bloque_cama_id=bloque_cama.bloque_cama_id,
            variedad_id=form_data['variedad_id'],
            area_id=area.area_id,
            densidad_id=form_data['densidad_id'],
            fecha_siembra=form_data['fecha_siembra'],
            usuario_id=usuario_id
        )
        
        db.session.add(siembra)
        db.session.commit()
        return siembra

    @staticmethod
    def actualizar_siembra(siembra_id, form_data):
        siembra = Siembra.query.get_or_404(siembra_id)
        
        nueva_ubicacion = BloqueCamaLado.query.filter_by(
            bloque_id=form_data['bloque_id'],
            cama_id=form_data['cama_id'],
            lado_id=form_data['lado_id']
        ).first() or BloqueCamaLado(
            bloque_id=form_data['bloque_id'],
            cama_id=form_data['cama_id'],
            lado_id=form_data['lado_id']
        )
        
        db.session.add(nueva_ubicacion)
        db.session.flush()
        
        siembra.bloque_cama_id = nueva_ubicacion.bloque_cama_id
        siembra.variedad_id = form_data['variedad_id']
        siembra.densidad_id = form_data['densidad_id']
        siembra.fecha_siembra = form_data['fecha_siembra']
        
        if form_data['area_id']:
            siembra.area_id = form_data['area_id']
        
        db.session.commit()
        return siembra

    @staticmethod
    def registrar_inicio_corte(siembra_id, fecha_inicio):
        siembra = Siembra.query.get_or_404(siembra_id)
        siembra.fecha_inicio_corte = fecha_inicio
        db.session.commit()
        return siembra

    @staticmethod
    def finalizar_siembra(siembra_id):
        siembra = Siembra.query.get_or_404(siembra_id)
        
        if not siembra.fecha_fin_corte:
            if siembra.cortes:
                siembra.fecha_fin_corte = max([c.fecha_corte for c in siembra.cortes])
            else:
                siembra.fecha_fin_corte = datetime.now().date()
        
        siembra.estado = 'Finalizada'
        db.session.commit()
        return siembra