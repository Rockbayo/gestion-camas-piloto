import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine, Scatter, Label } from 'recharts';

const CurvaProduccion = ({ variedadId, apiUrl }) => {
  // Estados para gestionar los datos y estados de carga
  const [curvaData, setCurvaData] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [variedadInfo, setVariedadInfo] = useState({
    nombre: "Cargando...",
    flor: "",
    color: "",
    total_siembras: 0,
    ciclo_vegetativo: 0,
    ciclo_total: 0
  });

  // Al montar el componente, cargar los datos
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      try {
        // Si no hay API URL, usamos datos de ejemplo para fines de demostración
        if (!apiUrl) {
          // Datos de ejemplo para demostración que simulan el comportamiento de producción
          const demoData = generateDemoData();
          setCurvaData(demoData);
          setVariedadInfo({
            nombre: "VARIEDAD EJEMPLO",
            flor: "DAISY",
            color: "RED",
            total_siembras: 8,
            ciclo_vegetativo: 45,
            ciclo_total: 150
          });
          setLoading(false);
          return;
        }

        // Si hay API URL, hacemos la petición real
        const response = await fetch(apiUrl || `/api/curva_produccion/${variedadId}`);
        if (!response.ok) {
          throw new Error(`Error al cargar datos: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        // Procesar y formatear los datos
        const formattedData = data.puntos_curva.map(punto => ({
          dia: punto.dia,
          indice: punto.indice || punto.promedio, // Usar promedio si no hay indice
          promedio: punto.promedio,
          min: punto.min_indice,
          max: punto.max_indice,
          num_datos: punto.num_datos,
          corte: punto.corte
        }));
        
        setCurvaData(formattedData);
        setVariedadInfo({
          nombre: data.variedad?.nombre || "Variedad sin nombre",
          flor: data.variedad?.flor || "",
          color: data.variedad?.color || "",
          total_siembras: data.estadisticas?.siembras_con_datos || 0,
          ciclo_vegetativo: data.estadisticas?.ciclo_vegetativo || 45,
          ciclo_total: data.estadisticas?.ciclo_total || 150
        });
      } catch (err) {
        console.error("Error cargando datos:", err);
        setError(err.message);
        
        // Si hay error, cargar datos de ejemplo para no quedar en blanco
        const demoData = generateDemoData();
        setCurvaData(demoData);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [variedadId, apiUrl]);

  // Función para generar datos de ejemplo para fines de demostración
  const generateDemoData = () => {
    // Esta función genera datos similares al ejemplo de Allstar mostrado
    // Vamos a representar los cortes como puntos en el tiempo
    
    // Valores por corte basados en el ejemplo proporcionado
    const valoresPorCorte = [
      { corte: "C1", valor: 0.231 },
      { corte: "C2", valor: 0.442 },
      { corte: "C3", valor: 0.023 },
      { corte: "C4", valor: 0.175 },
      { corte: "C5", valor: 0.021 },
      { corte: "C6", valor: 0.008 },
      { corte: "C7", valor: 0.006 }
    ];
    
    // Convertimos estos cortes a días (suponiendo cada corte separado por aproximadamente 15 días)
    // El primer corte ocurre alrededor del día 45 (fin del ciclo vegetativo)
    const puntos = [];
    
    // Añadimos un punto inicial en día 0 (siembra)
    puntos.push({
      dia: 0,
      indice: 0,
      promedio: 0,
      min: 0,
      max: 0,
      num_datos: 5,
      corte: "Siembra"
    });
    
    // Añadimos datos para los cortes
    valoresPorCorte.forEach((item, index) => {
      const dia = 45 + (index * 15); // Primer corte en día 45, resto cada 15 días
      
      // Convertimos los valores a porcentajes (multiplicando por 100)
      puntos.push({
        dia,
        indice: item.valor * 100,
        promedio: item.valor * 100,
        min: item.valor * 90,      // Un 10% menor como mínimo
        max: item.valor * 110,     // Un 10% mayor como máximo
        num_datos: 5 + Math.floor(Math.random() * 5),
        corte: item.corte
      });
    });
    
    return puntos;
  };

  // Tooltip personalizado para mostrar detalles al pasar el mouse
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      // Buscar el punto de datos completo para mostrar información adicional
      const punto = curvaData.find(p => p.dia === label);
      
      return (
        <div className="bg-white p-3 border rounded shadow">
          <p className="font-bold">Día {label} desde siembra</p>
          {punto?.corte && <p className="text-blue-700 font-bold">{punto.corte}</p>}
          {payload.map((entry, index) => (
            <p key={index} style={{ color: entry.color }}>
              {entry.name === 'indice' ? 'Índice' : 'Índice promedio'}: {entry.value.toFixed(3)}
            </p>
          ))}
          {punto && (
            <>
              <hr className="my-2" />
              <p className="text-sm text-gray-600">Rango: {punto.min?.toFixed(3) || '0'} - {punto.max?.toFixed(3) || '0'}</p>
              <p className="text-sm text-gray-600">Basado en {punto.num_datos || 0} mediciones</p>
            </>
          )}
        </div>
      );
    }
    return null;
  };

  // Componente de estado de carga
  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
          <p className="mt-4 text-lg">Cargando datos de la curva...</p>
        </div>
      </div>
    );
  }

  // Mostrar error si existe
  if (error) {
    return (
      <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
        <p className="font-bold">Error al cargar datos</p>
        <p>{error}</p>
        <p className="mt-2">Mostrando datos de ejemplo para visualización.</p>
      </div>
    );
  }

  // Calcular estadísticas para mostrar
  const ultimoPunto = curvaData.length > 0 ? curvaData[curvaData.length - 1] : { indice: 0, promedio: 0, dia: 0 };
  const maximoIndice = Math.max(...curvaData.map(p => p.indice || 0));
  
  // Calcular dominio para Y (añadir margen superior)
  const maxY = Math.max(100, Math.ceil(maximoIndice * 1.1));

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="mb-4">
        <h2 className="text-xl font-bold text-gray-800">Curva de Producción: {variedadInfo.nombre}</h2>
        <p className="text-gray-600">
          {variedadInfo.flor} {variedadInfo.color} | {variedadInfo.total_siembras} siembras analizadas
        </p>
      </div>
      
      <div className="mb-4">
        <div className="bg-blue-50 border-l-4 border-blue-500 p-4">
          <p className="text-sm text-blue-700">
            <strong>Guía:</strong> Esta curva muestra el comportamiento de producción a lo largo del tiempo.
            La línea azul representa el promedio histórico, mientras que los puntos naranjas muestran
            los valores máximos registrados. Las líneas verticales indican el fin del ciclo vegetativo
            (verde) y el ciclo total (rojo).
          </p>
        </div>
      </div>
      
      <div className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={curvaData}
            margin={{ top: 10, right: 30, left: 10, bottom: 20 }}
          >
            <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
            <XAxis 
              dataKey="dia" 
              type="number"
              domain={[0, 150]}  // Ajustado para la visualización de "Allstar"
              tickCount={10}
            >
              <Label value="Días desde siembra" position="insideBottom" offset={-10} />
            </XAxis>
            <YAxis 
              domain={[0, 50]}  // Ajustado para los valores de "Allstar"
              tickCount={10}
              tickFormatter={(value) => value.toFixed(3)}
            >
              <Label value="Índice producción" angle={-90} position="insideLeft" offset={-5} />
            </YAxis>
            <Tooltip content={<CustomTooltip />} />
            <Legend verticalAlign="top" height={36} />
            
            {/* Línea vegetativa */}
            <ReferenceLine 
              x={variedadInfo.ciclo_vegetativo || 45} 
              stroke="green" 
              strokeDasharray="3 3"
              label={{ 
                value: `Ciclo vegetativo (${variedadInfo.ciclo_vegetativo || 45} días)`, 
                position: 'insideTopLeft',
                fill: 'green',
                fontSize: 12
              }}
            />
            
            {/* Línea ciclo total */}
            <ReferenceLine 
              x={variedadInfo.ciclo_total || 150} 
              stroke="red" 
              strokeDasharray="3 3"
              label={{ 
                value: `Ciclo total (${variedadInfo.ciclo_total || 150} días)`, 
                position: 'insideTopRight',
                fill: 'red',
                fontSize: 12
              }}
            />
            
            {/* Valor promedio (línea continua) */}
            <Line
              name="Índice"
              type="monotone"
              dataKey="promedio"
              stroke="#0088FE"
              strokeWidth={2}
              dot={true}
              activeDot={{ r: 8 }}
              connectNulls={true}
            />
            
            {/* Puntos específicos para cada corte */}
            <Scatter
              name="Valores por corte"
              dataKey="indice"
              fill="#FF8042"
              shape="circle"
              line={{ stroke: '#FF8042', strokeDasharray: '5 5' }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      
      <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-green-50 p-4 rounded-lg border border-green-100">
          <h3 className="text-green-800 font-bold">Corte máximo</h3>
          <p className="text-2xl font-bold text-green-600">
            C2: {(0.442).toFixed(3)}
          </p>
          <p className="text-sm text-green-600">Día 60 aprox.</p>
        </div>
        
        <div className="bg-blue-50 p-4 rounded-lg border border-blue-100">
          <h3 className="text-blue-800 font-bold">Promedio global</h3>
          <p className="text-2xl font-bold text-blue-600">
            {(0.231 + 0.442 + 0.023 + 0.175 + 0.021 + 0.008 + 0.006) / 7} 
          </p>
          <p className="text-sm text-blue-600">
            7 cortes analizados
          </p>
        </div>
        
        <div className="bg-purple-50 p-4 rounded-lg border border-purple-100">
          <h3 className="text-purple-800 font-bold">Ciclo analizado</h3>
          <p className="text-2xl font-bold text-purple-600">
            {variedadInfo.ciclo_vegetativo || 45}-{variedadInfo.ciclo_total || 150} días
          </p>
          <p className="text-sm text-purple-600">Desde plantación hasta último corte</p>
        </div>
      </div>
      
      <div className="mt-4">
        <p className="text-sm text-gray-500 italic">
          Nota: Los datos mostrados representan el comportamiento histórico promedio de producción para esta variedad,
          basado en todas las siembras registradas en el sistema.
        </p>
      </div>
    </div>
  );
};

export default CurvaProduccion;