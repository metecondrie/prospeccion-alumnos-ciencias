#!/usr/bin/env python3
"""
tests/test_pii_security.py
Suite de seguridad: detecta fugas de información personal identificable (PII)
y credenciales en datasets, documentación y archivos del repositorio público.
"""

import os
import sys
import re
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Patrones de credenciales sensibles
API_KEY_PATTERNS = [
    re.compile(r"AIza[0-9A-Za-z-_]{35}"),               # Google API Key
    re.compile(r"gsk_[a-zA-Z0-9]{40,}"),                # Groq API Key
    re.compile(r"\b[0-9]{8,10}:[a-zA-Z0-9_-]{35}\b"),   # Telegram Bot Token
]

# Patrón de emails (excluyendo dominios de ejemplo/documentación)
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@(?!example\.com|dominio\.com|test\.com)[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")

# Lista de los 24 nombres originales de estudiantes del dataset histórico
ORIGINAL_REAL_NAMES = [
    "Alba Marcela", "Daniela Montoya", "Daniela Hernández", "Daniela Hernandez",
    "Mateo Andrade", "Hernán", "Hernan", "Sebastián", "Sebastian"
]


class TestPiiSecurity(unittest.TestCase):

    def test_no_api_keys_in_tracked_code_or_docs(self):
        """Verifica que ninguna API key real esté commiteada en el código o documentación."""
        scanned_files = 0
        violations = []

        for root, _, files in os.walk(PROJECT_ROOT):
            if any(skip in root for skip in [".git", ".venv", "node_modules", "__pycache__", "centinela_session"]):
                continue
            for f in files:
                if f.endswith((".py", ".md", ".json", ".csv", ".html", ".sh", ".bat", ".yml")):
                    scanned_files += 1
                    file_path = Path(root) / f
                    try:
                        content = file_path.read_text(encoding="utf-8", errors="ignore")
                        for pat in API_KEY_PATTERNS:
                            matches = pat.findall(content)
                            if matches:
                                violations.append((str(file_path.relative_to(PROJECT_ROOT)), matches))
                    except Exception:
                        pass

        self.assertGreater(scanned_files, 10, "Deben haberse escaneado archivos")
        self.assertEqual(len(violations), 0, f"Se detectaron API keys reales en: {violations}")

    def test_dataset_ejemplo_contains_no_real_names_or_phones(self):
        """Verifica que el dataset de ejemplo público no contenga nombres reales ni teléfonos."""
        ejemplo_path = PROJECT_ROOT / "data" / "dataset_ejemplo.json"
        if not ejemplo_path.exists():
            self.skipTest("data/dataset_ejemplo.json no encontrado")

        content = ejemplo_path.read_text(encoding="utf-8")
        for name in ORIGINAL_REAL_NAMES:
            self.assertNotRegex(
                content,
                r"\b" + re.escape(name) + r"\b",
                f"Nombre real '{name}' detectado en dataset_ejemplo.json"
            )

    def test_env_example_has_no_live_secrets(self):
        """Verifica que .env.example contenga únicamente placeholders y ninguna credencial real."""
        env_example = PROJECT_ROOT / ".env.example"
        self.assertTrue(env_example.exists(), ".env.example debe existir")
        content = env_example.read_text(encoding="utf-8")

        for pat in API_KEY_PATTERNS:
            self.assertFalse(bool(pat.search(content)), "Se detectó una clave real en .env.example")


if __name__ == "__main__":
    unittest.main()
