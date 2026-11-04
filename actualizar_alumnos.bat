@echo off
setlocal
cd /d "%~dp0"
if exist "bin\actualizar_alumnos.bat" (
    call "bin\actualizar_alumnos.bat" %*
) else (
    echo [ERROR] No se encontro bin\actualizar_alumnos.bat
    pause
)
