"""
generate_word_report.py
Genera el Documento Técnico Oficial editable en Microsoft Word (.docx)
con gráficas científicas a 300 DPI, tablas de resultados CV, auditoría de calidad
del dataset y catálogo completo de las 59 predicciones para el Reto AgroCebada FIRA 2026.
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


def set_cell_background(cell, hex_color: str):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def generate_figures(summary: dict):
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    plt.rcParams["font.sans-serif"] = "DejaVu Sans"
    plt.rcParams["axes.edgecolor"] = "#27272A"
    plt.rcParams["axes.linewidth"] = 0.9

    # 1. Figura 1: Dispersión Validación Out-Of-Fold (138 Parcelas)
    oof = summary["oof_validation_scatter"]
    actuals = [x["actual"] for x in oof]
    preds = [x["predicted_oof"] for x in oof]

    fig, ax = plt.subplots(figsize=(6.4, 4.4), dpi=300)
    ax.scatter(actuals, preds, c="#FF4F00", alpha=0.78, edgecolors="#111111", s=42, label="Parcelas (138 OOF)")
    ax.plot([2.0, 5.6], [2.0, 5.6], "--", color="#111111", linewidth=1.4, label="Ajuste Ideal (y = x)")
    ax.fill_between([2.0, 5.6], [1.5, 5.1], [2.5, 6.1], color="#111111", alpha=0.07, label="Banda ±0.50 t/ha")
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
    ax.set_title("Importancia Relativa de Variables Predictoras (Top 12)", fontsize=11, fontweight="bold", pad=10)
    ax.set_xlabel("Peso Relativo en el Ensamble (%)", fontsize=9.5, fontweight="bold")
    ax.tick_params(axis="y", labelsize=8.5)
    ax.grid(axis="x", linestyle=":", alpha=0.45, color="#71717A")
    for bar in bars:
        w = bar.get_width()
        ax.text(w + 0.18, bar.get_y() + bar.get_height() / 2, f"{w:.1f}%", va="center", fontsize=8, fontweight="bold")
    ax.set_xlim(0, max(vals) * 1.16)
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

    fig, ax = plt.subplots(figsize=(6.4, 3.9), dpi=300)
    ax.plot(months, high_y, "-o", color="#16A34A", linewidth=2.2, label="Parcelas Alto Rendimiento (≥4.35 t/ha)")
    ax.plot(months, all_y, "--s", color="#18181B", linewidth=1.6, label="Media Regional (197 Parcelas)")
    ax.plot(months, low_y, ":^", color="#FF4F00", linewidth=2.0, label="Parcelas Bajo Rendimiento (≤3.30 t/ha)")
    ax.set_title("Dinámica Fenológica Mensual del Vigor Satelital (NDVI)", fontsize=11, fontweight="bold", pad=10)
    ax.set_xlabel("Mes del Ciclo Agrícola", fontsize=9.5, fontweight="bold")
    ax.set_ylabel("Índice Satelital NDVI Promedio", fontsize=9.5, fontweight="bold")
    ax.grid(True, linestyle=":", alpha=0.45, color="#71717A")
    ax.legend(frameon=True, facecolor="#FFFFFF", edgecolor="#D4D4D8", fontsize=8.5)
    fig.tight_layout()
    fig3_path = FIGURES_DIR / "fig3_ndvi_phenology.png"
    fig.savefig(fig3_path, dpi=300)
    plt.close(fig)

    return fig1_path, fig2_path, fig3_path


def build_word_document():
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    pred_df = pd.read_csv(PRED_CSV_PATH)
    stats = summary["dataset_stats"]
    eff = summary["efficiency_metrics"]
    models_comp = summary["models_comparison"]
    winner = models_comp[0]

    fig1_path, fig2_path, fig3_path = generate_figures(summary)

    doc = Document()

    # Configurar márgenes editoriales limpios
    for section in doc.sections:
        section.top_margin = Inches(0.85)
        section.bottom_margin = Inches(0.85)
        section.left_margin = Inches(0.9)
        section.right_margin = Inches(0.9)

    normal_style = doc.styles["Normal"]
    normal_style.font.name = "Calibri"
    normal_style.font.size = Pt(10.5)
    normal_style.font.color.rgb = RGBColor(24, 24, 27)

    # PORTADA INSTITUCIONAL
    if LOGO_JPG_PATH.exists():
        p_logo = doc.add_paragraph()
        p_logo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_logo = p_logo.add_run()
        run_logo.add_picture(str(LOGO_JPG_PATH), width=Inches(2.2))

    p_kicker = doc.add_paragraph()
    p_kicker.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_k = p_kicker.add_run("RETO AGROCEBADA FIRA 2026 · DOCUMENTO TÉCNICO Y METODOLÓGICO")
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
    r_t.font.size = Pt(18)
    r_t.font.color.rgb = RGBColor(17, 17, 17)

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_s = p_sub.add_run(
        "Equipo: Agrotec-Amanteca  |  197 Parcelas Analizadas (138 Entrenamiento · 59 Predicción Ciega)\n"
        f"Modelo Ganador: {winner['model']} (MAE CV: {winner['mae_cv']:.4f} t/ha · RMSE CV: {winner['rmse_cv']:.4f} t/ha · R²: {winner['r2_cv']:.4f})"
    )
    r_s.font.size = Pt(10.5)
    r_s.font.color.rgb = RGBColor(82, 82, 91)

    # Tabla de Ficha Ejecutiva en Portada
    meta_table = doc.add_table(rows=6, cols=2)
    meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    meta_rows = [
        ("Equipo Competidor", "Agrotec-Amanteca (Célula de Datos Geoespaciales + Célula Web Cloud)"),
        ("Universo de Estudio", f"{stats['total_parcelas']} polígonos agrícolas ({stats['total_area_ha']:.2f} hectáreas totales)"),
        ("Partición Oficial FIRA", f"{stats['train_parcelas']} parcelas con target observado | {stats['pred_parcelas']} parcelas ciegas de prueba"),
        ("Calidad y Depuración de Datos", f"Reducción de 175 a {stats['base_features_after_pearson']} variables vía filtro de Pearson (|r| < 0.90), 0% valores nulos"),
        ("Precisión en Validación Cruzada", f"MAE = {winner['mae_cv']:.4f} t/ha | RMSE = {winner['rmse_cv']:.4f} t/ha | R² = {winner['r2_cv']:.4f} | MAPE OOF = {eff['mape_oof_pct']:.2f}%"),
        ("Eficiencia e Infraestructura Cloud", f"Inferencia de 197 parcelas en {eff['inference_197_ms']:.2f} ms | Backend en Railway + Dashboard Responsive en Vercel/Cloudflare"),
    ]
    for idx, (k, v) in enumerate(meta_rows):
        row_cells = meta_table.rows[idx].cells
        row_cells[0].text = k
        row_cells[1].text = v
        row_cells[0].paragraphs[0].runs[0].bold = True
        set_cell_background(row_cells[0], "F4F4F5")
        set_cell_background(row_cells[1], "FFFFFF")

    doc.add_page_break()

    # SECCIÓN 1: RESUMEN EJECUTIVO Y OBJETIVO
    h1 = doc.add_heading("1. Resumen Ejecutivo y Enfoque Analítico", level=1)
    h1.runs[0].font.color.rgb = RGBColor(17, 17, 17)
    doc.add_paragraph(
        "El presente documento técnico describe la arquitectura de ingeniería de datos geoespaciales, "
        "el protocolo de aseguramiento de calidad estadística, el diseño de modelos de aprendizaje automático "
        "(Machine Learning) y la plataforma web en la nube desarrollados por el equipo Agrotec-Amanteca para "
        "el Reto AgroCebada FIRA 2026. Nuestra prioridad absoluta se centró en tres ejes: (1) la máxima precisión "
        "predictiva fuera de muestra sobre las 59 parcelas ciegas, (2) la pureza estadística y trazabilidad física "
        "del dataset, y (3) la eficiencia computacional tanto en entrenamiento como en inferencia en tiempo real."
    )

    # SECCIÓN 2: CALIDAD DEL DATASET E INGENIERÍA DE DATOS GEOESPACIALES
    h2 = doc.add_heading("2. Calidad del Dataset e Ingeniería de Datos Espaciales", level=1)
    h2.runs[0].font.color.rgb = RGBColor(17, 17, 17)
    doc.add_paragraph(
        "La calidad de cualquier modelo predictivo agrícola está limitada por la fidelidad espacial y temporal "
        "de sus variables de entrada. Nuestro pipeline de Ingeniería de Datos procesó múltiples fuentes "
        "heterogéneas aplicando controles estrictos de integridad:"
    )

    bullets_s2 = [
        (
            "Extracción Zonal Climática con all_touched=True (Rasters CHIRPS 2022–2025): ",
            "Dado que las parcelas de cebada presentan áreas desde 1.5 ha hasta más de 18 ha y los píxeles de "
            "precipitación y temperatura máxima (Tmax) poseen resolución espacial kilométrica, se aplicó la regla "
            "all_touched=True. Esto garantiza que ningún polígono pequeño quede sin cobertura climática y que los "
            "bordes parcelarios capturen fielmente el gradiente microclimático.",
        ),
        (
            "Modelos Digitales de Elevación y Pendiente (INEGI CEM4 a 120 m): ",
            "Se extrajo la altitud media (msnm, rango 2,400–2,850 m) y la pendiente topográfica en grados para "
            "modelar la retención de humedad edáfica, el riesgo de heladas y la escorrentía superficial.",
        ),
        (
            "Reconstrucción e Interpolación Fenológica de Índices Satelitales (NDVI): ",
            "A partir de las observaciones multiespectrales libres de nubosidad, se consolidaron perfiles "
            "mensuales de NDVI (meses 1 y 5 al 11), cubriendo pre-siembra, emergencia, amacollamiento, "
            "encañado, espigamiento (agosto), llenado de grano y madurez fisiológica.",
        ),
        (
            "Control de Multicolinealidad mediante Filtro de Correlación de Pearson (|r| < 0.90): ",
            f"La matriz inicial contenía 175 variables brutas. Con N = 138 parcelas de entrenamiento, mantener "
            f"175 columnas colineales induce sobreajuste severo (p > N). El filtro de Pearson eliminó el "
            f"{stats['collinearity_reduction_pct']}% de variables redundantes, preservando {stats['base_features_after_pearson']} "
            f"predictores numéricos ortogonales con 100% de completitud (0 valores nulos) y una correlación "
            f"media entre pares de apenas {stats['mean_pairwise_corr']:.4f}.",
        ),
    ]
    for b_bold, b_text in bullets_s2:
        p = doc.add_paragraph(style="List Bullet")
        r1 = p.add_run(b_bold)
        r1.bold = True
        p.add_run(b_text)

    p_fig3 = doc.add_paragraph()
    p_fig3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_fig3.add_run().add_picture(str(fig3_path), width=Inches(5.8))
    p_cap3 = doc.add_paragraph("Figura 1. Curva fenológica mensual de NDVI comparando parcelas élite (≥4.35 t/ha), media regional y bajo rendimiento.")
    p_cap3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cap3.runs[0].italic = True
    p_cap3.runs[0].font.size = Pt(9)

    # SECCIÓN 3: ENTRENAMIENTO, VALIDACIÓN CRUZADA Y PRECISIÓN DE LAS PREDICCIONES
    h3 = doc.add_heading("3. Metodología de Modelado, Validación Cruzada y Eficiencia", level=1)
    h3.runs[0].font.color.rgb = RGBColor(17, 17, 17)
    doc.add_paragraph(
        "Para garantizar que el modelo seleccionado generalice con el menor error posible sobre las 59 parcelas "
        "ciegas, implementamos un protocolo de doble validación: (1) Validación Cruzada de 5 Pliegues (5-Fold CV, "
        "shuffle=True, random_state=42) y (2) Validación Cruzada Repetida 5×5 (25 evaluaciones independientes). "
        "Asimismo, se evaluó tanto el conjunto de 39 predictores base como el conjunto extendido a 44 variables "
        "con índices fenológicos sintéticos (Integral AUC de NDVI, tasa vegetativa e índice hidrotérmico)."
    )

    # Tabla Comparativa de Modelos
    t_mod = doc.add_table(rows=len(models_comp) + 1, cols=6)
    t_mod.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers_mod = ["Modelo / Arquitectura", "Variables", "MAE 5-Fold (t/ha)", "RMSE 5-Fold (t/ha)", "R² (5-Fold)", "Tiempo CV (ms)"]
    for c_idx, h_text in enumerate(headers_mod):
        cell = t_mod.rows[0].cells[c_idx]
        cell.text = h_text
        cell.paragraphs[0].runs[0].bold = True
        cell.paragraphs[0].runs[0].font.size = Pt(9)
        set_cell_background(cell, "E4E4E7")

    for r_idx, m in enumerate(models_comp, start=1):
        row = t_mod.rows[r_idx].cells
        row[0].text = m["model"]
        row[1].text = m["feature_set"]
        row[2].text = f"{m['mae_cv']:.4f} ± {m['mae_std']:.3f}"
        row[3].text = f"{m['rmse_cv']:.4f} ± {m['rmse_std']:.3f}"
        row[4].text = f"{m['r2_cv']:.4f}"
        row[5].text = f"{m['cv_time_ms']:.0f} ms"
        bg = "FFF7ED" if r_idx == 1 else ("FFFFFF" if r_idx % 2 == 1 else "FAFAFA")
        for c_i in range(6):
            set_cell_background(row[c_i], bg)
            row[c_i].paragraphs[0].runs[0].font.size = Pt(9)
            if r_idx == 1:
                row[c_i].paragraphs[0].runs[0].bold = True

    doc.add_paragraph()
    p_fig1 = doc.add_paragraph()
    p_fig1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_fig1.add_run().add_picture(str(fig1_path), width=Inches(5.6))
    p_cap1 = doc.add_paragraph(
        f"Figura 2. Desempeño Out-Of-Fold en las 138 parcelas de entrenamiento. "
        f"El {eff['oof_within_050_t_ha_pct']}% de las parcelas se ubica dentro de la banda de ±0.50 t/ha (MAPE = {eff['mape_oof_pct']}%)."
    )
    p_cap1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cap1.runs[0].italic = True
    p_cap1.runs[0].font.size = Pt(9)

    # SECCIÓN 4: INTERPRETABILIDAD AGRONÓMICA (XAI)
    h4 = doc.add_heading("4. Interpretabilidad Agronómica y Variables Determinantes", level=1)
    h4.runs[0].font.color.rgb = RGBColor(17, 17, 17)
    doc.add_paragraph(
        "El análisis de importancia combinada (reducción de impureza en árboles + importancia por permutación "
        "fuera de muestra) confirma que el modelo aprende relaciones agronómicas físicamente coherentes: "
        "la precipitación durante el establecimiento y encañado (mayo–julio), la regulación térmica pre-siembra "
        "y el vigor fotosintético NDVI entre mayo y agosto concentran el mayor poder predictivo."
    )

    p_fig2 = doc.add_paragraph()
    p_fig2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_fig2.add_run().add_picture(str(fig2_path), width=Inches(5.9))
    p_cap2 = doc.add_paragraph("Figura 3. Ranking de las 12 variables con mayor peso relativo en la predicción del rendimiento de cebada.")
    p_cap2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cap2.runs[0].italic = True
    p_cap2.runs[0].font.size = Pt(9)

    doc.add_page_break()

    # SECCIÓN 5: CATÁLOGO COMPLETO DE LAS 59 PREDICCIONES CIEGAS
    h5 = doc.add_heading("5. Catálogo Oficial de Predicciones (59 Parcelas Ciegas)", level=1)
    h5.runs[0].font.color.rgb = RGBColor(17, 17, 17)
    doc.add_paragraph(
        f"A continuación se presenta la tabla íntegra con las 59 predicciones generadas por el modelo ganador "
        f"({winner['model']}). El rendimiento medio predicho es de {stats['pred_yield_mean']:.3f} t/ha "
        f"(desviación estándar de {stats['pred_yield_std']:.3f} t/ha, rango {stats['pred_yield_min']:.2f} a "
        f"{stats['pred_yield_max']:.2f} t/ha), estimando una cosecha total de {stats['pred_production_ton']:.2f} "
        f"toneladas en las {stats['pred_area_ha']:.2f} hectáreas del conjunto de prueba."
    )

    t_pred = doc.add_table(rows=len(pred_df) + 1, cols=6)
    t_pred.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers_p = ["#", "ID Polígono", "Área (ha)", "Rendimiento Predicho (t/ha)", "Incertidumbre (±t/ha)", "Producción Estimada (ton)"]
    for c_idx, h_text in enumerate(headers_p):
        cell = t_pred.rows[0].cells[c_idx]
        cell.text = h_text
        cell.paragraphs[0].runs[0].bold = True
        cell.paragraphs[0].runs[0].font.size = Pt(8.5)
        set_cell_background(cell, "E4E4E7")

    for idx, row_data in pred_df.iterrows():
        row = t_pred.rows[idx + 1].cells
        row[0].text = str(idx + 1)
        row[1].text = str(row_data["ID_POLIGONO"])
        row[2].text = f"{float(row_data['AREA_HA']):.2f}"
        row[3].text = f"{float(row_data['RENDIMIENTO_T_HA']):.4f}"
        row[4].text = f"±{float(row_data['INCERTIDUMBRE_T_HA']):.3f}"
        row[5].text = f"{float(row_data['PRODUCCION_ESTIMADA_TON']):.2f}"
        bg = "FFFFFF" if idx % 2 == 0 else "F8FAFC"
        for c_i in range(6):
            set_cell_background(row[c_i], bg)
            row[c_i].paragraphs[0].runs[0].font.size = Pt(8.5)

    # SECCIÓN 6: ARQUITECTURA CLOUD Y DASHBOARD MULTI-DISPOSITIVO
    h6 = doc.add_heading("6. Arquitectura Cloud (Railway + Vercel/Cloudflare) y Diseño Swiss", level=1)
    h6.runs[0].font.color.rgb = RGBColor(17, 17, 17)
    doc.add_paragraph(
        "El sistema se estructuró bajo una arquitectura desacoplada lista para producción en la nube: "
        "(1) Backend API en FastAPI desplegable en Railway con inferencia en memoria (<5 ms) y simulador "
        "agronómico 'What-If' en vivo, y (2) Frontend React + Vite desplegable en Vercel o Cloudflare Pages, "
        "diseñado bajo el sistema estético Swiss (retícula técnica de 1px, tipografía grotesca tabular, "
        "cartografía satelital/topográfica Esri libre de API Keys y adaptabilidad responsive completa para "
        "smartphones, tablets, laptops, monitores y proyectores de auditorio)."
    )

    doc.save(DOCX_OUT_1)
    doc.save(DOCX_OUT_2)
    print(f"✅ Documento Técnico en Word (.docx) generado exitosamente en:\n  - {DOCX_OUT_1}\n  - {DOCX_OUT_2}")


if __name__ == "__main__":
    build_word_document()
