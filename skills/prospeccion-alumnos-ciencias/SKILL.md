---
name: prospeccion-alumnos-ciencias
description: >-
  Captura, clasifica con Gemini 3.6/3.8 Flash y gestiona oportunidades de alumnos que buscan profesor de ciencias exactas (Matemáticas, Física, Química, Biología) en plataformas hispanohablantes (TusClases, Tablón, Cronoshare, Reddit). Preserva el seguimiento de CRM y genera dashboards interactivos auditados con sincronización en Google Drive y Sheets.
---

# Prospección y CRM de Alumnos de Ciencias Exactas

## Overview
Esta skill proporciona un sistema integral para capturar demandas genuinas de alumnos secundarios y universitarios que buscan contratar clases particulares virtuales de ciencias exactas en España y Latinoamérica (Argentina, Chile, Colombia, México y Perú).

El sistema resuelve la asimetría estructural de los portales de clasificados (donde el 90% son anuncios de academias y ofertas docentes), utilizando modelos de frontera **Gemini 3.6 Flash** y **Gemini 3.8 Flash** para filtrar anuncios con alta tasa de solicitudes, y compilar un CRM interactivo liviano (`dashboard.html`) con seguimiento de contactos, carta personalizada con un clic y sincronización multi-destino.

---

## Dependencies
- **`gemini-api-dev`**: Manejo de credenciales de Google Generative Language y cuotas de inferencia.
- **`gsheets`**: Sincronización en vivo con la hoja de cálculo de Google Sheets.
- **`gdrive`**: Respaldo y versionado de entregables en Google Drive.

---

## Quick Start

Para ejecutar una actualización completa de prospectos:
```bash
python skills/prospeccion-alumnos-ciencias/scripts/prospector.py run --model gemini-3.6-flash --desktop-sync
```

O por etapas individuales:
```bash
# 1. Auditar anuncios brutos con Gemini 3.6 Flash
python skills/prospeccion-alumnos-ciencias/scripts/prospector.py audit --input data/extracted_listings.json --output-approved data/approved.json --output-discarded data/discarded.json

# 2. Compilar dashboard y sincronizar en el Escritorio
python skills/prospeccion-alumnos-ciencias/scripts/prospector.py build --approved data/approved.json --discarded data/discarded.json --desktop-sync
```

---

## Utility Scripts (`scripts/prospector.py`)

El script `prospector.py` dispone de los siguientes subcomandos:

* **`audit`**: Evalúa lotes de anuncios contra la API de Gemini forzando salida en JSON. Cada registro recibe `decision_ia` ("Aprobado" / "Descartado") y `justificacion_ia`.
* **`build`**: Genera `dashboard.html`, `alumnos_ciencias_exactas.csv` y `dashboard_crm.csv`. Previene colisión de identificadores, inyecciones XSS y fórmulas en CSV.
* **`run`**: Orquesta el pipeline completo de punta a punta.

---

## Workflow Protocol (Paso a Paso)

### 1. Ingesta de Solicitudes
Rastreo en secciones de demanda filtradas (`?demanda=1`, `/estudiantes/`, `/alumnos/`):
- **TusClases**: España, Argentina, Chile, Colombia, México y Perú.
- **Tablón de Anuncios**: Búsquedas directas de alumnos con formulario web.
- **Cronoshare**: Solicitudes de presupuesto (con indicación de costo de créditos).
- **Reddit**: Comunidades de estudiantes universitarios (`r/UBA`, `r/empleos_AR`).

### 2. Auditoría Semántica con Gemini 3 Flash
- Se procesan en lotes de 10 a 15 anuncios.
- Se utiliza `gemini-3.6-flash` (con fallback automático a `gemini-3.8-flash` ante saturación).
- Se aplica control de tasa adaptativo (1.5 segundos entre lotes) y reintentos exponenciales ante HTTP 429 (`RateLimitError`).

### 3. Supervisión y Observabilidad (Descartados por IA)
- Todo anuncio descartado se almacena con el motivo emitido por el modelo.
- El usuario puede inspeccionar la lista de descartados desde el Dashboard y ejecutar **`↺ Rescatar Prospecto`** para corregir cualquier falso negativo de la IA sin reiniciar el proceso.

### 4. Presentación y Operación del CRM
- **Carta personalizada automática**: El botón de contacto adapta el saludo con el nombre de pila del alumno (`¡Hola Sebastián!`), la materia y el nivel.
- **Acción Segura**: `Copiar Mensaje & Abrir Anuncio` no cambia el estado del prospecto a "Contactado" prematuramente; el estado se confirma mediante el botón `✓ Confirmar Envío`.
- **Respaldo Local**: Botones de `💾 Respaldo JSON` y `📂 Restaurar` para prevenir pérdidas de datos ante borrados de caché.
- **Sincronización Triple**: Escritorio del usuario, Google Sheets y Google Drive.
