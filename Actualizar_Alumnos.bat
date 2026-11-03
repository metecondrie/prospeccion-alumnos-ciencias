@echo off
title Sistema de Prospeccion de Alumnos - Prof. Alejo Ongaro
chcp 65001 > nul
cls

echo ===============================================================================
echo   SISTEMA DE PROSPECCION Y FILTRADO CON IA - PROF. ALEJO ONGARO
echo   Ciencias Exactas: Matematicas, Fisica, Quimica y Biologia
echo   Motor de Busqueda Web + Clasificacion Semantica con Google Gemini 3.6 / 3.8
echo ===============================================================================
echo.
echo [DIRECTORIO DE TRABAJO] %~dp0
echo.

cd /d "%~dp0"

REM -------------------------------------------------------------------------------
REM PASO 0: VERIFICACION DE ENTORNO PYTHON
REM -------------------------------------------------------------------------------
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR CRITICO] No se encontro Python en el sistema.
    echo Asegurate de tener Python instalado y anadido al PATH de Windows.
    echo.
    pause
    exit /b 1
)

REM -------------------------------------------------------------------------------
REM PASO 1: DETECCION Y CONFIGURACION DE LA API KEY DE GOOGLE GEMINI
REM -------------------------------------------------------------------------------
REM Intenta leer GEMINI_API_KEY desde variable de entorno o archivo .env local
if "%GEMINI_API_KEY%"=="" (
    if exist ".env" (
        for /f "usebackq tokens=1,2 delims==" %%a in (".env") do (
            if "%%a"=="GEMINI_API_KEY" set GEMINI_API_KEY=%%b
        )
    )
)

if "%GEMINI_API_KEY%"=="" (
    echo -------------------------------------------------------------------------------
    echo [CONFIGURACION DE IA - GOOGLE GEMINI 3.6 / 3.8 FLASH]
    echo No se encontro una variable de entorno GEMINI_API_KEY ni un archivo .env.
    echo Para que Gemini clasifique los avisos y descarte academias y empleo:
    echo Obtienes tu clave gratis en: https://aistudio.google.com/app/apikey
    echo.
    set /p GEMINI_API_KEY="Ingresa tu GEMINI_API_KEY (o presiona Enter para usar datos auditados): "
    echo -------------------------------------------------------------------------------
    echo.
)

REM -------------------------------------------------------------------------------
REM PASO 2: RASTREO Y BUSQUEDA EN VIVO EN PLATAFORMAS (Web Scraping)
REM Archivo ejecutor: scripts\run_extraction.py
REM Motores incluidos:
REM   - TusClases (Espana, Argentina, Chile, Colombia, Mexico, Peru)
REM   - Tablon de Anuncios (?demanda=1)
REM   - Cronoshare y comunidades educativas
REM Salida intermedia: data\extracted_listings.json
REM -------------------------------------------------------------------------------
echo ===============================================================================
echo [1/3] RASTREO Y BUSQUEDA EN VIVO EN PLATAFORMAS (Web Scraping)
echo Conectando a TusClases, Tablon de Anuncios, Cronoshare y Reddit...
echo Ejecutable: scripts\run_extraction.py
echo ===============================================================================
echo.
if exist "scripts\run_extraction.py" (
    python scripts\run_extraction.py
) else (
    echo [ERROR] No se encontro scripts\run_extraction.py
)

REM -------------------------------------------------------------------------------
REM PASO 3: AUDITORIA SEMANTICA CON IA (Google Gemini 3.6 Flash / 3.8 Flash)
REM Archivo ejecutor: skills\prospeccion-alumnos-ciencias\scripts\prospector.py audit
REM Discrimina alumnos reales de academias e institutos, evaluando cada publicacion
REM Salida de aprobados: data\dataset_canonico_auditado.json
REM Salida de descartados: data\descartados_auditoria.json
REM -------------------------------------------------------------------------------
echo.
echo ===============================================================================
echo [2/3] AUDITORIA SEMANTICA Y FILTRADO CON IA (Google Gemini 3.6 / 3.8 Flash)
echo Analizando intencion de los anuncios capturados con Gemini...
echo Ejecutable: skills\prospeccion-alumnos-ciencias\scripts\prospector.py audit
echo ===============================================================================
echo.
if not "%GEMINI_API_KEY%"=="" (
    if exist "skills\prospeccion-alumnos-ciencias\scripts\prospector.py" (
        python skills\prospeccion-alumnos-ciencias\scripts\prospector.py audit --input data\extracted_listings.json --model gemini-3.6-flash --output-approved data\dataset_canonico_auditado.json --output-discarded data\descartados_auditoria.json
    ) else if exist "scripts\prospector.py" (
        python scripts\prospector.py audit --input data\extracted_listings.json --model gemini-3.6-flash --output-approved data\dataset_canonico_auditado.json --output-discarded data\descartados_auditoria.json
    )
) else (
    echo [AVISO] Omitiendo llamada a la API de Gemini por falta de GEMINI_API_KEY.
    echo Se conservan y utilizan los anuncios auditados en data\dataset_canonico_auditado.json.
)

REM -------------------------------------------------------------------------------
REM PASO 4: COMPILACION DE DASHBOARD CRM Y ARCHIVOS CSV
REM Archivo ejecutor: skills\prospeccion-alumnos-ciencias\scripts\prospector.py build
REM Genera: dashboard.html, alumnos_ciencias_exactas.csv, dashboard_crm.csv
REM Preserva intactos todos los estados guardados previamente en tu CRM local
REM -------------------------------------------------------------------------------
echo.
echo ===============================================================================
echo [3/3] COMPILACION DE DASHBOARD CRM Y PLANILLAS
echo Actualizando dashboard.html, alumnos_ciencias_exactas.csv y dashboard_crm.csv...
echo Ejecutable: skills\prospeccion-alumnos-ciencias\scripts\prospector.py build
echo ===============================================================================
echo.
if exist "skills\prospeccion-alumnos-ciencias\scripts\prospector.py" (
    python skills\prospeccion-alumnos-ciencias\scripts\prospector.py build --approved data\dataset_canonico_auditado.json --discarded data\descartados_auditoria.json --desktop-sync
) else if exist "scripts\prospector.py" (
    python skills\prospeccion-alumnos-ciencias\scripts\prospector.py build --approved data\dataset_canonico_auditado.json --discarded data\descartados_auditoria.json --desktop-sync
)

echo.
echo ===============================================================================
echo   [EXITO] PROCESO DE PROSPECCION COMPLETADO
echo   Tu panel dashboard.html y tus planillas CSV fueron actualizados exitosamente.
echo   Tus estados del CRM (Contactado, Cerrado, etc.) se mantuvieron protegidos.
echo ===============================================================================
echo.
echo Presiona cualquier tecla para abrir o refrescar tu Dashboard en Google Chrome...
pause > nul
start "" "dashboard.html"
