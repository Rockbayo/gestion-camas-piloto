"""Eliminar tablas causas y perdidas

Revision ID: f987d521e987
Revises: e0a8fcdd3553
Create Date: 2025-05-07 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = 'f987d521e987'
down_revision = 'e0a8fcdd3553'
branch_labels = None
depends_on = None


def upgrade():
    # Verificar si existen las tablas antes de intentar eliminarlas
    conn = op.get_bind()
    
    # Eliminar referencias a perdidas en vistas si existen
    result = conn.execute(text("SHOW TABLES LIKE 'vista_produccion_acumulada'"))
    if result.fetchone():
        # Modificar la vista para que no muestre la columna total_perdidas
        # o recrearla sin esta columna
        op.execute("""
        CREATE OR REPLACE VIEW vista_produccion_acumulada AS
        SELECT
            s.siembra_id,
            b.bloque,
            c.cama,
            l.lado,
            v.variedad,
            f.flor,
            col.color,
            s.fecha_siembra,
            s.fecha_inicio_corte,
            COALESCE(SUM(co.cantidad_tallos), 0) AS total_tallos,
            COUNT(co.corte_id) AS total_cortes,
            0 AS total_perdidas,
            DATEDIFF(COALESCE(MAX(co.fecha_corte), CURDATE()), s.fecha_siembra) AS dias_ciclo
        FROM
            siembras s
        JOIN bloques_camas_lado bcl ON s.bloque_cama_id = bcl.bloque_cama_id
        JOIN bloques b ON bcl.bloque_id = b.bloque_id
        JOIN camas c ON bcl.cama_id = c.cama_id
        JOIN lados l ON bcl.lado_id = l.lado_id
        JOIN variedades v ON s.variedad_id = v.variedad_id
        JOIN flor_color fc ON v.flor_color_id = fc.flor_color_id
        JOIN flores f ON fc.flor_id = f.flor_id
        JOIN colores col ON fc.color_id = col.color_id
        LEFT JOIN cortes co ON s.siembra_id = co.siembra_id
        GROUP BY
            s.siembra_id
        """)
    
    # Verificar y eliminar la tabla perdidas
    result = conn.execute(text("SHOW TABLES LIKE 'perdidas'"))
    if result.fetchone():
        op.drop_table('perdidas')
    
    # Verificar y eliminar la tabla causas
    result = conn.execute(text("SHOW TABLES LIKE 'causas'"))
    if result.fetchone():
        op.drop_table('causas')


def downgrade():
    # Recrear tabla causas
    op.create_table('causas',
        sa.Column('causa_id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('causa', sa.String(length=25), nullable=False),
        sa.PrimaryKeyConstraint('causa_id'),
        sa.UniqueConstraint('causa')
    )
    
    # Recrear tabla perdidas
    op.create_table('perdidas',
        sa.Column('perdida_id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('siembra_id', sa.Integer(), nullable=False),
        sa.Column('causa_id', sa.Integer(), nullable=False),
        sa.Column('cantidad', sa.Integer(), nullable=False),
        sa.Column('observaciones', sa.Text(), nullable=True),
        sa.Column('usuario_id', sa.Integer(), nullable=False),
        sa.Column('fecha_registro', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['causa_id'], ['causas.causa_id']),
        sa.ForeignKeyConstraint(['siembra_id'], ['siembras.siembra_id']),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.usuario_id']),
        sa.PrimaryKeyConstraint('perdida_id')
    )
    
    # Restaurar vista original si existe
    conn = op.get_bind()
    result = conn.execute(text("SHOW TABLES LIKE 'vista_produccion_acumulada'"))
    if result.fetchone():
        op.execute("""
        CREATE OR REPLACE VIEW vista_produccion_acumulada AS
        SELECT
            s.siembra_id,
            b.bloque,
            c.cama,
            l.lado,
            v.variedad,
            f.flor,
            col.color,
            s.fecha_siembra,
            s.fecha_inicio_corte,
            COALESCE(SUM(co.cantidad_tallos), 0) AS total_tallos,
            COUNT(co.corte_id) AS total_cortes,
            COALESCE(SUM(p.cantidad), 0) AS total_perdidas,
            DATEDIFF(COALESCE(MAX(co.fecha_corte), CURDATE()), s.fecha_siembra) AS dias_ciclo
        FROM
            siembras s
        JOIN bloques_camas_lado bcl ON s.bloque_cama_id = bcl.bloque_cama_id
        JOIN bloques b ON bcl.bloque_id = b.bloque_id
        JOIN camas c ON bcl.cama_id = c.cama_id
        JOIN lados l ON bcl.lado_id = l.lado_id
        JOIN variedades v ON s.variedad_id = v.variedad_id
        JOIN flor_color fc ON v.flor_color_id = fc.flor_color_id
        JOIN flores f ON fc.flor_id = f.flor_id
        JOIN colores col ON fc.color_id = col.color_id
        LEFT JOIN cortes co ON s.siembra_id = co.siembra_id
        LEFT JOIN perdidas p ON s.siembra_id = p.siembra_id
        GROUP BY
            s.siembra_id
        """)