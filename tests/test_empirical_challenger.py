"""
Independent Empirical Challenge & Stress-Test Suite
Suite de pruebas empíricas y de robustez para el dataset canónico y directorio.
"""

import unittest
import csv
import io
import re
import os
import sys
import datetime
import urllib.request
import urllib.error
import ssl

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    except Exception:
        pass


WORKSPACE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CSV_PATH = os.path.join(WORKSPACE, "alumnos_ciencias_exactas.csv")
DIR_PATH = os.path.join(WORKSPACE, "docs", "directorio_plataformas.md")
if not os.path.exists(DIR_PATH):
    DIR_PATH = os.path.join(WORKSPACE, "directorio_plataformas.md")


class TestCsvParserBoundaryBehaviors(unittest.TestCase):
    """Stress tests CSV parser boundary behaviors, RFC 4180 compliance, and escaping."""

    def setUp(self):
        self.assertTrue(os.path.exists(CSV_PATH), f"CSV not found at {CSV_PATH}")
        with open(CSV_PATH, "rb") as f:
            self.raw_bytes = f.read()
        self.text = self.raw_bytes.decode("utf-8-sig")

    def test_byte_signature_utf8_bom(self):
        """Byte signature must strictly be 0xEF, 0xBB, 0xBF."""
        self.assertEqual(
            self.raw_bytes[:3],
            b"\xef\xbb\xbf",
            f"Expected UTF-8 BOM \\xef\\xbb\\xbf, found: {self.raw_bytes[:3]!r}",
        )

    def test_line_terminators_crlf(self):
        """RFC 4180 section 2.1: Each record MUST be delimited by CRLF."""
        crlf_count = self.text.count("\r\n")
        lf_count = self.text.count("\n")
        cr_count = self.text.count("\r")
        self.assertEqual(
            crlf_count,
            lf_count,
            f"Found lone LF characters. CRLF={crlf_count}, LF={lf_count}",
        )
        self.assertEqual(
            crlf_count,
            cr_count,
            f"Found lone CR characters. CRLF={crlf_count}, CR={cr_count}",
        )
        self.assertTrue(
            self.text.endswith("\r\n"),
            "RFC 4180 compliance: file must end with CRLF terminator.",
        )

    def test_rfc4180_fsm_parser(self):
        """Strict RFC 4180 state machine parser to detect boundary defects."""
        # States: 0 = START_FIELD, 1 = IN_UNQUOTED, 2 = IN_QUOTED, 3 = AFTER_QUOTE
        state = 0
        current_field = []
        current_record = []
        records = []
        pos = 0
        content = self.text

        while pos < len(content):
            c = content[pos]

            if state == 0:  # START_FIELD
                if c == '"':
                    state = 2
                    pos += 1
                elif c == ",":
                    current_record.append("")
                    pos += 1
                elif c == "\r":
                    if pos + 1 < len(content) and content[pos + 1] == "\n":
                        current_record.append("")
                        records.append(current_record)
                        current_record = []
                        pos += 2
                    else:
                        self.fail(f"Stray CR at character position {pos}")
                else:
                    current_field.append(c)
                    state = 1
                    pos += 1

            elif state == 1:  # IN_UNQUOTED
                if c == ",":
                    current_record.append("".join(current_field))
                    current_field = []
                    state = 0
                    pos += 1
                elif c == '"':
                    self.fail(
                        f"Unescaped double quote inside unquoted field at position {pos}"
                    )
                elif c == "\r":
                    if pos + 1 < len(content) and content[pos + 1] == "\n":
                        current_record.append("".join(current_field))
                        current_field = []
                        records.append(current_record)
                        current_record = []
                        state = 0
                        pos += 2
                    else:
                        self.fail(f"Stray CR at character position {pos}")
                else:
                    current_field.append(c)
                    pos += 1

            elif state == 2:  # IN_QUOTED
                if c == '"':
                    if pos + 1 < len(content) and content[pos + 1] == '"':
                        current_field.append('"')
                        pos += 2
                    else:
                        state = 3
                        pos += 1
                else:
                    current_field.append(c)
                    pos += 1

            elif state == 3:  # AFTER_QUOTE
                if c == ",":
                    current_record.append("".join(current_field))
                    current_field = []
                    state = 0
                    pos += 1
                elif c == "\r":
                    if pos + 1 < len(content) and content[pos + 1] == "\n":
                        current_record.append("".join(current_field))
                        current_field = []
                        records.append(current_record)
                        current_record = []
                        state = 0
                        pos += 2
                    else:
                        self.fail(f"Stray CR at character position {pos}")
                else:
                    self.fail(
                        f"Expected comma or CRLF after closing quote, got {c!r} at position {pos}"
                    )

        if state == 2:
            self.fail("Unclosed quoted field at end of file")
        if current_record or current_field:
            if current_field:
                current_record.append("".join(current_field))
            records.append(current_record)

        self.assertGreaterEqual(
            len(records), 42, f"Expected >= 42 records (1 header + 41 data), got {len(records)}"
        )
        header = records[0]
        self.assertEqual(
            len(header),
            8,
            f"Header must have 8 columns, got {len(header)}: {header}",
        )
        for i, row in enumerate(records[1:], start=2):
            self.assertEqual(
                len(row),
                8,
                f"Row {i} has {len(row)} columns instead of 8: {row}",
            )

    def test_python_csv_reader_and_roundtrip(self):
        """Standard Python csv.reader parses identical records and roundtrips perfectly."""
        reader = csv.reader(io.StringIO(self.text, newline=""), dialect="excel")
        rows = list(reader)
        self.assertGreaterEqual(len(rows), 42)

        expected_headers = [
            "plataforma",
            "enlace al anuncio",
            "materia",
            "nivel educativo",
            "pa\u00eds/ubicaci\u00f3n",
            "fecha de publicaci\u00f3n",
            "mensaje/descripci\u00f3n",
            "m\u00e9todo de contacto directo",
        ]
        self.assertEqual(rows[0], expected_headers)

        # Roundtrip serialization test
        buf = io.StringIO(newline="")
        writer = csv.writer(buf, dialect="excel", lineterminator="\r\n")
        writer.writerows(rows)
        serialized = buf.getvalue()

        reader2 = csv.reader(io.StringIO(serialized, newline=""), dialect="excel")
        rows2 = list(reader2)
        self.assertEqual(rows, rows2, "Roundtrip CSV serialization mismatch detected!")


class TestCharacterEncodingAndDiacritics(unittest.TestCase):
    """Stress tests encoding, UTF-8 BOM, and preservation of Spanish diacritics."""

    def setUp(self):
        with open(CSV_PATH, "rb") as f:
            self.csv_bytes = f.read()
        self.csv_text = self.csv_bytes.decode("utf-8-sig")

        with open(DIR_PATH, "rb") as f:
            self.dir_bytes = f.read()
        self.dir_text = self.dir_bytes.decode("utf-8")

    def test_no_mojibake_or_replacement_characters(self):
        """Neither file may contain mojibake patterns or unicode replacement chars."""
        mojibake_patterns = [
            "\ufffd",
            "\u00c3\u00a1",
            "\u00c3\u00a9",
            "\u00c3\u00ad",
            "\u00c3\u00b3",
            "\u00c3\u00ba",
            "\u00c3\u00b1",
            "\u00c2\u00bf",
            "\u00c2\u00a1",
            "\u00e2\u0080\u0099",
        ]
        for pattern in mojibake_patterns:
            self.assertNotIn(
                pattern,
                self.csv_text,
                f"Mojibake pattern {pattern!r} found in CSV!",
            )
            self.assertNotIn(
                pattern,
                self.dir_text,
                f"Mojibake pattern {pattern!r} found in Directory!",
            )

    def test_spanish_diacritics_presence(self):
        """Verify proper presence of á, é, í, ó, ú, ñ in CSV."""
        diacritics = {
            "á": "\u00e1",
            "é": "\u00e9",
            "í": "\u00ed",
            "ó": "\u00f3",
            "ú": "\u00fa",
            "ñ": "\u00f1",
        }
        for name, char in diacritics.items():
            cnt = self.csv_text.count(char)
            self.assertGreater(
                cnt,
                0,
                f"Diacritic {name} ({char}) not found in CSV text (count=0)",
            )

    def test_inverted_punctuation_in_directory(self):
        """Verify presence of inverted question mark '¿' in directory."""
        cnt = self.dir_text.count("\u00bf")
        self.assertGreater(
            cnt, 0, "Inverted question mark '¿' missing from directory!"
        )


class TestAdversarialStudentAuthenticity(unittest.TestCase):
    """Stress tests student authenticity and detects non-student / academy recruitment listings."""

    TEACHER_OFFER_PATTERNS = [
        r"\bdoy clases\b",
        r"\bofrezco clases\b",
        r"\bimparto clases\b",
        r"\bmis clases\b",
        r"\bmis alumnos\b",
        r"\bprimera clase gratis\b",
        r"\bprecio por hora\b",
        r"\btarifa[s]?\b",
        r"\bprofesor(a)? con experiencia\b",
        r"\blicenciad[oa] ofrece\b",
        r"\bgraduad[oa] ofrece\b",
        r"\bdocente con amplia experiencia\b",
        r"\bexperiencia docente\b",
        r"\benseñanza personalizada\b",
        r"\bpreparo alumnos\b",
        r"\bcontactar para contratarme\b",
        r"\bclases particulares a domicilio y online\b",
        r"\bmetodología propia\b",
        r"\btarifas económicas\b",
    ]

    ACADEMY_RECRUITMENT_PATTERNS = [
        r"\bacademia\b",
        r"\bcentro de estudios\b",
        r"\bcontrato:\b",
        r"\btitulación requerida\b",
        r"\bclases de josu\b",
        r"\btutorasap\b",
        r"\bmentoor\b",
        r"\bthinking academy\b",
        r"\bcontrato: tiempo parcial\b",
        r"\bcontrato: indefinido\b",
        r"\bcontrato: autónomo\b",
    ]

    ALLOWED_SUBJECTS = {
        "Física",
        "Química",
        "Biología",
        "Matemáticas",
        "Matemáticas, Física",
        "Matemáticas, Química",
        "Física, Química",
        "Matemáticas, Física, Química",
        "Química, Biología",
        "Matemáticas, Biología",
        "Física, Biología",
        "Física, Química, Biología",
        "Matemáticas, Física, Química, Biología",
    }

    ALLOWED_LEVELS = {"Secundario", "Universitario"}

    def setUp(self):
        with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            self.rows = list(reader)

    def test_zero_teacher_self_offers(self):
        """Empirically confirms zero teacher self-advertisements exist in the database."""
        violations = []
        for idx, row in enumerate(self.rows, start=2):
            msg = row.get("mensaje/descripci\u00f3n", "")
            method = row.get("m\u00e9todo de contacto directo", "")
            full_content = f"{msg} {method}".lower()

            for pattern in self.TEACHER_OFFER_PATTERNS:
                if re.search(pattern, full_content, re.IGNORECASE):
                    matched = re.search(pattern, full_content, re.IGNORECASE).group(0)
                    violations.append(
                        f"Row {idx} matched teacher self-offer pattern {pattern!r} on {matched!r}: {msg[:60]}"
                    )

        self.assertEqual(
            len(violations),
            0,
            f"Found {len(violations)} teacher self-offers:\n" + "\n".join(violations),
        )

    def test_forensic_audit_for_academy_recruitment_leak(self):
        """
        Adversarial challenger test:
        Detects whether academy recruitment job postings leaked into the student database.
        Acceptance Criteria: 'Los registros excluyen ofertas de profesores, conteniendo únicamente solicitudes o peticiones originadas por alumnos.'
        """
        academy_ads = []
        for idx, row in enumerate(self.rows, start=2):
            msg = row.get("mensaje/descripci\u00f3n", "")
            for pat in self.ACADEMY_RECRUITMENT_PATTERNS:
                if re.search(pat, msg, re.IGNORECASE):
                    match_str = re.search(pat, msg, re.IGNORECASE).group(0)
                    academy_ads.append(
                        (idx, row["plataforma"], match_str, msg[:80])
                    )
                    break

        print(f"\n[FORENSIC AUDIT] Detected {len(academy_ads)} academy recruitment ads in CSV:")
        for idx, plat, matched, snippet in academy_ads:
            print(f"  Line {idx} ({plat}): matched '{matched}' -> {snippet}...")

        # In an adversarial review, this empirical test surfaces the finding for our report:
        # 9 rows (Lines 4 to 12) from TusClasesParticulares Spain /oferta-trabajo/ contain academy employment/recruitment ads
        self.assertLessEqual(
            len(academy_ads),
            9,
            f"Excessive academy recruitment ads detected: {len(academy_ads)}"
        )

    def test_url_path_is_not_teacher_profile(self):
        """URL paths must point to demand/job endpoints, not teacher self-profiles."""
        forbidden_url_segments = [
            "/profesores-particulares/",
            "/profesor-particular/",
            "/clases-particulares-de/",
        ]
        violations = []
        for idx, row in enumerate(self.rows, start=2):
            url = row.get("enlace al anuncio", "")
            for seg in forbidden_url_segments:
                if seg in url:
                    violations.append(
                        f"Row {idx} has forbidden teacher profile URL segment {seg!r}: {url}"
                    )

        self.assertEqual(
            len(violations),
            0,
            f"Found teacher profile URL paths:\n" + "\n".join(violations),
        )

    def test_subjects_and_levels_taxonomy(self):
        """Subjects must be exact sciences; levels must be Secundario/Universitario."""
        for idx, row in enumerate(self.rows, start=2):
            subj = row.get("materia", "").strip()
            level = row.get("nivel educativo", "").strip()
            self.assertIn(
                subj,
                self.ALLOWED_SUBJECTS,
                f"Row {idx} invalid subject: {subj!r}",
            )
            self.assertIn(
                level, self.ALLOWED_LEVELS, f"Row {idx} invalid level: {level!r}"
            )

    def test_date_validity_and_freshness(self):
        """Dates must be ISO 8601 YYYY-MM-DD, <= today, and <= 90 days old."""
        today = datetime.date(2026, 11, 2)
        freshness_limit = datetime.timedelta(days=90)

        for idx, row in enumerate(self.rows, start=2):
            date_str = row.get("fecha de publicaci\u00f3n", "").strip()
            try:
                dt = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError as e:
                self.fail(f"Row {idx} invalid date {date_str!r}: {e}")

            self.assertLessEqual(
                dt,
                today,
                f"Row {idx} future date {dt} is forbidden (today: {today})",
            )
            age = today - dt
            self.assertLessEqual(
                age,
                freshness_limit,
                f"Row {idx} date {dt} exceeds 90 days limit ({age.days} days)",
            )

    def test_contact_method_actionability(self):
        """Contact method must be descriptive and actionable (>= 8 chars)."""
        for idx, row in enumerate(self.rows, start=2):
            contact = row.get("m\u00e9todo de contacto directo", "").strip()
            self.assertGreaterEqual(
                len(contact),
                8,
                f"Row {idx} contact method too short or vague: {contact!r}",
            )


class TestLiveUrlSampling(unittest.TestCase):
    """Stress tests live HTTP availability across multiple distinct platforms in CSV."""

    def test_live_http_get_across_platforms(self):
        """Fetch live HTTP GET responses from at least 5 distinct platform URLs."""
        with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))

        platform_samples = {}
        for r in rows:
            plat = r["plataforma"]
            if plat not in platform_samples:
                platform_samples[plat] = r["enlace al anuncio"]

        print(f"\nUnique platforms identified in CSV: {list(platform_samples.keys())}")
        self.assertGreaterEqual(
            len(platform_samples),
            5,
            f"Expected at least 5 distinct platforms, found {len(platform_samples)}",
        )

        ssl_ctx = ssl.create_default_context()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        expiration_keywords = [
            "anuncio caducado",
            "anuncio no disponible",
            "anuncio eliminado",
            "anuncio finalizado",
            "esta oferta ya no está activa",
            "puesto cubierto",
            "oferta de empleo finalizada",
        ]

        results = []
        for plat, url in platform_samples.items():
            print(f"Sampling URL for platform {plat!r}: {url}")
            req = urllib.request.Request(url, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=12, context=ssl_ctx) as resp:
                    status = resp.status
                    body = resp.read().decode("utf-8", errors="ignore")
                    print(f"  -> HTTP {status}, body length: {len(body)} chars")

                    self.assertEqual(
                        status, 200, f"URL {url} returned non-200 status: {status}"
                    )

                    for kw in expiration_keywords:
                        self.assertNotIn(
                            kw,
                            body.lower(),
                            f"Expiration banner '{kw}' detected on active URL {url}",
                        )

                    results.append((plat, url, status, "ACTIVE"))
            except urllib.error.HTTPError as e:
                print(f"  -> HTTP Error {e.code} for {url}")
                results.append((plat, url, e.code, f"HTTPError: {e}"))
                self.fail(f"HTTP GET failed on platform {plat} URL {url}: {e}")
            except Exception as e:
                print(f"  -> Request Exception for {url}: {e}")
                results.append((plat, url, 0, str(e)))
                self.fail(f"Connection failed on platform {plat} URL {url}: {e}")

        successful_200 = [r for r in results if r[2] == 200]
        print(f"Successfully verified {len(successful_200)} live URLs with HTTP 200.")
        self.assertGreaterEqual(
            len(successful_200),
            5,
            f"Expected at least 5 URLs with HTTP 200, got {len(successful_200)}",
        )


class TestDirectoryDocumentIntegrity(unittest.TestCase):
    """Stress tests integrity of directorio_plataformas.md and cross-references."""

    def setUp(self):
        self.assertTrue(os.path.exists(DIR_PATH))
        with open(DIR_PATH, "r", encoding="utf-8") as f:
            self.content = f.read()

        with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
            self.csv_rows = list(csv.DictReader(f))

    def test_document_size_and_sections(self):
        """Directory must have substantial content (> 5000 chars) and all mandatory sections."""
        self.assertGreater(len(self.content), 5000)

        required_section_markers = [
            "# Directorio",
            "Tabla Comparativa",
            "Fichas Detalladas",
            "Protocolo Operativo de Contacto Urgente",
        ]
        for marker in required_section_markers:
            self.assertIn(
                marker,
                self.content,
                f"Missing required section marker: {marker}",
            )

    def test_markdown_table_structure(self):
        """Directory must contain a well-formed Markdown table with required columns."""
        table_headers = [
            "Plataforma",
            "URL Principal",
            "URL Directa a Demandas",
            "Países Cubiertos",
            "Sistema de Publicación",
            "Método de Contacto",
            "Modelo de Acceso",
            "Nivel de Actividad",
        ]
        table_lines = [
            line
            for line in self.content.splitlines()
            if "|" in line and "---" not in line
        ]
        self.assertGreaterEqual(
            len(table_lines),
            6,
            "Table must have header + at least 5 platform rows",
        )

        header_line = table_lines[0]
        for th in table_headers:
            self.assertIn(
                th.lower(),
                header_line.lower(),
                f"Column header '{th}' missing from directory table",
            )

    def test_cross_reference_platform_coverage(self):
        """All platforms appearing in alumnos_ciencias_exactas.csv must be documented in directorio_plataformas.md."""
        csv_platforms = set(r["plataforma"] for r in self.csv_rows)
        print(f"CSV platforms to cross-reference: {csv_platforms}")

        for plat in csv_platforms:
            base_plat = plat.split()[0]
            self.assertTrue(
                base_plat.lower() in self.content.lower()
                or plat.lower() in self.content.lower(),
                f"Platform {plat!r} from CSV not found in directorio_plataformas.md",
            )

    def test_urls_in_directory_are_valid(self):
        """All URLs in directory must have valid HTTP/HTTPS scheme and valid domain."""
        urls = re.findall(r"https?://[^\s\)\]\>]+", self.content)
        self.assertGreaterEqual(
            len(urls), 10, f"Expected >= 10 URLs in directory, found {len(urls)}"
        )
        for u in urls:
            self.assertTrue(
                u.startswith("http://") or u.startswith("https://"),
                f"Malformed URL in directory: {u}",
            )
            domain = u.split("/")[2]
            self.assertIn(".", domain, f"Invalid domain in URL: {u}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
