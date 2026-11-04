#!/usr/bin/env python3
"""
tests/test_data_persistence.py
Pruebas de integridad, persistencia atómica, tolerancia a fallos y concurrencia.
"""

import os
import sys
import json
import time
import unittest
import tempfile
import threading
from pathlib import Path

# Agregar scripts al path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from storage import (
    FileLock,
    atomic_write_json,
    safe_read_json,
    atomic_write_text,
    merge_crm_tracking,
    compute_stable_id
)

class TestStorageIntegrity(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_atomic_write_and_safe_read_json(self):
        file_path = self.dir_path / "data.json"
        data = [{"id": "item_1", "nombre": "Estudiante A", "materia": "Física"}]
        
        atomic_write_json(str(file_path), data)
        self.assertTrue(file_path.exists())
        
        read_back = safe_read_json(str(file_path))
        self.assertEqual(len(read_back), 1)
        self.assertEqual(read_back[0]["id"], "item_1")

    def test_safe_read_recovers_from_corrupted_file(self):
        file_path = self.dir_path / "dataset.json"
        valid_data = [{"id": "rec_1", "materia": "Química"}]
        
        # 1. Escritura válida (crea .bak)
        atomic_write_json(str(file_path), valid_data)
        bak_file = file_path.with_suffix(".json.bak")
        # Forzar creación de backup con segunda escritura válida
        valid_data_v2 = [{"id": "rec_1", "materia": "Química"}, {"id": "rec_2", "materia": "Álgebra"}]
        atomic_write_json(str(file_path), valid_data_v2)
        self.assertTrue(bak_file.exists())

        # 2. Corromper deliberadamente el archivo principal simulando caída de corriente
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("{ invalid json truncated ...")

        # 3. safe_read_json debe detectar la corrupción y recuperar desde .bak
        recovered = safe_read_json(str(file_path))
        self.assertIsInstance(recovered, list)
        self.assertTrue(len(recovered) >= 1)
        self.assertEqual(recovered[0]["id"], "rec_1")

    def test_file_lock_mutual_exclusion(self):
        lock_file = self.dir_path / "test.lock"
        counter = {"val": 0}

        def worker():
            for _ in range(10):
                with FileLock(str(lock_file), timeout=5.0):
                    curr = counter["val"]
                    time.sleep(0.005)
                    counter["val"] = curr + 1

        t1 = threading.Thread(target=worker)
        t2 = threading.Thread(target=worker)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertEqual(counter["val"], 20)

    def test_merge_crm_tracking_preserves_notes_and_status(self):
        existing = [
            {
                "id": "tc_101",
                "nombre": "Ana M.",
                "estado_contacto": "Contactado",
                "notas_seguimiento": "Prefiere clases por Zoom los sábados a las 10hs",
                "fecha_contacto": "2026-11-02"
            }
        ]
        
        # Nuevos datos provenientes de un re-scrape / re-auditoría
        new_incoming = [
            {
                "id": "tc_101",
                "nombre": "Ana M.",
                "materia": "Matemática",
                "nivel educativo": "Secundario"
            },
            {
                "id": "tc_102",
                "nombre": "Lucas B.",
                "materia": "Física"
            }
        ]

        merged = merge_crm_tracking(new_incoming, existing)
        self.assertEqual(len(merged), 2)
        
        item_101 = next(it for it in merged if it["id"] == "tc_101")
        self.assertEqual(item_101.get("estado_contacto"), "Contactado")
        self.assertEqual(item_101.get("notas_seguimiento"), "Prefiere clases por Zoom los sábados a las 10hs")
        self.assertEqual(item_101.get("fecha_contacto"), "2026-11-02")
        self.assertEqual(item_101.get("materia"), "Matemática")

    def test_compute_stable_id_deterministic(self):
        id1 = compute_stable_id("TusClases", "Juan P.", "2026-11-01", "Busco profesor de análisis matemático")
        id2 = compute_stable_id("TusClases", "Juan P.", "2026-11-01", "Busco profesor de análisis matemático")
        id3 = compute_stable_id("Tablón de Anuncios", "Pedro G.", "2026-11-01", "Busco clases")

        self.assertEqual(id1, id2)
        self.assertNotEqual(id1, id3)
        self.assertTrue(id1.startswith("tc_"))
        self.assertTrue(id3.startswith("tb_"))


if __name__ == "__main__":
    unittest.main()
