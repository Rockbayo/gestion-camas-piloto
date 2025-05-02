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
   flask init-db  # Inicializa datos básicos
   ```

5. Ejecutar la aplicación:
   ```
   python run.py
   ```

## Características

- Gestión de siembras
- Registro de cortes
- Seguimiento de pérdidas
- Generación de reportes y estadísticas
```