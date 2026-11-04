# Informe de Auditoría de Seguridad — Historial de Commits Git

**Proyecto:** Pipeline de Prospección y CRM de Alumnos de Ciencias Exactas  
**Fecha:** 4 de noviembre de 2026  
**Auditor:** Auditoría Técnica y Forense de Seguridad  
**Estado:** Documentado / Mitigación en marcha  

---

## 1. Alcance y Objetivo de la Auditoría

De acuerdo con el principio de transparencia y las directrices de protección de datos personales (RGPD / Ley 25.326 de Protección de Datos Personales), se realizó una auditoría retrospectiva de los commits del repositorio `metecondrie/prospeccion-alumnos-ciencias` para identificar si en versiones anteriores se commitearon datos personales identificables (PII) de terceros o credenciales operativas.

---

## 2. Hallazgos en el Historial Git

| Rango de Commits | Archivos Afectados | Exposición Identificada | Severidad | Estado Actual |
|---|---|---|---|---|
| Commits `#1` a `#22` (v1.0 - v3.3) | `data/dataset_canonico_auditado.json`, `data/extracted_listings.json`, CSVs | Nombres reales de 24 estudiantes y enlaces directos a sus anuncios originales | Alta (Privacidad) | Anonimizado en archivos del árbol de trabajo (`main`), pero persistente en objetos blob del historial Git inmutable. |
| Commits `#1` a `#22` | `dashboard.html`, `docs/CONCLUSIONES.md` | Enlace a planilla privada de Google Sheets y dirección de correo de contacto | Media (Privacidad) | Enlaces y emails eliminados en `main`. Persisten en commits históricos previos a `a357e00`. |
| Commits `#23` en adelante | Todo el repositorio | Cero nombres residuales, rutas locales desacopladas, tests de seguridad PII automáticos activos | Nula (Conforme) | Verificado con suite `tests/test_pii_security.py`. |

---

## 3. Limitación Técnica de Git y Política de Inmutabilidad

Git almacena instantáneas criptográficamente firmadas por hashes SHA-1. La modificación o edición de un archivo en un commit posterior **no elimina el contenido de los commits anteriores**: cualquier usuario que clone el repositorio con `git clone` y ejecute `git log -p` puede inspeccionar el contenido histórico de los blobs.

Reescribir el historial existente mediante herramientas como `git filter-repo` o `git filter-branch`:
1. Altera las firmas SHA de todos los commits posteriores.
2. Rompe las referencias remotas para cualquier clon local existente.
3. Requiere un `push --force` con riesgo de pérdida de historial.

---

## 4. Estrategia de Mitigación y Buenas Prácticas Recomendadas

Para compatibilizar la preservación de la historia de desarrollo con la protección estricta de la privacidad de terceros en un portfolio público:

1. **Mantener el repositorio actual en modo PRIVADO:**  
   El repositorio `metecondrie/prospeccion-alumnos-ciencias` conserva el historial técnico legítimo de desarrollo para uso privado del autor.
2. **Publicar la versión pública desidentificada desde `_publico`:**  
   La herramienta [`scripts/anonymize_for_public.py`](../scripts/anonymize_for_public.py) genera la versión `../prospeccion-alumnos-ciencias_publico/`, la cual:
   * Contiene 0 nombres reales residuales.
   * Contiene URLs desidentificadas sintéticamente que impiden localizar a los anunciantes originales.
   * Contiene un historial Git limpio de un único commit de lanzamiento v4.0, garantizando que ningún commit previo exponga información sensible.
