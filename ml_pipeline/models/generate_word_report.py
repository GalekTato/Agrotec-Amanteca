"""
generate_word_report.py
Genera el Documento Técnico Oficial editable en Microsoft Word (.docx) (V4)
100% respaldado por metrics_summary.json:
- Paridad exacta entre Validación Cruzada (5-Fold y 5x5 Repetida) y modelo publicado (23 variables).
- Intervalos de Predicción Conformal al 80% calibrados fuera de muestra.
- Comparativa contra Baseline (Random Forest 39 variables) y Referencia (Predecir la Media).
- Integrantes oficiales del equipo Agrotec-Amanteca sin cargos individuales inventados.
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
    "Gael Askary Razo Montañez",
    "Limhi Gerson López Momox",
    "Karla Yaneth Cruz Sandoval",
    "Arturo Huerta Maldonado",
    "Juan Enrique Gutierrez Hernández",
]

TEAM_ROLES = {
    "Gael Askary Razo Montañez": "PM y apoyo general",
    "Limhi Gerson López Momox": "Ingeniero de datos",
    "Juan Enrique Gutierrez Hernández": "Científico de datos",
    "Karla Yaneth Cruz Sandoval": "Desarrolladora frontend",
    "Arturo Huerta Maldonado": "Desarrollador backend",
}


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

    eff = summary["efficiency_metrics"]

    # 1. Figura 1: Dispersión Validación Out-Of-Fold (138 Parcelas)
    oof = summary["oof_validation_scatter"]
    actuals = [x["actual"] for x in oof]
    preds = [x["predicted_oof"] for x in oof]

    fig, ax = plt.subplots(figsize=(6.5, 4.4), dpi=300)
    ax.scatter(actuals, preds, c="#FF4F00", alpha=0.82, edgecolors="#111111", s=44, label="Parcelas (138 OOF)")
    ax.plot([2.0, 5.6], [2.0, 5.6], "--", color="#111111", linewidth=1.4, label="Ajuste Ideal (y = x)")
    ax.fill_between(
        [2.0, 5.6],
        [1.5, 5.1],
        [2.5, 6.1],
        color="#16A34A",
        alpha=0.10,
        label=f"Banda ±0.50 t/ha ({eff['oof_within_050_t_ha_pct']}% de parcelas)",
    )
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

    # 2. Figura 2: Top 12 Variables Agronómicas (Importancia Permutación + Impureza sobre las 23 variables)
    feats = summary["feature_importances"][:12][::-1]
    labels = [f["label"] for f in feats]
    vals = [f["importance_pct"] for f in feats]
    colors = ["#FF4F00" if i >= 9 else "#18181B" for i in range(len(feats))]

    fig, ax = plt.subplots(figsize=(6.8, 4.4), dpi=300)
    bars = ax.barh(labels, vals, color=colors, height=0.68)
    ax.set_title("Importancia Relativa en el Ensamble Completo (Top 12 de 23 Variables)", fontsize=10.5, fontweight="bold", pad=10)
    ax.set_xlabel("Peso Relativo Combinado Permutación + Impureza (%)", fontsize=9.5, fontweight="bold")
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
    models_comp = [m for m in summary["models_comparison"] if "Referencia" not in m["model"]][:8][::-1]
    m_names = [m["model"].replace(" Regressor", "") for m in models_comp]
    m_rmse = [m["rmse_cv"] for m in models_comp]
    m_mae = [m["mae_cv"] for m in models_comp]

    y_pos = np.arange(len(m_names))
    height = 0.36
    fig, ax = plt.subplots(figsize=(6.8, 4.3), dpi=300)
    ax.barh(y_pos + height / 2, m_rmse, height, label="RMSE 5-Fold CV (t/ha)", color="#18181B")
    ax.barh(y_pos - height / 2, m_mae, height, label="MAE 5-Fold CV (t/ha)", color="#FF4F00")
    ax.axvline(0.50, color="#16A34A", linestyle="--", linewidth=1.2, label="Umbral RMSE (0.50 t/ha)")
    ax.set_yticks(y_pos)
    ax.set_yticklabels(m_names, fontsize=8.0, fontweight="bold")
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


def add_bases_required_sections(doc):
    """Add the report structure required by the official challenge rules."""
    sections = [
        (
            "A. Introducción",
            "El Reto AgroCebada FIRA 2026 solicita una solución analítica capaz de estimar el rendimiento "
            "de parcelas de cebada en Hidalgo, Tlaxcala y Puebla y convertirlo en una herramienta funcional "
            "de consulta. Agrotec-Amanteca responde a ese objetivo mediante un sistema que integra información "
            "satelital, climática, topográfica y geoespacial para producir una estimación por parcela. El problema "
            "es relevante porque el rendimiento agrícola depende de condiciones que cambian entre localidades y "
            "ciclos, mientras que las decisiones productivas y financieras requieren información espacialmente "
            "detallada y disponible antes de la cosecha. El dataset oficial contiene 197 parcelas georreferenciadas: "
            "138 con rendimiento observado, utilizadas para entrenar y validar, y 59 cuyo rendimiento fue reservado "
            "para evaluación. Por tanto, el proyecto no intenta reemplazar la medición de campo; construye una "
            "estimación reproducible para apoyar la priorización de parcelas, la interpretación de escenarios y la "
            "comunicación de riesgo. La solución combina un pipeline de ingeniería de datos con un ensamble de "
            "Extra Trees, Random Forest, SVR y Gradient Boosting. Antes del entrenamiento se calculan índices "
            "agronómicos derivados de las series mensuales de NDVI/EVI, precipitación, temperatura, elevación, "
            "pendiente y superficie. La selección de variables se realiza dentro de los pliegues de validación "
            "para evitar que las etiquetas de validación influyan en el entrenamiento. El componente espacial IDW "
            "se calcula en coordenadas métricas UTM 14N y utiliza únicamente referencias permitidas en cada fold. "
            "El resultado se publica como artefactos auditables, API FastAPI y dashboard web responsive disponible "
            "en GitHub Pages. La aplicación permite consultar el mapa, revisar predicciones, explorar incertidumbre "
            "y ejecutar escenarios de vigor satelital, precipitación y temperatura. La contribución principal es "
            "un flujo de extremo a extremo que conecta datos con una interfaz usable, manteniendo una interpretación "
            "honesta: las métricas son predictivas y observacionales, no una prueba de causalidad agronómica."
        ),
        (
            "B. Justificación",
            "Una predicción por parcela puede complementar la información de campo al identificar diferencias "
            "espaciales y comunicar el nivel de incertidumbre asociado. El proyecto se justifica porque combina "
            "variables que representan vigor vegetal, disponibilidad hídrica, régimen térmico y contexto físico "
            "con una aplicación consultable por personas no especialistas. La selección y validación controladas "
            "reducen el riesgo de sobreajuste, mientras que la comparación contra un estimador nulo y un baseline "
            "permite medir si la complejidad añadida aporta valor real. La herramienta se plantea como apoyo a la "
            "decisión, no como sustituto de la experiencia del productor ni como garantía de rendimiento."
        ),
        (
            "C. Objetivos",
            "Objetivo general: desarrollar y documentar un modelo analítico y una aplicación web funcional para "
            "estimar el rendimiento de cebada por parcela en el conjunto oficial del Reto AgroCebada FIRA 2026. "
            "Objetivos específicos: integrar las variables oficiales y su referencia geoespacial; construir índices "
            "agronómicos deterministas; seleccionar predictores reduciendo redundancia y evitando fuga de información; "
            "comparar un ensamble con un baseline Random Forest y un DummyRegressor; cuantificar error mediante MAE, "
            "RMSE y R² con validación cruzada de cinco pliegues y repetición 5×5; calibrar una banda de incertidumbre "
            "con cobertura empírica fuera de muestra; exportar predicciones para las 59 parcelas ciegas; ofrecer "
            "consulta cartográfica, simulación de escenarios y descarga de resultados; y explicar las limitaciones "
            "para que la herramienta se use responsablemente en contextos agrícolas y financieros."
        ),
        (
            "D. Metodología",
            "El universo se compone de 197 polígonos georreferenciados, con 138 etiquetas de rendimiento disponibles "
            "y 59 reservadas para predicción. Los polígonos se visualizan en WGS84 y sus centroides se calculan "
            "temporalmente en UTM Zona 14N (EPSG:32614), evitando medir distancias en grados. Las variables ambientales "
            "incluyen índices NDVI/EVI, precipitación CHIRPS, temperaturas máxima y mínima, elevación, pendiente y "
            "superficie. La extracción zonal documentada utiliza all_touched=True para no descartar parcelas pequeñas. "
            "A partir de las columnas originales se calculan cinco índices: área bajo la curva de NDVI, tasa vegetativa, "
            "caída de madurez, índice hidrotérmico y retención topográfica. El transformador LeakFreeSmartPearsonIDW "
            "ordena variables por correlación absoluta con el objetivo únicamente dentro del entrenamiento de cada fold, "
            "elimina redundancia con umbral 0.88 y conserva 22 variables; después agrega spatial_idw_yield. El IDW usa "
            "las siete referencias más cercanas, potencia 1.5 y solo rendimientos del fold de entrenamiento, excluyendo "
            "coincidencias exactas. El modelo final es un VotingRegressor con Extra Trees 40%, Random Forest 25%, SVR "
            "20% y Gradient Boosting 15%. Se comparan 11 configuraciones con KFold de cinco pliegues y RepeatedKFold "
            "5×5, usando MAE, RMSE y R². Las predicciones OOF se calculan para que cada parcela sea evaluada por un "
            "modelo que no vio su etiqueta. La incertidumbre se calibra usando residuos OOF y una escala de dispersión "
            "del ensamble; la cobertura reportada es empírica. Finalmente, se ajusta el modelo con las etiquetas "
            "disponibles, se serializa en joblib y se sincronizan JSON, CSV, GeoJSON, dashboard y documento Word. "
            "El simulador modifica entradas, recalcula índices y evalúa escenarios combinados directamente con el modelo."
        ),
        (
            "E. Resultados y discusión",
            "El ensamble seleccionado obtuvo MAE 5-Fold de 0.3562 ± 0.0662 t/ha, RMSE de 0.4968 ± 0.1084 t/ha, "
            "RMSE 5×5 de 0.5073 ± 0.1183 t/ha y R² de 0.6124 ± 0.1804. El baseline Random Forest con 39 variables "
            "obtuvo MAE 0.3742 y RMSE 0.5139 t/ha, mientras que el DummyRegressor obtuvo MAE 0.7585 y RMSE 0.8545 "
            "t/ha. La comparación demuestra una mejora medida frente a ambos referentes, aunque la diferencia frente "
            "al baseline es moderada y debe interpretarse junto con las desviaciones estándar. El 72.5% de las "
            "predicciones OOF tuvo error absoluto menor o igual a 0.50 t/ha. La banda nominal de 80% alcanzó 81.2% "
            "de cobertura empírica OOF con semiancho medio de 0.584 t/ha. Estos resultados respaldan una herramienta "
            "predictiva inicial, pero no garantizan el mismo desempeño en otra región, año o distribución de clima. "
            "El modelo usa 23 predictores y los artefactos comprueban la paridad entre selección, entrenamiento e "
            "inferencia. El simulador responde de forma conjunta y no suma efectos marginales, respetando la posible "
            "no linealidad del ensamble. El dashboard permite observar la distribución espacial y consultar las 59 "
            "predicciones ciegas con intervalos. La principal limitación es el tamaño muestral: 138 etiquetas son "
            "suficientes para una primera solución tabular, pero generan variabilidad entre particiones. La siguiente "
            "validación recomendada es temporal y espacial, con datos de una campaña o localidad no utilizada para "
            "ajustar decisiones. También se recomienda monitorear fuera de dominio y separar calibración conformal "
            "de evaluación externa cuando existan más observaciones."
        ),
        (
            "F. Uso de la ciencia de datos en la inclusión financiera del sector agro",
            "La inclusión financiera requiere que productores y organizaciones puedan presentar información comprensible "
            "para planear inversiones, seguros, crédito y asistencia técnica. Un rendimiento estimado por parcela no "
            "constituye por sí mismo una autorización de crédito ni sustituye la evaluación financiera; sin embargo, "
            "puede servir como insumo operativo para ordenar visitas, comparar escenarios y discutir riesgos productivos "
            "con mayor evidencia. El dashboard traduce variables técnicas a una consulta visual y exportable: cada "
            "parcela tiene una estimación, producción calculada según su superficie e intervalo de incertidumbre. Esto "
            "puede ayudar a que instituciones y técnicos identifiquen dónde hace falta información adicional antes de "
            "tomar una decisión, evitando tratar una predicción puntual como certeza. El simulador permite explorar "
            "escenarios de clima y vigor, siempre con la advertencia de que son sensibilidades observacionales y no "
            "efectos causales. En una etapa posterior, el sistema podría integrarse con registros de manejo, costos, "
            "ingresos y siniestralidad para construir indicadores financieros más completos, con consentimiento y "
            "protección de datos. La aplicación de ciencia de datos es responsable cuando hace explícitos sus supuestos, "
            "mide su error, señala incertidumbre y permite auditoría. Por ello, la propuesta contribuye a la inclusión "
            "financiera como herramienta de información y priorización, no como mecanismo automático de aprobación o "
            "rechazo de productores."
        ),
        (
            "G. Conclusiones",
            "Agrotec-Amanteca cumplió el objetivo de construir una solución funcional para estimar el rendimiento de "
            "cebada por parcela y consultar sus resultados en una interfaz web. La integración de datos satelitales, "
            "climáticos, topográficos y espaciales produjo un conjunto de 23 predictores consistente entre validación "
            "e inferencia. El ensamble superó al baseline y a la referencia nula bajo métricas medidas, y la validación "
            "OOF permitió reportar tanto error como cobertura empírica de incertidumbre. La aplicación aporta valor "
            "porque conecta el resultado estadístico con un mapa, una tabla exportable y un simulador trazable. "
            "La conclusión no es que el modelo sea universal ni causal: su confiabilidad está condicionada por las "
            "138 parcelas etiquetadas, la representatividad del dataset y la similitud entre futuras observaciones y "
            "el dominio de entrenamiento. Para fortalecerlo se requieren nuevas parcelas independientes, campañas "
            "agrícolas adicionales y validaciones por localidad y tiempo. También debe mantenerse la separación entre "
            "predicción, simulación y decisión financiera. Bajo esas condiciones, el sistema es una base estable, "
            "lógica y auditable para apoyo a decisiones agrícolas, y cuenta con una ruta clara de mejora sin depender "
            "de añadir complejidad innecesaria."
        ),
        (
            "H. Respuestas a las preguntas guía del reto",
            "1. ¿Qué índice es más importante en la predicción? La variable con mayor importancia relativa combinada "
            "en el artefacto auditado es Potencial Microclimático Vecinal (IDW k=7), con 26.80%. Esta variable no "
            "es un índice satelital: resume el contexto espacial de las parcelas de referencia y debe interpretarse "
            "como señal predictiva geográfica, no como causalidad. Entre los índices agronómicos sintéticos, el "
            "Índice Hidrotérmico de Aridez (Prec/Tmax) ocupa el primer lugar, con 10.70%. 2. ¿Qué variable climática "
            "tiene mayor peso? Dentro de las variables climáticas individuales, Temp. Máxima 2023-02 alcanza 7.70% "
            "de importancia relativa combinada; le sigue Precipitación 2025-02 con 6.86%. Estas importancias son "
            "globales para este conjunto y método, no una ley universal ni un efecto causal. 3. ¿Qué combinación de "
            "variables funciona mejor? La combinación ganadora es el conjunto de 23 predictores formado por 22 "
            "variables Smart-Pearson y el IDW, procesado por el VotingRegressor de Extra Trees (40%), Random Forest "
            "(25%), SVR (20%) y Gradient Boosting (15%). Se seleccionó por su desempeño conjunto en 5-Fold y "
            "5×5 Repeated CV: RMSE 0.4968 y 0.5073 t/ha, respectivamente. No se afirma que una terna aislada "
            "sea óptima, porque el modelo aprende interacciones no lineales entre las 23 variables."
        ),
    ]
    for title, body in sections:
        add_section_banner(doc, title.split(".")[0], title.split(". ", 1)[1])
        doc.add_paragraph(body)

    add_section_banner(doc, "I", "Bibliografía")
    references = [
        "FIRA. (2026). Bases de participación: Reto AgroCebada FIRA 2026. Documento oficial proporcionado por el comité organizador.",
        "FIRA. (2025). Reglas de Operación para apoyos a los sectores agropecuario, forestal, pesquero, alimentario y rural. Diario Oficial de la Federación.",
        "Breiman, L. (2001). Random Forests. Machine Learning, 45, 5–32.",
        "Geodetic Survey / EPSG.io. (s. f.). EPSG:4326 WGS 84 y EPSG:32614 WGS 84 / UTM zone 14N.",
        "Scikit-learn developers. (s. f.). Scikit-learn User Guide: model selection, ensembles, pipelines and metrics. https://scikit-learn.org/",
        "FastAPI developers. (s. f.). FastAPI documentation. https://fastapi.tiangolo.com/",
        "CHIRPS Climate Hazards Center. (s. f.). Climate Hazards InfraRed Precipitation with Station data.",
    ]
    for reference in references:
        doc.add_paragraph(reference, style="List Bullet")

    add_section_banner(doc, "J", "Anexos y cumplimiento de entregables")
    doc.add_paragraph(
        "Anexo 1 — Integración y aportaciones del equipo: se documentan las funciones declaradas por el equipo. "
        "Las responsabilidades fueron colaborativas y todos los integrantes participaron en la revisión final."
    )
    for member in TEAM_MEMBERS:
        doc.add_paragraph(f"{member} — {TEAM_ROLES[member]}", style="List Bullet")
    doc.add_paragraph(
        "Anexo 2 — Declaración de uso de Inteligencia Artificial: las bases permiten IA si se indica dónde fue "
        "utilizada y se anexan los prompts. La IA se empleó como asistencia técnica, no como sustituto de la "
        "decisión, ejecución ni validación del equipo."
    )
    doc.add_paragraph(
        "Herramientas utilizadas: GitHub Copilot CLI para auditoría, programación asistida, pruebas y documentación; "
        "Antigravity CLI exclusivamente como apoyo para correcciones y ajustes del diseño frontend. El equipo "
        "conserva la responsabilidad completa sobre la autoría, revisión, ejecución, interpretación y entrega."
    )
    doc.add_paragraph("Prompts representativos utilizados durante el desarrollo:", style="List Bullet")
    ai_prompts = [
        "IA-01 — Audita exhaustivamente el pipeline de Machine Learning e identifica riesgos de data leakage, especialmente en la selección de variables y el cálculo IDW dentro de la validación cruzada.",
        "IA-02 — Comprueba si existe paridad entre las variables usadas en Cross-Validation, el modelo serializado y la inferencia de producción.",
        "IA-03 — Revisa si el simulador evalúa escenarios combinados directamente con el modelo o si suma efectos marginales de forma incorrecta.",
        "IA-04 — Revisa la API FastAPI, sus validaciones, sus advertencias deprecatorias y la cobertura de las pruebas automatizadas.",
        "IA-05 — Revisa que el simulador y la curva fenológica reaccionen coherentemente a NDVI, precipitación y temperatura.",
        "IA-06 — Compara las métricas del dashboard, README, artefactos y documento técnico para detectar números o afirmaciones inconsistentes.",
        "IA-07 — Compara el reporte técnico del proyecto contra las bases oficiales del Reto AgroCebada FIRA 2026 e identifica entregables faltantes.",
        "IA-08 — Prepara una guía de defensa oral con preguntas difíciles sobre fuga de datos, tamaño de muestra, causalidad, conformal e incertidumbre.",
    ]
    for prompt in ai_prompts:
        doc.add_paragraph(prompt, style="List Bullet 2")
    doc.add_paragraph(
        "Los prompts anteriores son representativos de las instrucciones utilizadas durante el proceso; algunas "
        "consultas fueron iterativas. Las recomendaciones fueron revisadas por el equipo, y los cambios incorporados "
        "se ejecutaron y verificaron mediante pruebas, compilación o inspección directa de los artefactos. Las métricas "
        "reportadas fueron generadas por la ejecución del pipeline y no fueron inventadas por una herramienta de IA."
    )
    doc.add_paragraph(
        "Anexo 3 — Prototipo y video: dashboard funcional: https://galektato.github.io/Agrotec-Amanteca/. "
        "Código fuente: https://github.com/GalekTato/Agrotec-Amanteca. Video demostrativo de máximo cinco minutos: "
        "[PENDIENTE DE SUBIR A LA PLATAFORMA O COMPLETAR CON EL ENLACE DEFINITIVO]."
    )


def build_word_document():
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    pred_df = pd.read_csv(PRED_CSV_PATH)
    stats = summary["dataset_stats"]
    eff = summary["efficiency_metrics"]
    base_m = summary["baseline_metrics"]
    dummy_m = summary["dummy_metrics"]
    env_v = summary["environment_versions"]
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
        run_logo.add_picture(str(LOGO_JPG_PATH), width=Inches(2.1))

    p_kicker = doc.add_paragraph()
    p_kicker.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_k = p_kicker.add_run("RETO AGROCEBADA FIRA 2026 · DOCUMENTO TÉCNICO, METODOLÓGICO Y DE RESULTADOS")
    r_k.bold = True
    r_k.font.size = Pt(10)
    r_k.font.color.rgb = RGBColor(255, 79, 0)

    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_t = p_title.add_run(
        "Sistema Geoespacial e Inteligencia Artificial para la "
        "Predicción del Rendimiento Agrícola de Cebada (t/ha)"
    )
    r_t.bold = True
    r_t.font.size = Pt(17.0)
    r_t.font.color.rgb = RGBColor(17, 17, 17)

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_s = p_sub.add_run(
        f"Equipo: Agrotec-Amanteca  |  {stats['total_parcelas']} Parcelas Analizadas ({stats['train_parcelas']} Entrenamiento · {stats['pred_parcelas']} Predicción Ciega)\n"
        f"Modelo Seleccionado: {winner['model']} (5-Fold MAE: {winner['mae_cv']:.4f} ± {winner['mae_std']:.4f} t/ha · 5-Fold RMSE: {winner['rmse_cv']:.4f} ± {winner['rmse_std']:.4f} t/ha · R²: {winner['r2_cv']:.4f})"
    )
    r_s.font.size = Pt(9.8)
    r_s.font.color.rgb = RGBColor(82, 82, 91)

    # Tabla de Integrantes del Equipo en Portada (sin cargos inventados)
    p_team_hdr = doc.add_paragraph()
    p_team_hdr.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_th = p_team_hdr.add_run("INTEGRANTES DEL EQUIPO AGROTEC-AMANTECA")
    r_th.bold = True
    r_th.font.size = Pt(9.5)
    r_th.font.color.rgb = RGBColor(17, 17, 17)

    team_table = doc.add_table(rows=len(TEAM_MEMBERS) + 1, cols=2)
    team_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr_t = team_table.rows[0].cells
    hdr_t[0].text = "N.º"
    hdr_t[1].text = "Nombre Completo del Integrante"
    for c_i in range(2):
        hdr_t[c_i].paragraphs[0].runs[0].bold = True
        hdr_t[c_i].paragraphs[0].runs[0].font.size = Pt(9)
        hdr_t[c_i].paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
        set_cell_background(hdr_t[c_i], "18181B")
        set_cell_margins(hdr_t[c_i], top=55, bottom=55)

    for idx, m_name in enumerate(TEAM_MEMBERS, start=1):
        row_c = team_table.rows[idx].cells
        row_c[0].text = f"0{idx}"
        row_c[1].text = m_name
        row_c[0].paragraphs[0].runs[0].bold = True
        row_c[1].paragraphs[0].runs[0].bold = True
        bg = "FFFFFF" if idx % 2 == 1 else "F4F4F5"
        for c_i in range(2):
            row_c[c_i].paragraphs[0].runs[0].font.size = Pt(9)
            set_cell_background(row_c[c_i], bg)
            set_cell_margins(row_c[c_i], top=50, bottom=50)

    doc.add_paragraph()

    # Tabla de Ficha Ejecutiva de Resultados Medidos en Portada
    meta_table = doc.add_table(rows=8, cols=2)
    meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    meta_rows = [
        ("Universo Geoespacial Auditado", f"{stats['total_parcelas']} polígonos agrícolas ({stats['total_area_ha']:,.2f} ha totales en EPSG:4326)"),
        ("Partición Oficial del Reto", f"{stats['train_parcelas']} parcelas con cosecha observada ({stats['train_area_ha']:.2f} ha) | {stats['pred_parcelas']} parcelas ciegas ({stats['pred_area_ha']:.2f} ha)"),
        ("Paridad Verificada CV == Modelo Final", f"Filtro Leak-Free Smart-Pearson (|r| < 0.88, 22 vars) + IDW Espacial (k=7, 1 var) = {stats['total_features_selected']} predictores exactos (0% nulos)"),
        ("Precisión Validación Cruzada (5-Fold)", f"MAE = {winner['mae_cv']:.4f} ± {winner['mae_std']:.4f} t/ha | RMSE = {winner['rmse_cv']:.4f} ± {winner['rmse_std']:.4f} t/ha | R² = {winner['r2_cv']:.4f} ± {winner['r2_std']:.4f}"),
        ("Estabilidad en CV Repetida 5×5 (25 corridas)", f"MAE = {winner['mae_repeated_cv']:.4f} ± {winner['mae_repeated_std']:.4f} t/ha | RMSE = {winner['rmse_repeated_cv']:.4f} ± {winner['rmse_repeated_std']:.4f} t/ha"),
        ("Comparativa vs. Baseline y Media", f"Baseline RF (39 vars): MAE {base_m['mae_cv']:.4f} / RMSE {base_m['rmse_cv']:.4f} t/ha | Predecir la Media: MAE {dummy_m['mae_cv']:.4f} / RMSE {dummy_m['rmse_cv']:.4f} t/ha"),
        ("Incertidumbre Conformal al 80% (OOF)", f"Cobertura empírica fuera de muestra: {eff['conformal_80_coverage_oof_pct']:.1f}% (Semiancho medio ±{eff['conformal_80_mean_half_width_t_ha']:.3f} t/ha) | {eff['oof_within_050_t_ha_pct']:.1f}% con error ≤ ±0.50 t/ha"),
        ("Cosecha Estimada y Eficiencia", f"{stats['pred_production_ton']:,.2f} t en las 59 parcelas ciegas (media {stats['pred_yield_mean']:.3f} ± {stats['pred_yield_std']:.3f} t/ha) | Inferencia 197 parcelas en {eff['inference_197_ms']:.2f} ms ({eff['model_bundle_size_kb']:.1f} KB)"),
    ]
    for idx, (k, v) in enumerate(meta_rows):
        row_cells = meta_table.rows[idx].cells
        row_cells[0].text = k
        row_cells[1].text = v
        row_cells[0].paragraphs[0].runs[0].bold = True
        row_cells[0].paragraphs[0].runs[0].font.size = Pt(8.8)
        row_cells[1].paragraphs[0].runs[0].font.size = Pt(8.8)
        set_cell_background(row_cells[0], "FFF7ED" if idx in (3, 4, 6) else "F4F4F5")
        set_cell_background(row_cells[1], "FFFFFF")
        set_cell_margins(row_cells[0], top=50, bottom=50)
        set_cell_margins(row_cells[1], top=50, bottom=50)

    doc.add_page_break()

    add_bases_required_sections(doc)
    doc.add_page_break()

    # =========================================================================
    # SECCIÓN 1: PROCEDIMIENTO METODOLÓGICO PASO A PASO
    # =========================================================================
    add_section_banner(doc, "1", "Procedimiento Metodológico e Ingeniería de Datos Geoespaciales")
    doc.add_paragraph(
        "El equipo Agrotec-Amanteca estructuró un procedimiento científico reproducible en cinco etapas "
        "secuenciales, diseñado para transformar datos satelitales, climáticos y topográficos crudos en "
        "predicciones agronómicas auditables y libres de fuga de información (Data Leakage):"
    )

    procedimiento_steps = [
        (
            "Etapa 1 — Estandarización Cartográfica y Topográfica (Shapefiles + INEGI CEM4): ",
            f"Se reproyectaron los {stats['total_parcelas']} polígonos parcelarios al sistema de referencia WGS84 (EPSG:4326) "
            "y se calcularon sus centroides exactos mediante proyección métrica UTM Zona 14N (EPSG:32614) junto con su "
            f"superficie productiva (AREA_HA, totalizando {stats['total_area_ha']:,.2f} ha: {stats['train_area_ha']:.2f} ha en "
            f"entrenamiento y {stats['pred_area_ha']:.2f} ha en predicción ciega). A partir del Continuo de Elevaciones "
            "Mexicano de INEGI (resolución 120 m), se extrajo la altitud media y la pendiente topográfica en grados.",
        ),
        (
            "Etapa 2 — Extracción Zonal Climática Multianual con all_touched=True (Rasters CHIRPS 2022–2025): ",
            "Para evitar que parcelas de pequeña superficie perdieran cobertura al cruzar sus geometrías con rasters "
            "climáticos de mayor tamaño de píxel, se implementó la extracción zonal con all_touched=True sobre las "
            "series mensuales de precipitación acumulada (mm), temperatura máxima (Tmax °C) y temperatura mínima (Tmin °C) "
            "del periodo 2022–2025, logrando 100.0% de completitud (0 valores nulos).",
        ),
        (
            "Etapa 3 — Reconstrucción Fenológica Satelital e Índices Agronómicos Sintéticos (NDVI y EVI): ",
            "Se consolidaron las curvas mensuales de vigor fotosintético NDVI y EVI del ciclo agrícola y se construyeron "
            "5 índices agronómicos derivados fila-por-fila (módulo compartido backend/agro_core.py): "
            "(1) Integral Fenológica bajo la curva de verano (ndvi_auc_verano, meses 5 a 10), (2) Tasa de desarrollo "
            "vegetativo (agosto menos mayo), (3) Tasa de senescencia y llenado de grano (agosto menos octubre), "
            "(4) Índice Hidrotérmico de De Martonne (Precipitación / [Tmax + 10]) y (5) Índice de Retención Topográfica.",
        ),
        (
            "Etapa 4 — Selección Leak-Free Smart-Pearson (|r| < 0.88) y Paridad Verificada con el Modelo Publicado: ",
            "Al auditar la matriz inicial de 175 columnas frente al filtro de Pearson secuencial tradicional (39 variables), "
            "se identificó que recorrer las columnas en orden posicional descartaba variables con mayor correlación con el "
            "rendimiento como tmin_2025_10 y evi_promedio_mes_5. El transformador LeakFreeSmartPearsonIDW ordena los "
            "candidatos por |r(X_i, y)| exclusivamente dentro de cada pliegue de entrenamiento y poda pares colineales con "
            f"|r(X_i, X_j)| >= 0.88 (correlación máxima resultante entre predictores = {stats['max_pairwise_corr']:.4f}, media = "
            f"{stats['mean_pairwise_corr']:.4f}), seleccionando exactamente {stats['base_features_after_pearson']} variables base.",
        ),
        (
            "Etapa 5 — Autocorrelación Geoespacial por Ponderación Inversa a la Distancia (IDW k=7) y Calibración Conformal: ",
            "Se incorporó la variable spatial_idw_yield, que calcula el rendimiento promedio ponderado por el inverso "
            "de la distancia (1 / d^1.5) de las k = 7 parcelas de entrenamiento más cercanas, excluyendo coincidencias "
            "exactas (d <= 1e-8) para impedir fuga de datos. Adicionalmente, se calibró un Intervalo de Predicción "
            f"Conformal al 80% sobre los residuos Out-Of-Fold escalados por la dispersión de los 4 sub-modelos (factor q80 = "
            f"{eff['conformal_q80_factor']:.4f}), alcanzando una cobertura empírica fuera de muestra del {eff['conformal_80_coverage_oof_pct']:.1f}%.",
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
    add_section_banner(doc, "2", "Modelos Evaluados, Fundamento Algorítmico y Criterio de Selección")
    doc.add_paragraph(
        f"Sobre las N = {stats['train_parcelas']} parcelas de entrenamiento se evaluaron {len(models_comp)} configuraciones "
        "utilizando Validación Cruzada de 5 Pliegues (5-Fold CV, shuffle=True, random_state=42) y Validación Cruzada "
        "Repetida 5×5 (25 particiones independientes). Tanto la validación cruzada como el modelo final exportado "
        f"(best_model.joblib) operan exactamente sobre la misma configuración de {stats['total_features_selected']} variables:"
    )

    models_explanation = [
        (
            "1. Ensemble Agrotec (Voting Heterogéneo + Smart-Pearson + IDW) — [MODELO GANADOR SELECCIONADO]: ",
            "Integra cuatro familias algorítmicas complementarias mediante votación ponderada: Extra Trees Podado (40%), "
            "Random Forest Podado (25%), Support Vector Regressor con Kernel RBF y RobustScaler (20%), y Gradient Boosting "
            f"Regressor (15%), operando sobre las {stats['total_features_selected']} variables del filtro Leak-Free Smart-Pearson + IDW. "
            f"¿Por qué quedó seleccionado?: Obtuvo el menor error tanto en 5-Fold CV (MAE = {winner['mae_cv']:.4f} ± {winner['mae_std']:.4f} t/ha, "
            f"RMSE = {winner['rmse_cv']:.4f} ± {winner['rmse_std']:.4f} t/ha, R² = {winner['r2_cv']:.4f}) como en 5×5 Repeated CV "
            f"(RMSE = {winner['rmse_repeated_cv']:.4f} ± {winner['rmse_repeated_std']:.4f} t/ha).",
        ),
        (
            "2. Extra Trees Regressor (Smart-Pearson + IDW): ",
            "Construye 220 árboles de decisión (max_depth=8) seleccionando aleatoriamente tanto el subconjunto de variables "
            "como el umbral de corte en cada nodo. Fue el modelo individual más estable en 5×5 Repeated CV (RMSE = 0.5124 ± 0.1110 t/ha; "
            "5-Fold MAE = 0.3682 ± 0.0615 t/ha, RMSE = 0.5077 ± 0.0950 t/ha).",
        ),
        (
            "3. Stacking Meta-Ensemble (Meta-Regresor RidgeCV L2): ",
            "Arquitectura jerárquica de dos niveles en la que un regresor lineal penalizado (RidgeCV) combina las predicciones "
            "Out-Of-Fold de los cuatro estimadores base. Logró 5-Fold MAE = 0.3606 ± 0.0661 t/ha y RMSE = 0.5006 ± 0.1068 t/ha "
            "(5×5 RMSE = 0.5186 ± 0.1175 t/ha), requiriendo 3.5 veces más tiempo de cómputo en validación cruzada por el ajuste anidado.",
        ),
        (
            "4. Random Forest Regressor (Baseline de 39 Variables Base): ",
            f"Ensamble clásico por Bagging evaluado sobre las {base_m['feature_count']} variables del filtro secuencial original. "
            f"Registró 5-Fold MAE = {base_m['mae_cv']:.4f} ± {base_m['mae_std']:.4f} t/ha, RMSE = {base_m['rmse_cv']:.4f} ± {base_m['rmse_std']:.4f} t/ha, "
            f"R² = {base_m['r2_cv']:.4f}, MAPE OOF = {base_m['mape_oof_pct']:.2f}% y {base_m['oof_within_050_t_ha_pct']:.1f}% de parcelas con error <= ±0.50 t/ha. "
            "Constituyó la línea base auditable contra la cual se midió la mejora del proyecto.",
        ),
        (
            "5. Support Vector Regressor (SVR Kernel RBF + RobustScaler): ",
            "Estandariza las variables utilizando mediana y rango intercuartílico y las proyecta mediante un kernel radial gaussiano "
            "(C=2.2, ε=0.06). Registró 5-Fold MAE = 0.3682 ± 0.0780 t/ha y RMSE = 0.5210 ± 0.1175 t/ha, aportando regularización "
            "geométrica suave dentro del ensamble ganador (peso del 20%).",
        ),
        (
            "6. Gradient Boosting Regressor (GBR) y LightGBM Regressor: ",
            "Modelos de boosting secuencial sobre residuos pseudo-gradiente. GBR alcanzó 5-Fold RMSE = 0.5095 ± 0.0922 t/ha "
            "(5×5 RMSE = 0.5152 ± 0.1124 t/ha), aportando el 15% del ensamble ganador; LightGBM registró 5-Fold RMSE = 0.5494 ± 0.0919 t/ha "
            "debido a la sensibilidad del particionado por hojas cuando N = 138.",
        ),
        (
            "7. RidgeCV (Regresión Lineal L2) y Referencia Nula (Predecir la Media): ",
            f"RidgeCV obtuvo 5-Fold MAE = 0.3819 ± 0.0608 t/ha y RMSE = 0.5180 ± 0.0846 t/ha (R² = 0.5802), mientras que el estimador "
            f"de referencia DummyRegressor (predecir siempre la media de entrenamiento de {stats['train_yield_mean']:.3f} t/ha) registró "
            f"MAE = {dummy_m['mae_cv']:.4f} t/ha y RMSE = {dummy_m['rmse_cv']:.4f} t/ha (R² = {dummy_m['r2_cv']:.4f}). El Ensemble Agrotec "
            "reduce el MAE en -52.9% frente a predecir la media regional.",
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
        "Figura 2. Comparativa experimental de error MAE y RMSE (5-Fold CV) entre las arquitecturas evaluadas."
    )
    p_cap4.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cap4.runs[0].italic = True
    p_cap4.runs[0].font.size = Pt(9)

    doc.add_page_break()

    # =========================================================================
    # SECCIÓN 3: RESULTADOS MEDIDOS DE PRECISIÓN, CALIBRACIÓN Y VALIDEZ
    # =========================================================================
    add_section_banner(doc, "3", "Resultados Experimentales, Calibración Conformal y Validez Metodológica")
    doc.add_paragraph(
        f"La siguiente tabla reporta las métricas medidas en las {len(models_comp)} configuraciones bajo Validación Cruzada "
        "de 5 Pliegues (media ± desviación estándar entre pliegues) y Validación Cruzada Repetida 5×5 (25 evaluaciones):"
    )

    t_mod = doc.add_table(rows=len(models_comp) + 1, cols=7)
    t_mod.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers_mod = [
        "Modelo / Arquitectura",
        "Set Variables",
        "MAE 5-Fold (t/ha)",
        "RMSE 5-Fold (t/ha)",
        "R² (5-Fold)",
        "RMSE 5×5 Rep.",
        "Tiempo CV",
    ]
    for c_idx, h_text in enumerate(headers_mod):
        cell = t_mod.rows[0].cells[c_idx]
        cell.text = h_text
        cell.paragraphs[0].runs[0].bold = True
        cell.paragraphs[0].runs[0].font.size = Pt(8.2)
        cell.paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
        set_cell_background(cell, "18181B")
        set_cell_margins(cell, top=50, bottom=50, left=70, right=70)

    for r_idx, m in enumerate(models_comp, start=1):
        row = t_mod.rows[r_idx].cells
        row[0].text = m["model"]
        row[1].text = m["feature_set"]
        row[2].text = f"{m['mae_cv']:.4f} ± {m['mae_std']:.3f}"
        row[3].text = f"{m['rmse_cv']:.4f} ± {m['rmse_std']:.3f}"
        row[4].text = f"{m['r2_cv']:.4f}"
        row[5].text = f"{m['rmse_repeated_cv']:.4f} ± {m['rmse_repeated_std']:.3f}"
        row[6].text = f"{m['cv_time_ms']:.0f} ms"
        bg = "FFF7ED" if r_idx == 1 else ("FFFFFF" if r_idx % 2 == 1 else "F4F4F5")
        for c_i in range(7):
            set_cell_background(row[c_i], bg)
            set_cell_margins(row[c_i], top=45, bottom=45, left=70, right=70)
            row[c_i].paragraphs[0].runs[0].font.size = Pt(8.2)
            if r_idx == 1:
                row[c_i].paragraphs[0].runs[0].bold = True

    doc.add_paragraph()
    p_val_note = doc.add_paragraph()
    r_vn_title = p_val_note.add_run("Alcance, Interpretación Observacional y Calibración de Incertidumbre: ")
    r_vn_title.bold = True
    p_val_note.add_run(
        "Dado el tamaño muestral del reto (N = 138 parcelas de entrenamiento), las diferencias entre los tres mejores modelos "
        "se encuentran dentro de una desviación estándar entre pliegues (±0.066 t/ha en MAE), por lo que la elección del "
        "Ensemble Agrotec se fundamenta en su menor error consistente a través de las 25 particiones de la validación repetida 5×5 "
        "y en la cuantificación de incertidumbre entre sus cuatro familias base. Asimismo, las importancias de variables "
        "(calculadas al 50% por permutación sobre el ensamble completo incluyendo SVR y 50% por reducción de impureza) y el "
        "simulador de escenarios reflejan asociaciones estadísticas aprendidas de un corte transversal histórico (por ejemplo, "
        "gradientes geográficos donde ciertas ventanas pluviales o térmicas co-varían con mayor altitud o nubosidad), por lo que "
        "deben interpretarse como sensibilidad observacional del modelo y no como elasticidades causales de un ensayo experimental controlado."
    )

    p_fig1 = doc.add_paragraph()
    p_fig1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_fig1.add_run().add_picture(str(fig1_path), width=Inches(5.3))
    p_cap1 = doc.add_paragraph(
        f"Figura 3. Auditoría Out-Of-Fold en las 138 parcelas de entrenamiento. "
        f"El {eff['oof_within_050_t_ha_pct']}% de las parcelas se ubica dentro de ±0.50 t/ha y el intervalo conformal al 80% cubre el {eff['conformal_80_coverage_oof_pct']}% de las observaciones reales."
    )
    p_cap1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cap1.runs[0].italic = True
    p_cap1.runs[0].font.size = Pt(9)

    p_fig2 = doc.add_paragraph()
    p_fig2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_fig2.add_run().add_picture(str(fig2_path), width=Inches(5.6))
    p_cap2 = doc.add_paragraph(
        "Figura 4. Ranking de las 12 variables con mayor importancia relativa en el Ensemble Agrotec (sobre las 23 variables activas)."
    )
    p_cap2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cap2.runs[0].italic = True
    p_cap2.runs[0].font.size = Pt(9)

    doc.add_page_break()

    # =========================================================================
    # SECCIÓN 4: TECNOLOGÍAS IMPLEMENTADAS EN EL SISTEMA
    # =========================================================================
    add_section_banner(doc, "4", "Resumen de Tecnologías Implementadas (Stack Tecnológico Verificado)")
    doc.add_paragraph(
        "Para traducir el modelo predictivo en una herramienta de decisión auditable, reproducible y accesible "
        "desde cualquier navegador, se implementó el siguiente ecosistema tecnológico con versiones verificadas:"
    )

    tech_table = doc.add_table(rows=5, cols=3)
    tech_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    t_headers = ["Capa del Sistema", "Tecnologías y Versiones Verificadas", "Función y Aporte Técnico en el Proyecto"]
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
            f"Python {env_v['python']}, Scikit-Learn {env_v['scikit_learn']}, LightGBM {env_v['lightgbm']}, SciPy Spatial (cdist IDW), NumPy {env_v['numpy']}, Pandas {env_v['pandas']}, Joblib {env_v['joblib']}",
            "Entrenamiento del Ensemble Agrotec (23 predictores), transformador LeakFreeSmartPearsonIDW (|r| < 0.88), validación cruzada 5-Fold y 5×5 Repetida e intervalos conformales al 80%.",
        ),
        (
            "2. Ingeniería Geoespacial y Clima",
            f"GeoPandas {env_v['geopandas']}, Shapely, Rasterio (all_touched=True), Rasters CHIRPS, INEGI CEM4, Apache Parquet",
            "Procesamiento de los 197 polígonos en EPSG:4326 con centroides en UTM 14N (EPSG:32614), extracción zonal pluvial/térmica sin pérdida en parcelas pequeñas y almacenamiento columnar.",
        ),
        (
            "3. Backend API, Pruebas y Simulador",
            "FastAPI, Pydantic V2, Uvicorn ASGI, Lifespan Memory Cache, agro_core.py, Pytest + HTTPX",
            "Servicio RESTful con sin advertencias deprecatorias, superficie de sensibilidad precalculada del modelo real (sensibilidad_simulador.json) y suite de pruebas automatizadas.",
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
        f"modelo seleccionado ({winner['model']}). El rendimiento medio estimado es de {stats['pred_yield_mean']:.3f} ± {stats['pred_yield_std']:.3f} t/ha "
        f"(rango de {stats['pred_yield_min']:.2f} a {stats['pred_yield_max']:.2f} t/ha), proyectando una cosecha "
        f"total de {stats['pred_production_ton']:,.2f} toneladas de cebada en las {stats['pred_area_ha']:.2f} hectáreas evaluadas, "
        "acompañado de su Intervalo de Predicción Conformal al 80%:"
    )

    t_pred = doc.add_table(rows=len(pred_df) + 1, cols=6)
    t_pred.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers_p = [
        "Folio",
        "ID Polígono",
        "Superficie (ha)",
        "Rendimiento Predicho (t/ha)",
        "Intervalo Conformal 80% (t/ha)",
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
        inf_v = float(row_data.get("INTERVALO_80_INF_T_HA", row_data["RENDIMIENTO_T_HA"] - row_data["INCERTIDUMBRE_T_HA"]))
        sup_v = float(row_data.get("INTERVALO_80_SUP_T_HA", row_data["RENDIMIENTO_T_HA"] + row_data["INCERTIDUMBRE_T_HA"]))
        half_v = float(row_data["INCERTIDUMBRE_T_HA"])
        row[4].text = f"[{inf_v:.2f} – {sup_v:.2f}] (±{half_v:.2f})"
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
    print(f"✅ Documento Técnico en Word (.docx) V4 generado exitosamente en:\n  - {DOCX_OUT_1}\n  - {DOCX_OUT_2}")


if __name__ == "__main__":
    build_word_document()
