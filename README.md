# Prospección de Alumnos y CRM Local (Ciencias Exactas)

[![CI](https://github.com/metecondrie/prospeccion-alumnos-ciencias/actions/workflows/ci.yml/badge.svg)](https://github.com/metecondrie/prospeccion-alumnos-ciencias/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Architecture](https://img.shields.io/badge/Architecture-Web%20Scraping%20%2B%20Telegram%20Stream-lightgrey.svg)](docs/DOCUMENTACION_TECNICA.md)

> **TL;DR (EN):** Lead-generation pipeline for a STEM tutor: multi-site scraper (175 raw listings), two-stage filter (regex → LLM semantic audit with multi-provider failover), real-time Telegram sentinel with push alerts, and a local CRM dashboard. 41 verified student leads, $0/mo operating cost, all public data anonymized. Full 73-test harness included.

---

Herramienta de software libre orientada a docentes particulares de ciencias exactas (Matemática, Física, Química y Biología) para la captación ética, filtrado semántico asistido por IA y gestión de prospectos de nivel universitario y secundario superior.

Combina extracción web periódica en portales públicos clasificados, escucha en tiempo real de consultas públicas en comunidades estudiantiles de Telegram (vía cliente MTProto) y un panel interactivo local en HTML5/Tailwind (`dashboard.html`) para el seguimiento de postulaciones.

---

## 📋 Características Principales

* **Extracción Multicanal:** Scraping concurrente de demandas públicas de alumnos en TusClases (España, Argentina, México, Colombia, Chile, Perú), Tablón de Anuncios, Cronoshare y foros de Reddit (175 anuncios crudos procesados).
* **Escucha Pasiva en Telegram (`scripts/telegram_centinela.py`):** Monitorización de eventos en vivo en grupos universitarios públicos (UTN, FIUBA, UNLP, CBC) para detectar estudiantes solicitando apoyo académico, con alertas push opcionales al móvil.
* **Filtrado Semántico con IA y Fallback Local:** Clasificación de intención para discriminar estudiantes reales de academias comerciales o docentes, utilizando Google Gemini 2.5 Flash (con failover a Cloudflare, Groq, Mistral y motor heurístico determinista de respaldo sin conexión).
* **Panel CRM Local Autónomo (`dashboard.html`):** Interfaz web local que opera 100% en el navegador (sin servidor backend), con persistencia en `localStorage`, notas por alumno, registro de contacto y filtrado dinámico.
* **Cobertura de Pruebas Automatizadas:** 73 pruebas exhaustivas con `pytest` y `unittest` que verifican integridad de esquemas CSV (RFC 4180), prevención de CSV Injection, cálculo determinista de IDs, coherencia taxonómica y validación del dataset.

---

## 📊 Embudo de Conversión y Validación del Negocio

Resultados obtenidos durante la corrida piloto del pipeline:

| Etapa del Embudo | Volumen | Tasa de Conversión | Descripción Operativa |
|---|---|---|---|
| **1. Extracción Bruta** | 175 avisos | 100% | Rastrillaje multicanal en 8 plataformas y foros públicos. |
| **2. Calificación Semántica IA** | 41 prospectos | **23.4%** | Filtrado estricto con Gemini 2.5 Flash; 134 avisos de academias, docentes y ofertas laborales descartados. |
| **3. Contacto Inicial (Piloto)** | 18 contactados | **43.9%** | Postulaciones enviadas mediante formularios oficiales y mensajería directa autorizada. |
| **4. Respuestas Recibidas** | 7 alumnos | **38.8%** | Estudiantes que solicitaron disponibilidad horaria, temario y cotización de honorarios. |
| **5. Conversión a Clases Pagadas** | **3 alumnos activos** | **16.7%** | Alumnos que contrataron paquetes mensuales (2 de Álgebra Universitaria y 1 de Física Secundaria). |

**Unit Economics del Piloto:**
* **Costo de Adquisición de Clientes (CAC):** **$0 USD** (operación sostenida sobre capas gratuitas de Gemini Flash y scraping web directo).
* **Honorarios promedio:** $15.000 ARS/hora (~$12 USD).
* **Ingreso recurrente promedio:** $60.000 ARS/mes (~$48 USD/mes) por alumno activo (paquete estándar de 4 horas/mes).

---

## 🛡️ Resiliencia Técnica y Prevención de Baneos

*¿Cuánto tiempo dura este sistema en producción real sin romperse?*

1. **Scraping Web Resistente a Cambios de HTML:**
   - Los extractores combinan selectores CSS con expresiones regulares semánticas y análisis de texto plano. Si una plataforma altera su DOM o nombres de clases, el extractor no se quiebra: extrae el texto del contenedor principal y recurre a heurísticas léxicas.
   - Headers HTTP rotativos con User-Agents modernos y pausas defensivas entre solicitudes para evitar bloqueos por IP.
2. **Escucha en Telegram: Cero Riesgo de Baneo (Modo Pasivo):**
   - El Centinela (`telegram_centinela.py`) opera en modo **Event-Driven Listener** sobre grupos en los que la cuenta ya participa.
   - **No realiza envíos salientes automatizados ni spam masivo por mensaje privado.** No contacta alumnos por bot.
   - Las alertas se envían **únicamente al bot privado del docente**; el contacto con el estudiante es siempre 100% manual y humano (*Human-in-the-Loop*).
   - Control explícito de excepciones `telethon.errors.FloodWaitError` con retroceso exponencial (*exponential backoff*) y jitter.
3. **Alternativa Web sin MTProto:**
   - En caso de no disponer de credenciales MTProto de Telegram, el extractor `scripts/extract_telegram.py` permite monitorear canales públicos a través del espejo web oficial (`https://t.me/s/...`) mediante HTTP estándar.
4. **Respaldo Heurístico sin Conexión (Offline Fallback):**
   - Si no se configuran API keys de Gemini o se produce una caída en los servicios externos de IA, el pipeline activa de inmediato su motor determinista de reglas locales de PLN, garantizando continuidad operativa sin interrupciones.

---

## 📁 Estructura del Repositorio

El proyecto mantiene una estructura modular y limpia:

```text
├── main.py                     # Punto de entrada unificado CLI (Linux / macOS / Windows)
├── dashboard.html              # Interfaz web CRM autónoma (HTML5 / Tailwind CSS)
├── alumnos_ciencias_exactas.csv# Base de datos tabular canónica (8 columnas, RFC 4180)
├── dashboard_crm.csv           # Planilla extendida para importación en hojas de cálculo
├── requirements.txt            # Dependencias de producción
├── requirements-dev.txt        # Dependencias de testing y calidad de código
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
│   ├── dataset_canonico_auditado.json # 41 prospectos calificados (anonimizados)
│   ├── descartados_auditoria.json     # Registro forense de descartes
│   ├── extracted_listings.json        # 175 avisos crudos extraídos
│   └── telegram_channels.json         # Directorio de grupos estudiantiles
│
├── docs/                       # Documentación técnica y bitácora
│   ├── AUDITORIA_CAMBIOS.md    # Registro de auditorías técnicas y decisiones de diseño
│   ├── CONCLUSIONES.md         # Análisis de negocio y resultados pedagógicos
│   └── DOCUMENTACION_TECNICA.md# Especificación técnica, diagramas y contratos
│
├── scripts/                    # Módulos del pipeline de prospección
│   ├── anonymize_for_public.py # Generador de datos públicos con seudónimos deterministas
│   ├── common_filter.py        # Filtros léxicos y normalización taxonómica
│   ├── extract_cronoshare_workana.py
│   ├── extract_tablon.py
│   ├── extract_telegram.py
│   ├── extract_tusclases.py
│   ├── prospector.py           # CLI multiproveedor (Gemini Flash, Groq, Mistral, Fallback)
│   ├── run_extraction.py
│   └── telegram_centinela.py   # Daemon en tiempo real (MTProto Telethon)
│
└── tests/                      # Suite de pruebas automatizadas (73 tests)
    ├── check_dashboard.cjs     # Suite DOM para dashboard CRM (Node.js)
    ├── test_common_filter.py
    ├── test_e2e_deliverables.py
    ├── test_empirical_challenger.py
    ├── test_milestone1_extractors.py
    ├── test_prospector.py      # Pruebas unitarias de parsing, sanitización CSV y failover
    └── verify_survey_deliverables.py
```

---

## 🚀 Puesta en Marcha Rápida

### 1. Instalación de Dependencias

```bash
git clone https://github.com/metecondrie/prospeccion-alumnos-ciencias.git
cd prospeccion-alumnos-ciencias
python -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 2. Configuración de Entorno (`.env`)

Crea un archivo `.env` en la raíz (puedes tomar como base las variables opcionales):

```ini
# Proveedor principal de IA (opcional: si no está presente se activa el motor heurístico local)
GEMINI_API_KEY=tu_clave_de_google_ai_studio

# Proveedores de respaldo opcionales
CLOUDFLARE_ACCOUNT_ID=tu_account_id
CLOUDFLARE_API_TOKEN=tu_api_token
GROQ_API_KEY=tu_clave_de_groq
MISTRAL_API_KEY=tu_clave_de_mistral

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

# Ejecutar la suite completa de pruebas (73 tests)
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
python -m unittest discover -s tests   # Suite completa Python (73 tests)
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
