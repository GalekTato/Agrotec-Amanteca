"""
agro_core.py
Núcleo compartido entre el pipeline de entrenamiento (02_train_and_export_artifacts.py)
y el servidor de inferencia FastAPI (backend/main.py).
Garantiza coherencia exacta en ingeniería de variables, selección Smart-Pearson,
interpolación espacial IDW y simulación de escenarios.
"""

from typing import List
import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist
from sklearn.base import BaseEstimator, TransformerMixin

NDVI_GRID = [-25, -20, -15, -10, -5, 0, 5, 10, 15, 20, 25]
PREC_GRID = [-40, -35, -30, -25, -20, -15, -10, -5, 0, 5, 10, 15, 20, 25, 30, 35, 40]
TMAX_GRID = [-3.0, -2.5, -2.0, -1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]


def add_agronomic_features(df_in: pd.DataFrame) -> pd.DataFrame:
    """
    Construye 5 índices agronómicos de dominio fila-por-fila (100% libre de data leakage).
    """
    d = df_in.copy()

    def _c(col_name: str, default: float = 0.0) -> pd.Series:
        if col_name in d.columns:
            return d[col_name].astype(float)
        return pd.Series(np.full(len(d), default, dtype=float), index=d.index)

    # 1. Integral Fenológica bajo la curva de NDVI en ventana reproductiva (Mayo a Octubre)
    d["ndvi_auc_verano"] = (
        0.5 * _c("ndvi_promedio_mes_5", 0.25)
        + _c("ndvi_promedio_mes_6", 0.35)
        + _c("ndvi_promedio_mes_7", 0.50)
        + _c("ndvi_promedio_mes_8", 0.60)
        + _c("ndvi_promedio_mes_9", 0.52)
        + 0.5 * _c("ndvi_promedio_mes_10", 0.38)
    )
    # 2. Velocidad de desarrollo vegetativo (Emergencia -> Espigamiento)
    d["ndvi_tasa_vegetativa"] = _c("ndvi_promedio_mes_8", 0.60) - _c("ndvi_promedio_mes_5", 0.25)
    # 3. Tasa de llenado de grano y senescencia (Espigamiento -> Madurez)
    d["ndvi_caida_madurez"] = _c("ndvi_promedio_mes_8", 0.60) - _c("ndvi_promedio_mes_10", 0.38)
    # 4. Índice Hidrotérmico de De Martonne (disponibilidad hídrica frente a estrés térmico)
    prec_clave = _c("prec_2022_07", 95.0) + _c("prec_2023_05", 48.0) + _c("prec_2022_05", 42.0)
    tmax_clave = (_c("tmax_2022_03", 24.0) + _c("tmax_2023_03", 24.0) + _c("tmax_2024_03", 24.0)) / 3.0
    d["indice_hidrotermico"] = prec_clave / np.maximum(tmax_clave + 10.0, 1.0)
    # 5. Retención topográfica de humedad (infiltración vs escorrentía por pendiente)
    d["retencion_topografica"] = prec_clave / (1.0 + np.maximum(_c("pendiente_promedio", 3.0), 0.0))
    return d


def select_smart_pearson_columns(
    X_df: pd.DataFrame, y_ser: pd.Series, corr_thresh: float = 0.88, top_k: int = 22
) -> List[str]:
    """
    Filtro Smart-Pearson guiado por relevancia con la variable objetivo:
    Ordena las variables por |r(X_i, y)| dentro del conjunto de entrenamiento y poda
    pares colineales con |r(X_i, X_j)| >= corr_thresh.
    """
    corrs = X_df.apply(lambda c: abs(c.corr(y_ser))).fillna(0.0).sort_values(ascending=False)
    selected: List[str] = []
    corr_mat = X_df.corr().abs().fillna(0.0)
    for col in corrs.index:
        if len(selected) == 0:
            selected.append(col)
        else:
            if all(corr_mat.loc[col, s] < corr_thresh for s in selected):
                selected.append(col)
        if len(selected) >= top_k:
            break
    return selected


def compute_spatial_idw_feature(
    coords_target: np.ndarray,
    coords_ref: np.ndarray,
    y_ref: np.ndarray,
    k_neighbors: int = 7,
    power: float = 1.5,
) -> np.ndarray:
    """
    Calcula el rendimiento promedio ponderado por el inverso de la distancia (IDW)
    de las k parcelas de referencia más cercanas, excluyendo coincidencias exactas (d <= 1e-8)
    para evitar fuga de datos cuando se evalúa sobre el propio conjunto de entrenamiento.
    """
    dists = cdist(coords_target, coords_ref)
    idw_vals = np.zeros(len(coords_target), dtype=float)
    for i in range(len(coords_target)):
        d = dists[i]
        mask = d > 1e-8
        d_valid = d[mask]
        y_valid = y_ref[mask]
        idx = np.argsort(d_valid)[:k_neighbors]
        w = 1.0 / (np.maximum(d_valid[idx], 1e-5) ** power)
        idw_vals[i] = float(np.sum(w * y_valid[idx]) / np.sum(w))
    return idw_vals


class LeakFreeSmartPearsonIDW(BaseEstimator, TransformerMixin):
    """
    Transformador Scikit-Learn 100% libre de fuga de datos (Data Leakage):
    1. Calcula el potencial microclimático vecinal (IDW k=7, power=1.5) usando únicamente las etiquetas del fold de entrenamiento.
    2. Ejecuta la selección Smart-Pearson (|r| < corr_thresh) estrictamente dentro del fold de entrenamiento.
    """

    def __init__(self, corr_thresh: float = 0.88, top_k: int = 22, k_neighbors: int = 7, power: float = 1.5):
        self.corr_thresh = corr_thresh
        self.top_k = top_k
        self.k_neighbors = k_neighbors
        self.power = power

    def fit(self, X: pd.DataFrame, y: pd.Series):
        self.coords_train_ = X[["lat", "lon"]].values
        self.y_train_ = np.asarray(y, dtype=float)
        feat_df = X.drop(columns=["lat", "lon"], errors="ignore")
        self.selected_cols_ = select_smart_pearson_columns(
            feat_df, pd.Series(self.y_train_, index=X.index), self.corr_thresh, self.top_k
        )
        return self

    def transform(self, X: pd.DataFrame) -> np.ndarray:
        coords = X[["lat", "lon"]].values
        idw_vals = compute_spatial_idw_feature(
            coords, self.coords_train_, self.y_train_, k_neighbors=self.k_neighbors, power=self.power
        )
        X_sel = X[self.selected_cols_].copy()
        X_sel["spatial_idw_yield"] = idw_vals
        return X_sel.values

    def get_feature_names_out(self) -> List[str]:
        return list(self.selected_cols_) + ["spatial_idw_yield"]


def apply_scenario_df(
    df_in: pd.DataFrame,
    ndvi_delta_pct: float = 0.0,
    prec_delta_pct: float = 0.0,
    tmax_delta_c: float = 0.0,
) -> pd.DataFrame:
    """
    Aplica perturbaciones de escenario sobre un DataFrame de parcelas y recalcula
    los 5 índices agronómicos derivados.
    """
    sim_df = df_in.copy()
    for col in list(sim_df.columns):
        if (col.startswith("ndvi_promedio_mes_") or col.startswith("evi_promedio_mes_")) and ndvi_delta_pct != 0.0:
            sim_df[col] = np.clip(sim_df[col].astype(float) * (1.0 + ndvi_delta_pct / 100.0), 0.05, 0.95)
        elif col.startswith("prec_") and prec_delta_pct != 0.0:
            sim_df[col] = np.maximum(0.0, sim_df[col].astype(float) * (1.0 + prec_delta_pct / 100.0))
        elif (col.startswith("tmax_") or col.startswith("tmin_")) and tmax_delta_c != 0.0:
            sim_df[col] = sim_df[col].astype(float) + tmax_delta_c

    return add_agronomic_features(sim_df)
