#!/usr/bin/env bash
# Probar envío de alerta push a Telegram (Linux / macOS)
set -e
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR/.."

PYTHON_CMD=$(command -v python3 || command -v python)
exec $PYTHON_CMD scripts/test_centinela_pipeline.py
