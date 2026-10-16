"""
02_train_and_export_artifacts.py
Pipeline de Alta Precisión ML, Ingeniería de Variables Fenológicas/Hidrotérmicas,
Auditoría de Calidad de Datos y Eficiencia Computacional para el Reto AgroCebada FIRA 2026.
"""

import json
from pathlib import Path
import sys
import time
import warnings

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import geopandas as gpd
import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.ensemble import (
    ExtraTreesRegressor,
    GradientBoostingRegressor,
    RandomForestRegressor,
    StackingRegressor,
    VotingRegressor,
)
from sklearn.inspection import permutation_importance
from sklearn.linear_model import Ridge, RidgeCV
from sklearn.model_selection import KFold, RepeatedKFold, cross_val_predict, cross_validate
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import RobustScaler
from sklearn.svm import SVR

warnings.filterwarnings("ignore")

ROOT_DIR = Path(__file__).resolve().parents[2]
PARQUET_PATH = ROOT_DIR / "data" / "processed" / "MATRIZ_FINAL_OPTIMIZADA.parquet"
if not PARQUET_PATH.exists():
    PARQUET_PATH = Path(r"D:\Agrotec\MATRIZ_FINAL_OPTIMIZADA.parquet")

SHP_PATH = ROOT_DIR / "data" / "raw" / "Parcelas_Reto_AGC_CONJUNTO_70_30" / "Parcelas_Reto_AGC_CONJUNTO.shp"
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
BACKEND_ARTIFACTS_DIR = ROOT_DIR / "backend" / "artifacts"
FRONTEND_DATA_DIR = ROOT_DIR / "frontend" / "public" / "data"

FEATURE_LABELS_ES = {
    "AREA_HA": "Superficie de Parcela (ha)",
    "ndvi_promedio_mes_1": "NDVI Enero (Pre-siembra)",
    "ndvi_promedio_mes_5": "NDVI Mayo (Emergencia)",
    "ndvi_promedio_mes_6": "NDVI Junio (Amacollamiento)",
    "ndvi_promedio_mes_7": "NDVI Julio (Encañado)",
    "ndvi_promedio_mes_8": "NDVI Agosto (Espigamiento - Pico)",
    "ndvi_promedio_mes_9": "NDVI Septiembre (Llenado de grano)",
    "ndvi_promedio_mes_10": "NDVI Octubre (Madurez fisiológica)",
    "ndvi_promedio_mes_11": "NDVI Noviembre (Cosecha)",
    "elevacion_promedio": "Elevación Promedio (msnm)",
    "pendiente_promedio": "Pendiente Topográfica (°)",
    "ndvi_auc_verano": "Integral Fenológica NDVI (Mayo–Oct)",
    "ndvi_tasa_vegetativa": "Tasa Desarrollo Vegetativo (Ago–May)",
    "ndvi_caida_madurez": "Tasa Senescencia / Llenado (Ago–Oct)",
    "indice_hidrotermico": "Índice Hidrotérmico de Aridez (Prec/Tmax)",
    "retencion_topografica": "Índice Retención Hídrica por Pendiente",
}


def add_agronomic_features(df_in: pd.DataFrame) -> pd.DataFrame:
    """
    Construye 5 índices agronómicos de dominio fila-por-fila (100% libre de data leakage
    entre entrenamiento y validación, pues depende únicamente de las lecturas físicas de cada parcela).
    """
    d = df_in.copy()
    # 1. Integral Fenológica bajo la curva de NDVI en ventana reproductiva (Mayo a Octubre)
    d["ndvi_auc_verano"] = (
        0.5 * d["ndvi_promedio_mes_5"]
        + d["ndvi_promedio_mes_6"]
        + d["ndvi_promedio_mes_7"]
        + d["ndvi_promedio_mes_8"]
        + d["ndvi_promedio_mes_9"]
        + 0.5 * d["ndvi_promedio_mes_10"]
    )
    # 2. Velocidad de desarrollo vegetativo (Emergencia -> Espigamiento)
    d["ndvi_tasa_vegetativa"] = d["ndvi_promedio_mes_8"] - d["ndvi_promedio_mes_5"]
    # 3. Tasa de llenado de grano y senescencia (Espigamiento -> Madurez)
    d["ndvi_caida_madurez"] = d["ndvi_promedio_mes_8"] - d["ndvi_promedio_mes_10"]
    # 4. Índice Hidrotérmico de De Martonne (disponibilidad hídrica frente a estrés térmico)
    prec_clave = d["prec_2022_07"] + d["prec_2023_05"] + d["prec_2022_05"]
    tmax_clave = (d["tmax_2022_03"] + d["tmax_2023_03"] + d["tmax_2024_03"]) / 3.0
    d["indice_hidrotermico"] = prec_clave / (tmax_clave + 10.0)
    # 5. Retención topográfica de humedad (infiltración vs escorrentía por pendiente)
    d["retencion_topografica"] = prec_clave / (1.0 + d["pendiente_promedio"])
    return d


def get_feature_label(col: str) -> str:
    if col in FEATURE_LABELS_ES:
        return FEATURE_LABELS_ES[col]
    if col.startswith("prec_"):
        parts = col.split("_")
        return f"Precipitación {parts[1]}-{parts[2]} (mm)"
    if col.startswith("tmax_"):
        parts = col.split("_")
        return f"Temp. Máxima {parts[1]}-{parts[2]} (°C)"
    return col


def get_feature_category(col: str) -> str:
    if col in (
        "ndvi_auc_verano",
        "ndvi_tasa_vegetativa",
        "ndvi_caida_madurez",
        "indice_hidrotermico",
        "retencion_topografica",
    ):
        return "Índices Agronómicos Sintéticos"
    if col.startswith("ndvi_"):
        return "Vigor Satelital (NDVI)"
    if col.startswith("prec_"):
        return "Precipitación (CHIRPS)"
    if col.startswith("tmax_"):
        return "Temperatura Máxima (CHIRPS)"
    if col in ("elevacion_promedio", "pendiente_promedio", "AREA_HA"):
        return "Fisiografía y Superficie (INEGI)"
    return "Otros"


def main():
    t0_pipeline = time.perf_counter()
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    BACKEND_ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    FRONTEND_DATA_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 78)
    print("🌾 ENTRENAMIENTO DE ALTA PRECISIÓN, CALIDAD DE DATOS Y EFICIENCIA (V2)")
    print("=" * 78)

    df_raw = pd.read_parquet(PARQUET_PATH)
    empty_cols = [c for c in df_raw.columns if df_raw[c].isna().all()]
    if empty_cols:
        df_raw = df_raw.drop(columns=empty_cols)

    non_feature_cols = ["ID_POLIGONO", "RENDIMIENTO_T_HA", "CONJUNTO"]
    base_feature_cols = [c for c in df_raw.columns if c not in non_feature_cols]

    # Enriquecer con índices agronómicos de dominio
    df = add_agronomic_features(df_raw)
    engineered_cols = [c for c in df.columns if c not in non_feature_cols]

    train_df = df[df["RENDIMIENTO_T_HA"].notna()].copy().reset_index(drop=True)
    pred_df = df[df["RENDIMIENTO_T_HA"].isna()].copy().reset_index(drop=True)

    X_train_base = train_df[base_feature_cols]
    X_train_eng = train_df[engineered_cols]
    y_train = train_df["RENDIMIENTO_T_HA"]

    # Definir modelos
    rf_baseline = RandomForestRegressor(
        n_estimators=300,
        max_depth=None,
        min_samples_split=4,
        min_samples_leaf=2,
        max_features="sqrt",
        random_state=42,
        n_jobs=-1,
    )

    et_model = ExtraTreesRegressor(
        n_estimators=650,
        max_depth=12,
        min_samples_split=3,
        min_samples_leaf=1,
        max_features=0.45,
        random_state=42,
        n_jobs=-1,
    )

    svr_model = make_pipeline(RobustScaler(), SVR(kernel="rbf", C=1.9, epsilon=0.07))

    gbr_model = GradientBoostingRegressor(
        n_estimators=230,
        learning_rate=0.035,
        max_depth=3,
        subsample=0.80,
        max_features="sqrt",
        random_state=42,
    )

    lgbm_model = LGBMRegressor(
        n_estimators=180,
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
            ("et", et_model),
            ("rf", rf_baseline),
            ("svr", svr_model),
            ("gbr", gbr_model),
        ],
        weights=[0.42, 0.28, 0.20, 0.10],
    )

    stacking_model = StackingRegressor(
        estimators=[
            ("et", et_model),
            ("rf", rf_baseline),
            ("svr", svr_model),
            ("gbr", gbr_model),
        ],
        final_estimator=RidgeCV(alphas=np.logspace(-2, 2, 20)),
        cv=5,
        n_jobs=-1,
    )

    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    rkf = RepeatedKFold(n_splits=5, n_repeats=5, random_state=42)
    scoring = {
        "mae": "neg_mean_absolute_error",
        "rmse": "neg_root_mean_squared_error",
        "r2": "r2",
    }

    # Evaluar tanto en las 39 variables base como en las 44 con Ingeniería Fenológica
    eval_configs = [
        ("Ensemble Agrotec-Amanteca (Voting)", ensemble_voting, X_train_base, "39 base"),
        ("Stacking Meta-Ensemble (RidgeCV)", stacking_model, X_train_base, "39 base"),
        ("Ensemble + Variables Fenológicas (44)", ensemble_voting, X_train_eng, "44 eng"),
        ("Extra Trees Regressor", et_model, X_train_base, "39 base"),
        ("Random Forest (Baseline)", rf_baseline, X_train_base, "39 base"),
        ("SVR (Kernel RBF + RobustScaler)", svr_model, X_train_base, "39 base"),
        ("Gradient Boosting Regressor", gbr_model, X_train_base, "39 base"),
        ("RidgeCV Lineal Regularizado", ridge_model, X_train_base, "39 base"),
        ("LightGBM Regressor", lgbm_model, X_train_base, "39 base"),
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
        mae_rep = float((-rcv_res["test_mae"]).mean())
        rmse_rep = float((-rcv_res["test_rmse"]).mean())

        comparison_table.append(
            {
                "model": name,
                "feature_set": feat_tag,
                "mae_cv": round(mae_5f, 4),
                "mae_std": round(mae_5f_std, 4),
                "rmse_cv": round(rmse_5f, 4),
                "rmse_std": round(rmse_5f_std, 4),
                "r2_cv": round(r2_5f, 4),
                "mae_repeated_cv": round(mae_rep, 4),
                "rmse_repeated_cv": round(rmse_rep, 4),
                "cv_time_ms": round(t_cv_ms, 1),
                "folds_mae": [round(float(x), 4) for x in (-cv_res["test_mae"])],
                "folds_rmse": [round(float(x), 4) for x in (-cv_res["test_rmse"])],
                "folds_r2": [round(float(x), 4) for x in cv_res["test_r2"]],
            }
        )
        print(
            f"  - {name:<38} | MAE: {mae_5f:.4f} | RMSE: {rmse_5f:.4f} | "
            f"R²: {r2_5f:.4f} | 5x5 RMSE: {rmse_rep:.4f} | {t_cv_ms:.0f} ms"
        )

    comparison_table.sort(key=lambda x: (x["rmse_cv"], x["mae_cv"]))
    winner_entry = comparison_table[0]
    winner_name = winner_entry["model"]
    use_eng = winner_entry["feature_set"] == "44 eng"
    active_feature_cols = engineered_cols if use_eng else base_feature_cols
    X_train_final = train_df[active_feature_cols]
    X_all_final = df[active_feature_cols]

    print(
        f"\n🏆 Modelo Ganador Seleccionado: {winner_name} "
        f"(MAE = {winner_entry['mae_cv']:.4f} t/ha | RMSE = {winner_entry['rmse_cv']:.4f} t/ha | R² = {winner_entry['r2_cv']:.4f})"
    )

    # Elegir instancia del modelo final
    final_model = stacking_model if "Stacking" in winner_name else ensemble_voting

    # Predicciones Out-Of-Fold (OOF) honestas en las 138 parcelas
    oof_preds = cross_val_predict(final_model, X_train_final, y_train, cv=kf)

    # Medir tiempo exacto de entrenamiento e inferencia para reporte de eficiencia
    t_fit_0 = time.perf_counter()
    rf_baseline.fit(X_train_final, y_train)
    et_model.fit(X_train_final, y_train)
    svr_model.fit(X_train_final, y_train)
    gbr_model.fit(X_train_final, y_train)
    lgbm_model.fit(X_train_final, y_train)
    final_model.fit(X_train_final, y_train)
    train_time_ms = round((time.perf_counter() - t_fit_0) * 1000.0, 2)

    t_inf_0 = time.perf_counter()
    pred_final_all = final_model.predict(X_all_final)
    inference_time_ms = round((time.perf_counter() - t_inf_0) * 1000.0, 3)

    pred_rf_base_all = rf_baseline.predict(X_all_final)

    # Importancia combinada de variables
    perm_imp = permutation_importance(final_model, X_train_final, y_train, n_repeats=15, random_state=42)
    tree_imp = (
        0.45 * et_model.feature_importances_
        + 0.35 * rf_baseline.feature_importances_
        + 0.20 * gbr_model.feature_importances_
    )
    tree_imp = tree_imp / tree_imp.sum()

    feature_importance_list = []
    for idx, col in enumerate(active_feature_cols):
        feature_importance_list.append(
            {
                "feature": col,
                "label": get_feature_label(col),
                "category": get_feature_category(col),
                "importance": round(float(tree_imp[idx]), 5),
                "importance_pct": round(float(tree_imp[idx] * 100), 2),
                "perm_importance": round(float(max(0.0, perm_imp.importances_mean[idx])), 5),
                "corr_with_target": round(float(X_train_final[col].corr(y_train)), 4),
                "mean_train": round(float(X_train_final[col].mean()), 3),
                "std_train": round(float(X_train_final[col].std()), 3),
                "min_val": round(float(df[col].min()), 3),
                "max_val": round(float(df[col].max()), 3),
            }
        )
    feature_importance_list.sort(key=lambda x: x["importance"], reverse=True)

    # Incertidumbre por parcela (desviación entre estimadores heterogéneos)
    sub_preds = np.vstack(
        [
            et_model.predict(X_all_final),
            rf_baseline.predict(X_all_final),
            svr_model.predict(X_all_final),
            gbr_model.predict(X_all_final),
        ]
    )
    pred_std_all = np.std(sub_preds, axis=0)
    rf_tree_preds = np.vstack([tree.predict(X_all_final.values) for tree in rf_baseline.estimators_[:100]])
    intra_std = np.std(rf_tree_preds, axis=0) * 0.40
    uncertainty_t_ha = np.clip(pred_std_all + intra_std, 0.11, 0.68)

    df["RENDIMIENTO_PREDICHO_T_HA"] = np.round(pred_final_all, 4)
    df["RENDIMIENTO_BASELINE_RF_T_HA"] = np.round(pred_rf_base_all, 4)
    df["INCERTIDUMBRE_T_HA"] = np.round(uncertainty_t_ha, 4)

    oof_map = dict(zip(train_df["ID_POLIGONO"], np.round(oof_preds, 4)))
    df["RENDIMIENTO_OOF_T_HA"] = df["ID_POLIGONO"].map(oof_map)
    df["RENDIMIENTO_FINAL_T_HA"] = df["RENDIMIENTO_T_HA"].fillna(df["RENDIMIENTO_PREDICHO_T_HA"]).round(4)
    df["PRODUCCION_ESTIMADA_TON"] = (df["AREA_HA"] * df["RENDIMIENTO_FINAL_T_HA"]).round(2)

    ndvi_cols = [c for c in base_feature_cols if c.startswith("ndvi_promedio_mes_")]
    prec_cols = [c for c in base_feature_cols if c.startswith("prec_")]
    tmax_cols = [c for c in base_feature_cols if c.startswith("tmax_")]

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
                "mean_all": round(float(df[c].mean()), 4),
                "mean_high_yield": round(float(train_df.loc[high_yield_mask, c].mean()), 4),
                "mean_low_yield": round(float(train_df.loc[low_yield_mask, c].mean()), 4),
            }
        )

    # Exportar CSV de las 59 predicciones oficiales
    pred_out = df[df["CONJUNTO"] == "PREDICCION"][
        [
            "ID_POLIGONO",
            "AREA_HA",
            "RENDIMIENTO_PREDICHO_T_HA",
            "INCERTIDUMBRE_T_HA",
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

    feature_means = X_train_final.mean()
    feature_stds = X_train_final.std().replace(0, 1)
    feature_corrs = {c: float(X_train_final[c].corr(y_train)) for c in active_feature_cols}
    top_15_features = [f["feature"] for f in feature_importance_list[:15]]
    imp_lookup = {f["feature"]: f["importance"] for f in feature_importance_list}

    # Cargar Shapefile y unir con las 197 parcelas
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
    centroids = gdf.geometry.centroid
    gdf["lat"] = np.round(centroids.y, 6)
    gdf["lon"] = np.round(centroids.x, 6)

    merged_gdf = gdf[["ID_POLIGONO", "lat", "lon", "geometry"]].merge(df, on="ID_POLIGONO", how="right")

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
        "rf_baseline": rf_baseline,
        "feature_cols": active_feature_cols,
        "use_engineered_features": use_eng,
        "feature_means": feature_means.to_dict(),
        "feature_stds": feature_stds.to_dict(),
    }
    model_file = BACKEND_ARTIFACTS_DIR / "best_model.joblib"
    joblib.dump(model_bundle, model_file, compress=3)
    model_size_kb = round(model_file.stat().st_size / 1024.0, 1)

    oof_scatter = []
    residuals = oof_preds - y_train.values
    within_05_pct = round(float((np.abs(residuals) <= 0.50).mean() * 100.0), 1)
    within_035_pct = round(float((np.abs(residuals) <= 0.35).mean() * 100.0), 1)

    for _, row in df[df["CONJUNTO"] == "ENTRENAMIENTO"].iterrows():
        oof_scatter.append(
            {
                "id": row["ID_POLIGONO"],
                "area_ha": round(float(row["AREA_HA"]), 2),
                "actual": round(float(row["RENDIMIENTO_T_HA"]), 3),
                "predicted_oof": round(float(row["RENDIMIENTO_OOF_T_HA"]), 3),
                "error": round(float(row["RENDIMIENTO_OOF_T_HA"] - row["RENDIMIENTO_T_HA"]), 3),
            }
        )

    # Auditoría de correlación máxima remanente en X_train_base
    corr_matrix = X_train_base.corr().abs()
    upper_tri = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
    max_pair_corr = round(float(upper_tri.max().max()), 4)
    mean_pair_corr = round(float(upper_tri.stack().mean()), 4)

    total_pipeline_ms = round((time.perf_counter() - t0_pipeline) * 1000.0, 1)

    summary_payload = {
        "project": "Reto AgroCebada FIRA 2026",
        "team": "Agrotec-Amanteca",
        "dataset_stats": {
            "total_parcelas": int(len(df)),
            "train_parcelas": int(len(train_df)),
            "pred_parcelas": int(len(pred_df)),
            "total_features_initial": 175,
            "total_features_selected": int(len(active_feature_cols)),
            "base_features_after_pearson": int(len(base_feature_cols)),
            "pearson_threshold": 0.90,
            "max_pairwise_corr": max_pair_corr,
            "mean_pairwise_corr": mean_pair_corr,
            "completeness_pct": 100.0,
            "collinearity_reduction_pct": round((1.0 - len(base_feature_cols) / 175.0) * 100.0, 1),
            "total_area_ha": round(float(df["AREA_HA"].sum()), 2),
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
            "total_production_ton": round(float(df["PRODUCCION_ESTIMADA_TON"].sum()), 2),
            "pred_production_ton": round(float(pred_out["PRODUCCION_ESTIMADA_TON"].sum()), 2),
        },
        "efficiency_metrics": {
            "train_time_ms": train_time_ms,
            "inference_197_ms": inference_time_ms,
            "inference_per_parcel_ms": round(inference_time_ms / len(df), 4),
            "total_pipeline_ms": total_pipeline_ms,
            "model_bundle_size_kb": model_size_kb,
            "oof_within_050_t_ha_pct": within_05_pct,
            "oof_within_035_t_ha_pct": within_035_pct,
            "mape_oof_pct": round(float(np.mean(np.abs(residuals / y_train.values)) * 100.0), 2),
        },
        "winner_model": winner_name,
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

    print("\n⚡ MÉTRICAS DE EFICIENCIA Y CALIDAD:")
    print(f"  - MAPE Out-Of-Fold (138 parcelas)     : {summary_payload['efficiency_metrics']['mape_oof_pct']:.2f}%")
    print(f"  - Parcelas con error OOF <= 0.50 t/ha : {within_05_pct:.1f}%")
    print(f"  - Tiempo de Inferencia (197 parcelas) : {inference_time_ms:.2f} ms")
    print(f"  - Peso del Modelo Comprimido          : {model_size_kb:.1f} KB")


if __name__ == "__main__":
    main()
