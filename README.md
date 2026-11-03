# Sistema Autónomo de Prospección con IA y CRM de Alumnos (Ciencias Exactas)

[![AI Engine](https://img.shields.io/badge/AI_Engine-Gemini_%2F_Groq_%2F_Mistral-blue.svg)](https://aistudio.google.com/)
[![Audit Tests](https://img.shields.io/badge/Audit_Tests-Passed_100%25-brightgreen.svg)](#validación-y-pruebas-automatizadas)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Audited_Production_v3.4-indigo.svg)](#)

Sistema integral de ingeniería de datos, web scraping concurrente, filtrado semántico multiproveedor (**Google Gemini 3.5 Flash-Lite**, **Groq LPU** y **Mistral AI**) y panel CRM interactivo autónomo (**`dashboard.html`**) para la captación, filtrado y gestión de alumnos en materias de ciencias exactas (**Matemáticas, Física, Química y Biología**) para nivel secundario, técnico y universitario en España e Hispanoamérica (Argentina, Chile, Colombia, México, Perú).

Diseñado a medida para la propuesta pedagógica del **Prof. Alejo Ongaro** (más de 18 años de experiencia docente, estudiante de Biología Molecular, modalidad **100% Online / Virtual**).

---

## 🚀 Características Principales

1. **Rastreador Web en Vivo (Web Scraping)**:
   - Extrae automáticamente solicitudes y demandas reales (`?demanda=1`, `/estudiantes/`) en portales clasificados:
     - **TusClases**: Red en España, Argentina, Chile, Colombia, México y Perú.
     - **Tablón de Anuncios**: Tablones de demanda escolar y universitaria en España.
     - **Cronoshare**: Solicitudes con categorización transparente de créditos (Cronos).
     - **Reddit**: Comunidades de estudiantes y búsqueda de apoyo académico (`r/empleos_AR`).
2. **Auditoría Semántica Multiproveedor con IA (Failover en Cascada)**:
   - Resuelve el problema asimétrico de los clasificados (donde el 90% son ofertas de trabajo o academias buscando docentes).
   - **Triple Motor de Relevo**:
     - **Titular**: Google Gemini (`gemini-3.5-flash-lite`), máxima precisión y JSON estructurado.
     - **Suplente 1**: Groq LPU (`openai/gpt-oss-20b` / `qwen/qwen3.8-27b`), velocidad ultrarrápida (<1s por lote) y 1.000 req/día gratis.
     - **Suplente 2**: Mistral AI (`ministral-8b-latest`), tokenizador Tekken y alta fidelidad en español.
   - Explica de forma transparente cada decisión en el campo `Criterio_IA`.
3. **Panel CRM Interactivo (`dashboard.html`)**:
   - Funciona autónomamente en el navegador con Tailwind CSS y persistencia segura en `localStorage` (con fallback de memoria).
   - **Buscador sin acentos (Normalización Unicode NFD)**: Buscar "hernan", "cordoba", "peru", "matematicas" encuentra sus respectivos avisos.
   - **Filtro estricto por nivel educativo**: "Universitario" devuelve exactamente 16 prospectos puros sin mezclar con pre-universitarios.
   - **Bitácora y Notas CRM por lead**: Modal para registrar notas, WhatsApp, precio acordado, próximas fechas de seguimiento y confirmación de respuesta.
   - **Tratamiento honesto de Cronoshare**: Botón diferenciado `🔍 Buscar en Cronoshare (Requiere Créditos)` con tooltip explicativo y sin sobrescribir el portapapeles.
   - **Flujo de contacto seguro**: Botón `📋 Copiar & Abrir` separado de la confirmación `✓ Confirmar Envío`. Si un prospecto está en estado `Cerrado`, nunca sufre regresión a `Contactado`.
   - **Copias de seguridad**: Botones de `💾 Respaldo JSON` y `📁 Restaurar` para no perder notas ni cambios al cambiar de equipo.
4. **Ejecutor Seguro de Un Clic (`Actualizar_Alumnos.bat`)**:
   - Puente nativo en Windows para correr el scraping, consultar la IA con relevo automático, validar la integridad determinista del dataset, inyectar los prospectos y recargar el Dashboard en Chrome.

---

## 🏗️ Arquitectura del Pipeline

```mermaid
flowchart TD
    A["Fuentes Web (ES, AR, CL, CO, PE, MX)"] -->|Web Scraping Concurrente| B["data/extracted_listings.json"]
    B -->|Evaluación Batch Multiproveedor| C{"Cascada de IA"}
    C -->|Titular| D["Google Gemini 3.5 Flash-Lite"]
    C -->|Fallback 1| E["Groq LPU (GPT-OSS 20B)"]
    C -->|Fallback 2| F["Mistral AI (Ministral 8B)"]
    D -->|¿Es Alumno Real?| G{"Clasificación"}
    E -->|¿Es Alumno Real?| G
    F -->|¿Es Alumno Real?| G
    G -->|No: Academias / Empleo| H["data/descartados_auditoria.json"]
    G -->|Sí: Estudiantes Legítimos| I["data/dataset_canonico_auditado.json"]
    I -->|Validación Determinista| J["validate_dataset.py"]
    J -->|Compilación Idempotente| K["scripts/prospector.py build"]
    K -->|Sincronización Escritorio| L["dashboard.html (Web CRM)"]
    K -->|Exportación Planillas| M["alumnos_ciencias_exactas.csv & dashboard_crm.csv"]
```

---

## 📁 Estructura del Repositorio

```text
├── Actualizar_Alumnos.bat         # Lanzador ejecutable nativo de 3 pasos para Windows
├── dashboard.html                 # Aplicación web CRM interactiva (HTML5/Tailwind/JS)
├── alumnos_ciencias_exactas.csv   # Base de datos canónica tabular con BOM UTF-8 y protección anti-fórmula
├── dashboard_crm.csv              # Planilla operativa CRM para importación en Google Sheets / Excel
├── check_dashboard.cjs            # Suite de pruebas automatizadas en Node.js (Aserciones estrictas)
├── validate_dataset.py            # Validador determinista de integridad de datos y URLs
├── requirements.txt               # Dependencias de Python requeridas
├── .env.example                   # Plantilla para configuración de claves de IA
├── INFORME_BENCHMARKING_Y_ARQUITECTURA_MULTIPROVEEDOR.pdf # Informe técnico comparativo
├── DOCUMENTACION_TECNICA_PROYECTO.md # Documento técnico de especificación y seguridad
├── Conclusiones_del_Proyecto.md   # Conclusiones comerciales, operativas y estrategia de captación
├── directorio_plataformas.md      # Análisis comparativo de los portales evaluados
├── data/
│   ├── dataset_canonico_auditado.json # 41 publicaciones aprobadas (38 estudiantes únicos)
│   ├── descartados_auditoria.json     # Registro de academias y ofertas rechazadas por la IA
│   └── extracted_listings.json        # Datos brutos de la extracción web
├── scripts/
│   ├── prospector.py              # CLI unificado (comandos: audit, build, run)
│   ├── run_extraction.py          # Orquestador del scraping concurrente
│   ├── extract_tusclases.py       # Scraper para red TusClases (6 países)
│   ├── extract_tablon.py          # Scraper de Tablón de Anuncios (?demanda=1)
│   ├── extract_cronoshare_workana.py # Scraper de Cronoshare y Reddit
│   └── common_filter.py           # Validadores de estructura y verificación HTTP de enlaces
└── skills/
    └── prospeccion-alumnos-ciencias/
        ├── SKILL.md               # Definición de la Skill de prospección para Antigravity
        └── scripts/
            └── prospector.py      # Réplica sincronizada de prospector CLI
```

---

## 🛠️ Requisitos e Instalación

### Requisitos Previos
- **Windows 10 / 11** (o Linux/macOS).
- **Python 3.10 o superior**.
- **Node.js v18 o superior** (para ejecutar la suite de pruebas del dashboard).

### Instalación de Dependencias
```bash
pip install -r requirements.txt
```

### Configuración de Claves de IA (.env)
1. Copia `.env.example` a `.env`:
   ```bash
   cp .env.example .env
   ```
2. Completa tus claves de API gratuitas (el sistema funciona con cualquiera de ellas, y si configuras varias, activa el relevo automático):
   ```env
   GEMINI_API_KEY=tu_clave_de_google_ai_studio
   GROQ_API_KEY=tu_clave_de_groq_console
   MISTRAL_API_KEY=tu_clave_de_mistral_la_plateforme
   ```

---

## 🧪 Validación y Pruebas Automatizadas

Para auditar y comprobar el 100% de la integridad del sistema:

1. **Validación del Dataset (Python)**:
   ```bash
   python validate_dataset.py
   ```
2. **Validación del Dashboard y Frontend (Node.js)**:
   ```bash
   node check_dashboard.cjs
   ```
3. **Recompilación Idempotente y Sincronización en Escritorio**:
   ```bash
   python scripts/prospector.py build --desktop-sync
   ```

---

## 📄 Licencia

Este proyecto está bajo la Licencia MIT.
