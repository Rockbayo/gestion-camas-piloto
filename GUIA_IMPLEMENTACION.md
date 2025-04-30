# Guía de Implementación - Sistema de Gestión de Camas Piloto

Esta guía te llevará paso a paso a través del proceso de configuración e implementación de tu sistema de gestión de camas piloto.

## Requisitos Previos

Antes de comenzar, asegúrate de tener instalado:

1. **Python 3.8 o superior** - [Descargar Python](https://www.python.org/downloads/)
2. **MySQL 8.0 o superior** - [Descargar MySQL](https://dev.mysql.com/downloads/mysql/)
3. **Git** (opcional, pero recomendado) - [Descargar Git](https://git-scm.com/downloads)
4. **Visual Studio Code** (o tu editor preferido) - [Descargar VS Code](https://code.visualstudio.com/download)

## Paso 1: Configurar el Repositorio

### Opción A: Usar Git (recomendado)

1. Crea un nuevo repositorio en GitHub:
   - Ve a [GitHub](https://github.com/)
   - Haz clic en el botón "+" y selecciona "New repository"
   - Nombra tu repositorio (por ejemplo, "sistema-camas-piloto")
   - Marca la opción "Initialize this repository with a README"
   - Haz clic en "Create repository"

2. Clona el repositorio en tu máquina local:
   ```bash
   git clone https://github.com/TU_USUARIO/sistema-camas-piloto.git
   cd sistema-camas-piloto
   ```

### Opción B: Sin usar Git

1. Crea una nueva carpeta para el proyecto:
   ```bash
   mkdir sistema-camas-piloto
   cd sistema-camas-piloto
   ```

## Paso 2: Configurar el Entorno Virtual

Crear y activar un entorno virtual es esencial para mantener las dependencias del proyecto aisladas:

### En Windows:
```bash
python -m venv venv
venv\Scripts\activate
```

### En macOS/Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```

## Paso 3: Crear la Estructura del Proyecto

Ahora vamos a crear la estructura de carpetas y archivos principales:

```bash
# Crear estructura básica
mkdir -p app/static/{css,js,img}
mkdir -p app/templates
mkdir -p app/auth/templates/auth
mkdir -p app/siembras/templates/siembras
mkdir -p app/cortes/templates/cortes
mkdir -p app/reportes/templates/reportes
```

## Paso 4: Instalar Dependencias

1. Crea un archivo `requirements.txt` con el siguiente contenido:
   ```
   flask==2.3.3
   flask-sqlalchemy==3.1.1
   flask-login==0.6.3
   flask-wtf==1.2.1
   flask-migrate==4.0.5
   pymysql==1.1.0
   python-dotenv==1.0.0
   werkzeug==2.3.7
   ```

2. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```

## Paso 5: Configurar la Base de Datos

1. Inicia MySQL y crea una base de datos:
   ```sql
   CREATE DATABASE cpc CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
   ```

2. Crea un archivo `.env` en la raíz del proyecto con la siguiente configuración:
   ```
   FLASK_APP=run.py
   FLASK_ENV=development
   SECRET_KEY=tu_clave_secreta_personalizada
   
   # Configuración de la base de datos
   DB_HOST=localhost
   DB_USER=tu_usuario_mysql
   DB_PASSWORD=tu_contraseña_mysql
   DB_NAME=cpc
   ```

## Paso 6: Implementar los Archivos del Proyecto

Ahora debes crear todos los archivos que hemos visto anteriormente. Puedes copiar y pegar el código desde los archivos que hemos desarrollado.

1. **Archivos de configuración**:
   - `config.py` - Configuración de la aplicación
   - `run.py` - Punto de entrada para ejecutar la aplicación
   - `.gitignore` - Archivos a ignorar en Git

2. **Archivos principales de la aplicación**:
   - `app/__init__.py` - Inicialización de la aplicación Flask
   - `app/models.py` - Modelos de la base de datos
   - `app/routes.py` - Rutas principales

3. **Módulo de autenticación**:
   - `app/auth/__init__.py`
   - `app/auth/routes.py`
   - `app/auth/forms.py`
   - Plantillas HTML en `app/auth/templates/auth/`

4. **Módulo de siembras**:
   - `app/siembras/__init__.py`
   - `app/siembras/routes.py`
   - `app/siembras/forms.py`
   - Plantillas HTML en `app/siembras/templates/siembras/`

5. **Módulo de cortes**:
   - `app/cortes/__init__.py`
   - `app/cortes/routes.py`
   - `app/cortes/forms.py`
   - Plantillas HTML en `app/cortes/templates/cortes/`

6. **Módulo de reportes**:
   - `app/reportes/__init__.py`
   - `app/reportes/routes.py`
   - Plantillas HTML en `app/reportes/templates/reportes/`

7. **Plantillas base y archivos estáticos**:
   - `app/templates/base.html`
   - `app/templates/navbar.html`
   - `app/templates/index.html`
   - `app/templates/dashboard.html`
   - `app/static/css/styles.css`
   - `app/static/js/scripts.js`

## Paso 7: Inicializar la Base de Datos

1. Inicializa las migraciones de Flask-Migrate:
   ```bash
   flask db init
   ```

2. Crea la primera migración:
   ```bash
   flask db migrate -m "Estructura inicial"
   ```

3. Aplica la migración para crear las tablas:
   ```bash
   flask db upgrade
   ```

4. Ejecuta el script para inicializar datos base:
   ```bash
   python init_db.py
   ```

5. Crea un usuario administrador:
   ```bash
   python create_admin.py
   ```

## Paso 8: Ejecutar la Aplicación

1. Inicia la aplicación Flask:
   ```bash
   flask run
   ```

2. Abre tu navegador y accede a: http://127.0.0.1:5000/

3. Inicia sesión con las credenciales del usuario administrador que creaste.

## Paso 9: Personalización y Uso

Después de la instalación básica, puedes personalizar el sistema según tus necesidades:

1. **Configurar ubicaciones**: Establece los bloques, camas y lados disponibles.
2. **Gestionar variedades**: Añade o edita las variedades de flores.
3. **Registrar siembras**: Comienza a registrar tus siembras en el sistema.
4. **Registrar cortes**: A medida que realices cortes, regístralos en la aplicación.
5. **Generar reportes**: Utiliza las funciones de reportes para analizar la producción.

## Solución de Problemas Comunes

### Problema de conexión a la base de datos
Si encuentras errores de conexión a la base de datos:
- Verifica que MySQL esté en ejecución.
- Comprueba las credenciales en el archivo `.env`.
- Asegúrate de que la base de datos `cpc` exista.

### Errores de importación
Si encuentras errores de importación en Python:
- Verifica que el entorno virtual esté activado.
- Confirma que todas las dependencias estén instaladas.
- Comprueba la estructura de carpetas del proyecto.

### Problemas con las migraciones
Si encuentras problemas con las migraciones de la base de datos:
- Elimina la carpeta `migrations/` y el archivo `.sqlite` (si existe).
- Reinicia el proceso de migración (pasos 7.1 a 7.3).

## Mantenimiento

Para mantener tu aplicación funcionando correctamente:

1. **Copias de seguridad**: Realiza copias de seguridad regulares de la base de datos.
2. **Actualizaciones**: Mantén actualizadas las dependencias de Python.
3. **Monitoreo**: Revisa los logs de la aplicación para detectar errores.

## Próximos Pasos

Una vez que tengas el sistema básico funcionando, considera estas mejoras:

1. **Implementar autenticación más robusta** (por ejemplo, recuperación de contraseñas).
2. **Añadir más tipos de reportes** específicos para tus necesidades.
3. **Implementar gráficos más avanzados** para una mejor visualización de datos.
4. **Desarrollar una API** para integrar con otros sistemas.
5. **Configurar un servidor de producción** (por ejemplo, con Gunicorn y Nginx) para uso en producción.

## Contacto y Soporte

Si encuentras problemas o tienes preguntas sobre el sistema, no dudes en:
- Revisar la documentación en este repositorio.
- Abrir un Issue en GitHub si encuentras un bug.
- Contactar al desarrollador para soporte adicional.

---

¡Felicidades! Ahora tienes un sistema de gestión de camas piloto personalizado y listo para usar. Este sistema te ayudará a mejorar significativamente el seguimiento y análisis de tu producción.