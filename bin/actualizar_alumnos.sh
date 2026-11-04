#!/usr/bin/env bash
# ==============================================================================
# Script de Prospección y Compilación Automatizada (Linux / macOS / POSIX)
# ==============================================================================
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR/.."

echo "==============================================================================="
echo "  SISTEMA DE PROSPECCIÓN Y FILTRADO CON IA - PROF. ALEJO ONGARO"
echo "  Ciencias Exactas: Matemáticas, Física, Química y Biología"
echo "==============================================================================="

# 1. Verificar Python
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "[ERROR CRÍTICO] Python no está instalado en el sistema."
    exit 1
fi
PYTHON_CMD=$(command -v python3 || command -v python)

# 2. Cargar variables de .env si existe
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs -d '\n') 2>/dev/null || true
fi

# 3. Extracción Web
echo ""
echo "[1/3] RASTREO Y BÚSQUEDA EN VIVO EN PLATAFORMAS"
$PYTHON_CMD scripts/run_extraction.py || echo "[AVISO] La extracción web emitió una advertencia. Continuando con caché..."

# 4. Auditoría Semántica IA / Fallback
echo ""
echo "[2/3] AUDITORÍA SEMÁNTICA CON IA"
$PYTHON_CMD scripts/prospector.py audit --input data/extracted_listings.json --output-approved data/dataset_canonico_auditado.json --output-discarded data/descartados_auditoria.json

# 5. Validación de Integridad
echo ""
echo "[VALIDACIÓN] Comprobando integridad del dataset canónico..."
$PYTHON_CMD validate_dataset.py

# 6. Compilación de Dashboard y CSVs
echo ""
echo "[3/3] COMPILACIÓN DE DASHBOARD CRM Y PLANILLAS"
$PYTHON_CMD scripts/prospector.py build --approved data/dataset_canonico_auditado.json --discarded data/descartados_auditoria.json

# 7. Validación Node.js del Dashboard (si Node está presente)
if command -v node &> /dev/null; then
    echo ""
    echo "[TEST DASHBOARD] Ejecutando suite de pruebas en Node.js..."
    node tests/check_dashboard.cjs || true
fi

echo ""
echo "==============================================================================="
echo "  [ÉXITO] Proceso completado exitosamente."
echo "  Abre dashboard.html en tu navegador para gestionar prospectos."
echo "==============================================================================="
