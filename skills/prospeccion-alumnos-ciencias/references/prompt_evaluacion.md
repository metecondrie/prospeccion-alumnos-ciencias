# Criterios del Prompt de Clasificación Semántica y Esquema JSON

## Modelo Utilizado
* **Primario**: `gemini-3.6-flash`
* **Secundario / Fallback**: `gemini-3.8-flash`
* **Formato de Salida**: `responseMimeType: "application/json"`

---

## 1. Criterios de Exclusión Estrictos (`is_student: false`)

1. **Academias e Institutos Privados**:
   - Centros de estudios, colegios o academias buscando contratar docentes.
   - Textos con "se busca docente", "necesitamos profesor de matemáticas", "incorporamos tutor para sede en Valladolid/Madrid".
2. **Ofertas Laborales / Empleo Docente**:
   - Anuncios clasificados en categorías de demanda laboral para profesores particulares.
3. **Ofertas de Clases de Otros Profesores**:
   - Docentes particulares promocionando sus clases ("Doy clases particulares", "Tengo amplia experiencia").
4. **Páginas Índice y Menús de Categorías Web**:
   - URLs de navegación general como `/estudiantes/ingles/`, `/estudiantes/matematicas/`.

---

## 2. Criterios de Inclusión Estrictos (`is_student: true`)

1. **Estudiantes Secundarios o Universitarios**:
   - Textos donde una persona expresa su necesidad de aprendizaje: "necesito clases", "busco profesor de biofísica para rendir final", "preparar examen de análisis", "apoyo escolar para 2º bachillerato".
2. **Padres o Madres de Alumnos**:
   - Solicitudes familiares buscando apoyo académico para sus hijos.

---

## 3. Esquema JSON de Respuesta

```json
[
  {
    "id": "tc_ar_2466634",
    "is_student": true,
    "decision_ia": "Aprobado",
    "justificacion_ia": "Estudiante universitario real buscando profesor de matemáticas para clases online particulares."
  }
]
```
