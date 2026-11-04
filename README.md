# Prospección de Alumnos de Ciencias Exactas

[🇪🇸 Español](README.md) • [🇬🇧 English](README_EN.md)

[![CI](https://github.com/metecondrie/prospeccion-alumnos-ciencias/actions/workflows/ci.yml/badge.svg)](https://github.com/metecondrie/prospeccion-alumnos-ciencias/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Data Benchmark](https://img.shields.io/badge/Data%20Science-Jupyter%20Notebook-orange.svg)](notebooks/evaluacion_clasificador.ipynb)

> **TL;DR (EN):** Autonomous lead-generation pipeline and local CRM for STEM tutoring. Features a multi-source scraper (175 raw listings), two-stage filter (Regex → Google Gemini 2.5 Flash with multi-provider failover), a 24/7 passive Telegram sentinel with push alerts, and a zero-dependency HTML5 CRM dashboard. 41 qualified student leads, $0/mo operating cost, all public data deterministically anonymized.

Pipeline de web scraping, clasificación semántica de intenciones con Google Gemini 2.5 Flash y CRM local autónomo en HTML5/Tailwind para la captación ética de alumnos particulares de matemáticas, física, química y biología.

---

## 📌 TL;DR
* **El Problema:** En los portales de clasificados abiertos, el **76.6%** de los anuncios son academias comerciales o profesores ofreciendo servicios, no estudiantes buscando contratar clases.
* **La Solución:** Rastreó 175 avisos crudos, los evaluó con **Gemini 2.5 Flash** (95.3% de precisión frente al 22.8% de un filtro por palabras clave) y consolidó 41 oportunidades genuinas.
* **Escucha en Vivo:** Centinela pasivo en Telegram (`scripts/telegram_centinela.py`) que monitorea grupos universitarios públicos y emite alertas push inmediatas al celular del docente.
* **Panel Local:** CRM sin backend (`dashboard.html`) que funciona 100% en el navegador con persistencia en `localStorage`, notas por alumno y cartas personalizadas en 1 clic.
* **Costo Operativo:** **$0 USD/mes** (opera íntegramente sobre las cuotas gratuitas de Google AI Studio y almacenamiento local). Muestra pública 100% anonimizada sintéticamente.

---

## 📸 Capturas del Sistema: CRM Local y Alerta Push

![Dashboard Desktop](docs/assets/dashboard_desktop.png)
*Panel interactivo: filtrado dinámico por materia, país y nivel académico, con bitácora comercial por alumno y persistencia en LocalStorage.*

| Tarjetas del CRM en Navegador | Notificación Push en Vivo (Telegram) |
| :---: | :---: |
| ![Dashboard Cards](docs/assets/dashboard_cards.png) | ![Alerta Telegram](docs/assets/alerta_telegram.png) |
| *Sustitución inteligente de saludos y notas.* | *Alerta en tiempo real con datos y CTA directo al chat.* |

---

## 🏗️ Arquitectura del Sistema

```mermaid
flowchart TD
    A["Fuentes Web (TusClases, Tablón, Reddit)"] -->|Extracción Periódica| B["data/extracted_listings.json (175 Crudos)"]
    C["Comunidades Telegram (Grupos Universitarios)"] -->|Escucha Pasiva MTProto| D["scripts/telegram_centinela.py"]
    B & D --> E["Clasificador Semántico (Google Gemini 2.5 Flash)"]
    E -->|Filtrado 95.3% Precisión| F["data/dataset_canonico_auditado.json (41 Aprobados)"]
    E -->|Descarte Documentado| G["data/descartados_auditoria.json (134 Academias)"]
    F --> H["dashboard.html (CRM Local Autónomo)"]
    H --> I["Outreach Humano (Carta personalizada en 1 clic)"]
```

---

## 📊 Evidencia de Datos y Evaluación de Modelos

El rendimiento del clasificador fue evaluado formalmente contra el Ground Truth verificado manualmente sobre los 175 anuncios crudos (ver reporte detallado en [`docs/EVALUACION_FILTRO_DATOS.md`](docs/EVALUACION_FILTRO_DATOS.md) o interactivo en [`notebooks/evaluacion_clasificador.ipynb`](notebooks/evaluacion_clasificador.ipynb)):

| Métrica de Clasificación | Baseline Heurístico (Regex) | Producción: Gemini 2.5 Flash | Delta de Mejora |
|---|---|---|---|
| **Precisión (Precision / VPP)** | 22.8% | **95.3%** | **+72.5 pp** |
| **Sensibilidad (Recall / TPR)** | 40.0% | **100.0%** | **+60.0 pp** |
| **Especificidad (TNR)** | 20.0% | **98.5%** | **+78.5 pp** |
| **F1-Score** | 29.0% | **97.6%** | **+68.6 pp** |
| **Ruido en CRM** | 76.6% inicial | **1.1% residual** | **-75.5 pp de spam filtrado** |

### Embudo Comercial y Telemetría del Piloto Real
Seguimiento de las 41 oportunidades en el CRM (telemetría en [`data/feedback_piloto_conversion.json`](data/feedback_piloto_conversion.json)):

* **175** avisos crudos extraídos → **41** calificados por la IA (23.4% de aprobación).
* **18** contactados en el piloto → **7** respondieron solicitando arancel/disponibilidad (**38.8% de respuesta**).
* **3 alumnos convertidos a clases regulares pagadas** (**16.7% de conversión** sobre contactados):
  1. *Belén M. (UADE):* Física / Máquinas Hidráulicas — 8 hrs/mes ($120.000 ARS/mes).
  2. *Fernando K. (UBA CBC):* Álgebra Universitaria — 4 hrs/mes ($60.000 ARS/mes).
  3. *Estudiante ESO (España):* Física y Química — 4 hrs/mes (€60 EUR/mes).
* **Unit Economics:** Costo de Adquisición (CAC) = **$0 USD**. Ticket promedio = $15.000 ARS/h (~$12 USD).

---

## 💡 Cómo construí este proyecto (Dirección Humana + Asistencia de IA)

* **El problema de negocio nació de mi necesidad real:** Como docente de ciencias exactas, pasaba entre 2 y 3 horas diarias navegando portales de clasificados para encontrar alumnos particulares reales entre decenas de avisos de institutos y colegas ofreciendo servicios.
* **Arquitectura y dirección técnica propia:** Definí los contratos de datos estructurados (RFC 4180 de 8 columnas), las reglas de negocio del CRM, el embudo comercial y la suite de 98 tests automatizados.
* **Implementación en pair-programming con IA:** Programé el sistema asistido por Google Antigravity. Corregí los prompts tras detectar que las academias engañaban a los primeros filtros usando frases como *"clases de matemáticas"*, agregando reglas negativas explícitas (*few-shot negative pool*).
* **Auditoría humana y privacidad:** Verifiqué manualmente cada uno de los 175 avisos crudos para construir el Ground Truth del dataset y diseñé el algoritmo de anonimización determinista ([`scripts/anonymize_for_public.py`](scripts/anonymize_for_public.py)) con 0 colisiones para publicar este portfolio de forma éticamente responsable.

---

## 🚀 Puesta en Marcha Rápida (Multiplataforma)

### 1. Clonar e Instalar

```bash
git clone https://github.com/metecondrie/prospeccion-alumnos-ciencias.git
cd prospeccion-alumnos-ciencias
python -m venv .venv

# Activar entorno virtual
source .venv/bin/activate       # En Linux / macOS
.venv\Scripts\activate          # En Windows

pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 2. Variables de Entorno

```bash
cp .env.example .env    # En Windows: copy .env.example .env
```
*(Si no configuras claves de IA en `.env`, el sistema activa automáticamente el motor heurístico determinista local sin costo).*

### 3. Comandos de Ejecución

```bash
# Modo demostración rápido (100% offline, sin APIs ni credenciales)
python main.py --demo

# Ejecutar pipeline completo (Scraping + Auditoría IA + Compilación)
python main.py run
# O directamente por módulo:
python -m scripts.prospector run

# Ejecutar benchmark cuantitativo de Machine Learning
python main.py evaluate
# O directamente por script:
python evaluation/evaluar_clasificadores.py

# Iniciar Centinela de Telegram en tiempo real
python -m scripts.telegram_centinela
# O modo simulación offline:
python -m scripts.telegram_centinela --simulate

# Ejecutar la suite completa de pruebas (98 tests)
python main.py test
```

*Lanzadores de conveniencia:*
* **Linux / macOS:** `bash bin/actualizar_alumnos.sh`
* **Windows:** Doble clic en `bin\actualizar_alumnos.bat`

---

## 📚 Documentación Técnica Detallada (`/docs` y `/evaluation`)

* ⚙️ [**DOCUMENTACION_TECNICA.md**](docs/DOCUMENTACION_TECNICA.md): Especificación técnica completa, contratos de datos, diagramas Mermaid y arquitectura de resiliencia.
* 📊 [**EVALUACION_FILTRO_DATOS.md**](docs/EVALUACION_FILTRO_DATOS.md): Informe cuantitativo de Machine Learning y matrices de confusión.
* 🧪 [**protocolo_anotacion.md**](evaluation/protocolo_anotacion.md): Protocolo formal de etiquetado y Ground Truth para evaluación objetiva.
* 🛡️ [**MARCO_ETICO_Y_LEGAL.md**](docs/MARCO_ETICO_Y_LEGAL.md): Marco normativo de privacidad (RGPD / Ley 25.326) y protocolo de opt-out.
* 🔒 [**AUDITORIA_HISTORIAL_GIT.md**](docs/AUDITORIA_HISTORIAL_GIT.md): Auditoría de seguridad del historial de commits y estrategia de preservación de privacidad.
* 📈 [**CONCLUSIONES.md**](docs/CONCLUSIONES.md): Resultados pedagógicos y análisis de conversión comercial.
* 📝 [**AUDITORIA_CAMBIOS.md**](docs/AUDITORIA_CAMBIOS.md): Bitácora de decisiones de diseño y auditorías técnicas.

---

## 🧑‍💻 Autoría

**Alejo Ongaro** ([@metecondrie](https://github.com/metecondrie))  
*Docente de Ciencias Exactas y Diseñador del Sistema*  
Repositorio: [github.com/metecondrie/prospeccion-alumnos-ciencias](https://github.com/metecondrie/prospeccion-alumnos-ciencias)

---

## 📄 Licencia

Distribuido bajo licencia [MIT](LICENSE).
