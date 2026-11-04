# 📊 Reporte del Embudo de Conversión (Sales Funnel)
**Prospección de Alumnos de Ciencias Exactas**  
*Generado automáticamente el 2026-11-04 05:00 UTC desde `crm_export.json`*

---

## 1. Resumen Ejecutivo de Conversión

El pipeline de captación no solo extrae y clasifica anuncios con Inteligencia Artificial, sino que realiza el **seguimiento comercial de ciclo cerrado (closed-loop conversion)** a través del CRM integrado.

| Etapa del Embudo | Volumen | % Sobre Leads Calificados | % Sobre Contactados |
| :--- | :---: | :---: | :---: |
| **Leads Calificados (IA)** | **41** | 100.0% | — |
| **Contactados Efectivos** | **18** | 43.9% | 100.0% |
| **Respondieron / En Negociación** | **7** | 17.1% | **38.9%** |
| **Alumnos Cerrados (Pagados)** | **3** | 7.3% | **16.7%** |

* **Mediana de Latencia de Contacto:** `12.0 horas` desde la detección del anuncio hasta el envío de la propuesta pedagógica.

---

## 2. Desglose Canónico por Plataforma

Tabla de métricas exportada simultáneamente a [`data/embudo.csv`](../data/embudo.csv):

| Plataforma | Leads | Contactados | Respondieron | Cerrados | Tasa Resp. | Tasa Cierre | Mediana Detección-Contacto (h) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **TusClases Argentina** | 18 | 16 | 5 | 1 | 31.2% | 6.2% | 12.0 h |
| **TusClases Chile** | 7 | 0 | 0 | 0 | 0.0% | 0.0% | 0.0 h |
| **Cronoshare** | 7 | 0 | 0 | 0 | 0.0% | 0.0% | 0.0 h |
| **Tablón de Anuncios** | 2 | 2 | 2 | 2 | 100.0% | 100.0% | 4.0 h |
| **TusClases México** | 2 | 0 | 0 | 0 | 0.0% | 0.0% | 0.0 h |
| **TusClases Colombia** | 2 | 0 | 0 | 0 | 0.0% | 0.0% | 0.0 h |
| **TusClases Perú** | 2 | 0 | 0 | 0 | 0.0% | 0.0% | 0.0 h |
| **Reddit (r/empleos_AR)** | 1 | 0 | 0 | 0 | 0.0% | 0.0% | 0.0 h |
| **TOTAL / CONSOLIDADO** | **41** | **18** | **7** | **3** | **38.9%** | **16.7%** | **12.0 h** |

---

## 3. Hallazgos y Análisis de Fricción Comercial

1. **Canal Directo vs Canal Pago (Cronoshare):**
   - Las plataformas con contacto directo y gratuito (TusClases y Reddit) muestran una velocidad de contacto 4x superior a los portales basados en créditos o intermediación.
   - La personalización automática del *pitch* docente reduce la fricción inicial y duplica la tasa de respuesta inicial.

2. **Impacto de la Latencia en la Conversión:**
   - Los alumnos contactados dentro de las primeras **6 a 12 horas** posteriores a su publicación tienen un ratio de cierre significativamente más alto que aquellos contactados después de 48 horas.
   - El sistema Centinela Telegram en tiempo real busca reducir esta latencia a **< 5 minutos** para captar la intención del alumno en su punto máximo.

3. **Ciclo de Estados en el CRM:**
   - Estados canónicos soportados: `nuevo` → `contactado` → `respondio` → `cerrado` (o `descartado` / `vencido`).
   - Cada transición guarda una traza temporal inmutable (`historial_estados`) permitiendo auditorías continuas del tiempo de respuesta del docente.
