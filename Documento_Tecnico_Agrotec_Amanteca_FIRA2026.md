![](img/img001.jpeg)

**RETO AGROCEBADA FIRA 2026 · DOCUMENTO TÉCNICO, METODOLÓGICO Y DE RESULTADOS**

**Sistema Geoespacial e Inteligencia Artificial para la Predicción del Rendimiento Agrícola de Cebada (t/ha)**

Equipo: Agrotec-Amanteca | 197 Parcelas Analizadas (138 Entrenamiento · 59 Predicción Ciega)
Modelo Seleccionado: Ensemble Agrotec (Smart-Pearson + IDW) (5-Fold MAE: 0.3562 ± 0.0662 t/ha · 5-Fold RMSE: 0.4968 ± 0.1085 t/ha · R²: 0.6124)

**INTEGRANTES DEL EQUIPO AGROTEC-AMANTECA**

|  |  |
| --- | --- |
| **N.º** | **Nombre Completo del Integrante** |
| **01** | **Gael Askary Razo Montañez** |
| **02** | **Limhi Gerson López Momox** |
| **03** | **Karla Yaneth Cruz Sandoval** |
| **04** | **Arturo Huerta Maldonado** |
| **05** | **Juan Enrique Gutierrez Hernández** |

|  |  |
| --- | --- |
| **Universo Geoespacial Auditado** | 197 polígonos agrícolas (1,301.05 ha totales en EPSG:4326) |
| **Partición Oficial del Reto** | 138 parcelas con cosecha observada (907.48 ha) | 59 parcelas ciegas (393.57 ha) |
| **Paridad Verificada CV == Modelo Final** | Filtro Leak-Free Smart-Pearson (|r| < 0.88, 22 vars) + IDW Espacial (k=7, 1 var) = 23 predictores exactos (0% nulos) |
| **Precisión Validación Cruzada (5-Fold)** | MAE = 0.3562 ± 0.0662 t/ha | RMSE = 0.4968 ± 0.1085 t/ha | R² = 0.6124 ± 0.1795 |
| **Estabilidad en CV Repetida 5×5 (25 corridas)** | MAE = 0.3720 ± 0.0624 t/ha | RMSE = 0.5073 ± 0.1180 t/ha |
| **Comparativa vs. Baseline y Media** | Baseline RF (39 vars): MAE 0.3742 / RMSE 0.5139 t/ha | Predecir la Media: MAE 0.7585 / RMSE 0.8545 t/ha |
| **Incertidumbre Conformal al 80% (OOF)** | Cobertura empírica fuera de muestra: 81.2% (Semiancho medio ±0.584 t/ha) | 72.5% con error ≤ ±0.50 t/ha |
| **Cosecha Estimada y Eficiencia** | 1,540.38 t en las 59 parcelas ciegas (media 3.940 ± 0.692 t/ha) | Inferencia 197 parcelas en 89.50 ms (1436.8 KB) |

# **A. Introducción**

El Reto AgroCebada FIRA 2026 solicita una solución analítica capaz de estimar el rendimiento de parcelas de cebada en Hidalgo, Tlaxcala y Puebla y convertirlo en una herramienta funcional de consulta. Agrotec-Amanteca responde a ese objetivo mediante un sistema que integra información satelital, climática, topográfica y geoespacial para producir una estimación por parcela. El problema es relevante porque el rendimiento agrícola depende de condiciones que cambian entre localidades y ciclos, mientras que las decisiones productivas y financieras requieren información espacialmente detallada y disponible antes de la cosecha. El dataset oficial contiene 197 parcelas georreferenciadas: 138 con rendimiento observado, utilizadas para entrenar y validar, y 59 cuyo rendimiento fue reservado para evaluación. Por tanto, el proyecto no intenta reemplazar la medición de campo; construye una estimación reproducible para apoyar la priorización de parcelas, la interpretación de escenarios y la comunicación de riesgo. La solución combina un pipeline de ingeniería de datos con un ensamble de Extra Trees, Random Forest, SVR y Gradient Boosting. Antes del entrenamiento se calculan índices agronómicos derivados de las series mensuales de NDVI/EVI, precipitación, temperatura, elevación, pendiente y superficie. La selección de variables se realiza dentro de los pliegues de validación para evitar que las etiquetas de validación influyan en el entrenamiento. El componente espacial IDW se calcula en coordenadas métricas UTM 14N y utiliza únicamente referencias permitidas en cada fold. El resultado se publica como artefactos auditables, API FastAPI y dashboard web responsive disponible en GitHub Pages. La aplicación permite consultar el mapa, revisar predicciones, explorar incertidumbre y ejecutar escenarios de vigor satelital, precipitación y temperatura. La contribución principal es un flujo de extremo a extremo que conecta datos con una interfaz usable, manteniendo una interpretación honesta: las métricas son predictivas y observacionales, no una prueba de causalidad agronómica.

# **B. Justificación**

Una predicción por parcela puede complementar la información de campo al identificar diferencias espaciales y comunicar el nivel de incertidumbre asociado. El proyecto se justifica porque combina variables que representan vigor vegetal, disponibilidad hídrica, régimen térmico y contexto físico con una aplicación consultable por personas no especialistas. La selección y validación controladas reducen el riesgo de sobreajuste, mientras que la comparación contra un estimador nulo y un baseline permite medir si la complejidad añadida aporta valor real. La herramienta se plantea como apoyo a la decisión, no como sustituto de la experiencia del productor ni como garantía de rendimiento.

# **C. Objetivos**

Objetivo general: desarrollar y documentar un modelo analítico y una aplicación web funcional para estimar el rendimiento de cebada por parcela en el conjunto oficial del Reto AgroCebada FIRA 2026. Objetivos específicos: integrar las variables oficiales y su referencia geoespacial; construir índices agronómicos deterministas; seleccionar predictores reduciendo redundancia y evitando fuga de información; comparar un ensamble con un baseline Random Forest y un DummyRegressor; cuantificar error mediante MAE, RMSE y R² con validación cruzada de cinco pliegues y repetición 5×5; calibrar una banda de incertidumbre con cobertura empírica fuera de muestra; exportar predicciones para las 59 parcelas ciegas; ofrecer consulta cartográfica, simulación de escenarios y descarga de resultados; y explicar las limitaciones para que la herramienta se use responsablemente en contextos agrícolas y financieros.

# **D. Metodología**

El universo se compone de 197 polígonos georreferenciados, con 138 etiquetas de rendimiento disponibles y 59 reservadas para predicción. Los polígonos se visualizan en WGS84 y sus centroides se calculan temporalmente en UTM Zona 14N (EPSG:32614), evitando medir distancias en grados. Las variables ambientales incluyen índices NDVI/EVI, precipitación CHIRPS, temperaturas máxima y mínima, elevación, pendiente y superficie. La extracción zonal documentada utiliza all\_touched=True para no descartar parcelas pequeñas. A partir de las columnas originales se calculan cinco índices: área bajo la curva de NDVI, tasa vegetativa, caída de madurez, índice hidrotérmico y retención topográfica. El transformador LeakFreeSmartPearsonIDW ordena variables por correlación absoluta con el objetivo únicamente dentro del entrenamiento de cada fold, elimina redundancia con umbral 0.88 y conserva 22 variables; después agrega spatial\_idw\_yield. El IDW usa las siete referencias más cercanas, potencia 1.5 y solo rendimientos del fold de entrenamiento, excluyendo coincidencias exactas. El modelo final es un VotingRegressor con Extra Trees 40%, Random Forest 25%, SVR 20% y Gradient Boosting 15%. Se comparan 11 configuraciones con KFold de cinco pliegues y RepeatedKFold 5×5, usando MAE, RMSE y R². Las predicciones OOF se calculan para que cada parcela sea evaluada por un modelo que no vio su etiqueta. La incertidumbre se calibra usando residuos OOF y una escala de dispersión del ensamble; la cobertura reportada es empírica. Finalmente, se ajusta el modelo con las etiquetas disponibles, se serializa en joblib y se sincronizan JSON, CSV, GeoJSON, dashboard y documento Word. El simulador modifica entradas, recalcula índices y evalúa escenarios combinados directamente con el modelo.

# **E. Resultados y discusión**

El ensamble seleccionado obtuvo MAE 5-Fold de 0.3562 ± 0.0662 t/ha, RMSE de 0.4968 ± 0.1084 t/ha, RMSE 5×5 de 0.5073 ± 0.1183 t/ha y R² de 0.6124 ± 0.1804. El baseline Random Forest con 39 variables obtuvo MAE 0.3742 y RMSE 0.5139 t/ha, mientras que el DummyRegressor obtuvo MAE 0.7585 y RMSE 0.8545 t/ha. La comparación demuestra una mejora medida frente a ambos referentes, aunque la diferencia frente al baseline es moderada y debe interpretarse junto con las desviaciones estándar. El 72.5% de las predicciones OOF tuvo error absoluto menor o igual a 0.50 t/ha. La banda nominal de 80% alcanzó 81.2% de cobertura empírica OOF con semiancho medio de 0.584 t/ha. Estos resultados respaldan una herramienta predictiva inicial, pero no garantizan el mismo desempeño en otra región, año o distribución de clima. El modelo usa 23 predictores y los artefactos comprueban la paridad entre selección, entrenamiento e inferencia. El simulador responde de forma conjunta y no suma efectos marginales, respetando la posible no linealidad del ensamble. El dashboard permite observar la distribución espacial y consultar las 59 predicciones ciegas con intervalos. La principal limitación es el tamaño muestral: 138 etiquetas son suficientes para una primera solución tabular, pero generan variabilidad entre particiones. La siguiente validación recomendada es temporal y espacial, con datos de una campaña o localidad no utilizada para ajustar decisiones. También se recomienda monitorear fuera de dominio y separar calibración conformal de evaluación externa cuando existan más observaciones.

# **F. Uso de la ciencia de datos en la inclusión financiera del sector agro**

La inclusión financiera requiere que productores y organizaciones puedan presentar información comprensible para planear inversiones, seguros, crédito y asistencia técnica. Un rendimiento estimado por parcela no constituye por sí mismo una autorización de crédito ni sustituye la evaluación financiera; sin embargo, puede servir como insumo operativo para ordenar visitas, comparar escenarios y discutir riesgos productivos con mayor evidencia. El dashboard traduce variables técnicas a una consulta visual y exportable: cada parcela tiene una estimación, producción calculada según su superficie e intervalo de incertidumbre. Esto puede ayudar a que instituciones y técnicos identifiquen dónde hace falta información adicional antes de tomar una decisión, evitando tratar una predicción puntual como certeza. El simulador permite explorar escenarios de clima y vigor, siempre con la advertencia de que son sensibilidades observacionales y no efectos causales. En una etapa posterior, el sistema podría integrarse con registros de manejo, costos, ingresos y siniestralidad para construir indicadores financieros más completos, con consentimiento y protección de datos. La aplicación de ciencia de datos es responsable cuando hace explícitos sus supuestos, mide su error, señala incertidumbre y permite auditoría. Por ello, la propuesta contribuye a la inclusión financiera como herramienta de información y priorización, no como mecanismo automático de aprobación o rechazo de productores.

# **G. Conclusiones**

Agrotec-Amanteca cumplió el objetivo de construir una solución funcional para estimar el rendimiento de cebada por parcela y consultar sus resultados en una interfaz web. La integración de datos satelitales, climáticos, topográficos y espaciales produjo un conjunto de 23 predictores consistente entre validación e inferencia. El ensamble superó al baseline y a la referencia nula bajo métricas medidas, y la validación OOF permitió reportar tanto error como cobertura empírica de incertidumbre. La aplicación aporta valor porque conecta el resultado estadístico con un mapa, una tabla exportable y un simulador trazable. La conclusión no es que el modelo sea universal ni causal: su confiabilidad está condicionada por las 138 parcelas etiquetadas, la representatividad del dataset y la similitud entre futuras observaciones y el dominio de entrenamiento. Para fortalecerlo se requieren nuevas parcelas independientes, campañas agrícolas adicionales y validaciones por localidad y tiempo. También debe mantenerse la separación entre predicción, simulación y decisión financiera. Bajo esas condiciones, el sistema es una base estable, lógica y auditable para apoyo a decisiones agrícolas, y cuenta con una ruta clara de mejora sin depender de añadir complejidad innecesaria.

# **H. Bibliografía**

* FIRA. (2026). Bases de participación: Reto AgroCebada FIRA 2026. Documento oficial proporcionado por el comité organizador.
* FIRA. (2025). Reglas de Operación para apoyos a los sectores agropecuario, forestal, pesquero, alimentario y rural. Diario Oficial de la Federación.
* Breiman, L. (2001). Random Forests. Machine Learning, 45, 5–32.
* Geodetic Survey / EPSG.io. (s. f.). EPSG:4326 WGS 84 y EPSG:32614 WGS 84 / UTM zone 14N.
* Scikit-learn developers. (s. f.). Scikit-learn User Guide: model selection, ensembles, pipelines and metrics. https://scikit-learn.org/
* FastAPI developers. (s. f.). FastAPI documentation. https://fastapi.tiangolo.com/
* CHIRPS Climate Hazards Center. (s. f.). Climate Hazards InfraRed Precipitation with Station data.

# **I. Anexos y cumplimiento de entregables**

Anexo 1 — Integración y aportaciones del equipo: se documentan las funciones declaradas por el equipo. Las responsabilidades fueron colaborativas y todos los integrantes participaron en la revisión final.

* Gael Askary Razo Montañez — PM y apoyo general
* Limhi Gerson López Momox — Ingeniero de datos
* Karla Yaneth Cruz Sandoval — Desarrolladora frontend
* Arturo Huerta Maldonado — Desarrollador backend
* Juan Enrique Gutierrez Hernández — Científico de datos

Anexo 2 — Declaración de uso de Inteligencia Artificial: las bases permiten IA si se indica dónde fue utilizada y se anexan los prompts. La IA se empleó como asistencia técnica, no como sustituto de la decisión, ejecución ni validación del equipo.

Herramientas utilizadas: GitHub Copilot CLI para auditoría, programación asistida, pruebas y documentación; Antigravity CLI exclusivamente como apoyo para correcciones y ajustes del diseño frontend. El equipo conserva la responsabilidad completa sobre la autoría, revisión, ejecución, interpretación y entrega.

* Prompts representativos utilizados durante el desarrollo:
* IA-01 — Audita exhaustivamente el pipeline de Machine Learning e identifica riesgos de data leakage, especialmente en la selección de variables y el cálculo IDW dentro de la validación cruzada.
* IA-02 — Comprueba si existe paridad entre las variables usadas en Cross-Validation, el modelo serializado y la inferencia de producción.
* IA-03 — Revisa si el simulador evalúa escenarios combinados directamente con el modelo o si suma efectos marginales de forma incorrecta.
* IA-04 — Revisa la API FastAPI, sus validaciones, sus advertencias deprecatorias y la cobertura de las pruebas automatizadas.
* IA-05 — Revisa que el simulador y la curva fenológica reaccionen coherentemente a NDVI, precipitación y temperatura.
* IA-06 — Compara las métricas del dashboard, README, artefactos y documento técnico para detectar números o afirmaciones inconsistentes.
* IA-07 — Compara el reporte técnico del proyecto contra las bases oficiales del Reto AgroCebada FIRA 2026 e identifica entregables faltantes.
* IA-08 — Prepara una guía de defensa oral con preguntas difíciles sobre fuga de datos, tamaño de muestra, causalidad, conformal e incertidumbre.

Los prompts anteriores son representativos de las instrucciones utilizadas durante el proceso; algunas consultas fueron iterativas. Las recomendaciones fueron revisadas por el equipo, y los cambios incorporados se ejecutaron y verificaron mediante pruebas, compilación o inspección directa de los artefactos. Las métricas reportadas fueron generadas por la ejecución del pipeline y no fueron inventadas por una herramienta de IA.

Anexo 3 — Prototipo y video: dashboard funcional: https://galektato.github.io/Agrotec-Amanteca/. Código fuente: https://github.com/GalekTato/Agrotec-Amanteca. Video demostrativo de máximo cinco minutos: [PENDIENTE DE SUBIR A LA PLATAFORMA O COMPLETAR CON EL ENLACE DEFINITIVO].

# **1. Procedimiento Metodológico e Ingeniería de Datos Geoespaciales**

El equipo Agrotec-Amanteca estructuró un procedimiento científico reproducible en cinco etapas secuenciales, diseñado para transformar datos satelitales, climáticos y topográficos crudos en predicciones agronómicas auditables y libres de fuga de información (Data Leakage):

* **Etapa 1 — Estandarización Cartográfica y Topográfica (Shapefiles + INEGI CEM4):** Se reproyectaron los 197 polígonos parcelarios al sistema de referencia WGS84 (EPSG:4326) y se calcularon sus centroides exactos mediante proyección métrica UTM Zona 14N (EPSG:32614) junto con su superficie productiva (AREA\_HA, totalizando 1,301.05 ha: 907.48 ha en entrenamiento y 393.57 ha en predicción ciega). A partir del Continuo de Elevaciones Mexicano de INEGI (resolución 120 m), se extrajo la altitud media y la pendiente topográfica en grados.
* **Etapa 2 — Extracción Zonal Climática Multianual con all\_touched=True (Rasters CHIRPS 2022–2025):** Para evitar que parcelas de pequeña superficie perdieran cobertura al cruzar sus geometrías con rasters climáticos de mayor tamaño de píxel, se implementó la extracción zonal con all\_touched=True sobre las series mensuales de precipitación acumulada (mm), temperatura máxima (Tmax °C) y temperatura mínima (Tmin °C) del periodo 2022–2025, logrando 100.0% de completitud (0 valores nulos).
* **Etapa 3 — Reconstrucción Fenológica Satelital e Índices Agronómicos Sintéticos (NDVI y EVI):** Se consolidaron las curvas mensuales de vigor fotosintético NDVI y EVI del ciclo agrícola y se construyeron 5 índices agronómicos derivados fila-por-fila (módulo compartido backend/agro\_core.py): (1) Integral Fenológica bajo la curva de verano (ndvi\_auc\_verano, meses 5 a 10), (2) Tasa de desarrollo vegetativo (agosto menos mayo), (3) Tasa de senescencia y llenado de grano (agosto menos octubre), (4) Índice Hidrotérmico de De Martonne (Precipitación / [Tmax + 10]) y (5) Índice de Retención Topográfica.
* **Etapa 4 — Selección Leak-Free Smart-Pearson (|r| < 0.88) y Paridad Verificada con el Modelo Publicado:** Al auditar la matriz inicial de 175 columnas frente al filtro de Pearson secuencial tradicional (39 variables), se identificó que recorrer las columnas en orden posicional descartaba variables con mayor correlación con el rendimiento como tmin\_2025\_10 y evi\_promedio\_mes\_5. El transformador LeakFreeSmartPearsonIDW ordena los candidatos por |r(X\_i, y)| exclusivamente dentro de cada pliegue de entrenamiento y poda pares colineales con |r(X\_i, X\_j)| >= 0.88 (correlación máxima resultante entre predictores = 0.8646, media = 0.3999), seleccionando exactamente 22 variables base.
* **Etapa 5 — Autocorrelación Geoespacial por Ponderación Inversa a la Distancia (IDW k=7) y Calibración Conformal:** Se incorporó la variable spatial\_idw\_yield, que calcula el rendimiento promedio ponderado por el inverso de la distancia (1 / d^1.5) de las k = 7 parcelas de entrenamiento más cercanas, excluyendo coincidencias exactas (d <= 1e-8) para impedir fuga de datos. Adicionalmente, se calibró un Intervalo de Predicción Conformal al 80% sobre los residuos Out-Of-Fold escalados por la dispersión de los 4 sub-modelos (factor q80 = 3.6257), alcanzando una cobertura empírica fuera de muestra del 81.2%.

![](img/img002.png)

*Figura 1. Dinámica fenológica mensual del NDVI comparando parcelas élite (≥4.35 t/ha), media regional y parcelas de bajo rendimiento (≤3.30 t/ha).*

# **2. Modelos Evaluados, Fundamento Algorítmico y Criterio de Selección**

Sobre las N = 138 parcelas de entrenamiento se evaluaron 11 configuraciones utilizando Validación Cruzada de 5 Pliegues (5-Fold CV, shuffle=True, random\_state=42) y Validación Cruzada Repetida 5×5 (25 particiones independientes). Tanto la validación cruzada como el modelo final exportado (best\_model.joblib) operan exactamente sobre la misma configuración de 23 variables:

* **1. Ensemble Agrotec (Voting Heterogéneo + Smart-Pearson + IDW) — [MODELO GANADOR SELECCIONADO]:** Integra cuatro familias algorítmicas complementarias mediante votación ponderada: Extra Trees Podado (40%), Random Forest Podado (25%), Support Vector Regressor con Kernel RBF y RobustScaler (20%), y Gradient Boosting Regressor (15%), operando sobre las 23 variables del filtro Leak-Free Smart-Pearson + IDW. ¿Por qué quedó seleccionado?: Obtuvo el menor error tanto en 5-Fold CV (MAE = 0.3562 ± 0.0662 t/ha, RMSE = 0.4968 ± 0.1085 t/ha, R² = 0.6124) como en 5×5 Repeated CV (RMSE = 0.5073 ± 0.1180 t/ha).
* **2. Extra Trees Regressor (Smart-Pearson + IDW):** Construye 220 árboles de decisión (max\_depth=8) seleccionando aleatoriamente tanto el subconjunto de variables como el umbral de corte en cada nodo. Fue el modelo individual más estable en 5×5 Repeated CV (RMSE = 0.5124 ± 0.1110 t/ha; 5-Fold MAE = 0.3682 ± 0.0615 t/ha, RMSE = 0.5077 ± 0.0950 t/ha).
* **3. Stacking Meta-Ensemble (Meta-Regresor RidgeCV L2):** Arquitectura jerárquica de dos niveles en la que un regresor lineal penalizado (RidgeCV) combina las predicciones Out-Of-Fold de los cuatro estimadores base. Logró 5-Fold MAE = 0.3606 ± 0.0661 t/ha y RMSE = 0.5006 ± 0.1068 t/ha (5×5 RMSE = 0.5186 ± 0.1175 t/ha), requiriendo 3.5 veces más tiempo de cómputo en validación cruzada por el ajuste anidado.
* **4. Random Forest Regressor (Baseline de 39 Variables Base):** Ensamble clásico por Bagging evaluado sobre las 39 variables del filtro secuencial original. Registró 5-Fold MAE = 0.3742 ± 0.0592 t/ha, RMSE = 0.5139 ± 0.0923 t/ha, R² = 0.5859, MAPE OOF = 10.65% y 71.7% de parcelas con error <= ±0.50 t/ha. Constituyó la línea base auditable contra la cual se midió la mejora del proyecto.
* **5. Support Vector Regressor (SVR Kernel RBF + RobustScaler):** Estandariza las variables utilizando mediana y rango intercuartílico y las proyecta mediante un kernel radial gaussiano (C=2.2, ε=0.06). Registró 5-Fold MAE = 0.3682 ± 0.0780 t/ha y RMSE = 0.5210 ± 0.1175 t/ha, aportando regularización geométrica suave dentro del ensamble ganador (peso del 20%).
* **6. Gradient Boosting Regressor (GBR) y LightGBM Regressor:** Modelos de boosting secuencial sobre residuos pseudo-gradiente. GBR alcanzó 5-Fold RMSE = 0.5095 ± 0.0922 t/ha (5×5 RMSE = 0.5152 ± 0.1124 t/ha), aportando el 15% del ensamble ganador; LightGBM registró 5-Fold RMSE = 0.5494 ± 0.0919 t/ha debido a la sensibilidad del particionado por hojas cuando N = 138.
* **7. RidgeCV (Regresión Lineal L2) y Referencia Nula (Predecir la Media):** RidgeCV obtuvo 5-Fold MAE = 0.3819 ± 0.0608 t/ha y RMSE = 0.5180 ± 0.0846 t/ha (R² = 0.5802), mientras que el estimador de referencia DummyRegressor (predecir siempre la media de entrenamiento de 3.955 t/ha) registró MAE = 0.7585 t/ha y RMSE = 0.8545 t/ha (R² = -0.0870). El Ensemble Agrotec reduce el MAE en -52.9% frente a predecir la media regional.

![](img/img003.png)

*Figura 2. Comparativa experimental de error MAE y RMSE (5-Fold CV) entre las arquitecturas evaluadas.*

# **3. Resultados Experimentales, Calibración Conformal y Validez Metodológica**

La siguiente tabla reporta las métricas medidas en las 11 configuraciones bajo Validación Cruzada de 5 Pliegues (media ± desviación estándar entre pliegues) y Validación Cruzada Repetida 5×5 (25 evaluaciones):

|  |  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- |
| **Modelo / Arquitectura** | **Set Variables** | **MAE 5-Fold (t/ha)** | **RMSE 5-Fold (t/ha)** | **R² (5-Fold)** | **RMSE 5×5 Rep.** | **Tiempo CV** |
| **Ensemble Agrotec (Smart-Pearson + IDW)** | **23 Smart-Pearson+IDW** | **0.3562 ± 0.066** | **0.4968 ± 0.108** | **0.6124** | **0.5073 ± 0.118** | **3023 ms** |
| Ensemble Voting (Filtro Secuencial 39) | 39 base | 0.3661 ± 0.063 | 0.5058 ± 0.097 | 0.5999 | 0.5129 ± 0.112 | 2782 ms |
| Extra Trees (Smart-Pearson + IDW) | 23 Smart-Pearson+IDW | 0.3662 ± 0.061 | 0.5061 ± 0.095 | 0.5974 | 0.5131 ± 0.111 | 1301 ms |
| Gradient Boosting Regressor | 39 base | 0.3841 ± 0.062 | 0.5095 ± 0.092 | 0.5952 | 0.5152 ± 0.112 | 361 ms |
| Random Forest (Baseline 39 base) | 39 base | 0.3742 ± 0.059 | 0.5139 ± 0.092 | 0.5859 | 0.5175 ± 0.111 | 1735 ms |
| RidgeCV Lineal Regularizado | 39 base | 0.3819 ± 0.061 | 0.5180 ± 0.085 | 0.5802 | 0.5201 ± 0.105 | 66 ms |
| Stacking Meta-Ensemble (Smart-Pearson + IDW) | 23 Smart-Pearson+IDW | 0.3617 ± 0.067 | 0.5047 ± 0.105 | 0.6031 | 0.5219 ± 0.116 | 15413 ms |
| Extra Trees Regressor (39 base) | 39 base | 0.3731 ± 0.064 | 0.5134 ± 0.096 | 0.5857 | 0.5220 ± 0.110 | 1042 ms |
| SVR (Kernel RBF + RobustScaler) | 39 base | 0.3682 ± 0.078 | 0.5210 ± 0.117 | 0.5729 | 0.5310 ± 0.118 | 61 ms |
| LightGBM Regressor | 39 base | 0.4198 ± 0.065 | 0.5494 ± 0.092 | 0.5321 | 0.5426 ± 0.102 | 106 ms |
| Referencia (Predecir la Media) | Constante | 0.7585 ± 0.089 | 0.8545 ± 0.093 | -0.0870 | 0.8507 ± 0.074 | 16 ms |

**Alcance, Interpretación Observacional y Calibración de Incertidumbre:** Dado el tamaño muestral del reto (N = 138 parcelas de entrenamiento), las diferencias entre los tres mejores modelos se encuentran dentro de una desviación estándar entre pliegues (±0.066 t/ha en MAE), por lo que la elección del Ensemble Agrotec se fundamenta en su menor error consistente a través de las 25 particiones de la validación repetida 5×5 y en la cuantificación de incertidumbre entre sus cuatro familias base. Asimismo, las importancias de variables (calculadas al 50% por permutación sobre el ensamble completo incluyendo SVR y 50% por reducción de impureza) y el simulador de escenarios reflejan asociaciones estadísticas aprendidas de un corte transversal histórico (por ejemplo, gradientes geográficos donde ciertas ventanas pluviales o térmicas co-varían con mayor altitud o nubosidad), por lo que deben interpretarse como sensibilidad observacional del modelo y no como elasticidades causales de un ensayo experimental controlado.

![](img/img004.png)

*Figura 3. Auditoría Out-Of-Fold en las 138 parcelas de entrenamiento. El 72.5% de las parcelas se ubica dentro de ±0.50 t/ha y el intervalo conformal al 80% cubre el 81.2% de las observaciones reales.*

![](img/img005.png)

*Figura 4. Ranking de las 12 variables con mayor importancia relativa en el Ensemble Agrotec (sobre las 23 variables activas).*

# **4. Resumen de Tecnologías Implementadas (Stack Tecnológico Verificado)**

Para traducir el modelo predictivo en una herramienta de decisión auditable, reproducible y accesible desde cualquier navegador, se implementó el siguiente ecosistema tecnológico con versiones verificadas:

|  |  |  |
| --- | --- | --- |
| **Capa del Sistema** | **Tecnologías y Versiones Verificadas** | **Función y Aporte Técnico en el Proyecto** |
| **1. Ciencia de Datos y Machine Learning** | Python 3.14.7, Scikit-Learn 1.9.1, LightGBM 4.7.0, SciPy Spatial (cdist IDW), NumPy 2.5.3, Pandas 3.0.6, Joblib 1.6.0 | Entrenamiento del Ensemble Agrotec (23 predictores), transformador LeakFreeSmartPearsonIDW (|r| < 0.88), validación cruzada 5-Fold y 5×5 Repetida e intervalos conformales al 80%. |
| **2. Ingeniería Geoespacial y Clima** | GeoPandas 1.2.0, Shapely, Rasterio (all\_touched=True), Rasters CHIRPS, INEGI CEM4, Apache Parquet | Procesamiento de los 197 polígonos en EPSG:4326 con centroides en UTM 14N (EPSG:32614), extracción zonal pluvial/térmica sin pérdida en parcelas pequeñas y almacenamiento columnar. |
| **3. Backend API, Pruebas y Simulador** | FastAPI, Pydantic V2, Uvicorn ASGI, Lifespan Memory Cache, agro\_core.py, Pytest + HTTPX | Servicio RESTful con sin advertencias deprecatorias, superficie de sensibilidad precalculada del modelo real (sensibilidad\_simulador.json) y suite de pruebas automatizadas. |
| **4. Frontend Cartográfico y Reporteo** | React 18, Vite 6, Tailwind CSS, LeafletJS, Esri ArcGIS Online, Recharts, python-docx, Matplotlib | Dashboard bajo estética Swiss (Modo Claro) e Industrial (Modo Oscuro) con 3 capas satelitales/topográficas libres de API Key y generación automatizada de informes Word a 300 DPI. |

# **5. Catálogo Oficial de Predicciones (59 Parcelas de Prueba Ciega)**

A continuación se presenta el padrón completo de las 59 parcelas ciegas pronosticadas por el modelo seleccionado (Ensemble Agrotec (Smart-Pearson + IDW)). El rendimiento medio estimado es de 3.940 ± 0.692 t/ha (rango de 2.70 a 4.99 t/ha), proyectando una cosecha total de 1,540.38 toneladas de cebada en las 393.57 hectáreas evaluadas, acompañado de su Intervalo de Predicción Conformal al 80%:

|  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| **Folio** | **ID Polígono** | **Superficie (ha)** | **Rendimiento Predicho (t/ha)** | **Intervalo Conformal 80% (t/ha)** | **Producción Estimada (ton)** |
| 01 | **AGC\_003** | 18.68 | **3.4092** | [2.50 – 4.32] (±0.91) | 63.68 |
| 02 | **AGC\_011** | 7.17 | **4.5543** | [3.90 – 5.21] (±0.66) | 32.65 |
| 03 | **AGC\_016** | 7.47 | **4.3300** | [3.79 – 4.87] (±0.54) | 32.35 |
| 04 | **AGC\_025** | 2.00 | **2.9403** | [2.40 – 3.48] (±0.54) | 5.88 |
| 05 | **AGC\_027** | 8.46 | **3.2125** | [2.67 – 3.76] (±0.54) | 27.18 |
| 06 | **AGC\_028** | 1.86 | **4.6254** | [4.08 – 5.17] (±0.54) | 8.60 |
| 07 | **AGC\_029** | 5.90 | **3.1847** | [1.71 – 4.66] (±1.48) | 18.79 |
| 08 | **AGC\_030** | 13.05 | **3.2592** | [2.72 – 3.80] (±0.54) | 42.53 |
| 09 | **AGC\_031** | 1.98 | **4.3845** | [3.84 – 4.93] (±0.54) | 8.68 |
| 10 | **AGC\_036** | 5.00 | **4.2887** | [3.74 – 4.83] (±0.54) | 21.44 |
| 11 | **AGC\_039** | 7.71 | **2.9165** | [2.37 – 3.46] (±0.54) | 22.49 |
| 12 | **AGC\_042** | 3.81 | **3.0632** | [2.52 – 3.61] (±0.54) | 11.67 |
| 13 | **AGC\_043** | 7.15 | **4.4892** | [3.95 – 5.03] (±0.54) | 32.10 |
| 14 | **AGC\_050** | 2.42 | **2.9865** | [2.44 – 3.53] (±0.54) | 7.23 |
| 15 | **AGC\_052** | 6.23 | **4.4068** | [3.86 – 4.95] (±0.54) | 27.45 |
| 16 | **AGC\_061** | 7.23 | **3.0100** | [2.47 – 3.55] (±0.54) | 21.76 |
| 17 | **AGC\_063** | 12.54 | **4.4061** | [3.86 – 4.95] (±0.54) | 55.25 |
| 18 | **AGC\_065** | 60.88 | **4.4006** | [3.86 – 4.94] (±0.54) | 267.91 |
| 19 | **AGC\_071** | 5.21 | **3.0317** | [2.49 – 3.58] (±0.54) | 15.80 |
| 20 | **AGC\_075** | 3.90 | **3.0177** | [2.47 – 3.56] (±0.54) | 11.77 |
| 21 | **AGC\_076** | 1.01 | **4.5541** | [4.01 – 5.10] (±0.54) | 4.60 |
| 22 | **AGC\_082** | 2.77 | **4.4259** | [3.88 – 4.97] (±0.54) | 12.26 |
| 23 | **AGC\_085** | 5.50 | **3.9041** | [2.87 – 4.93] (±1.03) | 21.47 |
| 24 | **AGC\_086** | 4.73 | **2.9456** | [2.40 – 3.49] (±0.54) | 13.93 |
| 25 | **AGC\_087** | 5.66 | **2.7039** | [2.16 – 3.25] (±0.54) | 15.30 |
| 26 | **AGC\_088** | 5.91 | **4.3724** | [3.83 – 4.92] (±0.54) | 25.84 |
| 27 | **AGC\_091** | 0.35 | **4.6763** | [4.13 – 5.22] (±0.54) | 1.64 |
| 28 | **AGC\_093** | 3.71 | **3.0785** | [2.53 – 3.62] (±0.54) | 11.42 |
| 29 | **AGC\_094** | 3.63 | **4.6595** | [4.12 – 5.20] (±0.54) | 16.91 |
| 30 | **AGC\_095** | 1.33 | **4.5230** | [3.98 – 5.07] (±0.54) | 6.02 |
| 31 | **AGC\_107** | 2.63 | **4.5277** | [3.98 – 5.07] (±0.54) | 11.91 |
| 32 | **AGC\_113** | 10.58 | **3.0503** | [2.45 – 3.65] (±0.60) | 32.27 |
| 33 | **AGC\_116** | 7.43 | **4.3521** | [3.81 – 4.90] (±0.54) | 32.34 |
| 34 | **AGC\_118** | 4.42 | **3.1135** | [2.57 – 3.66] (±0.54) | 13.76 |
| 35 | **AGC\_120** | 7.47 | **3.2973** | [2.62 – 3.97] (±0.67) | 24.63 |
| 36 | **AGC\_126** | 5.75 | **4.3411** | [3.80 – 4.88] (±0.54) | 24.96 |
| 37 | **AGC\_128** | 6.15 | **4.3601** | [3.82 – 4.90] (±0.54) | 26.81 |
| 38 | **AGC\_129** | 8.16 | **3.3103** | [2.35 – 4.27] (±0.96) | 27.01 |
| 39 | **AGC\_130** | 12.10 | **4.3110** | [3.77 – 4.85] (±0.54) | 52.16 |
| 40 | **AGC\_136** | 1.69 | **4.2397** | [3.70 – 4.78] (±0.54) | 7.17 |
| 41 | **AGC\_142** | 1.29 | **4.9891** | [4.45 – 5.53] (±0.54) | 6.44 |
| 42 | **AGC\_143** | 11.48 | **4.5561** | [4.01 – 5.10] (±0.54) | 52.30 |
| 43 | **AGC\_147** | 6.80 | **3.0317** | [2.49 – 3.58] (±0.54) | 20.62 |
| 44 | **AGC\_149** | 8.99 | **4.4166** | [3.87 – 4.96] (±0.54) | 39.71 |
| 45 | **AGC\_153** | 1.99 | **4.2450** | [3.70 – 4.79] (±0.54) | 8.45 |
| 46 | **AGC\_154** | 1.49 | **4.6823** | [4.14 – 5.23] (±0.54) | 6.98 |
| 47 | **AGC\_156** | 8.20 | **3.1428** | [2.60 – 3.69] (±0.54) | 25.77 |
| 48 | **AGC\_158** | 11.22 | **4.2852** | [3.74 – 4.83] (±0.54) | 48.08 |
| 49 | **AGC\_173** | 3.60 | **3.4046** | [2.17 – 4.64] (±1.24) | 12.26 |
| 50 | **AGC\_174** | 6.89 | **3.8811** | [3.23 – 4.53] (±0.65) | 26.74 |
| 51 | **AGC\_175** | 1.41 | **4.1996** | [3.61 – 4.79] (±0.59) | 5.92 |
| 52 | **AGC\_177** | 5.66 | **4.3128** | [3.77 – 4.86] (±0.54) | 24.41 |
| 53 | **AGC\_182** | 4.13 | **4.4568** | [3.91 – 5.00] (±0.54) | 18.41 |
| 54 | **AGC\_183** | 7.85 | **2.9540** | [2.41 – 3.50] (±0.54) | 23.19 |
| 55 | **AGC\_186** | 11.70 | **4.4211** | [3.88 – 4.96] (±0.54) | 51.73 |
| 56 | **AGC\_188** | 2.34 | **4.5730** | [4.03 – 5.12] (±0.54) | 10.70 |
| 57 | **AGC\_190** | 5.01 | **4.3427** | [3.80 – 4.89] (±0.54) | 21.76 |
| 58 | **AGC\_191** | 1.75 | **4.9337** | [4.39 – 5.48] (±0.54) | 8.63 |
| 59 | **AGC\_192** | 2.14 | **4.9813** | [4.44 – 5.53] (±0.54) | 10.66 |

© 2026 Equipo Agrotec-Amanteca · Todos los derechos reservados · Reto AgroCebada FIRA 2026
Integrantes: Gael Askary Razo Montañez · Limhi Gerson López Momox · Karla Yaneth Cruz Sandoval · Arturo Huerta Maldonado · Juan Enrique Gutierrez Hernández