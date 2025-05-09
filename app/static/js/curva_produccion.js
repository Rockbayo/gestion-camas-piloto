import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine, Scatter } from 'recharts';

const CurvaProduccion = () => {
  // Estado para almacenar los datos de la curva
  const [curvaData, setCurvaData] = useState([]);
  // Estado para controlar errores
  const [error, setError] = useState(null);
  // Estado para controlar carga
  const [loading, setLoading] = useState(true);
  // Estado para almacenar información de la variedad
  const [variedadInfo, setVariedadInfo] = useState({
    nombre: "Cargando...",
    flor: "",
    color: "",
    total_siembras: 0
  });

  // Datos de ejemplo para desarrollo (esto se reemplazaría con datos reales)
  const dataExample = [
    { dia: 75, indice: 15.5, promedio: 17.2 },
    { dia: 82, indice: 25.3, promedio: 26.8 },
    { dia: 89, indice: 38.7, promedio: 36.5 },
    { dia: 96, indice: 48.2, promedio: 45.1 },
    { dia: 103, indice: 57.9, promedio: 53.7 },
    { dia: 110, indice: 63.5, promedio: 61.4 },
    { dia: 117, indice: 72.8, promedio: 68.9 },
    { dia: 124, indice: 78.1, promedio: 75.3 },
    { dia: 131, indice: 85.6, promedio: 81.2 },
    { dia: 138, indice: 91.2, promedio: 86.5 },
    { dia: 145, indice: 94.7, promedio: 90.8 },
  ];

  useEffect(() => {
    // Simulación de carga de datos
    const loadData = async () => {
      try {
        setLoading(true);
        // En una implementación real, aquí se cargarían los datos desde el backend
        // mediante una llamada fetch o axios

        // Para demostración, usamos un timeout para simular una carga
        setTimeout(() => {
          // Usar datos de ejemplo
          setCurvaData(dataExample);
          
          // Configurar información de variedad (ejemplo)
          setVariedadInfo({
            nombre: "ZIPPO",
            flor: "NOVELTY",
            color: "YELLOW",
            total_siembras: 12
          });
          
          setLoading(false);
        }, 1500);
      } catch (err) {
        setError("Error al cargar los datos de la curva de producción");
        setLoading(false);
      }
    };

    loadData();
  }, []);

  // Función para personalizar el tooltip
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white p-3 border rounded shadow">
          <p className="font-bold">Día {label} desde siembra</p>
          {payload.map((entry, index) => (
            <p key={index} style={{ color: entry.color }}>
              {entry.name === 'indice' ? 'Índice' : 'Promedio'}: {entry.value.toFixed(2)}%
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

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

  if (error) {
    return (
      <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
        <p>{error}</p>
        <p>Por favor, intente nuevamente o contacte al administrador.</p>
      </div>
    );
  }

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
            <strong>Ayuda:</strong> Esta curva muestra el índice de producción (% de tallos sobre plantas sembradas) 
            a lo largo del tiempo. La línea azul representa los datos históricos promedio, mientras que los puntos 
            representan los índices individuales.
          </p>
        </div>
      </div>
      
      <div className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={curvaData}
            margin={{ top: 5, right: 20, left: 10, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis 
              dataKey="dia" 
              label={{ value: 'Días desde siembra', position: 'insideBottomRight', offset: -10 }} 
            />
            <YAxis 
              label={{ value: 'Índice producción (%)', angle: -90, position: 'insideLeft' }}
              domain={[0, 100]} 
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend />
            <ReferenceLine y={75} stroke="green" strokeDasharray="3 3" label="Objetivo 75%" />
            <Line 
              type="monotone" 
              dataKey="promedio" 
              stroke="#0088FE" 
              name="Promedio histórico" 
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 8 }}
            />
            <Scatter 
              dataKey="indice" 
              fill="#FF8042" 
              name="Índice actual" 
              shape="circle"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      
      <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-green-50 p-4 rounded-lg border border-green-100">
          <h3 className="text-green-800 font-bold">Estado actual</h3>
          <p className="text-2xl font-bold text-green-600">
            {curvaData.length > 0 ? `${curvaData[curvaData.length - 1].indice}%` : 'N/A'}
          </p>
          <p className="text-sm text-green-600">Día {curvaData.length > 0 ? curvaData[curvaData.length - 1].dia : 'N/A'}</p>
        </div>
        
        <div className="bg-blue-50 p-4 rounded-lg border border-blue-100">
          <h3 className="text-blue-800 font-bold">Promedio esperado</h3>
          <p className="text-2xl font-bold text-blue-600">
            {curvaData.length > 0 ? `${curvaData[curvaData.length - 1].promedio}%` : 'N/A'}
          </p>
          <p className="text-sm text-blue-600">
            {curvaData.length > 0 ? 
              (curvaData[curvaData.length - 1].indice > curvaData[curvaData.length - 1].promedio ? 
                'Por encima del promedio' : 'Por debajo del promedio') 
              : 'N/A'}
          </p>
        </div>
        
        <div className="bg-purple-50 p-4 rounded-lg border border-purple-100">
          <h3 className="text-purple-800 font-bold">Primer corte promedio</h3>
          <p className="text-2xl font-bold text-purple-600">
            {curvaData.length > 0 ? `${curvaData[0].dia} días` : 'N/A'}
          </p>
          <p className="text-sm text-purple-600">Índice inicial: {curvaData.length > 0 ? `${curvaData[0].indice}%` : 'N/A'}</p>
        </div>
      </div>
      
      <div className="mt-4">
        <p className="text-sm text-gray-500 italic">
          Nota: Los datos mostrados son un promedio histórico basado en todas las siembras de esta variedad. 
          Los resultados individuales pueden variar según condiciones específicas de cultivo.
        </p>
      </div>
    </div>
  );
};

export default CurvaProduccion;