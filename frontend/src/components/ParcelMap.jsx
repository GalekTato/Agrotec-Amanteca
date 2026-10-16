import React, { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import { Maximize2 } from 'lucide-react'

export function getYieldColor(yieldVal) {
  if (yieldVal == null || Number.isNaN(Number(yieldVal))) return '#71717A'
  const y = Number(yieldVal)
  if (y < 3.1) return '#DC2626' // Bajo (< 3.1 t/ha)
  if (y < 3.6) return '#EA580C' // Medio-Bajo (3.1 - 3.6 t/ha)
  if (y < 4.1) return '#CA8A04' // Medio (3.6 - 4.1 t/ha)
  if (y < 4.45) return '#16A34A' // Alto (4.1 - 4.45 t/ha)
  return '#047857' // Élite (>= 4.45 t/ha)
}

// Capas 100% libres de API Key (Servidores Oficiales ArcGIS Online)
const TILE_LAYERS = {
  satellite: {
    label: 'Satélite Óptico (Esri)',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
  },
  tactical: {
    label: 'Cartografía Técnica (Esri Dark Gray)',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}',
  },
  topo: {
    label: 'Topográfico INEGI / Esri',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}',
  },
}

export default function ParcelMap({
  geojson,
  selectedId,
  onSelectParcel,
  filterConjunto,
}) {
  const mapContainerRef = useRef(null)
  const mapInstanceRef = useRef(null)
  const geoJsonLayerRef = useRef(null)
  const tileLayerRef = useRef(null)
  const [mapStyle, setMapStyle] = useState('satellite')

  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return

    const map = L.map(mapContainerRef.current, {
      center: [19.75, -98.55],
      zoom: 10,
      zoomControl: false,
      attributionControl: false,
    })

    L.control.zoom({ position: 'bottomright' }).addTo(map)

    const baseLayer = L.tileLayer(TILE_LAYERS.satellite.url, {
      maxZoom: 19,
    }).addTo(map)

    tileLayerRef.current = baseLayer
    mapInstanceRef.current = map

    // Asegurar que Leaflet recalcule su tamaño exacto dentro del contenedor flex/grid
    setTimeout(() => {
      map.invalidateSize()
    }, 100)

    return () => {
      map.remove()
      mapInstanceRef.current = null
    }
  }, [])

  useEffect(() => {
    const map = mapInstanceRef.current
    if (!map || !tileLayerRef.current) return

    map.removeLayer(tileLayerRef.current)
    const layerConfig = TILE_LAYERS[mapStyle] || TILE_LAYERS.satellite
    tileLayerRef.current = L.tileLayer(layerConfig.url, { maxZoom: 19 }).addTo(map)
    tileLayerRef.current.bringToBack()
  }, [mapStyle])

  useEffect(() => {
    const map = mapInstanceRef.current
    if (!map || !geojson || !geojson.features) return

    if (geoJsonLayerRef.current) {
      map.removeLayer(geoJsonLayerRef.current)
    }

    const filteredFeatures = geojson.features.filter((f) => {
      if (!filterConjunto || filterConjunto === 'TODAS') return true
      return f.properties?.CONJUNTO === filterConjunto
    })

    if (filteredFeatures.length === 0) return

    const layer = L.geoJSON(
      { type: 'FeatureCollection', features: filteredFeatures },
      {
        style: (feature) => {
          const props = feature.properties || {}
          const isSelected = props.ID_POLIGONO === selectedId
          const isPred = props.CONJUNTO === 'PREDICCION'
          const yVal = props.RENDIMIENTO_FINAL_T_HA ?? props.RENDIMIENTO_T_HA
          const fillColor = getYieldColor(yVal)

          return {
            color: isSelected ? '#FF4F00' : isPred ? '#38BDF8' : '#FFFFFF',
            weight: isSelected ? 3.5 : isPred ? 2.2 : 1.3,
            opacity: 1,
            fillColor,
            fillOpacity: isSelected ? 0.88 : 0.68,
            dashArray: isPred && !isSelected ? '4 2' : null,
          }
        },
        onEachFeature: (feature, lyr) => {
          const p = feature.properties || {}
          const yVal = Number(p.RENDIMIENTO_FINAL_T_HA || 0).toFixed(2)
          const setLabel =
            p.CONJUNTO === 'PREDICCION' ? 'PREDICCIÓN CIEGA (59)' : 'ENTRENAMIENTO (138)'

          const inf80 = Number(p.INTERVALO_80_INF_T_HA || (Number(yVal) - Number(p.INCERTIDUMBRE_T_HA || 0.56))).toFixed(2)
          const sup80 = Number(p.INTERVALO_80_SUP_T_HA || (Number(yVal) + Number(p.INCERTIDUMBRE_T_HA || 0.56))).toFixed(2)
          const half80 = Number(p.INCERTIDUMBRE_T_HA || 0.56).toFixed(2)

          lyr.bindTooltip(
            `<div>
              <div style="font-weight:800;font-size:12px;border-bottom:1px solid var(--rule-hairline);padding-bottom:3px;margin-bottom:4px;">
                ${p.ID_POLIGONO} · <span style="color:#FF4F00;">${setLabel}</span>
              </div>
              <div>Rendimiento: <b>${yVal} t/ha</b> (Int. 80%: [${inf80}–${sup80}], ±${half80})</div>
              <div>Área: <b>${Number(p.AREA_HA || 0).toFixed(2)} ha</b> · Cosecha: <b>${Number(p.PRODUCCION_ESTIMADA_TON || 0).toFixed(1)} t</b></div>
            </div>`,
            { sticky: true, className: 'swiss-tooltip' }
          )

          lyr.on('click', () => {
            onSelectParcel(p.ID_POLIGONO)
          })
        },
      }
    ).addTo(map)

    geoJsonLayerRef.current = layer

    if (selectedId) {
      let targetSubLayer = null
      layer.eachLayer((sub) => {
        if (sub.feature?.properties?.ID_POLIGONO === selectedId) {
          targetSubLayer = sub
        }
      })
      if (targetSubLayer) {
        map.flyToBounds(targetSubLayer.getBounds(), {
          padding: [55, 55],
          maxZoom: 16,
          duration: 0.65,
        })
      }
    } else {
      const bounds = layer.getBounds()
      if (bounds.isValid()) {
        map.fitBounds(bounds, { padding: [24, 24] })
      }
    }
  }, [geojson, selectedId, filterConjunto, onSelectParcel])

  const handleResetBounds = () => {
    const map = mapInstanceRef.current
    const layer = geoJsonLayerRef.current
    if (map && layer && layer.getBounds().isValid()) {
      map.fitBounds(layer.getBounds(), { padding: [24, 24] })
    }
  }

  return (
    <div className="relative isolate z-0 w-full h-full overflow-hidden border border-[var(--rule-strong)] bg-[var(--surface-subtle)]">
      <div ref={mapContainerRef} className="w-full h-full z-0" />

      {/* Selector de Cartografía Libre de API Keys (aislado dentro del contexto z-0 del mapa) */}
      <div className="absolute top-3 left-3 right-3 z-[400] flex flex-wrap items-center justify-between gap-2 pointer-events-none">
        <div className="pointer-events-auto inline-flex bg-[var(--surface-panel)] border border-[var(--rule-strong)] divide-x divide-[var(--rule-strong)]">
          {Object.entries(TILE_LAYERS).map(([key, cfg]) => (
            <button
              key={key}
              type="button"
              onClick={() => setMapStyle(key)}
              className={`px-2.5 sm:px-3 py-1.5 text-[11px] font-bold tracking-tight transition cursor-pointer ${
                mapStyle === key
                  ? 'bg-[#FF4F00] text-white'
                  : 'bg-[var(--surface-panel)] text-[var(--ink-primary)] hover:bg-[var(--surface-subtle)]'
              }`}
            >
              {cfg.label}
            </button>
          ))}
        </div>

        <button
          type="button"
          onClick={handleResetBounds}
          className="pointer-events-auto flex items-center gap-1.5 bg-[var(--surface-panel)] hover:bg-[#FF4F00] hover:text-white border border-[var(--rule-strong)] px-3 py-1.5 text-[11px] font-bold text-[var(--ink-primary)] transition cursor-pointer"
        >
          <Maximize2 className="w-3.5 h-3.5" />
          <span>Encuadrar 197 Parcelas</span>
        </button>
      </div>

      {/* Escala Cartográfica de Rendimiento (t/ha) */}
      <div className="absolute bottom-3 left-3 z-[400] bg-[var(--surface-panel)] border border-[var(--rule-strong)] px-3 py-2 text-[11px] text-[var(--ink-primary)] max-w-[86%] tabular-nums">
        <div className="font-bold border-b border-[var(--rule-hairline)] pb-1 mb-1.5 flex items-center justify-between gap-4">
          <span>Escala de Rendimiento (t/ha)</span>
          <span className="text-[#FF4F00] font-bold">Trazo Punteado = 59 Ciegas</span>
        </div>
        <div className="flex flex-wrap items-center gap-3 font-medium">
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 bg-[#DC2626] border border-[var(--rule-strong)] inline-block" /> &lt;3.1
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 bg-[#EA580C] border border-[var(--rule-strong)] inline-block" /> 3.1–3.6
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 bg-[#CA8A04] border border-[var(--rule-strong)] inline-block" /> 3.6–4.1
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 bg-[#16A34A] border border-[var(--rule-strong)] inline-block" /> 4.1–4.45
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 bg-[#047857] border border-[var(--rule-strong)] inline-block" /> &ge;4.45
          </span>
        </div>
      </div>
    </div>
  )
}
