# Protocolo de Criterios para Futuro Etiquetado Independiente

Este documento establece los criterios metodológicos y las directrices técnicas diseñadas para la **futura ejecución de un proceso de etiquetado independiente** sobre el universo de anuncios de portales clasificados y redes sociales.

> [!NOTE]
> **Estado del Proceso**: Criterios de diseño metodológico propuestos. **No ha sido ejecutado aún**.
> En el estado actual del repositorio, la referencia de evaluación del pipeline proviene de la salida estructurada auditada por LLM (41 aprobados / 134 descartados) validada mediante revisión del owner por muestreo puntual. Las métricas reportadas reflejan consistencia interna y autoconsistencia del pipeline frente a sus propias etiquetas, no una evaluación externa independiente.

---

## 1. Definición de Clases para Futura Anotación

* **Clase Positiva (Etiqueta = 1 — Alumno Genuino):**  
  Cualquier publicación donde un individuo (estudiante o padre/tutor en su representación) solicita expresamente la contratación de clases particulares o apoyo académico en ciencias exactas (Matemáticas, Física, Química, Biología o áreas afines de ingeniería/salud).

* **Clase Negativa (Etiqueta = 0 — No Alumno / Ruido):**  
  - **Docentes particulares:** Profesores que publican para ofrecer sus propios servicios.
  - **Academias e institutos:** Empresas comerciales que ofrecen cursos, diplomaturas o captación de profesores.
  - **Publicaciones irrelevantes:** Consultas administrativas, venta de apuntes o charlas generales en grupos.

---

## 2. Reglas Específicas de Decisión para Anotadores

### 2.1 Indicadores Positivos de Alumno (Clase 1)
1. **Intención de demanda en primera persona:**
   * *"Busco profesor para..."*, *"Necesito alguien que me explique..."*, *"¿Alguien que prepare para el examen de...?"*.
2. **Contexto de evaluación inminente:**
   * Mención de materias específicas, programas universitarios (*CBC, UBA XXI, PAES, Selectividad*), o fechas de parciales y finales.
3. **Solicitudes por terceros directos:**
   * Padres o familiares buscando tutor para sus hijos de nivel secundario o primario (*"Busco profe para mi hijo de 3er año"*). Se consideran prospectos válidos de clase particular.

### 2.2 Indicadores Negativos de Exclusión (Clase 0)
1. **Oferta explícita de servicios docentes:**
   * *"Doy clases..."*, *"Ofrezco apoyo..."*, *"Profesor particular con 10 años de experiencia..."*.
2. **Promociones comerciales:**
   * *"Primera clase gratis"*, *"Grupos reducidos"*, *"Aranceles promocionales por hora"*.
3. **Reclutamiento docente:**
   * *"Academia busca incorporar profesores de matemáticas"*.
4. **Venta de material:**
   * *"Vendo resumen de biofísica"*, *"Vendo libro de Stewart"*.

---

## 3. Protocolo Propuesto para Futura Auditoría Cruzada

* **Asignación Ciega:** En la futura etapa de anotación, los 175 registros extraídos se presentarán sin revelar las predicciones previas de los modelos a los evaluadores independientes.
* **Resolución de Ambigüedades:** En casos de ambigüedad sintáctica (por ejemplo, textos muy breves como *"Clases de análisis"*), el evaluador consultará la URL o endpoint original para constatar si el aviso se emitió en la categoría de oferta de servicios o demanda de clases.
* **Concordancia Inter-Evaluador:** Se calculará el índice Kappa de Fleiss/Cohen entre al menos dos anotadores independientes para establecer un patrón de referencia definitivo y libre de sesgos del propio pipeline.
