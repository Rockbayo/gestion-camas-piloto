# Sistema de Gestión para Cultivos

Sistema de gestión para cultivos con seguimiento de siembras, cortes y pérdidas.

## Requisitos

- Python 3.8 o superior
- MySQL 5.7 o superior

## Instalación

1. Clonar el repositorio:
   ```
   git clone https://github.com/tu-usuario/gestion-camas-piloto.git
   cd gestion-camas-piloto
   ```

2. Crear un entorno virtual e instalar dependencias:
   ```
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Configurar variables de entorno:
   - Copiar el archivo `.env.example` a `.env` y personalizar las variables
   - Asegurarse de que la DATABASE_URL esté configurada correctamente

4. Configurar la base de datos:
   ```
   flask db upgrade
   python manage.py init_db  # Inicializa datos básicos
   ```

5. Ejecutar la aplicación:
   ```
   python manage.py run
   ```

## Características

- **Gestión de siembras**: Registra y controla todas las siembras realizadas
- **Registro de cortes**: Documenta cortes de plantas con fechas y cantidades
- **Seguimiento de pérdidas**: Registra pérdidas con sus causas y cantidades
- **Generación de reportes**: Obtiene informes y estadísticas del cultivo
- **Gestión de datos maestros**: Administra variedades, bloques, camas, etc.

## Estructura del Proyecto

El proyecto sigue una estructura modular con blueprints de Flask:

```
gestion-camas-piloto/
├── app/                     # Aplicación principal
│   ├── admin/               # Módulo de administración
│   ├── auth/                # Módulo de autenticación
│   ├── cortes/              # Módulo de cortes
│   ├── main/                # Módulo principal
│   ├── perdidas/            # Módulo de pérdidas
│   ├── reportes/            # Módulo de reportes
│   ├── siembras/            # Módulo de siembras
│   ├── static/              # Archivos estáticos (CSS, JS)
│   ├── templates/           # Plantillas HTML
│   ├── utils/               # Utilidades
│   │   └── dataset_importer.py  # Utilidad para importación de datos
│   ├── __init__.py          # Inicialización de la aplicación
│   └── models.py            # Modelos de datos
├── migrations/              # Migraciones de base de datos
├── .env.example             # Ejemplo de variables de entorno
├── .gitignore               # Archivos ignorados por Git
├── config.py                # Configuración de la aplicación
├── db_management.py         # Gestión de base de datos
├── manage.py                # Script de administración
├── README.md                # Este archivo
├── requirements.txt         # Dependencias del proyecto
└── run.py                   # Punto de entrada alternativo
```

## Scripts de Administración

El proyecto incluye un script unificado `manage.py` para realizar tareas administrativas:

- **Inicializar la base de datos**: `python manage.py init_db`
- **Limpiar la base de datos**: `python manage.py clean_db`
- **Crear roles y permisos**: `python manage.py init_roles`
- **Crear usuario administrador**: `python manage.py init_admin`
- **Verificar la base de datos**: `python manage.py check_db`
- **Crear un nuevo usuario**: `python manage.py create_user`
- **Resetear contraseña**: `python manage.py reset_password`
- **Ejecutar servidor**: `python manage.py run`

## Gestión de Módulos

### Siembras

El módulo de siembras permite:
- Registrar nuevas siembras especificando variedad, ubicación y área
- Establecer fecha de inicio de corte
- Finalizar siembras
- Ver detalles completos de cada siembra

### Cortes

El módulo de cortes permite:
- Registrar cortes para cada siembra
- Especificar fecha y cantidad de tallos
- Editar o eliminar cortes existentes
- Ver historial de cortes

### Pérdidas

El módulo de pérdidas permite:
- Registrar pérdidas para cada siembra
- Especificar causa, fecha y cantidad
- Añadir observaciones
- Ver historial de pérdidas

### Reportes

El módulo de reportes permite:
- Ver estadísticas de producción por variedad
- Ver estadísticas de producción por bloque
- Analizar días de producción por corte
- Exportar datos a Excel

## Importación de Datos

El sistema permite importar datos mediante archivos Excel:

1. Acceder a la sección "Datasets" desde el menú principal
2. Seleccionar el tipo de datos a importar
3. Cargar un archivo Excel
4. Confirmar la asignación de columnas
5. Validar y/o importar los datos

## Usuarios y Permisos

El sistema cuenta con los siguientes roles:

- **Administrador**: Acceso completo al sistema
- **Supervisor**: Gestión de siembras, cortes y pérdidas
- **Operador**: Registro de cortes y pérdidas
- **Visitante**: Solo lectura

## Contribución

Para contribuir al proyecto:

1. Crear un fork del repositorio
2. Crear una rama para nuevas características
3. Realizar cambios y pruebas
4. Enviar un pull request