from app import create_app, db
from app.models import (Usuario, Documento, Bloque, Cama, Lado, 
                        BloqueCamaLado, Flor, Color, FlorColor, 
                        Variedad, Area, Densidad, Siembra, Corte,
                        Causa, Perdida)

app = create_app()

@app.context_processor
def utility_processor():
    def now(format_string='%Y'):
        from datetime import datetime
        return datetime.now().strftime(format_string)
    return {'now': now}

@app.route('/')
def index():
    from app.routes import index
    return index()

@app.route('/dashboard')
def dashboard():
    from flask_login import login_required
    from flask import render_template
    from sqlalchemy import func, desc
    import matplotlib.pyplot as plt
    from io import BytesIO
    import base64
    
    @login_required
    def dashboard_view():
        # Obtener estadísticas para el dashboard
        siembras_activas = Siembra.query.filter_by(estado='Activa').count()
        total_cortes = Corte.query.count()
        total_tallos = db.session.query(func.sum(Corte.cantidad_tallos)).scalar() or 0
        total_variedades = Variedad.query.count()
        
        stats = {
            'siembras_activas': siembras_activas,
            'total_cortes': total_cortes,
            'total_tallos': total_tallos,
            'total_variedades': total_variedades
        }
        
        # Obtener últimos cortes
        ultimos_cortes = Corte.query.order_by(Corte.fecha_corte.desc()).limit(5).all()
        
        # Obtener últimas siembras
        ultimas_siembras = Siembra.query.order_by(Siembra.fecha_siembra.desc()).limit(5).all()
        
        # Crear gráfico de producción por variedad para el dashboard
        produccion_por_variedad = db.session.query(
            Variedad.variedad,
            func.sum(Corte.cantidad_tallos).label('total_tallos')
        ).join(
            Corte.siembra
        ).join(
            Siembra.variedad
        ).group_by(
            Variedad.variedad
        ).order_by(
            desc('total_tallos')
        ).limit(5).all()
        
        if produccion_por_variedad:
            # Crear gráfico con matplotlib
            plt.figure(figsize=(10, 6))
            plt.bar([r.variedad for r in produccion_por_variedad], 
                   [r.total_tallos for r in produccion_por_variedad])
            plt.xlabel('Variedad')
            plt.ylabel('Total de Tallos')
            plt.title('Top 5 Variedades por Producción')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            
            # Guardar gráfico en formato base64
            buffer = BytesIO()
            plt.savefig(buffer, format='png')
            buffer.seek(0)
            grafico_produccion = base64.b64encode(buffer.getvalue()).decode('utf-8')
            plt.close()
        else:
            grafico_produccion = None
        
        return render_template('dashboard.html', 
                              title='Dashboard', 
                              stats=stats, 
                              ultimos_cortes=ultimos_cortes, 
                              ultimas_siembras=ultimas_siembras,
                              grafico_produccion=grafico_produccion)
    
    return dashboard_view()

if __name__ == '__main__':
    app.run(debug=True)