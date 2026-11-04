#!/usr/bin/env python3
"""
tests/test_validate_dataset.py
Pruebas exhaustivas para el validador general de esquemas:
Verifica que el validador acepte datasets de cualquier tamaño N >= 1 (incluyendo +10 nuevos registros),
detecte campos obligatorios faltantes, rechace IDs duplicados y valide URLs.
"""

import unittest
import copy
from validate_dataset import (
    validate_dataset_schema,
    validate_canonical_snapshot,
    MANDATORY_FIELDS
)

SAMPLE_VALID_RECORD = {
    "id": "lead_demo_001",
    "plataforma": "TusClases Argentina",
    "enlace al anuncio": "https://www.tusclases.com.ar/anuncio/demo-01",
    "materia": "Física",
    "nivel educativo": "Universitario",
    "país/ubicación": "Argentina",
    "mensaje/descripción": "Busco profesor particular de física para preparar final de Mecánica.",
    "método de contacto directo": "Mensaje en plataforma",
    "decision_ia": "Aprobado",
    "justificacion_ia": "El usuario es un estudiante que solicita clases de física para preparar examen final."
}


class TestValidateDataset(unittest.TestCase):

    def test_single_valid_record_passes(self):
        data = [copy.deepcopy(SAMPLE_VALID_RECORD)]
        stats = validate_dataset_schema(data)
        self.assertEqual(stats["total_records"], 1)
        self.assertEqual(stats["unique_ids"], 1)

    def test_incremental_dataset_with_10_new_students_passes(self):
        """Aceptación explícita: incorporar 10 nuevos alumnos válidos no rompe las pruebas."""
        base_records = [copy.deepcopy(SAMPLE_VALID_RECORD) for _ in range(5)]
        for i, r in enumerate(base_records):
            r["id"] = f"lead_base_{i}"
            r["enlace al anuncio"] = f"https://www.tusclases.com.ar/anuncio/base-{i}"

        # Agregar 10 nuevos alumnos válidos
        for i in range(10):
            new_student = copy.deepcopy(SAMPLE_VALID_RECORD)
            new_student["id"] = f"lead_incremental_{i}"
            new_student["enlace al anuncio"] = f"https://www.tablondeanuncios.com/anuncio/inc-{i}"
            new_student["materia"] = "Matemáticas" if i % 2 == 0 else "Química"
            base_records.append(new_student)

        self.assertEqual(len(base_records), 15)
        stats = validate_dataset_schema(base_records)
        self.assertEqual(stats["total_records"], 15)
        self.assertEqual(stats["unique_ids"], 15)

    def test_empty_dataset_raises_assertion(self):
        with self.assertRaises(AssertionError) as ctx:
            validate_dataset_schema([])
        self.assertIn("vacío", str(ctx.exception))

    def test_duplicate_id_raises_assertion(self):
        rec1 = copy.deepcopy(SAMPLE_VALID_RECORD)
        rec2 = copy.deepcopy(SAMPLE_VALID_RECORD)
        rec2["enlace al anuncio"] = "https://www.tusclases.com.ar/anuncio/demo-02"
        # Mismo ID 'lead_demo_001'
        with self.assertRaises(AssertionError) as ctx:
            validate_dataset_schema([rec1, rec2])
        self.assertIn("duplicados", str(ctx.exception))

    def test_missing_mandatory_field_raises_assertion(self):
        for field in MANDATORY_FIELDS:
            rec = copy.deepcopy(SAMPLE_VALID_RECORD)
            rec[field] = ""  # Vaciar campo obligatorio
            with self.assertRaises(AssertionError) as ctx:
                validate_dataset_schema([rec])
            self.assertIn(field, str(ctx.exception))

    def test_malformed_url_raises_assertion(self):
        rec = copy.deepcopy(SAMPLE_VALID_RECORD)
        rec["enlace al anuncio"] = "invalid_protocol://no-domain"
        with self.assertRaises(AssertionError) as ctx:
            validate_dataset_schema([rec])
        self.assertIn("URL inválida", str(ctx.exception))

    def test_too_short_message_raises_assertion(self):
        rec = copy.deepcopy(SAMPLE_VALID_RECORD)
        rec["mensaje/descripción"] = "hola"
        with self.assertRaises(AssertionError) as ctx:
            validate_dataset_schema([rec])
        self.assertIn("demasiado corto", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
