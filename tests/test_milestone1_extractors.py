"""
test_milestone1_extractors.py
Comprehensive test suite verifying Milestone 1 Data Extraction & Filtering Engine.
"""

import os
import sys
import json
import unittest
from datetime import datetime, date
from urllib.parse import urlparse

# Add scripts directory to path
SCRIPT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, SCRIPT_DIR)

from common_filter import (
    VALID_SUBJECTS,
    VALID_LEVELS,
    TEACHER_BLACKLIST_PATTERNS,
    validate_listing_record,
    validate_url_liveness
)

DATA_JSON_PATH = os.path.join(PROJECT_ROOT, "data", "extracted_listings.json")


class TestMilestone1Extractors(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.assertTrue(os.path.exists(DATA_JSON_PATH), f"Missing data file: {DATA_JSON_PATH}")
        with open(DATA_JSON_PATH, "r", encoding="utf-8") as f:
            cls.listings = json.load(f)

    def test_json_file_structure_and_volume(self):
        """Verify that extracted_listings.json contains an authentic list of listings (>50 records)."""
        self.assertIsInstance(self.listings, list)
        self.assertGreaterEqual(len(self.listings), 50, "Should have extracted at least 50 listings")
        print(f"\n[PASS] Verified {len(self.listings)} records in extracted_listings.json")

    def test_all_records_conform_to_contract(self):
        """Verify 100% of records satisfy the interface contract and schema rules."""
        required_keys = [
            "plataforma", "enlace_anuncio", "materia", "nivel_educativo",
            "pais_ubicacion", "fecha_publicacion", "mensaje_descripcion",
            "metodo_contacto_directo"
        ]
        for idx, rec in enumerate(self.listings, 1):
            for k in required_keys:
                self.assertIn(k, rec, f"Record {idx} missing key '{k}'")
                self.assertTrue(rec[k], f"Record {idx} has empty value for '{k}'")

            is_valid, err = validate_listing_record(rec)
            self.assertTrue(is_valid, f"Record {idx} failed validation: {err}")

    def test_zero_teacher_ad_leakage(self):
        """Verify that absolutely zero teacher advertisements leaked into the dataset."""
        import re
        for idx, rec in enumerate(self.listings, 1):
            msg_lower = rec["mensaje_descripcion"].lower()
            for pattern in TEACHER_BLACKLIST_PATTERNS:
                match = re.search(pattern, msg_lower)
                self.assertIsNone(
                    match,
                    f"Record {idx} ({rec['enlace_anuncio']}) leaked teacher pattern '{pattern}': '{rec['mensaje_descripcion'][:80]}'"
                )

    def test_all_exact_sciences_represented(self):
        """Verify that all four required exact sciences are present in the dataset."""
        all_subjects_found = set()
        for rec in self.listings:
            for s in rec["materia"].split(","):
                all_subjects_found.add(s.strip())

        for required_subj in ["Física", "Química", "Biología", "Matemáticas"]:
            self.assertIn(required_subj, all_subjects_found, f"Missing required exact science: {required_subj}")

    def test_both_educational_levels_represented(self):
        """Verify that both Secundario and Universitario levels are represented."""
        levels = set(r["nivel_educativo"] for r in self.listings)
        self.assertIn("Secundario", levels)
        self.assertIn("Universitario", levels)

    def test_multi_country_coverage(self):
        """Verify representation across Spain and Latin American countries."""
        countries = set(r["pais_ubicacion"].split(" - ")[0] for r in self.listings)
        self.assertIn("España", countries)
        self.assertIn("Argentina", countries)
        # Should also have Mexico or Colombia
        self.assertTrue(any(c in countries for c in ["México", "Colombia"]))

    def test_multi_platform_coverage(self):
        """Verify representation across multiple distinct platforms."""
        platforms = set(r["plataforma"] for r in self.listings)
        self.assertGreaterEqual(len(platforms), 4, f"Expected at least 4 platforms, got: {platforms}")

    @unittest.skipUnless(os.environ.get("RUN_LIVE_TESTS"), "Live HTTP sampling skipped in CI")
    def test_sample_url_liveness(self):
        """Sample check at least 3 live URLs to verify real HTTP 200 liveness and active status."""
        import random
        sample = random.sample(self.listings, min(3, len(self.listings)))
        for rec in sample:
            url = rec["enlace_anuncio"]
            is_live, status, msg = validate_url_liveness(url, timeout=10)
            self.assertTrue(is_live, f"URL liveness check failed for {url}: status={status}, msg={msg}")


if __name__ == "__main__":
    unittest.main()
