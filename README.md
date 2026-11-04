# Prospección de Alumnos y CRM Local (Ciencias Exactas)

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Tests Passing](https://img.shields.io/badge/Tests-64%20passed%20(100%25)-success.svg)](tests/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Architecture](https://img.shields.io/badge/Architecture-Web%20Scraping%20%2B%20Telegram%20Stream-lightgrey.svg)](docs/DOCUMENTACION_TECNICA.md)

Herramienta de software libre orientada a docentes particulares de ciencias exactas (Matemática, Física, Química y Biología) para la captación ética, filtrado semántico asistido por IA y gestión de prospectos de nivel universitario y secundario superior.

Combina extracción web periódica en portales públicos clasificados, escucha en tiempo real de consultas públicas en comunidades estudiantiles de Telegram (vía cliente MTProto) y un panel interactivo local en HTML5/Tailwind (`dashboard.html`) para el seguimiento de postulaciones.

---

## 📋 Características Principales

* **Extracción Multicanal:** Scraping concurrente de demandas públicas de alumnos en TusClases (España, Argentina, México, Colombia, Chile, Perú), Tablón de Anuncios, Cronoshare y foros de Reddit.
* **Escucha Pasiva en Telegram (`scripts/telegram_centinela.py`):** Monitorización de eventos en vivo en grupos universitarios públicos (UTN, FIUBA, UNLP, CBC) para detectar estudiantes solicitando apoyo académico, con alertas push opcionales al móvil.
* **Filtrado Semántico con IA:** Clasificación de intención para descartar ofertas de empleo docente, academias comerciales y anuncios no relacionados, utilizando modelos LLM (Google Gemini / Groq) con validación estructurada en JSON.
* **Panel CRM Local Autónomo (`dashboard.html`):** Interfaz web local que opera 100% en el navegador (sin servidor backend), con persistencia en `localStorage`, notas por alumno, registro de contacto y filtrado dinámico.
* **Cobertura de Pruebas Automatizadas:** 64 pruebas con `pytest` que verifican integridad de esquemas CSV (RFC 4180), coherencia taxonómica y validación determinista del dataset.

---

## 📁 Estructura del Repositorio

El proyecto mantiene una estructura modular y limpia:

```text
├── main.py                     # Punto de entrada unificado CLI (Linux / macOS / Windows)
├── dashboard.html              # Interfaz web CRM autónoma (HTML5 / Tailwind CSS)
├── alumnos_ciencias_exactas.csv# Base de datos tabular canónica (8 columnas, RFC 4180)
├── dashboard_crm.csv           # Planilla extendida para importación en hojas de cálculo
├── requirements.txt            # Dependencias de Python
├── LICENSE                     # Licencia MIT
│
├── bin/                        # Lanzadores de conveniencia para Windows (.bat)
│   ├── actualizar_alumnos.bat
│   ├── iniciar_centinela.bat
│   ├── probar_alerta.bat
│   └── unirme_a_grupos.bat
│
├── data/                       # Esquemas de datos y canales auditados
│   ├── dataset_canonico_auditado.json  # Base de datos de prospectos validados
│   ├── descartados_auditoria.json      # Registro de anuncios descartados
│   ├── extracted_listings.json         # Extracciones crudas
│   └── telegram_channels.json          # Comunidades y canales objetivo
│
├── docs/                       # Documentación técnica y metodológica
│   ├── DOCUMENTACION_TECNICA.md
│   ├── DIRECTORIO_PLATAFORMAS.md
│   ├── CONCLUSIONES.md
│   └── INFORME_BENCHMARKING.md
│
├── scripts/                    # Módulos de extracción, filtrado y escucha
│   ├── prospector.py           # CLI central, evaluación con IA y compilador
│   ├── telegram_centinela.py   # Listener MTProto en tiempo real
│   ├── auto_join_groups.py     # Gestor de suscripción con filtro de actividad
│   ├── run_extraction.py       # Orquestador concurrente de scrapers web
│   ├── extract_tusclases.py    # Extractor para red TusClases
│   ├── extract_tablon.py       # Extractor de Tablón de Anuncios
│   └── extract_cronoshare_workana.py # Extractor Cronoshare y Reddit RSS
│
└── tests/                      # Suite de pruebas automatizadas (pytest)
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
```

### 2. Configuración Opcional (`.env`)

Crea un archivo `.env` en la raíz si deseas habilitar la auditoría con IA o las alertas de Telegram:

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

## ⚖️ Consideraciones Éticas y Cumplimiento de ToS

* **Enfoque Exclusivo en Adultos:** El sistema descarta activamente anuncios dirigidos a menores de edad sin representación parental (primaria y primeros cursos de secundaria). Se enfoca prioritariamente en estudiantes universitarios (CBC, FIUBA, UTN, UNLP, FP Superior).
* **Escucha Pasiva sin Spam:** El módulo de Telegram opera únicamente en modo escucha pasiva en grupos públicos de libre acceso en los que el usuario ya participa. **No realiza envío automatizado de mensajes directos (DMs) ni acciones no solicitadas.** Todo contacto posterior se realiza de forma manual y contextual por el docente.
* **Gobernanza de Datos:** Los datasets compartidos contienen datos anonimizados o extraídos de tablones estrictamente públicos, respetando principios de minimización de datos.

---

## 🧪 Pruebas Automatizadas

Para ejecutar las comprobaciones de integridad y esquema offline:

```bash
pytest tests/
python validate_dataset.py
```

---

## 📄 Licencia

Distribuido bajo licencia [MIT](LICENSE).
