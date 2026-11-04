# Protocolo de Anotación y Ground Truth — Clasificación de Prospectos

Este documento establece los criterios metodológicos y las directrices de etiquetado humano utilizadas para construir el conjunto de referencia (*Ground Truth*) de 175 anuncios de portales de clasificados y redes sociales.

---

## 1. Definición del Problema de Clasificación

* **Clase Positiva (Etiqueta = 1 — Alumno Genuino):**  
  Cualquier publicación donde un individuo (estudiante o padre/tutor en su representación) solicita expresamente la contratación de clases particulares o apoyo académico en ciencias exactas (Matemáticas, Física, Química, Biología o áreas afines de ingeniería/salud).

* **Clase Negativa (Etiqueta = 0 — No Alumno / Ruido):**  
  - **Docentes particulares:** Profesores que publican para ofrecer sus propios servicios.
  - **Academias e institutos:** Empresas comerciales que ofrecen cursos, diplomaturas o captación de profesores.
  - **Publicaciones irrelevantes:** Consultas administrativas, venta de apuntes, memes o charlas generales en grupos.

---

## 2. Reglas Específicas de Decisión

### 2.1 Indicadores Positivos de Alumno (Clase 1)
1. **Intención de demanda en primera persona:**
   * *"Busco profesor para..."*, *"Necesito alguien que me explique..."*, *"¿Alguien que prepare para el examen de...?"*.
2. **Contexto de evaluación inminente:**
   * Mención de materias específicas, programas universitarios (*CBC, UBA XXI, PAES, Selectividad*), o fechas de parciales y finales.
3. **Solicitudes por terceros directos:**
   * Padres o familiares buscando tutor para sus hijos de nivel secundario o primario (*"Busco profe para mi hijo de 3er año"*). Se consideran leads válidos de clase particular.

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

## 3. Protocolo de Auditoría Cruzada

* Los 175 registros extraídos fueron etiquetados independientemente por el evaluador humano y sometidos a una verificación cruzada frente a los avisos públicos originales.
* En casos de ambigüedad sintáctica (por ejemplo, textos muy breves como *"Clases de análisis"*), se revisó el endpoint de origen de la plataforma para verificar si el usuario publicó en la sección de *oferta* o en la de *demanda*.
* El dataset resultante sirve como patrón inmutable para medir la precisión, recall y F1 de los algoritmos sin sesgo de entrenamiento.
