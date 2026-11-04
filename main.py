#!/usr/bin/env python3
"""
main.py
Punto de entrada unificado y multiplataforma (Linux / macOS / Windows)
para el Sistema de Prospección y CRM de Alumnos de Ciencias Exactas.
"""

import os
import sys
import argparse
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_PATH = os.path.join(SCRIPT_DIR, "scripts")
if SCRIPTS_PATH not in sys.path:
    sys.path.insert(0, SCRIPTS_PATH)

from prospector import main as prospector_main

def run_script(script_name, extra_args=None):
    script_file = os.path.join(SCRIPTS_PATH, script_name)
    cmd = [sys.executable, script_file] + (extra_args or [])
    return subprocess.call(cmd)

def main():
    parser = argparse.ArgumentParser(
        description="Sistema de Prospección de Alumnos de Ciencias Exactas - CLI Unificado"
    )
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponibles")

    # Command: run (Pipeline completo de scraping + auditoría + build)
    subparsers.add_parser("run", help="Ejecuta el ciclo completo: extracción web, auditoría IA y compilación")

    # Command: extract
    subparsers.add_parser("extract", help="Ejecuta únicamente la extracción web concurrente")

    # Command: audit
    audit_parser = subparsers.add_parser("audit", help="Ejecuta la auditoría de IA sobre los avisos extraídos")
    audit_parser.add_argument("--model", default="gemini-2.5-flash-lite", help="Modelo principal de IA")

    # Command: build
    subparsers.add_parser("build", help="Compila el dashboard.html y los CSVs a partir de la base de datos auditada")

    # Command: sentinel
    subparsers.add_parser("sentinel", help="Inicia el Centinela de Telegram en tiempo real")

    # Command: join
    subparsers.add_parser("join", help="Conecta a grupos estudiantiles activos con filtro de liveness")

    # Command: test
    subparsers.add_parser("test", help="Ejecuta la suite completa de pruebas unitarias y de integración (pytest)")

    args, unknown = parser.parse_known_args()

    if not args.command or args.command == "run":
        print("--> Ejecutando pipeline completo de prospección...")
        ret = run_script("run_extraction.py")
        if ret == 0:
            sys.argv = ["prospector.py", "audit"] + unknown
            prospector_main()
            sys.argv = ["prospector.py", "build"] + unknown
            prospector_main()
    elif args.command == "extract":
        run_script("run_extraction.py")
    elif args.command == "audit":
        sys.argv = ["prospector.py", "audit"] + unknown
        prospector_main()
    elif args.command == "build":
        sys.argv = ["prospector.py", "build"] + unknown
        prospector_main()
    elif args.command == "sentinel":
        run_script("telegram_centinela.py")
    elif args.command == "join":
        run_script("auto_join_groups.py")
    elif args.command == "test":
        subprocess.call([sys.executable, "-m", "pytest", "tests"])
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
