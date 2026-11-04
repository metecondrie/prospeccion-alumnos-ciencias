# Prospección de Alumnos y CRM Local (Ciencias Exactas)

[![CI](https://github.com/metecondrie/prospeccion-alumnos-ciencias/actions/workflows/ci.yml/badge.svg)](https://github.com/metecondrie/prospeccion-alumnos-ciencias/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Architecture](https://img.shields.io/badge/Architecture-Web%20Scraping%20%2B%20Telegram%20Stream-lightgrey.svg)](docs/DOCUMENTACION_TECNICA.md)

> **TL;DR (EN):** Lead-generation pipeline for a STEM tutor: multi-site scraper (175 raw listings), two-stage filter (regex → LLM semantic audit with multi-provider failover), real-time Telegram sentinel with push alerts, and a local CRM dashboard. 41 verified student leads, $0/mo operating cost, all public data anonymized. Full 75-test harness included.

---

Herramienta de software libre orientada a docentes particulares de ciencias exactas (Matemática, Física, Química y Biología) para la captación ética, filtrado semántico asistido por IA y gestión de prospectos de nivel universitario y secundario superior.

Combina extracción web periódica en portales públicos clasificados, escucha en tiempo real de consultas públicas en comunidades estudiantiles de Telegram (vía cliente MTProto) y un panel interactivo local en HTML5/Tailwind (`dashboard.html`) para el seguimiento de postulaciones.

---

## 📋 Características Principales

* **Extracción Multicanal:** Scraping concurrente de demandas públicas de alumnos en TusClases (España, Argentina, México, Colombia, Chile, Perú), Tablón de Anuncios, Cronoshare y foros de Reddit (175 anuncios crudos procesados).
* **Escucha Pasiva en Telegram (`scripts/telegram_centinela.py`):** Monitorización de eventos en vivo en grupos universitarios públicos (UTN, FIUBA, UNLP, CBC) para detectar estudiantes solicitando apoyo académico, con alertas push opcionales al móvil.
* **Filtrado Semántico con IA y Fallback Local:** Clasificación de intención para discriminar estudiantes reales de academias comerciales o docentes, utilizando Google Gemini 2.5 Flash (con failover a Cloudflare Workers AI, Groq, Mistral y motor heurístico determinista de respaldo sin conexión).
* **Panel CRM Local Autónomo (`dashboard.html`):** Interfaz web local que opera 100% en el navegador (sin servidor backend), con persistencia en `localStorage`, notas por alumno, registro de contacto y filtrado dinámico.
* **Cobertura de Pruebas Automatizadas:** 75 pruebas exhaustivas con `pytest` y `unittest` que verifican integridad de esquemas CSV (RFC 4180), prevención de CSV Injection, cálculo determinista de IDs, coherencia taxonómica, métricas de evaluación y validación del dataset.

---

## 📊 Métricas Cuantitativas de Machine Learning (Data Science Benchmark)

Evaluación formal sobre el universo ground-truth de 175 anuncios etiquetados manualmente (ver reporte completo en [`docs/EVALUACION_FILTRO_DATOS.md`](docs/EVALUACION_FILTRO_DATOS.md)):

| Métrica | Baseline Heurístico (Regex) | Producción: Gemini 2.5 Flash | Delta de Rendimiento |
|---|---|---|---|
| **Precisión (Precision)** | 22.8% | **95.3%** | **+72.5 pp** |
| **Sensibilidad (Recall)** | 40.0% | **100.0%** | **+60.0 pp** |
| **Especificidad** | 20.0% | **98.5%** | **+78.5 pp** |
| **F1-Score** | 29.0% | **97.6%** | **+68.6 pp** |
| **Reducción de Ruido** | 76.6% inicial | **1.1% residual** | **-75.5 pp de spam en CRM** |

*¿Por qué falla el baseline de Regex?* Porque los docentes utilizan el mismo léxico que los alumnos (*"clases particulares de física"*, *"apoyo escolar"*). La inferencia semántica de Gemini es estrictamente necesaria para discriminar el rol gramatical de la transacción (quién ofrece vs quién solicita).

---

## 📈 Embudo de Conversión y Telemetría del Piloto Real

Resultados cuantitativos del seguimiento en el CRM local (telemetría documentada en [`data/feedback_piloto_conversion.json`](data/feedback_piloto_conversion.json)):

| Etapa del Embudo | Volumen | Conversión | Detalle Operativo |
|---|---|---|---|
| **1. Extracción Bruta** | 175 avisos | 100% | Rastrillaje multicanal en 8 plataformas. |
| **2. Calificación Semántica IA** | 41 prospectos | **23.4%** | Filtrado con Gemini 2.5 Flash; 134 avisos irrelevantes descartados. |
| **3. Contacto Inicial (Piloto)** | 18 contactados | **43.9%** | Postulaciones mediante canales directos gratuitos y formularios. |
| **4. Respuestas Recibidas** | 7 alumnos | **38.8%** | Consultas por disponibilidad horaria, temario y cotización. |
| **5. Clases Pagadas Cerradas** | **3 alumnos activos** | **16.7%** | Alumnos que contrataron paquetes mensuales (2 de Álgebra Universitaria y 1 de Física). |

* **Costo de Adquisición (CAC):** **$0 USD** (operación sobre capas gratuitas de Gemini Flash y web scraping directo).
* **Ticket promedio:** $15.000 ARS/hora (~$12 USD).
* **LTV estimado (cuatrimestre):** $240.000 ARS (~$192 USD) por alumno activo.

---

## 🛡️ Marco Ético, Legal y Prevención de Baneos

Para una explicación exhaustiva de cumplimiento normativo (RGPD / Ley 25.326) y arquitectura defensiva, consulta [`docs/MARCO_ETICO_Y_LEGAL.md`](docs/MARCO_ETICO_Y_LEGAL.md):

1. **Scraping Ético y de Acceso Público:**
   - La recolección se realiza únicamente sobre anuncios públicos donde el usuario solicita explícitamente ser contactado para clases.
   - No se eluden barreras de acceso, paywalls ni CAPTCHAs.
2. **Escucha en Telegram: Cero Riesgo de Baneo (Modo Pasivo):**
   - El Centinela (`telegram_centinela.py`) opera en modo **Event-Driven Listener** sobre grupos en los que la cuenta ya participa.
   - **No realiza envíos salientes automatizados ni spam masivo por mensaje privado.**
   - Las alertas se envían **únicamente al bot privado del docente**; el contacto con el estudiante es siempre manual (*Human-in-the-Loop*).
   - Manejo de `FloodWaitError` de Telethon con enfriamiento exponencial y jitter.
3. **Anonimización Estricta en Portfolio Público:**
   - Ningún dato personal real (nombres, teléfonos, @usuarios de Telegram) se encuentra en este repositorio. Todos los nombres fueron reemplazados por seudónimos sintéticos deterministas mediante `scripts/anonymize_for_public.py` (0 colisiones verificadas).

---

## 📁 Estructura del Repositorio

El proyecto mantiene una estructura modular multiplataforma:

```text
├── main.py                     # Punto de entrada unificado CLI (Linux / macOS / Windows)
├── dashboard.html              # Interfaz web CRM autónoma (HTML5 / Tailwind CSS)
├── alumnos_ciencias_exactas.csv# Base de datos tabular canónica (8 columnas, RFC 4180)
├── dashboard_crm.csv           # Planilla extendida para importación en hojas de cálculo
├── requirements.txt            # Dependencias de producción
├── requirements-dev.txt        # Dependencias de testing y calidad de código
├── .env.example                # Plantilla de variables de entorno documentadas
├── LICENSE                     # Licencia MIT
│
├── .github/workflows/          # Integración Continua (CI)
│   └── ci.yml                  # Automatización de pruebas en GitHub Actions
│
├── bin/                        # Lanzadores de conveniencia multiplataforma
│   ├── actualizar_alumnos.bat  # Windows Batch launcher
│   ├── actualizar_alumnos.sh   # POSIX Bash launcher (Linux / macOS)
│   ├── iniciar_centinela.bat
│   ├── iniciar_centinela.sh
│   ├── probar_alerta.bat
│   ├── probar_alerta.sh
│   ├── unirme_a_grupos.bat
│   └── unirme_a_grupos.sh
│
├── data/                       # Esquemas de datos y telemetría de conversión
│   ├── dataset_canonico_auditado.json # 41 prospectos calificados (anonimizados)
│   ├── descartados_auditoria.json     # Registro forense de descartes
│   ├── extracted_listings.json        # 175 avisos crudos extraídos
│   ├── feedback_piloto_conversion.json# Telemetría de conversión y objeciones
│   └── telegram_channels.json         # Directorio de grupos estudiantiles
│
├── docs/                       # Documentación técnica y auditorías
│   ├── AUDITORIA_CAMBIOS.md    # Registro de auditorías técnicas y decisiones de diseño
│   ├── CONCLUSIONES.md         # Análisis de negocio y resultados pedagógicos
│   ├── DOCUMENTACION_TECNICA.md# Especificación técnica, diagramas y contratos
│   ├── EVALUACION_FILTRO_DATOS.md # Reporte cuantitativo de Machine Learning
│   └── MARCO_ETICO_Y_LEGAL.md  # Marco regulatorio (RGPD / Ley 25.326)
│
├── scripts/                    # Módulos del pipeline de prospección
│   ├── anonymize_for_public.py # Generador de datos públicos con seudónimos deterministas
│   ├── common_filter.py        # Filtros léxicos y normalización taxonómica
│   ├── evaluate_filter.py      # Benchmark cuantitativo de Machine Learning
│   ├── extract_cronoshare_workana.py
│   ├── extract_tablon.py
│   ├── extract_telegram.py
│   ├── extract_tusclases.py
│   ├── prospector.py           # CLI multiproveedor (Gemini Flash, Groq, Mistral, Fallback)
│   ├── run_extraction.py
│   └── telegram_centinela.py   # Daemon en tiempo real (MTProto Telethon)
│
└── tests/                      # Suite de pruebas automatizadas (75 tests)
    ├── check_dashboard.cjs     # Suite DOM para dashboard CRM (Node.js)
    ├── test_common_filter.py
    ├── test_e2e_deliverables.py
    ├── test_empirical_challenger.py
    ├── test_milestone1_extractors.py
    ├── test_prospector.py      # Pruebas unitarias de parsing, sanitización CSV, benchmark y failover
    └── verify_survey_deliverables.py
```

---

## 🚀 Puesta en Marcha Rápida (Multiplataforma)

### 1. Instalación de Dependencias

```bash
git clone https://github.com/metecondrie/prospeccion-alumnos-ciencias.git
cd prospeccion-alumnos-ciencias
python -m venv .venv

# En Linux / macOS:
source .venv/bin/activate

# En Windows:
.venv\Scripts\activate

pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 2. Configuración de Entorno (`.env`)

Copia la plantilla de ejemplo y configura tus credenciales opcionales:

```bash
# En Linux / macOS:
cp .env.example .env

# En Windows:
copy .env.example .env
```

*(Si no configuras claves de IA, el sistema activa automáticamente el motor heurístico determinista local sin costo).*

### 3. Comandos de Ejecución Multiplataforma

```bash
# Ejecutar pipeline completo (Scraping + Auditoría IA + Compilación)
python main.py run
# O bien mediante módulo directo:
python -m scripts.prospector run

# Ejecutar benchmark cuantitativo de Machine Learning
python scripts/evaluate_filter.py

# Iniciar el Centinela de Telegram en tiempo real
python -m scripts.telegram_centinela

# Ejecutar la suite completa de pruebas (75 tests)
python main.py test
```

*Lanzadores de conveniencia:*
* **En Linux / macOS:** `bash bin/actualizar_alumnos.sh`
* **En Windows:** Doble clic en `bin\actualizar_alumnos.bat`

---

## 🧪 Cómo correr las verificaciones

```bash
pip install -r requirements.txt        # Dependencias de producción
pip install -r requirements-dev.txt    # Dependencias de testing
python validate_dataset.py             # Integridad criptográfica del dataset
python -m unittest discover -s tests   # Suite completa Python (75 tests)
node tests/check_dashboard.cjs         # Suite del dashboard CRM (Node.js)
```

---

## 🧑‍💻 Autoría y Rol

**Autor:** **Alejo Ongaro** ([@metecondrie](https://github.com/metecondrie))
* **Rol:** Diseñador del sistema, Arquitecto de Software y Docente de Ciencias Exactas.
* **Perfil GitHub:** [github.com/metecondrie](https://github.com/metecondrie)
* **Repositorio:** [github.com/metecondrie/prospeccion-alumnos-ciencias](https://github.com/metecondrie/prospeccion-alumnos-ciencias)

Diseñé y dirigí este proyecto de punta a punta: definí el problema de negocio (asimetría 90/10 en portales de clasificados donde la gran mayoría de publicaciones corresponden a academias o profesores ofreciendo clases y no a estudiantes contratando), diseñé la arquitectura del pipeline multicanal y audité cada entrega con criterios de aceptación verificables. La implementación de código fue asistida por IA (Google Antigravity); la dirección técnica, verificación de datos, correcciones estructurales, suite de pruebas automatizadas y decisiones de privacidad y producción fueron conducidas por mí a lo largo de sucesivas iteraciones (ver [historial de auditoría y decisiones de diseño](docs/AUDITORIA_CAMBIOS.md)).

---

## 📄 Licencia

Distribuido bajo licencia [MIT](LICENSE).
