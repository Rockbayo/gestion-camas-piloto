# Conexión a la base de datos y definición de modelos para la aplicación Flask
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import text

@login_manager.user_loader
def load_user(id):
    return Usuario.query.get(int(id))

class Documento(db.Model):
    __tablename__ = 'documentos'
    doc_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    documento = db.Column(db.String(25), nullable=False)
    
    def __repr__(self):
        return f'<Documento {self.documento}>'

class Rol(db.Model):
    __tablename__ = 'roles'
    rol_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    descripcion = db.Column(db.String(200))
    
    # Relación con permisos (muchos a muchos)
    permisos = db.relationship('Permiso', secondary='roles_permisos', backref='roles')
    
    def __repr__(self):
        return f'<Rol {self.nombre}>'

class Permiso(db.Model):
    __tablename__ = 'permisos'
    permiso_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    codigo = db.Column(db.String(50), unique=True, nullable=False)
    descripcion = db.Column(db.String(200))
    
    def __repr__(self):
        return f'<Permiso {self.codigo}>'

# Tabla de relación entre roles y permisos
roles_permisos = db.Table('roles_permisos',
    db.Column('rol_id', db.Integer, db.ForeignKey('roles.rol_id'), primary_key=True),
    db.Column('permiso_id', db.Integer, db.ForeignKey('permisos.permiso_id'), primary_key=True)
)

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    usuario_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre_1 = db.Column(db.String(20), nullable=False)
    nombre_2 = db.Column(db.String(20))
    apellido_1 = db.Column(db.String(20), nullable=False)
    apellido_2 = db.Column(db.String(20))
    cargo = db.Column(db.String(30), nullable=False)  # Longitud aumentada a 30 para coincidir con BD
    num_doc = db.Column(db.Integer, nullable=False)
    documento_id = db.Column(db.Integer, db.ForeignKey('documentos.doc_id'), nullable=False)
    # Campos para autenticación
    username = db.Column(db.String(20), unique=True)
    password_hash = db.Column(db.String(255))  # Cambiado a VARCHAR(255) según direct_db_update.py
    # Campo para rol
    rol_id = db.Column(db.Integer, db.ForeignKey('roles.rol_id'))
    
    # Relaciones
    documento = db.relationship('Documento', backref='usuarios')
    rol = db.relationship('Rol', backref='usuarios')
    
    def get_id(self):
        return str(self.usuario_id)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @hybrid_property
    def full_name(self):
        """Devuelve el nombre completo del usuario."""
        if self.nombre_2 and self.apellido_2:
            return f"{self.nombre_1} {self.nombre_2} {self.apellido_1} {self.apellido_2}"
        elif self.nombre_2:
            return f"{self.nombre_1} {self.nombre_2} {self.apellido_1}"
        elif self.apellido_2:
            return f"{self.nombre_1} {self.apellido_1} {self.apellido_2}"
        else:
            return f"{self.nombre_1} {self.apellido_1}"
    
    def has_permission(self, permission_code):
        """Verifica si el usuario tiene un permiso específico a través de su rol"""
        if not self.rol:
            return False
        
        for permiso in self.rol.permisos:
            if permiso.codigo == permission_code:
                return True
        
        return False
    
    def has_role(self, role_name):
        """Verifica si el usuario tiene un rol específico"""
        if not self.rol:
            return False
        
        return self.rol.nombre == role_name
    
    def __repr__(self):
        return f'<Usuario {self.nombre_1} {self.apellido_1}>'

class Bloque(db.Model):
    __tablename__ = 'bloques'
    # Corregido para utilizar TINYINT como en la base de datos
    bloque_id = db.Column(db.SmallInteger, primary_key=True, autoincrement=True)
    bloque = db.Column(db.String(20), nullable=False, unique=True)
    
    def __repr__(self):
        return f'<Bloque {self.bloque}>'

class Cama(db.Model):
    __tablename__ = 'camas'
    cama_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    cama = db.Column(db.String(10), nullable=False, unique=True)
    
    def __repr__(self):
        return f'<Cama {self.cama}>'

class Lado(db.Model):
    __tablename__ = 'lados'
    lado_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    lado = db.Column(db.String(10), nullable=False, unique=True)
    
    def __repr__(self):
        return f'<Lado {self.lado}>'

class BloqueCamaLado(db.Model):
    __tablename__ = 'bloques_camas_lado'
    bloque_cama_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # Corregido para utilizar TINYINT como en la base de datos
    bloque_id = db.Column(db.SmallInteger, db.ForeignKey('bloques.bloque_id'))
    cama_id = db.Column(db.Integer, db.ForeignKey('camas.cama_id'))
    lado_id = db.Column(db.Integer, db.ForeignKey('lados.lado_id'))
    
    # Relaciones
    bloque = db.relationship('Bloque', backref='bloques_camas_lado')
    cama = db.relationship('Cama', backref='bloques_camas_lado')
    lado = db.relationship('Lado', backref='bloques_camas_lado')
    
    __table_args__ = (db.UniqueConstraint('bloque_id', 'cama_id', 'lado_id'),)
    
    # Propiedad híbrida para obtener ubicación completa
    @hybrid_property
    def ubicacion_completa(self):
        return f"{self.bloque.bloque}-{self.cama.cama}-{self.lado.lado}"
    
    def __repr__(self):
        return f'<BloqueCamaLado {self.bloque_id}-{self.cama_id}-{self.lado_id}>'

class Flor(db.Model):
    __tablename__ = 'flores'
    flor_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    flor = db.Column(db.String(10), nullable=False, unique=True)
    flor_abrev = db.Column(db.String(10), nullable=False, unique=True)
    
    def __repr__(self):
        return f'<Flor {self.flor}>'

class Color(db.Model):
    __tablename__ = 'colores'
    color_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    color = db.Column(db.String(20), nullable=False, unique=True)
    color_abrev = db.Column(db.String(20), nullable=False, unique=True)
    
    def __repr__(self):
        return f'<Color {self.color}>'

class FlorColor(db.Model):
    __tablename__ = 'flor_color'
    flor_color_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    flor_id = db.Column(db.Integer, db.ForeignKey('flores.flor_id'))
    color_id = db.Column(db.Integer, db.ForeignKey('colores.color_id'))
    
    # Relaciones
    flor = db.relationship('Flor', backref='flor_color')
    color = db.relationship('Color', backref='flor_color')
    
    __table_args__ = (db.UniqueConstraint('flor_id', 'color_id'),)
    
    # Propiedad híbrida para obtener la descripción completa
    @hybrid_property
    def descripcion_completa(self):
        return f"{self.flor.flor} {self.color.color}"
    
    def __repr__(self):
        return f'<FlorColor {self.flor_id}-{self.color_id}>'

class Variedad(db.Model):
    __tablename__ = 'variedades'
    variedad_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    variedad = db.Column(db.String(100), nullable=False)
    flor_color_id = db.Column(db.Integer, db.ForeignKey('flor_color.flor_color_id'), nullable=False)
    
    # Relación
    flor_color = db.relationship('FlorColor', backref='variedades')
    
    # Propiedades híbridas para acceso directo a información relacionada
    @hybrid_property
    def flor_nombre(self):
        return self.flor_color.flor.flor
    
    @hybrid_property
    def color_nombre(self):
        return self.flor_color.color.color
    
    def __repr__(self):
        return f'<Variedad {self.variedad}>'

class Area(db.Model):
    __tablename__ = 'areas'
    area_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    siembra = db.Column(db.String(20), nullable=False, unique=True)
    area = db.Column(db.Float, nullable=False)
    
    def __repr__(self):
        return f'<Area {self.siembra}>'

class Densidad(db.Model):
    __tablename__ = 'densidades'
    densidad_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    densidad = db.Column(db.String(20), nullable=False, unique=True)
    # Nuevo campo para el valor de plantas por metro cuadrado
    valor = db.Column(db.Float, nullable=False, default=1.0)
    
    def __repr__(self):
        return f'<Densidad {self.densidad} ({self.valor} plantas/m²)>'

class Siembra(db.Model):
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
    
    # Relaciones
    bloque_cama = db.relationship('BloqueCamaLado', backref='siembras')
    variedad = db.relationship('Variedad', backref='siembras')
    area = db.relationship('Area', backref='siembras')
    densidad = db.relationship('Densidad', backref='siembras')
    usuario = db.relationship('Usuario', backref='siembras')
    
    # Métodos para operaciones comunes
    def finalizar(self):
        """Finaliza la siembra cambiando su estado"""
        self.estado = 'Finalizada'
        db.session.commit()
    
    def registrar_inicio_corte(self, fecha_inicio):
        """Registra la fecha de inicio de corte"""
        if not self.fecha_inicio_corte:
            self.fecha_inicio_corte = fecha_inicio
            db.session.commit()
            return True
        return False
    
    # Propiedades para calcular estadísticas
    @hybrid_property
    def total_tallos(self):
        return sum(corte.cantidad_tallos for corte in self.cortes)
    
    @hybrid_property
    def total_perdidas(self):
        return sum(perdida.cantidad for perdida in self.perdidas)
    
    @hybrid_property
    def dias_ciclo(self):
        """Calcula días desde la siembra hasta hoy o hasta el último corte"""
        ultima_fecha = max([corte.fecha_corte for corte in self.cortes]) if self.cortes else datetime.now().date()
        return (ultima_fecha - self.fecha_siembra).days
    
    def __repr__(self):
        return f'<Siembra {self.siembra_id}>'

class Corte(db.Model):
    __tablename__ = 'cortes'
    corte_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    siembra_id = db.Column(db.Integer, db.ForeignKey('siembras.siembra_id'), nullable=False)
    num_corte = db.Column(db.Integer, nullable=False)
    fecha_corte = db.Column(db.Date, nullable=False)
    cantidad_tallos = db.Column(db.Integer, nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.usuario_id'), nullable=False)
    fecha_registro = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relaciones
    siembra = db.relationship('Siembra', backref='cortes')
    usuario = db.relationship('Usuario', backref='cortes')
    
    __table_args__ = (db.UniqueConstraint('siembra_id', 'num_corte', name='siembra_corte_unique'),)
    
    @classmethod
    def registrar(cls, siembra_id, num_corte, fecha_corte, cantidad_tallos, usuario_id):
        """Método para registrar un nuevo corte utilizando el procedimiento almacenado"""
        sql = text("""
            CALL registrar_corte(:siembra_id, :num_corte, :fecha_corte, :cantidad_tallos, :usuario_id)
        """)
        db.session.execute(sql, {
            'siembra_id': siembra_id,
            'num_corte': num_corte,
            'fecha_corte': fecha_corte,
            'cantidad_tallos': cantidad_tallos,
            'usuario_id': usuario_id
        })
        db.session.commit()
    
    def __repr__(self):
        return f'<Corte {self.corte_id}>'

class Causa(db.Model):
    __tablename__ = 'causas'
    causa_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    causa = db.Column(db.String(25), nullable=False, unique=True)
    
    def __repr__(self):
        return f'<Causa {self.causa}>'

class Perdida(db.Model):
    __tablename__ = 'perdidas'
    perdida_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    siembra_id = db.Column(db.Integer, db.ForeignKey('siembras.siembra_id'), nullable=False)
    causa_id = db.Column(db.Integer, db.ForeignKey('causas.causa_id'), nullable=False)
    fecha_perdida = db.Column(db.Date, nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    observaciones = db.Column(db.Text)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.usuario_id'), nullable=False)
    fecha_registro = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relaciones
    siembra = db.relationship('Siembra', backref='perdidas')
    causa = db.relationship('Causa', backref='perdidas')
    usuario = db.relationship('Usuario', backref='perdidas')
    
    def __repr__(self):
        return f'<Perdida {self.perdida_id}>'

# Clase para acceder a las vistas de la base de datos
class VistaProduccionAcumulada(db.Model):
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
    total_perdidas = db.Column(db.Integer)
    dias_ciclo = db.Column(db.Integer)

# Clase para acceder a la vista por día de producción
class VistaProduccionPorDia(db.Model):
    __tablename__ = 'vista_produccion_por_dia'
    __table_args__ = {'info': {'is_view': True}}
    
    # Al ser una vista necesitamos definir una clave primaria compuesta
    variedad_id = db.Column(db.Integer, primary_key=True)
    dias_desde_siembra = db.Column(db.Integer, primary_key=True)
    variedad = db.Column(db.String(100))
    flor = db.Column(db.String(10))
    color = db.Column(db.String(20))
    promedio_tallos = db.Column(db.Float)

    