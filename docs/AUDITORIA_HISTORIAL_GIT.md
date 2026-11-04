# Auditoría de Seguridad y Protección de Privacidad (Post-PII)

**Proyecto**: Pipeline de Prospección Educativa y CRM Local  
**Responsable**: Alejo Ongaro ([@metecondrie](https://github.com/metecondrie))  
**Fecha de Verificación**: 4 de noviembre de 2026  
**Estado**: Verificado empíricamente con suites de pruebas y comandos Git.

---

## 1. Mapeo Privado de Identidad Excluido de Git

* Los archivos con la correspondencia nombre real → seudónimo (`data/name_map.privado.json` y `data/name_map.local.json`) residen en almacenamiento local y están formalmente bloqueados por `.gitignore`, sin estar trackeados en el control de versiones.
* **Comandos de verificación:**
  ```bash
  git check-ignore data/name_map.privado.json data/name_map.local.json
  # Salida esperada: ambas rutas reportadas como ignoradas

  git ls-files data/name_map*
  # Salida esperada: vacío (cero archivos trackeados)
  ```

---

## 2. Exclusión Estricta de Registros Crudos de Extracción

* Los registros crudos de extracción web (`data/extracted_listings.json`, `*raw*.json`, `*_real.csv`, `data/leads_centinela_en_vivo.json`) están excluidos por `.gitignore` y permanecen fuera de los archivos trackeados en Git.
* **Comandos de verificación:**
  ```bash
  git check-ignore data/extracted_listings.json data/leads_centinela_en_vivo.json
  # Salida esperada: ambas rutas reportadas como ignoradas

  git ls-files data/extracted_listings.json data/leads_centinela_en_vivo.json
  # Salida esperada: vacío (cero archivos trackeados)
  ```

---

## 3. Desidentificación Determinista y URLs Sintéticas en Datos Públicos

* Todos los archivos de datos (`data/*.json`), entregables CSV (`alumnos_ciencias_exactas.csv`, `dashboard_crm.csv`) y visualización (`dashboard.html`) trackeados contienen exclusivamente URLs sintéticas (`https://anuncio-ejemplo-anonimizado.local/...`).
* Cero enlaces reales a los portales de clasificados (`tusclases`, `tablondeanuncios`, `cronoshare`, `reddit`) en artefactos de datos públicos.
* **Comandos de verificación:**
  ```bash
  grep -rE "tusclases|tablondeanuncios|cronoshare\.com|reddit\.com" data/ *.csv dashboard.html
  # Salida esperada: 0 coincidencias (exit code 1)

  grep -c "anuncio-ejemplo-anonimizado.local" data/dataset_canonico_auditado.json
  # Salida esperada: 41
  ```

---

## 4. Validación Criptográfica y Defensas en CI

* La suite de seguridad [`tests/test_pii_security.py`](../tests/test_pii_security.py) valida de forma automatizada:
  1. Ausencia de API keys reales en código y documentación (`test_no_api_keys_in_tracked_code_or_docs`).
  2. Ausencia de nombres reales y teléfonos en datasets públicos vía hashes SHA-256 (`test_dataset_ejemplo_contains_no_real_names_or_phones`).
  3. Ausencia de credenciales reales en `.env.example` (`test_env_example_has_no_live_secrets`).
  4. Ausencia de links reales a portales externos en archivos trackeados de datos y entregables (`test_no_real_portal_links_in_tracked_data_or_deliverables`).
  5. Exclusión formal de archivos crudos de extracción en el árbol Git (`test_raw_extractions_not_tracked`).
* La suite [`tests/test_correcciones.py`](../tests/test_correcciones.py) incluye el test `test_c11_urls_sinteticas_y_slugs_sin_pii` que garantiza 0 URLs reales y 0 tokens de slugs con hashes de nombres prohibidos.
* **Comandos de verificación:**
  ```bash
  python -m unittest tests/test_pii_security.py
  # Salida esperada: Ran 5 tests ... OK

  pytest tests/test_correcciones.py
  # Salida esperada: 16 passed
  ```

---

## 5. Anonimizador Integral Automatizado

* El script [`scripts/anonymize_for_public.py`](../scripts/anonymize_for_public.py) procesa de forma determinista y reproducible todos los datasets, CSVs y la interfaz web, certificando 0 nombres reales y 0 links reales residuales.
* **Comandos de verificación:**
  ```bash
  python scripts/anonymize_for_public.py
  # Salida esperada:
  # [OK] 0 nombres reales residuales
  # [OK] 0 links reales a anuncios residuales
  ```
