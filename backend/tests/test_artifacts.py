"""
test_artifacts.py
Pruebas automatizadas de integridad, paridad y coherencia sobre los artefactos
generados por el pipeline V4 (02_train_and_export_artifacts.py).
"""

import json
from pathlib import Path

import joblib
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[2]
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
BACKEND_ARTIFACTS_DIR = ROOT_DIR / "backend" / "artifacts"
FRONTEND_DATA_DIR = ROOT_DIR / "frontend" / "public" / "data"


def test_artifact_files_exist_and_are_synced():
    filenames = [
        "metrics_summary.json",
        "parcelas_197_dashboard.geojson",
        "predicciones_59_parcelas.csv",
        "sensibilidad_simulador.json",
    ]
    for fname in filenames:
        p_proc = PROCESSED_DIR / fname
        p_back = BACKEND_ARTIFACTS_DIR / fname
        p_front = FRONTEND_DATA_DIR / fname
        assert p_proc.exists(), f"Falta {p_proc}"
        assert p_back.exists(), f"Falta {p_back}"
        assert p_front.exists(), f"Falta {p_front}"
        assert p_proc.read_bytes() == p_back.read_bytes(), f"Desincronización entre processed y backend en {fname}"
        assert p_back.read_bytes() == p_front.read_bytes(), f"Desincronización entre backend y frontend en {fname}"


def test_model_cv_feature_parity():
    summary = json.loads((BACKEND_ARTIFACTS_DIR / "metrics_summary.json").read_text(encoding="utf-8"))
    bundle = joblib.load(BACKEND_ARTIFACTS_DIR / "best_model.joblib")

    feature_cols = bundle["feature_cols"]
    assert len(feature_cols) == 23, f"El modelo debe tener exactamente 23 variables, tiene {len(feature_cols)}"
    assert summary["dataset_stats"]["total_features_selected"] == 23
    assert summary["selected_features"] == feature_cols
    assert len(summary["feature_importances"]) == 23


def test_59_predictions_csv_and_conformal_intervals():
    df = pd.read_csv(BACKEND_ARTIFACTS_DIR / "predicciones_59_parcelas.csv")
    assert len(df) == 59, f"Deben ser exactamente 59 predicciones, se encontraron {len(df)}"
    assert int(df.isna().sum().sum()) == 0, "No debe haber valores nulos en predicciones_59_parcelas.csv"
    assert (df["RENDIMIENTO_T_HA"] >= 1.5).all() and (df["RENDIMIENTO_T_HA"] <= 6.0).all()
    assert (df["INTERVALO_80_INF_T_HA"] < df["RENDIMIENTO_T_HA"]).all()
    assert (df["RENDIMIENTO_T_HA"] < df["INTERVALO_80_SUP_T_HA"]).all()


def test_conformal_coverage_and_baseline_measured():
    summary = json.loads((BACKEND_ARTIFACTS_DIR / "metrics_summary.json").read_text(encoding="utf-8"))
    eff = summary["efficiency_metrics"]
    base = summary["baseline_metrics"]
    dummy = summary["dummy_metrics"]

    assert 75.0 <= eff["conformal_80_coverage_oof_pct"] <= 90.0
    assert base["feature_count"] == 39
    assert base["mae_cv"] > summary["models_comparison"][0]["mae_cv"]
    assert dummy["mae_cv"] > 0.70


def test_sensitivity_surface_completeness():
    sim = json.loads((BACKEND_ARTIFACTS_DIR / "sensibilidad_simulador.json").read_text(encoding="utf-8"))
    parcels = sim["parcels"]
    assert len(parcels) == 197
    for pid, pdata in parcels.items():
        assert pdata["ndvi_deltas"]["0"] == 0.0
        assert pdata["prec_deltas"]["0"] == 0.0
        assert pdata["tmax_deltas"]["0.0"] == 0.0
        assert pdata["combined_deltas"]["0|0|0.0"] == 0.0


def test_no_unverified_or_legacy_numbers_in_codebase_and_docs():
    docs_data_dir = ROOT_DIR / "docs" / "data"
    for fname in [
        "metrics_summary.json",
        "parcelas_197_dashboard.geojson",
        "predicciones_59_parcelas.csv",
        "sensibilidad_simulador.json",
    ]:
        assert (docs_data_dir / fname).exists(), f"Falta en docs/data: {fname}"
        assert (docs_data_dir / fname).read_bytes() == (BACKEND_ARTIFACTS_DIR / fname).read_bytes()

    forbidden_strings = [
        "1,560.60",
        "1560.6",
        "67.4%",
        "2,150 KB",
        "(Punto #",
        "0.42",
        "-0.065",
    ]
    checked_files = [
        ROOT_DIR / "README.md",
        ROOT_DIR / "frontend" / "src" / "App.jsx",
        ROOT_DIR / "backend" / "main.py",
    ]
    for fpath in checked_files:
        content = fpath.read_text(encoding="utf-8")
        for bad in forbidden_strings:
            assert bad not in content, f"Se encontró texto legado/no verificado '{bad}' en {fpath.name}"
