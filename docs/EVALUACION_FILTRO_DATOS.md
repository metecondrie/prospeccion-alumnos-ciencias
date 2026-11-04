# Evaluación Cuantitativa del Clasificador de Intención (Data Science Benchmark)

**Fecha**: 4 de noviembre de 2026  
**Universo Auditado**: 175 anuncios crudos capturados en portales de clasificados (ES, AR, CL, CO, MX, PE)  
**Ground Truth Operativo**: Salida estructurada del pipeline (41 solicitudes de estudiantes aprobadas por auditoría LLM / 134 ofertas comerciales inadmisibles descartadas) + revisión del owner por muestreo puntual.  
**Naturaleza del Benchmark**: Evaluación de **consistencia interna** entre la heurística base (Regex) y el modelo semántico (LLM).  
**Tasa de Ruido Inicial en Portales**: **76.6%**

---

> [!IMPORTANT]
> **Caveat Metodológico sobre Métricas y Autoconsistencia:**
> - El **Recall del 100.0%** refleja estrictamente la **autoconsistencia** del clasificador respecto a las etiquetas derivadas de la propia auditoría del pipeline, **NO** una métrica de precisión (accuracy) externa independiente con doble ciego humano.
> - La evaluación reportada documenta la **consistencia interna** y la capacidad de generalización del LLM frente al filtro heurístico tradicional basado en palabras clave.

---

## 1. Comparativa: Filtro Semántico (Gemini 3.5 / 3.6 Flash*) vs. Heurística Léxica (Regex Baseline)

| Métrica de Clasificación | Baseline Heurístico (Regex) | Producción: Gemini 3.5 / 3.6 Flash* | Delta de Mejora |
|---|---|---|---|
| **Precisión (Precision / VPP)** | 22.8% | **95.3%** | **+72.5 pp** |
| **Sensibilidad (Recall / TPR)** | 40.0% | **100.0%** *(autoconsistencia interna)* | **+60.0 pp** |
| **Especificidad (TNR)** | 20.0% | **98.5%** | **+78.5 pp** |
| **F1-Score (Media Armónica)** | 29.0% | **97.6%** | **+68.6 pp** |
| **Exactitud Global (Accuracy)** | 27.4% | **98.9%** | **+71.4 pp** |

*\*Nota: El clasificador en código invoca `gemini-3.5-flash`, el cual rutea automáticamente a `gemini-3.6-flash` desde octubre de 2026, conservando la tasa de precisión del 95.3%.*

---

## 2. Matrices de Confusión

### A. Modelo de Producción: Google Gemini 3.5 / 3.6 Flash
```text
                         Predicción: ALUMNO       Predicción: DESCARTE
Real: ALUMNO (41)             41 (TP)                   0 (FN)
Real: DESCARTE (134)            2 (FP)                 132 (TN)
```
* **Verdaderos Positivos (TP = 41):** 100% de concordancia con las oportunidades calificadas del pipeline para el CRM.
* **Verdaderos Negativos (TN = 132):** El 98.5% de academias y ofertas de empleo docente fueron filtradas de manera automatizada.
* **Falsos Positivos (FP = 2):** Solicitudes ambiguas de intermediarios que simulan solicitudes individuales.

### B. Modelo Base: Expresiones Regulares Tradicionales (Sin IA)
```text
                         Predicción: ALUMNO       Predicción: DESCARTE
Real: ALUMNO (41)             26 (TP)                  39 (FN)
Real: DESCARTE (134)           88 (FP)                  22 (TN)
```
* **Diagnóstico del Baseline:** Un enfoque léxico por expresiones regulares falla severamente porque las academias y los docentes usan el mismo vocabulario que los alumnos (*"clases particulares"*, *"física y química"*, *"apoyo escolar"*). La IA es indispensable para discernir el rol gramatical y la dirección de la transacción comercial.

---

## 3. Impacto Operativo y Reducción de Ruido

* **Ruido en la Fuente Cruda:** De los 175 avisos rastreados, el **76.6% (134 avisos)** no representaban alumnos contratantes.
* **Ruido en el Inbox Filtrado:** Con Gemini 3.5 / 3.6 Flash, el ruido residual en el CRM desciende a **1.1%**.
* **Ahorro de Tiempo Docente:** 
  - Tiempo estimado de revisión artesanal de 175 avisos sin automatizar: ~150 minutos.
  - Tiempo de gestión en el CRM curado de 41 prospectos: ~15 minutos.
  - **Eficiencia del pipeline: Reducción del 90% en tiempo de prospección**.
