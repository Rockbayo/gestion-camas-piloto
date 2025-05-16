// app/static/js/curva_interactiva.js
import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine, Area, Bar } from 'recharts';

const CurvaProduccionInteractiva = () => {
  // Estados para almacenar datos y controlar visualización
  const [puntosCurva, setPuntosCurva] = useState([]);
  const [infoVariedad, setInfoVariedad] = useState({ nombre: '', flor: '', color: '' });
  const [ciclos, setCiclos] = useState({ vegetativo: 0, productivo: 0, total: 0 });
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);
  const [modoVisualizacion, setModoVisualizacion] = useState('linea'); // linea, area, barras
  const [mostrarEtiquetas, setMostrarEtiquetas] = useState(true);
  const [mostrarLineasCiclo, setMostrarLineasCiclo] = useState(true);
  
  // Extraer datos de la página (inyectados desde Flask)
  useEffect(() => {
    try {
      setCargando(true);
      
      // Obtener datos de Flask (inyectados como variables globales)
      const puntosCurvaData = window.PUNTOS_CURVA || [];
      const ciclosData = {
        vegetativo: window.CICLO_VEGETATIVO || 0,
        productivo: window.CICLO_PRODUCTIVO || 0,
        total: window.CICLO_TOTAL || 0
      };
      const variedadData = {
        nombre: window.VARIEDAD_NOMBRE || '',
        flor: window.VARIEDAD_FLOR || '',
        color: window.VARIEDAD_COLOR || ''
      };
      
      // Si no hay datos y existe el endpoint de API, intentar cargarlos por AJAX
      if (puntosCurvaData.length === 0 && window.VARIEDAD_ID) {
        // Usar datos de ejemplo por ahora
        const datosEjemplo = generarDatosEjemplo(window.VARIEDAD_ID);
        setPuntosCurva(datosEjemplo.puntos);
        setCiclos(datosEjemplo.ciclos);
        setInfoVariedad(datosEjemplo.variedad);
      } else {
        // Usar datos proporcionados por Flask
        setPuntosCurva(procesarPuntosCurva(puntosCurvaData));
        setCiclos(ciclosData);
        setInfoVariedad(variedadData);
      }
      
      setCargando(false);
    } catch (err) {
      console.error("Error al cargar datos:", err);
      setError("Error al cargar los datos de la curva de producción");
      setCargando(false);
    }
  }, []);
  
  // Función para procesar los puntos de la curva
  const procesarPuntosCurva = (puntosCrudos) => {
    return puntosCrudos.map(punto => ({
      dia: punto.dia,
      indice: punto.indice_promedio,
      minIndice: punto.min_indice || 0,
      maxIndice: punto.max_indice || punto.indice_promedio * 1.1,
      muestras: punto.num_datos || 1
    }));
  };
  
  // Función para datos de ejemplo (cuando no hay datos reales)
  const generarDatosEjemplo = (variedadId) => {
    const cicloVegetativo = 65;
    const cicloTotal = 90;
    
    // Generar puntos de ejemplo
    const puntos = [];
    puntos.push({ dia: 0, indice: 0, minIndice: 0, maxIndice: 0, muestras: 1 });
    
    // Fase vegetativa (crecimiento lento)
    for (let dia = cicloVegetativo; dia < cicloTotal; dia += 5) {
      // Crecimiento logístico simulado
      const fase = (dia - cicloVegetativo) / (cicloTotal - cicloVegetativo);
      const indice = 80 * (1 / (1 + Math.exp(-10 * (fase - 0.5))));
      
      puntos.push({
        dia,
        indice: Math.round(indice * 10) / 10,
        minIndice: Math.round(indice * 0.8 * 10) / 10,
        maxIndice: Math.round(indice * 1.2 * 10) / 10,
        muestras: Math.floor(Math.random() * 5) + 1
      });
    }
    
    return {
      puntos,
      ciclos: {
        vegetativo: cicloVegetativo,
        productivo: cicloTotal - cicloVegetativo,
        total: cicloTotal
      },
      variedad: {
        nombre: `Variedad ${variedadId}`,
        flor: "Flor Ejemplo",
        color: "Color Ejemplo"
      }
    };
  };
  
  // Componente personalizado para el tooltip
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white p-2 border rounded shadow-sm">
          <p className="font-weight-bold mb-0">Día {label}</p>
          <p className="mb-0">Índice: {payload[0].value.toFixed(2)}%</p>
          {payload[0].payload.minIndice !== undefined && (
            <p className="mb-0 small text-muted">
              Rango: {payload[0].payload.minIndice.toFixed(2)}% - {payload[0].payload.maxIndice.toFixed(2)}%
            </p>
          )}
          {payload[0].payload.muestras && (
            <p className="mb-0 small text-muted">
              Basado en {payload[0].payload.muestras} muestras
            </p>
          )}
        </div>
      );
    }
    return null;
  };
  
  // Si está cargando, mostrar indicador
  if (cargando) {
    return (
      <div className="d-flex justify-content-center align-items-center p-5">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Cargando...</span>
        </div>
      </div>
    );
  }
  
  // Si hay error, mostrar mensaje
  if (error) {
    return (
      <div className="alert alert-danger">
        <i className="fas fa-exclamation-triangle me-2"></i>
        {error}
      </div>
    );
  }
  
  // Si no hay datos, mostrar mensaje
  if (!puntosCurva || puntosCurva.length === 0) {
    return (
      <div className="alert alert-info">
        <i className="fas fa-info-circle me-2"></i>
        No hay datos suficientes para generar la curva de producción.
      </div>
    );
  }
  
  return (
    <div className="card shadow">
      <div className="card-header bg-primary text-white">
        <h5 className="card-title mb-0">
          Curva de Producción Interactiva: {infoVariedad.nombre}
          <small className="ms-2">{infoVariedad.flor} {infoVariedad.color}</small>
        </h5>
      </div>
      <div className="card-body">
        {/* Controles de visualización */}
        <div className="mb-3 d-flex justify-content-between align-items-center">
          <div className="btn-group">
            <button 
              className={`btn btn-sm ${modoVisualizacion === 'linea' ? 'btn-primary' : 'btn-outline-primary'}`}
              onClick={() => setModoVisualizacion('linea')}
            >
              <i className="fas fa-chart-line me-1"></i> Línea
            </button>
            <button 
              className={`btn btn-sm ${modoVisualizacion === 'area' ? 'btn-primary' : 'btn-outline-primary'}`}
              onClick={() => setModoVisualizacion('area')}
            >
              <i className="fas fa-chart-area me-1"></i> Área
            </button>
            <button 
              className={`btn btn-sm ${modoVisualizacion === 'barras' ? 'btn-primary' : 'btn-outline-primary'}`}
              onClick={() => setModoVisualizacion('barras')}
            >
              <i className="fas fa-chart-bar me-1"></i> Barras
            </button>
          </div>
          
          <div>
            <div className="form-check form-check-inline">
              <input 
                className="form-check-input" 
                type="checkbox" 
                id="mostrarEtiquetas" 
                checked={mostrarEtiquetas} 
                onChange={() => setMostrarEtiquetas(!mostrarEtiquetas)}
              />
              <label className="form-check-label" htmlFor="mostrarEtiquetas">
                Mostrar etiquetas
              </label>
            </div>
            <div className="form-check form-check-inline">
              <input 
                className="form-check-input" 
                type="checkbox" 
                id="mostrarLineasCiclo" 
                checked={mostrarLineasCiclo} 
                onChange={() => setMostrarLineasCiclo(!mostrarLineasCiclo)}
              />
              <label className="form-check-label" htmlFor="mostrarLineasCiclo">
                Mostrar ciclos
              </label>
            </div>
          </div>
        </div>
        
        {/* Gráfico de curva de producción */}
        <div style={{ width: '100%', height: 400 }}>
          <ResponsiveContainer>
            <LineChart data={puntosCurva} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="dia" 
                label={{ value: 'Días desde siembra', position: 'insideBottomRight', offset: -5 }}
              />
              <YAxis 
                label={{ value: 'Índice (%)', angle: -90, position: 'insideLeft' }}
                domain={[0, 'dataMax']} 
              />
              <Tooltip content={<CustomTooltip />} />
              
              {mostrarEtiquetas && <Legend />}
              
              {/* Líneas de ciclo */}
              {mostrarLineasCiclo && (
                <>
                  <ReferenceLine 
                    x={ciclos.vegetativo} 
                    stroke="green" 
                    strokeDasharray="3 3" 
                    label={{ value: 'Fin Ciclo Vegetativo', angle: 90, position: 'insideTopRight' }} 
                  />
                  <ReferenceLine 
                    x={ciclos.total} 
                    stroke="red" 
                    strokeDasharray="3 3" 
                    label={{ value: 'Fin Ciclo Total', angle: 90, position: 'insideTopRight' }} 
                  />
                </>
              )}
              
              {/* Gráfico según el modo de visualización */}
              {modoVisualizacion === 'linea' && (
                <Line 
                  type="monotone" 
                  dataKey="indice" 
                  stroke="#007bff" 
                  activeDot={{ r: 8 }}
                  name="Índice de Producción"
                />
              )}
              
              {modoVisualizacion === 'area' && (
                <Area 
                  type="monotone" 
                  dataKey="indice" 
                  stroke="#007bff" 
                  fill="#007bff" 
                  fillOpacity={0.3} 
                  name="Índice de Producción"
                />
              )}
              
              {modoVisualizacion === 'barras' && (
                <Bar 
                  dataKey="indice" 
                  fill="#007bff" 
                  name="Índice de Producción"
                />
              )}
            </LineChart>
          </ResponsiveContainer>
        </div>
        
        {/* Tarjetas de resumen */}
        <div className="row mt-4">
          <div className="col-md-4">
            <div className="card bg-light">
              <div className="card-body">
                <h6 className="card-title">Ciclo Vegetativo</h6>
                <p className="card-text h3">{ciclos.vegetativo} días</p>
                <p className="card-text small text-muted">Desde siembra hasta primer corte</p>
              </div>
            </div>
          </div>
          <div className="col-md-4">
            <div className="card bg-light">
              <div className="card-body">
                <h6 className="card-title">Ciclo Productivo</h6>
                <p className="card-text h3">{ciclos.productivo} días</p>
                <p className="card-text small text-muted">Desde primer corte hasta fin de corte</p>
              </div>
            </div>
          </div>
          <div className="col-md-4">
            <div className="card bg-light">
              <div className="card-body">
                <h6 className="card-title">Ciclo Total</h6>
                <p className="card-text h3">{ciclos.total} días</p>
                <p className="card-text small text-muted">Desde siembra hasta fin de corte</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CurvaProduccionInteractiva;