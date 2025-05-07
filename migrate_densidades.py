"""
Script para migrar las densidades existentes y añadir el campo de valor de plantas por metro cuadrado
"""
from app import create_app, db
from app.models import Densidad
from sqlalchemy import text

def actualizar_densidades():
    """Actualiza las densidades existentes con los valores predeterminados"""
    app = create_app()
    
    with app.app_context():
        # Verificar si la columna 'valor' existe en la tabla
        try:
            # Intentar añadir la columna si no existe
            db.session.execute(text("ALTER TABLE densidades ADD COLUMN valor FLOAT NOT NULL DEFAULT 1.0"))
            db.session.commit()
            print("Columna 'valor' añadida a la tabla densidades")
        except Exception as e:
            # Si ya existe, puede dar un error
            print(f"Info: {str(e)}")
            print("Continuando con la migración...")
        
        # Definir los valores predeterminados para las densidades comunes
        valores_densidades = {
            'BAJA': 1.0,    # 1 planta por metro cuadrado
            'NORMAL': 2.0,  # 2 plantas por metro cuadrado
            'ALTA': 4.0     # 4 plantas por metro cuadrado
        }
        
        # Obtener todas las densidades
        densidades = Densidad.query.all()
        
        # Si no hay densidades, crear las predeterminadas
        if not densidades:
            print("No hay densidades registradas. Creando densidades predeterminadas...")
            for nombre, valor in valores_densidades.items():
                densidad = Densidad(densidad=nombre, valor=valor)
                db.session.add(densidad)
            
            db.session.commit()
            print("Densidades predeterminadas creadas")
            return
        
        # Actualizar las densidades existentes si corresponden a las predeterminadas
        densidades_actualizadas = 0
        for densidad in densidades:
            # Convertir a mayúsculas para comparación insensible a casos
            nombre_upper = densidad.densidad.upper()
            
            # Buscar coincidencias aproximadas
            for key, valor in valores_densidades.items():
                if key in nombre_upper:
                    densidad.valor = valor
                    densidades_actualizadas += 1
                    print(f"Densidad '{densidad.densidad}' actualizada con valor {valor}")
                    break
        
        # Si no se han actualizado todas, establecer valores por defecto según el orden
        if densidades_actualizadas < len(densidades):
            print("Estableciendo valores por defecto para densidades restantes...")
            # Ordenar densidades por ID
            densidades_sin_valor = sorted(
                [d for d in densidades if d.valor == 1.0], 
                key=lambda x: x.densidad_id
            )
            
            # Asignar valores predeterminados en orden ascendente
            valores_por_defecto = [1.0, 2.0, 4.0]
            for i, densidad in enumerate(densidades_sin_valor):
                if i < len(valores_por_defecto):
                    densidad.valor = valores_por_defecto[i]
                    print(f"Densidad '{densidad.densidad}' configurada con valor por defecto {valores_por_defecto[i]}")
                else:
                    # Si hay más densidades que valores predefinidos, usar el último valor
                    densidad.valor = valores_por_defecto[-1]
                    print(f"Densidad '{densidad.densidad}' configurada con valor por defecto {valores_por_defecto[-1]}")
        
        db.session.commit()
        print("Migración de densidades completada")

if __name__ == "__main__":
    actualizar_densidades()