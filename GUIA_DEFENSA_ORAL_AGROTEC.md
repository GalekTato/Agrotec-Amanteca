# Guía de defensa oral — Agrotec-Amanteca

## 1. Mensaje central del proyecto

> **Agrotec-Amanteca es un sistema de apoyo a la decisión para estimar rendimiento de cebada por parcela. Integra información satelital, climática, topográfica y espacial en un modelo de ensamble, valida su desempeño con predicciones fuera de muestra y comunica tanto la predicción como su incertidumbre en un dashboard cartográfico.**

La propuesta no pretende demostrar causalidad agronómica ni sustituir una medición de campo. Su objetivo es ser:

- **Confiable:** compara contra referencias y reporta error e incertidumbre.
- **Estable:** usa validación cruzada repetida, semillas controladas y un ensamble de modelos.
- **Lógica:** las variables representan vigor vegetal, agua, temperatura, fisiografía y contexto espacial.
- **Operativa:** entrega resultados por parcela en un mapa, una API y archivos reproducibles.

La respuesta corta para abrir la presentación puede ser:

> “No afirmamos que el modelo conozca el futuro ni que sus asociaciones sean causales. Afirmamos algo más defendible: con las 138 parcelas etiquetadas disponibles, el modelo generaliza mejor que predecir la media y que el baseline de Random Forest, y sus resultados se entregan con una banda de incertidumbre y trazabilidad completa.”

---

## 2. ¿Qué problema resuelve?

El reto contiene **197 polígonos agrícolas**:

- **138 parcelas de entrenamiento**, con rendimiento observado.
- **59 parcelas de predicción ciega**, sin rendimiento disponible al entrenar.
- Aproximadamente **1,301.05 ha** en total.
- Variable objetivo: `RENDIMIENTO_T_HA`, expresada en toneladas por hectárea.

El sistema responde tres preguntas:

1. ¿Cuál es el rendimiento estimado de cada parcela?
2. ¿Qué tan incierta es esa estimación?
3. ¿Cómo cambia la predicción si se modifica un escenario de vigor satelital, precipitación o temperatura?

Es importante distinguir:

- **Predicción:** una estimación estadística del rendimiento.
- **Simulación:** una evaluación de qué ocurre con el modelo al modificar entradas.
- **Causalidad:** una afirmación experimental de que cambiar una variable produce físicamente un efecto. El proyecto **no** hace esta última afirmación.

---

## 3. Arquitectura completa del sistema

```text
Datos geoespaciales y ambientales
        |
        v
Matriz tabular por parcela
        |
        v
Ingeniería agronómica + coordenadas
        |
        v
LeakFreeSmartPearsonIDW
        |
        v
23 predictores finales
        |
        v
VotingRegressor
  Extra Trees 40%
  Random Forest 25%
  SVR 20%
  Gradient Boosting 15%
        |
        +--> Validación cruzada, OOF e incertidumbre
        +--> best_model.joblib
        +--> predicciones_59_parcelas.csv
        +--> sensibilidad_simulador.json
        +--> metrics_summary.json
                         |
                         +--> FastAPI
                         +--> React/Vite/Leaflet/Recharts
                         +--> GitHub Pages
```

### Componentes principales

| Componente | Función |
|---|---|
| `ml_pipeline/models/02_train_and_export_artifacts.py` | Entrena, valida y exporta el modelo y los artefactos |
| `backend/agro_core.py` | Núcleo compartido de variables, selección e IDW |
| `backend/artifacts/best_model.joblib` | Modelo serializado para inferencia |
| `backend/artifacts/metrics_summary.json` | Fuente de verdad de métricas |
| `backend/artifacts/sensibilidad_simulador.json` | Superficie de escenarios precalculados |
| `backend/main.py` | API FastAPI y simulador dinámico |
| `frontend/src/App.jsx` | Dashboard, métricas y simulador |
| `frontend/src/components/ParcelMap.jsx` | Mapa Leaflet por capas |
| `docs/` | Build estático publicado en GitHub Pages |

---

## 4. De dónde salen las variables

### 4.1 Vigor satelital

NDVI y EVI resumen el vigor y la respuesta espectral de la vegetación en distintos meses. No se usa únicamente un mes aislado: la serie mensual permite representar etapas del ciclo del cultivo.

Una forma sencilla de explicarlo:

> “El NDVI no es rendimiento. Es una señal indirecta del estado de la cubierta vegetal. El modelo aprende si determinados patrones temporales de vigor se asocian con mayor o menor rendimiento dentro de las parcelas observadas.”

### 4.2 Precipitación CHIRPS

Las variables `prec_*` representan acumulaciones o resúmenes temporales de precipitación. Se usan para capturar disponibilidad hídrica y posibles periodos de estrés.

Para parcelas pequeñas, la extracción zonal se documenta con `all_touched=True`, de modo que no se descarte una parcela por no contener completamente el centro de un píxel climático.

### 4.3 Temperatura

Las variables `tmax_*` y `tmin_*` representan el régimen térmico. La temperatura puede afectar desarrollo, llenado de grano y estrés; el modelo aprende asociaciones históricas, no una función fisiológica universal.

### 4.4 Topografía y superficie

Se incorporan elevación, pendiente y superficie de parcela. La pendiente participa también en el índice sintético de retención topográfica.

### 4.5 Índices agronómicos sintéticos

`add_agronomic_features` calcula cinco variables fila por fila:

1. `ndvi_auc_verano`: aproximación de la integral de NDVI entre mayo y octubre.
2. `ndvi_tasa_vegetativa`: diferencia entre agosto y mayo.
3. `ndvi_caida_madurez`: diferencia entre agosto y octubre.
4. `indice_hidrotermico`: precipitación clave dividida entre temperatura máxima más 10.
5. `retencion_topografica`: precipitación clave dividida entre uno más la pendiente.

Defensa correcta:

> “Son índices de ingeniería de variables con interpretación agronómica plausible. No son mediciones fisiológicas directas ni leyes biológicas calibradas universalmente. Se calculan de forma determinista y fila por fila, sin consultar el rendimiento objetivo.”

---

## 5. Por qué se proyectan los centroides y el IDW

Las geometrías se leen y se visualizan en WGS84 (`EPSG:4326`, latitud/longitud), pero latitud y longitud están expresadas en grados. No es correcto interpretar directamente una diferencia de grados como una distancia métrica uniforme.

Por eso:

1. Los polígonos se reproyectan temporalmente a **UTM Zona 14N (`EPSG:32614`)**.
2. Allí se calculan los centroides sin advertencia de geometría en coordenadas geográficas.
3. Los centroides se convierten nuevamente a WGS84 para almacenar y visualizar.
4. Para IDW, las coordenadas lat/lon se vuelven a transformar a UTM antes de usar `cdist`.

La respuesta ante un jurado es:

> “Guardamos WGS84 porque es el estándar de intercambio y del mapa, pero calculamos geometría y distancias en UTM 14N porque es un sistema métrico adecuado para la zona.”

### ¿Qué significa el IDW?

El IDW estima un potencial espacial a partir de las siete parcelas de referencia más cercanas:

```text
peso_i = 1 / distancia_i^1.5
IDW = suma(peso_i * rendimiento_i) / suma(peso_i)
```

El transformador excluye coincidencias exactas para no reutilizar directamente la etiqueta de la misma parcela. Durante validación cruzada, el IDW usa únicamente las coordenadas y rendimientos del pliegue de entrenamiento.

Esto evita la fuga más peligrosa: que el rendimiento real de una parcela de validación entre indirectamente en su propio predictor.

---

## 6. Selección de las 23 variables

El modelo final trabaja con:

- **22 variables** seleccionadas por `Smart-Pearson`.
- **1 variable** adicional: `spatial_idw_yield`.

El selector:

1. Calcula la correlación absoluta de cada predictor con `y` **solo dentro del conjunto de entrenamiento del fold**.
2. Ordena por relevancia.
3. Elimina variables excesivamente colineales con otras ya elegidas (`|r| >= 0.88`).
4. Conserva hasta `top_k=22`.
5. Añade el predictor espacial IDW.

La palabra clave es **dentro del fold**. Si el selector se hubiera ajustado usando las 138 etiquetas antes de dividir, la validación sería optimista. La implementación actual integra el selector como transformador de Scikit-Learn, por lo que cada entrenamiento de fold ajusta su propia selección.

La paridad se verifica porque el artefacto contiene `feature_cols`, y las pruebas comprueban que son 23 y que coinciden con las columnas esperadas.

---

## 7. Cómo funciona el modelo

El modelo seleccionado es un `VotingRegressor` heterogéneo:

| Modelo | Peso | Qué aporta |
|---|---:|---|
| Extra Trees | 40% | Captura relaciones no lineales y reduce varianza mediante aleatoriedad |
| Random Forest podado | 25% | Aporta estabilidad mediante bagging |
| SVR con kernel RBF y `RobustScaler` | 20% | Suaviza relaciones y maneja escalas mediante rangos robustos |
| Gradient Boosting | 15% | Captura correcciones secuenciales y gradientes no lineales |

La predicción final es una combinación ponderada de las cuatro salidas. La razón de usar un ensamble no es “hacerlo más complejo por sí mismo”, sino reducir dependencia de una sola familia algorítmica.

### ¿Por qué no usar el modelo más complejo?

Porque el criterio no fue complejidad. Se evaluaron varias configuraciones y se eligió la que tuvo menor error en 5-Fold y en 5×5 Repeated CV. Si un modelo más simple fuera más estable, sería preferible.

---

## 8. Cómo se validó

### 8.1 5-Fold CV

Las 138 parcelas etiquetadas se dividen en cinco pliegues. En cada iteración:

1. Se ajusta todo el pipeline con cuatro pliegues.
2. Se predice el pliegue dejado fuera.
3. Se repite hasta obtener una predicción fuera de muestra para cada parcela.

La configuración usa `shuffle=True` y `random_state=42`.

### 8.2 5×5 Repeated CV

Se repite el procedimiento de cinco pliegues cinco veces con distintas particiones controladas. Esto permite observar si el resultado depende demasiado de una única división.

No convierte una muestra pequeña en una muestra grande, pero sí proporciona una medida más estable de variabilidad del procedimiento.

### 8.3 Predicciones OOF

OOF significa **Out-Of-Fold**. Cada predicción OOF se produce con un modelo que no vio la etiqueta de esa parcela durante el ajuste correspondiente.

Por eso se usan para:

- MAE y RMSE honestos.
- Error por parcela.
- Porcentaje con error menor o igual a `0.50 t/ha`.
- Cobertura empírica de intervalos.

### 8.4 Comparaciones

El modelo se compara contra:

- `DummyRegressor(strategy="mean")`: siempre predice la media del entrenamiento.
- Random Forest baseline con las 39 variables del filtro original.
- Modelos individuales y otras arquitecturas evaluadas.

El baseline no se presenta como un número inventado: se ajusta, se valida con CV y se calculan sus predicciones OOF por separado.

---

## 9. Resultados que deben memorizar

Las cifras provienen de `backend/artifacts/metrics_summary.json`:

| Métrica | Resultado del ensamble |
|---|---:|
| MAE 5-Fold | **0.3562 ± 0.0662 t/ha** |
| RMSE 5-Fold | **0.4968 ± 0.1084 t/ha** |
| RMSE 5×5 Repeated CV | **0.5073 ± 0.1183 t/ha** |
| R² 5-Fold | **0.6124 ± 0.1804** |
| Error OOF ≤ 0.50 t/ha | **72.5%** |
| Cobertura empírica de intervalo nominal 80% | **81.2%** |
| Semiancho medio del intervalo | **0.584 t/ha** |
| Predictores finales | **23** |

### Cómo interpretar las métricas

- **MAE 0.3562:** en promedio, el error absoluto fue de aproximadamente 0.36 t/ha.
- **RMSE 0.4968:** penaliza más los errores grandes; está cerca de 0.50 t/ha.
- **R² 0.6124:** el modelo explica aproximadamente 61% de la variabilidad observada en esta validación, no “61% de certeza”.
- **81.2% de cobertura:** de las parcelas OOF evaluadas, aproximadamente 81.2% quedaron dentro de la banda construida para un objetivo nominal de 80%.

Nunca decir:

- “El modelo tiene 61% de precisión.”
- “El intervalo garantiza 80% en cualquier región.”
- “El simulador demuestra que llover más causa exactamente X toneladas.”

Decir:

- “El R² fue 0.6124 en esta validación.”
- “La cobertura empírica OOF fue 81.2%.”
- “La simulación es una respuesta del modelo ante entradas modificadas, no un experimento causal.”

---

## 10. Incertidumbre y conformal

El sistema no entrega únicamente un punto. También genera una banda:

```text
predicción - semiancho <= rendimiento esperado <= predicción + semiancho
```

El factor conformal se calibra a partir de errores OOF y se combina con una escala relacionada con la dispersión de los submodelos. La cobertura reportada es empírica sobre OOF.

La explicación rigurosa es:

> “Usamos calibración conformal basada en residuos fuera de muestra. El 80% es el nivel nominal y 81.2% es la cobertura empírica observada en estas 138 parcelas. No lo presentamos como una garantía universal fuera de la distribución de datos.”

### ¿Por qué el intervalo no tiene el mismo ancho en todas las parcelas?

Porque el ancho incorpora una escala de dispersión por parcela, con un mínimo para evitar intervalos artificialmente estrechos. Una parcela donde los submodelos discrepan más recibe mayor incertidumbre.

### ¿El intervalo significa que el rendimiento real estará siempre allí?

No. Es una banda calibrada estadísticamente bajo condiciones parecidas a los datos de validación. Si aparece una parcela en otra región, otro ciclo agrícola o bajo condiciones fuera de rango, la cobertura puede deteriorarse.

---

## 11. Cómo funciona el simulador

El simulador permite cambiar:

- NDVI/EVI: porcentaje relativo.
- Precipitación: porcentaje relativo.
- Temperatura máxima y mínima: cambio absoluto en °C.

Antes de predecir:

1. Copia la fila de la parcela.
2. Modifica las variables ambientales correspondientes.
3. Recalcula los cinco índices agronómicos sintéticos.
4. Aplica el mismo modelo y las mismas 23 variables.
5. Devuelve rendimiento simulado, diferencia, producción total e intervalo.

Los escenarios combinados se evalúan conjuntamente para conservar las interacciones no lineales. Esto es superior a sumar tres efectos marginales como si el modelo fuera lineal.

La malla `combined_deltas` en `sensibilidad_simulador.json` permite que el frontend estático responda rápidamente. Si el backend está disponible, `/api/simular` evalúa el escenario directamente con `best_model.joblib`. Para valores entre puntos de la malla, el frontend interpola como fallback visual; la API puede calcular el modelo directamente.

### ¿La curva fenológica es una nueva predicción por etapa?

No debe presentarse así. Es una visualización de la variación porcentual del escenario sobre la ventana fenológica activa. Sirve para comunicar respuesta dinámica, pero no constituye una predicción independiente de rendimiento en cada día o etapa.

### Validaciones del API

El endpoint rechaza:

- Parcelas inexistentes: `404`.
- Valores fuera de límites: `422`.
- Variables personalizadas desconocidas: `422`.
- Valores no finitos: `422`.

---

## 12. Frontend, API y GitHub Pages

### Dashboard

React construye la interfaz y Vite genera el bundle. Leaflet muestra:

- Parcelas de entrenamiento y predicción.
- Colores por rendimiento.
- Selección de parcela.
- Capas cartográficas.

Recharts muestra métricas, comparaciones y respuesta fenológica.

### API

FastAPI carga los artefactos con un evento de `lifespan` y mantiene un cache en memoria. Los endpoints principales son:

| Endpoint | Uso |
|---|---|
| `/api/health` | Estado de artefactos y modelo |
| `/api/summary` | Métricas auditadas |
| `/api/parcelas` | GeoJSON completo o filtrado |
| `/api/parcelas/{id}` | Detalle de una parcela |
| `/api/sensibilidad` | Superficie precalculada |
| `/api/simular` | Escenario dinámico |
| `/api/export/csv` | Exportación de predicciones |

### GitHub Pages

GitHub Pages sirve el contenido estático de `docs/`. Por eso el dashboard puede abrirse aunque la API no esté desplegada: usa datos sincronizados en `frontend/public/data` y `docs/data`.

La diferencia importante es:

- **Modo estático:** usa artefactos JSON y superficie precalculada.
- **Modo API:** consulta `/api/simular` para evaluar escenarios dinámicamente.

---

## 13. ¿Debe aumentarse el tamaño de muestra?

### Respuesta corta

**Sí, si se busca aumentar la confianza de generalización. No porque el modelo actual sea inválido.**

Con 138 parcelas, el proyecto puede demostrar una señal predictiva útil, pero la incertidumbre estadística sigue siendo relevante. El RMSE repetido `0.5073 ± 0.1183` muestra que el desempeño cambia entre particiones.

### ¿Cuántas parcelas serían ideales?

No existe un número mágico. Como orientación:

- **138:** suficiente para un prototipo competitivo y una primera validación.
- **200–300 parcelas etiquetadas:** mejor estabilidad para seleccionar variables y comparar modelos.
- **300–500 o más:** preferible si se quiere evaluar varios ciclos, municipios o condiciones climáticas.

Más importante que sumar filas es aumentar la **diversidad y representatividad**:

- diferentes localidades;
- distintos tipos de suelo;
- rangos bajos, medios y altos de rendimiento;
- distintos años agrícolas;
- parcelas con distintos tamaños;
- presencia de eventos climáticos contrastantes.

Duplicar parcelas muy cercanas del mismo ciclo puede aumentar el número aparente sin aumentar la información independiente.

### ¿Cómo conseguir más datos correctamente?

1. Medir rendimiento real con un protocolo consistente.
2. Registrar fecha, variedad, manejo, fertilización, riego y cosecha.
3. Mantener la geometría y el identificador de cada parcela.
4. Repetir durante varios ciclos agrícolas.
5. Separar validación espacial y temporal.
6. Reservar un conjunto externo que no se use para ajustar decisiones.

### ¿Qué no debe hacerse?

- Crear etiquetas sintéticas y tratarlas como observaciones reales.
- Copiar varias veces las mismas parcelas.
- Mezclar parcelas vecinas entre entrenamiento y validación sin evaluar autocorrelación.
- Agregar datos externos sin el mismo criterio de medición.

### Siguiente mejora estadística

Con más parcelas, la mejora más importante sería una validación de bloque:

- **Leave-one-location-out** o `GroupKFold` por localidad/campo.
- Separación temporal por año.
- Un conjunto final completamente externo.

Esto respondería mejor a: “¿funciona en una zona o año que no vio durante el entrenamiento?”

---

## 14. Mejoras recomendadas por prioridad

### Prioridad 1 — Validación externa

Conseguir datos reales de una campaña posterior o localidad distinta y no tocar el modelo antes de medirlos. Es la evidencia más valiosa para confiabilidad.

### Prioridad 2 — Validación espacial y temporal

Añadir `GroupKFold` por zona o parcela agrupada y pruebas de generalización por año. La CV aleatoria es útil, pero parcelas cercanas pueden compartir condiciones.

### Prioridad 3 — Intervalos más rigurosos

Con más datos, usar calibración conformal separada o conformal adaptativa con un conjunto de calibración independiente. Reportar cobertura global y por subgrupos.

### Prioridad 4 — Monitoreo de deriva

Comparar en producción la distribución de NDVI, lluvia, temperatura y topografía contra la distribución de entrenamiento. Marcar como “fuera de dominio” las parcelas muy diferentes.

### Prioridad 5 — Reproducibilidad de datos

Versionar:

- huellas o checksums de rasters;
- fecha de descarga;
- CRS;
- resolución;
- tratamiento de `nodata`;
- versiones exactas de paquetes;
- semilla y configuración del pipeline.

### Prioridad 6 — Mejorar la semántica agronómica

Si se desea una simulación de manejo y no solo de escenarios, incorporar variables de manejo observadas y diseñar experimentos o análisis causales. El simulador actual debe seguir etiquetándose como **escenario del modelo**.

### Prioridad 7 — Mejorar la interfaz

Añadir en el dashboard:

- advertencia visible cuando un escenario está fuera de la malla;
- indicador de confianza o fuera de dominio;
- fecha y versión del modelo;
- explicación de que correlación no implica causalidad;
- botón para exportar el escenario simulado.

---

## 15. Preguntas difíciles del jurado y respuestas

### “¿Por qué 23 variables y no 39?”

> “No elegimos 23 por estética. El selector Smart-Pearson ordena variables por asociación con el rendimiento dentro del entrenamiento y elimina redundancia por colinealidad. La selección se repite dentro de cada fold. Después se agrega una sola variable espacial IDW. El artefacto final y las pruebas verifican las mismas 23 columnas.”

### “¿No hay fuga de información en el IDW?”

> “El IDW usa rendimientos únicamente de las parcelas de entrenamiento del fold. Además, excluye coincidencias exactas. Para inferir una parcela de predicción usa las referencias disponibles, pero no usa su rendimiento objetivo.”

### “¿No hay fuga al seleccionar variables con la variable objetivo?”

> “La selección usa la variable objetivo, pero se ajusta dentro de cada fold, no sobre todo el dataset antes de validar. Esa es precisamente la función del transformador integrado en el pipeline.”

### “¿El baseline de 39 variables fue medido de verdad?”

> “Sí. Se ajustó un Random Forest separado, se validó con los mismos esquemas de CV y se generaron sus predicciones OOF. Sus métricas se guardan en `metrics_summary.json`.”

### “¿Por qué confiar en un R² de 0.6124?”

> “No lo llamamos certeza. Significa que en la validación usada explica alrededor del 61% de la variabilidad observada. También reportamos MAE, RMSE, repetición 5×5 y cobertura, porque ninguna métrica aislada es suficiente.”

### “¿El 81.2% prueba que los intervalos son correctos?”

> “Prueba que en las 138 predicciones OOF observadas, el 81.2% quedó dentro de la banda nominal del 80%. Es una cobertura empírica, no una garantía universal para cualquier región o año.”

### “¿Por qué no usar una red neuronal?”

> “Con 138 parcelas etiquetadas, una red neuronal tendría alto riesgo de sobreajuste y no ofrece una ventaja justificada. Preferimos modelos tabulares regularizados, comparados con CV y un ensamble estable.”

### “¿El modelo descubre qué causa el rendimiento?”

> “No. Aprende asociaciones predictivas observacionales. Para afirmar causalidad se necesitarían diseños experimentales, tratamientos controlados o métodos causales con supuestos explícitos.”

### “¿El simulador demuestra que aumentar lluvia aumenta el rendimiento?”

> “No. Demuestra cómo responde el modelo cuando modificamos las entradas de precipitación. Es útil para explorar escenarios, pero no sustituye un experimento agronómico.”

### “¿Por qué una combinación no equivale a sumar NDVI, lluvia y temperatura?”

> “Porque el ensamble es no lineal. El efecto de una variable puede depender del nivel de las otras. Por eso los escenarios combinados se evalúan conjuntamente con el modelo.”

### “¿Qué pasa si la parcela está fuera del rango histórico?”

> “La predicción puede ser menos confiable. Por eso una mejora prioritaria es incorporar detección de fuera de dominio y validación externa. El intervalo no elimina ese riesgo.”

### “¿Por qué el dashboard funciona si no se ve un backend?”

> “GitHub Pages sirve un build estático. El frontend carga GeoJSON, métricas y superficie de sensibilidad versionados en `docs/data`. La API FastAPI existe para inferencia dinámica, pero la demo publicada también tiene un fallback estático.”

### “¿Qué parte aporta cada integrante?”

La respuesta debe ser veraz y acordada por el equipo. No inventen roles técnicos retrospectivos. Pueden explicar el trabajo por áreas solo si cada integrante realmente participó:

- datos y georreferenciación;
- modelado y validación;
- backend y pruebas;
- frontend y visualización;
- documentación y presentación.

Los cinco integrantes oficiales son:

1. Gael Askary Razo Montañez
2. Limhi Gerson López Momox
3. Karla Yaneth Cruz Sandoval
4. Arturo Huerta Maldonado
5. Juan Enrique Gutierrez Hernández

---

## 16. Respuestas que conviene evitar

No decir:

- “Tiene 100% de precisión.”
- “El modelo es causal.”
- “El intervalo siempre contiene el valor real.”
- “Más variables siempre significa mejor modelo.”
- “El IDW usa todas las parcelas sin riesgo.”
- “La curva fenológica predice el rendimiento diario.”
- “El R² es el porcentaje de aciertos.”
- “La app demuestra que una práctica agrícola funciona.”

Sustituir por:

- “Tiene error medido y reportado.”
- “Es predictivo y observacional.”
- “La cobertura fue empíricamente 81.2% en OOF.”
- “La selección busca reducir redundancia y sobreajuste.”
- “El IDW se calcula con referencias permitidas en cada fold.”
- “La curva comunica la respuesta del escenario del modelo.”

---

## 17. Guion de presentación de cinco minutos

### Minuto 1 — Problema

“Tenemos 197 parcelas de cebada, 138 con rendimiento observado y 59 parcelas ciegas. Queremos estimar rendimiento por parcela y mostrar dónde existe mayor o menor incertidumbre.”

### Minuto 2 — Datos y método

“Integramos NDVI/EVI, precipitación CHIRPS, temperatura, topografía y ubicación. Calculamos índices agronómicos deterministas y usamos selección Smart-Pearson más un IDW espacial en UTM 14N.”

### Minuto 3 — Modelo y validación

“El modelo es un VotingRegressor de Extra Trees, Random Forest, SVR y Gradient Boosting. Se validó con 5-Fold y 5×5 Repeated CV. Cada predicción OOF se produjo sin usar la etiqueta de la parcela evaluada.”

### Minuto 4 — Resultados

“Obtuvimos MAE 0.3562 t/ha, RMSE 0.4968 t/ha en 5-Fold, RMSE 0.5073 t/ha en 5×5 y R² 0.6124. El 72.5% de las parcelas OOF tuvo error menor o igual a 0.50 t/ha. La cobertura empírica del intervalo nominal de 80% fue 81.2%.”

### Minuto 5 — Producto y límites

“El resultado se consume en un dashboard cartográfico, una API y archivos exportables. El simulador evalúa escenarios conjuntos del modelo. No afirmamos causalidad: reconocemos que aumentar la muestra, validar por espacio y tiempo y medir campañas nuevas son las siguientes mejoras.”

---

## 18. Conclusión para el equipo

El proyecto ya es defendible porque no depende solo de una pantalla atractiva: tiene pipeline, artefactos, métricas, API, pruebas y una explicación honesta de sus límites.

La posición más fuerte ante el jurado no es prometer que el modelo es perfecto. Es demostrar que:

1. saben exactamente qué entra al modelo;
2. saben cómo se evitó la fuga de información;
3. pueden reproducir las métricas;
4. distinguen predicción de causalidad;
5. entienden que 138 parcelas permiten una primera solución, pero no agotan la validación;
6. tienen un plan claro para mejorar con datos nuevos.

**Veredicto técnico:** el sistema es confiable y lógico como herramienta predictiva inicial, suficientemente estable para la entrega actual y competitivo para clasificación. Su principal oportunidad de mejora no es añadir complejidad, sino obtener más observaciones independientes y validar fuera de las parcelas y condiciones históricas usadas para entrenar.
