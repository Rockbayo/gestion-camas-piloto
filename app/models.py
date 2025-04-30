from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager

@login_manager.user_loader
def load_user(id):
    return Usuario.query.get(int(id))

class Documento(db.Model):
    __tablename__ = 'documentos'
    doc_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    documento = db.Column(db.String(25), nullable=False)
    
    def __repr__(self):
        return f'<Documento {self.documento}>'

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    usuario_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre_1 = db.Column(db.String(20), nullable=False)
    nombre_2 = db.Column(db.String(20))
    apellido_1 = db.Column(db.String(20), nullable=False)
    apellido_2 = db.Column(db.String(20))
    cargo = db.Column(db.String(20), nullable=False)
    num_doc = db.Column(db.Integer, nullable=False)
    documento_id = db.Column(db.Integer, db.ForeignKey('documentos.doc_id'), nullable=False)
    # Campos adicionales para autenticación
    username = db.Column(db.String(20), unique=True)
    password_hash = db.Column(db.String(128))
    
    # Relación con documento
    documento = db.relationship('Documento', backref='usuarios')
    
    def get_id(self):
        return str(self.usuario_id)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<Usuario {self.nombre_1} {self.apellido_1}>'

class Bloque(db.Model):
    __tablename__ = 'bloques'
    bloque_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
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
    bloque_id = db.Column(db.Integer, db.ForeignKey('bloques.bloque_id'))
    cama_id = db.Column(db.Integer, db.ForeignKey('camas.cama_id'))
    lado_id = db.Column(db.Integer, db.ForeignKey('lados.lado_id'))
    
    # Relaciones
    bloque = db.relationship('Bloque', backref='bloques_camas_lado')
    cama = db.relationship('Cama', backref='bloques_camas_lado')
    lado = db.relationship('Lado', backref='bloques_camas_lado')
    
    __table_args__ = (db.UniqueConstraint('bloque_id', 'cama_id', 'lado_id'),)
    
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
    
    def __repr__(self):
        return f'<FlorColor {self.flor_id}-{self.color_id}>'

class Variedad(db.Model):
    __tablename__ = 'variedades'
    variedad_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    variedad = db.Column(db.String(100), nullable=False)
    flor_color_id = db.Column(db.Integer, db.ForeignKey('flor_color.flor_color_id'), nullable=False)
    
    # Relación
    flor_color = db.relationship('FlorColor', backref='variedades')
    
    def __repr__(self):
        return f'<Variedad {self.variedad}>'

class Area(db.Model):
    __tablename__ = 'areas'
    area_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    siembra = db.Column(db.String(20), nullable=False, unique=True)
    area = db.Column(db.Float, nullable=False, unique=True)
    
    def __repr__(self):
        return f'<Area {self.siembra}>'

class Densidad(db.Model):
    __tablename__ = 'densidades'
    densidad_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    densidad = db.Column(db.String(20), nullable=False, unique=True)
    
    def __repr__(self):
        return f'<Densidad {self.densidad}>'

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