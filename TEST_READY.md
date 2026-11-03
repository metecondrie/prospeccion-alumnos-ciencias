# TEST_READY: E2E Test Suite & Deliverables Verification Harness

**Project**: Base de Datos de Alumnos en Ciencias Exactas y Directorio de Plataformas  
**Status**: TEST SUITE READY & VERIFIED  
**Author**: `e2e_test_writer`  
**Date**: 2026-11-02  
**Target Deliverables**:
1. `alumnos_ciencias_exactas.csv` (CSV Database of Student Listings)
2. `directorio_plataformas.md` (Directory Catalog of Student Tutor Platforms)

---

## 1. Test Runner Commands

The testing harness provides two complementary execution modes: a standalone auditor script with rich diagnostics and a 4-tier `unittest`/`pytest` test suite.

### A. Standalone Deliverables Audit Tool
Execute the dedicated audit script to perform comprehensive forensic verification of deliverables:

```powershell
# Standard audit execution
python tests/verify_survey_deliverables.py

# Audit execution with live HTTP URL sampling and verification
python tests/verify_survey_deliverables.py --sample-urls

# Verbose audit diagnostics
python tests/verify_survey_deliverables.py --verbose
```

**Exit Codes**:
- `0`: All deliverables pass 100% of schema, encoding, authenticity, and freshness specifications.
- `1`: Deliverable validation failed (detailed error list and row-level diagnostics output to stderr/stdout).

### B. Standard Unittest / Pytest Suite
Execute the full automated test suite using Python's standard test runner or `pytest`:

```powershell
# Standard unittest execution
python -m unittest tests/test_e2e_deliverables.py

# Discover all test suites in tests/
python -m unittest discover -s tests -p "test_*.py"

# Pytest execution (if pytest is installed)
pytest tests/test_e2e_deliverables.py -v
```

---

## 2. Test Coverage Summary Table

| Test Tier | Focus & Scope | Automated Test Cases | Status |
|:---|:---|:---|:---:|
| **Tier 1: Feature Coverage** | Fundamental deliverable presence, canonical schema, complete records, platform catalog structure. | `test_01_csv_file_existence`<br>`test_02_directory_file_existence`<br>`test_03_canonical_8_headers_exact_match`<br>`test_04_non_empty_records`<br>`test_05_directory_required_sections`<br>`test_06_directory_platform_coverage` | READY |
| **Tier 2: Boundary & Corner Cases** | UTF-8 BOM signature (`0xEF, 0xBB, 0xBF`), RFC 4180 CRLF (`\r\n`), quote escaping (`""`), Spanish accents preservation (`á, é, í, ó, ú, ñ`), ISO 8601 date parsing, calendar validity, no future dates, freshness window (≤ 90 days). | `test_01_utf8_bom_signature`<br>`test_02_rfc4180_crlf_line_terminators`<br>`test_03_character_encoding_spanish_accents`<br>`test_04_date_format_and_calendar_validity`<br>`test_05_date_no_future_dates`<br>`test_06_date_freshness_window_90_days` | READY |
| **Tier 3: Cross-Feature Combinations** | Canonical exact sciences taxonomy (`Física`, `Química`, `Biología`, `Matemáticas`), educational levels (`Secundario`, `Universitario`), Subject x Level matrix coverage, Spain + LATAM geographic diversity. | `test_01_subject_taxonomy_compliance`<br>`test_02_educational_level_compliance`<br>`test_03_subject_x_level_matrix_coverage`<br>`test_04_geographic_representation_spain_and_latam`<br>`test_05_location_formatting_consistency` | READY |
| **Tier 4: Real-World Workload Testing** | 100% student authenticity guarantee via 25+ negative teacher regex blacklist patterns, positive student intent signals, valid URL schemes (`http`/`https`), live HTTP 200 sampling, contact actionability (≥ 8 chars). | `test_01_student_authenticity_teacher_blacklist`<br>`test_02_student_intent_positive_signals`<br>`test_03_url_format_and_canonical_schemes`<br>`test_04_live_url_http_sampling`<br>`test_05_contact_method_actionability` | READY |
| **Unit & Pipeline Integration** | Self-verification of teacher/student intent classifiers, date freshness logic, and audit runner validation using compliant and mutated synthetic fixtures. | `test_teacher_blacklist_catches_teacher_ads`<br>`test_student_whitelist_accepts_student_requests`<br>`test_teacher_blacklist_does_not_false_positive`<br>`test_subject_taxonomy_set`<br>`test_date_freshness_logic`<br>`test_pipeline_passes_with_compliant_fixture`<br>`test_pipeline_fails_when_csv_missing_bom`<br>`test_pipeline_fails_when_teacher_ad_injected`<br>`test_pipeline_fails_when_date_is_future`<br>`test_pipeline_fails_when_date_exceeds_freshness_window` | **PASSED (10/10)** |

---

## 3. Requirement Traceability Matrix

| Requirement ID | Specification | Acceptance Criteria | Automated Test Mapping |
|:---|:---|:---|:---|
| **R1** | Identificación exhaustiva de plataformas de búsqueda de profesores de habla hispana en ciencias exactas. | Plataformas de clasificados, portales y tablones cubiertos para España y LATAM. | `test_05_directory_required_sections`<br>`test_06_directory_platform_coverage`<br>`test_04_geographic_representation_spain_and_latam` |
| **R2** | Base de datos CSV (`alumnos_ciencias_exactas.csv`) estructurada para apertura directa en Excel / Google Sheets. | Archivo en raíz del proyecto, 8 columnas canónicas, UTF-8 con BOM (`utf-8-sig`), RFC 4180 CRLF y quote escaping. | `test_01_csv_file_existence`<br>`test_03_canonical_8_headers_exact_match`<br>`test_01_utf8_bom_signature`<br>`test_02_rfc4180_crlf_line_terminators`<br>`test_03_character_encoding_spanish_accents` |
| **R2 (Taxonomía)** | Materias restringidas a ciencias exactas; niveles educativos secundario y universitario. | `materia` en {`Física`, `Química`, `Biología`, `Matemáticas`}; `nivel educativo` en {`Secundario`, `Universitario`}. | `test_01_subject_taxonomy_compliance`<br>`test_02_educational_level_compliance`<br>`test_03_subject_x_level_matrix_coverage` |
| **R2 (Autenticidad)** | Exclusión total de ofertas de profesores; 100% solicitudes de alumnos. | 0 coincidencias contra patrones docentes ("doy clases", "ofrezco clases", "imparto clases", "primera clase gratis", "tarifas"). | `test_01_student_authenticity_teacher_blacklist`<br>`test_02_student_intent_positive_signals` |
| **R2 (Temporalidad)** | Anuncios activos y recientes sin fechas futuras. | Fechas ISO 8601 `YYYY-MM-DD`, fecha ≤ hoy, antigüedad ≤ 90 días. | `test_04_date_format_and_calendar_validity`<br>`test_05_date_no_future_dates`<br>`test_06_date_freshness_window_90_days` |
| **R2 (Contacto)** | Vías de contacto directas para comunicación urgente. | URL funcional, campo `método de contacto directo` ≥ 8 caracteres accionable (WhatsApp, teléfono, mensajería). | `test_03_url_format_and_canonical_schemes`<br>`test_04_live_url_http_sampling`<br>`test_05_contact_method_actionability` |
| **R3** | Directorio de plataformas (`directorio_plataformas.md`) con tabla comparativa, URLs directas y notas de contacto. | Documento en raíz con tabla comparativa Markdown, URLs a secciones de demandas, y protocolo de contacto rápido. | `test_02_directory_file_existence`<br>`test_05_directory_required_sections`<br>`test_06_directory_platform_coverage` |

---

## 4. Current Execution Status

- **Harness & Framework Implementation**: 100% COMPLETE.
- **Unit & Heuristics Pipeline Integration**: **10 / 10 Tests Passing** (`TestClassifierHeuristicsUnit`, `TestAuditPipelineIntegrationUnit`).
- **Artifacts Gate**: Tests for deliverable files will execute as soon as Milestone M2 compiles `alumnos_ciencias_exactas.csv` and `directorio_plataformas.md`.
- **Zero Facade Testing Guarantee**: The test suite actively executes verification logic, tests both positive and negative constraints, and enforces strict boundary checks.
