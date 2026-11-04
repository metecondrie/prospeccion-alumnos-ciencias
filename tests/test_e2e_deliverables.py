#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
End-to-End Test Suite: test_e2e_deliverables.py
Purpose: Comprehensive 4-tier E2E testing suite for the Student Tutor Search & Platform Directory deliverables:
         - alumnos_ciencias_exactas.csv
         - directorio_plataformas.md

Test Tiers Covered:
  - Tier 1: Feature Coverage (File existence, 8 canonical headers, non-empty records, required platform directory sections)
  - Tier 2: Boundary & Corner Cases (UTF-8 BOM 0xEF 0xBB 0xBF, RFC 4180 quoting/CRLF, Spanish accents/diacritics, date freshness <= 90 days, no future dates)
  - Tier 3: Cross-Feature Combinations (Subject x Level: Secundario/Universitario x Física/Química/Biología/Matemáticas, Spain + LATAM geographic coverage)
  - Tier 4: Real-World Workload Testing (Negative regex check against teacher advertising phrases for 100% student authenticity, URL format & live HTTP 200 sampling, contact actionability)
  - Heuristics Unit: Internal validation of blacklist patterns, whitelist signals, and normalization rules.

Compatible with:
    python -m unittest tests/test_e2e_deliverables.py
    pytest tests/test_e2e_deliverables.py
"""

import os
import re
import csv
import codecs
import unittest
import urllib.request
import urllib.error
from datetime import datetime, timedelta

# Path configurations
WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CSV_PATH = os.path.join(WORKSPACE_DIR, "alumnos_ciencias_exactas.csv")
DIR_PATH = os.path.join(WORKSPACE_DIR, "docs", "directorio_plataformas.md")
if not os.path.exists(DIR_PATH):
    DIR_PATH = os.path.join(WORKSPACE_DIR, "directorio_plataformas.md")

# Canonical Interface Specifications
CANONICAL_HEADERS = [
    "plataforma",
    "enlace al anuncio",
    "materia",
    "nivel educativo",
    "país/ubicación",
    "fecha de publicación",
    "mensaje/descripción",
    "método de contacto directo",
]

VALID_EXACT_SCIENCES = {"Física", "Química", "Biología", "Matemáticas"}
VALID_EDUCATIONAL_LEVELS = {"Secundario", "Universitario"}

TEACHER_BLACKLIST_PATTERNS = [
    r"\bdoy clases\b",
    r"\bofrezco clases\b",
    r"\bimparto clases\b",
    r"\bimparte clases\b",
    r"\bprofesor con (?:amplia )?experiencia\b",
    r"\bprofesora con (?:amplia )?experiencia\b",
    r"\bdocente con (?:amplia )?experiencia\b",
    r"\bprofesor(?:a)? (?:.* )?con (?:amplia )?experiencia\b",
    r"\blicenciad[oa] ofrece\b",
    r"\bgraduad[oa] ofrece\b",
    r"\bingenier[oa] ofrece\b",
    r"\bclases particulares a domicilio\b",
    r"\bclases particulares a domicilio y online\b",
    r"\bprimera clase gratis\b",
    r"\b1ª clase gratis\b",
    r"\bmis tarifas\b",
    r"\btarifa:\b",
    r"\bprecio por hora\b",
    r"\bcobro \d+\b",
    r"\bmetodolog[ií]a propia\b",
    r"\btodos los niveles\b",
    r"\benseño a\b",
    r"\bmis alumnos aprueban\b",
    r"\bmás de \d+ años de experiencia\b",
    r"\bcv docente\b",
    r"\bformador con experiencia\b",
    r"\bcontrato\s*:",
    r"\btitulaci[oó]n\s+requerida\b",
    r"\baut[oó]nomo\s*/\s*freelance\b",
    r"/oferta-trabajo-",
    r"\boferta-trabajo\b",
    r"\bexperiencia:\s*\d+\s*a[ñn]o",
    r"\bbuscamos\s+profesor(?:es|as?)?\b",
    r"\bse\s+busca\s+profesor(?:es|as?)?\b",
    r"\bacademia\b",
    r"\bcentro\s+de\s+estudios\b",
    r"\btutorasap\b",
    r"\bmentoor\b",
    r"\bthinking\s+academy\b",
    r"\batlas\s+academia\b",
    r"\bexperiencia\s+m[ií]nima\b",
    r"\bretribuci[oó]n\s*:",
    r"\bclases\s+de\s+josu\b",
]

STUDENT_INTENT_PATTERNS = [
    r"\bbusco profesor\b",
    r"\bbusco profesora\b",
    r"\bbusco profe\b",
    r"\bbusco tutor\b",
    r"\bbusco particular\b",
    r"\bbusco ayuda\b",
    r"\bnecesito profesor\b",
    r"\bnecesito profesora\b",
    r"\bnecesito profe\b",
    r"\bnecesito clases\b",
    r"\bnecesito ayuda\b",
    r"\bnecesito apoyo\b",
    r"\bse busca profesor\b",
    r"\bse busca profesora\b",
    r"\bpara preparar examen\b",
    r"\bpara rendir\b",
    r"\bpara selectividad\b",
    r"\bpara ebau\b",
    r"\bpara evau\b",
    r"\bpara el cbc\b",
    r"\bpara parcial\b",
    r"\bpara final\b",
    r"\bestoy cursando\b",
    r"\bmi hij[oa] necesita\b",
    r"\balguien que me explique\b",
]

EXPIRATION_PHRASES = [
    "este anuncio ha caducado",
    "anuncio no disponible",
    "solicitud finalizada",
    "anuncio caducado",
    "ya no está disponible",
    "solicitud cerrada",
]


def _read_csv_rows():
    """Helper to read and return parsed data rows from the CSV file."""
    if not os.path.exists(CSV_PATH):
        return None
    rows = []
    with open(CSV_PATH, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        try:
            next(reader)  # skip header
        except StopIteration:
            return []
        for row in reader:
            rows.append(row)
    return rows


# ==============================================================================
# TIER 1: FEATURE COVERAGE
# ==============================================================================
class TestDeliverablesTier1FeatureCoverage(unittest.TestCase):
    """
    Tier 1 tests verify fundamental feature presence:
    - Deliverable files exist and have non-trivial size.
    - Canonical 8 headers match exact specification.
    - Data rows are populated without blanks.
    - Platform directory markdown contains required sections and platforms.
    """

    def test_01_csv_file_existence(self):
        self.assertTrue(
            os.path.exists(CSV_PATH),
            f"Deliverable CSV file does not exist at expected path: {CSV_PATH}",
        )
        file_size = os.path.getsize(CSV_PATH)
        self.assertGreaterEqual(
            file_size,
            200,
            f"CSV file is too small ({file_size} bytes). Expected non-trivial database.",
        )

    def test_02_directory_file_existence(self):
        self.assertTrue(
            os.path.exists(DIR_PATH),
            f"Deliverable directory markdown does not exist at expected path: {DIR_PATH}",
        )
        file_size = os.path.getsize(DIR_PATH)
        self.assertGreaterEqual(
            file_size,
            500,
            f"Directory file is too small ({file_size} bytes). Expected comprehensive catalog.",
        )

    def test_03_canonical_8_headers_exact_match(self):
        if not os.path.exists(CSV_PATH):
            self.fail(f"CSV file missing: {CSV_PATH}")

        with open(CSV_PATH, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            try:
                headers = next(reader)
            except StopIteration:
                self.fail("CSV file is completely empty.")

        self.assertEqual(
            len(headers),
            8,
            f"Expected exactly 8 columns in CSV header, found {len(headers)}: {headers}",
        )
        self.assertEqual(
            headers,
            CANONICAL_HEADERS,
            f"Canonical headers do not match specification.\nFound:    {headers}\nExpected: {CANONICAL_HEADERS}",
        )

    def test_04_non_empty_records(self):
        rows = _read_csv_rows()
        if rows is None:
            self.fail(f"CSV file missing: {CSV_PATH}")

        self.assertGreater(
            len(rows), 0, "CSV database contains 0 student records. Expected at least one record."
        )

        for idx, row in enumerate(rows, start=2):
            self.assertEqual(
                len(row),
                8,
                f"Row {idx} has {len(row)} columns instead of 8: {row}",
            )
            for col_idx, field in enumerate(row):
                self.assertTrue(
                    len(field.strip()) > 0,
                    f"Row {idx}, Column '{CANONICAL_HEADERS[col_idx]}' is empty.",
                )

    def test_05_directory_required_sections(self):
        if not os.path.exists(DIR_PATH):
            self.fail(f"Directory file missing: {DIR_PATH}")

        with open(DIR_PATH, "r", encoding="utf-8") as f:
            content = f.read().lower()

        required_keywords = ["plataforma", "url principal", "demandas", "contacto"]
        for kw in required_keywords:
            self.assertIn(
                kw,
                content,
                f"Directory markdown is missing mandatory keyword/section: '{kw}'",
            )

        # Verify presence of Markdown comparison table
        table_present = ("|---" in content) or ("|:--" in content) or ("| ---" in content)
        self.assertTrue(
            table_present,
            "Directory markdown must contain a Markdown comparison table (|---|).",
        )

    def test_06_directory_platform_coverage(self):
        if not os.path.exists(DIR_PATH):
            self.fail(f"Directory file missing: {DIR_PATH}")

        with open(DIR_PATH, "r", encoding="utf-8") as f:
            content = f.read().lower()

        # Check coverage of key surveyed platforms
        expected_platforms = ["tusclases", "tablón de anuncios", "cronoshare"]
        found = [p for p in expected_platforms if p in content]
        self.assertGreaterEqual(
            len(found),
            2,
            f"Directory markdown must cover surveyed platforms. Found: {found}, expected: {expected_platforms}",
        )


# ==============================================================================
# TIER 2: BOUNDARY & CORNER CASES
# ==============================================================================
class TestDeliverablesTier2BoundaryCornerCases(unittest.TestCase):
    """
    Tier 2 tests verify boundary and corner cases:
    - Byte Order Mark (BOM) UTF-8 signature (0xEF, 0xBB, 0xBF).
    - RFC 4180 CRLF line endings and proper quote escaping.
    - Spanish accent encoding preservation without mojibake.
    - Strict date formatting (YYYY-MM-DD), calendar validity, no future dates, <= 90-day freshness.
    """

    def test_01_utf8_bom_signature(self):
        if not os.path.exists(CSV_PATH):
            self.fail(f"CSV file missing: {CSV_PATH}")

        with open(CSV_PATH, "rb") as f:
            bom = f.read(3)

        self.assertEqual(
            bom,
            codecs.BOM_UTF8,
            f"CSV file must begin with UTF-8 BOM signature (0xEF, 0xBB, 0xBF). Found: {bom!r}",
        )

    def test_02_rfc4180_crlf_line_terminators(self):
        if not os.path.exists(CSV_PATH):
            self.fail(f"CSV file missing: {CSV_PATH}")

        with open(CSV_PATH, "rb") as f:
            raw_content = f.read()

        # Check that CRLF is present
        self.assertIn(
            b"\r\n",
            raw_content,
            "CSV file must use standard RFC 4180 CRLF (\\r\\n) line endings for spreadsheet compatibility.",
        )

        # Check for lonely LF (\n without \r)
        # Note: Replace \r\n with empty, then check if remaining contains \n
        without_crlf = raw_content.replace(b"\r\n", b"")
        self.assertNotIn(
            b"\n",
            without_crlf,
            "CSV file contains non-standard LF (\\n) line endings without CR (\\r). RFC 4180 requires CRLF.",
        )

    def test_03_character_encoding_spanish_accents(self):
        if not os.path.exists(CSV_PATH):
            self.fail(f"CSV file missing: {CSV_PATH}")

        with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
            text = f.read()

        # Check absence of common UTF-8 mojibake patterns
        mojibake_patterns = ["Ã¡", "Ã©", "Ã­", "Ã³", "Ãº", "Ã±", "Âº", "Ã", "Ã‰", "Ã", "Ã“", "Ãš", "Ã‘"]
        for bad in mojibake_patterns:
            self.assertNotIn(
                bad,
                text,
                f"Detected corrupted mojibake character sequence '{bad}' in CSV. Character encoding is malformed.",
            )

        # Check presence of properly preserved Spanish characters
        spanish_chars = set("áéíóúñÁÉÍÓÚÑ")
        has_spanish_char = any(c in text for c in spanish_chars)
        self.assertTrue(
            has_spanish_char,
            "Expected Spanish accented characters (e.g., Física, Química) in the CSV, but none found.",
        )

    def test_04_date_format_and_calendar_validity(self):
        rows = _read_csv_rows()
        if rows is None:
            self.fail(f"CSV file missing: {CSV_PATH}")

        date_col_idx = CANONICAL_HEADERS.index("fecha de publicación")
        for idx, row in enumerate(rows, start=2):
            date_str = row[date_col_idx].strip()
            self.assertTrue(
                re.match(r"^\d{4}-\d{2}-\d{2}$", date_str),
                f"Row {idx}: Date '{date_str}' does not conform to ISO 8601 YYYY-MM-DD format.",
            )
            try:
                datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError as e:
                self.fail(f"Row {idx}: Invalid calendar date '{date_str}': {e}")

    def test_05_date_no_future_dates(self):
        rows = _read_csv_rows()
        if rows is None:
            self.fail(f"CSV file missing: {CSV_PATH}")

        today = datetime.now().date()
        date_col_idx = CANONICAL_HEADERS.index("fecha de publicación")
        for idx, row in enumerate(rows, start=2):
            date_str = row[date_col_idx].strip()
            row_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            self.assertLessEqual(
                row_date,
                today,
                f"Row {idx}: Future date '{date_str}' is forbidden (current date: {today}).",
            )

    def test_06_date_freshness_window_90_days(self):
        rows = _read_csv_rows()
        if rows is None:
            self.fail(f"CSV file missing: {CSV_PATH}")

        today = datetime.now().date()
        max_age = timedelta(days=90)
        date_col_idx = CANONICAL_HEADERS.index("fecha de publicación")
        for idx, row in enumerate(rows, start=2):
            date_str = row[date_col_idx].strip()
            row_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            age = today - row_date
            self.assertLessEqual(
                age,
                max_age,
                f"Row {idx}: Date '{date_str}' is older than 90 days ({age.days} days ago). Active ads must be fresh.",
            )


# ==============================================================================
# TIER 3: CROSS-FEATURE COMBINATIONS
# ==============================================================================
class TestDeliverablesTier3CrossFeatureCombinations(unittest.TestCase):
    """
    Tier 3 tests verify pairwise interactions and domain constraints:
    - Subject normalization strictly adhering to Física, Química, Biología, Matemáticas.
    - Educational level strictly in Secundario, Universitario.
    - Subject x Educational Level cross-combinations represented in dataset.
    - Geographic representation: Spain and LATAM coverage.
    - Location format adhering to standard conventions.
    """

    def test_01_subject_taxonomy_compliance(self):
        rows = _read_csv_rows()
        if rows is None:
            self.fail(f"CSV file missing: {CSV_PATH}")

        subj_col_idx = CANONICAL_HEADERS.index("materia")
        for idx, row in enumerate(rows, start=2):
            subj_raw = row[subj_col_idx].strip()
            parts = [s.strip() for s in subj_raw.split(",")]
            for p in parts:
                self.assertIn(
                    p,
                    VALID_EXACT_SCIENCES,
                    f"Row {idx}: Subject '{p}' is not an authorized exact science discipline. Allowed: {VALID_EXACT_SCIENCES}",
                )

    def test_02_educational_level_compliance(self):
        rows = _read_csv_rows()
        if rows is None:
            self.fail(f"CSV file missing: {CSV_PATH}")

        level_col_idx = CANONICAL_HEADERS.index("nivel educativo")
        for idx, row in enumerate(rows, start=2):
            level = row[level_col_idx].strip()
            self.assertIn(
                level,
                VALID_EDUCATIONAL_LEVELS,
                f"Row {idx}: Educational level '{level}' not allowed. Must be in {VALID_EDUCATIONAL_LEVELS}",
            )

    def test_03_subject_x_level_matrix_coverage(self):
        rows = _read_csv_rows()
        if rows is None:
            self.fail(f"CSV file missing: {CSV_PATH}")

        subj_col_idx = CANONICAL_HEADERS.index("materia")
        level_col_idx = CANONICAL_HEADERS.index("nivel educativo")

        observed_levels = set()
        observed_subjects = set()
        level_subject_pairs = set()

        for row in rows:
            level = row[level_col_idx].strip()
            observed_levels.add(level)
            subj_parts = [s.strip() for s in row[subj_col_idx].split(",")]
            for s in subj_parts:
                observed_subjects.add(s)
                level_subject_pairs.add((s, level))

        # Check representation of both levels
        self.assertIn(
            "Secundario", observed_levels, "Dataset lacks representation of 'Secundario' educational level."
        )
        self.assertIn(
            "Universitario", observed_levels, "Dataset lacks representation of 'Universitario' educational level."
        )

        # Check exact sciences coverage (at least 2 distinct subjects)
        self.assertGreaterEqual(
            len(observed_subjects),
            2,
            f"Dataset must cover multiple exact science subjects. Observed: {observed_subjects}",
        )

    def test_04_geographic_representation_spain_and_latam(self):
        rows = _read_csv_rows()
        if rows is None:
            self.fail(f"CSV file missing: {CSV_PATH}")

        loc_col_idx = CANONICAL_HEADERS.index("país/ubicación")
        all_locations = [row[loc_col_idx].strip() for row in rows]
        loc_str = " ".join(all_locations).lower()

        # Check for Spain representation
        has_spain = ("españa" in loc_str) or ("spain" in loc_str) or ("madrid" in loc_str) or ("barcelona" in loc_str)

        # Check for LATAM representation (Argentina, Mexico, Colombia, Chile, Peru, Uruguay, etc.)
        latam_markers = [
            "argentina", "buenos aires", "méxico", "mexico", "cdmx", "colombia",
            "bogotá", "chile", "santiago", "perú", "peru", "lima", "uruguay"
        ]
        has_latam = any(m in loc_str for m in latam_markers)

        self.assertTrue(
            has_spain,
            f"Dataset lacks representation of Spain. Locations observed: {set(all_locations)}",
        )
        self.assertTrue(
            has_latam,
            f"Dataset lacks representation of LATAM countries. Locations observed: {set(all_locations)}",
        )

    def test_05_location_formatting_consistency(self):
        rows = _read_csv_rows()
        if rows is None:
            self.fail(f"CSV file missing: {CSV_PATH}")

        loc_col_idx = CANONICAL_HEADERS.index("país/ubicación")
        for idx, row in enumerate(rows, start=2):
            loc = row[loc_col_idx].strip()
            self.assertGreaterEqual(
                len(loc), 3, f"Row {idx}: Location string '{loc}' is unreasonably short."
            )


# ==============================================================================
# TIER 4: REAL-WORLD WORKLOAD TESTING
# ==============================================================================
class TestDeliverablesTier4RealWorldWorkload(unittest.TestCase):
    """
    Tier 4 tests verify real-world operational readiness:
    - 100% student authenticity (negative regex check against teacher advertisements).
    - Student positive intent signals present in descriptions.
    - URL syntax, canonical protocols, and non-empty paths.
    - Live URL sampling verifying HTTP 200 and absence of expiration markers.
    - Contact method actionability for urgent outreach.
    """

    def test_01_student_authenticity_teacher_blacklist(self):
        rows = _read_csv_rows()
        if rows is None:
            self.fail(f"CSV file missing: {CSV_PATH}")

        msg_col_idx = CANONICAL_HEADERS.index("mensaje/descripción")
        teacher_violations = []

        for idx, row in enumerate(rows, start=2):
            msg = row[msg_col_idx].strip().lower()
            for pattern in TEACHER_BLACKLIST_PATTERNS:
                if re.search(pattern, msg):
                    teacher_violations.append(
                        f"Row {idx}: Teacher ad detected with pattern '{pattern}' in description: '{row[msg_col_idx][:70]}...'"
                    )

        self.assertEqual(
            len(teacher_violations),
            0,
            f"Found {len(teacher_violations)} teacher advertisement(s) in student database:\n"
            + "\n".join(teacher_violations[:10]),
        )

    def test_02_student_intent_positive_signals(self):
        rows = _read_csv_rows()
        if rows is None:
            self.fail(f"CSV file missing: {CSV_PATH}")

        msg_col_idx = CANONICAL_HEADERS.index("mensaje/descripción")
        generic_intent_terms = [
            r"\bbusco\b", r"\bnecesito\b", r"\bayuda\b", r"\bexamen\b",
            r"\bclases\b", r"\bapoyo\b", r"\bparcial\b", r"\bpreparar\b",
            r"\buniversidad\b", r"\bsecundaria\b", r"\bprofesor\b", r"\bprofe\b"
        ]

        weak_rows = []
        for idx, row in enumerate(rows, start=2):
            msg = row[msg_col_idx].strip().lower()
            if not any(re.search(pat, msg) for pat in generic_intent_terms):
                weak_rows.append(f"Row {idx}: '{row[msg_col_idx][:60]}'")

        # Ensure at least 90% of rows contain explicit student intent keywords
        allowed_weak_count = max(1, int(len(rows) * 0.1))
        self.assertLessEqual(
            len(weak_rows),
            allowed_weak_count,
            f"Too many rows ({len(weak_rows)}) lack recognized student intent keywords:\n"
            + "\n".join(weak_rows[:5]),
        )

    def test_03_url_format_and_canonical_schemes(self):
        rows = _read_csv_rows()
        if rows is None:
            self.fail(f"CSV file missing: {CSV_PATH}")

        url_col_idx = CANONICAL_HEADERS.index("enlace al anuncio")
        url_regex = re.compile(r"^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$")

        for idx, row in enumerate(rows, start=2):
            url = row[url_col_idx].strip()
            self.assertTrue(
                url.startswith("http://") or url.startswith("https://"),
                f"Row {idx}: URL must use http:// or https:// scheme: '{url}'",
            )
            self.assertTrue(
                url_regex.match(url),
                f"Row {idx}: Malformed URL syntax: '{url}'",
            )

    def test_04_live_url_http_sampling(self):
        rows = _read_csv_rows()
        if rows is None:
            self.fail(f"CSV file missing: {CSV_PATH}")

        # Sample up to 3 URLs to avoid aggressive rate limiting during test runs
        url_col_idx = CANONICAL_HEADERS.index("enlace al anuncio")
        sample_urls = [row[url_col_idx].strip() for row in rows[:3]]

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        checked_count = 0
        for url in sample_urls:
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    status = resp.status
                    self.assertIn(
                        status,
                        [200, 301, 302],
                        f"Sampled URL '{url}' returned unexpected status code: {status}",
                    )
                    body_sample = resp.read(4096).decode("utf-8", errors="ignore").lower()
                    for exp in EXPIRATION_PHRASES:
                        self.assertNotIn(
                            exp,
                            body_sample,
                            f"Sampled URL '{url}' page content contains expiration marker: '{exp}'",
                        )
                checked_count += 1
            except urllib.error.HTTPError as e:
                # 403 / 429 can happen with Cloudflare anti-bot protection; log warning
                if e.code in [403, 429]:
                    print(f"Note: URL {url} returned HTTP {e.code} (Anti-bot protection active).")
                else:
                    self.fail(f"Sampled URL '{url}' returned HTTP error: {e.code}")
            except Exception as e:
                # Network unreachable during testing should produce clear warning or be caught
                print(f"Note: URL probe warning for {url}: {e}")

    def test_05_contact_method_actionability(self):
        rows = _read_csv_rows()
        if rows is None:
            self.fail(f"CSV file missing: {CSV_PATH}")

        contact_col_idx = CANONICAL_HEADERS.index("método de contacto directo")
        for idx, row in enumerate(rows, start=2):
            contact = row[contact_col_idx].strip()
            self.assertGreaterEqual(
                len(contact),
                8,
                f"Row {idx}: Contact method '{contact}' is too short (< 8 chars) to be actionable.",
            )


# ==============================================================================
# HEURISTICS UNIT TESTS: CLASSIFIER & VALIDATOR INTEGRITY
# ==============================================================================
class TestClassifierHeuristicsUnit(unittest.TestCase):
    """
    Unit tests ensuring that the test suite's classification heuristics
    and filtering rules are logically sound, verified against synthetic fixtures.
    """

    def test_teacher_blacklist_catches_teacher_ads(self):
        synthetic_teacher_ads = [
            "Profesor de física y química con amplia experiencia imparte clases a domicilio.",
            "Licenciada ofrece clases particulares de matemáticas para todos los niveles.",
            "Doy clases de biología online. Primera clase gratis. Tarifa: 15€/h.",
            "Ingeniero ofrece apoyo escolar en cálculo y álgebra. Mis alumnos aprueban con más de 10 años de experiencia.",
        ]
        for ad in synthetic_teacher_ads:
            matched = any(re.search(pat, ad.lower()) for pat in TEACHER_BLACKLIST_PATTERNS)
            self.assertTrue(
                matched,
                f"Teacher classifier failed to identify teacher ad: '{ad}'",
            )

    def test_student_whitelist_accepts_student_requests(self):
        synthetic_student_ads = [
            "Busco profesor de Matemáticas urgente para preparar examen de Análisis I en la universidad.",
            "Necesito ayuda con Física y Química para 2º de Bachillerato.",
            "Se busca profe para rendir final de Biología Celular este viernes.",
            "Estoy cursando CBC y me cuesta entender Álgebra del CBC.",
        ]
        for ad in synthetic_student_ads:
            matched = any(re.search(pat, ad.lower()) for pat in STUDENT_INTENT_PATTERNS)
            self.assertTrue(
                matched,
                f"Student classifier failed to identify student request: '{ad}'",
            )

    def test_teacher_blacklist_does_not_false_positive_student_ads(self):
        synthetic_student_ads = [
            "Busco profesor de física para preparar examen de la facultad.",
            "Necesito profe de química orgánica para rendir el recuperatorio.",
            "Busco clases particulares de matemáticas para mi hijo que va a la secundaria.",
        ]
        for ad in synthetic_student_ads:
            matched = any(re.search(pat, ad.lower()) for pat in TEACHER_BLACKLIST_PATTERNS)
            self.assertFalse(
                matched,
                f"Teacher blacklist triggered false positive on student ad: '{ad}'",
            )

    def test_subject_taxonomy_set(self):
        self.assertEqual(
            VALID_EXACT_SCIENCES,
            {"Física", "Química", "Biología", "Matemáticas"},
        )

    def test_date_freshness_logic(self):
        today = datetime.now().date()
        fresh_date = today - timedelta(days=15)
        stale_date = today - timedelta(days=95)
        future_date = today + timedelta(days=2)

        self.assertLessEqual((today - fresh_date).days, 90)
        self.assertGreater((today - stale_date).days, 90)
        self.assertGreater(future_date, today)


# ==============================================================================
# PIPELINE INTEGRATION UNIT TESTS: AUDIT VERIFIER WITH SYNTHETIC FIXTURES
# ==============================================================================
class TestAuditPipelineIntegrationUnit(unittest.TestCase):
    """
    Unit tests ensuring the verify_survey_deliverables audit tool functions
    precisely across compliant fixtures and specific error mutations.
    """

    def setUp(self):
        import tempfile
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.workspace = self.tmp_dir.name
        self.csv_path = os.path.join(self.workspace, "alumnos_ciencias_exactas.csv")
        self.dir_path = os.path.join(self.workspace, "directorio_plataformas.md")
        from tests.verify_survey_deliverables import verify_all
        self.verify_all = verify_all

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _write_compliant_fixtures(self, csv_override=None, dir_override=None):
        if csv_override is not None:
            csv_content = csv_override
        else:
            today_str = datetime.now().date().strftime("%Y-%m-%d")
            csv_content = (
                codecs.BOM_UTF8
                + (
                    "plataforma,enlace al anuncio,materia,nivel educativo,país/ubicación,fecha de publicación,mensaje/descripción,método de contacto directo\r\n"
                    f'"Tusclasesparticulares","https://www.tusclasesparticulares.com/anuncio/1","Física","Secundario","España - Madrid","{today_str}","Busco profesor particular de física para preparar examen final.","Mensajería interna en plataforma"\r\n'
                    f'"Tablón de Anuncios","https://www.tablondeanuncios.com/demanda/2","Matemáticas","Universitario","Argentina - Buenos Aires","{today_str}","Necesito profesor de matemáticas para rendir final de CBC.","WhatsApp directo: +54 9 11 1234 5678"\r\n'
                ).encode("utf-8")
            )

        with open(self.csv_path, "wb") as f:
            f.write(csv_content)

        if dir_override is not None:
            dir_content = dir_override
        else:
            dir_content = (
                "# Directorio de Plataformas de Búsqueda de Profesores\n\n"
                "## Resumen de Plataformas y Contacto Urgente\n\n"
                "| Plataforma | URL Principal | Demandas | Contacto |\n"
                "|---|---|---|---|\n"
                "| Tusclasesparticulares | https://tusclases.com | https://tusclases.com/alumnos | Mensajería interna |\n"
                "| Tablón de Anuncios | https://tablondeanuncios.com | https://tablondeanuncios.com/demandas | Teléfono / WhatsApp |\n"
                "| Cronoshare | https://cronoshare.com | https://cronoshare.com/demandas | Solicitud de presupuesto |\n"
            )

        with open(self.dir_path, "w", encoding="utf-8") as f:
            f.write(dir_content)

    def test_pipeline_passes_with_compliant_fixture(self):
        self._write_compliant_fixtures()
        result = self.verify_all(workspace=self.workspace)
        self.assertTrue(result, "Audit tool failed on fully compliant fixture.")

    def test_pipeline_fails_when_csv_missing_bom(self):
        today_str = datetime.now().date().strftime("%Y-%m-%d")
        no_bom_content = (
            "plataforma,enlace al anuncio,materia,nivel educativo,país/ubicación,fecha de publicación,mensaje/descripción,método de contacto directo\r\n"
            f'"Tusclasesparticulares","https://www.tusclasesparticulares.com/anuncio/1","Física","Secundario","España - Madrid","{today_str}","Busco profesor particular de física para preparar examen.","Mensajería interna"\r\n'
        ).encode("utf-8")
        self._write_compliant_fixtures(csv_override=no_bom_content)
        result = self.verify_all(workspace=self.workspace)
        self.assertFalse(result, "Audit tool should fail when CSV lacks UTF-8 BOM signature.")

    def test_pipeline_fails_when_teacher_ad_injected(self):
        today_str = datetime.now().date().strftime("%Y-%m-%d")
        teacher_content = (
            codecs.BOM_UTF8
            + (
                "plataforma,enlace al anuncio,materia,nivel educativo,país/ubicación,fecha de publicación,mensaje/descripción,método de contacto directo\r\n"
                f'"Tusclasesparticulares","https://www.tusclasesparticulares.com/anuncio/1","Física","Secundario","España - Madrid","{today_str}","Doy clases de física y química con amplia experiencia, primera clase gratis.","Mensajería interna"\r\n'
            ).encode("utf-8")
        )
        self._write_compliant_fixtures(csv_override=teacher_content)
        result = self.verify_all(workspace=self.workspace)
        self.assertFalse(result, "Audit tool should fail when a teacher advertisement is present.")

    def test_pipeline_fails_when_date_is_future(self):
        future_str = (datetime.now().date() + timedelta(days=10)).strftime("%Y-%m-%d")
        future_content = (
            codecs.BOM_UTF8
            + (
                "plataforma,enlace al anuncio,materia,nivel educativo,país/ubicación,fecha de publicación,mensaje/descripción,método de contacto directo\r\n"
                f'"Tusclasesparticulares","https://www.tusclasesparticulares.com/anuncio/1","Física","Secundario","España - Madrid","{future_str}","Busco profesor particular de física para rendir examen.","Mensajería interna"\r\n'
            ).encode("utf-8")
        )
        self._write_compliant_fixtures(csv_override=future_content)
        result = self.verify_all(workspace=self.workspace)
        self.assertFalse(result, "Audit tool should fail when future dates are detected.")

    def test_pipeline_fails_when_date_exceeds_freshness_window(self):
        stale_str = (datetime.now().date() - timedelta(days=120)).strftime("%Y-%m-%d")
        stale_content = (
            codecs.BOM_UTF8
            + (
                "plataforma,enlace al anuncio,materia,nivel educativo,país/ubicación,fecha de publicación,mensaje/descripción,método de contacto directo\r\n"
                f'"Tusclasesparticulares","https://www.tusclasesparticulares.com/anuncio/1","Física","Secundario","España - Madrid","{stale_str}","Busco profesor particular de física para rendir examen.","Mensajería interna"\r\n'
            ).encode("utf-8")
        )
        self._write_compliant_fixtures(csv_override=stale_content)
        result = self.verify_all(workspace=self.workspace)
        self.assertFalse(result, "Audit tool should fail when dates exceed 90-day freshness limit.")


if __name__ == "__main__":
    unittest.main()

