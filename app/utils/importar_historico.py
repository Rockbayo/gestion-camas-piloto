# app/utils/importar_historico.py
import pandas as pd
from datetime import datetime, timedelta
import re
import os
from app import db, create_app
from app.models import Variedad, FlorColor, Flor, Color, Siembra, Corte, BloqueCamaLado
from app.models import Bloque, Cama, Lado, Area, Densidad, Usuario
from werkzeug.security import generate_password_hash

def importar_historico(archivo_excel):
    """Importa datos históricos de variedades, siembras y cortes desde el formato específico"""
    print(f"Iniciando importación desde archivo: {archivo_excel}")
    
    if not os.path.exists(archivo_excel):
        print(f"Error: El archivo {archivo_excel} no existe.")
        return
    
    try:
        # Cargar el archivo Excel
        df = pd.read_excel(archivo_excel)
        print(f"Archivo cargado exitosamente. {len(df)} filas encontradas.")
    except Exception as e:
        print(f"Error al cargar el archivo Excel: {e}")
        return
    
    # Crear la aplicación y contexto
    app = create_app()
    with app.app_context():
        # Obtener o crear el usuario administrador para asociar los registros
        admin = Usuario.query.filter_by(username='admin').first()
        if not admin:
            print("No se encontró usuario administrador. Creando uno...")
            doc = None
            try:
                from app.models import Documento
                doc = Documento.query.get(1)
                if not doc:
                    doc = Documento(doc_id=1, documento='Cedula de Ciudadania')
                    db.session.add(doc)
                    db.session.flush()
            except Exception as e:
                print(f"Error creando documento: {e}")
                return
            
            admin = Usuario(
                nombre_1='Admin',
                apellido_1='Sistema',
                cargo='Administrador',
                num_doc=999999,
                documento_id=1,
                username='admin'
            )
            admin.password_hash = generate_password_hash('admin123')
            db.session.add(admin)
            try:
                db.session.commit()
                print("Usuario administrador creado exitosamente.")
            except Exception as e:
                db.session.rollback()
                print(f"Error al crear usuario administrador: {e}")
                return
        
        total_siembras = 0
        total_cortes = 0
        
        # Procesar cada fila del Excel
        for index, row in df.iterrows():
            try:
                # Extraer datos básicos
                bloque_nombre = str(row.get('BLOQUE', ''))
                cama_completa = str(row.get('CAMA', ''))
                
                # Separar cama y lado
                lado_nombre = "A"  # Valor predeterminado
                cama_nombre = cama_completa.strip()
                
                # Extraer el lado (último carácter si es una letra)
                if cama_nombre and re.search(r'[A-Za-z]$', cama_nombre):
                    lado_nombre = cama_nombre[-1].upper()
                    cama_nombre = cama_nombre[:-1].strip()  # Quitar la letra del lado
                
                # Extraer área
                area_valor = 0
                try:
                    area_valor = float(row.get(' Area ', 0))
                except (ValueError, TypeError):
                    area_valor = 59.0  # Valor predeterminado
                
                # Extraer información de flor, color y variedad
                flor_nombre = str(row.get('FLOR', '')).strip().upper()
                color_nombre = str(row.get('COLOR', '')).strip().upper()
                variedad_nombre = str(row.get('VARIEDAD', '')).strip().upper()
                
                # Extraer fechas
                fecha_siembra = None
                fecha_inicio_corte = None
                fecha_fin_corte = None
                
                try:
                    if 'FECHA SIEMBRA' in row and not pd.isna(row['FECHA SIEMBRA']):
                        fecha_siembra = pd.to_datetime(row['FECHA SIEMBRA']).date()
                    
                    if 'FECHA INICIO CORTE' in row and not pd.isna(row['FECHA INICIO CORTE']):
                        fecha_inicio_corte = pd.to_datetime(row['FECHA INICIO CORTE']).date()
                    
                    if 'FECHA FIN CORTE' in row and not pd.isna(row['FECHA FIN CORTE']):
                        fecha_fin_corte = pd.to_datetime(row['FECHA FIN CORTE']).date()
                except Exception as e:
                    print(f"Error al convertir fechas en fila {index}: {e}")
                    continue
                
                # Si no hay fecha de siembra, no podemos continuar con esta fila
                if not fecha_siembra:
                    print(f"Fila {index}: Sin fecha de siembra, omitiendo.")
                    continue
                
                # Extraer detalles de siembra
                plantas = 0
                try:
                    plantas = int(row.get('PLANTAS', 0))
                except (ValueError, TypeError):
                    plantas = 0
                
                densidad_valor = 0
                try:
                    densidad_valor = float(row.get(' DENSIDAD ', 0))
                except (ValueError, TypeError):
                    densidad_valor = 85.0  # Valor predeterminado
                
                # Extraer tallos totales
                tallos_totales = 0
                try:
                    tallos_totales = int(row.get('TALLOS', 0))
                except (ValueError, TypeError):
                    tallos_totales = 0
                
                # Extraer datos de cortes (columnas numéricas del 1 al 15)
                cortes_datos = []
                for i in range(1, 16):  # Del 1 al 15
                    if i in row and not pd.isna(row[i]) and row[i] > 0:
                        try:
                            tallos = int(row[i])
                            # Calcular fecha aproximada si tenemos fecha de inicio
                            if fecha_inicio_corte:
                                # Aproximación: primer corte en fecha_inicio_corte, luego cada 7 días
                                fecha_corte = fecha_inicio_corte + timedelta(days=(i-1) * 7)
                                cortes_datos.append((i, fecha_corte, tallos))
                            else:
                                # Si no hay fecha de inicio, usamos días aproximados desde siembra
                                dias_estimados = 75 + (i-1) * 7  # 75 días para primer corte, luego cada 7
                                fecha_corte = fecha_siembra + timedelta(days=dias_estimados)
                                cortes_datos.append((i, fecha_corte, tallos))
                        except (ValueError, TypeError):
                            continue
                
                # Si no hay datos de cortes pero hay tallos totales, crear al menos un corte
                if not cortes_datos and tallos_totales > 0 and fecha_inicio_corte:
                    cortes_datos.append((1, fecha_inicio_corte, tallos_totales))
                
                # Proceder a crear entidades en la base de datos
                
                # Buscar o crear flor
                flor = Flor.query.filter(Flor.flor.ilike(flor_nombre)).first()
                if not flor and flor_nombre:
                    flor = Flor(flor=flor_nombre, flor_abrev=flor_nombre[:10])
                    db.session.add(flor)
                    db.session.flush()
                
                # Buscar o crear color
                color = Color.query.filter(Color.color.ilike(color_nombre)).first()
                if not color and color_nombre:
                    color = Color(color=color_nombre, color_abrev=color_nombre[:10])
                    db.session.add(color)
                    db.session.flush()
                
                # Buscar o crear combinación flor-color
                flor_color = None
                if flor and color:
                    flor_color = FlorColor.query.filter_by(flor_id=flor.flor_id, color_id=color.color_id).first()
                    if not flor_color:
                        flor_color = FlorColor(flor_id=flor.flor_id, color_id=color.color_id)
                        db.session.add(flor_color)
                        db.session.flush()
                
                # Buscar o crear variedad
                variedad = None
                if flor_color and variedad_nombre:
                    variedad = Variedad.query.filter(Variedad.variedad.ilike(variedad_nombre)).first()
                    if not variedad:
                        variedad = Variedad(variedad=variedad_nombre, flor_color_id=flor_color.flor_color_id)
                        db.session.add(variedad)
                        db.session.flush()
                
                # Si no tenemos variedad, no podemos continuar
                if not variedad:
                    print(f"Fila {index}: No se pudo obtener o crear variedad, omitiendo.")
                    continue
                
                # Buscar o crear bloque
                bloque = Bloque.query.filter(Bloque.bloque.ilike(bloque_nombre)).first()
                if not bloque and bloque_nombre:
                    bloque = Bloque(bloque=bloque_nombre)
                    db.session.add(bloque)
                    db.session.flush()
                
                # Buscar o crear cama
                cama = Cama.query.filter(Cama.cama.ilike(cama_nombre)).first()
                if not cama and cama_nombre:
                    cama = Cama(cama=cama_nombre)
                    db.session.add(cama)
                    db.session.flush()
                
                # Buscar o crear lado
                lado = Lado.query.filter(Lado.lado.ilike(lado_nombre)).first()
                if not lado and lado_nombre:
                    lado = Lado(lado=lado_nombre)
                    db.session.add(lado)
                    db.session.flush()
                
                # Si falta alguno de estos, no podemos continuar
                if not bloque or not cama or not lado:
                    print(f"Fila {index}: Faltan datos de ubicación, omitiendo.")
                    continue
                
                # Buscar o crear ubicación (bloque_cama_lado)
                bloque_cama = BloqueCamaLado.query.filter_by(
                    bloque_id=bloque.bloque_id, 
                    cama_id=cama.cama_id, 
                    lado_id=lado.lado_id
                ).first()
                
                if not bloque_cama:
                    bloque_cama = BloqueCamaLado(
                        bloque_id=bloque.bloque_id,
                        cama_id=cama.cama_id,
                        lado_id=lado.lado_id
                    )
                    db.session.add(bloque_cama)
                    db.session.flush()
                
                # Buscar o crear densidad
                densidad_nombre = f"D{int(densidad_valor)}"
                densidad = Densidad.query.filter(Densidad.densidad.ilike(densidad_nombre)).first()
                if not densidad:
                    densidad = Densidad(densidad=densidad_nombre, valor=densidad_valor)
                    db.session.add(densidad)
                    db.session.flush()
                
                # Buscar o crear área
                area_nombre = f"ÁREA {area_valor}m²"
                area = Area.query.filter(Area.siembra.ilike(area_nombre)).first()
                if not area:
                    area = Area(siembra=area_nombre, area=area_valor)
                    db.session.add(area)
                    db.session.flush()
                
                # Verificar si ya existe una siembra similar
                siembra_existente = Siembra.query.filter_by(
                    bloque_cama_id=bloque_cama.bloque_cama_id,
                    variedad_id=variedad.variedad_id,
                    fecha_siembra=fecha_siembra
                ).first()
                
                # Crear nueva siembra si no existe
                siembra = None
                if not siembra_existente:
                    estado = 'Finalizada' if fecha_fin_corte else 'Activa'
                    
                    siembra = Siembra(
                        bloque_cama_id=bloque_cama.bloque_cama_id,
                        variedad_id=variedad.variedad_id,
                        area_id=area.area_id,
                        densidad_id=densidad.densidad_id,
                        fecha_siembra=fecha_siembra,
                        fecha_inicio_corte=fecha_inicio_corte,
                        estado=estado,
                        usuario_id=admin.usuario_id
                    )
                    db.session.add(siembra)
                    db.session.flush()
                    total_siembras += 1
                else:
                    siembra = siembra_existente
                
                # Crear cortes
                for num_corte, fecha_corte, tallos in cortes_datos:
                    # Verificar si ya existe este corte
                    corte_existente = Corte.query.filter_by(
                        siembra_id=siembra.siembra_id,
                        num_corte=num_corte
                    ).first()
                    
                    if not corte_existente and tallos > 0:
                        corte = Corte(
                            siembra_id=siembra.siembra_id,
                            num_corte=num_corte,
                            fecha_corte=fecha_corte,
                            cantidad_tallos=tallos,
                            usuario_id=admin.usuario_id
                        )
                        db.session.add(corte)
                        total_cortes += 1
                
                # Confirmar cambios cada 10 filas para evitar transacciones muy largas
                if index % 10 == 0:
                    db.session.commit()
                    print(f"Procesadas {index+1} filas. Siembras: {total_siembras}, Cortes: {total_cortes}")
            
            except Exception as e:
                print(f"Error al procesar fila {index}: {e}")
                db.session.rollback()
                continue
        
        # Confirmar cambios finales
        try:
            db.session.commit()
            print(f"Importación completada. Total: {total_siembras} siembras y {total_cortes} cortes importados.")
        except Exception as e:
            db.session.rollback()
            print(f"Error al guardar cambios finales: {e}")

# Para probar directamente
if __name__ == "__main__":
    archivo = "Historicos CPC.xlsx"
    importar_historico(archivo)