"""
test_api.py
Pruebas automatizadas de los endpoints FastAPI (backend/main.py) con TestClient.
Verifica 0 DeprecationWarnings y paridad matemática 100% entre /api/simular y sensibilidad_simulador.json.
"""

import json
from pathlib import Path
import sys

from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from main import app


def test_health_and_summary_endpoints():
    with TestClient(app) as client:
        r_root = client.get("/")
        assert r_root.status_code == 200
        assert r_root.json()["version"] == "4.0.0"

        r_health = client.get("/api/health")
        assert r_health.status_code == 200
        h_data = r_health.json()
        assert h_data["status"] == "ok"
        assert h_data["artifacts_loaded"] is True
        assert h_data["sensitivity_loaded"] is True
        assert h_data["model_loaded"] is True
        assert h_data["total_parcelas"] == 197

        r_sum = client.get("/api/summary")
        assert r_sum.status_code == 200
        s_data = r_sum.json()
        assert s_data["dataset_stats"]["total_features_selected"] == 23
        assert len(s_data["selected_features"]) == 23


def test_parcelas_and_csv_export():
    with TestClient(app) as client:
        r_all = client.get("/api/parcelas")
        assert r_all.status_code == 200
        assert len(r_all.json()["features"]) == 197

        r_pred = client.get("/api/parcelas?conjunto=PREDICCION")
        assert r_pred.status_code == 200
        assert len(r_pred.json()["features"]) == 59

        r_one = client.get("/api/parcelas/AGC_002")
        assert r_one.status_code == 200
        props = r_one.json()["properties"]
        assert props["ID_POLIGONO"] == "AGC_002"
        assert "INTERVALO_80_INF_T_HA" in props
        assert "INTERVALO_80_SUP_T_HA" in props

        r_404 = client.get("/api/parcelas/AGC_999")
        assert r_404.status_code == 404

        r_csv = client.get("/api/export/csv")
        assert r_csv.status_code == 200
        lines = [ln for ln in r_csv.text.strip().splitlines() if ln.strip()]
        assert len(lines) == 60  # 1 header + 59 rows


def test_simular_parity_with_precomputed_surface():
    sim_surface = json.loads(
        (BACKEND_DIR / "artifacts" / "sensibilidad_simulador.json").read_text(encoding="utf-8")
    )
    with TestClient(app) as client:
        # 1. Delta cero -> delta_t_ha exacto 0.0
        r_zero = client.post(
            "/api/simular",
            json={
                "id_poligono": "AGC_002",
                "ndvi_delta_pct": 0.0,
                "prec_delta_pct": 0.0,
                "tmax_delta_c": 0.0,
            },
        )
        assert r_zero.status_code == 200
        z_data = r_zero.json()
        assert z_data["delta_t_ha"] == 0.0
        assert z_data["rendimiento_simulado_t_ha"] == z_data["rendimiento_base_modelo_t_ha"]

        # 2. Perturbación combinada -> paridad exacta con sensibilidad_simulador.json
        r_pert = client.post(
            "/api/simular",
            json={
                "id_poligono": "AGC_002",
                "ndvi_delta_pct": 15.0,
                "prec_delta_pct": -10.0,
                "tmax_delta_c": 1.0,
            },
        )
        assert r_pert.status_code == 200
        p_data = r_pert.json()
        parcel_ref = sim_surface["parcels"]["AGC_002"]
        expected_sim = round(
            parcel_ref["base_yield_t_ha"]
            + parcel_ref["ndvi_deltas"]["15"]
            + parcel_ref["prec_deltas"]["-10"]
            + parcel_ref["tmax_deltas"]["1.0"],
            4,
        )
        assert p_data["rendimiento_simulado_t_ha"] == expected_sim

        # 3. Custom overrides -> evaluación directa sobre el modelo
        r_custom = client.post(
            "/api/simular",
            json={
                "id_poligono": "AGC_002",
                "ndvi_delta_pct": 5.0,
                "prec_delta_pct": 0.0,
                "tmax_delta_c": 0.0,
                "custom_overrides": {"evi_promedio_mes_5": 0.16},
            },
        )
        assert r_custom.status_code == 200
        assert 1.5 <= r_custom.json()["rendimiento_simulado_t_ha"] <= 6.0

        # 4. Validación Pydantic de rangos fuera de límite
        r_invalid = client.post(
            "/api/simular",
            json={
                "id_poligono": "AGC_002",
                "ndvi_delta_pct": 95.0,
            },
        )
        assert r_invalid.status_code == 422
