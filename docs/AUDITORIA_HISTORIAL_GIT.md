# Auditoría de Seguridad del Historial Git y Protección de Privacidad (Post-PII)

**Proyecto**: Pipeline de Prospección Educativa y CRM Local  
**Responsable**: Alejo Ongaro ([@metecondrie](https://github.com/metecondrie))  
**Fecha de Auditoría**: 4 de noviembre de 2026  
**Estado**: Estrategia de Gobernanza Aprobada / Migración a Repositorio Limpio PENDIENTE

---

## 1. Contexto y Objetivos de Seguridad

Durante las fases iniciales de desarrollo y prototipado rápido del pipeline, se procesaron anuncios públicos capturados en plataformas de clasificados educativos. Con el objetivo de garantizar una publicación de portfolio 100% ética y con estricto apego a normativas de protección de datos personales (RGPD en Europa y Ley 25.326 en Argentina), se implementó una auditoría exhaustiva para eliminar cualquier riesgo de exposición residual.

---

## 2. Medidas Técnicas de Privacidad Implementadas

### A. Mapeo Privado y Gitignoreado de Nombres Reales
* La correspondencia biunívoca entre nombres reales de estudiantes extraídos de los portales y sus seudónimos deterministas (`NAME_MAP`) reside exclusivamente en los archivos locales:
  - `data/name_map.local.json`
  - `data/name_map.privado.json`
* Ambos archivos están estrictamente bloqueados por el `.gitignore` del proyecto y **nunca han sido ni serán incluidos en commits públicos**.
* Las pruebas automatizadas del repositorio (`tests/test_pii_security.py`) validan la ausencia de nombres reales mediante hashes criptográficos unidireccionales SHA-256, sin almacenar nombres en texto plano dentro del código de prueba.

### B. Desidentificación Determinista y URLs Sintéticas
* Todas las direcciones URL hacia portales de clasificados (`tusclasesparticulares`, `tablondeanuncios`, `cronoshare`) fueron sustituidas mediante un algoritmo determinista (`scripts/anonymize_for_public.py`).
* Los enlaces resultantes apuntan a dominios sintéticos (`https://anuncio-ejemplo-anonimizado.local/...`), previniendo la correlación inversa o reidentificación de los autores de los avisos.

### C. Exclusión Estricta de Registros Crudos
* Los archivos crudos sin procesar (`*raw*.json`, `*_real.csv`) están formalmente excluidos por `.gitignore`.
* Los artefactos entregables públicos (`alumnos_ciencias_exactas.csv`, `dashboard_crm.csv`, `data/crm_export.json`) contienen exclusivamente datos sintéticos anonimizados.

---

## 3. Mitigación de Historial Git: Estrategia de Repositorio Público Limpio

Dado que en un sistema de control de versiones distribuido como Git los commits históricos preservan estados anteriores del código, la mitigación definitiva para prevenir la persistencia de trazas tempranas de desarrollo es:

1. **Privatización del Repositorio de Desarrollo:**  
   El repositorio actual de desarrollo (`metecondrie/prospeccion-alumnos-ciencias`) se mantendrá con visibilidad **privada** como entorno interno de trabajo.
2. **Generación de Repositorio Público con Commit Único:**  
   Se generará un repositorio público completamente nuevo a partir de la copia limpia anonimizada por `scripts/anonymize_for_public.py`, inicializado con un **único commit inicial** sin historial retrospectivo (`git init`, commit `chore: initial public release`).
3. **Estado de la Acción:**  
   Esta mitigación requiere intervención de credenciales de GitHub por parte del propietario del proyecto (**Acción manual del owner, PENDIENTE**).

---

## 4. Verificación Automatizada en CI

El pipeline de integración continua ejecuta de forma obligatoria la suite `tests/test_pii_security.py` en cada pull request y push, asegurando que ningún commit introduzca credenciales, nombres reales o enlaces a anuncios reales en los archivos públicos del proyecto.
