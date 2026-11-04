# Prospección de Alumnos y CRM Local (Ciencias Exactas)

[![CI](https://github.com/metecondrie/prospeccion-alumnos-ciencias/actions/workflows/ci.yml/badge.svg)](https://github.com/metecondrie/prospeccion-alumnos-ciencias/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Architecture](https://img.shields.io/badge/Architecture-Web%20Scraping%20%2B%20Telegram%20Stream-lightgrey.svg)](docs/DOCUMENTACION_TECNICA.md)

> **TL;DR (EN):** Lead-generation pipeline for a STEM tutor: multi-site scraper (175 raw listings), two-stage filter (regex → LLM semantic audit with multi-provider failover), real-time Telegram sentinel with push alerts, and a local CRM dashboard. 41 verified student leads, $0/mo operating cost, all public data anonymized. Full test harness included.

---

Herramienta de software libre orientada a docentes particulares de ciencias exactas (Matemática, Física, Química y Biología) para la captación ética, filtrado semántico asistido por IA y gestión de prospectos de nivel universitario y secundario superior.

Combina extracción web periódica en portales públicos clasificados, escucha en tiempo real de consultas públicas en comunidades estudiantiles de Telegram (vía cliente MTProto) y un panel interactivo local en HTML5/Tailwind (`dashboard.html`) para el seguimiento de postulaciones.

---

## 📋 Características Principales

* **Extracción Multicanal:** Scraping concurrente de demandas públicas de alumnos en TusClases (España, Argentina, México, Colombia, Chile, Perú), Tablón de Anuncios, Cronoshare y foros de Reddit (175 anuncios crudos procesados).
* **Escucha Pasiva en Telegram (`scripts/telegram_centinela.py`):** Monitorización de eventos en vivo en grupos universitarios públicos (UTN, FIUBA, UNLP, CBC) para detectar estudiantes solicitando apoyo académico, con alertas push opcionales al móvil.
* **Filtrado Semántico con IA:** Clasificación de intención para descartar ofertas de empleo docente, academias comerciales y anuncios no relacionados, utilizando Google Gemini 2.5 Flash Lite (con respaldo en Groq LPU) y validación estructurada en JSON.
* **Panel CRM Local Autónomo (`dashboard.html`):** Interfaz web local que opera 100% en el navegador (sin servidor backend), con persistencia en `localStorage`, notas por alumno, registro de contacto y filtrado dinámico.
* **Cobertura de Pruebas Automatizadas:** 64 pruebas exhaustivas con `pytest` y `unittest` que verifican integridad de esquemas CSV (RFC 4180), coherencia taxonómica y validación determinista del dataset.

---

## 📁 Estructura del Repositorio

El proyecto mantiene una estructura modular y limpia:

```text
├── main.py                     # Punto de entrada unificado CLI (Linux / macOS / Windows)
├── dashboard.html              # Interfaz web CRM autónoma (HTML5 / Tailwind CSS)
├── alumnos_ciencias_exactas.csv# Base de datos tabular canónica (8 columnas, RFC 4180)
├── dashboard_crm.csv           # Planilla extendida para importación en hojas de cálculo
├── requirements.txt            # Dependencias de producción
├── requirements-dev.txt        # Dependencias de testing (pytest)
├── LICENSE                     # Licencia MIT
│
├── .github/workflows/          # Integración Continua (CI)
│   └── ci.yml                  # Automatización de pruebas en GitHub Actions
│
├── bin/                        # Lanzadores de conveniencia para Windows (.bat)
│   ├── actualizar_alumnos.bat
│   ├── iniciar_centinela.bat
│   ├── probar_alerta.bat
│   └── unirme_a_grupos.bat
│
├── data/                       # Esquemas de datos y canales auditados
│   ├── dataset_canonico_auditado.json  # Base de datos de prospectos validados (41 leads)
│   ├── descartados_auditoria.json      # Registro de anuncios descartados
│   ├── extracted_listings.json         # Extracciones crudas (175 listings)
│   └── telegram_channels.json          # Directorio de comunidades auditadas
│
├── docs/                       # Documentación técnica y metodológica
│   ├── DOCUMENTACION_TECNICA.md
│   ├── DIRECTORIO_PLATAFORMAS.md
│   ├── CONCLUSIONES.md
│   ├── INFORME_BENCHMARKING.md
│   └── AUDITORIA_CAMBIOS.md    # Historial de cambios y auditorías de diseño
│
├── scripts/                    # Módulos de extracción, filtrado y escucha
│   ├── prospector.py           # CLI central, evaluación con IA y compilador
│   ├── telegram_centinela.py   # Listener MTProto en tiempo real
│   ├── auto_join_groups.py     # Gestor de suscripción con filtro de liveness
│   ├── run_extraction.py       # Orquestador concurrente de scrapers web
│   ├── extract_tusclases.py    # Extractor para red TusClases
│   ├── extract_tablon.py       # Extractor de Tablón de Anuncios
│   ├── extract_cronoshare_workana.py # Extractor Cronoshare y Reddit RSS
│   └── anonymize_for_public.py # Generador determinístico de muestras públicas
│
└── tests/                      # Suite de pruebas automatizadas (pytest / unittest)
    ├── test_e2e_deliverables.py
    ├── test_empirical_challenger.py
    ├── test_common_filter.py
    ├── test_milestone1_extractors.py
    └── check_dashboard.cjs     # Validación headless del frontend (Node.js)
```

---

## 🚀 Uso Rápido

### 1. Instalación de Dependencias

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 2. Configuración Opcional (`.env`)

Crea un archivo `.env` en la raíz a partir de `.env.example`:

```env
# Clave opcional de IA (Google AI Studio o Groq)
GEMINI_API_KEY=tu_clave_aqui
GROQ_API_KEY=tu_clave_aqui

# Credenciales de Telegram (solo para el Centinela en tiempo real)
TELEGRAM_API_ID=tu_api_id
TELEGRAM_API_HASH=tu_api_hash
TELEGRAM_BOT_TOKEN=tu_bot_token
TELEGRAM_CHAT_ID=tu_chat_id
```

### 3. Comandos CLI (`main.py`)

```bash
# Ejecutar pipeline completo (Scraping + Auditoría IA + Compilación)
python main.py run

# Ejecutar únicamente la extracción web
python main.py extract

# Iniciar el Centinela de Telegram en tiempo real
python main.py sentinel

# Ejecutar la suite completa de pruebas (64 tests)
python main.py test
```

---

## 🔒 Privacidad y Uso Responsable

* Los datos de este repositorio son una **muestra anonimizada** (seudónimos determinísticos generados con `scripts/anonymize_for_public.py`). Los registros operativos reales son privados y no se publican.
* La información proviene de **anuncios públicos** donde las personas solicitan explícitamente ser contactadas por profesores particulares, y se usa exclusivamente para ese fin.
* No se almacenan datos sensibles. Si un aviso corresponde a un menor de edad, el contacto se realiza siempre a través del medio que publicó el responsable del anuncio.
* El scraping respeta el acceso público de los sitios (sin eludir logins ni medidas de protección) y la escucha de Telegram opera solo sobre grupos a los que la cuenta se unió manualmente, con límites de tasa (*rate-limiting* y protección contra *FloodWait*).
* ¿Ves tu aviso en la muestra y preferís que no esté? Escribime y lo elimino.

---

## 🧪 Cómo correr las verificaciones

```bash
pip install -r requirements.txt        # Dependencias de producción
pip install -r requirements-dev.txt    # Dependencias de testing
python validate_dataset.py             # Integridad criptográfica del dataset
python -m unittest discover -s tests   # Suite completa Python (64 tests)
node tests/check_dashboard.cjs         # Suite del dashboard CRM (Node.js)
```

---

## 🧑‍💻 Sobre este proyecto y mi rol

Diseñé y dirigí este proyecto de punta a punta: definí el problema de negocio (asimetría 90/10 en portales de clasificados donde la mayoría son academias o docentes buscando alumnos), diseñé la arquitectura del pipeline y audité cada entrega con criterios de aceptación verificables. La implementación fue asistida por IA (Google Antigravity); la verificación de datos, las correcciones estructurales y las decisiones de calidad y privacidad fueron humanas a lo largo de múltiples iteraciones (ver [historial de auditoría y decisiones de diseño](docs/AUDITORIA_CAMBIOS.md)).

---

## 📄 Licencia

Distribuido bajo licencia [MIT](LICENSE).
