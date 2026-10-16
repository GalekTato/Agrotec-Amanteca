"""
main.py
API Backend en FastAPI para Reto AgroCebada FIRA 2026 - Equipo Agrotec-Amanteca (V4).
Optimizado con Lifespan Events, Pydantic V2 (0 DeprecationWarnings) y paridad 100%
con las predicciones reales del Ensemble Agrotec (agro_core.py + sensibilidad_simulador.json).
"""

from contextlib import asynccontextmanager
import json
import os
import sys
from pathlib import Path
from typing import Dict, Optional

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from agro_core import apply_scenario_df

ARTIFACTS_DIR = BASE_DIR / "artifacts"

# Cache en memoria con recarga automática si los artefactos en disco se actualizan
STATE = {
    "geojson": None,
    "summary": None,
    "sensitivity": None,
    "model_bundle": None,
    "features_by_id": {},
    "artifacts_mtime": 0.0,
}


def load_artifacts(force: bool = False):
    geojson_path = ARTIFACTS_DIR / "parcelas_197_dashboard.geojson"
    summary_path = ARTIFACTS_DIR / "metrics_summary.json"
    sim_path = ARTIFACTS_DIR / "sensibilidad_simulador.json"
    model_path = ARTIFACTS_DIR / "best_model.joblib"

    current_mtime = 0.0
    for p in (geojson_path, summary_path, sim_path, model_path):
        if p.exists():
            current_mtime = max(current_mtime, p.stat().st_mtime)

    if not force and STATE["geojson"] is not None and current_mtime <= STATE["artifacts_mtime"]:
        return

    if geojson_path.exists():
        STATE["geojson"] = json.loads(geojson_path.read_text(encoding="utf-8"))
        STATE["features_by_id"] = {
            feat["properties"]["ID_POLIGONO"]: feat for feat in STATE["geojson"].get("features", [])
        }
    if summary_path.exists():
        STATE["summary"] = json.loads(summary_path.read_text(encoding="utf-8"))
    if sim_path.exists():
        STATE["sensitivity"] = json.loads(sim_path.read_text(encoding="utf-8"))
    if model_path.exists():
        STATE["model_bundle"] = joblib.load(model_path)

    STATE["artifacts_mtime"] = current_mtime


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_artifacts(force=True)
    yield


app = FastAPI(
    title="Agrotec-Amanteca API | Reto AgroCebada FIRA 2026",
    description=(
        "API Geoespacial y Motor de Inferencia Agronómica V4 para la predicción de rendimiento "
        "de cebada (t/ha) en 197 parcelas (138 entrenamiento, 59 predicción ciega) con "
        "Intervalos de Predicción Conformal al 80% y Simulador respaldado 100% por el modelo."
    ),
    version="4.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SimulationRequest(BaseModel):
    id_poligono: str = Field(
        ...,
        description="ID de la parcela (AGC_001 a AGC_197)",
        json_schema_extra={"example": "AGC_002"},
    )
    ndvi_delta_pct: float = Field(
        0.0,
        ge=-40.0,
        le=40.0,
        description="Variación porcentual en vigor satelital NDVI/EVI",
    )
    prec_delta_pct: float = Field(
        0.0,
        ge=-50.0,
        le=50.0,
        description="Variación porcentual en precipitación acumulada CHIRPS",
    )
    tmax_delta_c: float = Field(
        0.0,
        ge=-5.0,
        le=5.0,
        description="Cambio absoluto en Temperatura Máxima/Mínima (°C)",
    )
    custom_overrides: Optional[Dict[str, float]] = Field(
        default=None,
        description="Valores personalizados opcionales por nombre de columna",
    )


def _lookup_or_interp(delta_map: Dict[str, float], val: float, is_float_key: bool = False) -> Optional[float]:
    if not delta_map:
        return None
    key_exact = f"{float(val):.1f}" if is_float_key else str(int(round(val)))
    if not is_float_key and abs(val - round(val)) < 1e-6 and key_exact in delta_map:
        return float(delta_map[key_exact])
    if is_float_key and key_exact in delta_map:
        return float(delta_map[key_exact])
    # Interpolación lineal sobre la malla precalculada del modelo
    pts = sorted((float(k), float(v)) for k, v in delta_map.items())
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    if val <= xs[0]:
        return ys[0]
    if val >= xs[-1]:
        return ys[-1]
    return float(np.interp(val, xs, ys))


@app.get("/")
def root():
    return {
        "service": "Agrotec-Amanteca Backend API",
        "challenge": "Reto AgroCebada FIRA 2026",
        "version": "4.0.0",
        "status": "online",
        "docs": "/docs",
        "endpoints": [
            "/api/health",
            "/api/summary",
            "/api/parcelas",
            "/api/sensibilidad",
            "/api/simular",
            "/api/export/csv",
        ],
    }


@app.get("/api/health")
def health_check():
    load_artifacts()
    return {
        "status": "ok",
        "artifacts_loaded": STATE["geojson"] is not None and STATE["summary"] is not None,
        "sensitivity_loaded": STATE["sensitivity"] is not None,
        "model_loaded": STATE["model_bundle"] is not None,
        "total_parcelas": len(STATE["features_by_id"]),
    }


@app.get("/api/summary")
def get_summary():
    load_artifacts()
    if STATE["summary"] is None:
        raise HTTPException(status_code=503, detail="Artefactos de resumen aún no disponibles.")
    return JSONResponse(content=STATE["summary"])


@app.get("/api/sensibilidad")
def get_sensibilidad():
    load_artifacts()
    if STATE["sensitivity"] is None:
        raise HTTPException(status_code=503, detail="Superficie de sensibilidad del modelo aún no disponible.")
    return JSONResponse(content=STATE["sensitivity"])


@app.get("/api/parcelas")
def get_parcelas(conjunto: Optional[str] = Query(None, description="Filtrar por ENTRENAMIENTO o PREDICCION")):
    load_artifacts()
    if STATE["geojson"] is None:
        raise HTTPException(status_code=503, detail="GeoJSON de parcelas no encontrado.")

    if not conjunto or conjunto.upper() == "TODAS":
        return JSONResponse(content=STATE["geojson"])

    conjunto_upper = conjunto.upper()
    filtered_features = [
        f
        for f in STATE["geojson"].get("features", [])
        if str(f.get("properties", {}).get("CONJUNTO", "")).upper() == conjunto_upper
    ]
    return JSONResponse(content={"type": "FeatureCollection", "features": filtered_features})


@app.get("/api/parcelas/{id_poligono}")
def get_parcela_detail(id_poligono: str):
    load_artifacts()
    feat = STATE["features_by_id"].get(id_poligono.upper())
    if not feat:
        raise HTTPException(status_code=404, detail=f"Parcela {id_poligono} no encontrada.")
    return JSONResponse(content=feat)


@app.post("/api/simular")
def simular_escenario(req: SimulationRequest):
    load_artifacts()
    if not STATE["features_by_id"] or STATE["model_bundle"] is None:
        raise HTTPException(status_code=503, detail="Modelo o artefactos no cargados.")

    parcela_id = req.id_poligono.upper()
    feat = STATE["features_by_id"].get(parcela_id)
    if not feat:
        raise HTTPException(status_code=404, detail=f"Parcela {parcela_id} no encontrada.")

    props = feat["properties"]
    bundle = STATE["model_bundle"]
    feature_cols = bundle["feature_cols"]
    feature_means = bundle.get("feature_means", {})
    model = bundle["model"]

    row_dict = {}
    for k, v in props.items():
        if isinstance(v, (int, float)) and v is not None and not np.isnan(v):
            row_dict[k] = float(v)
    for col in feature_cols:
        if col not in row_dict:
            row_dict[col] = float(feature_means.get(col, 0.0))

    base_df = pd.DataFrame([row_dict])
    for col in feature_cols:
        if col not in base_df.columns:
            base_df[col] = float(feature_means.get(col, 0.0))

    pred_base = float(props.get("RENDIMIENTO_PREDICHO_T_HA", model.predict(base_df[feature_cols])[0]))
    half_width_80 = float(props.get("INCERTIDUMBRE_T_HA", 0.564))

    # Si no hay overrides manuales y existe la superficie precalculada del modelo real,
    # evaluamos los efectos marginales exactos del modelo (paridad 100% con el Frontend estático).
    sim_parcel = (STATE["sensitivity"] or {}).get("parcels", {}).get(parcela_id)
    if not req.custom_overrides and sim_parcel is not None:
        pred_base = float(sim_parcel.get("base_yield_t_ha", pred_base))
        d_ndvi = _lookup_or_interp(sim_parcel.get("ndvi_deltas", {}), req.ndvi_delta_pct, is_float_key=False) or 0.0
        d_prec = _lookup_or_interp(sim_parcel.get("prec_deltas", {}), req.prec_delta_pct, is_float_key=False) or 0.0
        d_tmax = _lookup_or_interp(sim_parcel.get("tmax_deltas", {}), req.tmax_delta_c, is_float_key=True) or 0.0
        delta_t_ha = float(d_ndvi + d_prec + d_tmax)
        pred_sim = float(np.clip(pred_base + delta_t_ha, 1.0, 6.5))
    else:
        sim_df = apply_scenario_df(
            base_df,
            ndvi_delta_pct=req.ndvi_delta_pct,
            prec_delta_pct=req.prec_delta_pct,
            tmax_delta_c=req.tmax_delta_c,
        )
        if req.custom_overrides:
            for k, v in req.custom_overrides.items():
                if k in sim_df.columns:
                    sim_df[k] = float(v)
        for col in feature_cols:
            if col not in sim_df.columns:
                sim_df[col] = float(feature_means.get(col, 0.0))
        pred_sim = float(np.clip(model.predict(sim_df[feature_cols])[0], 1.0, 6.5))
        d_ndvi = 0.0
        d_prec = 0.0
        d_tmax = 0.0

    if req.ndvi_delta_pct == 0.0 and req.prec_delta_pct == 0.0 and req.tmax_delta_c == 0.0 and not req.custom_overrides:
        pred_sim = pred_base

    delta_t_ha = pred_sim - pred_base
    delta_pct = (delta_t_ha / pred_base * 100.0) if pred_base > 0 else 0.0
    area_ha = float(props.get("AREA_HA", 1.0))

    return {
        "id_poligono": parcela_id,
        "conjunto": props.get("CONJUNTO"),
        "area_ha": round(area_ha, 2),
        "rendimiento_real_t_ha": props.get("RENDIMIENTO_T_HA"),
        "rendimiento_base_modelo_t_ha": round(pred_base, 4),
        "rendimiento_simulado_t_ha": round(pred_sim, 4),
        "intervalo_80_inf_t_ha": round(max(1.0, pred_sim - half_width_80), 4),
        "intervalo_80_sup_t_ha": round(pred_sim + half_width_80, 4),
        "incertidumbre_80_t_ha": round(half_width_80, 4),
        "delta_t_ha": round(delta_t_ha, 4),
        "delta_pct": round(delta_pct, 2),
        "desglose_modelo_t_ha": {
            "efecto_ndvi_t_ha": round(float(d_ndvi), 4),
            "efecto_precipitacion_t_ha": round(float(d_prec), 4),
            "efecto_temperatura_t_ha": round(float(d_tmax), 4),
        },
        "produccion_base_ton": round(pred_base * area_ha, 2),
        "produccion_simulada_ton": round(pred_sim * area_ha, 2),
        "parametros_aplicados": {
            "ndvi_delta_pct": req.ndvi_delta_pct,
            "prec_delta_pct": req.prec_delta_pct,
            "tmax_delta_c": req.tmax_delta_c,
        },
    }


@app.get("/api/export/csv")
def export_predictions_csv():
    csv_path = ARTIFACTS_DIR / "predicciones_59_parcelas.csv"
    if not csv_path.exists():
        raise HTTPException(status_code=404, detail="Archivo de predicciones no encontrado.")
    return FileResponse(
        path=csv_path,
        media_type="text/csv",
        filename="Predicciones_59_Parcelas_Agrotec_Amanteca_FIRA2026.csv",
    )


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
