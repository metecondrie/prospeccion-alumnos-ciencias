#!/usr/bin/env python3
"""
tests/test_pii_security.py
Suite de seguridad: detecta fugas de información personal identificable (PII)
y credenciales en datasets, documentación y archivos del repositorio público.
"""

import os
import sys
import re
import hashlib
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

# Hashes SHA-256 de nombres originales para auditoría ciega de privacidad sin exponer PII
FORBIDDEN_NAME_HASHES = {
    "a953e6c34b6871f9481523e302e78b343f9aa7394370afbfc35455ae9d0ae4e7",
    "a93991200ee4a2de3e1d7ddb6a4d218c3e4069d9d4c4c347a9897b4472ededbe",
    "c9176f204b1c6e7eef80e5f575c6398dccffac9909b111a4a9d279f2b481e3ae",
    "813c24889530d746fdb8941722ff8431bfbbbbe9e52ac9c3297ccf90a65336f2",
    "718c4908545eef5dddda9848f1293979819b3378f85276f8e159c5d15b5f4214",
    "6bc97be98f6fdb38c91a399171e97fa2a3d8edf918bf209bef0269c8676cf041",
    "099c3231aa0d0d61b796bb35e0c096bcdd633a41ba62570ff5b7f98ecf92a278",
    "8334189876be0d2ef800371ca423cff695a53df472dc05e3a1a52fac867a4670",
    "db0284fc80b4881fa545953441a21958470c49d73508714a84a259cb62a5dbb5",
    "ee6aa9381e07c60412e8bca2932326f413828ccabca7b96380b4170f7e704605",
    "3e6b74c49ac4235996c8c207db3b7bce963f29380e9dcc46dc0fed04b75fe3cc",
    "253387e8620ee1896c76809782406e139bce35860aaa0d61991965319ba0dc32",
    "6cc61e6e49ab38053f9c3df1ba795a7229332ff783e7dbc12232bfe6d34d83b1",
    "80d161545383dd77c8703ec50d566ae19f9f6bb5b68b42b26482f1cdf21bf8f2",
    "0c3392045342bf3019bf8eedb0a7c015d0e33772cc21c6ef533ccb1ceddbd77b",
    "0c030df5a4e7477d218012c0121ebce6d61bb8dc46e0a6c4f8e1cc8091b946a5",
    "ace2008b98c1980f9df9a009b38a80652a0dee2ffab3406090cf77e788fe18af",
    "2db7a0c30b879e153450129605fc826cee1db5d4df9d5ead38b81fb7f5935dc8",
    "e7d36336232ab24b6c522a8614d0f23a9861b95fdfed7edd0a7fc0a9358d8fb0",
    "a81ef43a50006221a2810a2de453541cc7c6a0084df970a7e35b2f7b3717cda8",
    "c04bc8058a898b568913ca6a8187624e9f15167c32c7019e9712ab694f90752f",
    "8272dcce0d7192d4599a7ee498066f8e7c36dcffe1a7c70f15854fd228fdfa25",
    "006e3a93b8f63344095bc538966c67539282df6d4f566ccff5d983acb0c18be8",
    "240cca8d7560bceea72e5709ff401a198d240a43b3a0c2ef8a79edc0d29bbf31",
    "d179191d1c83b81f3d2c2671b7a3a317a668408edfbd689ad906c2b380d35614",
    "5ad4a23bc13eaf92e9c035b1d3edbb92582a99f2dbe64525009755f989eedfb2",
    "c09213cf20b32fe2436b92ded92caeed5d938b454c0cd94fea66658823c812b3",
    "c7a11e9a55de2b146e3b2d75e9112ee6af4e5b439658e725e6afca92e93bf0bd",
}


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
        """Verifica que el dataset de ejemplo público no contenga nombres reales ni teléfonos (vía SHA-256)."""
        ejemplo_path = PROJECT_ROOT / "data" / "dataset_ejemplo.json"
        if not ejemplo_path.exists():
            self.skipTest("data/dataset_ejemplo.json no encontrado")

        content = ejemplo_path.read_text(encoding="utf-8")
        tokens = re.findall(r"\b[\wáéíóúÁÉÍÓÚñÑ]+\b", content)
        for i in range(len(tokens)):
            h1 = hashlib.sha256(tokens[i].encode("utf-8")).hexdigest()
            self.assertNotIn(h1, FORBIDDEN_NAME_HASHES, f"Token sensible detectado en {ejemplo_path.name}")
            if i + 1 < len(tokens):
                bigram = f"{tokens[i]} {tokens[i+1]}"
                h2 = hashlib.sha256(bigram.encode("utf-8")).hexdigest()
                self.assertNotIn(h2, FORBIDDEN_NAME_HASHES, f"Bigrama sensible detectado en {ejemplo_path.name}")

    def test_env_example_has_no_live_secrets(self):
        """Verifica que .env.example contenga únicamente placeholders y ninguna credencial real."""
        env_example = PROJECT_ROOT / ".env.example"
        self.assertTrue(env_example.exists(), ".env.example debe existir")
        content = env_example.read_text(encoding="utf-8")

        for pat in API_KEY_PATTERNS:
            self.assertFalse(bool(pat.search(content)), "Se detectó una clave real en .env.example")


if __name__ == "__main__":
    unittest.main()
