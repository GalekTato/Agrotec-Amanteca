"""
generate_word_report.py
Genera el Documento Técnico Oficial editable en Microsoft Word (.docx)
con enfoque exhaustivo en Procedimiento Metodológico, Explicación de Modelos Evaluados,
Resultados Demostrativos de Precisión/Eficiencia, Stack de Tecnologías Implementadas
y Catálogo de las 59 Predicciones para el Reto AgroCebada FIRA 2026.
"""

import json
from pathlib import Path
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[2]
SUMMARY_PATH = ROOT_DIR / "backend" / "artifacts" / "metrics_summary.json"
PRED_CSV_PATH = ROOT_DIR / "data" / "processed" / "predicciones_59_parcelas.csv"
LOGO_JPG_PATH = ROOT_DIR / "frontend" / "public" / "logo_agrotec_amanteca.jpg"
FIGURES_DIR = ROOT_DIR / "data" / "processed" / "figures"

DOCX_OUT_1 = ROOT_DIR / "Documento_Tecnico_Agrotec_Amanteca_FIRA2026.docx"
DOCX_OUT_2 = ROOT_DIR.parent / "Documento_Tecnico_Agrotec_Amanteca_FIRA2026.docx"

TEAM_MEMBERS = [
    ("Gael Askary Razo Montañez", "Ciencia de Datos, Arquitectura Machine Learning e Integración Cloud"),
    ("Limhi Gerson López Momox", "Ingeniería de Datos Geoespaciales y Procesamiento ETL (Rasters CHIRPS / INEGI)"),
    ("Karla Yaneth Cruz Sandoval", "Modelado Estadístico, Validación Cruzada y Análisis Fenológico (NDVI / EVI)"),
    ("Arturo Huerta Maldonado", "Desarrollo Backend API (FastAPI) y Motor de Simulación Agronómica"),
    ("Juan Enrique Gutierrez Hernández", "Desarrollo Frontend Cartográfico (React + Leaflet) y Diseño de Interfaz"),
]


def set_cell_background(cell, hex_color: str):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def set_cell_margins(cell, top=80, bottom=80, left=120, right=120):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement("w:tcMar")
    for m_name, val in [("top", top), ("bottom", bottom), ("left", left), ("right", right)]:
        node = OxmlElement(f"w:{m_name}")
        node.set(qn("w:w"), str(val))
        node.set(qn("w:type"), "dxa")
        tcMar.append(node)
    tcPr.append(tcMar)


def generate_figures(summary: dict):
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    plt.rcParams["font.sans-serif"] = "DejaVu Sans"
    plt.rcParams["axes.edgecolor"] = "#27272A"
    plt.rcParams["axes.linewidth"] = 0.9

    # 1. Figura 1: Dispersión Validación Out-Of-Fold (138 Parcelas)
    oof = summary["oof_validation_scatter"]
    actuals = [x["actual"] for x in oof]
    preds = [x["predicted_oof"] for x in oof]

    fig, ax = plt.subplots(figsize=(6.5, 4.4), dpi=300)
    ax.scatter(actuals, preds, c="#FF4F00", alpha=0.80, edgecolors="#111111", s=44, label="Parcelas (138 OOF)")
    ax.plot([2.0, 5.6], [2.0, 5.6], "--", color="#111111", linewidth=1.4, label="Ajuste Ideal (y = x)")
    ax.fill_between([2.0, 5.6], [1.5, 5.1], [2.5, 6.1], color="#16A34A", alpha=0.10, label="Banda de Precisión ±0.50 t/ha (73.2%)")
    ax.set_title("Validación Cruzada Out-Of-Fold (138 Parcelas de Entrenamiento)", fontsize=11, fontweight="bold", pad=10)
    ax.set_xlabel("Rendimiento Observado en Campo (t/ha)", fontsize=9.5, fontweight="bold")
    ax.set_ylabel("Rendimiento Predicho Fuera de Muestra (t/ha)", fontsize=9.5, fontweight="bold")
    ax.set_xlim(1.85, 5.75)
    ax.set_ylim(1.85, 5.75)
    ax.grid(True, linestyle=":", alpha=0.45, color="#71717A")
    ax.legend(frameon=True, facecolor="#FFFFFF", edgecolor="#D4D4D8", fontsize=8.5)
    fig.tight_layout()
    fig1_path = FIGURES_DIR / "fig1_oof_validation.png"
    fig.savefig(fig1_path, dpi=300)
    plt.close(fig)

    # 2. Figura 2: Top 12 Variables Agronómicas
    feats = summary["feature_importances"][:12][::-1]
    labels = [f["label"] for f in feats]
    vals = [f["importance_pct"] for f in feats]
    colors = ["#FF4F00" if i >= 9 else "#18181B" for i in range(len(feats))]

    fig, ax = plt.subplots(figsize=(6.8, 4.4), dpi=300)
    bars = ax.barh(labels, vals, color=colors, height=0.68)
    ax.set_title("Importancia Relativa de Variables Predictoras V3 (Top 12)", fontsize=11, fontweight="bold", pad=10)
    ax.set_xlabel("Peso Relativo en el Ensamble (%)", fontsize=9.5, fontweight="bold")
    ax.tick_params(axis="y", labelsize=8.5)
    ax.grid(axis="x", linestyle=":", alpha=0.45, color="#71717A")
    for bar in bars:
        w = bar.get_width()
        ax.text(w + 0.18, bar.get_y() + bar.get_height() / 2, f"{w:.1f}%", va="center", fontsize=8, fontweight="bold")
    ax.set_xlim(0, max(vals) * 1.18)
    fig.tight_layout()
    fig2_path = FIGURES_DIR / "fig2_feature_importance.png"
    fig.savefig(fig2_path, dpi=300)
    plt.close(fig)

    # 3. Figura 3: Curvas Fenológicas NDVI
    bench = summary["ndvi_benchmarks"]
    months = [b["month_name"] for b in bench]
    high_y = [b["mean_high_yield"] for b in bench]
    all_y = [b["mean_all"] for b in bench]
    low_y = [b["mean_low_yield"] for b in bench]

    fig, ax = plt.subplots(figsize=(6.5, 3.9), dpi=300)
    ax.plot(months, high_y, "-o", color="#16A34A", linewidth=2.3, label="Parcelas Alto Rendimiento (≥4.35 t/ha)")
    ax.plot(months, all_y, "--s", color="#18181B", linewidth=1.7, label="Media Regional (197 Parcelas)")
    ax.plot(months, low_y, ":^", color="#FF4F00", linewidth=2.1, label="Parcelas Bajo Rendimiento (≤3.30 t/ha)")
    ax.set_title("Dinámica Fenológica Mensual del Vigor Satelital (NDVI)", fontsize=11, fontweight="bold", pad=10)
    ax.set_xlabel("Mes del Ciclo Agrícola", fontsize=9.5, fontweight="bold")
    ax.set_ylabel("Índice Satelital NDVI Promedio", fontsize=9.5, fontweight="bold")
    ax.grid(True, linestyle=":", alpha=0.45, color="#71717A")
    ax.legend(frameon=True, facecolor="#FFFFFF", edgecolor="#D4D4D8", fontsize=8.5)
    fig.tight_layout()
    fig3_path = FIGURES_DIR / "fig3_ndvi_phenology.png"
    fig.savefig(fig3_path, dpi=300)
    plt.close(fig)

    # 4. Figura 4: Comparativa de Modelos Evaluados (MAE y RMSE en 5-Fold CV)
    models_comp = summary["models_comparison"][:8][::-1]
    m_names = [m["model"].replace(" Regressor", "").replace(" (Smart-Pearson + IDW)", " V3") for m in models_comp]
    m_rmse = [m["rmse_cv"] for m in models_comp]
    m_mae = [m["mae_cv"] for m in models_comp]

    y_pos = np.arange(len(m_names))
    height = 0.36
    fig, ax = plt.subplots(figsize=(6.8, 4.3), dpi=300)
    b1 = ax.barh(y_pos + height / 2, m_rmse, height, label="RMSE 5-Fold CV (t/ha)", color="#18181B")
    b2 = ax.barh(y_pos - height / 2, m_mae, height, label="MAE 5-Fold CV (t/ha)", color="#FF4F00")
    ax.axvline(0.50, color="#16A34A", linestyle="--", linewidth=1.2, label="Umbral Meta RMSE (0.50 t/ha)")
    ax.set_yticks(y_pos)
    ax.set_yticklabels(m_names, fontsize=8.2, fontweight="bold")
    ax.set_xlabel("Error de Predicción en Validación Cruzada (t/ha — Menor es Mejor)", fontsize=9, fontweight="bold")
    ax.set_title("Comparativa Experimental de Arquitecturas Evaluadas (5-Fold CV)", fontsize=10.5, fontweight="bold", pad=10)
    ax.set_xlim(0.28, max(m_rmse) * 1.08)
    ax.grid(axis="x", linestyle=":", alpha=0.45, color="#71717A")
    ax.legend(frameon=True, facecolor="#FFFFFF", edgecolor="#D4D4D8", fontsize=8)
    fig.tight_layout()
    fig4_path = FIGURES_DIR / "fig4_models_comparison.png"
    fig.savefig(fig4_path, dpi=300)
    plt.close(fig)

    return fig1_path, fig2_path, fig3_path, fig4_path


def add_section_banner(doc, number_str: str, title_str: str):
    h = doc.add_heading(f"{number_str}. {title_str}", level=1)
    for r in h.runs:
        r.font.name = "Calibri"
        r.font.size = Pt(14.5)
        r.font.bold = True
        r.font.color.rgb = RGBColor(17, 17, 17)
    return h


def build_word_document():
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    pred_df = pd.read_csv(PRED_CSV_PATH)
    stats = summary["dataset_stats"]
    eff = summary["efficiency_metrics"]
    models_comp = summary["models_comparison"]
    winner = models_comp[0]

    fig1_path, fig2_path, fig3_path, fig4_path = generate_figures(summary)

    doc = Document()

    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.85)
        section.right_margin = Inches(0.85)

    normal_style = doc.styles["Normal"]
    normal_style.font.name = "Calibri"
    normal_style.font.size = Pt(10.5)
    normal_style.font.color.rgb = RGBColor(24, 24, 27)

    # =========================================================================
    # PORTADA EJECUTIVA E INSTITUCIONAL
    # =========================================================================
    if LOGO_JPG_PATH.exists():
        p_logo = doc.add_paragraph()
        p_logo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_logo = p_logo.add_run()
        run_logo.add_picture(str(LOGO_JPG_PATH), width=Inches(2.15))

    p_kicker = doc.add_paragraph()
    p_kicker.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_k = p_kicker.add_run("RETO AGROCEBADA FIRA 2026 · DOCUMENTO TÉCNICO, METODOLÓGICO Y DE RESULTADOS")
    r_k.bold = True
    r_k.font.size = Pt(10)
    r_k.font.color.rgb = RGBColor(255, 79, 0)

    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_t = p_title.add_run(
        "Sistema Geoespacial e Inteligencia Artificial de Alta Precisión para la "
        "Predicción del Rendimiento Agrícola de Cebada (t/ha)"
    )
    r_t.bold = True
    r_t.font.size = Pt(17.5)
    r_t.font.color.rgb = RGBColor(17, 17, 17)

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_s = p_sub.add_run(
        "Equipo: Agrotec-Amanteca  |  197 Parcelas Analizadas (138 Entrenamiento · 59 Predicción Ciega)\n"
        f"Arquitectura Ganadora: {winner['model']} (MAE CV: {winner['mae_cv']:.4f} t/ha · RMSE CV: {winner['rmse_cv']:.4f} t/ha · R²: {winner['r2_cv']:.4f})"
    )
    r_s.font.size = Pt(10)
    r_s.font.color.rgb = RGBColor(82, 82, 91)

    # Tabla de Integrantes del Equipo en Portada
    p_team_hdr = doc.add_paragraph()
    p_team_hdr.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_th = p_team_hdr.add_run("INTEGRANTES DEL EQUIPO AGROTEC-AMANTECA")
    r_th.bold = True
    r_th.font.size = Pt(9.5)
    r_th.font.color.rgb = RGBColor(17, 17, 17)

    team_table = doc.add_table(rows=len(TEAM_MEMBERS) + 1, cols=2)
    team_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr_t = team_table.rows[0].cells
    hdr_t[0].text = "Integrante"
    hdr_t[1].text = "Especialidad y Responsabilidad en el Proyecto"
    for c_i in range(2):
        hdr_t[c_i].paragraphs[0].runs[0].bold = True
        hdr_t[c_i].paragraphs[0].runs[0].font.size = Pt(9)
        hdr_t[c_i].paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
        set_cell_background(hdr_t[c_i], "18181B")
        set_cell_margins(hdr_t[c_i], top=60, bottom=60)

    for idx, (m_name, m_role) in enumerate(TEAM_MEMBERS, start=1):
        row_c = team_table.rows[idx].cells
        row_c[0].text = m_name
        row_c[1].text = m_role
        row_c[0].paragraphs[0].runs[0].bold = True
        bg = "FFFFFF" if idx % 2 == 1 else "F4F4F5"
        for c_i in range(2):
            row_c[c_i].paragraphs[0].runs[0].font.size = Pt(9)
            set_cell_background(row_c[c_i], bg)
            set_cell_margins(row_c[c_i], top=55, bottom=55)

    doc.add_paragraph()

    # Tabla de Ficha Ejecutiva de Resultados Demostrativos en Portada
    meta_table = doc.add_table(rows=7, cols=2)
    meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    meta_rows = [
        ("Universo Geoespacial Auditado", f"{stats['total_parcelas']} polígonos agrícolas ({stats['total_area_ha']:.2f} ha totales en EPSG:4326)"),
        ("Partición Oficial del Reto", f"{stats['train_parcelas']} parcelas con cosecha observada ({stats['train_area_ha']:.2f} ha) | {stats['pred_parcelas']} parcelas ciegas ({stats['pred_area_ha']:.2f} ha)"),
        ("Innovación en Selección de Variables", f"Filtro Leak-Free Smart-Pearson (|r| < 0.88) + IDW Espacial (k=7): de 175 a {stats['total_features_selected']} predictores (0% nulos)"),
        ("Precisión Validación Cruzada (5-Fold)", f"MAE = {winner['mae_cv']:.4f} t/ha | RMSE = {winner['rmse_cv']:.4f} t/ha (< 0.50 t/ha) | R² = {winner['r2_cv']:.4f} (61.0% varianza explicada)"),
        ("Certeza Práctica en Campo (OOF)", f"Precisión media del {100.0 - eff['mape_oof_pct']:.2f}% (MAPE = {eff['mape_oof_pct']:.2f}%) | {eff['oof_within_050_t_ha_pct']}% de parcelas con error ≤ ±0.50 t/ha"),
        ("Eficiencia Computacional V3", f"Inferencia de 197 parcelas en {eff['inference_197_ms']:.2f} ms (0.44 ms/parcela) | Modelo 70% más compacto ({eff['model_bundle_size_kb']:.1f} KB)"),
        ("Cosecha Estimada en 59 Ciegas", f"{stats['pred_production_ton']:.2f} toneladas totales (Rendimiento medio predicho: {stats['pred_yield_mean']:.3f} ± {stats['pred_yield_std']:.3f} t/ha)"),
    ]
    for idx, (k, v) in enumerate(meta_rows):
        row_cells = meta_table.rows[idx].cells
        row_cells[0].text = k
        row_cells[1].text = v
        row_cells[0].paragraphs[0].runs[0].bold = True
        row_cells[0].paragraphs[0].runs[0].font.size = Pt(9)
        row_cells[1].paragraphs[0].runs[0].font.size = Pt(9)
        set_cell_background(row_cells[0], "FFF7ED" if idx in (3, 4) else "F4F4F5")
        set_cell_background(row_cells[1], "FFFFFF")
        set_cell_margins(row_cells[0], top=55, bottom=55)
        set_cell_margins(row_cells[1], top=55, bottom=55)

    doc.add_page_break()

    # =========================================================================
    # SECCIÓN 1: PROCEDIMIENTO METODOLÓGICO PASO A PASO
    # =========================================================================
    add_section_banner(doc, "1", "Procedimiento Metodológico e Ingeniería de Datos Geoespaciales")
    doc.add_paragraph(
        "El equipo Agrotec-Amanteca estructuró un procedimiento científico reproducible en cinco etapas "
        "secuenciales, diseñado para transformar datos satelitales, climáticos y topográficos crudos en "
        "predicciones agronómicas de alta precisión libres de fuga de información (Data Leakage):"
    )

    procedimiento_steps = [
        (
            "Etapa 1 — Estandarización Cartográfica y Topográfica (Shapefiles + INEGI CEM4): ",
            "Se reproyectaron los 197 polígonos parcelarios al sistema de referencia WGS84 (EPSG:4326), "
            "calculando sus centroides exactos (latitud, longitud) y superficie productiva (AREA_HA, totalizando "
            "1,560.60 ha). A partir del Continuo de Elevaciones Mexicano de INEGI (resolución 120 m), se extrajo "
            "la altitud media (2,400 a 2,850 msnm) y la pendiente topográfica en grados, variables críticas para "
            "modelar la escorrentía superficial y el riesgo de heladas por inversión térmica.",
        ),
        (
            "Etapa 2 — Extracción Zonal Climática Multianual con all_touched=True (Rasters CHIRPS 2022–2025): ",
            "Para evitar que parcelas de pequeña superficie (1.5 a 3.0 ha) perdieran cobertura al cruzar sus "
            "geometrías con rasters climáticos de mayor tamaño de píxel, se implementó la extracción zonal con "
            "all_touched=True sobre las series mensuales de precipitación acumulada (mm), temperatura máxima (Tmax °C) "
            "y temperatura mínima (Tmin °C) del periodo 2022–2025.",
        ),
        (
            "Etapa 3 — Reconstrucción Fenológica Satelital e Índices Agronómicos Sintéticos (NDVI y EVI): ",
            "Se consolidaron las curvas mensuales de vigor fotosintético NDVI y EVI del ciclo agrícola. "
            "Adicionalmente, se diseñaron 5 variables sintéticas fila-por-fila basadas en fisiología de cereales: "
            "(1) Integral Fenológica bajo la curva de verano (ndvi_auc_verano, meses 5 a 10), (2) Tasa de desarrollo "
            "vegetativo (agosto menos mayo), (3) Tasa de senescencia y llenado de grano (agosto menos octubre), "
            "(4) Índice Hidrotérmico de De Martonne (Precipitación / [Tmax + 10]) y (5) Índice de Retención Hídrica "
            "por Pendiente.",
        ),
        (
            "Etapa 4 — Descubrimiento y Corrección del Sesgo de Selección mediante Leak-Free Smart-Pearson (|r| < 0.88): ",
            "Al auditar la matriz inicial de 175 columnas frente al filtro de Pearson secuencial tradicional (|r| < 0.90), "
            "detectamos un hallazgo fundamental: recorrer las columnas de izquierda a derecha sin ordenarlas primero "
            "por su relevancia con el rendimiento descartaba accidentalmente todas las temperaturas mínimas (tmin_*, "
            "indispensables para detectar daño por heladas en espigamiento) y el vigor temprano evi_promedio_mes_5 "
            "(r = +0.692 con el rendimiento). Para solucionarlo sin incurrir en fuga de datos, creamos el transformador "
            "LeakFreeSmartPearson, que dentro de cada pliegue de entrenamiento ordena los predictores por |r(X_i, y)| "
            "y poda pares colineales con |r(X_i, X_j)| >= 0.88.",
        ),
        (
            "Etapa 5 — Autocorrelación Geoespacial por Ponderación Inversa a la Distancia (IDW k=7): ",
            "El rendimiento agrícola exhibe continuidad microclimática y edáfica entre parcelas cercanas. "
            "Incorporamos la variable spatial_idw_yield, que calcula el rendimiento promedio ponderado por el inverso "
            "de la distancia euclidiana (1 / d^1.5) de las k = 7 parcelas de entrenamiento más cercanas, excluyendo "
            "estrictamente la propia parcela evaluada (Leave-One-Out / Out-Of-Fold) para garantizar cero sobreajuste.",
        ),
    ]
    for title_b, body_t in procedimiento_steps:
        p = doc.add_paragraph(style="List Bullet")
        r1 = p.add_run(title_b)
        r1.bold = True
        p.add_run(body_t)

    p_fig3 = doc.add_paragraph()
    p_fig3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_fig3.add_run().add_picture(str(fig3_path), width=Inches(5.9))
    p_cap3 = doc.add_paragraph(
        "Figura 1. Dinámica fenológica mensual del NDVI comparando parcelas élite (≥4.35 t/ha), media regional y parcelas de bajo rendimiento (≤3.30 t/ha)."
    )
    p_cap3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cap3.runs[0].italic = True
    p_cap3.runs[0].font.size = Pt(9)

    doc.add_page_break()

    # =========================================================================
    # SECCIÓN 2: EXPLICACIÓN DE CADA MODELO EVALUADO Y ELECCIÓN DEL GANADOR
    # =========================================================================
    add_section_banner(doc, "2", "Modelos Evaluados, Fundamento Algorítmico y Justificación del Ganador")
    doc.add_paragraph(
        "Con el propósito de encontrar la arquitectura óptima sobre las N = 138 parcelas de entrenamiento, "
        "se evaluaron 10 configuraciones utilizando Validación Cruzada de 5 Pliegues (5-Fold CV, shuffle=True, "
        "random_state=42) y Validación Cruzada Repetida 5×5 (25 particiones independientes). A continuación se "
        "explica en qué consiste cada modelo revisado y el criterio técnico por el cual se eligió al ganador:"
    )

    models_explanation = [
        (
            "1. Ensemble Agrotec V3 (Voting Heterogéneo + Smart-Pearson + IDW) — [MODELO GANADOR SELECCIONADO]: ",
            "Integra cuatro familias matemáticas complementarias mediante votación ponderada: Extra Trees Podado (40%), "
            "Random Forest Podado (25%), Support Vector Regressor con Kernel RBF y RobustScaler (20%), y Gradient Boosting "
            "Regressor (15%), operando sobre las variables del filtro Leak-Free Smart-Pearson + IDW Espacial. "
            "¿Por qué quedó seleccionado?: Obtuvo el menor error absoluto (MAE = 0.3576 t/ha) y cuadrático (RMSE = 0.4984 t/ha, "
            "rompiendo la barrera de 0.50 t/ha) y el mayor coeficiente de determinación (R² = 0.6098). Al combinar árboles "
            "aleatorizados con un hiperplano de margen geométrico (SVR) y boosting secuencial, cancela los errores "
            "individuales de varianza y sesgo.",
        ),
        (
            "2. Stacking Meta-Ensemble V3 (Meta-Regresor RidgeCV L2): ",
            "Arquitectura jerárquica de dos niveles en la que un regresor lineal penalizado (RidgeCV) aprende a combinar "
            "las predicciones Out-Of-Fold de los cuatro estimadores base. Alcanzó el segundo mejor resultado global "
            "(MAE = 0.3606 t/ha, RMSE = 0.5006 t/ha, R² = 0.6095), validando la potencia del ensamble, aunque requiere "
            "5.5 veces más tiempo de cómputo que el Voting Regressor.",
        ),
        (
            "3. Extra Trees Regressor (Extremely Randomized Trees): ",
            "Construye múltiples árboles de decisión (n_estimators=220, max_depth=8) seleccionando aleatoriamente tanto "
            "el subconjunto de variables como el umbral exacto de corte en cada nodo. Fue el mejor algoritmo individual "
            "(MAE = 0.3682 t/ha, RMSE = 0.5077 t/ha en V3) por su alta resistencia al sobreajuste en muestras pequeñas.",
        ),
        (
            "4. Random Forest Regressor (Modelo Base / Baseline): ",
            "Ensamble clásico por Bagging (muestreo bootstrap con reemplazo) y selección de cortes óptimos CART. "
            "Evaluado sobre las 39 variables iniciales registró MAE = 0.3742 t/ha, RMSE = 0.5139 t/ha y R² = 0.5859. "
            "Constituyó el punto de referencia oficial contra el cual medimos cada mejora del proyecto.",
        ),
        (
            "5. Support Vector Regressor (SVR Kernel RBF + RobustScaler): ",
            "Estandariza las variables utilizando mediana y rango intercuartílico (resistente a valores extremos) y las "
            "proyecta mediante un kernel radial gaussiano para ajustar un tubo ε-insensible (C=2.2, ε=0.06). Logró un "
            "MAE competitivo de 0.3682 t/ha y proporciona continuidad suave al simulador agronómico.",
        ),
        (
            "6. Gradient Boosting Regressor (GBR) y LightGBM Regressor: ",
            "Modelos de boosting secuencial donde cada árbol de baja profundidad (max_depth=3–4) se entrena sobre los "
            "residuos pseudo-gradiente acumulados. GBR alcanzó RMSE = 0.5095 t/ha (R² = 0.5952), aportando el 15% del "
            "ensamble ganador, mientras que LightGBM (RMSE = 0.5494 t/ha) mostró mayor sensibilidad al tamaño muestral.",
        ),
        (
            "7. RidgeCV (Regresión Lineal con Regularización de Tikhonov L2): ",
            "Modelo lineal paramétrico con búsqueda automática de penalización α (MAE = 0.3819 t/ha, RMSE = 0.5180 t/ha, "
            "R² = 0.5802). Sirvió como línea de control para demostrar el +3.0% adicional de varianza no lineal capturada "
            "por el Ensemble Agrotec V3.",
        ),
    ]
    for m_title, m_desc in models_explanation:
        p = doc.add_paragraph(style="List Bullet")
        r1 = p.add_run(m_title)
        r1.bold = True
        p.add_run(m_desc)

    p_fig4 = doc.add_paragraph()
    p_fig4.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_fig4.add_run().add_picture(str(fig4_path), width=Inches(6.0))
    p_cap4 = doc.add_paragraph(
        "Figura 2. Comparativa experimental de error MAE y RMSE (5-Fold CV) entre las arquitecturas evaluadas. El Ensemble Agrotec V3 es el único que rompe el umbral de RMSE < 0.50 t/ha."
    )
    p_cap4.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cap4.runs[0].italic = True
    p_cap4.runs[0].font.size = Pt(9)

    doc.add_page_break()

    # =========================================================================
    # SECCIÓN 3: RESULTADOS DEMOSTRATIVOS DE PRECISIÓN Y EFICIENCIA
    # =========================================================================
    add_section_banner(doc, "3", "Resultados Demostrativos de Precisión, Calidad y Eficiencia Computacional")
    doc.add_paragraph(
        "La siguiente tabla resume las métricas obtenidas por las 10 configuraciones en Validación Cruzada "
        "de 5 Pliegues (5-Fold CV) y Validación Cruzada Repetida 5×5 (25 ejecuciones), junto con su tiempo "
        "real de ejecución:"
    )

    t_mod = doc.add_table(rows=len(models_comp) + 1, cols=7)
    t_mod.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers_mod = [
        "Modelo / Arquitectura",
        "Set Variables",
        "MAE 5-Fold",
        "RMSE 5-Fold",
        "R² (5-Fold)",
        "RMSE 5×5 Rep.",
        "Tiempo CV",
    ]
    for c_idx, h_text in enumerate(headers_mod):
        cell = t_mod.rows[0].cells[c_idx]
        cell.text = h_text
        cell.paragraphs[0].runs[0].bold = True
        cell.paragraphs[0].runs[0].font.size = Pt(8.5)
        cell.paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
        set_cell_background(cell, "18181B")
        set_cell_margins(cell, top=55, bottom=55, left=80, right=80)

    for r_idx, m in enumerate(models_comp, start=1):
        row = t_mod.rows[r_idx].cells
        row[0].text = m["model"]
        row[1].text = m["feature_set"]
        row[2].text = f"{m['mae_cv']:.4f} ± {m['mae_std']:.3f}"
        row[3].text = f"{m['rmse_cv']:.4f} ± {m['rmse_std']:.3f}"
        row[4].text = f"{m['r2_cv']:.4f}"
        row[5].text = f"{m['rmse_repeated_cv']:.4f}"
        row[6].text = f"{m['cv_time_ms']:.0f} ms"
        bg = "FFF7ED" if r_idx == 1 else ("FFFFFF" if r_idx % 2 == 1 else "F4F4F5")
        for c_i in range(7):
            set_cell_background(row[c_i], bg)
            set_cell_margins(row[c_i], top=50, bottom=50, left=80, right=80)
            row[c_i].paragraphs[0].runs[0].font.size = Pt(8.5)
            if r_idx == 1:
                row[c_i].paragraphs[0].runs[0].bold = True

    doc.add_paragraph()
    p_fig1 = doc.add_paragraph()
    p_fig1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_fig1.add_run().add_picture(str(fig1_path), width=Inches(5.5))
    p_cap1 = doc.add_paragraph(
        f"Figura 3. Auditoría Out-Of-Fold en las 138 parcelas de entrenamiento. "
        f"El {eff['oof_within_050_t_ha_pct']}% de las parcelas se ubica dentro de ±0.50 t/ha respecto al valor real (Precisión media = {100.0 - eff['mape_oof_pct']:.2f}%)."
    )
    p_cap1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cap1.runs[0].italic = True
    p_cap1.runs[0].font.size = Pt(9)

    p_fig2 = doc.add_paragraph()
    p_fig2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_fig2.add_run().add_picture(str(fig2_path), width=Inches(5.8))
    p_cap2 = doc.add_paragraph(
        "Figura 4. Ranking de las 12 variables con mayor importancia relativa en el Ensemble Agrotec V3."
    )
    p_cap2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cap2.runs[0].italic = True
    p_cap2.runs[0].font.size = Pt(9)

    doc.add_page_break()

    # =========================================================================
    # SECCIÓN 4: TECNOLOGÍAS IMPLEMENTADAS EN EL SISTEMA
    # =========================================================================
    add_section_banner(doc, "4", "Resumen de Tecnologías Implementadas (Stack Tecnológico Completo)")
    doc.add_paragraph(
        "Para traducir el modelo predictivo en una herramienta de decisión ágil, auditable y accesible desde "
        "cualquier dispositivo (PC, laptop, pantalla de auditorio, tablet y smartphone), se implementó el "
        "siguiente ecosistema tecnológico:"
    )

    tech_table = doc.add_table(rows=5, cols=3)
    tech_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    t_headers = ["Capa del Sistema", "Tecnologías y Librerías Clave", "Función y Aporte Técnico en el Proyecto"]
    for c_i, h_str in enumerate(t_headers):
        cell = tech_table.rows[0].cells[c_i]
        cell.text = h_str
        cell.paragraphs[0].runs[0].bold = True
        cell.paragraphs[0].runs[0].font.size = Pt(9)
        cell.paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
        set_cell_background(cell, "18181B")
        set_cell_margins(cell, top=60, bottom=60)

    tech_rows = [
        (
            "1. Ciencia de Datos y Machine Learning",
            "Python 3.11, Scikit-Learn, LightGBM, SciPy Spatial (cdist IDW), NumPy, Pandas, Joblib",
            "Entrenamiento del Ensemble Agrotec V3, transformador LeakFreeSmartPearson (|r| < 0.88), validación cruzada 5-Fold y 5×5 Repetida y cuantificación de incertidumbre por parcela.",
        ),
        (
            "2. Ingeniería Geoespacial y Clima",
            "GeoPandas, Shapely, Rasterio (all_touched=True), Rasters CHIRPS, INEGI CEM4, Apache Parquet",
            "Procesamiento de los 197 polígonos en EPSG:4326, extracción zonal pluvial/térmica sin pérdida en parcelas pequeñas y almacenamiento columnar comprimido.",
        ),
        (
            "3. Backend API y Simulador en Vivo",
            "FastAPI, Pydantic V2, Uvicorn ASGI, Lifespan Memory Cache, Docker",
            "Servicio RESTful de ultra-baja latencia (<5 ms) libre de warnings de deprecación, que recalcula en tiempo real escenarios 'What-If' de NDVI, lluvia CHIRPS y anomalía térmica Tmax °C.",
        ),
        (
            "4. Frontend Cartográfico y Reporteo",
            "React 18, Vite 6, Tailwind CSS, LeafletJS, Esri ArcGIS Online, Recharts, python-docx, Matplotlib",
            "Dashboard bajo estética Swiss (Modo Claro) e Industrial (Modo Oscuro) con 3 capas satelitales/topográficas libres de API Key y generación automatizada de informes Word a 300 DPI.",
        ),
    ]
    for r_i, (c1, c2, c3) in enumerate(tech_rows, start=1):
        row_c = tech_table.rows[r_i].cells
        row_c[0].text = c1
        row_c[1].text = c2
        row_c[2].text = c3
        row_c[0].paragraphs[0].runs[0].bold = True
        bg = "FFFFFF" if r_i % 2 == 1 else "F4F4F5"
        for col_j in range(3):
            row_c[col_j].paragraphs[0].runs[0].font.size = Pt(9)
            set_cell_background(row_c[col_j], bg)
            set_cell_margins(row_c[col_j], top=55, bottom=55)

    doc.add_page_break()

    # =========================================================================
    # SECCIÓN 5: CATÁLOGO OFICIAL DE LAS 59 PREDICCIONES CIEGAS
    # =========================================================================
    add_section_banner(doc, "5", "Catálogo Oficial de Predicciones (59 Parcelas de Prueba Ciega)")
    doc.add_paragraph(
        f"A continuación se presenta el padrón completo de las 59 parcelas ciegas pronosticadas por el "
        f"modelo ganador ({winner['model']}). El rendimiento medio estimado es de {stats['pred_yield_mean']:.3f} t/ha "
        f"(rango de {stats['pred_yield_min']:.2f} a {stats['pred_yield_max']:.2f} t/ha), proyectando una cosecha "
        f"total de {stats['pred_production_ton']:.2f} toneladas de cebada en las {stats['pred_area_ha']:.2f} hectáreas evaluadas."
    )

    t_pred = doc.add_table(rows=len(pred_df) + 1, cols=6)
    t_pred.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers_p = [
        "Folio",
        "ID Polígono",
        "Superficie (ha)",
        "Rendimiento Predicho (t/ha)",
        "Incertidumbre (±t/ha)",
        "Producción Estimada (ton)",
    ]
    for c_idx, h_text in enumerate(headers_p):
        cell = t_pred.rows[0].cells[c_idx]
        cell.text = h_text
        cell.paragraphs[0].runs[0].bold = True
        cell.paragraphs[0].runs[0].font.size = Pt(8.5)
        cell.paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
        set_cell_background(cell, "18181B")
        set_cell_margins(cell, top=45, bottom=45)

    for idx, row_data in pred_df.iterrows():
        row = t_pred.rows[idx + 1].cells
        row[0].text = f"{idx + 1:02d}"
        row[1].text = str(row_data["ID_POLIGONO"])
        row[2].text = f"{float(row_data['AREA_HA']):.2f}"
        row[3].text = f"{float(row_data['RENDIMIENTO_T_HA']):.4f}"
        row[4].text = f"±{float(row_data['INCERTIDUMBRE_T_HA']):.3f}"
        row[5].text = f"{float(row_data['PRODUCCION_ESTIMADA_TON']):.2f}"
        row[1].paragraphs[0].runs[0].bold = True
        row[3].paragraphs[0].runs[0].bold = True
        bg = "FFFFFF" if idx % 2 == 0 else "F8FAFC"
        for c_i in range(6):
            set_cell_background(row[c_i], bg)
            set_cell_margins(row[c_i], top=38, bottom=38)
            row[c_i].paragraphs[0].runs[0].font.size = Pt(8.5)

    doc.add_paragraph()
    p_footer = doc.add_paragraph()
    p_footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_f = p_footer.add_run(
        "© 2026 Equipo Agrotec-Amanteca · Todos los derechos reservados · Reto AgroCebada FIRA 2026\n"
        "Integrantes: Gael Askary Razo Montañez · Limhi Gerson López Momox · Karla Yaneth Cruz Sandoval · "
        "Arturo Huerta Maldonado · Juan Enrique Gutierrez Hernández"
    )
    r_f.font.size = Pt(8.5)
    r_f.font.color.rgb = RGBColor(113, 113, 122)

    doc.save(DOCX_OUT_1)
    doc.save(DOCX_OUT_2)
    print(f"✅ Documento Técnico en Word (.docx) V3.1 generado exitosamente en:\n  - {DOCX_OUT_1}\n  - {DOCX_OUT_2}")


if __name__ == "__main__":
    build_word_document()
