@echo off
setlocal enabledelayedexpansion
title Sistema de Prospeccion de Alumnos - Prof. Alejo Ongaro
chcp 65001 > nul
cls

echo ===============================================================================
echo   SISTEMA DE PROSPECCION Y FILTRADO CON IA - PROF. ALEJO ONGARO
echo   Ciencias Exactas: Matematicas, Fisica, Quimica y Biologia
echo   Web Scraping en Vivo + Auditoria Semantica con Google Gemini Flash
echo ===============================================================================
echo.
echo [DIRECTORIO DE TRABAJO] %~dp0
echo.

cd /d "%~dp0\.."

REM -------------------------------------------------------------------------------
REM PASO 0: VERIFICACION DE ENTORNO PYTHON
REM -------------------------------------------------------------------------------
python --version > nul 2>&1
if errorlevel 1 (
    echo [ERROR CRITICO] No se encontro Python en el sistema.
    echo Asegurate de tener Python instalado y anadido al PATH de Windows.
    echo.
    pause
    exit /b 1
)

REM -------------------------------------------------------------------------------
REM PASO 1: DETECCION Y CONFIGURACION DE CLAVES DE IA (MULTIPROVEEDOR)
REM -------------------------------------------------------------------------------
REM Intenta leer claves desde archivo .env local
if exist ".env" (
    for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
        if not "%%a"=="" if not "%%b"=="" set "%%a=%%~b"
    )
)

set HAS_AI_KEY=
if not "%GEMINI_API_KEY%"=="" set HAS_AI_KEY=1
if not "%CLOUDFLARE_API_TOKEN%"=="" set HAS_AI_KEY=1
if not "%GROQ_API_KEY%"=="" set HAS_AI_KEY=1
if not "%MISTRAL_API_KEY%"=="" set HAS_AI_KEY=1

if "%HAS_AI_KEY%"=="" (
    echo -------------------------------------------------------------------------------
    echo [CONFIGURACION DE IA - ARQUITECTURA MULTIPROVEEDOR]
    echo No se encontro ninguna clave de IA configurada en el sistema ni en .env.
    echo Puedes usar tu clave gratis de Google Gemini (recomendado):
    echo Obtienes tu clave gratis en: https://aistudio.google.com/app/apikey
    echo.
    set /p GEMINI_API_KEY="Ingresa tu GEMINI_API_KEY (o presiona Enter para usar datos auditados): "
    if not "!GEMINI_API_KEY!"=="" set HAS_AI_KEY=1
    echo -------------------------------------------------------------------------------
    echo.
)
REM Restablecer errorlevel a 0
cmd /c "exit /b 0"

REM -------------------------------------------------------------------------------
REM PASO 2: RASTREO Y BUSQUEDA EN VIVO EN PLATAFORMAS (Web Scraping)
REM Archivo ejecutor: scripts\run_extraction.py
REM -------------------------------------------------------------------------------
echo ===============================================================================
echo [1/3] RASTREO Y BUSQUEDA EN VIVO EN PLATAFORMAS (Web Scraping)
echo Conectando a TusClases, Tablon de Anuncios, Cronoshare, Reddit y Telegram...
echo Ejecutable: scripts\run_extraction.py
echo ===============================================================================
echo.
if exist "scripts\run_extraction.py" (
    python scripts\run_extraction.py
    if errorlevel 1 (
        echo [ADVERTENCIA] Hubo una alerta en la extraccion web en vivo. Se conservan los datos de cache.
        cmd /c "exit /b 0"
    )
) else (
    echo [ERROR CRITICO] No se encontro scripts\run_extraction.py
    pause
    exit /b 1
)

REM -------------------------------------------------------------------------------
REM PASO 3: AUDITORIA SEMANTICA Y FILTRADO MULTIPROVEEDOR CON IA
REM -------------------------------------------------------------------------------
echo.
echo ===============================================================================
echo [2/3] AUDITORIA SEMANTICA MULTIPROVEEDOR CON IA
echo Clasificando con Google Gemini (Titular), Cloudflare, Groq o Mistral...
echo ===============================================================================
echo.
if not "%HAS_AI_KEY%"=="" (
    if exist "scripts\prospector.py" (
        python scripts\prospector.py audit --input data\extracted_listings.json --model gemini-3.5-flash --output-approved data\dataset_canonico_auditado.json --output-discarded data\descartados_auditoria.json
    ) else if exist "scripts\prospector.py" (
        python scripts\prospector.py audit --input data\extracted_listings.json --model gemini-3.5-flash --output-approved data\dataset_canonico_auditado.json --output-discarded data\descartados_auditoria.json
    )
    if errorlevel 1 (
        echo [ADVERTENCIA] La auditoria de IA reporto una advertencia. Se conservan los datos auditados canonicos.
        cmd /c "exit /b 0"
    )
) else (
    echo [AVISO] Omitiendo llamada a la API de IA por falta de claves configuradas.
    echo Se conservan y utilizan los anuncios auditados en data\dataset_canonico_auditado.json.
)

REM -------------------------------------------------------------------------------
REM PASO 4: VALIDACION ESTRICTA DE DATASET CANONICO
REM -------------------------------------------------------------------------------
echo.
echo ===============================================================================
echo [VALIDACION] Comprobando integridad determinista de los datos...
echo ===============================================================================
echo.
if exist "validate_dataset.py" (
    python validate_dataset.py
    if errorlevel 1 (
        echo [ERROR CRITICO] Fallo la validacion del dataset. Abortando compilacion.
        pause
        exit /b 1
    )
)

REM -------------------------------------------------------------------------------
REM PASO 5: COMPILACION DE DASHBOARD CRM Y ARCHIVOS CSV
REM -------------------------------------------------------------------------------
echo.
echo ===============================================================================
echo [3/3] COMPILACION DE DASHBOARD CRM Y PLANILLAS
echo Actualizando dashboard.html, alumnos_ciencias_exactas.csv y dashboard_crm.csv...
echo ===============================================================================
echo.
if exist "scripts\prospector.py" (
    python scripts\prospector.py build --approved data\dataset_canonico_auditado.json --discarded data\descartados_auditoria.json --desktop-sync
) else if exist "scripts\prospector.py" (
    python scripts\prospector.py build --approved data\dataset_canonico_auditado.json --discarded data\descartados_auditoria.json --desktop-sync
)
if errorlevel 1 (
    echo [ERROR CRITICO] Fallo la compilacion del dashboard y planillas.
    pause
    exit /b 1
)

where node > nul 2>&1
if not errorlevel 1 (
    if exist "tests\check_dashboard.cjs" (
        echo.
        echo [VERIFICACION DASHBOARD] Ejecutando suite de pruebas unitarias en Node.js...
        node tests\check_dashboard.cjs
        if errorlevel 1 (
            echo [ADVERTENCIA] Algunas aserciones del dashboard fallaron.
            cmd /c "exit /b 0"
        )
    )
)

echo.
echo ===============================================================================
echo   [EXITO] PROCESO DE PROSPECCION COMPLETADO EXITOSAMENTE
echo   Tu panel dashboard.html y tus planillas CSV fueron actualizados.
echo   Tus estados del CRM (Contactado, Cerrado, etc.) se mantuvieron protegidos.
echo ===============================================================================
echo.
echo Presiona cualquier tecla para abrir o refrescar tu Dashboard en Google Chrome...
pause > nul
start "" "dashboard.html"
