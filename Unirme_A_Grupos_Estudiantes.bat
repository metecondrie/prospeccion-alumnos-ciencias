@echo off
setlocal enabledelayedexpansion
title Conexion Automatica a Grupos Estudiantiles de Telegram - Prof. Alejo Ongaro
chcp 65001 > nul
cls

echo ===============================================================================
echo   CONEXION AUTOMATICA SEGURA A GRUPOS ESTUDIANTILES DE TELEGRAM
echo   Ciencias Exactas: CBC UBA, FIUBA y UTN
echo ===============================================================================
echo.
echo [DIRECTORIO DE TRABAJO] %~dp0
echo.

cd /d "%~dp0"

python --version > nul 2>&1
if errorlevel 1 (
    echo [ERROR CRITICO] No se encontro Python en el sistema.
    pause
    exit /b 1
)

if exist "scripts\auto_join_groups.py" (
    python scripts\auto_join_groups.py
) else (
    echo [ERROR CRITICO] No se encontro scripts\auto_join_groups.py
    pause
    exit /b 1
)

echo.
pause
