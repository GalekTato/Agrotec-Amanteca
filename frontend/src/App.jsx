import React, { useEffect, useMemo, useState } from 'react'
import {
  ArrowUpRight,
  Download,
  Moon,
  RefreshCw,
  Search,
  Sun,
} from 'lucide-react'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import ParcelMap, { getYieldColor } from './components/ParcelMap.jsx'

const API_BASE = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')

const TEAM_MEMBERS = [
  'Gael Askary Razo Montañez',
  'Limhi Gerson López Momox',
  'Karla Yaneth Cruz Sandoval',
  'Arturo Huerta Maldonado',
  'Juan Enrique Gutierrez Hernández',
]

const MODEL_ARCHITECTURES_INFO = [
  {
    name: 'Ensemble Agrotec (Voting Heterogéneo + Smart-Pearson + IDW Espacial)',
    badge: 'MODELO GANADOR SELECCIONADO',
    isWinner: true,
    metrics:
      '5-Fold MAE: 0.3576 ± 0.0662 t/ha · 5-Fold RMSE: 0.4984 ± 0.1084 t/ha · 5×5 RMSE: 0.5076 ± 0.1183 t/ha · R²: 0.6098',
    description:
      'Combina cuatro familias algorítmicas complementarias (Extra Trees 40% + Random Forest Podado 25% + SVR Kernel RBF 20% + Gradient Boosting 15%) entrenadas exactamente sobre los 23 predictores seleccionados por el transformador Leak-Free Smart-Pearson (|r| < 0.88, top_k=22) más el potencial microclimático vecinal IDW (k=7).',
    whySelected:
      'Fue seleccionado por obtener el menor error tanto en validación cruzada 5-Fold (RMSE 0.4984 t/ha) como en validación cruzada repetida 5×5 (25 evaluaciones independientes, RMSE 0.5076 t/ha), logrando que el 73.2% de las parcelas tengan un error Out-Of-Fold menor o igual a ±0.50 t/ha.',
  },
  {
    name: 'Extra Trees Regressor (Smart-Pearson + IDW)',
    badge: 'MEJOR MODELO INDIVIDUAL EN 5×5 CV',
    isWinner: false,
    metrics:
      '5-Fold MAE: 0.3682 ± 0.0615 t/ha · 5-Fold RMSE: 0.5077 ± 0.0950 t/ha · 5×5 RMSE: 0.5124 ± 0.1110 t/ha · R²: 0.5947',
    description:
      'Ensamble de árboles de decisión extremadamente aleatorizados que introduce cortes aleatorios en cada nodo, reduciendo la varianza en datasets tabulares de tamaño moderado (N = 138 parcelas de entrenamiento).',
    whySelected:
      'Aporta el 40% del peso dentro del ensamble ganador gracias a su estabilidad frente al ruido en lecturas satelitales mensuales.',
  },
  {
    name: 'Stacking Meta-Ensemble (Meta-Regresor RidgeCV L2)',
    badge: 'ALTA PRECISIÓN EN 5-FOLD CV',
    isWinner: false,
    metrics:
      '5-Fold MAE: 0.3606 ± 0.0661 t/ha · 5-Fold RMSE: 0.5006 ± 0.1068 t/ha · 5×5 RMSE: 0.5186 ± 0.1175 t/ha · R²: 0.6095',
    description:
      'Arquitectura jerárquica de dos niveles donde un regresor lineal penalizado (RidgeCV) aprende los pesos sobre las predicciones Out-Of-Fold generadas por los estimadores base.',
    whySelected:
      'Obtuvo el segundo menor RMSE en 5-Fold CV (0.5006 t/ha), pero presenta mayor varianza en 5×5 Repeated CV y mayor costo computacional por el entrenamiento anidado.',
  },
  {
    name: 'Random Forest Regressor (Baseline 39 Variables Base)',
    badge: 'PUNTO DE REFERENCIA (BASELINE)',
    isWinner: false,
    metrics:
      '5-Fold MAE: 0.3742 ± 0.0592 t/ha · 5-Fold RMSE: 0.5139 ± 0.0923 t/ha · 5×5 RMSE: 0.5175 ± 0.1107 t/ha · R²: 0.5859',
    description:
      'Bosque aleatorio clásico entrenado mediante Bagging (muestreo bootstrap con reemplazo) sobre las 39 variables del filtro secuencial original.',
    whySelected:
      'Sirvió como línea base auditable para medir la ganancia neta de precisión (-4.4% en MAE CV y -3.0% en RMSE CV) alcanzada por la selección Smart-Pearson + IDW.',
  },
  {
    name: 'Support Vector Regressor (SVR Kernel RBF + RobustScaler)',
    badge: 'REGULARIZACIÓN GEOMÉTRICA',
    isWinner: false,
    metrics:
      '5-Fold MAE: 0.3682 ± 0.0780 t/ha · 5-Fold RMSE: 0.5210 ± 0.1175 t/ha · 5×5 RMSE: 0.5310 ± 0.1183 t/ha · R²: 0.5729',
    description:
      'Proyecta los predictores escalados por rango intercuartílico (RobustScaler) mediante un kernel gaussiano RBF, construyendo un tubo de tolerancia ε-insensible.',
    whySelected:
      'Integra el 20% del peso del ensamble ganador, suavizando las predicciones escalonadas típicas de los árboles de decisión.',
  },
  {
    name: 'Gradient Boosting Regressor (GBR) y LightGBM',
    badge: 'BOOSTING SECUENCIAL',
    isWinner: false,
    metrics:
      'GBR 5-Fold RMSE: 0.5095 ± 0.0922 t/ha (5×5 RMSE: 0.5152) · LightGBM 5-Fold RMSE: 0.5494 ± 0.0919 t/ha',
    description:
      'Entrenan árboles secuenciales de baja profundidad donde cada árbol corrige los residuos pseudo-gradiente de la iteración previa.',
    whySelected:
      'GBR se integró con 15% de peso en el ensamble final para capturar gradientes térmicos finos; LightGBM en solitario tiende a sobreajustar cuando N = 138.',
  },
  {
    name: 'RidgeCV Lineal y Referencia (Predecir la Media)',
    badge: 'CONTROLES PARAMÉTRICO Y NULO',
    isWinner: false,
    metrics:
      'RidgeCV 5-Fold RMSE: 0.5180 ± 0.0846 t/ha (R²: 0.5802) · Dummy Media 5-Fold RMSE: 0.8545 ± 0.0926 t/ha (R²: -0.0870)',
    description:
      'RidgeCV aplica regresión lineal con penalización L2; el estimador Dummy predice siempre la media del pliegue de entrenamiento (3.955 t/ha) como piso estadístico.',
    whySelected:
      'Demuestran que el ensamble reduce el error absoluto medio en -52.9% frente a predecir la media regional (0.3576 vs. 0.7585 t/ha) y supera el techo lineal de RidgeCV.',
  },
]

function lookupGridDelta(deltaMap, val, isFloatKey = false) {
  if (!deltaMap) return 0
  const key = isFloatKey ? Number(val).toFixed(1) : String(Math.round(Number(val)))
  if (Object.prototype.hasOwnProperty.call(deltaMap, key)) {
    return Number(deltaMap[key])
  }
  const entries = Object.entries(deltaMap)
    .map(([k, v]) => [Number(k), Number(v)])
    .sort((a, b) => a[0] - b[0])
  if (!entries.length) return 0
  if (val <= entries[0][0]) return entries[0][1]
  if (val >= entries[entries.length - 1][0]) return entries[entries.length - 1][1]
  for (let i = 0; i < entries.length - 1; i += 1) {
    const [x0, y0] = entries[i]
    const [x1, y1] = entries[i + 1]
    if (val >= x0 && val <= x1) {
      const t = x1 === x0 ? 0 : (val - x0) / (x1 - x0)
      return y0 + t * (y1 - y0)
    }
  }
  return 0
}

export default function App() {
  const [summary, setSummary] = useState(null)
  const [geojson, setGeojson] = useState(null)
  const [sensitivity, setSensitivity] = useState(null)
  const [loading, setLoading] = useState(true)
  const [apiMode, setApiMode] = useState('checking')
  const [activeTab, setActiveTab] = useState('cockpit')
  const [filterConjunto, setFilterConjunto] = useState('TODAS')
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedId, setSelectedId] = useState('AGC_002')
  const [showLogoModal, setShowLogoModal] = useState(false)
  const [darkMode, setDarkMode] = useState(() => {
    try {
      return localStorage.getItem('agrotec_theme') === 'dark'
    } catch {
      return false
    }
  })

  useEffect(() => {
    const root = document.documentElement
    if (darkMode) {
      root.classList.add('dark')
    } else {
      root.classList.remove('dark')
    }
    try {
      localStorage.setItem('agrotec_theme', darkMode ? 'dark' : 'light')
    } catch {
      // ignore storage errors
    }
  }, [darkMode])

  // Parámetros del Simulador Agronómico
  const [ndviDelta, setNdviDelta] = useState(0)
  const [precDelta, setPrecDelta] = useState(0)
  const [tmaxDelta, setTmaxDelta] = useState(0)
  const [simResult, setSimResult] = useState(null)
  const [simLoading, setSimLoading] = useState(false)

  useEffect(() => {
    let mounted = true
    async function fetchAllData() {
      setLoading(true)
      try {
        const [sumRes, geoRes, simRes] = await Promise.all([
          fetch(`${API_BASE}/api/summary`),
          fetch(`${API_BASE}/api/parcelas`),
          fetch(`${API_BASE}/api/sensibilidad`),
        ])
        if (sumRes.ok && geoRes.ok && simRes.ok) {
          const [sumJson, geoJson, simJson] = await Promise.all([
            sumRes.json(),
            geoRes.json(),
            simRes.json(),
          ])
          if (mounted) {
            setSummary(sumJson)
            setGeojson(geoJson)
            setSensitivity(simJson)
            setApiMode('cloud')
            setLoading(false)
          }
          return
        }
      } catch {
        // Fallback automático a los artefactos estáticos precalculados del modelo
      }

      try {
        const [sumStatic, geoStatic, simStatic] = await Promise.all([
          fetch('./data/metrics_summary.json').then((r) => r.json()),
          fetch('./data/parcelas_197_dashboard.geojson').then((r) => r.json()),
          fetch('./data/sensibilidad_simulador.json').then((r) => r.json()),
        ])
        if (mounted) {
          setSummary(sumStatic)
          setGeojson(geoStatic)
          setSensitivity(simStatic)
          setApiMode('edge')
          setLoading(false)
        }
      } catch (err) {
        console.error('Error cargando datos:', err)
        if (mounted) setLoading(false)
      }
    }
    fetchAllData()
    return () => {
      mounted = false
    }
  }, [])

  const allParcels = useMemo(() => {
    if (!geojson || !geojson.features) return []
    return geojson.features.map((f) => f.properties || {})
  }, [geojson])

  const filteredParcels = useMemo(() => {
    return allParcels.filter((p) => {
      const matchConjunto =
        filterConjunto === 'TODAS' || p.CONJUNTO === filterConjunto
      const matchSearch =
        !searchQuery.trim() ||
        String(p.ID_POLIGONO || '')
          .toLowerCase()
          .includes(searchQuery.trim().toLowerCase())
      return matchConjunto && matchSearch
    })
  }, [allParcels, filterConjunto, searchQuery])

  const selectedParcel = useMemo(() => {
    if (!allParcels.length) return null
    return (
      allParcels.find((p) => p.ID_POLIGONO === selectedId) ||
      filteredParcels[0] ||
      allParcels[0]
    )
  }, [allParcels, filteredParcels, selectedId])

  // Simulador Agronómico 100% respaldado por la superficie de respuesta precalculada del modelo real
  useEffect(() => {
    if (!selectedParcel) return
    let cancelled = false

    const parcelId = selectedParcel.ID_POLIGONO
    const parcelSim = sensitivity?.parcels?.[parcelId]
    const baseYield = Number(
      parcelSim?.base_yield_t_ha ??
        selectedParcel.RENDIMIENTO_PREDICHO_T_HA ??
        selectedParcel.RENDIMIENTO_FINAL_T_HA ??
        3.95
    )
    const areaHa = Number(selectedParcel.AREA_HA || 1.0)
    const halfWidth80 = Number(selectedParcel.INCERTIDUMBRE_T_HA || 0.564)

    if (ndviDelta === 0 && precDelta === 0 && tmaxDelta === 0) {
      setSimLoading(false)
      setSimResult({
        rendimiento_base_modelo_t_ha: baseYield,
        rendimiento_simulado_t_ha: baseYield,
        intervalo_80_inf_t_ha: Math.max(1.0, +(baseYield - halfWidth80).toFixed(4)),
        intervalo_80_sup_t_ha: +(baseYield + halfWidth80).toFixed(4),
        delta_t_ha: 0,
        delta_pct: 0,
        desglose_modelo_t_ha: {
          efecto_ndvi_t_ha: 0,
          efecto_precipitacion_t_ha: 0,
          efecto_temperatura_t_ha: 0,
        },
        produccion_base_ton: +(baseYield * areaHa).toFixed(2),
        produccion_simulada_ton: +(baseYield * areaHa).toFixed(2),
      })
      return
    }

    const computePrecomputedModelResponse = () => {
      const dNdvi = lookupGridDelta(parcelSim?.ndvi_deltas, ndviDelta, false)
      const dPrec = lookupGridDelta(parcelSim?.prec_deltas, precDelta, false)
      const dTmax = lookupGridDelta(parcelSim?.tmax_deltas, tmaxDelta, true)
      const rawSim = Math.max(1.0, Math.min(6.5, baseYield + dNdvi + dPrec + dTmax))
      const simYield = +rawSim.toFixed(4)
      const delta = +(simYield - baseYield).toFixed(4)
      const deltaPct = baseYield > 0 ? +((delta / baseYield) * 100).toFixed(2) : 0
      return {
        rendimiento_base_modelo_t_ha: baseYield,
        rendimiento_simulado_t_ha: simYield,
        intervalo_80_inf_t_ha: Math.max(1.0, +(simYield - halfWidth80).toFixed(4)),
        intervalo_80_sup_t_ha: +(simYield + halfWidth80).toFixed(4),
        delta_t_ha: delta,
        delta_pct: deltaPct,
        desglose_modelo_t_ha: {
          efecto_ndvi_t_ha: +dNdvi.toFixed(4),
          efecto_precipitacion_t_ha: +dPrec.toFixed(4),
          efecto_temperatura_t_ha: +dTmax.toFixed(4),
        },
        produccion_base_ton: +(baseYield * areaHa).toFixed(2),
        produccion_simulada_ton: +(simYield * areaHa).toFixed(2),
      }
    }

    setSimResult(computePrecomputedModelResponse())

    async function syncBackendSimulation() {
      if (apiMode !== 'cloud') {
        setSimLoading(false)
        return
      }
      setSimLoading(true)
      try {
        const res = await fetch(`${API_BASE}/api/simular`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            id_poligono: parcelId,
            ndvi_delta_pct: ndviDelta,
            prec_delta_pct: precDelta,
            tmax_delta_c: tmaxDelta,
          }),
        })
        if (res.ok) {
          const data = await res.json()
          if (!cancelled && data && typeof data.rendimiento_simulado_t_ha === 'number') {
            setSimResult(data)
          }
        }
      } catch {
        // Conserva la predicción exacta precalculada del modelo en sensibilidad_simulador.json
      } finally {
        if (!cancelled) {
          setSimLoading(false)
        }
      }
    }

    syncBackendSimulation()
    return () => {
      cancelled = true
    }
  }, [selectedParcel, sensitivity, ndviDelta, precDelta, tmaxDelta, apiMode])

  const hasActiveSimulation = ndviDelta !== 0 || precDelta !== 0 || tmaxDelta !== 0

  // La curva fenológica de NDVI refleja directamente el escalamiento porcentual del slider de NDVI
  const ndviChartData = useMemo(() => {
    if (!selectedParcel || !summary?.ndvi_benchmarks) return []
    return summary.ndvi_benchmarks.map((b) => {
      const baseVal = Number(selectedParcel[b.feature] || 0)
      const simVal =
        ndviDelta !== 0
          ? Math.min(0.95, Math.max(0.05, +(baseVal * (1 + ndviDelta / 100)).toFixed(4)))
          : baseVal

      return {
        month: b.month_name,
        parcela: +baseVal.toFixed(3),
        simulado: +simVal.toFixed(3),
        altoRendimiento: +Number(b.mean_high_yield).toFixed(3),
        bajoRendimiento: +Number(b.mean_low_yield).toFixed(3),
      }
    })
  }, [selectedParcel, summary, ndviDelta])

  const localDrivers = useMemo(() => {
    if (!selectedParcel?.top_drivers) return []
    try {
      return typeof selectedParcel.top_drivers === 'string'
        ? JSON.parse(selectedParcel.top_drivers)
        : selectedParcel.top_drivers
    } catch {
      return []
    }
  }, [selectedParcel])

  const handleDownloadCsv = () => {
    const predRows = allParcels.filter((p) => p.CONJUNTO === 'PREDICCION')
    if (!predRows.length) return
    const headers = [
      'ID_POLIGONO',
      'AREA_HA',
      'RENDIMIENTO_T_HA',
      'INCERTIDUMBRE_T_HA',
      'INTERVALO_80_INF_T_HA',
      'INTERVALO_80_SUP_T_HA',
      'PRODUCCION_ESTIMADA_TON',
      'RENDIMIENTO_BASELINE_RF_T_HA',
    ]
    const csvLines = [
      headers.join(','),
      ...predRows.map((r) =>
        [
          r.ID_POLIGONO,
          Number(r.AREA_HA).toFixed(2),
          Number(r.RENDIMIENTO_PREDICHO_T_HA ?? r.RENDIMIENTO_FINAL_T_HA).toFixed(4),
          Number(r.INCERTIDUMBRE_T_HA ?? 0.564).toFixed(4),
          Number(r.INTERVALO_80_INF_T_HA ?? 3.2).toFixed(4),
          Number(r.INTERVALO_80_SUP_T_HA ?? 4.5).toFixed(4),
          Number(r.PRODUCCION_ESTIMADA_TON).toFixed(2),
          Number(r.RENDIMIENTO_BASELINE_RF_T_HA ?? r.RENDIMIENTO_FINAL_T_HA).toFixed(4),
        ].join(',')
      ),
    ]
    const blob = new Blob([csvLines.join('\n')], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', 'Predicciones_59_Parcelas_Agrotec_Amanteca_FIRA2026.csv')
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  const chartInk = darkMode ? '#F4F4F5' : '#111111'
  const chartGrid = darkMode ? '#27272A' : '#D4D4D8'
  const chartTooltipBg = darkMode ? '#121418' : '#FFFFFF'
  const chartTooltipBorder = darkMode ? '#3F3F46' : '#111111'

  if (loading) {
    return (
      <div className="min-h-screen bg-[var(--surface-bg)] text-[var(--ink-primary)] flex flex-col items-center justify-center p-6">
        <div className="border border-[var(--rule-strong)] bg-[var(--surface-panel)] p-8 max-w-md w-full text-left">
          <div className="text-xs font-bold uppercase tracking-widest text-[#FF4F00] mb-2">
            FIRA 2026 · Agrotec-Amanteca
          </div>
          <h1 className="text-xl font-black tracking-tight">
            Cargando Cartografía y Modelo Predictivo Auditado
          </h1>
          <p className="text-xs text-[var(--ink-secondary)] mt-2">
            Sincronizando 197 polígonos agrícolas (138 entrenamiento, 59 predicción ciega) y superficie de respuesta del modelo.
          </p>
        </div>
      </div>
    )
  }

  const stats = summary?.dataset_stats || {}
  const eff = summary?.efficiency_metrics || {}
  const baseMetrics = summary?.baseline_metrics || {}
  const envVer = summary?.environment_versions || {}
  const bestModelMetric = summary?.models_comparison?.[0] || {
    model: 'Ensemble Agrotec (Smart-Pearson + IDW)',
    mae_cv: 0.3576,
    mae_std: 0.0662,
    rmse_cv: 0.4984,
    rmse_std: 0.1084,
    r2_cv: 0.6098,
    rmse_repeated_cv: 0.5076,
    rmse_repeated_std: 0.1183,
  }

  const maeGainPct =
    baseMetrics.mae_cv && bestModelMetric.mae_cv
      ? (((baseMetrics.mae_cv - bestModelMetric.mae_cv) / baseMetrics.mae_cv) * 100).toFixed(1)
      : '4.4'
  const r2GainPts =
    baseMetrics.r2_cv && bestModelMetric.r2_cv
      ? ((bestModelMetric.r2_cv - baseMetrics.r2_cv) * 100).toFixed(2)
      : '2.39'

  const techStackDynamic = [
    {
      category: 'Ciencia de Datos y Machine Learning',
      items: `Python ${envVer.python || '3.14'} · Scikit-Learn ${envVer.scikit_learn || '1.9'} · LightGBM ${envVer.lightgbm || '4.7'} · SciPy Spatial (IDW k=7) · Joblib ${envVer.joblib || '1.6'}`,
      detail:
        'Pipeline reproducible con validación cruzada 5-Fold y 5×5 Repeated CV (25 corridas), transformador LeakFreeSmartPearsonIDW (|r| < 0.88, 23 variables exactas) e intervalos conformales al 80%.',
    },
    {
      category: 'Ingeniería Geoespacial y Clima',
      items: `GeoPandas ${envVer.geopandas || '1.2'} · Shapely · Rasterio (all_touched=True) · CHIRPS Rasters · INEGI CEM4 · Apache Parquet`,
      detail:
        'Extracción zonal multianual de precipitación y temperatura (2022–2025), elevación/pendiente a 120 m y reconstrucción fenológica mensual de NDVI y EVI en EPSG:4326 / UTM 14N.',
    },
    {
      category: 'Backend & Motor de Inferencia en Tiempo Real',
      items: 'FastAPI · Pydantic V2 · Uvicorn ASGI · Lifespan Memory Cache · Pytest Suite',
      detail:
        'API RESTful sin DeprecationWarnings con módulo compartido agro_core.py, superficie de sensibilidad precalculada y paridad matemática 100% entre cliente y servidor.',
    },
    {
      category: 'Frontend Cartográfico & Diseño Editorial',
      items: 'React 18 · Vite 6 · Tailwind CSS · LeafletJS · Esri ArcGIS Online · Recharts',
      detail:
        'Interfaz responsive multi-dispositivo bajo retícula técnica Swiss (Modo Claro) / Industrial (Modo Oscuro) con 3 capas satelitales y topográficas libres de API Key.',
    },
  ]

  return (
    <div className="min-h-screen bg-[var(--surface-bg)] text-[var(--ink-primary)] flex flex-col pb-16 md:pb-0">
      {/* MASTHEAD EDITORIAL SWISS (Z-INDEX 1000 PARA NUNCA SER CUBIERTO POR CONTROLES DEL MAPA) */}
      <header className="sticky top-0 z-[1000] bg-[var(--surface-panel)] border-b border-[var(--rule-strong)]">
        <div className="max-w-[1600px] mx-auto grid grid-cols-12 items-stretch">
          {/* Bloque Marca e Identidad */}
          <div className="col-span-6 sm:col-span-5 lg:col-span-3 px-3 sm:px-5 py-3 border-r border-[var(--rule-hairline)] flex items-center gap-3">
            <button
              type="button"
              onClick={() => setShowLogoModal(true)}
              className="w-10 h-10 border border-[var(--rule-strong)] bg-[#111111] flex items-center justify-center shrink-0 cursor-pointer hover:border-[#FF4F00] transition"
              title="Ver Emblema Oficial Agrotec-Amanteca"
            >
              <img
                src="./logo_agrotec_amanteca.svg"
                alt="Agrotec-Amanteca"
                className="w-8 h-8"
              />
            </button>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-black text-sm sm:text-base tracking-tight uppercase truncate">
                  Agrotec-Amanteca
                </span>
                <span className="hidden sm:inline-block bg-[#FF4F00] text-white text-[10px] font-bold px-1.5 py-0.5 uppercase">
                  FIRA 2026
                </span>
              </div>
              <p className="text-[11px] text-[var(--ink-secondary)] truncate">
                Predicción de Rendimiento de Cebada (t/ha) · 197 Parcelas
              </p>
            </div>
          </div>

          {/* Navegación Estructural Desktop */}
          <nav className="hidden lg:flex lg:col-span-5 items-stretch divide-x divide-[var(--rule-hairline)] border-r border-[var(--rule-hairline)]">
            {[
              { id: 'cockpit', num: '01', label: 'Cartografía y Diagnóstico' },
              { id: 'models', num: '02', label: 'Modelos ML y Explicación' },
              { id: 'predictions', num: '03', label: '59 Predicciones Oficiales' },
              { id: 'deploy', num: '04', label: 'Eficiencia y Tecnologías' },
            ].map((item) => {
              const active = activeTab === item.id
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setActiveTab(item.id)}
                  className={`flex-1 px-3 py-2 text-left transition cursor-pointer flex flex-col justify-between ${
                    active
                      ? 'bg-[var(--invert-bg)] text-[var(--invert-ink)]'
                      : 'bg-[var(--surface-panel)] text-[var(--ink-primary)] hover:bg-[var(--surface-subtle)]'
                  }`}
                >
                  <span
                    className={`text-[10px] font-bold tabular-nums ${
                      active ? 'text-[#FF4F00]' : 'text-[var(--ink-muted)]'
                    }`}
                  >
                    {item.num}
                  </span>
                  <span className="text-xs font-bold leading-tight">{item.label}</span>
                </button>
              )
            })}
          </nav>

          {/* Toggle Claro/Oscuro + Exportación CSV */}
          <div className="col-span-6 sm:col-span-7 lg:col-span-4 px-3 sm:px-5 py-2.5 flex items-center justify-end gap-2.5">
            <button
              type="button"
              onClick={() => setDarkMode((prev) => !prev)}
              className="inline-flex items-center gap-1.5 bg-[var(--surface-subtle)] hover:bg-[#FF4F00] hover:text-white text-[var(--ink-primary)] font-bold text-xs px-3 py-2 border border-[var(--rule-strong)] transition cursor-pointer"
              title="Alternar Modo Claro (Swiss) / Modo Oscuro (Industrial)"
            >
              {darkMode ? <Sun className="w-3.5 h-3.5" /> : <Moon className="w-3.5 h-3.5" />}
              <span className="hidden sm:inline">{darkMode ? 'Modo Claro' : 'Modo Oscuro'}</span>
            </button>

            <button
              type="button"
              onClick={handleDownloadCsv}
              className="inline-flex items-center gap-1.5 bg-[#FF4F00] hover:opacity-90 text-white font-bold text-xs px-3 sm:px-3.5 py-2 border border-[var(--rule-strong)] transition cursor-pointer"
            >
              <Download className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Exportar 59 Predicciones (.CSV)</span>
              <span className="sm:hidden">CSV (59)</span>
            </button>
          </div>
        </div>

        {/* Barra de Navegación para Tablets (md) */}
        <div className="hidden md:grid lg:hidden grid-cols-4 divide-x divide-[var(--rule-hairline)] border-t border-[var(--rule-hairline)] bg-[var(--surface-panel)]">
          {[
            { id: 'cockpit', num: '01', label: 'Cartografía y Simulador' },
            { id: 'models', num: '02', label: 'Modelos ML y Explicación' },
            { id: 'predictions', num: '03', label: 'Catálogo 59 Predicciones' },
            { id: 'deploy', num: '04', label: 'Eficiencia y Tecnologías' },
          ].map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setActiveTab(item.id)}
              className={`px-3 py-2 text-left text-xs font-bold ${
                activeTab === item.id
                  ? 'bg-[var(--invert-bg)] text-[var(--invert-ink)]'
                  : 'text-[var(--ink-primary)]'
              }`}
            >
              <span className="text-[#FF4F00] mr-1.5 tabular-nums">{item.num}</span>
              {item.label}
            </button>
          ))}
        </div>
      </header>

      {/* CUERPO EDITORIAL EN RETÍCULA SWISS */}
      <main className="flex-1 max-w-[1600px] w-full mx-auto px-3 sm:px-6 pt-5 pb-10 space-y-5">
        {/* BANDA DE NUMERALES DEMOSTRATIVOS DE PRECISIÓN Y EFICIENCIA */}
        <section className="grid grid-cols-2 lg:grid-cols-4 bg-[var(--surface-panel)] border border-[var(--rule-strong)] divide-y sm:divide-y-0 divide-x divide-[var(--rule-hairline)]">
          <div className="p-4 sm:p-5 flex flex-col justify-between">
            <div className="flex items-baseline justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--ink-secondary)]">
                01 · Rendimiento Medio Predicho
              </span>
              <span className="text-[11px] font-bold text-[#FF4F00] tabular-nums">59 Ciegas</span>
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="folio-numeral text-3xl sm:text-4xl lg:text-[42px] text-[var(--ink-primary)]">
                {Number(stats.pred_yield_mean || 3.948).toFixed(2)}
              </span>
              <span className="text-xs font-bold uppercase text-[var(--ink-secondary)]">t/ha</span>
            </div>
            <p className="text-xs text-[var(--ink-secondary)] mt-2 tabular-nums border-t border-[var(--rule-hairline)] pt-1.5">
              Media Entrenamiento (138): <b className="text-[var(--ink-primary)]">{Number(stats.train_yield_mean || 3.955).toFixed(2)} t/ha</b> · Rango: {Number(stats.pred_yield_min || 2.71).toFixed(2)}–{Number(stats.pred_yield_max || 5.0).toFixed(2)}
            </p>
          </div>

          <div className="p-4 sm:p-5 flex flex-col justify-between">
            <div className="flex items-baseline justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--ink-secondary)]">
                02 · Precisión Validación (5-Fold CV)
              </span>
              <span className="text-[11px] font-bold text-[#16A34A] tabular-nums">
                R² {Number(bestModelMetric.r2_cv).toFixed(4)}
              </span>
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="folio-numeral text-3xl sm:text-4xl lg:text-[42px] text-[var(--ink-primary)]">
                {Number(bestModelMetric.mae_cv).toFixed(4)}
              </span>
              <span className="text-xs font-bold uppercase text-[var(--ink-secondary)]">
                ±{Number(bestModelMetric.mae_std || 0.066).toFixed(3)} MAE
              </span>
            </div>
            <p className="text-xs text-[var(--ink-secondary)] mt-2 tabular-nums border-t border-[var(--rule-hairline)] pt-1.5">
              RMSE 5F: <b className="text-[var(--ink-primary)]">{Number(bestModelMetric.rmse_cv).toFixed(4)}</b> · RMSE 5×5: <b className="text-[var(--ink-primary)]">{Number(bestModelMetric.rmse_repeated_cv || 0.5076).toFixed(4)} t/ha</b>
            </p>
          </div>

          <div className="p-4 sm:p-5 flex flex-col justify-between">
            <div className="flex items-baseline justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--ink-secondary)]">
                03 · Volumen Productivo Estimado
              </span>
              <span className="text-[11px] font-bold text-[var(--ink-secondary)] tabular-nums">
                {Number(stats.total_area_ha || 1301.05).toFixed(1)} ha
              </span>
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="folio-numeral text-3xl sm:text-4xl lg:text-[42px] text-[var(--ink-primary)]">
                {Number(stats.total_production_ton || 5066.44).toLocaleString('es-MX', {
                  maximumFractionDigits: 0,
                })}
              </span>
              <span className="text-xs font-bold uppercase text-[var(--ink-secondary)]">toneladas</span>
            </div>
            <p className="text-xs text-[var(--ink-secondary)] mt-2 tabular-nums border-t border-[var(--rule-hairline)] pt-1.5">
              Cosecha en 59 parcelas de prueba: <b className="text-[var(--ink-primary)]">{Number(stats.pred_production_ton || 1542.68).toFixed(1)} t</b> ({Number(stats.pred_area_ha || 393.57).toFixed(1)} ha)
            </p>
          </div>

          <div className="p-4 sm:p-5 flex flex-col justify-between">
            <div className="flex items-baseline justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--ink-secondary)]">
                04 · Pureza de Datos y Cobertura 80%
              </span>
              <span className="text-[11px] font-bold text-[#FF4F00] tabular-nums">
                {Number(eff.inference_197_ms || 91.4).toFixed(1)} ms
              </span>
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="folio-numeral text-3xl sm:text-4xl lg:text-[42px] text-[var(--ink-primary)]">
                175→{stats.total_features_selected || 23}
              </span>
              <span className="text-xs font-bold uppercase text-[var(--ink-secondary)]">predictores</span>
            </div>
            <p className="text-xs text-[var(--ink-secondary)] mt-2 tabular-nums border-t border-[var(--rule-hairline)] pt-1.5">
              Smart-Pearson <b className="text-[var(--ink-primary)]">|r| &lt; 0.88</b> · Cobertura Int. 80%: <b className="text-[#16A34A]">{eff.conformal_80_coverage_oof_pct || 81.2}%</b>
            </p>
          </div>
        </section>

        {/* SECCIÓN 01: CARTOGRAFÍA Y DIAGNÓSTICO POR PARCELA */}
        {activeTab === 'cockpit' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 border border-[var(--rule-strong)] bg-[var(--surface-panel)] divide-y lg:divide-y-0 lg:divide-x divide-[var(--rule-strong)]">
            {/* IZQUIERDA (7 COLUMNAS): VISOR CARTOGRÁFICO DE LAS 197 PARCELAS */}
            <div className="lg:col-span-7 flex flex-col min-w-0">
              {/* Barra de Control y Filtro de Polígonos */}
              <div className="p-3 sm:p-4 border-b border-[var(--rule-hairline)] flex flex-wrap items-center justify-between gap-2.5 bg-[var(--surface-subtle)]">
                <div className="inline-flex border border-[var(--rule-strong)] bg-[var(--surface-panel)] divide-x divide-[var(--rule-strong)]">
                  {[
                    { id: 'TODAS', label: `Todas (${allParcels.length})` },
                    { id: 'PREDICCION', label: '59 Predicción Ciega' },
                    { id: 'ENTRENAMIENTO', label: '138 Entrenamiento' },
                  ].map((tab) => (
                    <button
                      key={tab.id}
                      type="button"
                      onClick={() => setFilterConjunto(tab.id)}
                      className={`px-3 py-1.5 text-xs font-bold transition cursor-pointer ${
                        filterConjunto === tab.id
                          ? 'bg-[var(--invert-bg)] text-[var(--invert-ink)]'
                          : 'bg-[var(--surface-panel)] text-[var(--ink-primary)] hover:bg-[var(--surface-subtle)]'
                      }`}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>

                <div className="relative flex-1 min-w-[180px] sm:max-w-[240px]">
                  <Search className="w-3.5 h-3.5 text-[var(--ink-secondary)] absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Filtrar ID (ej. AGC_002)..."
                    className="w-full bg-[var(--surface-panel)] border border-[var(--rule-strong)] pl-8 pr-3 py-1.5 text-xs text-[var(--ink-primary)] placeholder-[var(--ink-muted)] outline-none focus:border-[#FF4F00]"
                  />
                </div>
              </div>

              {/* Contenedor del Mapa Esri (con isolate z-0 y overflow-hidden para nunca sobreponerse al navbar ni a la tabla inferior) */}
              <div className="relative isolate z-0 h-[360px] sm:h-[450px] lg:h-[520px] p-3 bg-[var(--surface-panel)] overflow-hidden">
                <ParcelMap
                  geojson={geojson}
                  selectedId={selectedParcel?.ID_POLIGONO}
                  onSelectParcel={(id) => setSelectedId(id)}
                  filterConjunto={filterConjunto}
                />
              </div>

              {/* Índice Tabular de Selección Rápida de Polígonos */}
              <div className="p-3.5 sm:p-4 border-t border-[var(--rule-strong)] bg-[var(--surface-subtle)]">
                <div className="flex flex-wrap items-center justify-between gap-2 mb-2.5">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--ink-primary)]">
                    Índice de Polígonos ({filteredParcels.length} registros activos)
                  </span>
                  <span className="text-[11px] text-[var(--ink-secondary)]">
                    Selecciona un polígono para inspeccionar su curva NDVI y simulador
                  </span>
                </div>
                <div className="flex gap-2 overflow-x-auto pb-1.5">
                  {filteredParcels.slice(0, 60).map((p) => {
                    const isSel = p.ID_POLIGONO === selectedParcel?.ID_POLIGONO
                    const yVal = Number(p.RENDIMIENTO_FINAL_T_HA || 0)
                    return (
                      <button
                        key={p.ID_POLIGONO}
                        type="button"
                        onClick={() => setSelectedId(p.ID_POLIGONO)}
                        className={`shrink-0 px-3 py-2 border text-left transition cursor-pointer tabular-nums ${
                          isSel
                            ? 'bg-[#FF4F00] text-white border-[var(--rule-strong)]'
                            : 'bg-[var(--surface-panel)] text-[var(--ink-primary)] border-[var(--rule-hairline)] hover:border-[var(--rule-strong)]'
                        }`}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-bold text-xs">{p.ID_POLIGONO}</span>
                          <span
                            className="w-2.5 h-2.5 inline-block border border-[#111111]"
                            style={{ backgroundColor: getYieldColor(yVal) }}
                          />
                        </div>
                        <div
                          className={`text-[11px] mt-0.5 ${
                            isSel ? 'text-white/90' : 'text-[var(--ink-secondary)]'
                          }`}
                        >
                          <b>{yVal.toFixed(2)} t/ha</b> · {Number(p.AREA_HA).toFixed(1)} ha
                        </div>
                      </button>
                    )
                  })}
                </div>
              </div>
            </div>

            {/* DERECHA (5 COLUMNAS): EXPEDIENTE TÉCNICO DE LA PARCELA Y SIMULADOR */}
            {selectedParcel && (
              <div className="lg:col-span-5 flex flex-col divide-y divide-[var(--rule-hairline)] min-w-0">
                {/* Ficha de Identificación Parcelaria */}
                <div className="p-4 sm:p-5 bg-[var(--surface-panel)]">
                  <div className="flex flex-wrap items-start justify-between gap-2 border-b border-[var(--rule-strong)] pb-3">
                    <div>
                      <div className="text-[11px] font-bold uppercase tracking-wider text-[#FF4F00]">
                        Expediente Agronómico Individual
                      </div>
                      <h2 className="text-2xl sm:text-3xl font-black tracking-tight tabular-nums mt-0.5">
                        {selectedParcel.ID_POLIGONO}
                      </h2>
                    </div>
                    <span
                      className={`px-2.5 py-1 text-[11px] font-bold uppercase border border-[var(--rule-strong)] ${
                        selectedParcel.CONJUNTO === 'PREDICCION'
                          ? 'bg-[#FF4F00] text-white'
                          : 'bg-[var(--surface-subtle)] text-[var(--ink-primary)]'
                      }`}
                    >
                      {selectedParcel.CONJUNTO === 'PREDICCION'
                        ? 'Predicción Ciega (59)'
                        : 'Entrenamiento (138)'}
                    </span>
                  </div>

                  {/* Grilla de Parámetros Físicos y Productivos */}
                  <div className="grid grid-cols-3 divide-x divide-[var(--rule-hairline)] border border-[var(--rule-hairline)] mt-3 bg-[var(--surface-subtle)] tabular-nums">
                    <div className="p-2.5 sm:p-3">
                      <span className="text-[10px] font-bold uppercase text-[var(--ink-secondary)] block">
                        {selectedParcel.CONJUNTO === 'PREDICCION' ? 'Rendimiento Predicho' : 'Rendimiento Observado'}
                      </span>
                      <span
                        className="text-lg sm:text-xl font-black block mt-0.5"
                        style={{ color: getYieldColor(selectedParcel.RENDIMIENTO_FINAL_T_HA) }}
                      >
                        {Number(selectedParcel.RENDIMIENTO_FINAL_T_HA).toFixed(2)} t/ha
                      </span>
                      <span className="text-[11px] text-[var(--ink-secondary)] block">
                        Int. 80%: [{Number(selectedParcel.INTERVALO_80_INF_T_HA || 3.3).toFixed(2)}–{Number(selectedParcel.INTERVALO_80_SUP_T_HA || 4.5).toFixed(2)}] (±{Number(selectedParcel.INCERTIDUMBRE_T_HA || 0.56).toFixed(2)})
                      </span>
                    </div>

                    <div className="p-2.5 sm:p-3">
                      <span className="text-[10px] font-bold uppercase text-[var(--ink-secondary)] block">
                        Superficie y Cosecha
                      </span>
                      <span className="text-lg sm:text-xl font-black text-[var(--ink-primary)] block mt-0.5">
                        {Number(selectedParcel.PRODUCCION_ESTIMADA_TON).toFixed(1)} t
                      </span>
                      <span className="text-[11px] text-[var(--ink-secondary)]">
                        Área: {Number(selectedParcel.AREA_HA).toFixed(2)} ha
                      </span>
                    </div>

                    <div className="p-2.5 sm:p-3">
                      <span className="text-[10px] font-bold uppercase text-[var(--ink-secondary)] block">
                        Fisiografía INEGI
                      </span>
                      <span className="text-lg sm:text-xl font-black text-[var(--ink-primary)] block mt-0.5">
                        {Number(selectedParcel.elevacion_promedio).toFixed(0)} m
                      </span>
                      <span className="text-[11px] text-[var(--ink-secondary)]">
                        Pendiente: {Number(selectedParcel.pendiente_promedio).toFixed(2)}°
                      </span>
                    </div>
                  </div>
                </div>

                {/* Curva Fenológica Mensual de NDVI */}
                <div className="p-4 sm:p-5 bg-[var(--surface-panel)]">
                  <div className="mb-2">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--ink-primary)]">
                      Curva Fenológica Satelital (NDVI Mensual · Meses 1 a 11)
                    </h3>
                    <p className="text-xs text-[var(--ink-secondary)]">
                      Comparativa de {selectedParcel.ID_POLIGONO} frente al umbral élite (&ge;4.35 t/ha) y variación directa de NDVI satelital
                    </p>
                  </div>

                  <div className="h-48 sm:h-52 w-full mt-2">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={ndviChartData} margin={{ top: 6, right: 10, left: -22, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="2 2" stroke={chartGrid} />
                        <XAxis dataKey="month" tick={{ fill: chartInk, fontSize: 11, fontWeight: 600 }} />
                        <YAxis domain={[0.1, 0.85]} tick={{ fill: chartInk, fontSize: 11 }} />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: chartTooltipBg,
                            borderColor: chartTooltipBorder,
                            borderRadius: '0px',
                            fontSize: '12px',
                            color: chartInk,
                          }}
                        />
                        <Legend wrapperStyle={{ fontSize: '11px' }} />
                        <Area
                          type="monotone"
                          dataKey="altoRendimiento"
                          name="Referencia Élite (≥4.35 t/ha)"
                          stroke="#71717A"
                          strokeDasharray="4 4"
                          fill="none"
                          strokeWidth={1.8}
                        />
                        <Area
                          type="monotone"
                          dataKey="parcela"
                          name={`NDVI Base ${selectedParcel.ID_POLIGONO}`}
                          stroke={chartInk}
                          fill={chartInk}
                          fillOpacity={0.12}
                          strokeWidth={2.5}
                        />
                        {ndviDelta !== 0 && (
                          <Area
                            type="monotone"
                            dataKey="simulado"
                            name="NDVI Escalado Simulador"
                            stroke="#FF4F00"
                            fill="#FF4F00"
                            fillOpacity={0.14}
                            strokeWidth={2.4}
                          />
                        )}
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Simulador Agronómico de Sensibilidad Respaldado 100% por el Modelo */}
                <div className="p-4 sm:p-5 bg-[var(--surface-subtle)]">
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--ink-primary)]">
                        Simulador de Sensibilidad del Modelo (Predicciones Reales del Ensamble)
                      </h3>
                      <p className="text-xs text-[var(--ink-secondary)]">
                        Evalúa la respuesta aprendida por el Ensemble Agrotec ante perturbaciones en NDVI/EVI, CHIRPS o Tmax/Tmin
                      </p>
                    </div>
                    {hasActiveSimulation && (
                      <button
                        type="button"
                        onClick={() => {
                          setNdviDelta(0)
                          setPrecDelta(0)
                          setTmaxDelta(0)
                        }}
                        className="inline-flex items-center gap-1 text-xs font-bold bg-[var(--surface-panel)] border border-[var(--rule-strong)] px-2.5 py-1 hover:bg-[#FF4F00] hover:text-white transition cursor-pointer"
                      >
                        <RefreshCw className="w-3 h-3" /> Restablecer
                      </button>
                    )}
                  </div>

                  <div className="space-y-3 tabular-nums">
                    <div>
                      <div className="flex justify-between text-xs font-semibold mb-1">
                        <span>Vigor Satelital NDVI / EVI (Meses 1–11)</span>
                        <span className="font-bold text-[#FF4F00]">
                          {ndviDelta > 0 ? `+${ndviDelta}%` : `${ndviDelta}%`}
                        </span>
                      </div>
                      <input
                        type="range"
                        min="-25"
                        max="25"
                        step="5"
                        value={ndviDelta}
                        onChange={(e) => setNdviDelta(Number(e.target.value))}
                        className="swiss-slider"
                      />
                    </div>

                    <div>
                      <div className="flex justify-between text-xs font-semibold mb-1">
                        <span>Precipitación Mensual CHIRPS</span>
                        <span className="font-bold text-[#FF4F00]">
                          {precDelta > 0 ? `+${precDelta}%` : `${precDelta}%`}
                        </span>
                      </div>
                      <input
                        type="range"
                        min="-40"
                        max="40"
                        step="5"
                        value={precDelta}
                        onChange={(e) => setPrecDelta(Number(e.target.value))}
                        className="swiss-slider"
                      />
                    </div>

                    <div>
                      <div className="flex justify-between text-xs font-semibold mb-1">
                        <span>Régimen Térmico Tmax / Tmin (°C)</span>
                        <span className="font-bold text-[#FF4F00]">
                          {tmaxDelta > 0 ? `+${tmaxDelta.toFixed(1)} °C` : `${tmaxDelta.toFixed(1)} °C`}
                        </span>
                      </div>
                      <input
                        type="range"
                        min="-3"
                        max="3"
                        step="0.5"
                        value={tmaxDelta}
                        onChange={(e) => setTmaxDelta(Number(e.target.value))}
                        className="swiss-slider"
                      />
                    </div>
                  </div>

                  {simResult && (
                    <div className="mt-4 pt-3 border-t border-[var(--rule-strong)] bg-[var(--surface-panel)] p-3 border tabular-nums">
                      <div className="flex items-center justify-between">
                        <div>
                          <span className="text-[10px] font-bold uppercase text-[var(--ink-secondary)] block">
                            Predicción del Modelo ({simLoading ? 'Sincronizando...' : 'Superficie Real del Ensamble'})
                          </span>
                          <div className="flex items-baseline gap-2 mt-0.5">
                            <span className="text-2xl font-black text-[var(--ink-primary)]">
                              {Number(simResult.rendimiento_simulado_t_ha).toFixed(3)} t/ha
                            </span>
                            <span
                              className={`text-xs font-bold ${
                                simResult.delta_t_ha >= 0 ? 'text-[#16A34A]' : 'text-[#DC2626]'
                              }`}
                            >
                              ({simResult.delta_t_ha >= 0 ? '+' : ''}
                              {Number(simResult.delta_t_ha).toFixed(3)} t/ha / {simResult.delta_pct}%)
                            </span>
                          </div>
                        </div>
                        <div className="text-right">
                          <span className="text-[10px] font-bold uppercase text-[var(--ink-secondary)] block">
                            Producción Estimada
                          </span>
                          <span className="text-lg font-black text-[#FF4F00]">
                            {Number(simResult.produccion_simulada_ton).toFixed(1)} t
                          </span>
                        </div>
                      </div>
                      <p className="text-[11px] text-[var(--ink-secondary)] mt-2 pt-1.5 border-t border-[var(--rule-hairline)] leading-snug">
                        <b>Nota metodológica:</b> El simulador evalúa las predicciones reales del Ensemble Agrotec sobre los 23 predictores (reflejando correlaciones observacionales aprendidas del histórico, no causalidad física experimental). La gráfica superior muestra el ajuste directo del slider de NDVI.
                      </p>
                    </div>
                  )}
                </div>

                {/* Factores Destacados vs. Media Regional */}
                <div className="p-4 sm:p-5 bg-[var(--surface-panel)]">
                  <div className="mb-2.5">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--ink-primary)]">
                      Factores Destacados vs. Media Regional en {selectedParcel.ID_POLIGONO}
                    </h3>
                    <p className="text-[11px] text-[var(--ink-secondary)]">
                      Desviación estandarizada (z-score) ponderada por la importancia global de cada variable en el ensamble
                    </p>
                  </div>
                  <div className="divide-y divide-[var(--rule-hairline)] border border-[var(--rule-hairline)] tabular-nums">
                    {localDrivers.map((d) => (
                      <div
                        key={d.feature}
                        className="flex items-center justify-between text-xs px-3 py-2 bg-[var(--surface-panel)] hover:bg-[var(--surface-subtle)]"
                      >
                        <div>
                          <span className="font-bold text-[var(--ink-primary)] block">{d.label}</span>
                          <span className="text-[11px] text-[var(--ink-secondary)]">
                            Observado: <b>{d.value}</b> · Media Regional: {d.mean_ref}
                          </span>
                        </div>
                        <span
                          className={`font-bold px-2 py-0.5 text-[11px] border ${
                            d.impact_score >= 0
                              ? 'border-[#16A34A] text-[#16A34A]'
                              : 'border-[#DC2626] text-[#DC2626]'
                          }`}
                        >
                          {d.impact_score >= 0 ? 'Favorable ▲' : 'Desfavorable ▼'} ({d.z_score > 0 ? `+${d.z_score}` : d.z_score}σ)
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* SECCIÓN 02: EXPLICACIÓN DE MODELOS, VALIDACIÓN CRUZADA E IMPORTANCIA DE VARIABLES */}
        {activeTab === 'models' && (
          <div className="space-y-5">
            <div className="grid grid-cols-1 lg:grid-cols-12 border border-[var(--rule-strong)] bg-[var(--surface-panel)] divide-y lg:divide-y-0 lg:divide-x divide-[var(--rule-strong)]">
              {/* Tabla Comparativa de Modelos */}
              <div className="lg:col-span-7 p-4 sm:p-6">
                <div className="border-b border-[var(--rule-strong)] pb-3 mb-4">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-[#FF4F00]">
                    Experimentos Reproducibles · N = 138 Parcelas de Entrenamiento
                  </span>
                  <h2 className="text-lg sm:text-xl font-black text-[var(--ink-primary)] mt-0.5">
                    Comparativa de Modelos en Validación Cruzada (5-Fold CV y 5×5 Repetida)
                  </h2>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-xs tabular-nums border border-[var(--rule-hairline)]">
                    <thead>
                      <tr className="bg-[var(--invert-bg)] text-[var(--invert-ink)] uppercase text-[10px]">
                        <th className="py-2.5 px-3">Arquitectura</th>
                        <th className="py-2.5 px-3">Set</th>
                        <th className="py-2.5 px-3">MAE (5-Fold)</th>
                        <th className="py-2.5 px-3">RMSE (5-Fold)</th>
                        <th className="py-2.5 px-3">RMSE (5×5 Rep)</th>
                        <th className="py-2.5 px-3">R² (5F)</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[var(--rule-hairline)]">
                      {(summary?.models_comparison || []).map((m, idx) => (
                        <tr
                          key={`${m.model}-${m.feature_set}`}
                          className={
                            idx === 0
                              ? 'bg-[var(--surface-active)] font-bold text-[var(--ink-primary)]'
                              : 'hover:bg-[var(--surface-subtle)]'
                          }
                        >
                          <td className="py-2.5 px-3 flex items-center gap-2">
                            {idx === 0 && (
                              <span className="bg-[#FF4F00] text-white text-[10px] px-1.5 py-0.5 font-black">
                                GANADOR
                              </span>
                            )}
                            <span>{m.model}</span>
                          </td>
                          <td className="py-2.5 px-3 text-[var(--ink-secondary)]">{m.feature_set || '39 base'}</td>
                          <td className="py-2.5 px-3 font-bold">
                            {m.mae_cv.toFixed(4)} <span className="text-[var(--ink-muted)] font-normal">±{m.mae_std.toFixed(3)}</span>
                          </td>
                          <td className="py-2.5 px-3 font-bold">
                            {m.rmse_cv.toFixed(4)} <span className="text-[var(--ink-muted)] font-normal">±{m.rmse_std.toFixed(3)}</span>
                          </td>
                          <td className="py-2.5 px-3 font-bold">
                            {Number(m.rmse_repeated_cv || m.rmse_cv).toFixed(4)}{' '}
                            <span className="text-[var(--ink-muted)] font-normal">
                              ±{Number(m.rmse_repeated_std || m.rmse_std).toFixed(3)}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 font-bold text-[#16A34A]">{m.r2_cv.toFixed(4)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Gráfica de Dispersión Out-Of-Fold */}
              <div className="lg:col-span-5 p-4 sm:p-6">
                <div className="border-b border-[var(--rule-strong)] pb-3 mb-4">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--ink-secondary)]">
                    Auditoría Fuera de Muestra (5-Fold OOF · Cobertura Conformal 80%: {eff.conformal_80_coverage_oof_pct || 81.2}%)
                  </span>
                  <h3 className="text-lg font-black text-[var(--ink-primary)] mt-0.5">
                    Rendimiento Observado vs. Predicho (138 Parcelas)
                  </h3>
                </div>
                <div className="h-64 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <ScatterChart margin={{ top: 10, right: 15, bottom: 10, left: -15 }}>
                      <CartesianGrid strokeDasharray="2 2" stroke={chartGrid} />
                      <XAxis
                        type="number"
                        dataKey="actual"
                        name="Observado"
                        domain={[1.8, 5.8]}
                        tick={{ fill: chartInk, fontSize: 11 }}
                      />
                      <YAxis
                        type="number"
                        dataKey="predicted_oof"
                        name="Predicho OOF"
                        domain={[1.8, 5.8]}
                        tick={{ fill: chartInk, fontSize: 11 }}
                      />
                      <Tooltip
                        cursor={{ strokeDasharray: '2 2' }}
                        contentStyle={{
                          backgroundColor: chartTooltipBg,
                          borderColor: chartTooltipBorder,
                          borderRadius: '0px',
                          fontSize: '12px',
                          color: chartInk,
                        }}
                      />
                      <ReferenceLine
                        segment={[
                          { x: 2.0, y: 2.0 },
                          { x: 5.6, y: 5.6 },
                        ]}
                        stroke={chartInk}
                        strokeDasharray="4 4"
                      />
                      <Scatter
                        name="Parcelas (138 OOF)"
                        data={summary?.oof_validation_scatter || []}
                        fill="#FF4F00"
                      />
                    </ScatterChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>

            {/* EXPLICACIÓN DETALLADA DE CADA MODELO EVALUADO Y POR QUÉ GANÓ EL ENSEMBLE */}
            <div className="border border-[var(--rule-strong)] bg-[var(--surface-panel)] p-4 sm:p-6">
              <div className="border-b border-[var(--rule-strong)] pb-3 mb-4">
                <span className="text-[11px] font-bold uppercase tracking-wider text-[#FF4F00]">
                  Fundamento Algorítmico y Criterio de Selección
                </span>
                <h3 className="text-lg sm:text-xl font-black text-[var(--ink-primary)] mt-0.5">
                  ¿En qué consiste cada modelo evaluado y por qué fue seleccionado el Ensemble Agrotec?
                </h3>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {MODEL_ARCHITECTURES_INFO.map((item) => (
                  <div
                    key={item.name}
                    className={`p-4 border transition ${
                      item.isWinner
                        ? 'md:col-span-2 border-2 border-[#FF4F00] bg-[var(--surface-active)]'
                        : 'border-[var(--rule-hairline)] bg-[var(--surface-subtle)]'
                    }`}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                      <h4 className="text-sm sm:text-base font-black text-[var(--ink-primary)]">
                        {item.name}
                      </h4>
                      <span
                        className={`text-[10px] font-black uppercase px-2 py-0.5 border ${
                          item.isWinner
                            ? 'bg-[#FF4F00] text-white border-[#111111]'
                            : 'bg-[var(--surface-panel)] text-[var(--ink-secondary)] border-[var(--rule-hairline)]'
                        }`}
                      >
                        {item.badge}
                      </span>
                    </div>
                    <div className="text-xs font-bold text-[#16A34A] tabular-nums mb-2">
                      {item.metrics}
                    </div>
                    <p className="text-xs text-[var(--ink-secondary)] leading-relaxed mb-2">
                      <b className="text-[var(--ink-primary)]">¿En qué consiste?:</b> {item.description}
                    </p>
                    <p className="text-xs text-[var(--ink-secondary)] leading-relaxed border-t border-[var(--rule-hairline)] pt-2">
                      <b className="text-[var(--ink-primary)]">Rol y Justificación Técnica:</b> {item.whySelected}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            {/* Ranking de Importancia de Variables */}
            <div className="border border-[var(--rule-strong)] bg-[var(--surface-panel)] p-4 sm:p-6">
              <div className="border-b border-[var(--rule-strong)] pb-3 mb-4">
                <span className="text-[11px] font-bold uppercase tracking-wider text-[#FF4F00]">
                  Interpretabilidad Agronómica del Ensamble Completo (Permutación + Impureza)
                </span>
                <h3 className="text-lg font-black text-[var(--ink-primary)] mt-0.5">
                  Importancia Relativa de Variables Predictoras (Top 15 de las 23 Seleccionadas)
                </h3>
              </div>
              <div className="h-80 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={(summary?.feature_importances || []).slice(0, 15)}
                    layout="vertical"
                    margin={{ top: 5, right: 25, left: 45, bottom: 5 }}
                  >
                    <CartesianGrid strokeDasharray="2 2" stroke={chartGrid} />
                    <XAxis type="number" tick={{ fill: chartInk, fontSize: 11 }} unit="%" />
                    <YAxis
                      dataKey="label"
                      type="category"
                      width={220}
                      tick={{ fill: chartInk, fontSize: 11, fontWeight: 600 }}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: chartTooltipBg,
                        borderColor: chartTooltipBorder,
                        borderRadius: '0px',
                        fontSize: '12px',
                        color: chartInk,
                      }}
                    />
                    <Bar dataKey="importance_pct" name="Importancia (%)" radius={[0, 0, 0, 0]}>
                      {(summary?.feature_importances || []).slice(0, 15).map((entry, index) => (
                        <Cell
                          key={entry.feature}
                          fill={index < 3 ? '#FF4F00' : chartInk}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        )}

        {/* SECCIÓN 03: CATÁLOGO OFICIAL DE LAS 59 PREDICCIONES CIEGAS */}
        {activeTab === 'predictions' && (
          <div className="border border-[var(--rule-strong)] bg-[var(--surface-panel)] p-4 sm:p-6">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--rule-strong)] pb-4 mb-4">
              <div>
                <span className="text-[11px] font-bold uppercase tracking-wider text-[#FF4F00]">
                  Entregable Oficial del Reto
                </span>
                <h2 className="text-lg sm:text-xl font-black text-[var(--ink-primary)]">
                  Catálogo de Predicciones para las 59 Parcelas de Prueba Ciega
                </h2>
              </div>
              <button
                type="button"
                onClick={handleDownloadCsv}
                className="inline-flex items-center gap-2 bg-[#FF4F00] hover:opacity-90 text-white font-bold text-xs px-4 py-2.5 border border-[var(--rule-strong)] transition cursor-pointer"
              >
                <Download className="w-4 h-4" />
                Descargar CSV Oficial (59 Parcelas)
              </button>
            </div>

            <div className="overflow-x-auto max-h-[620px]">
              <table className="w-full text-left border-collapse text-xs sm:text-sm tabular-nums border border-[var(--rule-hairline)]">
                <thead className="sticky top-0 bg-[var(--invert-bg)] text-[var(--invert-ink)] text-[11px] uppercase">
                  <tr>
                    <th className="py-2.5 px-3">Folio</th>
                    <th className="py-2.5 px-3">ID Polígono</th>
                    <th className="py-2.5 px-3">Área (ha)</th>
                    <th className="py-2.5 px-3">Rendimiento Predicho (t/ha)</th>
                    <th className="py-2.5 px-3">Intervalo Conformal 80% (t/ha)</th>
                    <th className="py-2.5 px-3">Cosecha Estimada (ton)</th>
                    <th className="py-2.5 px-3">Elevación (msnm)</th>
                    <th className="py-2.5 px-3">Inspección</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--rule-hairline)]">
                  {allParcels
                    .filter((p) => p.CONJUNTO === 'PREDICCION')
                    .map((p, i) => {
                      const yVal = Number(p.RENDIMIENTO_PREDICHO_T_HA ?? p.RENDIMIENTO_FINAL_T_HA)
                      const inf80 = Number(p.INTERVALO_80_INF_T_HA || yVal - 0.56).toFixed(2)
                      const sup80 = Number(p.INTERVALO_80_SUP_T_HA || yVal + 0.56).toFixed(2)
                      const half80 = Number(p.INCERTIDUMBRE_T_HA || 0.56).toFixed(2)
                      return (
                        <tr key={p.ID_POLIGONO} className="hover:bg-[var(--surface-subtle)]">
                          <td className="py-2.5 px-3 text-[var(--ink-muted)] font-bold">
                            {String(i + 1).padStart(2, '0')}
                          </td>
                          <td className="py-2.5 px-3 font-black text-[var(--ink-primary)]">{p.ID_POLIGONO}</td>
                          <td className="py-2.5 px-3">{Number(p.AREA_HA).toFixed(2)}</td>
                          <td className="py-2.5 px-3 font-black">
                            <span
                              className="px-2 py-0.5 border border-[#111111] text-white"
                              style={{ backgroundColor: getYieldColor(yVal) }}
                            >
                              {yVal.toFixed(4)} t/ha
                            </span>
                          </td>
                          <td className="py-2.5 px-3 text-[var(--ink-secondary)]">
                            [{inf80} – {sup80}] <span className="text-[var(--ink-muted)]">(±{half80})</span>
                          </td>
                          <td className="py-2.5 px-3 font-bold text-[var(--ink-primary)]">
                            {Number(p.PRODUCCION_ESTIMADA_TON).toFixed(2)} t
                          </td>
                          <td className="py-2.5 px-3 text-[var(--ink-secondary)]">
                            {Number(p.elevacion_promedio).toFixed(0)} m
                          </td>
                          <td className="py-2.5 px-3">
                            <button
                              type="button"
                              onClick={() => {
                                setSelectedId(p.ID_POLIGONO)
                                setActiveTab('cockpit')
                              }}
                              className="inline-flex items-center gap-1 text-xs font-bold text-[#FF4F00] hover:underline cursor-pointer"
                            >
                              <span>Abrir en Mapa</span>
                              <ArrowUpRight className="w-3.5 h-3.5" />
                            </button>
                          </td>
                        </tr>
                      )
                    })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* SECCIÓN 04: CALIDAD DEL DATASET, CIFRAS DEMOSTRATIVAS Y RESUMEN DE TECNOLOGÍAS */}
        {activeTab === 'deploy' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 border border-[var(--rule-strong)] bg-[var(--surface-panel)] divide-y lg:divide-y-0 lg:divide-x divide-[var(--rule-strong)]">
            <div className="lg:col-span-4 p-6 flex flex-col items-start justify-between bg-[var(--surface-subtle)]">
              <div>
                <span className="text-[11px] font-bold uppercase tracking-wider text-[#FF4F00]">
                  Identidad del Equipo
                </span>
                <h2 className="text-2xl font-black text-[var(--ink-primary)] mt-1">
                  Agrotec-Amanteca
                </h2>
                <p className="text-xs text-[var(--ink-secondary)] mt-2 leading-relaxed">
                  Los <i>Amanteca</i> eran los maestros artesanos del México prehispánico especializados en ensamblar mosaicos naturales de alta precisión. Nuestro sistema integra mosaicos satelitales multiespectrales, rasters climáticos CHIRPS y modelos topográficos INEGI.
                </p>
              </div>

              <img
                src="./logo_agrotec_amanteca.jpg"
                alt="Emblema Agrotec-Amanteca"
                className="w-52 h-52 object-cover border border-[var(--rule-strong)] my-5"
                onError={(e) => {
                  e.currentTarget.src = './logo_agrotec_amanteca.svg'
                }}
              />

              {/* Integrantes Oficiales del Equipo */}
              <div className="w-full border-t border-[var(--rule-strong)] pt-3 text-xs">
                <div className="text-[10px] font-black uppercase tracking-wider text-[#FF4F00] mb-1.5">
                  Integrantes del Equipo Agrotec-Amanteca
                </div>
                <ul className="space-y-1 text-[var(--ink-primary)] font-semibold">
                  {TEAM_MEMBERS.map((member) => (
                    <li key={member} className="flex items-center gap-2">
                      <span className="w-1.5 h-1.5 bg-[#FF4F00] inline-block" />
                      <span>{member}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            <div className="lg:col-span-8 p-6 space-y-6">
              <div>
                <span className="text-[11px] font-bold uppercase tracking-wider text-[#FF4F00]">
                  Auditoría Estadística y Computacional
                </span>
                <h3 className="text-xl font-black text-[var(--ink-primary)] mt-0.5">
                  Cifras Medibles de Precisión, Calibración de Incertidumbre y Eficiencia
                </h3>
              </div>

              {/* 6 Indicadores Cuantitativos Medidos */}
              <div className="grid grid-cols-1 sm:grid-cols-3 border border-[var(--rule-strong)] divide-y sm:divide-y-0 sm:divide-x divide-[var(--rule-strong)] tabular-nums">
                <div className="p-4">
                  <span className="text-[10px] font-bold uppercase text-[var(--ink-secondary)] block">
                    Exactitud Media OOF (100 - MAPE)
                  </span>
                  <span className="text-2xl font-black text-[#16A34A] mt-1 block">
                    {Number(eff.accuracy_oof_pct || (100 - Number(eff.mape_oof_pct || 10.18))).toFixed(2)}%
                  </span>
                  <span className="text-xs text-[var(--ink-secondary)] mt-1 block">
                    MAPE Out-Of-Fold de <b>{eff.mape_oof_pct || 10.18}%</b> en las 138 parcelas (frente a <b>{baseMetrics.mape_oof_pct || 10.65}%</b> medido en el Baseline RF de 39 variables).
                  </span>
                </div>

                <div className="p-4">
                  <span className="text-[10px] font-bold uppercase text-[var(--ink-secondary)] block">
                    Certeza en Campo (&le;0.50 t/ha)
                  </span>
                  <span className="text-2xl font-black text-[var(--ink-primary)] mt-1 block">
                    {eff.oof_within_050_t_ha_pct || 73.2}%
                  </span>
                  <span className="text-xs text-[var(--ink-secondary)] mt-1 block">
                    De las parcelas OOF tienen error &le; ±0.50 t/ha (vs. <b>{baseMetrics.oof_within_050_t_ha_pct || 71.7}%</b> del Baseline RF). Cobertura Conformal 80% real: <b>{eff.conformal_80_coverage_oof_pct || 81.2}%</b>.
                  </span>
                </div>

                <div className="p-4">
                  <span className="text-[10px] font-bold uppercase text-[var(--ink-secondary)] block">
                    Latencia y Artefacto Serializado
                  </span>
                  <span className="text-2xl font-black text-[#FF4F00] mt-1 block">
                    {eff.inference_per_parcel_ms ? `${Number(eff.inference_per_parcel_ms).toFixed(2)} ms` : '0.46 ms'} / parcela
                  </span>
                  <span className="text-xs text-[var(--ink-secondary)] mt-1 block">
                    Inferencia de las 197 parcelas en <b>{Number(eff.inference_197_ms || 91.36).toFixed(1)} ms</b>; artefacto `.joblib` de 4 sub-modelos en <b>{eff.model_bundle_size_kb || 1433.7} KB</b>.
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 border border-[var(--rule-hairline)] bg-[var(--surface-subtle)] divide-y sm:divide-y-0 sm:divide-x divide-[var(--rule-hairline)] tabular-nums">
                <div className="p-3.5">
                  <span className="text-[10px] font-bold uppercase text-[var(--ink-secondary)] block">
                    Paridad Exacta CV == Modelo Final
                  </span>
                  <span className="text-lg font-black text-[var(--ink-primary)] mt-0.5 block">
                    -{stats.collinearity_reduction_pct || 86.9}% (175 → {stats.total_features_selected || 23})
                  </span>
                  <span className="text-[11px] text-[var(--ink-secondary)]">
                    22 variables por Smart-Pearson (|r| &lt; 0.88) + 1 potencial espacial IDW (k=7).
                  </span>
                </div>
                <div className="p-3.5">
                  <span className="text-[10px] font-bold uppercase text-[var(--ink-secondary)] block">
                    Integridad Tabular y Espacial
                  </span>
                  <span className="text-lg font-black text-[#16A34A] mt-0.5 block">
                    100% Completitud (0 Nulos)
                  </span>
                  <span className="text-[11px] text-[var(--ink-secondary)]">
                    197 polígonos en EPSG:4326 con centroides proyectados en UTM 14N (EPSG:32614).
                  </span>
                </div>
                <div className="p-3.5">
                  <span className="text-[10px] font-bold uppercase text-[var(--ink-secondary)] block">
                    Mejora Medida vs. Baseline RF
                  </span>
                  <span className="text-lg font-black text-[#FF4F00] mt-0.5 block">
                    -{maeGainPct}% MAE · +{r2GainPts} pts R²
                  </span>
                  <span className="text-[11px] text-[var(--ink-secondary)]">
                    Reducción de MAE de {Number(baseMetrics.mae_cv || 0.3742).toFixed(4)} a {Number(bestModelMetric.mae_cv).toFixed(4)} t/ha y R² de {Number(baseMetrics.r2_cv || 0.5859).toFixed(4)} a {Number(bestModelMetric.r2_cv).toFixed(4)}.
                  </span>
                </div>
              </div>

              {/* RESUMEN DE TECNOLOGÍAS IMPLEMENTADAS */}
              <div className="border border-[var(--rule-strong)] p-4 sm:p-5 bg-[var(--surface-subtle)] space-y-3">
                <div className="flex items-center justify-between border-b border-[var(--rule-hairline)] pb-2">
                  <div className="font-black text-xs sm:text-sm text-[var(--ink-primary)] uppercase">
                    Resumen de Tecnologías Implementadas (Stack Tecnológico Verificado)
                  </div>
                  <span className="text-[10px] font-bold uppercase text-[#FF4F00]">
                    Arquitectura Abierta y Reproducible
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                  {techStackDynamic.map((tech) => (
                    <div
                      key={tech.category}
                      className="p-3 bg-[var(--surface-panel)] border border-[var(--rule-hairline)]"
                    >
                      <div className="font-black text-[var(--ink-primary)] uppercase text-[11px]">
                        {tech.category}
                      </div>
                      <div className="text-[#FF4F00] font-bold text-[11px] mt-0.5">
                        {tech.items}
                      </div>
                      <p className="text-[var(--ink-secondary)] mt-1 leading-relaxed">
                        {tech.detail}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* FOOTER INSTITUCIONAL CON DERECHOS RESERVADOS E INTEGRANTES */}
      <footer className="border-t border-[var(--rule-strong)] bg-[var(--surface-panel)] text-[var(--ink-secondary)] text-xs">
        <div className="max-w-[1600px] mx-auto px-4 sm:px-6 py-6 grid grid-cols-1 md:grid-cols-12 gap-4 items-center">
          <div className="md:col-span-5 flex items-center gap-3">
            <img
              src="./logo_agrotec_amanteca.svg"
              alt="Logo Agrotec-Amanteca"
              className="w-9 h-9 border border-[var(--rule-strong)] bg-[#111111] p-1 shrink-0"
              onError={(e) => {
                e.currentTarget.src = './logo_agrotec_amanteca.jpg'
              }}
            />
            <div>
              <div className="font-black text-[var(--ink-primary)] uppercase tracking-tight">
                © 2026 Equipo Agrotec-Amanteca · Todos los derechos reservados
              </div>
              <div className="text-[11px] text-[var(--ink-secondary)]">
                Reto AgroCebada FIRA 2026 · Sistema Predictivo de Rendimiento Agrícola de Cebada (t/ha)
              </div>
            </div>
          </div>

          <div className="md:col-span-7 md:text-right">
            <div className="text-[10px] font-bold uppercase tracking-wider text-[#FF4F00] mb-1">
              Créditos de Desarrollo e Investigación Científica
            </div>
            <div className="text-[11px] font-semibold text-[var(--ink-primary)] leading-relaxed">
              {TEAM_MEMBERS.join('  ·  ')}
            </div>
          </div>
        </div>
      </footer>

      {/* NAVEGACIÓN INFERIOR MÓVIL (SMARTPHONES) */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-[1000] bg-[var(--surface-panel)] border-t border-[var(--rule-strong)] grid grid-cols-4 divide-x divide-[var(--rule-hairline)]">
        {[
          { id: 'cockpit', num: '01', label: 'Mapa' },
          { id: 'models', num: '02', label: 'Modelos' },
          { id: 'predictions', num: '03', label: '59 Preds' },
          { id: 'deploy', num: '04', label: 'Tecnologías' },
        ].map((item) => {
          const active = activeTab === item.id
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => setActiveTab(item.id)}
              className={`py-2.5 px-2 text-center ${
                active
                  ? 'bg-[var(--invert-bg)] text-[var(--invert-ink)]'
                  : 'bg-[var(--surface-panel)] text-[var(--ink-primary)]'
              }`}
            >
              <span className="block text-[10px] font-bold text-[#FF4F00] tabular-nums">
                {item.num}
              </span>
              <span className="block text-[11px] font-bold">{item.label}</span>
            </button>
          )
        })}
      </nav>

      {/* MODAL DEL EMBLEMA OFICIAL */}
      {showLogoModal && (
        <div
          className="fixed inset-0 z-[1100] bg-black/75 flex items-center justify-center p-4"
          onClick={() => setShowLogoModal(false)}
        >
          <div
            className="bg-[var(--surface-panel)] border-2 border-[var(--rule-strong)] p-6 max-w-md w-full text-left"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="text-[11px] font-bold uppercase text-[#FF4F00] mb-1">
              Identidad Visual Oficial
            </div>
            <h3 className="text-xl font-black text-[var(--ink-primary)] mb-4">Agrotec-Amanteca</h3>
            <img
              src="./logo_agrotec_amanteca.jpg"
              alt="Logo Agrotec-Amanteca"
              className="w-64 h-64 mx-auto border border-[var(--rule-strong)] object-cover mb-4"
              onError={(e) => {
                e.currentTarget.src = './logo_agrotec_amanteca.svg'
              }}
            />
            <button
              type="button"
              onClick={() => setShowLogoModal(false)}
              className="w-full py-2.5 bg-[#FF4F00] text-white font-bold text-xs uppercase cursor-pointer transition"
            >
              Cerrar Vista
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
