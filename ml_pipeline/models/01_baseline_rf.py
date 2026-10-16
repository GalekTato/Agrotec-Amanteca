"""
01_baseline_rf.py
Entrenamiento y evaluación por Validación Cruzada del Modelo Base (Random Forest)
para el Reto AgroCebada FIRA 2026 - Equipo Agrotec-Amanteca.
"""

from pathlib import Path
import sys
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import KFold, cross_validate

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# 1. Definir ruta del dataset optimizado
DATA_PATH = Path(r"D:\Agrotec\MATRIZ_FINAL_OPTIMIZADA.parquet")
if not DATA_PATH.exists():
    DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "processed" / "MATRIZ_FINAL_OPTIMIZADA.parquet"


def main():
    print("=" * 70)
    print("🌾 RETO AGROCEBADA 2026 - BASELINE RANDOM FOREST REGRESSOR")
    print("=" * 70)

    # 1. Leer el archivo MATRIZ_FINAL_OPTIMIZADA.parquet
    df = pd.read_parquet(DATA_PATH)
    print(f"\n[1] Dataset cargado exitosamente: {df.shape[0]} filas x {df.shape[1]} columnas.")

    # Eliminar columnas 100% vacías residuales (como 'Unnamed: 4' que tiene 197 NaNs)
    empty_cols = [col for col in df.columns if df[col].isna().all()]
    if empty_cols:
        print(f"    -> Eliminando columnas vacías residuales: {empty_cols}")
        df = df.drop(columns=empty_cols)

    # 2. Separar automáticamente el dataset en entrenamiento (138 filas) y predicción final (59 filas)
    train_df = df[df["RENDIMIENTO_T_HA"].notna()].copy()
    pred_df = df[df["RENDIMIENTO_T_HA"].isna()].copy()

    print(f"\n[2] División automática del dataset:")
    print(f"    -> Parcelas de Entrenamiento (con RENDIMIENTO_T_HA): {len(train_df)} filas")
    print(f"    -> Parcelas de Predicción Ciega (NaN en target):     {len(pred_df)} filas")

    # 3. Separar la variable objetivo (X e y)
    # Excluimos columnas identificadoras/metadatos no numéricos ('ID_POLIGONO', 'CONJUNTO') y el target
    non_feature_cols = ["ID_POLIGONO", "RENDIMIENTO_T_HA", "CONJUNTO"]
    feature_cols = [c for c in train_df.columns if c not in non_feature_cols]

    X_train = train_df[feature_cols]
    y_train = train_df["RENDIMIENTO_T_HA"]
    X_pred = pred_df[feature_cols]

    print(f"\n[3] Separación X e y completada:")
    print(f"    -> Total de variables predictoras limpias (X): {len(feature_cols)} columnas numéricas")
    print(f"    -> Valores nulos en X_train: {X_train.isna().sum().sum()} | en X_pred: {X_pred.isna().sum().sum()}")
    print(
        f"    -> Distribución de y_train (t/ha): Media = {y_train.mean():.3f} | "
        f"Std = {y_train.std():.3f} | Min = {y_train.min():.2f} | Max = {y_train.max():.2f}"
    )

    # 4. Definir y evaluar el modelo base (RandomForestRegressor) con Validación Cruzada (5-Fold CV)
    rf_baseline = RandomForestRegressor(
        n_estimators=300,
        max_depth=None,
        min_samples_split=4,
        min_samples_leaf=2,
        max_features="sqrt",
        random_state=42,
        n_jobs=-1,
    )

    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    scoring = {
        "mae": "neg_mean_absolute_error",
        "rmse": "neg_root_mean_squared_error",
        "r2": "r2",
    }

    cv_results = cross_validate(
        rf_baseline,
        X_train,
        y_train,
        cv=kf,
        scoring=scoring,
        return_train_score=True,
    )

    val_mae = -cv_results["test_mae"]
    val_rmse = -cv_results["test_rmse"]
    val_r2 = cv_results["test_r2"]
    train_mae = -cv_results["train_mae"]
    train_rmse = -cv_results["train_rmse"]

    print("\n" + "=" * 70)
    print("📊 RESULTADOS DE VALIDACIÓN CRUZADA (5-FOLD CROSS-VALIDATION)")
    print("=" * 70)
    for idx, (m_val, r_val, r2_v) in enumerate(zip(val_mae, val_rmse, val_r2), start=1):
        print(f"  Fold {idx}: MAE = {m_val:.4f} t/ha | RMSE = {r_val:.4f} t/ha | R² = {r2_v:.4f}")

    print("-" * 70)
    print(f"  ✅ MAE Validación (CV)  : {val_mae.mean():.4f} ± {val_mae.std():.4f} t/ha  (Train: {train_mae.mean():.4f})")
    print(f"  ✅ RMSE Validación (CV) : {val_rmse.mean():.4f} ± {val_rmse.std():.4f} t/ha  (Train: {train_rmse.mean():.4f})")
    print(f"  ✅ R² Validación (CV)   : {val_r2.mean():.4f} ± {val_r2.std():.4f}")
    print("=" * 70)

    # 5. Ajustar en las 138 parcelas para inspeccionar importancia de variables y generar predicción base
    rf_baseline.fit(X_train, y_train)
    importances = pd.Series(rf_baseline.feature_importances_, index=feature_cols).sort_values(ascending=False)

    print("\n🔥 TOP 10 VARIABLES MÁS IMPORTANTES (RANDOM FOREST BASELINE):")
    for rank, (feat, imp) in enumerate(importances.head(10).items(), start=1):
        print(f"  {rank:2d}. {feat:<25} -> Importancia: {imp:.4f} ({imp * 100:.2f}%)")

    pred_df["RENDIMIENTO_PREDICHO_T_HA"] = rf_baseline.predict(X_pred).round(4)
    print("\n🔍 Muestra de predicciones generadas para las 59 parcelas ciegas:")
    print(pred_df[["ID_POLIGONO", "AREA_HA", "RENDIMIENTO_PREDICHO_T_HA"]].head(8).to_string(index=False))


if __name__ == "__main__":
    main()
