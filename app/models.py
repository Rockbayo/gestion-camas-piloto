from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager

# Modelo para autenticación de usuarios
class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    
    usuario_id = db.Column(db.Integer, primary_key=True, autoincrement=True, unique=True)
    nombre_1 = db.Column(db.String(20), nullable=False)
    nombre_2 = db.Column(db.String(20))
    apellido_1 = db.Column(db.String(20), nullable=False)
    apellido_2 = db.Column(db.String(20))
    cargo = db.Column(db.String(20), nullable=False)
    num_doc = db.Column(db.Integer, nullable=False)
    documento_id = db.Column(db.Integer, db.ForeignKey('documentos.doc_id'), nullable=False)
    password_hash = db.Column(db.String(128))  # Campo adicional para almacenar contraseñas
    is_admin = db.Column(db.Boolean, default=False)  # Campo para identificar administradores
    
    # Relación con documento
    documento = db.relationship('Documento', backref='usuarios')
    
    # Relaciones para seguimiento de operaciones
    siembras = db.relationship('Siembra', backref='usuario', lazy='dynamic')
    cortes = db.relationship('Corte', backref='usuario', lazy='dynamic')
    perdidas = db.relationship('Perdida', backref='usuario', lazy='dynamic')
    
    def get_id(self):
        return str(self.usuario_id)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @property
    def nombre_completo(self):
        nombre = f"{self.nombre_1}"
        if self.nombre_2:
            nombre += f" {self.nombre_2}"
        nombre += f" {self.apellido_1}"
        if self.apellido_2:
            nombre += f" {self.apellido_2}"
        return nombre

@login_manager.user_loader
def load_user(id):
    return Usuario.query.get(int(id))

# Modelo para tipos de documento
class Documento(db.Model):
    __tablename__ = 'documentos'
    
    doc_id = db.Column(db.Integer, primary_key=True, autoincrement=True, unique=True)
    documento = db.Column(db.String(25), nullable=False)
    
    def __repr__(self):
        return self.documento

# Modelo para bloques
class Bloque(db.Model):
    __tablename__ = 'bloques'
    
    bloque_id = db.Column(db.Integer, primary_key=True, autoincrement=True, unique=True)
    bloque = db.Column(db.String(20), nullable=False, unique=True)
    
    def __repr__(self):
        return self.bloque

# Modelo para camas
class Cama(db.Model):
    __tablename__ = 'camas'
    
    cama_id = db.Column(db.Integer, primary_key=True, autoincrement=True, unique=True)
    cama = db.Column(db.String(10), nullable=False, unique=True)
    
    def __repr__(self):
        return self.cama

# Modelo para lados de camas
class Lado(db.Model):
    __tablename__ = 'lados'
    
    lado_id = db.Column(db.Integer, primary_key=True, autoincrement=True, unique=True)
    lado = db.Column(db.String(10), nullable=False, unique=True)
    
    def __repr__(self):
        return self.lado

# Tabla de relación muchos a muchos entre bloques, camas y lados
class BloqueCamaLado(db.Model):
    __tablename__ = 'bloques_camas_lado'
    
    bloque_cama_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    bloque_id = db.Column(db.Integer, db.ForeignKey('bloques.bloque_id'))
    cama_id = db.Column(db.Integer, db.ForeignKey('camas.cama_id'))
    lado_id = db.Column(db.Integer, db.ForeignKey('lados.lado_id'))
    
    # Restricción única compuesta
    __table_args__ = (db.UniqueConstraint('bloque_id', 'cama_id', 'lado_id'),)
    
    # Relaciones
    bloque = db.relationship('Bloque', backref=db.backref('camas_lados', lazy=True))
    cama = db.relationship('Cama', backref=db.backref('bloques_lados', lazy=True))
    lado = db.relationship('Lado', backref=db.backref('bloques_camas', lazy=True))
    siembras = db.relationship('Siembra', backref='bloque_cama_lado', lazy='dynamic')
    
    def __repr__(self):
        return f'Bloque {self.bloque.bloque} - Cama {self.cama.cama} - Lado {self.lado.lado}'

# Modelo para tipos de flor
class Flor(db.Model):
    __tablename__ = 'flores'
    
    flor_id = db.Column(db.Integer, primary_key=True, autoincrement=True, unique=True)
    flor = db.Column(db.String(10), nullable=False, unique=True)
    flor_abrev = db.Column(db.String(10), nullable=False, unique=True)
    
    # Relación muchos a muchos con colores
    colores = db.relationship('Color', secondary='flor_color', backref=db.backref('flores', lazy='dynamic'))
    
    def __repr__(self):
        return self.flor

# Modelo para colores de flores
class Color(db.Model):
    __tablename__ = 'colores'
    
    color_id = db.Column(db.Integer, primary_key=True, autoincrement=True, unique=True)
    color = db.Column(db.String(20), nullable=False, unique=True)
    color_abrev = db.Column(db.String(20), nullable=False, unique=True)
    
    def __repr__(self):
        return self.color

# Tabla de relación muchos a muchos entre flores y colores
class FlorColor(db.Model):
    __tablename__ = 'flor_color'
    
    flor_color_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    flor_id = db.Column(db.Integer, db.ForeignKey('flores.flor_id'))
    color_id = db.Column(db.Integer, db.ForeignKey('colores.color_id'))
    
    # Restricción única compuesta
    __table_args__ = (db.UniqueConstraint('flor_id', 'color_id'),)
    
    # Relaciones
    flor = db.relationship('Flor', backref=db.backref('flor_colores', lazy=True))
    color = db.relationship('Color', backref=db.backref('flor_colores', lazy=True))
    variedades = db.relationship('Variedad', backref='flor_color', lazy='dynamic')
    
    def __repr__(self):
        return f'{self.flor.flor} {self.color.color}'

# Modelo para variedades de flor
class Variedad(db.Model):
    __tablename__ = 'variedades'
    
    variedad_id = db.Column(db.Integer, primary_key=True, autoincrement=True, unique=True)
    variedad = db.Column(db.String(100), nullable=False)
    flor_color_id = db.Column(db.Integer, db.ForeignKey('flor_color.flor_color_id'), nullable=False)
    
    # Relación con siembras
    siembras = db.relationship('Siembra', backref='variedad', lazy='dynamic')
    
    # Relación con el historial de variedades
    historiales = db.relationship('VariedadHistorial', backref='variedad_actual', lazy='dynamic')
    
    def __repr__(self):
        return self.variedad

# Modelo para historial de nombres de variedades
class VariedadHistorial(db.Model):
    __tablename__ = 'var_hist'
    
    var_hist_id = db.Column(db.Integer, primary_key=True, autoincrement=True, unique=True)
    variedad_id = db.Column(db.Integer, db.ForeignKey('variedades.variedad_id'), nullable=False)
    variedad = db.Column(db.String(100))
    
    def __repr__(self):
        return self.variedad

# Modelo para áreas de siembra
class Area(db.Model):
    __tablename__ = 'areas'
    
    area_id = db.Column(db.Integer, primary_key=True, autoincrement=True, unique=True)
    siembra = db.Column(db.String(20), nullable=False, unique=True)
    area = db.Column(db.Float, nullable=False, unique=True)
    
    # Relación con siembras
    siembras = db.relationship('Siembra', backref='area_siembra', lazy='dynamic')
    
    def __repr__(self):
        return f'{self.siembra} ({self.area} m²)'

# Modelo para densidades de siembra
class Densidad(db.Model):
    __tablename__ = 'densidades'
    
    densidad_id = db.Column(db.Integer, primary_key=True, autoincrement=True, unique=True)
    densidad = db.Column(db.String(20), nullable=False, unique=True)
    
    # Relación con siembras
    siembras = db.relationship('Siembra', backref='densidad', lazy='dynamic')
    
    def __repr__(self):
        return self.densidad

# Modelo para siembras
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
    fecha_registro = db.Column(db.DateTime, nullable=False, default=datetime.now)
    
    # Relaciones con cortes y pérdidas
    cortes = db.relationship('Corte', backref='siembra', lazy='dynamic')
    perdidas = db.relationship('Perdida', backref='siembra', lazy='dynamic')
    
    def __repr__(self):
        ubicacion = str(self.bloque_cama_lado)
        return f'Siembra {self.siembra_id}: {self.variedad.variedad} en {ubicacion}'
    
    @property
    def dias_ciclo(self):
        """Calcula los días transcurridos desde la siembra hasta hoy o hasta el último corte."""
        ultima_fecha = datetime.now().date()
        ultimo_corte = self.cortes.order_by(Corte.fecha_corte.desc()).first()
        if ultimo_corte:
            ultima_fecha = ultimo_corte.fecha_corte
        
        return (ultima_fecha - self.fecha_siembra).days
    
    @property
    def total_tallos(self):
        """Suma el total de tallos cortados en esta siembra."""
        return sum(corte.cantidad_tallos for corte in self.cortes)
    
    @property
    def total_cortes(self):
        """Cuenta el número de cortes realizados."""
        return self.cortes.count()
    
    @property
    def total_perdidas(self):
        """Suma el total de pérdidas registradas."""
        return sum(perdida.cantidad for perdida in self.perdidas)

# Modelo para causas de pérdida
class Causa(db.Model):
    __tablename__ = 'causas'
    
    causa_id = db.Column(db.Integer, primary_key=True, autoincrement=True, unique=True)
    causa = db.Column(db.String(25), nullable=False, unique=True)
    
    # Relación con pérdidas
    perdidas = db.relationship('Perdida', backref='causa', lazy='dynamic')
    
    def __repr__(self):
        return self.causa

# Modelo para pérdidas
class Perdida(db.Model):
    __tablename__ = 'perdidas'
    
    perdida_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    siembra_id = db.Column(db.Integer, db.ForeignKey('siembras.siembra_id'), nullable=False)
    causa_id = db.Column(db.Integer, db.ForeignKey('causas.causa_id'), nullable=False)
    fecha_perdida = db.Column(db.Date, nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    observaciones = db.Column(db.Text)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.usuario_id'), nullable=False)
    fecha_registro = db.Column(db.DateTime, nullable=False, default=datetime.now)
    
    def __repr__(self):
        return f'Pérdida de {self.cantidad} en siembra {self.siembra_id} por {self.causa.causa}'

# Modelo para cortes
class Corte(db.Model):
    __tablename__ = 'cortes'
    
    corte_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    siembra_id = db.Column(db.Integer, db.ForeignKey('siembras.siembra_id'), nullable=False)
    num_corte = db.Column(db.Integer, nullable=False)
    fecha_corte = db.Column(db.Date, nullable=False)
    cantidad_tallos = db.Column(db.Integer, nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.usuario_id'), nullable=False)
    fecha_registro = db.Column(db.DateTime, nullable=False, default=datetime.now)
    
    # Restricción única compuesta para siembra_id y num_corte
    __table_args__ = (db.UniqueConstraint('siembra_id', 'num_corte', name='siembra_corte_unique'),)
    
    def __repr__(self):
        return f'Corte {self.num_corte} de siembra {self.siembra_id}: {self.cantidad_tallos} tallos'
    
    @property
    def dias_desde_siembra(self):
        """Calcula los días transcurridos desde la siembra hasta este corte."""
        return (self.fecha_corte - self.siembra.fecha_siembra).days
    
    @property
    def dias_desde_inicio(self):
        """Calcula los días transcurridos desde el inicio de corte hasta este corte."""
        if self.siembra.fecha_inicio_corte:
            return (self.fecha_corte - self.siembra.fecha_inicio_corte).days
        return None

# Modelo para labores
class Labor(db.Model):
    __tablename__ = 'labores'
    
    labor_id = db.Column(db.Integer, primary_key=True, autoincrement=True, unique=True)
    labor = db.Column(db.String(20), nullable=False, unique=True)
    
    def __repr__(self):
        return self.labor