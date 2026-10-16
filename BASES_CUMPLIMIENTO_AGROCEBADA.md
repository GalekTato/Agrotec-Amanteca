# Matriz de cumplimiento — Reto AgroCebada FIRA 2026

## Estado general

El modelo, el código fuente y el dashboard cumplen el objetivo técnico del reto. Antes de subir la entrega final a la plataforma de FIRA deben completarse los campos marcados como **pendientes del equipo**, porque corresponden a autoría, registro o archivos externos.

| Requisito de las bases | Evidencia en el proyecto | Estado |
|---|---|---|
| Predicción de rendimiento de cebada en Hidalgo, Tlaxcala y Puebla | `backend/artifacts/best_model.joblib`, métricas y 197 parcelas oficiales | Cumplido técnicamente |
| Estimar el 30% sin rendimiento publicado | 138 parcelas de entrenamiento y 59 predicciones ciegas | Cumplido |
| Modelo con métricas objetivas | MAE, RMSE, R², OOF y CV 5×5 en `metrics_summary.json` | Cumplido |
| Aplicación o dashboard funcional | GitHub Pages: https://galektato.github.io/Agrotec-Amanteca/ | Cumplido |
| Código fuente y documentación de ejecución | Repositorio GitHub, `README.md`, `backend/`, `frontend/`, `ml_pipeline/` | Cumplido |
| Aportaciones de cada integrante | Anexo 1: PM/apoyo general, datos, ciencia de datos, frontend y backend | Cumplido |
| Declaración de IA y prompts | Anexo 2: GitHub Copilot CLI, Antigravity CLI y 8 prompts representativos | Cumplido |
| Video demostrativo máximo 5 minutos | Enlace externo requerido por la plataforma | **Pendiente de subir o pegar enlace** |
| Presentación de máximo 15 minutos para finalistas | Preparación oral a cargo del equipo; no se incluye una guía en el repositorio | Pendiente del equipo |
| Preguntas guía para bonus | Respuestas preparadas por el equipo durante la presentación | Pendiente del equipo |

## Acciones antes de entregar

1. Grabar el video de máximo cinco minutos y pegar el enlace en el Anexo 3 y en la plataforma oficial.
2. Abrir el DOCX en Word o LibreOffice y comprobar que el anexo no exceda dos cuartillas.
3. Confirmar en la plataforma oficial el formato, tamaño máximo y campos adicionales de carga.
4. Mantener el enlace de GitHub Pages y el repositorio público disponibles durante la evaluación.

## Guion mínimo del video de cinco minutos

| Tiempo | Contenido |
|---:|---|
| 0:00–0:30 | Problema, reto y objetivo |
| 0:30–1:15 | Dataset: 197 parcelas, 138/59 y variables |
| 1:15–2:15 | Pipeline, selección leak-free, IDW y ensamble |
| 2:15–3:00 | Métricas, comparación y cobertura de incertidumbre |
| 3:00–4:20 | Demo del mapa, detalle de parcela y simulador |
| 4:20–5:00 | Inclusión financiera, límites y enlace final |

No se debe afirmar causalidad, precisión del 100% ni garantía universal de los intervalos. La cifra correcta es cobertura empírica OOF de 81.2% para un intervalo nominal de 80%.
