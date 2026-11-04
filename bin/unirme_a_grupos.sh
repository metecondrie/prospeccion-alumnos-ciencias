#!/usr/bin/env bash
# Unirse a grupos de estudiantes públicos configurados (Linux / macOS)
set -e
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR/.."

PYTHON_CMD=$(command -v python3 || command -v python)
exec $PYTHON_CMD scripts/auto_join_groups.py
