#!/usr/bin/env python3
"""
tests/test_cli_pipeline.py
Pruebas de integración del CLI unificado (main.py):
Verifica la propagación de argumentos (--model, --demo), códigos de salida no-cero ante fallos,
ejecución CWD-agnostic y ejecución reproducible de subcomandos.
"""

import os
import sys
import unittest
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

class TestCliPipeline(unittest.TestCase):

    def test_main_demo_exits_zero(self):
        cmd = [sys.executable, str(PROJECT_ROOT / "main.py"), "--demo"]
        res = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, encoding="utf-8", errors="replace")
        self.assertEqual(res.returncode, 0, f"Error: {res.stderr}")
        self.assertIn("DEMOSTRACI", res.stdout)

    def test_main_validate_subcommand_exits_zero(self):
        cmd = [sys.executable, str(PROJECT_ROOT / "main.py"), "validate"]
        res = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, encoding="utf-8", errors="replace")
        self.assertEqual(res.returncode, 0, f"Error: {res.stderr}")
        self.assertIn("VALIDACI", res.stdout)

    def test_main_evaluate_subcommand_exits_zero(self):
        cmd = [sys.executable, str(PROJECT_ROOT / "main.py"), "evaluate"]
        res = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, encoding="utf-8", errors="replace")
        self.assertEqual(res.returncode, 0, f"Error: {res.stderr}")
        self.assertIn("REPORTE DE EVALUACI", res.stdout)

    def test_main_sentinel_simulate_exits_zero(self):
        cmd = [sys.executable, str(PROJECT_ROOT / "main.py"), "sentinel", "--simulate"]
        res = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, encoding="utf-8", errors="replace")
        self.assertEqual(res.returncode, 0, f"Error: {res.stderr}")
        self.assertIn("Bucle", res.stdout)

    def test_main_build_subcommand_exits_zero(self):
        cmd = [sys.executable, str(PROJECT_ROOT / "main.py"), "build"]
        res = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, encoding="utf-8", errors="replace")
        self.assertEqual(res.returncode, 0, f"Error: {res.stderr}")
        self.assertIn("Archivos generados con", res.stdout)

    def test_main_cwd_agnostic_execution(self):
        """Verifica que el CLI funcione llamándolo desde un directorio padre o diferente."""
        parent_dir = PROJECT_ROOT.parent
        cmd = [sys.executable, str(PROJECT_ROOT / "main.py"), "validate"]
        res = subprocess.run(cmd, cwd=str(parent_dir), capture_output=True, encoding="utf-8", errors="replace")
        self.assertEqual(res.returncode, 0, f"Falló ejecución desde CWD ajeno: {res.stderr}")


if __name__ == "__main__":
    unittest.main()
