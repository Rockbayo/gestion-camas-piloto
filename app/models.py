"""
Modelos de la base de datos para la aplicación CPC (Cultivo de Plantas y Cortes).

Este módulo contiene todas las definiciones de modelos SQLAlchemy para la aplicación,
incluyendo relaciones, métodos de utilidad y propiedades híbridas.

Mejoras implementadas:
- Clase BaseModel para funcionalidad común
- Documentación completa de cada modelo
- Type hints para mayor claridad
- Organización lógica de los modelos
- Métodos de utilidad mejorados
- Relaciones optimizadas
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import text, func, and_, or_
from decimal import Decimal

class BaseModel(db.Model):
    """
    Clase base abstracta que proporciona funcionalidad común a todos los modelos.
    """
    __abstract__ = True
    
    def save(self):
        """Guarda el objeto en la base de datos."""
        db.session.add(self)
        try:
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            raise e
    
    def delete(self):
        """Elimina el objeto de la base de datos."""
        db.session.delete(self)
        try:
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            raise e
    
    @classmethod
    def get_all(cls):
        """Obtiene todos los registros de este modelo."""
        return cls.query.all()
    
    @classmethod
    def get_by_id(cls, id):
        """Obtiene un registro por su ID."""
        return cls.query.get(id)

# ==============================================
# MODELOS DE AUTENTICACIÓN Y USUARIOS
# ==============================================

class Documento(BaseModel):
    """
    Modelo para tipos de documentos de identidad.
    """
    __tablename__ = 'documentos'
    doc_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    documento = db.Column(db.String(25), nullable=False, unique=True)
    
    def __repr__(self):
        return f'<Documento {self.documento}>'

class Rol(BaseModel):
    """
    Modelo para roles de usuarios en el sistema.
    """
    __tablename__ = 'roles'
    rol_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    descripcion = db.Column(db.String(200))
    
    # Relación muchos-a-muchos con Permiso
    permisos = db.relationship('Permiso', secondary='roles_permisos', backref=db.backref('roles', lazy='dynamic'))
    
    def __repr__(self):
        return f'<Rol {self.nombre}>'

class Permiso(BaseModel):
    """
    Modelo para permisos del sistema.
    """
    __tablename__ = 'permisos'
    permiso_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    codigo = db.Column(db.String(50), unique=True, nullable=False)
    descripcion = db.Column(db.String(200))
    
    def __repr__(self):
        return f'<Permiso {self.codigo}>'

# Tabla de relación muchos-a-muchos entre roles y permisos
roles_permisos = db.Table('roles_permisos',
    db.Column('rol_id', db.Integer, db.ForeignKey('roles.rol_id'), primary_key=True),
    db.Column('permiso_id', db.Integer, db.ForeignKey('permisos.permiso_id'), primary_key=True)
)

class Usuario(UserMixin, BaseModel):
    """
    Modelo para usuarios del sistema.
    Hereda de UserMixin para integración con Flask-Login.
    """
    __tablename__ = 'usuarios'
    usuario_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre_1 = db.Column(db.String(20), nullable=False)
    nombre_2 = db.Column(db.String(20))
    apellido_1 = db.Column(db.String(20), nullable=False)
    apellido_2 = db.Column(db.String(20))
    cargo = db.Column(db.String(30), nullable=False)
    num_doc = db.Column(db.Integer, nullable=False)
    documento_id = db.Column(db.Integer, db.ForeignKey('documentos.doc_id'), nullable=False)
    username = db.Column(db.String(20), unique=True)
    password_hash = db.Column(db.String(255))
    rol_id = db.Column(db.Integer, db.ForeignKey('roles.rol_id'))
    
    # Relaciones
    documento = db.relationship('Documento', backref=db.backref('usuarios', lazy='dynamic'))
    rol = db.relationship('Rol', backref=db.backref('usuarios', lazy='dynamic'))
    
    def get_id(self):
        """Obligatorio para Flask-Login."""
        return str(self.usuario_id)
    
    def set_password(self, password: str):
        """Genera y guarda el hash de la contraseña."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password: str) -> bool:
        """Verifica si la contraseña coincide con el hash almacenado."""
        return check_password_hash(self.password_hash, password)
    
    @hybrid_property
    def nombre_completo(self) -> str:
        """Devuelve el nombre completo del usuario."""
        parts = [self.nombre_1]
        if self.nombre_2:
            parts.append(self.nombre_2)
        parts.append(self.apellido_1)
        if self.apellido_2:
            parts.append(self.apellido_2)
        return ' '.join(parts)
    
    def has_permission(self, permission_code: str) -> bool:
        """Verifica si el usuario tiene un permiso específico."""
        if not self.rol:
            return False
        return any(p.codigo == permission_code for p in self.rol.permisos)
    
    def has_role(self, role_name: str) -> bool:
        """Verifica si el usuario tiene un rol específico."""
        return self.rol and self.rol.nombre == role_name
    
    def __repr__(self):
        return f'<Usuario {self.nombre_1} {self.apellido_1}>'

# ==============================================
# MODELOS DE ESTRUCTURA DE PRODUCCIÓN
# ==============================================

class Bloque(BaseModel):
    """
    Modelo para bloques de producción.
    """
    __tablename__ = 'bloques'
    bloque_id = db.Column(db.SmallInteger, primary_key=True, autoincrement=True)
    bloque = db.Column(db.String(20), nullable=False, unique=True)
    
    @classmethod
    def get_all_ordered(cls):
        """Obtiene todos los bloques ordenados numéricamente."""
        return cls.query.order_by(
            # Ordenar por longitud primero, luego alfabéticamente
            # Esto asegura que "01" venga antes que "10"
            func.length(cls.bloque),
            cls.bloque
        ).all()
    
    def __repr__(self):
        return f'<Bloque {self.bloque}>'

class Cama(BaseModel):
    """
    Modelo para camas de producción dentro de los bloques.
    """
    __tablename__ = 'camas'
    cama_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    cama = db.Column(db.String(10), nullable=False, unique=True)
    
    @classmethod
    def get_all_ordered(cls):
        """Obtiene todas las camas ordenadas numéricamente."""
        return cls.query.order_by(
            # Ordenar por longitud primero, luego alfabéticamente
            # Esto asegura que "001" venga antes que "010"
            func.length(cls.cama),
            cls.cama
        ).all()
    
    def __repr__(self):
        return f'<Cama {self.cama}>'

class Lado(BaseModel):
    """
    Modelo para lados de las camas de producción.
    """
    __tablename__ = 'lados'
    lado_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    lado = db.Column(db.String(10), nullable=False, unique=True)
    
    @classmethod
    def get_all_ordered(cls):
        """Obtiene todos los lados ordenados alfabéticamente."""
        return cls.query.order_by(cls.lado).all()
    
    def __repr__(self):
        return f'<Lado {self.lado}>'

class BloqueCamaLado(BaseModel):
    """
    Modelo para la relación entre bloques, camas y lados.
    """
    __tablename__ = 'bloques_camas_lado'
    bloque_cama_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    bloque_id = db.Column(db.SmallInteger, db.ForeignKey('bloques.bloque_id'))
    cama_id = db.Column(db.Integer, db.ForeignKey('camas.cama_id'))
    lado_id = db.Column(db.Integer, db.ForeignKey('lados.lado_id'))
    
    # Relaciones
    bloque = db.relationship('Bloque', backref=db.backref('ubicaciones', lazy='dynamic'))
    cama = db.relationship('Cama', backref=db.backref('ubicaciones', lazy='dynamic'))
    lado = db.relationship('Lado', backref=db.backref('ubicaciones', lazy='dynamic'))
    
    __table_args__ = (db.UniqueConstraint('bloque_id', 'cama_id', 'lado_id'),)
    
    @classmethod
    def get_all_ordered(cls):
        """Obtiene todas las ubicaciones ordenadas por bloque, cama y lado."""
        return cls.query.join(Bloque).join(Cama).join(Lado).order_by(
            func.length(Bloque.bloque), Bloque.bloque,
            func.length(Cama.cama), Cama.cama,
            Lado.lado
        ).all()
    
    @hybrid_property
    def ubicacion_completa(self) -> str:
        """Devuelve la ubicación completa en formato Bloque-Cama-Lado."""
        return f"{self.bloque.bloque}-{self.cama.cama}-{self.lado.lado}"
    
    def __repr__(self):
        return f'<Ubicación {self.ubicacion_completa}>'

# ==============================================
# MODELOS DE VARIEDADES Y FLORES
# ==============================================

class Flor(BaseModel):
    """
    Modelo para tipos de flores.
    """
    __tablename__ = 'flores'
    flor_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    flor = db.Column(db.String(10), nullable=False, unique=True)
    flor_abrev = db.Column(db.String(10), nullable=False, unique=True)
    
    def __repr__(self):
        return f'<Flor {self.flor}>'

class Color(BaseModel):
    """
    Modelo para colores de flores.
    """
    __tablename__ = 'colores'
    color_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    color = db.Column(db.String(20), nullable=False, unique=True)
    color_abrev = db.Column(db.String(20), nullable=False, unique=True)
    
    def __repr__(self):
        return f'<Color {self.color}>'

class FlorColor(BaseModel):
    """
    Modelo para la relación entre flores y colores.
    """
    __tablename__ = 'flor_color'
    flor_color_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    flor_id = db.Column(db.Integer, db.ForeignKey('flores.flor_id'))
    color_id = db.Column(db.Integer, db.ForeignKey('colores.color_id'))
    
    # Relaciones
    flor = db.relationship('Flor', backref=db.backref('combinaciones', lazy='dynamic'))
    color = db.relationship('Color', backref=db.backref('combinaciones', lazy='dynamic'))
    
    __table_args__ = (db.UniqueConstraint('flor_id', 'color_id'),)
    
    @hybrid_property
    def descripcion_completa(self) -> str:
        """Devuelve la descripción completa en formato Flor Color."""
        return f"{self.flor.flor} {self.color.color}"
    
    def __repr__(self):
        return f'<FlorColor {self.descripcion_completa}>'

class Variedad(BaseModel):
    """
    Modelo para variedades de flores.
    """
    __tablename__ = 'variedades'
    variedad_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    variedad = db.Column(db.String(100), nullable=False)
    flor_color_id = db.Column(db.Integer, db.ForeignKey('flor_color.flor_color_id'), nullable=False)
    
    # Relación
    flor_color = db.relationship('FlorColor', backref=db.backref('variedades', lazy='dynamic'))
    
    # Propiedades híbridas para acceso directo
    @hybrid_property
    def flor_nombre(self) -> str:
        """Nombre de la flor asociada."""
        return self.flor_color.flor.flor
    
    @hybrid_property
    def color_nombre(self) -> str:
        """Nombre del color asociado."""
        return self.flor_color.color.color
    
    @hybrid_property
    def nombre_completo(self) -> str:
        """Nombre completo de la variedad."""
        return f"{self.flor_nombre} {self.color_nombre} {self.variedad}"
    
    def __repr__(self):
        return f'<Variedad {self.nombre_completo}>'

# ==============================================
# MODELOS DE SIEMBRAS Y PRODUCCIÓN
# ==============================================

class Area(BaseModel):
    """
    Modelo para áreas de siembra.
    """
    __tablename__ = 'areas'
    area_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    siembra = db.Column(db.String(20), nullable=False, unique=True)
    area = db.Column(db.Numeric(10, 4), nullable=False)  # Área en metros cuadrados
    
    def __repr__(self):
        return f'<Area {self.siembra} ({self.area}m²)>'

class Densidad(BaseModel):
    """
    Modelo para densidades de siembra.
    """
    __tablename__ = 'densidades'
    densidad_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    densidad = db.Column(db.String(20), nullable=False, unique=True)
    valor = db.Column(db.Numeric(10, 4), nullable=False, default=1.0)  # Plantas/m²
    
    @property
    def valor_formateado(self):
        """Devuelve el valor de densidad formateado con 1 decimal."""
        return f"{float(self.valor):.1f}"
    
    @property
    def descripcion_completa(self):
        """Devuelve la descripción completa de la densidad."""
        return f"{self.densidad} ({self.valor_formateado} plantas/m²)"
    
    def __repr__(self):
        return f'<Densidad {self.densidad} ({self.valor_formateado} plantas/m²)>'

class Siembra(BaseModel):
    """
    Modelo para registros de siembras.
    """
    __tablename__ = 'siembras'
    siembra_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    bloque_cama_id = db.Column(db.Integer, db.ForeignKey('bloques_camas_lado.bloque_cama_id'), nullable=False)
    variedad_id = db.Column(db.Integer, db.ForeignKey('variedades.variedad_id'), nullable=False)
    area_id = db.Column(db.Integer, db.ForeignKey('areas.area_id'), nullable=False)
    densidad_id = db.Column(db.Integer, db.ForeignKey('densidades.densidad_id'), nullable=False)
    fecha_siembra = db.Column(db.Date, nullable=False)
    fecha_inicio_corte = db.Column(db.Date)
    estado = db.Column(db.Enum('Activa', 'Finalizada'), nullable=False, default='Activa')
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.usuario_id'), nullable=False)
    fecha_registro = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    fecha_fin_corte = db.Column(db.Date)
    
    # Relaciones
    bloque_cama = db.relationship('BloqueCamaLado', backref=db.backref('siembras', lazy='dynamic'))
    variedad = db.relationship('Variedad', backref=db.backref('siembras', lazy='dynamic'))
    area = db.relationship('Area', backref=db.backref('siembras', lazy='dynamic'))
    densidad = db.relationship('Densidad', backref=db.backref('siembras', lazy='dynamic'))
    usuario = db.relationship('Usuario', backref=db.backref('siembras', lazy='dynamic'))
    
    # Métodos de negocio
    def finalizar(self):
        """Marca la siembra como finalizada."""
        self.estado = 'Finalizada'
        self.fecha_fin_corte = datetime.utcnow().date()
        return self.save()
    
    def registrar_inicio_corte(self, fecha_inicio=None):
        """Registra la fecha de inicio de corte."""
        if not self.fecha_inicio_corte:
            self.fecha_inicio_corte = fecha_inicio or datetime.utcnow().date()
            return self.save()
        return False
    
    # Propiedades calculadas
    @hybrid_property
    def total_tallos(self) -> int:
        """Total de tallos cosechados en esta siembra."""
        return sum(corte.cantidad_tallos for corte in self.cortes)
    
    @hybrid_property
    def dias_ciclo(self) -> int:
        """
        Días desde siembra hasta fin de corte o último corte.
        """
        if self.fecha_fin_corte:
            fecha_fin = self.fecha_fin_corte
        elif self.cortes:
            fecha_fin = max(corte.fecha_corte for corte in self.cortes)
        else:
            fecha_fin = datetime.now().date()
        
        dias = (fecha_fin - self.fecha_siembra).days
        return max(0, dias)  # Sin límite arbitrario, pero no negativo
    
    @hybrid_property
    def total_plantas(self) -> int:
        """Total de plantas sembradas (área × densidad)."""
        return int(self.area.area * self.densidad.valor)
    
    @hybrid_property
    def indice_aprovechamiento(self) -> float:
        """Índice de aprovechamiento (tallos/plantas en porcentaje)."""
        if self.total_plantas > 0:
            return round((self.total_tallos / self.total_plantas) * 100, 2)
        return 0.0
    
    def __repr__(self):
        return f'<Siembra {self.variedad.nombre_completo} en {self.bloque_cama.ubicacion_completa}>'

class Corte(BaseModel):
    """
    Modelo para registros de cortes de flores.
    """
    __tablename__ = 'cortes'
    corte_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    siembra_id = db.Column(db.Integer, db.ForeignKey('siembras.siembra_id'), nullable=False)
    num_corte = db.Column(db.Integer, nullable=False)
    fecha_corte = db.Column(db.Date, nullable=False)
    cantidad_tallos = db.Column(db.Integer, nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.usuario_id'), nullable=False)
    fecha_registro = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relaciones
    siembra = db.relationship('Siembra', backref=db.backref('cortes', lazy='dynamic'))
    usuario = db.relationship('Usuario', backref=db.backref('cortes', lazy='dynamic'))
    
    __table_args__ = (db.UniqueConstraint('siembra_id', 'num_corte', name='siembra_corte_unique'),)
    
    # Métodos de clase
    @classmethod
    def registrar(cls, siembra_id: int, num_corte: int, fecha_corte: datetime.date, 
                 cantidad_tallos: int, usuario_id: int):
        """
        Registra un nuevo corte usando procedimiento almacenado.
        """
        sql = text("""
            CALL registrar_corte(:siembra_id, :num_corte, :fecha_corte, :cantidad_tallos, :usuario_id)
        """)
        try:
            db.session.execute(sql, {
                'siembra_id': siembra_id,
                'num_corte': num_corte,
                'fecha_corte': fecha_corte,
                'cantidad_tallos': cantidad_tallos,
                'usuario_id': usuario_id
            })
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            raise e
    
    # Propiedades calculadas
    @hybrid_property
    def indice_sobre_total(self) -> float:
        """Índice de este corte sobre el total de plantas sembradas."""
        if self.siembra.total_plantas > 0:
            return round((self.cantidad_tallos / self.siembra.total_plantas) * 100, 2)
        return 0.0
    
    @hybrid_property
    def indice_acumulado(self) -> float:
        """Índice acumulado de todos los cortes hasta este inclusive."""
        cortes_anteriores = Corte.query.filter(
            Corte.siembra_id == self.siembra_id,
            Corte.num_corte <= self.num_corte
        ).all()
        
        total_tallos = sum(c.cantidad_tallos for c in cortes_anteriores)
        
        if self.siembra.total_plantas > 0:
            return round((total_tallos / self.siembra.total_plantas) * 100, 2)
        return 0.0
    
    def obtener_prediccion(self) -> Optional[Dict[str, Any]]:
        """
        Obtiene predicción de producción basada en datos históricos.
        
        Returns:
            Dict con información de predicción o None si no hay datos
        """
        try:
            # Obtener días desde siembra
            dias_desde_siembra = (self.fecha_corte - self.siembra.fecha_siembra).days
            
            # Buscar siembras similares (misma variedad)
            siembras_similares = Siembra.query.filter(
                Siembra.variedad_id == self.siembra.variedad_id,
                Siembra.siembra_id != self.siembra_id,
                Siembra.cortes.any()
            ).all()
            
            if not siembras_similares:
                return None
                
            # Recopilar índices de cortes en días similares (+/- 5 días)
            indices = []
            for siembra in siembras_similares:
                for corte in siembra.cortes:
                    dias_corte = (corte.fecha_corte - siembra.fecha_siembra).days
                    if abs(dias_corte - dias_desde_siembra) <= 5:
                        indice = corte.indice_sobre_total
                        indices.append(indice)
            
            if not indices:
                return None
                
            # Calcular estadísticas
            return {
                'indice_actual': self.indice_sobre_total,
                'indice_promedio': round(sum(indices) / len(indices), 2),
                'indice_maximo': round(max(indices), 2),
                'indice_minimo': round(min(indices), 2),
                'diferencia': round(self.indice_sobre_total - (sum(indices) / len(indices)), 2),
                'num_referencias': len(indices)
            }
        except Exception as e:
            return None
    
    def __repr__(self):
        return f'<Corte #{self.num_corte} de {self.siembra}>'

# ==============================================
# MODELOS DE GESTIÓN DE CULTIVO
# ==============================================

class TipoLabor(BaseModel):
    """
    Modelo para tipos de labores culturales.
    """
    __tablename__ = 'tipos_labor'
    tipo_labor_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(50), nullable=False, unique=True)
    descripcion = db.Column(db.String(255))
    flor_id = db.Column(db.Integer, db.ForeignKey('flores.flor_id'))
    
    # Relación
    flor = db.relationship('Flor', backref=db.backref('tipos_labor', lazy='dynamic'))
    
    def __repr__(self):
        return f'<TipoLabor {self.nombre}>'

class LaborCultural(BaseModel):
    """
    Modelo para registro de labores culturales realizadas.
    """
    __tablename__ = 'labores_culturales'
    labor_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    siembra_id = db.Column(db.Integer, db.ForeignKey('siembras.siembra_id'), nullable=False)
    tipo_labor_id = db.Column(db.Integer, db.ForeignKey('tipos_labor.tipo_labor_id'), nullable=False)
    fecha_labor = db.Column(db.Date, nullable=False)
    observaciones = db.Column(db.Text)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.usuario_id'), nullable=False)
    fecha_registro = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relaciones
    siembra = db.relationship('Siembra', backref=db.backref('labores', lazy='dynamic'))
    tipo_labor = db.relationship('TipoLabor', backref=db.backref('labores', lazy='dynamic'))
    usuario = db.relationship('Usuario', backref=db.backref('labores', lazy='dynamic'))
    
    @property
    def dias_hasta_inicio_corte(self) -> Optional[int]:
        """Días entre esta labor y el inicio de corte de la siembra."""
        if not self.siembra.fecha_inicio_corte:
            return None
        return (self.siembra.fecha_inicio_corte - self.fecha_labor).days
    
    def __repr__(self):
        return f'<Labor {self.tipo_labor.nombre} en {self.fecha_labor}>'

class CausaPerdida(BaseModel):
    """
    Modelo para causas de pérdidas en la producción.
    """
    __tablename__ = 'causas_perdida'
    causa_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(50), nullable=False, unique=True)
    descripcion = db.Column(db.String(255))
    es_predefinida = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<CausaPerdida {self.nombre}>'

class Perdida(BaseModel):
    """
    Modelo para registro de pérdidas en la producción.
    """
    __tablename__ = 'perdidas'
    perdida_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    siembra_id = db.Column(db.Integer, db.ForeignKey('siembras.siembra_id'), nullable=False)
    causa_id = db.Column(db.Integer, db.ForeignKey('causas_perdida.causa_id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    fecha_perdida = db.Column(db.Date, nullable=False)
    observaciones = db.Column(db.Text)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.usuario_id'), nullable=False)
    fecha_registro = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relaciones
    siembra = db.relationship('Siembra', backref=db.backref('perdidas', lazy='dynamic'))
    causa = db.relationship('CausaPerdida', backref=db.backref('registros', lazy='dynamic'))
    usuario = db.relationship('Usuario', backref=db.backref('perdidas', lazy='dynamic'))
    
    def __repr__(self):
        return f'<Pérdida {self.causa.nombre}: {self.cantidad} plantas>'

# ==============================================
# VISTAS DE LA BASE DE DATOS
# ==============================================

class VistaProduccionAcumulada(db.Model):
    """
    Vista para consultar producción acumulada por siembra.
    """
    __tablename__ = 'vista_produccion_acumulada'
    __table_args__ = {'info': {'is_view': True}}
    
    siembra_id = db.Column(db.Integer, primary_key=True)
    bloque = db.Column(db.String(20))
    cama = db.Column(db.String(10))
    lado = db.Column(db.String(10))
    variedad = db.Column(db.String(100))
    flor = db.Column(db.String(10))
    color = db.Column(db.String(20))
    fecha_siembra = db.Column(db.Date)
    fecha_inicio_corte = db.Column(db.Date)
    total_tallos = db.Column(db.Integer)
    total_cortes = db.Column(db.Integer)
    dias_ciclo = db.Column(db.Integer)
    
    def __repr__(self):
        return f'<Producción {self.variedad} en {self.bloque}-{self.cama}-{self.lado}>'

class VistaProduccionPorDia(db.Model):
    """
    Vista para consultar producción promedio por día desde siembra.
    """
    __tablename__ = 'vista_produccion_por_dia'
    __table_args__ = {'info': {'is_view': True}}
    
    variedad_id = db.Column(db.Integer, primary_key=True)
    dias_desde_siembra = db.Column(db.Integer, primary_key=True)
    variedad = db.Column(db.String(100))
    flor = db.Column(db.String(10))
    color = db.Column(db.String(20))
    promedio_tallos = db.Column(db.Float)
    
    def __repr__(self):
        return f'<ProducciónDía {self.variedad} día {self.dias_desde_siembra}>'

# ==============================================
# CONFIGURACIÓN DE LOGIN MANAGER
# ==============================================

@login_manager.user_loader
def load_user(user_id: str) -> Optional[Usuario]:
    """Función requerida por Flask-Login para cargar usuarios."""
    return Usuario.query.get(int(user_id))