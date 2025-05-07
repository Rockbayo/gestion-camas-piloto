@bp.route('/importar_causas_directo', methods=['GET', 'POST'])
@login_required
def importar_causas_directo():
    """Ruta simplificada para importar causas directamente"""
    if not current_user.has_permission('importar_datos'):
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        if 'archivo' not in request.files:
            flash('No se seleccionó ningún archivo', 'danger')
            return redirect(request.url)
        
        archivo = request.files['archivo']
        if archivo.filename == '':
            flash('No se seleccionó ningún archivo', 'danger')
            return redirect(request.url)
        
        if archivo and allowed_file(archivo.filename):
            # Guardar archivo temporalmente
            temp_path = os.path.join(TEMP_DIR, secure_filename(archivo.filename))
            archivo.save(temp_path)
            
            # Intentar importar causas
            try:
                print(f"Archivo guardado en: {temp_path}")
                print("Iniciando importación de causas...")
                
                # Detectar la columna correcta automáticamente
                df = pd.read_excel(temp_path)
                columnas = list(df.columns)
                column_mapping = {}
                
                # Buscar columna que contenga "causa" en su nombre
                for col in columnas:
                    if "causa" in col.lower():
                        column_mapping[col] = 'CAUSA'
                        print(f"Columna automáticamente mapeada: {col} -> CAUSA")
                        break
                
                # Si no se encontró, usar la primera columna
                if not column_mapping and columnas:
                    column_mapping[columnas[0]] = 'CAUSA'
                    print(f"Usando primera columna por defecto: {columnas[0]} -> CAUSA")
                
                # Importar causas
                success, message, stats = DatasetImporter.import_causas(
                    temp_path, 
                    column_mapping=column_mapping, 
                    validate_only=False, 
                    skip_first_row=True
                )
                
                print(f"Resultado: {success}")
                print(f"Mensaje: {message}")
                print(f"Estadísticas: {stats}")
                
                flash(message, 'success' if success else 'danger')
                
                # Redirigir a la vista de causas
                if success:
                    return redirect(url_for('admin.causas'))
                else:
                    return render_template('admin/importar_causas_directo.html')
            
            except Exception as e:
                import traceback
                print(f"Error al importar: {str(e)}")
                print(traceback.format_exc())
                flash(f"Error al importar: {str(e)}", 'danger')
                return redirect(request.url)
            finally:
                # Limpiar
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except:
                        pass
    
    return render_template('admin/importar_causas_directo.html')