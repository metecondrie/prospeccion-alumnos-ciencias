# 🎓 Sistema Autónomo de Prospección con IA, Centinela Telegram 24/7 y CRM de Alumnos (Ciencias Exactas)

<p align="center">
  <img src="https://img.shields.io/badge/AI_Engine-Gemini_Flash_%2F_Groq_%2F_Mistral-0052cc.svg?style=for-the-badge&logo=google" alt="AI Engine" />
  <img src="https://img.shields.io/badge/Realtime_Sentinel-Telegram_MTProto_24%2F7-26A5E4.svg?style=for-the-badge&logo=telegram" alt="Telegram Sentinel" />
  <img src="https://img.shields.io/badge/Push_Alerts-Directo_al_Celular-success.svg?style=for-the-badge&logo=pushover" alt="Push Alerts" />
  <img src="https://img.shields.io/badge/Cost-100%25_Gratuito_%240_USD-brightgreen.svg?style=for-the-badge" alt="Free Cost" />
  <img src="https://img.shields.io/badge/Version-4.0_Production_Enterprise-purple.svg?style=for-the-badge" alt="Version" />
</p>

---

## 📌 Visión General del Proyecto

Plataforma inteligente de ingeniería de datos, **escucha en tiempo real (MTProto)**, web scraping concurrente, auditoría semántica con **Triple Motor de Inteligencia Artificial (Google Gemini Flash Lite + Groq LPU + Mistral AI)** y panel de gestión comercial (**CRM interactivo `dashboard.html`**).

El sistema fue diseñado a la medida de la propuesta pedagógica del **Prof. Alejo Ongaro**:
* **Trayectoria:** Más de 18 años de experiencia docente universitaria y secundaria. Formación en Biología Molecular y Ciencias Exactas.
* **Especialidades:** Matemática, Física, Química, Biología, Biofísica, Álgebra, Análisis Matemático, CBC UBA, UTN, UNLP.
* **Modalidad:** 100% Online / Virtual para Argentina y Latinoamérica (con soporte en España).
* **Costo Operativo:** **$0 USD / mes** (100% en capas gratuitas oficiales de Google AI Studio, Groq Cloud, Mistral AI y Telegram Bot API).

---

## ⚡ Novedades Principales (Versión 4.0)

1. **🚨 Centinela Telegram en Tiempo Real 24/7 (`telegram_centinela.py`):**
   * Escucha continua por eventos en streaming (sin llamadas repetitivas o polling) en todos los grupos y comunidades estudiantiles donde el usuario sea miembro.
   * **Filtro de dos etapas:** 
     1. Heurística Regex a 0ms (descarta mensajes irrelevantes o charlas comunes sin costo computacional).
     2. Auditoría semántica con IA en 500ms para confirmar la intención del estudiante.
   * **Alertas Push Instantáneas:** Envío inmediato de la ficha del alumno a tu chat privado de Telegram con un botón directo (`tg://user?id=...` o `@usuario`) para escribirle en el acto.
   * **Latido en Pantalla (Heartbeat) y Caja Negra:** Muestra un pulso visual cada 60s con estadísticas en vivo y registra cada detección en `logs/centinela.log`.

2. **🛡️ Filtro de Liveness Inteligente (`auto_join_groups.py`):**
   * Audita la fecha del último mensaje público de cada grupo antes de unirse.
   * **Descarta grupos "fantasmas" o inactivos** (última actividad > 60 días) para no saturar tu cuenta ni activar límites de Telegram.
   * Manejo transparente y seguro de pausas (*FloodWait protection*).

3. **🕸️ Scraper Web Multicanal Ampliado (170+ avisos concurrentes):**
   * Extracción periódica de demandas estudiantiles reales (`?demanda=1`, `/estudiantes/`, RSS):
     * **TusClases:** Red en Argentina, España, México, Colombia, Chile y Perú.
     * **Tablón de Anuncios:** Demandas de bachillerato y clases universitarias.
     * **Cronoshare:** Peticiones con discriminación de coste por contacto.
     * **Reddit:** Comunidades universitarias (`r/UBA`, `r/empleos_AR`, `r/Cordoba`).
     * **Telegram Web Channels:** Extracción de canales públicos sin login vía `https://t.me/s/`.

4. **📊 Dashboard CRM Reactivo (`dashboard.html`):**
   * Persistencia local segura en `localStorage` con bitácora de notas, WhatsApp, precios pactados y fechas de seguimiento.
   * Buscador insensible a acentos (NFD) y filtrado estricto por nivel educativo (Universitario, Secundario, Terciario).

---

## 🏛️ Arquitectura del Sistema

El pipeline combina procesamiento por lotes (Batch) para la web y procesamiento reactivo continuo (Stream) para mensajería instantánea.

### 1. Diagrama de Flujo Integral

```mermaid
flowchart TD
    subgraph INGESTION["1. Fuentes de Datos Multicanal"]
        A1["Portales Web<br/>(TusClases, Tablón, Cronoshare, Reddit)"]
        A2["Canales Públicos Telegram<br/>(Web Scraper t.me/s/)"]
        A3["Grupos Estudiantiles en Vivo<br/>(Telethon MTProto Stream)"]
    end

    subgraph PREFILTER["2. Preprocesamiento & Filtro Rápido"]
        B1["Orquestador Batch<br/>(run_extraction.py)"]
        B2["Filtro Heurístico 0ms<br/>(Regex Triggers & Materias)"]
    end

    subgraph AI_ENGINE["3. Auditoría Semántica con Cascada de IA (Triple Motor)"]
        C{"Evaluador de Intención"}
        M1["Google Gemini 2.5 Flash Lite<br/>(Titular - Structured JSON)"]
        M2["Groq LPU Llama 3.3 70B<br/>(Fallback 1 - Velocidad <1s)"]
        M3["Mistral AI Small Latest<br/>(Fallback 2 - Tokenizador Tekken)"]
    end

    subgraph DECISION["4. Clasificación & Control Antifraude"]
        D1["Descartado: Academias / Ofertas Empleo / Spam"]
        D2["Aprobado: Estudiante Real buscando Clases"]
    end

    subgraph OUTPUTS["5. Despliegue, CRM y Notificaciones"]
        E1["Base de Datos Incremental<br/>(data/dataset_canonico_auditado.json)"]
        E2["Alerta Push Inmediata al Celular<br/>(Bot Telegram con Enlace Directo)"]
        E3["Planillas Operativas<br/>(alumnos_ciencias_exactas.csv & CRM CSV)"]
        E4["Panel Interactivo Local<br/>(dashboard.html en Chrome)"]
    end

    A1 --> B1
    A2 --> B1
    B1 -->|Lotes JSON| C
    A3 -->|Mensaje en Vivo| B2
    B2 -->|Match de Palabras Clave| C
    B2 -.->|Mensaje Irrelevante| D1

    C --> M1
    M1 -.->|Si hay error/cuota| M2
    M2 -.->|Si hay error/cuota| M3
    M1 --> D2
    M2 --> D2
    M3 --> D2

    D1 -->|Auditoría Histórica| F1["data/descartados_auditoria.json"]
    D2 --> E1
    D2 -->|Evento en Vivo| E2
    E1 --> E3
    E1 --> E4
```

---

### 2. Diagrama de Secuencia: Detección en Vivo con el Centinela

```mermaid
sequenceDiagram
    autonumber
    actor Estudiante as Estudiante en Grupo
    participant Telegram as Telegram MTProto
    participant Centinela as Centinela (telegram_centinela.py)
    participant IA as Cascada IA (Gemini / Groq)
    participant BD as CRM DB (JSON / CSV)
    actor Alejo as Prof. Alejo (Celular)

    Estudiante->>Telegram: "Hola chicos, ¿alguien conoce profe particular de Análisis 1 para la UTN?"
    Telegram->>Centinela: Evento NewMessage en tiempo real
    Note over Centinela: Filtro Regex: 'profe' + 'análisis' detectados (0ms)
    Centinela->>IA: Evaluar intención: ¿Es estudiante real de ciencias exactas?
    IA-->>Centinela: JSON: { is_student: true, decision_ia: 'Aprobado', materia: 'Análisis Matemático' }
    par Guardar en Base de Datos
        Centinela->>BD: Registro incremental sin duplicados
    and Notificar en Celular
        Centinela->>Alejo: 🚨 Notificación Push con resumen y botón de chat directo
    end
    Alejo->>Estudiante: Contacto directo en menos de 2 minutos vía Telegram
```

---

## 🎯 Criterios de Auditoría con Inteligencia Artificial

Para evitar el problema habitual donde más del 80% de los anuncios de internet son falsos positivos, la IA aplica reglas estrictas:

| Criterio | Acción de la IA | Ejemplos Detectados y Excluidos |
| :--- | :---: | :--- |
| **Estudiante o Padre buscando profesor** | ✅ **Aprobado** | *"Busco profe de Física para preparar final de la FIUBA"*, *"Necesito apoyo en Química para mi hijo de 4to año"*. |
| **Academia / Instituto privado** | ❌ **Descartado** | *"Academia Centro Universitario abre inscripciones a curso intensivo"*, *"Precios promocionales en nuestro instituto"*. |
| **Oferta laboral / Empleo docente** | ❌ **Descartado** | *"Colegio privado busca docente de Matemática para ciclo básico"*, *"Se busca profesor suplente turno tarde"*. |
| **Profesor ofreciendo sus clases** | ❌ **Descartado** | *"Doy clases particulares de Álgebra y Geometría, 15 años de experiencia"*, *"Profesor particular a domicilio"*. |
| **Materia fuera de Ciencias Exactas** | ❌ **Descartado** | Clases de inglés, guitarra, historia, programación web o marketing. |

---

## 👥 Comunidades Estudiantiles Monitoreadas en Telegram

El sistema se conecta a grupos y canales públicos verificados por el filtro de liveness:

```text
├── Grupos de Discusión en Vivo (Vigilancia Activa de Consultas):
│   ├── [UTN FRBA]        @ingresoutnfrba            (329 miembros)
│   ├── [FIUBA]           @QuimicaFIUBA              (207 miembros)
│   ├── [FIUBA]           @ASTAR_fiuba               (156 miembros)
│   ├── [Universitarios]  @us21_analisis_matematico  (500 miembros)
│   ├── [Universitarios]  @analisismatematicoi       (130 miembros)
│   ├── [UNLP La Plata]   @chatUNLP                  (93 miembros)
│   ├── [UNLP Medicina]   @IngMedUNLP2023            (104 miembros)
│   └── [CBC UBA]         @cbcalumnos                (36 miembros)
│
└── Canales de Noticias y Materiales (Extracción Web):
    ├── @universidad_nacional_de_laplata             (1.352 miembros)
    ├── @FIUBA_Noticias                              (690 miembros)
    └── @cbcubamateriales                            (105 miembros)
```

---

## 📋 Formato de la Alerta en tu Celular

Cuando el Centinela aprueba un alumno, recibes una notificación en tu bot personal (`@alejo_ciencias_alumnos_bot`):

```text
🚨 ¡CENTINELA TELEGRAM EN VIVO!
Nuevo alumno detectado en el grupo: Ingreso - UTN FRBA (Matemática y Física)

👤 Alumno: @lucas_utn26
📚 Materia: Análisis Matemático
🎯 Nivel: Universitario (Ingreso / Grado)

💬 Mensaje: "Buenas tardes, me cuesta un montón la parte de derivadas e integrales de la guía 3. ¿Algún profe que dé clases virtuales este fin de semana?"

👉 [Abrir chat y contactar al alumno]
```

---

## 💻 Guía Rápida de Uso en Windows

El sistema cuenta con ejecutables nativos `.bat` para operar en un clic:

```mermaid
stateDiagram-v2
    [*] --> IniciarCentinela: Iniciar_Centinela_Telegram.bat
    IniciarCentinela --> EscuchandoEnVivo: Cuenta autenticada
    EscuchandoEnVivo --> AlertaCelular: Estudiante escribe en grupo
    AlertaCelular --> EscuchandoEnVivo: Continúa vigilando 24/7

    [*] --> ActualizarWeb: Actualizar_Alumnos.bat
    ActualizarWeb --> ScrapingWeb: Portales + Reddit
    ScrapingWeb --> AuditoriaLotes: Cascada Gemini / Groq
    AuditoriaLotes --> DashboardAbierto: Inyecta y abre dashboard.html en Chrome
```

1. **Para activar el vigilante en tiempo real:**
   * Doble clic en `Iniciar_Centinela_Telegram.bat`.
   * Podés **minimizar** la ventana (con la raya `_`). Queda corriendo en segundo plano y te reporta el latido cada 60s.
2. **Para actualizar todos los portales web (TusClases, Tablón, Cronoshare, Reddit):**
   * Doble clic en `Actualizar_Alumnos.bat`.
   * En 30 segundos busca, audita y abre automáticamente `dashboard.html` en Chrome con los prospectos listos.
3. **Para explorar o gestionar prospectos:**
   * Abrí `dashboard.html` directamente con tu navegador favorito.

---

## ⚙️ Estructura del Proyecto

```text
├── Iniciar_Centinela_Telegram.bat     # Lanzador del bot Centinela 24/7
├── Actualizar_Alumnos.bat             # Lanzador del ciclo completo de scraping web y CRM
├── Unirme_A_Grupos_Estudiantes.bat    # Conector inteligente a grupos con filtro de actividad
├── dashboard.html                     # Aplicación Web CRM interactiva (Tailwind CSS)
├── alumnos_ciencias_exactas.csv       # Base de datos canónica tabular (BOM UTF-8, anti-fórmula)
├── dashboard_crm.csv                  # Planilla adaptada para Google Sheets / Excel
├── validate_dataset.py                # Validador determinista de integridad del dataset
├── requirements.txt                   # Dependencias de Python (telethon, requests, google-genai, etc.)
│
├── data/
│   ├── dataset_canonico_auditado.json # Dataset principal acumulativo de alumnos aprobados
│   ├── descartados_auditoria.json     # Historial de falsos positivos y academias filtradas
│   ├── extracted_listings.json        # Extracciones web crudas
│   └── telegram_channels.json         # Directorio de grupos y canales auditados
│
├── logs/
│   └── centinela.log                  # Registro cronológico continuo de detecciones del Centinela
│
└── scripts/
    ├── telegram_centinela.py          # Cliente MTProto en streaming con IA en vivo y push
    ├── auto_join_groups.py            # Validador de liveness y auto-join con rate-limit
    ├── prospector.py                  # CLI central del motor de IA y compilador del dashboard
    ├── run_extraction.py              # Orquestador concurrente de scrapers web
    ├── extract_tusclases.py           # Scraper para red TusClases (6 países)
    ├── extract_tablon.py              # Scraper de Tablón de Anuncios
    ├── extract_cronoshare_workana.py  # Scraper de Cronoshare y Reddit RSS
    └── extract_telegram.py            # Scraper de vistas web de canales públicos
```

---

## 🔒 Seguridad y Privacidad

* Las credenciales personales (`TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `TELEGRAM_BOT_TOKEN`, `GEMINI_API_KEY`) y la sesión (`centinela_session.session`) están estrictamente protegidas mediante `.gitignore` y variables en `.env`.
* No se guardan ni transmiten contraseñas en texto plano.
* Los archivos exportados para Excel están protegidos contra inyecciones de fórmulas maliciosas (`=`, `+`, `-`, `@`).

---

## 📄 Licencia

Desarrollado bajo licencia **MIT** para el **Prof. Alejo Ongaro**. Libre de costos de licenciamiento o infraestructura de pago.
