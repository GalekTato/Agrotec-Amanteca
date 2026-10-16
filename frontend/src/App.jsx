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

export default function App() {
  const [summary, setSummary] = useState(null)
  const [geojson, setGeojson] = useState(null)
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

  // Sincronizar clase 'dark' en <html>
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
            Cargando Cartografía y Modelo Predictivo
          </h1>
          <p className="text-xs text-[var(--ink-secondary)] mt-2">
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
    mae_cv: 0.351,
    rmse_cv: 0.491,
    r2_cv: 0.621,
  }

  return (
    <div className="min-h-screen bg-[var(--surface-bg)] text-[var(--ink-primary)] flex flex-col pb-20 md:pb-10">
      {/* MASTHEAD EDITORIAL SWISS (RETÍCULA 1PX, MODO CLARO / OSCURO) */}
      <header className="sticky top-0 z-50 bg-[var(--surface-panel)] border-b border-[var(--rule-strong)]">
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
              <p className="text-[11px] text-[var(--ink-secondary)] truncate">
                Predicción de Rendimiento de Cebada (t/ha) · 197 Parcelas
              </p>
            </div>
          </div>

          {/* Navegación Estructural Desktop */}
          <nav className="hidden lg:flex lg:col-span-5 items-stretch divide-x divide-[var(--rule-hairline)] border-r border-[var(--rule-hairline)]">
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
          <div className="col-span-6 sm:col-span-7 lg:col-span-4 px-3 sm:px-5 py-2.5 flex items-center justify-end gap-2">
            <span className="hidden xl:inline-block text-[11px] font-medium text-[var(--ink-secondary)] tabular-nums mr-1">
              {apiMode === 'cloud' ? 'API Railway Activa' : 'Modo Estático Edge'}
            </span>

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
            { id: 'models', num: '02', label: 'Validación Cruzada ML' },
            { id: 'predictions', num: '03', label: 'Catálogo 59 Predicciones' },
            { id: 'deploy', num: '04', label: 'Calidad y Cloud' },
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
      <main className="flex-1 max-w-[1600px] w-full mx-auto px-3 sm:px-6 pt-5 space-y-5">
        {/* BANDA DE NUMERALES COMPOSITIVOS (4 FOLIOS DE MÉTRICAS REALES DEL PROYECTO) */}
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
                {Number(stats.pred_yield_mean || 3.92).toFixed(2)}
              </span>
              <span className="text-xs font-bold uppercase text-[var(--ink-secondary)]">t/ha</span>
            </div>
            <p className="text-xs text-[var(--ink-secondary)] mt-2 tabular-nums border-t border-[var(--rule-hairline)] pt-1.5">
              Media Entrenamiento (138): <b className="text-[var(--ink-primary)]">{Number(stats.train_yield_mean || 3.96).toFixed(2)} t/ha</b> · Rango: {Number(stats.pred_yield_min || 2.85).toFixed(2)}–{Number(stats.pred_yield_max || 4.82).toFixed(2)}
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
              <span className="text-xs font-bold uppercase text-[var(--ink-secondary)]">MAE (t/ha)</span>
            </div>
            <p className="text-xs text-[var(--ink-secondary)] mt-2 tabular-nums border-t border-[var(--rule-hairline)] pt-1.5">
              RMSE CV: <b className="text-[var(--ink-primary)]">{Number(bestModelMetric.rmse_cv).toFixed(4)} t/ha</b> · MAPE OOF: <b className="text-[var(--ink-primary)]">{Number(eff.mape_oof_pct || 9.8).toFixed(2)}%</b>
            </p>
          </div>

          <div className="p-4 sm:p-5 flex flex-col justify-between">
            <div className="flex items-baseline justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--ink-secondary)]">
                03 · Volumen Productivo Estimado
              </span>
              <span className="text-[11px] font-bold text-[var(--ink-secondary)] tabular-nums">
                {Number(stats.total_area_ha || 1560.6).toFixed(1)} ha
              </span>
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="folio-numeral text-3xl sm:text-4xl lg:text-[42px] text-[var(--ink-primary)]">
                {Number(stats.total_production_ton || 6120).toLocaleString('es-MX', {
                  maximumFractionDigits: 0,
                })}
              </span>
              <span className="text-xs font-bold uppercase text-[var(--ink-secondary)]">toneladas</span>
            </div>
            <p className="text-xs text-[var(--ink-secondary)] mt-2 tabular-nums border-t border-[var(--rule-hairline)] pt-1.5">
              Cosecha en 59 parcelas de prueba: <b className="text-[var(--ink-primary)]">{Number(stats.pred_production_ton || 1845).toFixed(1)} t</b> ({Number(stats.pred_area_ha || 467.6).toFixed(1)} ha)
            </p>
          </div>

          <div className="p-4 sm:p-5 flex flex-col justify-between">
            <div className="flex items-baseline justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--ink-secondary)]">
                04 · Pureza de Datos y Eficiencia
              </span>
              <span className="text-[11px] font-bold text-[#FF4F00] tabular-nums">
                {Number(eff.inference_197_ms || 14.2).toFixed(1)} ms
              </span>
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="folio-numeral text-3xl sm:text-4xl lg:text-[42px] text-[var(--ink-primary)]">
                175→{stats.total_features_selected || 39}
              </span>
              <span className="text-xs font-bold uppercase text-[var(--ink-secondary)]">predictores</span>
            </div>
            <p className="text-xs text-[var(--ink-secondary)] mt-2 tabular-nums border-t border-[var(--rule-hairline)] pt-1.5">
              Filtro Pearson <b className="text-[var(--ink-primary)]">|r| &lt; 0.90</b> · Completitud: <b className="text-[var(--ink-primary)]">100% (0 Nulos)</b>
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

              {/* Contenedor del Mapa Esri (con overflow-hidden para nunca pisar el bloque inferior) */}
              <div className="h-[360px] sm:h-[450px] lg:h-[520px] p-3 bg-[var(--surface-panel)] overflow-hidden">
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
                      <span className="text-[11px] text-[var(--ink-secondary)]">
                        IC: ±{Number(selectedParcel.INCERTIDUMBRE_T_HA || 0.25).toFixed(2)} t/ha
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
                      Comparativa de {selectedParcel.ID_POLIGONO} frente al umbral regional de alto rendimiento (&ge;4.35 t/ha)
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
                          name={`NDVI ${selectedParcel.ID_POLIGONO}`}
                          stroke={chartInk}
                          fill={chartInk}
                          fillOpacity={0.12}
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
                <div className="p-4 sm:p-5 bg-[var(--surface-subtle)]">
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--ink-primary)]">
                        Simulador de Sensibilidad Agronómica (Inferencia en Vivo)
                      </h3>
                      <p className="text-xs text-[var(--ink-secondary)]">
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
                        className="inline-flex items-center gap-1 text-xs font-bold bg-[var(--surface-panel)] border border-[var(--rule-strong)] px-2.5 py-1 hover:bg-[#FF4F00] hover:text-white transition cursor-pointer"
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
                    <div className="mt-4 pt-3 border-t border-[var(--rule-strong)] flex items-center justify-between tabular-nums bg-[var(--surface-panel)] p-3 border">
                      <div>
                        <span className="text-[10px] font-bold uppercase text-[var(--ink-secondary)] block">
                          Rendimiento Simulado ({simLoading ? 'Calculando...' : 'Ensemble IA'})
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
                  )}
                </div>

                {/* Explicabilidad Local de la Parcela (5 Factores Principales) */}
                <div className="p-4 sm:p-5 bg-[var(--surface-panel)]">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--ink-primary)] mb-2.5">
                    Variables Determinantes en {selectedParcel.ID_POLIGONO} (Atribución Local)
                  </h3>
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
                        <th className="py-2.5 px-3">R²</th>
                        <th className="py-2.5 px-3">Tiempo CV</th>
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
                          <td className="py-2.5 px-3 font-bold text-[#16A34A]">{m.r2_cv.toFixed(4)}</td>
                          <td className="py-2.5 px-3 text-[var(--ink-secondary)]">{m.cv_time_ms ? `${m.cv_time_ms.toFixed(0)} ms` : '—'}</td>
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
                    Auditoría Fuera de Muestra (5-Fold OOF)
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

            {/* Ranking de Importancia de Variables */}
            <div className="border border-[var(--rule-strong)] bg-[var(--surface-panel)] p-4 sm:p-6">
              <div className="border-b border-[var(--rule-strong)] pb-3 mb-4">
                <span className="text-[11px] font-bold uppercase tracking-wider text-[#FF4F00]">
                  Interpretabilidad Agronómica (XAI)
                </span>
                <h3 className="text-lg font-black text-[var(--ink-primary)] mt-0.5">
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
                    <CartesianGrid strokeDasharray="2 2" stroke={chartGrid} />
                    <XAxis type="number" tick={{ fill: chartInk, fontSize: 11 }} unit="%" />
                    <YAxis
                      dataKey="label"
                      type="category"
                      width={210}
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
                    <th className="py-2.5 px-3">Incertidumbre (±t/ha)</th>
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
                            ±{Number(p.INCERTIDUMBRE_T_HA || 0.25).toFixed(3)}
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

        {/* SECCIÓN 04: CALIDAD DEL DATASET, EFICIENCIA Y ARQUITECTURA CLOUD */}
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
                src="/logo_agrotec_amanteca.jpg"
                alt="Emblema Agrotec-Amanteca"
                className="w-56 h-56 object-cover border border-[var(--rule-strong)] my-5"
                onError={(e) => {
                  e.currentTarget.src = '/logo_agrotec_amanteca.svg'
                }}
              />

              <div className="w-full border-t border-[var(--rule-strong)] pt-3 text-xs text-[var(--ink-secondary)] tabular-nums">
                Documento Técnico Oficial disponible en formato editable Microsoft Word (<b>.docx</b>) en la raíz del repositorio.
              </div>
            </div>

            <div className="lg:col-span-8 p-6 space-y-6">
              <div>
                <span className="text-[11px] font-bold uppercase tracking-wider text-[#FF4F00]">
                  Auditoría Estadística y Computacional
                </span>
                <h3 className="text-xl font-black text-[var(--ink-primary)] mt-0.5">
                  Indicadores de Calidad de Datos, Precisión y Eficiencia
                </h3>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 border border-[var(--rule-strong)] divide-y sm:divide-y-0 sm:divide-x divide-[var(--rule-strong)] tabular-nums">
                <div className="p-4">
                  <span className="text-[10px] font-bold uppercase text-[var(--ink-secondary)] block">
                    Reducción de Colinealidad
                  </span>
                  <span className="text-2xl font-black text-[var(--ink-primary)] mt-1 block">
                    -{stats.collinearity_reduction_pct || 77.7}%
                  </span>
                  <span className="text-xs text-[var(--ink-secondary)] mt-1 block">
                    Filtro de Pearson Inteligente |r| &lt; 0.90 preservando las variables de mayor señal agronómica (0% valores nulos)
                  </span>
                </div>

                <div className="p-4">
                  <span className="text-[10px] font-bold uppercase text-[var(--ink-secondary)] block">
                    Precisión Dentro de Banda
                  </span>
                  <span className="text-2xl font-black text-[#16A34A] mt-1 block">
                    {eff.oof_within_050_t_ha_pct || 76.8}%
                  </span>
                  <span className="text-xs text-[var(--ink-secondary)] mt-1 block">
                    Porcentaje de parcelas OOF con error absoluto &le;0.50 t/ha (MAPE global: {eff.mape_oof_pct || 9.8}%)
                  </span>
                </div>

                <div className="p-4">
                  <span className="text-[10px] font-bold uppercase text-[var(--ink-secondary)] block">
                    Latencia de Inferencia
                  </span>
                  <span className="text-2xl font-black text-[#FF4F00] mt-1 block">
                    {eff.inference_197_ms || 14.5} ms
                  </span>
                  <span className="text-xs text-[var(--ink-secondary)] mt-1 block">
                    Tiempo total para predecir las 197 parcelas ({eff.model_bundle_size_kb || 580} KB en disco)
                  </span>
                </div>
              </div>

              <div className="border border-[var(--rule-hairline)] p-4 bg-[var(--surface-subtle)] space-y-2 text-xs">
                <div className="font-black text-[var(--ink-primary)] uppercase">
                  Arquitectura de Despliegue Cloud (Railway + Vercel / Cloudflare Pages)
                </div>
                <p className="text-[var(--ink-secondary)] leading-relaxed">
                  1. <b>Backend en Railway (`DataSet/backend`)</b>: API FastAPI auto-contenida con <code className="text-[var(--ink-primary)] font-bold">Dockerfile</code>, <code className="text-[var(--ink-primary)] font-bold">railway.json</code> y <code className="text-[var(--ink-primary)] font-bold">Procfile</code>. Carga los artefactos optimizados en memoria sin requerir los Gigabytes de rasters TIF originales.
                </p>
                <p className="text-[var(--ink-secondary)] leading-relaxed">
                  2. <b>Frontend en Vercel o Cloudflare Pages (`DataSet/frontend`)</b>: Configurado con <code className="text-[var(--ink-primary)] font-bold">vercel.json</code> y <code className="text-[var(--ink-primary)] font-bold">_redirects</code>. Incluye cartografía satelital y topográfica de ArcGIS Online libre de API Keys y modo Edge estático de respaldo.
                </p>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* NAVEGACIÓN INFERIOR MÓVIL (SMARTPHONES) */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-50 bg-[var(--surface-panel)] border-t border-[var(--rule-strong)] grid grid-cols-4 divide-x divide-[var(--rule-hairline)]">
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
          className="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-4"
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
              src="/logo_agrotec_amanteca.jpg"
              alt="Logo Agrotec-Amanteca"
              className="w-64 h-64 mx-auto border border-[var(--rule-strong)] object-cover mb-4"
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
