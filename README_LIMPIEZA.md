# Limpieza del Sistema - Eliminación de Módulos no Utilizados

Este documento describe el proceso para eliminar completamente los módulos de causas y pérdidas que ya no se utilizan en el sistema de Gestión de Camas.

## Descripción de la Limpieza

Se han eliminado los siguientes componentes del sistema:

1. Modelo de datos `Causa` y `Perdida`
2. Rutas y controladores relacionados con causas y pérdidas
3. Formularios para la gestión de causas y pérdidas
4. Plantillas HTML para la visualización de causas y pérdidas
5. Referencias a causas y pérdidas en otros módulos
6. Utilidades para la importación de causas

## Pasos para Completar la Limpieza

Para completar el proceso de limpieza, siga estos pasos en orden:

### 1. Ejecutar la Migración de Base de Datos

Este paso eliminará las tablas `causas` y `perdidas` de la base de datos:

```bash
python run_migrations.py
```

### 2. Eliminar Archivos y Directorios Obsoletos

Este script eliminará todos los archivos y directorios relacionados con los módulos no utilizados:

```bash
python cleanup.py
```

### 3. Verificar la Limpieza

Puede verificar que todos los cambios se hayan aplicado correctamente iniciando la aplicación:

```bash
python run.py
```

Navegue por la aplicación y verifique que:
- No hay enlaces o referencias a "pérdidas" o "causas" en la interfaz
- Las siembras solo muestran información de cortes, sin secciones de pérdidas
- El menú de administración no muestra opciones para gestionar causas

## Estructura de Archivos Modificados

Los siguientes archivos han sido modificados para eliminar las referencias a causas y pérdidas:

- `app/models.py`
- `app/__init__.py`
- `app/admin/routes.py`
- `app/admin/forms.py`
- `app/utils/dataset_importer.py`
- `run.py`
- `manage.py`
- `db_management.py`
- `app/templates/admin/datasets.html`
- `app/templates/base.html`
- `app/templates/siembras/detalles.html`
- `app/templates/siembras/index.html`

## Archivos Eliminados

Los siguientes archivos han sido eliminados por completo:

- `app/perdidas/__init__.py`
- `app/perdidas/forms.py`
- `app/perdidas/routes.py`
- `app/templates/perdidas/crear.html`
- `app/templates/perdidas/editar.html`
- `app/templates/perdidas/index.html`
- `app/templates/admin/causas.html`
- `app/templates/admin/importar_causas.html`
- `app/templates/admin/importar_causas_directo.html`
- `app/utils/causas_importer.py`

## Solución de Problemas

Si encuentra algún problema durante el proceso de limpieza:

1. **Error en la Migración**: Asegúrese de que el archivo de migración `migrations/versions/eliminar_causas_perdidas.py` existe y está correctamente configurado.

2. **Archivos que No se Pueden Eliminar**: Si algunos archivos no se pueden eliminar, verifique los permisos del sistema de archivos y cierre cualquier programa que pueda estar utilizando esos archivos.

3. **Referencias Persistentes**: Si todavía encuentra referencias a causas o pérdidas en la aplicación, busque en todos los archivos utilizando:
   ```bash
   grep -r "causa\|perdida" app/
   ```

4. **Problemas de Base de Datos**: Si encuentra errores relacionados con la base de datos, puede restaurar desde su copia de seguridad y reintentar el proceso.

## Notas Adicionales

- Este proceso no afecta a los datos de siembras y cortes existentes
- La vista de producción acumulada ha sido modificada para no mostrar información de pérdidas
- Se ha actualizado el método `total_perdidas` en la clase `Siembra` para que siempre retorne 0