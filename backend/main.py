"""
main.py
API Backend en FastAPI para Reto AgroCebada FIRA 2026 - Equipo Agrotec-Amanteca.
Optimizado con Lifespan Events y Pydantic V2 (0 DeprecationWarnings).
"""

from contextlib import asynccontextmanager
import json
import os
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
ARTIFACTS_DIR = BASE_DIR / "artifacts"

# Cache en memoria con recarga automática si los artefactos en disco se actualizan
STATE = {
    "geojson": None,
    "summary": None,
    "model_bundle": None,
    "features_by_id": {},
    "artifacts_mtime": 0.0,
}


def load_artifacts(force: bool = False):
    geojson_path = ARTIFACTS_DIR / "parcelas_197_dashboard.geojson"
    summary_path = ARTIFACTS_DIR / "metrics_summary.json"
    model_path = ARTIFACTS_DIR / "best_model.joblib"

    current_mtime = 0.0
    for p in (geojson_path, summary_path, model_path):
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
        "API Geoespacial y Motor de Inferencia Agronómica V3 para la predicción de rendimiento "
        "de cebada (t/ha) en 197 parcelas (138 entrenamiento, 59 predicción ciega)."
    ),
    version="3.1.0",
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


@app.get("/")
def root():
    return {
        "service": "Agrotec-Amanteca Backend API",
        "challenge": "Reto AgroCebada FIRA 2026",
        "version": "3.1.0",
        "status": "online",
        "docs": "/docs",
        "endpoints": ["/api/health", "/api/summary", "/api/parcelas", "/api/simular", "/api/export/csv"],
    }


@app.get("/api/health")
def health_check():
    load_artifacts()
    return {
        "status": "ok",
        "artifacts_loaded": STATE["geojson"] is not None and STATE["summary"] is not None,
        "model_loaded": STATE["model_bundle"] is not None,
        "total_parcelas": len(STATE["features_by_id"]),
    }


@app.get("/api/summary")
def get_summary():
    load_artifacts()
    if STATE["summary"] is None:
        raise HTTPException(status_code=503, detail="Artefactos de resumen aún no disponibles.")
    return JSONResponse(content=STATE["summary"])


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


def _recompute_engineered(d_frame: pd.DataFrame) -> None:
    def _col(name: str, default: float = 0.0) -> pd.Series:
        if name in d_frame.columns:
            return d_frame[name]
        return pd.Series([default] * len(d_frame), index=d_frame.index, dtype=float)

    d_frame["ndvi_auc_verano"] = (
        0.5 * _col("ndvi_promedio_mes_5", 0.25)
        + _col("ndvi_promedio_mes_6", 0.35)
        + _col("ndvi_promedio_mes_7", 0.50)
        + _col("ndvi_promedio_mes_8", 0.60)
        + _col("ndvi_promedio_mes_9", 0.52)
        + 0.5 * _col("ndvi_promedio_mes_10", 0.38)
    )
    d_frame["ndvi_tasa_vegetativa"] = _col("ndvi_promedio_mes_8", 0.60) - _col("ndvi_promedio_mes_5", 0.25)
    d_frame["ndvi_caida_madurez"] = _col("ndvi_promedio_mes_8", 0.60) - _col("ndvi_promedio_mes_10", 0.38)
    prec_clave = _col("prec_2022_07", 95.0) + _col("prec_2023_05", 48.0) + _col("prec_2022_05", 42.0)
    tmax_clave = (_col("tmax_2022_03", 24.0) + _col("tmax_2023_03", 24.0) + _col("tmax_2024_03", 24.0)) / 3.0
    d_frame["indice_hidrotermico"] = prec_clave / np.maximum(tmax_clave + 10.0, 1.0)
    d_frame["retencion_topografica"] = prec_clave / (1.0 + np.maximum(_col("pendiente_promedio", 3.0), 0.0))


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
    sim_df = base_df.copy()

    # Aplicar ajustes de escenario agronómico (NDVI/EVI, Precipitación CHIRPS de ciclo mayo-sep y Régimen Térmico)
    for col in list(sim_df.columns):
        if (col.startswith("ndvi_promedio_mes_") or col.startswith("evi_promedio_mes_")) and req.ndvi_delta_pct != 0.0:
            sim_df[col] = float(np.clip(sim_df[col].iloc[0] * (1.0 + req.ndvi_delta_pct / 100.0), 0.05, 0.95))
        elif col.startswith("prec_") and req.prec_delta_pct != 0.0:
            # Escalar lluvias del ciclo vegetativo/reproductivo de cebada (mayo a septiembre)
            if any(col.endswith(m) for m in ("_05", "_06", "_07", "_08", "_09")):
                sim_df[col] = float(max(0.0, sim_df[col].iloc[0] * (1.0 + req.prec_delta_pct / 100.0)))
        elif (col.startswith("tmax_") or col.startswith("tmin_")) and req.tmax_delta_c != 0.0:
            sim_df[col] = float(sim_df[col].iloc[0] + req.tmax_delta_c)

    if req.custom_overrides:
        for k, v in req.custom_overrides.items():
            if k in sim_df.columns:
                sim_df[k] = float(v)

    _recompute_engineered(base_df)
    _recompute_engineered(sim_df)

    for col in feature_cols:
        if col not in base_df.columns:
            base_df[col] = float(feature_means.get(col, 0.0))
        if col not in sim_df.columns:
            sim_df[col] = float(feature_means.get(col, 0.0))

    X_base = base_df[feature_cols]
    X_sim = sim_df[feature_cols]

    pred_base = float(model.predict(X_base)[0])
    pred_tree_sim = float(model.predict(X_sim)[0])

    # Combinar la inferencia del ensamble con la elasticidad agronómica física calibrada
    elastic_delta = (
        pred_base * (req.ndvi_delta_pct / 100.0) * 0.42
        + pred_base * (req.prec_delta_pct / 100.0) * 0.28
        - 0.065 * req.tmax_delta_c
    )
    tree_delta = pred_tree_sim - pred_base
    # Si el salto discreto del árbol coincide en signo con la física agronómica, ponderamos ambos;
    # de lo contrario, prevalece la elasticidad agronómica calibrada para evitar artefactos de corte discreto
    if tree_delta * elastic_delta > 0:
        combined_delta = 0.45 * tree_delta + 0.55 * elastic_delta
    else:
        combined_delta = elastic_delta

    if req.ndvi_delta_pct == 0.0 and req.prec_delta_pct == 0.0 and req.tmax_delta_c == 0.0 and not req.custom_overrides:
        combined_delta = 0.0

    pred_sim = float(np.clip(pred_base + combined_delta, 1.40, 6.20))
    area_ha = float(props.get("AREA_HA", 1.0))

    delta_t_ha = pred_sim - pred_base
    delta_pct = (delta_t_ha / pred_base * 100.0) if pred_base > 0 else 0.0

    return {
        "id_poligono": parcela_id,
        "conjunto": props.get("CONJUNTO"),
        "area_ha": round(area_ha, 2),
        "rendimiento_real_t_ha": props.get("RENDIMIENTO_T_HA"),
        "rendimiento_base_modelo_t_ha": round(pred_base, 4),
        "rendimiento_simulado_t_ha": round(pred_sim, 4),
        "delta_t_ha": round(delta_t_ha, 4),
        "delta_pct": round(delta_pct, 2),
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
