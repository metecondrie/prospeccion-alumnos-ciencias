@echo off
setlocal enabledelayedexpansion
title Sistema Centinela Telegram en Tiempo Real - Prof. Alejo Ongaro
chcp 65001 > nul
cls

echo ===============================================================================
echo   SISTEMA CENTINELA TELEGRAM EN VIVO - PROF. ALEJO ONGARO
echo   Escucha automatica en tiempo real de grupos de estudiantes
echo   Auditoria instantanea con IA + Alerta push a tu celular en 2 segundos
echo ===============================================================================
echo.
echo [DIRECTORIO DE TRABAJO] %~dp0
echo.

cd /d "%~dp0\.."

python --version > nul 2>&1
if errorlevel 1 (
    echo [ERROR CRITICO] No se encontro Python en el sistema.
    pause
    exit /b 1
)

if exist "scripts\telegram_centinela.py" (
    python scripts\telegram_centinela.py
) else (
    echo [ERROR CRITICO] No se encontro scripts\telegram_centinela.py
    pause
    exit /b 1
)

echo.
echo [AVISO] El Centinela se ha detenido.
pause
