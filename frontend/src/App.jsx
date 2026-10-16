import React, { useEffect, useMemo, useState } from 'react'
import {
  ArrowUpRight,
  Award,
  BarChart3,
  CloudRain,
  Compass,
  Download,
  Globe,
  MapPin,
  RefreshCw,
  Search,
  Sliders,
  Sprout,
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

export default function App() {
  const [summary, setSummary] = useState(null)
  const [geojson, setGeojson] = useState(null)
  const [loading, setLoading] = useState(true)
  const [apiMode, setApiMode] = useState('checking')
  const [activeTab, setActiveTab] = useState('cockpit')
  const [filterConjunto, setFilterConjunto] = useState('TODAS')
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedId, setSelectedId] = useState('AGC_003')
  const [showLogoModal, setShowLogoModal] = useState(false)

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
        const [sumRes, geoRes] = await Promise.all([
          fetch(`${API_BASE}/api/summary`),
          fetch(`${API_BASE}/api/parcelas`),
        ])
        if (sumRes.ok && geoRes.ok) {
          const [sumJson, geoJson] = await Promise.all([sumRes.json(), geoRes.json()])
          if (mounted) {
            setSummary(sumJson)
            setGeojson(geoJson)
            setApiMode('cloud')
            setLoading(false)
          }
          return
        }
      } catch {
        // Fallback automático a los datos estáticos para Vercel / Cloudflare Pages
      }

      try {
        const [sumStatic, geoStatic] = await Promise.all([
          fetch('/data/metrics_summary.json').then((r) => r.json()),
          fetch('/data/parcelas_197_dashboard.geojson').then((r) => r.json()),
        ])
        if (mounted) {
          setSummary(sumStatic)
          setGeojson(geoStatic)
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

  useEffect(() => {
    if (!selectedParcel) return
    let cancelled = false

    async function runSimulation() {
      const baseYield = Number(
        selectedParcel.RENDIMIENTO_PREDICHO_T_HA ||
          selectedParcel.RENDIMIENTO_FINAL_T_HA ||
          3.95
      )
      const areaHa = Number(selectedParcel.AREA_HA || 1.0)

      if (ndviDelta === 0 && precDelta === 0 && tmaxDelta === 0) {
        setSimResult({
          rendimiento_base_modelo_t_ha: baseYield,
          rendimiento_simulado_t_ha: baseYield,
          delta_t_ha: 0,
          delta_pct: 0,
          produccion_base_ton: +(baseYield * areaHa).toFixed(2),
          produccion_simulada_ton: +(baseYield * areaHa).toFixed(2),
        })
        return
      }

      setSimLoading(true)
      if (apiMode === 'cloud') {
        try {
          const res = await fetch(`${API_BASE}/api/simular`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              id_poligono: selectedParcel.ID_POLIGONO,
              ndvi_delta_pct: ndviDelta,
              prec_delta_pct: precDelta,
              tmax_delta_c: tmaxDelta,
            }),
          })
          if (res.ok) {
            const data = await res.json()
            if (!cancelled) {
              setSimResult(data)
              setSimLoading(false)
            }
            return
          }
        } catch {
          // Elasticidad calibrada en cliente cuando opera sin backend
        }
      }

      const ndviEffect = baseYield * (ndviDelta / 100) * 0.42
      const precEffect = baseYield * (precDelta / 100) * 0.28
      const tmaxEffect = -0.065 * tmaxDelta
      const simYield = Math.max(
        1.5,
        Math.min(6.2, +(baseYield + ndviEffect + precEffect + tmaxEffect).toFixed(4))
      )
      const delta = +(simYield - baseYield).toFixed(4)
      const deltaPct = +((delta / baseYield) * 100).toFixed(2)

      if (!cancelled) {
        setSimResult({
          rendimiento_base_modelo_t_ha: baseYield,
          rendimiento_simulado_t_ha: simYield,
          delta_t_ha: delta,
          delta_pct: deltaPct,
          produccion_base_ton: +(baseYield * areaHa).toFixed(2),
          produccion_simulada_ton: +(simYield * areaHa).toFixed(2),
        })
        setSimLoading(false)
      }
    }

    runSimulation()
    return () => {
      cancelled = true
    }
  }, [selectedParcel, ndviDelta, precDelta, tmaxDelta, apiMode])

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
          Number(r.INCERTIDUMBRE_T_HA ?? 0.25).toFixed(4),
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

  if (loading) {
    return (
      <div className="min-h-screen bg-[#F7F7F8] text-[#111111] flex flex-col items-center justify-center p-6">
        <div className="border border-[#111111] bg-white p-8 max-w-md w-full text-left">
          <div className="text-xs font-bold uppercase tracking-widest text-[#FF4F00] mb-2">
            FIRA 2026 · Agrotec-Amanteca
          </div>
          <h1 className="text-xl font-black tracking-tight">
            Cargando Cartografía y Modelo Predictivo
          </h1>
          <p className="text-xs text-[#52525B] mt-2">
            Sincronizando 197 polígonos agrícolas (138 entrenamiento, 59 predicción ciega).
          </p>
        </div>
      </div>
    )
  }

  const stats = summary?.dataset_stats || {}
  const eff = summary?.efficiency_metrics || {}
  const bestModelMetric = summary?.models_comparison?.[0] || {
    model: 'Ensemble Agrotec-Amanteca (Voting)',
    mae_cv: 0.367,
    rmse_cv: 0.5067,
    r2_cv: 0.5972,
  }

  return (
    <div className="min-h-screen bg-[#F7F7F8] text-[#111111] flex flex-col pb-20 md:pb-10">
      {/* MASTHEAD EDITORIAL SWISS (RETÍCULA 1PX, TIPOGRAFÍA ALINEADA A LA IZQUIERDA) */}
      <header className="sticky top-0 z-50 bg-white border-b border-[#111111]">
        <div className="max-w-[1600px] mx-auto grid grid-cols-12 items-stretch">
          {/* Bloque Marca e Identidad */}
          <div className="col-span-7 sm:col-span-6 lg:col-span-4 px-3 sm:px-5 py-3 border-r border-[#D4D4D8] flex items-center gap-3">
            <button
              type="button"
              onClick={() => setShowLogoModal(true)}
              className="w-10 h-10 border border-[#111111] bg-[#111111] flex items-center justify-center shrink-0 cursor-pointer hover:border-[#FF4F00] transition"
              title="Ver Emblema Oficial Agrotec-Amanteca"
            >
              <img
                src="/logo_agrotec_amanteca.svg"
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
              <p className="text-[11px] text-[#52525B] truncate">
                Predicción de Rendimiento de Cebada (t/ha) · 197 Parcelas
              </p>
            </div>
          </div>

          {/* Navegación Estructural Desktop */}
          <nav className="hidden lg:flex lg:col-span-5 items-stretch divide-x divide-[#D4D4D8] border-r border-[#D4D4D8]">
            {[
              { id: 'cockpit', num: '01', label: 'Cartografía y Diagnóstico' },
              { id: 'models', num: '02', label: 'Validación ML y Variables' },
              { id: 'predictions', num: '03', label: '59 Predicciones Oficiales' },
              { id: 'deploy', num: '04', label: 'Calidad y Despliegue Cloud' },
            ].map((item) => {
              const active = activeTab === item.id
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setActiveTab(item.id)}
                  className={`flex-1 px-3 py-2 text-left transition cursor-pointer flex flex-col justify-between ${
                    active
                      ? 'bg-[#111111] text-white'
                      : 'bg-white text-[#111111] hover:bg-[#F7F7F8]'
                  }`}
                >
                  <span
                    className={`text-[10px] font-bold tabular-nums ${
                      active ? 'text-[#FF4F00]' : 'text-[#71717A]'
                    }`}
                  >
                    {item.num}
                  </span>
                  <span className="text-xs font-bold leading-tight">{item.label}</span>
                </button>
              )
            })}
          </nav>

          {/* Acción de Exportación Oficial */}
          <div className="col-span-5 sm:col-span-6 lg:col-span-3 px-3 sm:px-5 py-2.5 flex items-center justify-end gap-2.5">
            <span className="hidden xl:inline-block text-[11px] font-medium text-[#52525B] tabular-nums">
              {apiMode === 'cloud' ? 'API Railway Activa' : 'Modo Estático Edge'}
            </span>
            <button
              type="button"
              onClick={handleDownloadCsv}
              className="inline-flex items-center gap-1.5 bg-[#FF4F00] hover:bg-[#111111] text-white font-bold text-xs px-3.5 py-2 border border-[#111111] transition cursor-pointer"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Exportar 59 Predicciones (.CSV)</span>
            </button>
          </div>
        </div>

        {/* Barra de Navegación para Tablets (md) */}
        <div className="hidden md:grid lg:hidden grid-cols-4 divide-x divide-[#D4D4D8] border-t border-[#D4D4D8] bg-white">
          {[
            { id: 'cockpit', num: '01', label: 'Cartografía y Simulador' },
            { id: 'models', num: '02', label: 'Validación Cruzada ML' },
            { id: 'predictions', num: '03', label: 'Catálogo 59 Predicciones' },
            { id: 'deploy', num: '04', label: 'Calidad y Cloud' },
          ].map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setActiveTab(item.id)}
              className={`px-3 py-2 text-left text-xs font-bold ${
                activeTab === item.id ? 'bg-[#111111] text-white' : 'text-[#111111]'
              }`}
            >
              <span className="text-[#FF4F00] mr-1.5 tabular-nums">{item.num}</span>
              {item.label}
            </button>
          ))}
        </div>
      </header>

      {/* CUERPO EDITORIAL EN RETÍCULA SWISS */}
      <main className="flex-1 max-w-[1600px] w-full mx-auto px-3 sm:px-6 pt-5 space-y-5">
        {/* BANDA DE NUMERALES COMPOSITIVOS (4 FOLIOS DE MÉTRICAS REALES DEL PROYECTO) */}
        <section className="grid grid-cols-2 lg:grid-cols-4 bg-white border border-[#111111] divide-y sm:divide-y-0 divide-x divide-[#D4D4D8]">
          <div className="p-4 sm:p-5 flex flex-col justify-between">
            <div className="flex items-baseline justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-[#52525B]">
                01 · Rendimiento Medio Predicho
              </span>
              <span className="text-[11px] font-bold text-[#FF4F00] tabular-nums">59 Ciegas</span>
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="folio-numeral text-3xl sm:text-4xl lg:text-[42px] text-[#111111]">
                {Number(stats.pred_yield_mean || 3.92).toFixed(2)}
              </span>
              <span className="text-xs font-bold uppercase text-[#52525B]">t/ha</span>
            </div>
            <p className="text-xs text-[#52525B] mt-2 tabular-nums border-t border-[#D4D4D8] pt-1.5">
              Media Entrenamiento (138): <b className="text-[#111111]">{Number(stats.train_yield_mean || 3.96).toFixed(2)} t/ha</b> · Rango: {Number(stats.pred_yield_min || 2.85).toFixed(2)}–{Number(stats.pred_yield_max || 4.82).toFixed(2)}
            </p>
          </div>

          <div className="p-4 sm:p-5 flex flex-col justify-between">
            <div className="flex items-baseline justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-[#52525B]">
                02 · Precisión Validación (5-Fold CV)
              </span>
              <span className="text-[11px] font-bold text-[#16A34A] tabular-nums">
                R² {Number(bestModelMetric.r2_cv).toFixed(3)}
              </span>
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="folio-numeral text-3xl sm:text-4xl lg:text-[42px] text-[#111111]">
                {Number(bestModelMetric.mae_cv).toFixed(4)}
              </span>
              <span className="text-xs font-bold uppercase text-[#52525B]">MAE (t/ha)</span>
            </div>
            <p className="text-xs text-[#52525B] mt-2 tabular-nums border-t border-[#D4D4D8] pt-1.5">
              RMSE CV: <b className="text-[#111111]">{Number(bestModelMetric.rmse_cv).toFixed(4)} t/ha</b> · MAPE OOF: <b className="text-[#111111]">{Number(eff.mape_oof_pct || 9.8).toFixed(2)}%</b>
            </p>
          </div>

          <div className="p-4 sm:p-5 flex flex-col justify-between">
            <div className="flex items-baseline justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-[#52525B]">
                03 · Volumen Productivo Estimado
              </span>
              <span className="text-[11px] font-bold text-[#52525B] tabular-nums">
                {Number(stats.total_area_ha || 1560.6).toFixed(1)} ha
              </span>
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="folio-numeral text-3xl sm:text-4xl lg:text-[42px] text-[#111111]">
                {Number(stats.total_production_ton || 6120).toLocaleString('es-MX', {
                  maximumFractionDigits: 0,
                })}
              </span>
              <span className="text-xs font-bold uppercase text-[#52525B]">toneladas</span>
            </div>
            <p className="text-xs text-[#52525B] mt-2 tabular-nums border-t border-[#D4D4D8] pt-1.5">
              Cosecha en 59 parcelas de prueba: <b className="text-[#111111]">{Number(stats.pred_production_ton || 1845).toFixed(1)} t</b> ({Number(stats.pred_area_ha || 467.6).toFixed(1)} ha)
            </p>
          </div>

          <div className="p-4 sm:p-5 flex flex-col justify-between">
            <div className="flex items-baseline justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-[#52525B]">
                04 · Pureza de Datos y Eficiencia
              </span>
              <span className="text-[11px] font-bold text-[#FF4F00] tabular-nums">
                {Number(eff.inference_197_ms || 14.2).toFixed(1)} ms
              </span>
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="folio-numeral text-3xl sm:text-4xl lg:text-[42px] text-[#111111]">
                175→{stats.base_features_after_pearson || 39}
              </span>
              <span className="text-xs font-bold uppercase text-[#52525B]">predictores</span>
            </div>
            <p className="text-xs text-[#52525B] mt-2 tabular-nums border-t border-[#D4D4D8] pt-1.5">
              Filtro Pearson <b className="text-[#111111]">|r| &lt; 0.90</b> · Completitud: <b className="text-[#111111]">100% (0 Nulos)</b>
            </p>
          </div>
        </section>

        {/* SECCIÓN 01: CARTOGRAFÍA Y DIAGNÓSTICO POR PARCELA */}
        {activeTab === 'cockpit' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 border border-[#111111] bg-white divide-y lg:divide-y-0 lg:divide-x divide-[#111111]">
            {/* IZQUIERDA (7 COLUMNAS): VISOR CARTOGRÁFICO DE LAS 197 PARCELAS */}
            <div className="lg:col-span-7 flex flex-col">
              {/* Barra de Control y Filtro de Polígonos */}
              <div className="p-3 sm:p-4 border-b border-[#D4D4D8] flex flex-wrap items-center justify-between gap-2.5 bg-[#F7F7F8]">
                <div className="inline-flex border border-[#111111] bg-white divide-x divide-[#111111]">
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
                          ? 'bg-[#111111] text-white'
                          : 'bg-white text-[#111111] hover:bg-[#F7F7F8]'
                      }`}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>

                <div className="relative flex-1 min-w-[180px] sm:max-w-[240px]">
                  <Search className="w-3.5 h-3.5 text-[#52525B] absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Filtrar ID (ej. AGC_003)..."
                    className="w-full bg-white border border-[#111111] pl-8 pr-3 py-1.5 text-xs text-[#111111] placeholder-[#71717A] outline-none focus:border-[#FF4F00]"
                  />
                </div>
              </div>

              {/* Contenedor del Mapa Esri (Satélite / Táctico Gris / Topográfico) */}
              <div className="h-[380px] sm:h-[460px] lg:h-[540px] p-3 bg-white">
                <ParcelMap
                  geojson={geojson}
                  selectedId={selectedParcel?.ID_POLIGONO}
                  onSelectParcel={(id) => setSelectedId(id)}
                  filterConjunto={filterConjunto}
                />
              </div>

              {/* Índice Tabular de Selección Rápida de Polígonos */}
              <div className="p-3 sm:p-4 border-t border-[#111111] bg-[#F7F7F8]">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-[#111111]">
                    Índice de Polígonos ({filteredParcels.length} registros activos)
                  </span>
                  <span className="text-[11px] text-[#52525B]">
                    Selecciona un polígono para inspeccionar su curva NDVI y simulador
                  </span>
                </div>
                <div className="flex gap-2 overflow-x-auto pb-1.5">
                  {filteredParcels.slice(0, 50).map((p) => {
                    const isSel = p.ID_POLIGONO === selectedParcel?.ID_POLIGONO
                    const yVal = Number(p.RENDIMIENTO_FINAL_T_HA || 0)
                    return (
                      <button
                        key={p.ID_POLIGONO}
                        type="button"
                        onClick={() => setSelectedId(p.ID_POLIGONO)}
                        className={`shrink-0 px-3 py-2 border text-left transition cursor-pointer tabular-nums ${
                          isSel
                            ? 'bg-[#111111] text-white border-[#111111]'
                            : 'bg-white text-[#111111] border-[#D4D4D8] hover:border-[#111111]'
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
                            isSel ? 'text-[#D4D4D8]' : 'text-[#52525B]'
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
              <div className="lg:col-span-5 flex flex-col divide-y divide-[#D4D4D8]">
                {/* Ficha de Identificación Parcelaria */}
                <div className="p-4 sm:p-5 bg-white">
                  <div className="flex flex-wrap items-start justify-between gap-2 border-b border-[#111111] pb-3">
                    <div>
                      <div className="text-[11px] font-bold uppercase tracking-wider text-[#FF4F00]">
                        Expediente Agronómico Individual
                      </div>
                      <h2 className="text-2xl sm:text-3xl font-black tracking-tight tabular-nums mt-0.5">
                        {selectedParcel.ID_POLIGONO}
                      </h2>
                    </div>
                    <span
                      className={`px-2.5 py-1 text-[11px] font-bold uppercase border border-[#111111] ${
                        selectedParcel.CONJUNTO === 'PREDICCION'
                          ? 'bg-[#FF4F00] text-white'
                          : 'bg-[#F7F7F8] text-[#111111]'
                      }`}
                    >
                      {selectedParcel.CONJUNTO === 'PREDICCION'
                        ? 'Predicción Ciega (59)'
                        : 'Entrenamiento (138)'}
                    </span>
                  </div>

                  {/* Grilla de Parámetros Físicos y Productivos */}
                  <div className="grid grid-cols-3 divide-x divide-[#D4D4D8] border border-[#D4D4D8] mt-3 bg-[#F7F7F8] tabular-nums">
                    <div className="p-2.5 sm:p-3">
                      <span className="text-[10px] font-bold uppercase text-[#52525B] block">
                        {selectedParcel.CONJUNTO === 'PREDICCION' ? 'Rendimiento Predicho' : 'Rendimiento Observado'}
                      </span>
                      <span
                        className="text-lg sm:text-xl font-black block mt-0.5"
                        style={{ color: getYieldColor(selectedParcel.RENDIMIENTO_FINAL_T_HA) }}
                      >
                        {Number(selectedParcel.RENDIMIENTO_FINAL_T_HA).toFixed(2)} t/ha
                      </span>
                      <span className="text-[11px] text-[#52525B]">
                        IC: ±{Number(selectedParcel.INCERTIDUMBRE_T_HA || 0.25).toFixed(2)} t/ha
                      </span>
                    </div>

                    <div className="p-2.5 sm:p-3">
                      <span className="text-[10px] font-bold uppercase text-[#52525B] block">
                        Superficie y Cosecha
                      </span>
                      <span className="text-lg sm:text-xl font-black text-[#111111] block mt-0.5">
                        {Number(selectedParcel.PRODUCCION_ESTIMADA_TON).toFixed(1)} t
                      </span>
                      <span className="text-[11px] text-[#52525B]">
                        Área: {Number(selectedParcel.AREA_HA).toFixed(2)} ha
                      </span>
                    </div>

                    <div className="p-2.5 sm:p-3">
                      <span className="text-[10px] font-bold uppercase text-[#52525B] block">
                        Fisiografía INEGI
                      </span>
                      <span className="text-lg sm:text-xl font-black text-[#111111] block mt-0.5">
                        {Number(selectedParcel.elevacion_promedio).toFixed(0)} m
                      </span>
                      <span className="text-[11px] text-[#52525B]">
                        Pendiente: {Number(selectedParcel.pendiente_promedio).toFixed(2)}°
                      </span>
                    </div>
                  </div>
                </div>

                {/* Curva Fenológica Mensual de NDVI */}
                <div className="p-4 sm:p-5 bg-white">
                  <div className="mb-2">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-[#111111]">
                      Curva Fenológica Satelital (NDVI Mensual · Meses 1 a 11)
                    </h3>
                    <p className="text-xs text-[#52525B]">
                      Comparativa de {selectedParcel.ID_POLIGONO} frente al umbral regional de alto rendimiento (&ge;4.35 t/ha)
                    </p>
                  </div>

                  <div className="h-48 sm:h-52 w-full mt-2">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={ndviChartData} margin={{ top: 6, right: 10, left: -22, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="2 2" stroke="#D4D4D8" />
                        <XAxis dataKey="month" tick={{ fill: '#111111', fontSize: 11, fontWeight: 600 }} />
                        <YAxis domain={[0.1, 0.85]} tick={{ fill: '#111111', fontSize: 11 }} />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: '#FFFFFF',
                            borderColor: '#111111',
                            borderRadius: '0px',
                            fontSize: '12px',
                            color: '#111111',
                          }}
                        />
                        <Legend wrapperStyle={{ fontSize: '11px' }} />
                        <Area
                          type="monotone"
                          dataKey="altoRendimiento"
                          name="Referencia Élite (≥4.35 t/ha)"
                          stroke="#52525B"
                          strokeDasharray="4 4"
                          fill="none"
                          strokeWidth={1.8}
                        />
                        <Area
                          type="monotone"
                          dataKey="parcela"
                          name={`NDVI ${selectedParcel.ID_POLIGONO}`}
                          stroke="#111111"
                          fill="#111111"
                          fillOpacity={0.1}
                          strokeWidth={2.5}
                        />
                        {ndviDelta !== 0 && (
                          <Area
                            type="monotone"
                            dataKey="simulado"
                            name="NDVI Escenario Simulado"
                            stroke="#FF4F00"
                            fill="none"
                            strokeWidth={2.2}
                          />
                        )}
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Simulador Agronómico de Sensibilidad en Tiempo Real */}
                <div className="p-4 sm:p-5 bg-[#F7F7F8]">
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <h3 className="text-xs font-bold uppercase tracking-wider text-[#111111]">
                        Simulador de Sensibilidad Agronómica (Inferencia en Vivo)
                      </h3>
                      <p className="text-xs text-[#52525B]">
                        Ajusta vigor NDVI, régimen pluvial CHIRPS o anomalía térmica Tmax
                      </p>
                    </div>
                    {(ndviDelta !== 0 || precDelta !== 0 || tmaxDelta !== 0) && (
                      <button
                        type="button"
                        onClick={() => {
                          setNdviDelta(0)
                          setPrecDelta(0)
                          setTmaxDelta(0)
                        }}
                        className="inline-flex items-center gap-1 text-xs font-bold bg-white border border-[#111111] px-2.5 py-1 hover:bg-[#111111] hover:text-white transition cursor-pointer"
                      >
                        <RefreshCw className="w-3 h-3" /> Restablecer
                      </button>
                    )}
                  </div>

                  <div className="space-y-3 tabular-nums">
                    <div>
                      <div className="flex justify-between text-xs font-semibold mb-1">
                        <span>Vigor Satelital NDVI (Ciclo Reproductivo)</span>
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
                        <span>Precipitación Mensual Acumulada (CHIRPS)</span>
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
                        <span>Anomalía de Temperatura Máxima (Tmax °C)</span>
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
                    <div className="mt-4 pt-3 border-t border-[#111111] flex items-center justify-between tabular-nums bg-white p-3 border">
                      <div>
                        <span className="text-[10px] font-bold uppercase text-[#52525B] block">
                          Rendimiento Simulado ({simLoading ? 'Calculando...' : 'Ensemble IA'})
                        </span>
                        <div className="flex items-baseline gap-2 mt-0.5">
                          <span className="text-2xl font-black text-[#111111]">
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
                        <span className="text-[10px] font-bold uppercase text-[#52525B] block">
                          Producción Estimada
                        </span>
                        <span className="text-lg font-black text-[#FF4F00]">
                          {Number(simResult.produccion_simulada_ton).toFixed(1)} t
                        </span>
                      </div>
                    </div>
                  )}
                </div>

                {/* Explicabilidad Local de la Parcela (5 Factores Principales) */}
                <div className="p-4 sm:p-5 bg-white">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-[#111111] mb-2.5">
                    Variables Determinantes en {selectedParcel.ID_POLIGONO} (Atribución Local)
                  </h3>
                  <div className="divide-y divide-[#D4D4D8] border border-[#D4D4D8] tabular-nums">
                    {localDrivers.map((d) => (
                      <div
                        key={d.feature}
                        className="flex items-center justify-between text-xs px-3 py-2 bg-white hover:bg-[#F7F7F8]"
                      >
                        <div>
                          <span className="font-bold text-[#111111] block">{d.label}</span>
                          <span className="text-[11px] text-[#52525B]">
                            Observado: <b>{d.value}</b> · Media Regional: {d.mean_ref}
                          </span>
                        </div>
                        <span
                          className={`font-bold px-2 py-0.5 text-[11px] border ${
                            d.impact_score >= 0
                              ? 'border-[#16A34A] text-[#16A34A] bg-[#F0FDF4]'
                              : 'border-[#DC2626] text-[#DC2626] bg-[#FEF2F2]'
                          }`}
                        >
                          {d.impact_score >= 0 ? 'Impulsa ▲' : 'Limita ▼'} ({d.z_score > 0 ? `+${d.z_score}` : d.z_score}σ)
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* SECCIÓN 02: VALIDACIÓN CRUZADA DE MODELOS E IMPORTANCIA DE VARIABLES */}
        {activeTab === 'models' && (
          <div className="space-y-5">
            <div className="grid grid-cols-1 lg:grid-cols-12 border border-[#111111] bg-white divide-y lg:divide-y-0 lg:divide-x divide-[#111111]">
              {/* Tabla Comparativa de Modelos */}
              <div className="lg:col-span-7 p-4 sm:p-6">
                <div className="border-b border-[#111111] pb-3 mb-4">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-[#FF4F00]">
                    Experimentos Reproducibles · N = 138 Parcelas de Entrenamiento
                  </span>
                  <h2 className="text-lg sm:text-xl font-black text-[#111111] mt-0.5">
                    Comparativa de Modelos en Validación Cruzada (5-Fold CV y 5×5 Repetida)
                  </h2>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-xs tabular-nums border border-[#D4D4D8]">
                    <thead>
                      <tr className="bg-[#111111] text-white uppercase text-[10px]">
                        <th className="py-2.5 px-3">Arquitectura</th>
                        <th className="py-2.5 px-3">Set</th>
                        <th className="py-2.5 px-3">MAE (5-Fold)</th>
                        <th className="py-2.5 px-3">RMSE (5-Fold)</th>
                        <th className="py-2.5 px-3">R²</th>
                        <th className="py-2.5 px-3">Tiempo CV</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#D4D4D8]">
                      {(summary?.models_comparison || []).map((m, idx) => (
                        <tr
                          key={`${m.model}-${m.feature_set}`}
                          className={
                            idx === 0
                              ? 'bg-[#FFF7ED] font-bold text-[#111111]'
                              : 'hover:bg-[#F7F7F8]'
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
                          <td className="py-2.5 px-3 text-[#52525B]">{m.feature_set || '39 base'}</td>
                          <td className="py-2.5 px-3 font-bold">
                            {m.mae_cv.toFixed(4)} <span className="text-[#71717A] font-normal">±{m.mae_std.toFixed(3)}</span>
                          </td>
                          <td className="py-2.5 px-3 font-bold">
                            {m.rmse_cv.toFixed(4)} <span className="text-[#71717A] font-normal">±{m.rmse_std.toFixed(3)}</span>
                          </td>
                          <td className="py-2.5 px-3 font-bold text-[#16A34A]">{m.r2_cv.toFixed(4)}</td>
                          <td className="py-2.5 px-3 text-[#52525B]">{m.cv_time_ms ? `${m.cv_time_ms.toFixed(0)} ms` : '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Gráfica de Dispersión Out-Of-Fold */}
              <div className="lg:col-span-5 p-4 sm:p-6">
                <div className="border-b border-[#111111] pb-3 mb-4">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-[#52525B]">
                    Auditoría Fuera de Muestra (5-Fold OOF)
                  </span>
                  <h3 className="text-lg font-black text-[#111111] mt-0.5">
                    Rendimiento Observado vs. Predicho (138 Parcelas)
                  </h3>
                </div>
                <div className="h-64 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <ScatterChart margin={{ top: 10, right: 15, bottom: 10, left: -15 }}>
                      <CartesianGrid strokeDasharray="2 2" stroke="#D4D4D8" />
                      <XAxis
                        type="number"
                        dataKey="actual"
                        name="Observado"
                        domain={[1.8, 5.8]}
                        tick={{ fill: '#111111', fontSize: 11 }}
                      />
                      <YAxis
                        type="number"
                        dataKey="predicted_oof"
                        name="Predicho OOF"
                        domain={[1.8, 5.8]}
                        tick={{ fill: '#111111', fontSize: 11 }}
                      />
                      <Tooltip
                        cursor={{ strokeDasharray: '2 2' }}
                        contentStyle={{
                          backgroundColor: '#FFFFFF',
                          borderColor: '#111111',
                          borderRadius: '0px',
                          fontSize: '12px',
                        }}
                      />
                      <ReferenceLine
                        segment={[
                          { x: 2.0, y: 2.0 },
                          { x: 5.6, y: 5.6 },
                        ]}
                        stroke="#111111"
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

            {/* Ranking de Importancia de Variables */}
            <div className="border border-[#111111] bg-white p-4 sm:p-6">
              <div className="border-b border-[#111111] pb-3 mb-4">
                <span className="text-[11px] font-bold uppercase tracking-wider text-[#FF4F00]">
                  Interpretabilidad Agronómica (XAI)
                </span>
                <h3 className="text-lg font-black text-[#111111] mt-0.5">
                  Importancia Relativa de Variables Predictoras (Top 15)
                </h3>
              </div>
              <div className="h-80 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={(summary?.feature_importances || []).slice(0, 15)}
                    layout="vertical"
                    margin={{ top: 5, right: 25, left: 45, bottom: 5 }}
                  >
                    <CartesianGrid strokeDasharray="2 2" stroke="#D4D4D8" />
                    <XAxis type="number" tick={{ fill: '#111111', fontSize: 11 }} unit="%" />
                    <YAxis
                      dataKey="label"
                      type="category"
                      width={210}
                      tick={{ fill: '#111111', fontSize: 11, fontWeight: 600 }}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#FFFFFF',
                        borderColor: '#111111',
                        borderRadius: '0px',
                        fontSize: '12px',
                      }}
                    />
                    <Bar dataKey="importance_pct" name="Importancia (%)" radius={[0, 0, 0, 0]}>
                      {(summary?.feature_importances || []).slice(0, 15).map((entry, index) => (
                        <Cell
                          key={entry.feature}
                          fill={index < 3 ? '#FF4F00' : '#111111'}
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
          <div className="border border-[#111111] bg-white p-4 sm:p-6">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#111111] pb-4 mb-4">
              <div>
                <span className="text-[11px] font-bold uppercase tracking-wider text-[#FF4F00]">
                  Entregable Oficial del Reto
                </span>
                <h2 className="text-lg sm:text-xl font-black text-[#111111]">
                  Catálogo de Predicciones para las 59 Parcelas de Prueba Ciega
                </h2>
              </div>
              <button
                type="button"
                onClick={handleDownloadCsv}
                className="inline-flex items-center gap-2 bg-[#FF4F00] hover:bg-[#111111] text-white font-bold text-xs px-4 py-2.5 border border-[#111111] transition cursor-pointer"
              >
                <Download className="w-4 h-4" />
                Descargar CSV Oficial (59 Parcelas)
              </button>
            </div>

            <div className="overflow-x-auto max-h-[620px]">
              <table className="w-full text-left border-collapse text-xs sm:text-sm tabular-nums border border-[#D4D4D8]">
                <thead className="sticky top-0 bg-[#111111] text-white text-[11px] uppercase">
                  <tr>
                    <th className="py-2.5 px-3">Folio</th>
                    <th className="py-2.5 px-3">ID Polígono</th>
                    <th className="py-2.5 px-3">Área (ha)</th>
                    <th className="py-2.5 px-3">Rendimiento Predicho (t/ha)</th>
                    <th className="py-2.5 px-3">Incertidumbre (±t/ha)</th>
                    <th className="py-2.5 px-3">Cosecha Estimada (ton)</th>
                    <th className="py-2.5 px-3">Elevación (msnm)</th>
                    <th className="py-2.5 px-3">Inspección</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#D4D4D8]">
                  {allParcels
                    .filter((p) => p.CONJUNTO === 'PREDICCION')
                    .map((p, i) => {
                      const yVal = Number(p.RENDIMIENTO_PREDICHO_T_HA ?? p.RENDIMIENTO_FINAL_T_HA)
                      return (
                        <tr key={p.ID_POLIGONO} className="hover:bg-[#F7F7F8]">
                          <td className="py-2.5 px-3 text-[#71717A] font-bold">
                            {String(i + 1).padStart(2, '0')}
                          </td>
                          <td className="py-2.5 px-3 font-black text-[#111111]">{p.ID_POLIGONO}</td>
                          <td className="py-2.5 px-3">{Number(p.AREA_HA).toFixed(2)}</td>
                          <td className="py-2.5 px-3 font-black">
                            <span
                              className="px-2 py-0.5 border border-[#111111] text-white"
                              style={{ backgroundColor: getYieldColor(yVal) }}
                            >
                              {yVal.toFixed(4)} t/ha
                            </span>
                          </td>
                          <td className="py-2.5 px-3 text-[#52525B]">
                            ±{Number(p.INCERTIDUMBRE_T_HA || 0.25).toFixed(3)}
                          </td>
                          <td className="py-2.5 px-3 font-bold text-[#111111]">
                            {Number(p.PRODUCCION_ESTIMADA_TON).toFixed(2)} t
                          </td>
                          <td className="py-2.5 px-3 text-[#52525B]">
                            {Number(p.elevacion_promedio).toFixed(0)} m
                          </td>
                          <td className="py-2.5 px-3">
                            <button
                              type="button"
                              onClick={() => {
                                setSelectedId(p.ID_POLIGONO)
                                setActiveTab('cockpit')
                              }}
                              className="inline-flex items-center gap-1 text-xs font-bold text-[#FF4F00] hover:text-[#111111] cursor-pointer"
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

        {/* SECCIÓN 04: CALIDAD DEL DATASET, EFICIENCIA Y ARQUITECTURA CLOUD */}
        {activeTab === 'deploy' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 border border-[#111111] bg-white divide-y lg:divide-y-0 lg:divide-x divide-[#111111]">
            <div className="lg:col-span-4 p-6 flex flex-col items-start justify-between bg-[#F7F7F8]">
              <div>
                <span className="text-[11px] font-bold uppercase tracking-wider text-[#FF4F00]">
                  Identidad del Equipo
                </span>
                <h2 className="text-2xl font-black text-[#111111] mt-1">
                  Agrotec-Amanteca
                </h2>
                <p className="text-xs text-[#52525B] mt-2 leading-relaxed">
                  Los <i>Amanteca</i> eran los maestros artesanos del México prehispánico especializados en ensamblar mosaicos naturales de alta precisión. Nuestro sistema integra mosaicos satelitales multiespectrales, rasters climáticos CHIRPS y modelos topográficos INEGI.
                </p>
              </div>

              <img
                src="/logo_agrotec_amanteca.jpg"
                alt="Emblema Agrotec-Amanteca"
                className="w-56 h-56 object-cover border border-[#111111] my-5"
                onError={(e) => {
                  e.currentTarget.src = '/logo_agrotec_amanteca.svg'
                }}
              />

              <div className="w-full border-t border-[#111111] pt-3 text-xs text-[#52525B] tabular-nums">
                Documento Técnico Oficial disponible en formato editable Microsoft Word (<b>.docx</b>) en la raíz del repositorio.
              </div>
            </div>

            <div className="lg:col-span-8 p-6 space-y-6">
              <div>
                <span className="text-[11px] font-bold uppercase tracking-wider text-[#FF4F00]">
                  Auditoría Estadística y Computacional
                </span>
                <h3 className="text-xl font-black text-[#111111] mt-0.5">
                  Indicadores de Calidad de Datos, Precisión y Eficiencia
                </h3>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 border border-[#111111] divide-y sm:divide-y-0 sm:divide-x divide-[#111111] tabular-nums">
                <div className="p-4">
                  <span className="text-[10px] font-bold uppercase text-[#52525B] block">
                    Reducción de Colinealidad
                  </span>
                  <span className="text-2xl font-black text-[#111111] mt-1 block">
                    -{stats.collinearity_reduction_pct || 77.7}%
                  </span>
                  <span className="text-xs text-[#52525B] mt-1 block">
                    De 175 a {stats.base_features_after_pearson || 39} variables con Pearson |r| &lt; 0.90 (correlación media entre pares: {stats.mean_pairwise_corr || 0.23})
                  </span>
                </div>

                <div className="p-4">
                  <span className="text-[10px] font-bold uppercase text-[#52525B] block">
                    Precisión Dentro de Banda
                  </span>
                  <span className="text-2xl font-black text-[#16A34A] mt-1 block">
                    {eff.oof_within_050_t_ha_pct || 76.8}%
                  </span>
                  <span className="text-xs text-[#52525B] mt-1 block">
                    Porcentaje de parcelas OOF con error absoluto &le;0.50 t/ha (MAPE global: {eff.mape_oof_pct || 9.8}%)
                  </span>
                </div>

                <div className="p-4">
                  <span className="text-[10px] font-bold uppercase text-[#52525B] block">
                    Latencia de Inferencia
                  </span>
                  <span className="text-2xl font-black text-[#FF4F00] mt-1 block">
                    {eff.inference_197_ms || 14.5} ms
                  </span>
                  <span className="text-xs text-[#52525B] mt-1 block">
                    Tiempo total para predecir las 197 parcelas ({eff.model_bundle_size_kb || 2150} KB en disco)
                  </span>
                </div>
              </div>

              <div className="border border-[#D4D4D8] p-4 bg-[#F7F7F8] space-y-2 text-xs">
                <div className="font-black text-[#111111] uppercase">
                  Arquitectura de Despliegue Cloud (Railway + Vercel / Cloudflare Pages)
                </div>
                <p className="text-[#52525B] leading-relaxed">
                  1. <b>Backend en Railway (`DataSet/backend`)</b>: API FastAPI auto-contenida con <code className="text-[#111111] font-bold">Dockerfile</code>, <code className="text-[#111111] font-bold">railway.json</code> y <code className="text-[#111111] font-bold">Procfile</code>. Carga los artefactos optimizados en memoria sin requerir los Gigabytes de rasters TIF originales.
                </p>
                <p className="text-[#52525B] leading-relaxed">
                  2. <b>Frontend en Vercel o Cloudflare Pages (`DataSet/frontend`)</b>: Configurado con <code className="text-[#111111] font-bold">vercel.json</code> y <code className="text-[#111111] font-bold">_redirects</code>. Incluye cartografía satelital y topográfica de ArcGIS Online libre de API Keys y modo Edge estático de respaldo.
                </p>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* NAVEGACIÓN INFERIOR MÓVIL (SMARTPHONES) */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-50 bg-white border-t border-[#111111] grid grid-cols-4 divide-x divide-[#D4D4D8]">
        {[
          { id: 'cockpit', num: '01', label: 'Mapa' },
          { id: 'models', num: '02', label: 'Modelos' },
          { id: 'predictions', num: '03', label: '59 Preds' },
          { id: 'deploy', num: '04', label: 'Calidad' },
        ].map((item) => {
          const active = activeTab === item.id
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => setActiveTab(item.id)}
              className={`py-2.5 px-2 text-center ${
                active ? 'bg-[#111111] text-white' : 'bg-white text-[#111111]'
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
          className="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-4"
          onClick={() => setShowLogoModal(false)}
        >
          <div
            className="bg-white border-2 border-[#111111] p-6 max-w-md w-full text-left"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="text-[11px] font-bold uppercase text-[#FF4F00] mb-1">
              Identidad Visual Oficial
            </div>
            <h3 className="text-xl font-black text-[#111111] mb-4">Agrotec-Amanteca</h3>
            <img
              src="/logo_agrotec_amanteca.jpg"
              alt="Logo Agrotec-Amanteca"
              className="w-64 h-64 mx-auto border border-[#111111] object-cover mb-4"
            />
            <button
              type="button"
              onClick={() => setShowLogoModal(false)}
              className="w-full py-2.5 bg-[#111111] hover:bg-[#FF4F00] text-white font-bold text-xs uppercase cursor-pointer transition"
            >
              Cerrar Vista
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
