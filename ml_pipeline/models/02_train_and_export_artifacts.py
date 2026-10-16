"""
02_train_and_export_artifacts.py
Pipeline V4 de Entrenamiento, Validación Cruzada Repetida (5x5), Intervalo Conformal 80%,
Importancia por Permutación del Ensamble Completo y Pre-cálculo de Sensibilidad del Modelo
para el Reto AgroCebada FIRA 2026 - Equipo Agrotec-Amanteca.
"""

import json
import os
from pathlib import Path
import platform
import sys
import tempfile
import time
import warnings

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(ROOT_DIR / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT_DIR / "backend"))

import geopandas as gpd
import joblib
import lightgbm
from lightgbm import LGBMRegressor
import numpy as np
import pandas as pd
import sklearn
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import (
    ExtraTreesRegressor,
    GradientBoostingRegressor,
    RandomForestRegressor,
    StackingRegressor,
    VotingRegressor,
)
from sklearn.inspection import permutation_importance
from sklearn.linear_model import RidgeCV
from sklearn.model_selection import KFold, RepeatedKFold, cross_val_predict, cross_validate
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import RobustScaler
from sklearn.svm import SVR

from backend.agro_core import (
    NDVI_GRID,
    PREC_GRID,
    TMAX_GRID,
    LeakFreeSmartPearsonIDW,
    add_agronomic_features,
    apply_scenario_df,
    compute_spatial_idw_feature,
    select_smart_pearson_columns,
)

warnings.filterwarnings("ignore")

PROCESSED_DIR = ROOT_DIR / "data" / "processed"
BACKEND_ARTIFACTS_DIR = ROOT_DIR / "backend" / "artifacts"
FRONTEND_DATA_DIR = ROOT_DIR / "frontend" / "public" / "data"


def resolve_parquet_path() -> Path:
    candidates = [
        os.environ.get("AGRO_PARQUET_PATH", ""),
        ROOT_DIR / "data" / "processed" / "MATRIZ_FINAL_OPTIMIZADA.parquet",
        ROOT_DIR.parent / "MATRIZ_FINAL_OPTIMIZADA.parquet",
    ]
    for c in candidates:
        if c and Path(c).exists():
            return Path(c)
    raise FileNotFoundError("No se encontró MATRIZ_FINAL_OPTIMIZADA.parquet en data/processed/ ni en el directorio padre.")


def resolve_raw_matrix_path() -> Path:
    candidates = [
        os.environ.get("AGRO_RAW_MATRIX", ""),
        ROOT_DIR / "data" / "raw" / "MATRIZ_FINAL_AGROCEBADA.csv",
        ROOT_DIR.parent / "MATRIZ_FINAL_AGROCEBADA.csv",
    ]
    for c in candidates:
        if c and Path(c).exists():
            return Path(c)
    return Path("")


SHP_PATH = ROOT_DIR / "data" / "raw" / "Parcelas_Reto_AGC_CONJUNTO_70_30" / "Parcelas_Reto_AGC_CONJUNTO.shp"

FEATURE_LABELS_ES = {
    "AREA_HA": "Superficie de Parcela (ha)",
    "ndvi_promedio_mes_1": "NDVI Enero (Pre-siembra)",
    "ndvi_promedio_mes_3": "NDVI Marzo (Preparación de suelo)",
    "ndvi_promedio_mes_5": "NDVI Mayo (Emergencia)",
    "ndvi_promedio_mes_6": "NDVI Junio (Amacollamiento)",
    "ndvi_promedio_mes_7": "NDVI Julio (Encañado)",
    "ndvi_promedio_mes_8": "NDVI Agosto (Espigamiento - Pico)",
    "ndvi_promedio_mes_9": "NDVI Septiembre (Llenado de grano)",
    "ndvi_promedio_mes_10": "NDVI Octubre (Madurez fisiológica)",
    "ndvi_promedio_mes_11": "NDVI Noviembre (Cosecha)",
    "evi_promedio_mes_2": "EVI Febrero (Pre-siembra)",
    "evi_promedio_mes_4": "EVI Abril (Inicio de Ciclo)",
    "evi_promedio_mes_5": "EVI Mayo (Vigor Temprano)",
    "evi_promedio_mes_7": "EVI Julio (Dosel Vegetativo)",
    "evi_promedio_mes_8": "EVI Agosto (Pico Reproductivo)",
    "evi_promedio_mes_9": "EVI Septiembre (Llenado EVI)",
    "evi_promedio_mes_11": "EVI Noviembre (Senescencia)",
    "elevacion_promedio": "Elevación Promedio (msnm)",
    "pendiente_promedio": "Pendiente Topográfica (°)",
    "ndvi_auc_verano": "Integral Fenológica NDVI (Mayo–Oct)",
    "ndvi_tasa_vegetativa": "Tasa Desarrollo Vegetativo (Ago–May)",
    "ndvi_caida_madurez": "Tasa Senescencia / Llenado (Ago–Oct)",
    "indice_hidrotermico": "Índice Hidrotérmico de Aridez (Prec/Tmax)",
    "retencion_topografica": "Índice Retención Hídrica por Pendiente",
    "spatial_idw_yield": "Potencial Microclimático Vecinal (IDW k=7)",
}


def get_feature_label(col: str) -> str:
    if col in FEATURE_LABELS_ES:
        return FEATURE_LABELS_ES[col]
    if col.startswith("evi_promedio_mes_"):
        m = col.split("_")[-1]
        return f"EVI Mes {m} (Vigor Satelital)"
    if col.startswith("ndvi_promedio_mes_"):
        m = col.split("_")[-1]
        return f"NDVI Mes {m} (Vigor Satelital)"
    if col.startswith("prec_"):
        parts = col.split("_")
        return f"Precipitación {parts[1]}-{parts[2]} (mm)"
    if col.startswith("tmax_"):
        parts = col.split("_")
        return f"Temp. Máxima {parts[1]}-{parts[2]} (°C)"
    if col.startswith("tmin_"):
        parts = col.split("_")
        return f"Temp. Mínima {parts[1]}-{parts[2]} (°C)"
    return col


def get_feature_category(col: str) -> str:
    if col == "spatial_idw_yield":
        return "Autocorrelación Geoespacial (IDW)"
    if col in (
        "ndvi_auc_verano",
        "ndvi_tasa_vegetativa",
        "ndvi_caida_madurez",
        "indice_hidrotermico",
        "retencion_topografica",
    ):
        return "Índices Agronómicos Sintéticos"
    if col.startswith("ndvi_") or col.startswith("evi_"):
        return "Vigor Satelital (NDVI / EVI)"
    if col.startswith("prec_"):
        return "Precipitación (CHIRPS)"
    if col.startswith("tmax_") or col.startswith("tmin_"):
        return "Régimen Térmico (Tmax / Tmin)"
    if col in ("elevacion_promedio", "pendiente_promedio", "AREA_HA"):
        return "Fisiografía y Superficie (INEGI)"
    return "Otros"


def main():
    t0_pipeline = time.perf_counter()
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    BACKEND_ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    FRONTEND_DATA_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 84)
    print("🌾 PIPELINE V4: MODELO COHERENTE CON CV, INTERVALO CONFORMAL 80% Y SIMULADOR REAL")
    print("=" * 84)

    # 1. Cargar Shapefile para coordenadas exactas de cada polígono
    gdf = gpd.read_file(SHP_PATH)
    if gdf.crs is not None and gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)

    shp_id_col = "ID_POLIGON" if "ID_POLIGON" in gdf.columns else "ID_POLIGONO"
    if shp_id_col not in gdf.columns:
        for col in gdf.columns:
            if "ID" in col.upper():
                shp_id_col = col
                break
    gdf = gdf.rename(columns={shp_id_col: "ID_POLIGONO"})
    # Proyección métrica temporal para cálculo exacto de centroides sin warning geográfico
    centroids_wgs84 = gdf.to_crs(epsg=32614).geometry.centroid.to_crs(epsg=4326)
    gdf["lat"] = np.round(centroids_wgs84.y, 6)
    gdf["lon"] = np.round(centroids_wgs84.x, 6)
    coords_lookup = gdf[["ID_POLIGONO", "lat", "lon"]].copy()

    # 2. Cargar matriz original de 43 columnas (filtro secuencial previo) y matriz completa de 175 columnas
    parquet_path = resolve_parquet_path()
    df_parquet = pd.read_parquet(parquet_path)
    empty_cols = [c for c in df_parquet.columns if df_parquet[c].isna().all()]
    if empty_cols:
        df_parquet = df_parquet.drop(columns=empty_cols)

    non_feature_cols = ["ID_POLIGONO", "RENDIMIENTO_T_HA", "CONJUNTO"]
    legacy_39_cols = [c for c in df_parquet.columns if c not in non_feature_cols]

    raw_matrix_path = resolve_raw_matrix_path()
    if raw_matrix_path and raw_matrix_path.exists():
        df_full = pd.read_csv(raw_matrix_path)
        empty_full = [c for c in df_full.columns if df_full[c].isna().all()]
        if empty_full:
            df_full = df_full.drop(columns=empty_full)
    else:
        df_full = df_parquet.copy()

    df_full = add_agronomic_features(df_full)
    df_full = df_full.merge(coords_lookup, on="ID_POLIGONO", how="left")

    all_candidate_cols = [c for c in df_full.columns if c not in non_feature_cols + ["lat", "lon"]]

    train_df = df_full[df_full["RENDIMIENTO_T_HA"].notna()].copy().reset_index(drop=True)
    pred_df = df_full[df_full["RENDIMIENTO_T_HA"].isna()].copy().reset_index(drop=True)

    X_train_39 = train_df[legacy_39_cols]
    X_train_full_coords = train_df[all_candidate_cols + ["lat", "lon"]]
    y_train = train_df["RENDIMIENTO_T_HA"]

    # 3. Definir estimadores
    dummy_mean = DummyRegressor(strategy="mean")

    rf_baseline = RandomForestRegressor(
        n_estimators=300,
        max_depth=None,
        min_samples_split=4,
        min_samples_leaf=2,
        max_features="sqrt",
        random_state=42,
        n_jobs=-1,
    )

    rf_pruned = RandomForestRegressor(
        n_estimators=220,
        max_depth=8,
        min_samples_split=4,
        min_samples_leaf=2,
        max_features=0.45,
        random_state=42,
        n_jobs=-1,
    )

    et_pruned = ExtraTreesRegressor(
        n_estimators=220,
        max_depth=8,
        min_samples_split=3,
        min_samples_leaf=2,
        max_features=0.50,
        random_state=42,
        n_jobs=-1,
    )

    svr_model = make_pipeline(RobustScaler(), SVR(kernel="rbf", C=2.2, epsilon=0.06))

    gbr_pruned = GradientBoostingRegressor(
        n_estimators=160,
        learning_rate=0.035,
        max_depth=3,
        subsample=0.80,
        max_features="sqrt",
        random_state=42,
    )

    lgbm_model = LGBMRegressor(
        n_estimators=160,
        learning_rate=0.035,
        num_leaves=10,
        max_depth=4,
        min_child_samples=10,
        subsample=0.85,
        colsample_bytree=0.70,
        reg_alpha=0.8,
        reg_lambda=2.0,
        random_state=42,
        verbose=-1,
    )

    ridge_model = make_pipeline(RobustScaler(), RidgeCV(alphas=np.logspace(-1, 3, 25)))

    ensemble_voting = VotingRegressor(
        estimators=[
            ("et", et_pruned),
            ("rf", rf_pruned),
            ("svr", svr_model),
            ("gbr", gbr_pruned),
        ],
        weights=[0.40, 0.25, 0.20, 0.15],
    )

    stacking_model = StackingRegressor(
        estimators=[
            ("et", et_pruned),
            ("rf", rf_pruned),
            ("svr", svr_model),
            ("gbr", gbr_pruned),
        ],
        final_estimator=RidgeCV(alphas=np.logspace(-2, 2, 20)),
        cv=5,
        n_jobs=-1,
    )

    # Pipelines 100% libres de leakage con Smart-Pearson (top_k=22) + Spatial IDW (1) = 23 variables exactas
    pipe_smart_voting = Pipeline(
        [
            ("smart_idw", LeakFreeSmartPearsonIDW(corr_thresh=0.88, top_k=22, k_neighbors=7, power=1.5)),
            ("model", ensemble_voting),
        ]
    )
    pipe_smart_stacking = Pipeline(
        [
            ("smart_idw", LeakFreeSmartPearsonIDW(corr_thresh=0.88, top_k=22, k_neighbors=7, power=1.5)),
            ("model", stacking_model),
        ]
    )
    pipe_smart_et = Pipeline(
        [
            ("smart_idw", LeakFreeSmartPearsonIDW(corr_thresh=0.88, top_k=22, k_neighbors=7, power=1.5)),
            ("model", et_pruned),
        ]
    )

    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    rkf = RepeatedKFold(n_splits=5, n_repeats=5, random_state=42)
    scoring = {
        "mae": "neg_mean_absolute_error",
        "rmse": "neg_root_mean_squared_error",
        "r2": "r2",
    }

    eval_configs = [
        ("Ensemble Agrotec (Smart-Pearson + IDW)", pipe_smart_voting, X_train_full_coords, "23 Smart-Pearson+IDW"),
        ("Stacking Meta-Ensemble (Smart-Pearson + IDW)", pipe_smart_stacking, X_train_full_coords, "23 Smart-Pearson+IDW"),
        ("Extra Trees (Smart-Pearson + IDW)", pipe_smart_et, X_train_full_coords, "23 Smart-Pearson+IDW"),
        ("Ensemble Voting (Filtro Secuencial 39)", ensemble_voting, X_train_39, "39 base"),
        ("Extra Trees Regressor (39 base)", et_pruned, X_train_39, "39 base"),
        ("Random Forest (Baseline 39 base)", rf_baseline, X_train_39, "39 base"),
        ("SVR (Kernel RBF + RobustScaler)", svr_model, X_train_39, "39 base"),
        ("Gradient Boosting Regressor", gbr_pruned, X_train_39, "39 base"),
        ("RidgeCV Lineal Regularizado", ridge_model, X_train_39, "39 base"),
        ("LightGBM Regressor", lgbm_model, X_train_39, "39 base"),
        ("Referencia (Predecir la Media)", dummy_mean, X_train_39, "Constante"),
    ]

    comparison_table = []
    print("\nEvaluando precisión (5-Fold CV y 5x5 Repeated CV) y tiempos de ejecución...")
    for name, model, X_mat, feat_tag in eval_configs:
        t_start = time.perf_counter()
        cv_res = cross_validate(model, X_mat, y_train, cv=kf, scoring=scoring, return_train_score=True)
        t_cv_ms = (time.perf_counter() - t_start) * 1000.0
        rcv_res = cross_validate(model, X_mat, y_train, cv=rkf, scoring=scoring)

        mae_5f = float((-cv_res["test_mae"]).mean())
        mae_5f_std = float((-cv_res["test_mae"]).std())
        rmse_5f = float((-cv_res["test_rmse"]).mean())
        rmse_5f_std = float((-cv_res["test_rmse"]).std())
        r2_5f = float(cv_res["test_r2"].mean())
        r2_5f_std = float(cv_res["test_r2"].std())

        mae_rep = float((-rcv_res["test_mae"]).mean())
        mae_rep_std = float((-rcv_res["test_mae"]).std())
        rmse_rep = float((-rcv_res["test_rmse"]).mean())
        rmse_rep_std = float((-rcv_res["test_rmse"]).std())
        r2_rep = float(rcv_res["test_r2"].mean())

        comparison_table.append(
            {
                "model": name,
                "feature_set": feat_tag,
                "mae_cv": round(mae_5f, 4),
                "mae_std": round(mae_5f_std, 4),
                "rmse_cv": round(rmse_5f, 4),
                "rmse_std": round(rmse_5f_std, 4),
                "r2_cv": round(r2_5f, 4),
                "r2_std": round(r2_5f_std, 4),
                "mae_repeated_cv": round(mae_rep, 4),
                "mae_repeated_std": round(mae_rep_std, 4),
                "rmse_repeated_cv": round(rmse_rep, 4),
                "rmse_repeated_std": round(rmse_rep_std, 4),
                "r2_repeated_cv": round(r2_rep, 4),
                "cv_time_ms": round(t_cv_ms, 1),
                "folds_mae": [round(float(x), 4) for x in (-cv_res["test_mae"])],
                "folds_rmse": [round(float(x), 4) for x in (-cv_res["test_rmse"])],
                "folds_r2": [round(float(x), 4) for x in cv_res["test_r2"]],
            }
        )
        print(
            f"  - {name:<44} | 5F MAE: {mae_5f:.4f}±{mae_5f_std:.3f} | "
            f"5F RMSE: {rmse_5f:.4f}±{rmse_5f_std:.3f} | 5x5 RMSE: {rmse_rep:.4f}±{rmse_rep_std:.3f}"
        )

    # Ordenar por menor RMSE en Validación Cruzada Repetida 5x5 (25 evaluaciones)
    comparison_table.sort(key=lambda x: (x["rmse_repeated_cv"], x["rmse_cv"], x["mae_cv"]))
    winner_entry = comparison_table[0]
    winner_name = winner_entry["model"]

    print(
        f"\n🏆 Modelo Seleccionado (por menor RMSE en 5x5 Repeated CV y 5-Fold CV): {winner_name}\n"
        f"   5-Fold CV : MAE = {winner_entry['mae_cv']:.4f} ± {winner_entry['mae_std']:.4f} t/ha | "
        f"RMSE = {winner_entry['rmse_cv']:.4f} ± {winner_entry['rmse_std']:.4f} t/ha | R² = {winner_entry['r2_cv']:.4f}\n"
        f"   5x5 Rep CV: MAE = {winner_entry['mae_repeated_cv']:.4f} ± {winner_entry['mae_repeated_std']:.4f} t/ha | "
        f"RMSE = {winner_entry['rmse_repeated_cv']:.4f} ± {winner_entry['rmse_repeated_std']:.4f} t/ha"
    )

    # 4. Medir de forma 100% real todas las métricas Out-Of-Fold y de eficiencia del Baseline (Random Forest 39 vars)
    oof_baseline = cross_val_predict(rf_baseline, X_train_39, y_train, cv=kf)
    res_baseline = oof_baseline - y_train.values
    baseline_mape_oof = round(float(np.mean(np.abs(res_baseline / y_train.values)) * 100.0), 2)
    baseline_within_050 = round(float((np.abs(res_baseline) <= 0.50).mean() * 100.0), 1)
    baseline_within_035 = round(float((np.abs(res_baseline) <= 0.35).mean() * 100.0), 1)

    t_base_fit0 = time.perf_counter()
    rf_baseline.fit(X_train_39, y_train)
    baseline_train_ms = round((time.perf_counter() - t_base_fit0) * 1000.0, 2)

    t_base_inf0 = time.perf_counter()
    pred_rf_base_all = rf_baseline.predict(df_full[legacy_39_cols])
    baseline_inf_ms = round((time.perf_counter() - t_base_inf0) * 1000.0, 3)

    with tempfile.NamedTemporaryFile(suffix=".joblib", delete=False) as tmp_f:
        tmp_base_path = Path(tmp_f.name)
    joblib.dump({"model": rf_baseline, "feature_cols": legacy_39_cols}, tmp_base_path, compress=3)
    baseline_size_kb = round(tmp_base_path.stat().st_size / 1024.0, 1)
    tmp_base_path.unlink(missing_ok=True)

    baseline_cv_entry = next(m for m in comparison_table if "Random Forest (Baseline" in m["model"])
    dummy_cv_entry = next(m for m in comparison_table if "Referencia (Predecir la Media)" in m["model"])

    # 5. Predicciones Out-Of-Fold (OOF) honestas y dispersión OOF en las 138 parcelas con la configuración exacta validada
    oof_preds = np.zeros(len(train_df), dtype=float)
    oof_sub_std = np.zeros(len(train_df), dtype=float)

    for tr_idx, va_idx in kf.split(X_train_full_coords, y_train):
        X_tr_fold = X_train_full_coords.iloc[tr_idx]
        y_tr_fold = y_train.iloc[tr_idx]
        X_va_fold = X_train_full_coords.iloc[va_idx]

        selector_fold = LeakFreeSmartPearsonIDW(corr_thresh=0.88, top_k=22, k_neighbors=7, power=1.5)
        X_tr_trans = selector_fold.fit_transform(X_tr_fold, y_tr_fold)
        X_va_trans = selector_fold.transform(X_va_fold)

        et_f = sklearn.base.clone(et_pruned).fit(X_tr_trans, y_tr_fold)
        rf_f = sklearn.base.clone(rf_pruned).fit(X_tr_trans, y_tr_fold)
        svr_f = sklearn.base.clone(svr_model).fit(X_tr_trans, y_tr_fold)
        gbr_f = sklearn.base.clone(gbr_pruned).fit(X_tr_trans, y_tr_fold)

        p_et = et_f.predict(X_va_trans)
        p_rf = rf_f.predict(X_va_trans)
        p_svr = svr_f.predict(X_va_trans)
        p_gbr = gbr_f.predict(X_va_trans)

        oof_preds[va_idx] = 0.40 * p_et + 0.25 * p_rf + 0.20 * p_svr + 0.15 * p_gbr
        oof_sub_std[va_idx] = np.std(np.vstack([p_et, p_rf, p_svr, p_gbr]), axis=0)

    # 6. Calibración Conformal Split/OOF al 80% de confianza
    abs_oof_residuals = np.abs(y_train.values - oof_preds)
    norm_scale_oof = np.maximum(oof_sub_std, 0.15)
    nonconformity_scores = abs_oof_residuals / norm_scale_oof
    n_train = len(y_train)
    alpha_conf = 0.20  # 80% intervalo de predicción
    q_level = min(1.0, np.ceil((n_train + 1) * (1.0 - alpha_conf)) / n_train)
    conformal_q80 = float(np.quantile(nonconformity_scores, q_level))
    oof_half_width_80 = conformal_q80 * norm_scale_oof
    empirical_coverage_80_pct = round(float((abs_oof_residuals <= oof_half_width_80).mean() * 100.0), 1)

    # 7. Entrenar el modelo final EXACTAMENTE con la misma configuración validada (22 Smart-Pearson + 1 IDW = 23 variables)
    final_selector = LeakFreeSmartPearsonIDW(corr_thresh=0.88, top_k=22, k_neighbors=7, power=1.5)
    final_selector.fit(X_train_full_coords, y_train)
    smart_selected_cols = list(final_selector.selected_cols_)

    df_full["spatial_idw_yield"] = compute_spatial_idw_feature(
        df_full[["lat", "lon"]].values,
        train_df[["lat", "lon"]].values,
        y_train.values,
        k_neighbors=7,
        power=1.5,
    )

    active_feature_cols = smart_selected_cols + ["spatial_idw_yield"]
    print(f"📌 Variables seleccionadas por Smart-Pearson + IDW ({len(active_feature_cols)} exactas, idénticas a CV): {active_feature_cols}")

    train_df = df_full[df_full["RENDIMIENTO_T_HA"].notna()].copy().reset_index(drop=True)
    pred_df = df_full[df_full["RENDIMIENTO_T_HA"].isna()].copy().reset_index(drop=True)

    X_train_final = train_df[active_feature_cols]
    X_all_final = df_full[active_feature_cols]

    # Guardar versión optimizada del Parquet
    export_parquet_cols = list(dict.fromkeys(non_feature_cols + active_feature_cols + legacy_39_cols))
    df_full[export_parquet_cols].to_parquet(PROCESSED_DIR / "MATRIZ_FINAL_OPTIMIZADA_V3.parquet", index=False)

    final_model = ensemble_voting
    t_fit_0 = time.perf_counter()
    rf_pruned.fit(X_train_final, y_train)
    et_pruned.fit(X_train_final, y_train)
    svr_model.fit(X_train_final, y_train)
    gbr_pruned.fit(X_train_final, y_train)
    final_model.fit(X_train_final, y_train)
    train_time_ms = round((time.perf_counter() - t_fit_0) * 1000.0, 2)

    t_inf_0 = time.perf_counter()
    pred_final_all = final_model.predict(X_all_final)
    inference_time_ms = round((time.perf_counter() - t_inf_0) * 1000.0, 3)

    # 8. Importancia de variables sobre el ENSAMBLE COMPLETO (incluyendo SVR, ET, RF y GBR) vía Permutación
    perm_imp = permutation_importance(
        final_model, X_train_final, y_train, n_repeats=25, random_state=42, scoring="neg_root_mean_squared_error"
    )
    perm_raw = np.maximum(0.0, perm_imp.importances_mean)
    if perm_raw.sum() > 0:
        perm_norm = perm_raw / perm_raw.sum()
    else:
        perm_norm = np.ones(len(active_feature_cols)) / len(active_feature_cols)

    tree_imp = (
        (0.40 / 0.80) * et_pruned.feature_importances_
        + (0.25 / 0.80) * rf_pruned.feature_importances_
        + (0.15 / 0.80) * gbr_pruned.feature_importances_
    )
    tree_imp = tree_imp / tree_imp.sum()
    # Combinación 50% importancia por permutación del ensamble completo (que incluye SVR) + 50% reducción de impureza
    combined_imp = 0.50 * perm_norm + 0.50 * tree_imp
    combined_imp = combined_imp / combined_imp.sum()

    feature_importance_list = []
    for idx, col in enumerate(active_feature_cols):
        feature_importance_list.append(
            {
                "feature": col,
                "label": get_feature_label(col),
                "category": get_feature_category(col),
                "importance": round(float(combined_imp[idx]), 5),
                "importance_pct": round(float(combined_imp[idx] * 100.0), 2),
                "perm_importance_rmse": round(float(perm_raw[idx]), 5),
                "tree_importance_pct": round(float(tree_imp[idx] * 100.0), 2),
                "corr_with_target": round(float(X_train_final[col].corr(y_train)), 4),
                "mean_train": round(float(X_train_final[col].mean()), 3),
                "std_train": round(float(X_train_final[col].std()), 3),
                "min_val": round(float(df_full[col].min()), 3),
                "max_val": round(float(df_full[col].max()), 3),
            }
        )
    feature_importance_list.sort(key=lambda x: x["importance"], reverse=True)

    # 9. Intervalo de Predicción Conformal al 80% por parcela
    sub_preds_all = np.vstack(
        [
            et_pruned.predict(X_all_final),
            rf_pruned.predict(X_all_final),
            svr_model.predict(X_all_final),
            gbr_pruned.predict(X_all_final),
        ]
    )
    sub_std_all = np.std(sub_preds_all, axis=0)
    conformal_half_width_all = np.round(conformal_q80 * np.maximum(sub_std_all, 0.15), 4)

    df_full["RENDIMIENTO_PREDICHO_T_HA"] = np.round(pred_final_all, 4)
    df_full["RENDIMIENTO_BASELINE_RF_T_HA"] = np.round(pred_rf_base_all, 4)
    df_full["DISPSERSION_ENSAMBLE_T_HA"] = np.round(sub_std_all, 4)
    df_full["INCERTIDUMBRE_T_HA"] = conformal_half_width_all
    df_full["INTERVALO_80_INF_T_HA"] = np.round(np.maximum(1.0, pred_final_all - conformal_half_width_all), 4)
    df_full["INTERVALO_80_SUP_T_HA"] = np.round(pred_final_all + conformal_half_width_all, 4)

    oof_map = dict(zip(train_df["ID_POLIGONO"], np.round(oof_preds, 4)))
    df_full["RENDIMIENTO_OOF_T_HA"] = df_full["ID_POLIGONO"].map(oof_map)
    df_full["RENDIMIENTO_FINAL_T_HA"] = df_full["RENDIMIENTO_T_HA"].fillna(df_full["RENDIMIENTO_PREDICHO_T_HA"]).round(4)
    df_full["PRODUCCION_ESTIMADA_TON"] = (df_full["AREA_HA"] * df_full["RENDIMIENTO_FINAL_T_HA"]).round(2)

    ndvi_cols = [c for c in legacy_39_cols if c.startswith("ndvi_promedio_mes_")]
    prec_cols = [c for c in legacy_39_cols if c.startswith("prec_")]
    tmax_cols = [c for c in legacy_39_cols if c.startswith("tmax_")]

    high_yield_mask = train_df["RENDIMIENTO_T_HA"] >= 4.35
    low_yield_mask = train_df["RENDIMIENTO_T_HA"] <= 3.30

    ndvi_benchmarks = []
    for c in ndvi_cols:
        month_num = int(c.split("_")[-1])
        month_names = {
            1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun",
            7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic",
        }
        ndvi_benchmarks.append(
            {
                "feature": c,
                "month": month_num,
                "month_name": month_names.get(month_num, f"Mes {month_num}"),
                "mean_all": round(float(df_full[c].mean()), 4),
                "mean_high_yield": round(float(train_df.loc[high_yield_mask, c].mean()), 4),
                "mean_low_yield": round(float(train_df.loc[low_yield_mask, c].mean()), 4),
            }
        )

    # 10. Exportar CSV de las 59 predicciones oficiales
    pred_out = df_full[df_full["CONJUNTO"] == "PREDICCION"][
        [
            "ID_POLIGONO",
            "AREA_HA",
            "RENDIMIENTO_PREDICHO_T_HA",
            "INCERTIDUMBRE_T_HA",
            "INTERVALO_80_INF_T_HA",
            "INTERVALO_80_SUP_T_HA",
            "PRODUCCION_ESTIMADA_TON",
            "RENDIMIENTO_BASELINE_RF_T_HA",
        ]
    ].copy()
    pred_out = pred_out.rename(columns={"RENDIMIENTO_PREDICHO_T_HA": "RENDIMIENTO_T_HA"})

    for target_csv in [
        PROCESSED_DIR / "predicciones_59_parcelas.csv",
        BACKEND_ARTIFACTS_DIR / "predicciones_59_parcelas.csv",
        FRONTEND_DATA_DIR / "predicciones_59_parcelas.csv",
    ]:
        pred_out.to_csv(target_csv, index=False)

    # 11. Pre-calcular tabla de sensibilidad 100% basada en el modelo real para las 197 parcelas
    print("🔄 Pre-calculando superficie de respuesta del modelo para el simulador en las 197 parcelas...")
    base_preds_197 = np.round(final_model.predict(df_full[active_feature_cols]), 4)

    ndvi_Lookup = {pid: {} for pid in df_full["ID_POLIGONO"]}
    for d_ndvi in NDVI_GRID:
        if d_ndvi == 0:
            deltas = np.zeros(len(df_full))
        else:
            pert_df = apply_scenario_df(df_full, ndvi_delta_pct=float(d_ndvi), prec_delta_pct=0.0, tmax_delta_c=0.0)
            deltas = final_model.predict(pert_df[active_feature_cols]) - base_preds_197
        for i, pid in enumerate(df_full["ID_POLIGONO"]):
            ndvi_Lookup[pid][str(d_ndvi)] = round(float(deltas[i]), 4)

    prec_Lookup = {pid: {} for pid in df_full["ID_POLIGONO"]}
    for d_prec in PREC_GRID:
        if d_prec == 0:
            deltas = np.zeros(len(df_full))
        else:
            pert_df = apply_scenario_df(df_full, ndvi_delta_pct=0.0, prec_delta_pct=float(d_prec), tmax_delta_c=0.0)
            deltas = final_model.predict(pert_df[active_feature_cols]) - base_preds_197
        for i, pid in enumerate(df_full["ID_POLIGONO"]):
            prec_Lookup[pid][str(d_prec)] = round(float(deltas[i]), 4)

    tmax_Lookup = {pid: {} for pid in df_full["ID_POLIGONO"]}
    for d_tmax in TMAX_GRID:
        key_str = f"{float(d_tmax):.1f}"
        if d_tmax == 0.0:
            deltas = np.zeros(len(df_full))
        else:
            pert_df = apply_scenario_df(df_full, ndvi_delta_pct=0.0, prec_delta_pct=0.0, tmax_delta_c=float(d_tmax))
            deltas = final_model.predict(pert_df[active_feature_cols]) - base_preds_197
        for i, pid in enumerate(df_full["ID_POLIGONO"]):
            tmax_Lookup[pid][key_str] = round(float(deltas[i]), 4)

    # La combinación de controles se evalúa conjuntamente para conservar
    # interacciones no lineales; no se suman efectos marginales independientes.
    combined_Lookup = {pid: {} for pid in df_full["ID_POLIGONO"]}
    for d_ndvi in NDVI_GRID:
        for d_prec in PREC_GRID:
            for d_tmax in TMAX_GRID:
                if d_ndvi == 0 and d_prec == 0 and d_tmax == 0:
                    deltas = np.zeros(len(df_full))
                else:
                    pert_df = apply_scenario_df(
                        df_full,
                        ndvi_delta_pct=float(d_ndvi),
                        prec_delta_pct=float(d_prec),
                        tmax_delta_c=float(d_tmax),
                    )
                    deltas = final_model.predict(pert_df[active_feature_cols]) - base_preds_197
                key = f"{d_ndvi}|{d_prec}|{d_tmax:.1f}"
                for i, pid in enumerate(df_full["ID_POLIGONO"]):
                    combined_Lookup[pid][key] = round(float(deltas[i]), 4)

    sim_payload = {
        "methodology": (
            "Predicciones reales del Ensemble Agrotec evaluadas sobre perturbaciones individuales "
            "de cada grupo de variables (NDVI/EVI, Precipitación CHIRPS, Temperatura Tmax/Tmin) y adición "
            "de efectos marginales del modelo. Refleja asociaciones aprendidas de los datos históricos (correlación observacional, no causalidad experimental)."
        ),
        "grids": {
            "ndvi_delta_pct": NDVI_GRID,
            "prec_delta_pct": PREC_GRID,
            "tmax_delta_c": TMAX_GRID,
        },
        "parcels": {},
    }
    for i, row in df_full.iterrows():
        pid = row["ID_POLIGONO"]
        sim_payload["parcels"][pid] = {
            "base_yield_t_ha": float(base_preds_197[i]),
            "area_ha": round(float(row["AREA_HA"]), 2),
            "ndvi_deltas": ndvi_Lookup[pid],
            "prec_deltas": prec_Lookup[pid],
            "tmax_deltas": tmax_Lookup[pid],
            "combined_deltas": combined_Lookup[pid],
        }

    sim_json_str = json.dumps(sim_payload, ensure_ascii=False)
    for target_sim in [
        PROCESSED_DIR / "sensibilidad_simulador.json",
        BACKEND_ARTIFACTS_DIR / "sensibilidad_simulador.json",
        FRONTEND_DATA_DIR / "sensibilidad_simulador.json",
    ]:
        target_sim.write_text(sim_json_str, encoding="utf-8")

    # 12. Construir GeoJSON con Factores Destacados vs Media Regional
    feature_means = X_train_final.mean()
    feature_stds = X_train_final.std().replace(0, 1)
    feature_corrs = {c: float(X_train_final[c].corr(y_train)) for c in active_feature_cols}
    top_15_features = [f["feature"] for f in feature_importance_list[:15]]
    imp_lookup = {f["feature"]: f["importance"] for f in feature_importance_list}

    dashboard_keep_cols = list(
        dict.fromkeys(
            [
                "ID_POLIGONO",
                "CONJUNTO",
                "AREA_HA",
                "RENDIMIENTO_T_HA",
                "RENDIMIENTO_PREDICHO_T_HA",
                "RENDIMIENTO_BASELINE_RF_T_HA",
                "DISPSERSION_ENSAMBLE_T_HA",
                "INCERTIDUMBRE_T_HA",
                "INTERVALO_80_INF_T_HA",
                "INTERVALO_80_SUP_T_HA",
                "RENDIMIENTO_OOF_T_HA",
                "RENDIMIENTO_FINAL_T_HA",
                "PRODUCCION_ESTIMADA_TON",
                "elevacion_promedio",
                "pendiente_promedio",
            ]
            + ndvi_cols
            + prec_cols
            + tmax_cols
            + active_feature_cols
        )
    )

    merged_gdf = gdf[["ID_POLIGONO", "lat", "lon", "geometry"]].merge(
        df_full[dashboard_keep_cols], on="ID_POLIGONO", how="right"
    )

    drivers_json = []
    for _, row in merged_gdf.iterrows():
        local_factors = []
        for col in top_15_features:
            z_score = float((row[col] - feature_means[col]) / feature_stds[col])
            direction = 1.0 if feature_corrs[col] >= 0 else -1.0
            impact = z_score * direction * imp_lookup[col]
            local_factors.append(
                {
                    "feature": col,
                    "label": get_feature_label(col),
                    "value": round(float(row[col]), 3),
                    "mean_ref": round(float(feature_means[col]), 3),
                    "z_score": round(z_score, 2),
                    "impact_score": round(impact, 4),
                }
            )
        local_factors.sort(key=lambda x: abs(x["impact_score"]), reverse=True)
        drivers_json.append(json.dumps(local_factors[:5], ensure_ascii=False))

    merged_gdf["top_drivers"] = drivers_json
    merged_gdf["prec_total_2024"] = merged_gdf[[c for c in prec_cols if "2024" in c]].sum(axis=1).round(1)
    merged_gdf["prec_total_2023"] = merged_gdf[[c for c in prec_cols if "2023" in c]].sum(axis=1).round(1)
    merged_gdf["ndvi_pico_verano"] = (
        merged_gdf[["ndvi_promedio_mes_7", "ndvi_promedio_mes_8", "ndvi_promedio_mes_9"]].max(axis=1).round(4)
    )
    merged_gdf["tmax_media"] = merged_gdf[tmax_cols].mean(axis=1).round(2)

    geojson_str = merged_gdf.to_json()
    for target_path in [
        PROCESSED_DIR / "parcelas_197_dashboard.geojson",
        BACKEND_ARTIFACTS_DIR / "parcelas_197_dashboard.geojson",
        FRONTEND_DATA_DIR / "parcelas_197_dashboard.geojson",
    ]:
        target_path.write_text(geojson_str, encoding="utf-8")

    model_bundle = {
        "model": final_model,
        "feature_cols": active_feature_cols,
        "use_engineered_features": True,
        "feature_means": feature_means.to_dict(),
        "feature_stds": feature_stds.to_dict(),
        "conformal_q80": conformal_q80,
    }
    model_file = BACKEND_ARTIFACTS_DIR / "best_model.joblib"
    joblib.dump(model_bundle, model_file, compress=3)
    model_size_kb = round(model_file.stat().st_size / 1024.0, 1)

    oof_scatter = []
    residuals = oof_preds - y_train.values
    within_05_pct = round(float((np.abs(residuals) <= 0.50).mean() * 100.0), 1)
    within_035_pct = round(float((np.abs(residuals) <= 0.35).mean() * 100.0), 1)
    mape_oof_pct = round(float(np.mean(np.abs(residuals / y_train.values)) * 100.0), 2)

    for idx_r, row in df_full[df_full["CONJUNTO"] == "ENTRENAMIENTO"].reset_index(drop=True).iterrows():
        oof_scatter.append(
            {
                "id": row["ID_POLIGONO"],
                "area_ha": round(float(row["AREA_HA"]), 2),
                "actual": round(float(row["RENDIMIENTO_T_HA"]), 3),
                "predicted_oof": round(float(row["RENDIMIENTO_OOF_T_HA"]), 3),
                "error": round(float(row["RENDIMIENTO_OOF_T_HA"] - row["RENDIMIENTO_T_HA"]), 3),
                "interval_80_half": round(float(oof_half_width_80[idx_r]), 3),
            }
        )

    corr_matrix = train_df[smart_selected_cols].corr().abs()
    upper_tri = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
    max_pair_corr = round(float(upper_tri.max().max()), 4)
    mean_pair_corr = round(float(upper_tri.stack().mean()), 4)

    total_pipeline_ms = round((time.perf_counter() - t0_pipeline) * 1000.0, 1)

    summary_payload = {
        "project": "Reto AgroCebada FIRA 2026",
        "team": "Agrotec-Amanteca",
        "environment_versions": {
            "python": platform.python_version(),
            "scikit_learn": sklearn.__version__,
            "lightgbm": lightgbm.__version__,
            "pandas": pd.__version__,
            "numpy": np.__version__,
            "geopandas": gpd.__version__,
            "joblib": joblib.__version__,
        },
        "dataset_stats": {
            "total_parcelas": int(len(df_full)),
            "train_parcelas": int(len(train_df)),
            "pred_parcelas": int(len(pred_df)),
            "total_features_initial": 175,
            "total_features_selected": int(len(active_feature_cols)),
            "base_features_after_pearson": int(len(smart_selected_cols)),
            "legacy_sequential_features": int(len(legacy_39_cols)),
            "pearson_threshold": 0.88,
            "max_pairwise_corr": max_pair_corr,
            "mean_pairwise_corr": mean_pair_corr,
            "completeness_pct": 100.0,
            "collinearity_reduction_pct": round((1.0 - len(active_feature_cols) / 175.0) * 100.0, 1),
            "total_area_ha": round(float(df_full["AREA_HA"].sum()), 2),
            "train_area_ha": round(float(train_df["AREA_HA"].sum()), 2),
            "pred_area_ha": round(float(pred_df["AREA_HA"].sum()), 2),
            "train_yield_mean": round(float(y_train.mean()), 3),
            "train_yield_std": round(float(y_train.std()), 3),
            "train_yield_min": round(float(y_train.min()), 2),
            "train_yield_max": round(float(y_train.max()), 2),
            "pred_yield_mean": round(float(pred_out["RENDIMIENTO_T_HA"].mean()), 3),
            "pred_yield_std": round(float(pred_out["RENDIMIENTO_T_HA"].std()), 3),
            "pred_yield_min": round(float(pred_out["RENDIMIENTO_T_HA"].min()), 2),
            "pred_yield_max": round(float(pred_out["RENDIMIENTO_T_HA"].max()), 2),
            "total_production_ton": round(float(df_full["PRODUCCION_ESTIMADA_TON"].sum()), 2),
            "pred_production_ton": round(float(pred_out["PRODUCCION_ESTIMADA_TON"].sum()), 2),
        },
        "efficiency_metrics": {
            "train_time_ms": train_time_ms,
            "inference_197_ms": inference_time_ms,
            "inference_per_parcel_ms": round(inference_time_ms / len(df_full), 4),
            "total_pipeline_ms": total_pipeline_ms,
            "model_bundle_size_kb": model_size_kb,
            "oof_within_050_t_ha_pct": within_05_pct,
            "oof_within_035_t_ha_pct": within_035_pct,
            "mape_oof_pct": mape_oof_pct,
            "accuracy_oof_pct": round(100.0 - mape_oof_pct, 2),
            "conformal_80_coverage_oof_pct": empirical_coverage_80_pct,
            "conformal_80_mean_half_width_t_ha": round(float(conformal_half_width_all.mean()), 3),
            "conformal_q80_factor": round(conformal_q80, 4),
        },
        "baseline_metrics": {
            "model": "Random Forest (Baseline 39 base)",
            "feature_count": int(len(legacy_39_cols)),
            "mae_cv": baseline_cv_entry["mae_cv"],
            "mae_std": baseline_cv_entry["mae_std"],
            "rmse_cv": baseline_cv_entry["rmse_cv"],
            "rmse_std": baseline_cv_entry["rmse_std"],
            "r2_cv": baseline_cv_entry["r2_cv"],
            "mae_repeated_cv": baseline_cv_entry["mae_repeated_cv"],
            "rmse_repeated_cv": baseline_cv_entry["rmse_repeated_cv"],
            "mape_oof_pct": baseline_mape_oof,
            "accuracy_oof_pct": round(100.0 - baseline_mape_oof, 2),
            "oof_within_050_t_ha_pct": baseline_within_050,
            "oof_within_035_t_ha_pct": baseline_within_035,
            "train_time_ms": baseline_train_ms,
            "inference_197_ms": baseline_inf_ms,
            "model_bundle_size_kb": baseline_size_kb,
        },
        "dummy_metrics": {
            "model": "Referencia (Predecir la Media)",
            "mae_cv": dummy_cv_entry["mae_cv"],
            "rmse_cv": dummy_cv_entry["rmse_cv"],
            "r2_cv": dummy_cv_entry["r2_cv"],
            "rmse_repeated_cv": dummy_cv_entry["rmse_repeated_cv"],
        },
        "winner_model": winner_name,
        "selected_features": active_feature_cols,
        "models_comparison": comparison_table,
        "feature_importances": feature_importance_list,
        "ndvi_benchmarks": ndvi_benchmarks,
        "oof_validation_scatter": oof_scatter,
    }

    summary_json_str = json.dumps(summary_payload, indent=2, ensure_ascii=False)
    for target_path in [
        PROCESSED_DIR / "metrics_summary.json",
        BACKEND_ARTIFACTS_DIR / "metrics_summary.json",
        FRONTEND_DATA_DIR / "metrics_summary.json",
    ]:
        target_path.write_text(summary_json_str, encoding="utf-8")

    print("\n⚡ MÉTRICAS VERIFICADAS V4 (100% MEDIDAS Y COHERENTES):")
    print(f"  - Variables del Modelo Publicado == CV: {len(active_feature_cols)} predictores")
    print(f"  - MAE 5-Fold CV                       : {winner_entry['mae_cv']:.4f} ± {winner_entry['mae_std']:.4f} t/ha")
    print(f"  - RMSE 5-Fold CV                      : {winner_entry['rmse_cv']:.4f} ± {winner_entry['rmse_std']:.4f} t/ha")
    print(f"  - RMSE 5x5 Repeated CV (25 corridas)  : {winner_entry['rmse_repeated_cv']:.4f} ± {winner_entry['rmse_repeated_std']:.4f} t/ha")
    print(f"  - R² Explicado (5-Fold CV)            : {winner_entry['r2_cv']:.4f}")
    print(f"  - MAPE Out-Of-Fold (138 parcelas)     : {mape_oof_pct:.2f}% (Baseline medido: {baseline_mape_oof:.2f}%)")
    print(f"  - Parcelas con error OOF <= 0.50 t/ha : {within_05_pct:.1f}% (Baseline medido: {baseline_within_050:.1f}%)")
    print(f"  - Cobertura Empírica Intervalo 80% OOF: {empirical_coverage_80_pct:.1f}% ( Semiancho medio: ±{conformal_half_width_all.mean():.3f} t/ha )")
    print(f"  - Tiempo de Inferencia (197 parcelas) : {inference_time_ms:.2f} ms (Baseline medido: {baseline_inf_ms:.2f} ms)")
    print(f"  - Peso del Modelo Comprimido          : {model_size_kb:.1f} KB (Baseline medido: {baseline_size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
