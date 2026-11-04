@echo off
chcp 65001 > nul
title Prueba de Alerta en Vivo - Centinela Telegram
echo ======================================================================
echo    PRUEBA DE FLUJO COMPLETO: CENTINELA + GEMINI IA + ALERTA PUSH
echo ======================================================================
echo.
python scripts\test_centinela_pipeline.py
echo.
echo Presiona cualquier tecla para salir...
pause > nul
