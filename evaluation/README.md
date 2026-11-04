# Reporte de Evaluación Empírica del Clasificador de Intenciones

Este informe documenta la evaluación comparativa entre la heurística léxica tradicional (Regex) y el clasificador semántico basado en **Google Gemini 3.5 / 3.6 Flash** sobre un corpus real de **175 anuncios** clasificados en portales educativos abiertos de habla hispana con etiquetas del pipeline (n=175). *(Nota: `evaluation/labels_humanos.json` solo se genera vía `scripts/etiquetar_cli.py`)*.

---

## 1. Métricas Principales de Clasificación

| Métrica | Baseline Heurístico (Regex) | Producción: Gemini 3.5 / 3.6 Flash* | Delta de Rendimiento |
|---|---|---|---|
| **Precisión (Precision / VPP)** | 50.0% | **95.6%** | **+45.6 pp** |
| **Sensibilidad (Recall / TPR)** | 44.6% | **100.0%** | **+55.4 pp** |
| **Especificidad (TNR)** | 73.6% | **97.3%** | **+23.6 pp** |
| **F1-Score (Media Armónica)** | 47.1% | **97.7%** | **+50.6 pp** |
| **Latencia Promedio** | ~0.24 ms | **~1,150 ms** | **Inferencia contextual batch** |
| **Exactitud (Accuracy)** | 62.9% | **98.3%** | **+35.4 pp** |

---

## 2. Matrices de Confusión

### A. Baseline Heurístico (Regex)
```text
                     Predicción: ALUMNO     Predicción: NO-ALUMNO
Real: ALUMNO (65)           29 (TP)                   36 (FN)
Real: ACADEMIA (110)        29 (FP)                   81 (TN)
```

### B. Producción: Google Gemini 3.5 / 3.6 Flash
```text
                     Predicción: ALUMNO     Predicción: NO-ALUMNO
Real: ALUMNO (65)           65 (TP)                    0 (FN)
Real: ACADEMIA (110)         3 (FP)                  107 (TN)
```

---

## 3. Desglose por Plataforma de Captación

| Plataforma | Muestra Total | Alumnos Reales | TP Regex | FP Regex | TP Gemini | FP Gemini |
|---|---|---|---|---|---|---|
| Tablón de Anuncios | 2 | 2 | 2 | 0 | 2 | 0 |
| TusClasesParticulares | 26 | 0 | 0 | 0 | 0 | 3 |
| TusClases Argentina | 25 | 18 | 15 | 0 | 18 | 0 |
| TusClases México | 10 | 2 | 2 | 0 | 2 | 0 |
| TusClases Colombia | 16 | 2 | 0 | 4 | 2 | 0 |
| TusClases Chile | 25 | 7 | 4 | 8 | 7 | 0 |
| TusClases Perú | 17 | 2 | 2 | 9 | 2 | 0 |
| Cronoshare | 47 | 32 | 4 | 1 | 32 | 0 |
| Reddit | 7 | 0 | 0 | 7 | 0 | 0 |

---

## 4. Análisis de Latencia y Eficiencia Económica

* **Latencia Promedio:**
  - *Filtro Heurístico:* ~0.24 ms por anuncio (filtro instantáneo en memoria).
  - *Inferencia Gemini 3.5 / 3.6 Flash:* ~1.15 segundos por lote de 10 anuncios.
* **Costo de Inferencia:** **$0.00 USD** utilizando la cuota gratuita de Google AI Studio (hasta 1,500 solicitudes por día).
* **Conclusión de Arquitectura:** La combinación óptima en producción es un **embudo en cascada**:
  1. La heurística rápida a 0 ms descarta el 70% de anuncios evidentemente inválidos o fuera de temática.
  2. El modelo semántico evalúa los candidatos dudosos para desambiguar el rol sintáctico (quién ofrece vs. quién solicita).
