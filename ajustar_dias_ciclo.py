
from app import create_app, db
from sqlalchemy import text

app = create_app()
DIAS_MAX_CICLO = 155  # Establece un límite adaptativo para el ciclo

with app.app_context():
    # Eliminar vista existente si existe
    db.session.execute(text("DROP VIEW IF EXISTS vista_produccion_por_dia"))
    
    # Crear vista con límite de días de ciclo y fecha de fin de corte
    sql_vista = f"""
    CREATE VIEW vista_produccion_por_dia AS
    SELECT 
        v.variedad_id,
        LEAST(DATEDIFF(c.fecha_corte, s.fecha_siembra), {DIAS_MAX_CICLO}) AS dias_desde_siembra,
        v.variedad,
        f.flor,
        cl.color,
        AVG(c.cantidad_tallos / (a.area * d.valor) * 100) AS promedio_tallos
    FROM 
        cortes c
        JOIN siembras s ON c.siembra_id = s.siembra_id
        JOIN variedades v ON s.variedad_id = v.variedad_id
        JOIN flor_color fc ON v.flor_color_id = fc.flor_color_id
        JOIN flores f ON fc.flor_id = f.flor_id
        JOIN colores cl ON fc.color_id = cl.color_id
        JOIN areas a ON s.area_id = a.area_id
        JOIN densidades d ON s.densidad_id = d.densidad_id
    WHERE 
        DATEDIFF(c.fecha_corte, s.fecha_siembra) <= {DIAS_MAX_CICLO}
        AND (s.fecha_fin_corte IS NULL OR c.fecha_corte <= s.fecha_fin_corte)
    GROUP BY 
        v.variedad_id, 
        dias_desde_siembra,
        v.variedad,
        f.flor,
        cl.color;
    """
    
    db.session.execute(text(sql_vista))
    db.session.commit()
    print(f"Vista actualizada exitosamente con límite de {DIAS_MAX_CICLO} días")
