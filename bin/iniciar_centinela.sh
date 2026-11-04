#!/usr/bin/env bash
# Iniciar Daemon Centinela de Telegram en tiempo real (Linux / macOS)
set -e
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR/.."

PYTHON_CMD=$(command -v python3 || command -v python)
echo "Iniciando Centinela de Telegram en tiempo real..."
exec $PYTHON_CMD scripts/telegram_centinela.py
