#!/usr/bin/env python3
"""
main.py
Punto de entrada unificado y multiplataforma (Linux / macOS / Windows)
para el Sistema de Prospección y CRM de Alumnos de Ciencias Exactas.
Garantiza ejecución desde cualquier directorio de trabajo (CWD-agnostic),
propagación correcta de flags (--model, --demo), y códigos de salida no-cero ante fallos.
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path

# Directorio raíz del proyecto
PROJECT_ROOT = Path(__file__).resolve().parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
DATA_DIR = PROJECT_ROOT / "data"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from prospector import cmd_audit, cmd_build, cmd_run, load_env_file
import validate_dataset

load_env_file()


def run_demo_pipeline():
    """
    Modo demostración completamente offline:
    Ejecuta el ciclo de extracción sintética, clasificación determinista y compilación
    del CRM sin requerir API keys ni conexión de red.
    """
    print("==================================================")
    print("EJECUTANDO MODO DEMOSTRACIÓN (OFFLINE / 0 LLAMADAS EXTERNAS)")
    print("==================================================")
    
    demo_raw = DATA_DIR / "dataset_ejemplo.json"
    if not demo_raw.exists():
        demo_raw = DATA_DIR / "extracted_listings.json"

    # Argumentos para auditar en modo demo
    audit_args = argparse.Namespace(
        input=str(demo_raw),
        output_approved=str(DATA_DIR / "dataset_canonico_auditado.json"),
        output_discarded=str(DATA_DIR / "descartados_auditoria.json"),
        model="gemini-3.5-flash",
        batch_size=10,
        api_key=None
    )

    print("-> Paso 1/2: Auditoría heurística determinista offline...")
    cmd_audit(audit_args)

    print("-> Paso 2/2: Compilando CRM y planillas CSV...")
    build_args = argparse.Namespace(
        approved=str(DATA_DIR / "dataset_canonico_auditado.json"),
        discarded=str(DATA_DIR / "descartados_auditoria.json"),
        output_html=str(PROJECT_ROOT / "dashboard.html"),
        output_csv=str(PROJECT_ROOT / "alumnos_ciencias_exactas.csv"),
        desktop_sync=False
    )
    cmd_build(build_args)

    print("==================================================")
    print("✅ DEMOSTRACIÓN COMPLETADA CON ÉXITO")
    print(f"  Abra {PROJECT_ROOT / 'dashboard.html'} en cualquier navegador.")
    print("==================================================")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Sistema de Prospección de Alumnos de Ciencias Exactas - CLI Unificado"
    )
    parser.add_argument("--demo", action="store_true", help="Ejecuta en modo demo offline sin API keys ni red")
    
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponibles")

    # Command: run (Pipeline completo)
    p_run = subparsers.add_parser("run", help="Ejecuta el ciclo completo: extracción web, auditoría IA y compilación")
    p_run.add_argument("--model", default="gemini-3.5-flash", help="Modelo principal de IA (ej: gemini-3.5-flash)")
    p_run.add_argument("--batch-size", type=int, default=10, help="Tamaño de lote para la API")
    p_run.add_argument("--api-key", default=None, help="Clave API opcional")
    p_run.add_argument("--desktop-sync", action="store_true", help="Sincroniza en directorio secundario")
    p_run.add_argument("--demo", action="store_true", help="Modo demo offline")

    # Command: extract
    p_extract = subparsers.add_parser("extract", help="Ejecuta la extracción web concurrente")
    p_extract.add_argument("--demo", action="store_true", help="Extracción simulada sin llamadas HTTP")

    # Command: audit
    p_audit = subparsers.add_parser("audit", help="Ejecuta la auditoría de IA sobre anuncios extraídos")
    p_audit.add_argument("--input", default=str(DATA_DIR / "extracted_listings.json"))
    p_audit.add_argument("--output-approved", default=str(DATA_DIR / "dataset_canonico_auditado.json"))
    p_audit.add_argument("--output-discarded", default=str(DATA_DIR / "descartados_auditoria.json"))
    p_audit.add_argument("--model", default="gemini-3.5-flash", help="Modelo de IA")
    p_audit.add_argument("--batch-size", type=int, default=10)
    p_audit.add_argument("--api-key", default=None)
    p_audit.add_argument("--demo", action="store_true")

    # Command: build
    p_build = subparsers.add_parser("build", help="Compila dashboard.html y CSVs a partir de la base de datos")
    p_build.add_argument("--approved", default=str(DATA_DIR / "dataset_canonico_auditado.json"))
    p_build.add_argument("--discarded", default=str(DATA_DIR / "descartados_auditoria.json"))
    p_build.add_argument("--output-html", default=str(PROJECT_ROOT / "dashboard.html"))
    p_build.add_argument("--output-csv", default=str(PROJECT_ROOT / "alumnos_ciencias_exactas.csv"))
    p_build.add_argument("--desktop-sync", action="store_true")

    # Command: sentinel
    p_sentinel = subparsers.add_parser("sentinel", help="Inicia el Centinela de Telegram en tiempo real")
    p_sentinel.add_argument("--simulate", action="store_true", help="Ejecuta una prueba simulada de la cola y alertas")
    p_sentinel.add_argument("--test-mode", action="store_true")

    # Command: test
    p_test = subparsers.add_parser("test", help="Ejecuta la suite completa de pruebas automatizadas")
    p_test.add_argument("-v", "--verbose", action="store_true", help="Modo detallado")

    # Command: validate
    p_val = subparsers.add_parser("validate", help="Valida la integridad y esquema del dataset")
    p_val.add_argument("--snapshot", action="store_true", help="Verifica también el snapshot histórico estricto")

    # Command: evaluate
    subparsers.add_parser("evaluate", help="Ejecuta el benchmark de evaluación de Machine Learning")

    args = parser.parse_args()

    # Si se pide flag global --demo
    if getattr(args, "demo", False):
        return run_demo_pipeline()

    if not args.command or args.command == "run":
        if getattr(args, "demo", False):
            return run_demo_pipeline()

        print("--> Iniciando pipeline de prospección...")
        raw_path = DATA_DIR / "extracted_listings.json"
        if not raw_path.exists():
            print("-> data/extracted_listings.json no encontrado. Iniciando extracción web...")
            ret = subprocess.call([sys.executable, str(SCRIPTS_DIR / "run_extraction.py")], cwd=str(PROJECT_ROOT))
            if ret != 0:
                print(f"[ERROR] La extracción falló con código de salida: {ret}", file=sys.stderr)
                return ret

        audit_args = argparse.Namespace(
            input=str(raw_path),
            output_approved=str(DATA_DIR / "dataset_canonico_auditado.json"),
            output_discarded=str(DATA_DIR / "descartados_auditoria.json"),
            model=getattr(args, "model", "gemini-3.5-flash"),
            batch_size=getattr(args, "batch_size", 10),
            api_key=getattr(args, "api_key", None)
        )
        cmd_audit(audit_args)

        build_args = argparse.Namespace(
            approved=str(DATA_DIR / "dataset_canonico_auditado.json"),
            discarded=str(DATA_DIR / "descartados_auditoria.json"),
            output_html=str(PROJECT_ROOT / "dashboard.html"),
            output_csv=str(PROJECT_ROOT / "alumnos_ciencias_exactas.csv"),
            desktop_sync=getattr(args, "desktop_sync", False)
        )
        cmd_build(build_args)
        return 0

    elif args.command == "extract":
        ret = subprocess.call([sys.executable, str(SCRIPTS_DIR / "run_extraction.py")], cwd=str(PROJECT_ROOT))
        return ret

    elif args.command == "audit":
        audit_args = argparse.Namespace(
            input=args.input,
            output_approved=args.output_approved,
            output_discarded=args.output_discarded,
            model=args.model,
            batch_size=args.batch_size,
            api_key=args.api_key
        )
        cmd_audit(audit_args)
        return 0

    elif args.command == "build":
        cmd_build(args)
        return 0

    elif args.command == "sentinel":
        sentinel_cmd = [sys.executable, str(SCRIPTS_DIR / "telegram_centinela.py")]
        if args.simulate:
            sentinel_cmd.append("--simulate")
        if args.test_mode:
            sentinel_cmd.append("--test-mode")
        return subprocess.call(sentinel_cmd, cwd=str(PROJECT_ROOT))

    elif args.command == "test":
        unittest_cmd = [sys.executable, "-m", "unittest", "discover", "-s", "tests"]
        if getattr(args, "verbose", False):
            unittest_cmd.append("-v")
        ret1 = subprocess.call(unittest_cmd, cwd=str(PROJECT_ROOT))
        if ret1 != 0:
            return ret1

        node_cmd = ["node", str(PROJECT_ROOT / "tests" / "check_dashboard.cjs")]
        ret2 = subprocess.call(node_cmd, cwd=str(PROJECT_ROOT))
        return ret2

    elif args.command == "validate":
        ok = validate_dataset.run_validation(
            data_path=str(DATA_DIR / "dataset_canonico_auditado.json"),
            raw_path=str(DATA_DIR / "extracted_listings.json"),
            strict_snapshot=args.snapshot
        )
        return 0 if ok else 1

    elif args.command == "evaluate":
        eval_script = PROJECT_ROOT / "evaluation" / "evaluar_clasificadores.py"
        return subprocess.call([sys.executable, str(eval_script)], cwd=str(PROJECT_ROOT))

    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code or 0)
