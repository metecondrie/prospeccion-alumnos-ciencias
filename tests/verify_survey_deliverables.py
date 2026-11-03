#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verification Script: verify_survey_deliverables.py
Author: e2e_test_writer
Purpose: Standalone programmatic audit tool validating deliverables for the
         Student Tutor Search & Platform Directory project according to
         specifications in ORIGINAL_REQUEST.md, PROJECT.md, and spec_miner_survey_3/handoff.md.

Deliverables audited:
1. alumnos_ciencias_exactas.csv
2. directorio_plataformas.md

Usage:
    python tests/verify_survey_deliverables.py [--workspace PATH] [--sample-urls] [--verbose]
"""

import os
import sys
import re
import csv
import codecs
import argparse
from datetime import datetime, timedelta
import urllib.request
import urllib.error

# Canonical Specifications
EXPECTED_HEADERS = [
    "plataforma",
    "enlace al anuncio",
    "materia",
    "nivel educativo",
    "país/ubicación",
    "fecha de publicación",
    "mensaje/descripción",
    "método de contacto directo",
]

VALID_SUBJECTS = {"Física", "Química", "Biología", "Matemáticas"}
VALID_LEVELS = {"Secundario", "Universitario"}

TEACHER_BLACKLIST = [
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
]

STUDENT_INTENT_SIGNALS = [
    r"\bbusco\b",
    r"\bnecesito\b",
    r"\bse busca\b",
    r"\bayuda\b",
    r"\bapoyo\b",
    r"\bexamen\b",
    r"\bparcial\b",
    r"\bfinal\b",
    r"\brendir\b",
    r"\bcursando\b",
    r"\bpreparar\b",
    r"\bselectividad\b",
    r"\bebau\b",
    r"\bevau\b",
    r"\bcbc\b",
    r"\bprofe\b",
    r"\bprofesor\b",
    r"\bprofesora\b",
    r"\btutor\b",
    r"\bclases\b",
    r"\bexplicar\b",
    r"\bentender\b",
]

REQUIRED_DIR_TERMS = [
    "plataforma",
    "url principal",
    "demandas",
    "contacto",
]

REQUIRED_PLATFORMS_SAMPLE = [
    "tusclases",
    "tablón de anuncios",
    "cronoshare",
]

EXPIRATION_PHRASES = [
    "este anuncio ha caducado",
    "anuncio no disponible",
    "solicitud finalizada",
    "anuncio caducado",
    "ya no está disponible",
    "solicitud cerrada",
]


def verify_file_existence(csv_path, dir_path):
    """Check that both deliverables exist and are of non-trivial size."""
    errors = []
    if not os.path.exists(csv_path):
        errors.append(f"MISSING FILE: CSV database not found at {csv_path}")
    else:
        size = os.path.getsize(csv_path)
        if size < 200:
            errors.append(f"FILE TOO SMALL: CSV database has {size} bytes (minimum 200 bytes expected).")
        else:
            print(f"[OK] CSV file found ({size} bytes): {csv_path}")

    if not os.path.exists(dir_path):
        errors.append(f"MISSING FILE: Directory file not found at {dir_path}")
    else:
        size = os.path.getsize(dir_path)
        if size < 500:
            errors.append(f"FILE TOO SMALL: Directory has {size} bytes (minimum 500 bytes expected).")
        else:
            print(f"[OK] Directory file found ({size} bytes): {dir_path}")

    return errors


def verify_utf8_bom(csv_path):
    """Verify that the CSV begins with the exact 3-byte UTF-8 BOM signature."""
    errors = []
    try:
        with open(csv_path, "rb") as f:
            bom = f.read(3)
            if bom != codecs.BOM_UTF8:
                errors.append(
                    f"ENCODING ERROR: CSV missing UTF-8 BOM (0xEF, 0xBB, 0xBF). Found: {bom!r}, Expected: {codecs.BOM_UTF8!r}"
                )
            else:
                print("[OK] UTF-8 BOM signature verified (0xEF, 0xBB, 0xBF).")
    except Exception as e:
        errors.append(f"ERROR reading binary BOM: {e}")
    return errors


def verify_csv_structure(csv_path):
    """Parse CSV with utf-8-sig and verify canonical headers and row shapes."""
    errors = []
    rows = []
    try:
        with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            try:
                headers = next(reader)
            except StopIteration:
                errors.append("CSV is empty.")
                return errors, rows

            if headers != EXPECTED_HEADERS:
                errors.append(
                    f"HEADER MISMATCH:\nFound:    {headers}\nExpected: {EXPECTED_HEADERS}"
                )
            else:
                print(f"[OK] Exact 8 canonical headers verified: {headers}")

            for idx, row in enumerate(reader, start=2):
                if len(row) != 8:
                    errors.append(f"Row {idx}: column count is {len(row)} instead of 8: {row}")
                    continue
                rows.append((idx, row))

        if len(rows) == 0:
            errors.append("CSV contains 0 data rows.")
        else:
            print(f"[OK] Parsed {len(rows)} valid data rows.")

    except Exception as e:
        errors.append(f"CSV PARSING EXCEPTION: {e}")

    return errors, rows


def verify_data_rows(rows, sample_urls=False, verbose=False):
    """Validate data taxonomy, teacher blacklist, date freshness, and contact actionability."""
    errors = []
    today = datetime.now().date()
    max_age_days = 90
    earliest_allowed_date = today - timedelta(days=max_age_days)

    subjects_seen = set()
    levels_seen = set()
    locations_seen = set()

    for idx, row in rows:
        plat, url, subj, level, loc, date_str, msg, contact = row

        # 1. Platform name
        if not plat.strip():
            errors.append(f"Row {idx}: Platform name is empty.")

        # 2. URL validation
        if not re.match(r"^https?://[^\s/$.?#].[^\s]*$", url.strip(), re.IGNORECASE):
            errors.append(f"Row {idx}: Invalid URL format: '{url}'")

        # 3. Subject validation
        subj_parts = [s.strip() for s in subj.split(",")]
        for sp in subj_parts:
            subjects_seen.add(sp)
            if sp not in VALID_SUBJECTS:
                errors.append(f"Row {idx}: Subject '{sp}' not in allowed set {VALID_SUBJECTS}")

        # 4. Educational Level validation
        levels_seen.add(level.strip())
        if level.strip() not in VALID_LEVELS:
            errors.append(f"Row {idx}: Level '{level}' not in allowed set {VALID_LEVELS}")

        # 5. Location
        loc_clean = loc.strip()
        locations_seen.add(loc_clean)
        if len(loc_clean) < 3:
            errors.append(f"Row {idx}: Location '{loc}' is invalid or too short.")

        # 6. Date validation
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str.strip()):
            errors.append(f"Row {idx}: Date '{date_str}' not in YYYY-MM-DD format.")
        else:
            try:
                d = datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
                if d > today:
                    errors.append(f"Row {idx}: Future date '{date_str}' is forbidden (today: {today}).")
                if d < earliest_allowed_date:
                    errors.append(
                        f"Row {idx}: Date '{date_str}' exceeds freshness limit of {max_age_days} days."
                    )
            except ValueError:
                errors.append(f"Row {idx}: Invalid calendar date '{date_str}'.")

        # 7. Student authenticity (Negative teacher regex check)
        msg_clean = msg.strip()
        if len(msg_clean) < 15:
            errors.append(f"Row {idx}: Message description too short (< 15 chars): '{msg_clean}'")

        msg_lower = msg_clean.lower()
        for pat in TEACHER_BLACKLIST:
            if re.search(pat, msg_lower):
                errors.append(f"Row {idx}: Teacher intent detected by regex pattern '{pat}' in: '{msg_clean[:80]}...'")

        # Positive student intent signal
        has_student_signal = any(re.search(pat, msg_lower) for pat in STUDENT_INTENT_SIGNALS)
        if not has_student_signal and verbose:
            print(f"[WARN] Row {idx}: Weak student intent signal in message: '{msg_clean[:60]}...'")

        # 8. Contact method actionability
        contact_clean = contact.strip()
        if len(contact_clean) < 8:
            errors.append(f"Row {idx}: Contact method '{contact_clean}' too short or missing (< 8 chars).")

    print(f"[OK] Distinct subjects observed: {sorted(list(subjects_seen))}")
    print(f"[OK] Distinct educational levels observed: {sorted(list(levels_seen))}")
    print(f"[OK] Total distinct locations: {len(locations_seen)}")

    # URL liveness sampling (optional or requested)
    if sample_urls and rows:
        import random
        sample_size = min(5, len(rows))
        sample_rows = random.sample(rows, sample_size)
        print(f"\n--- Sampling {sample_size} URLs for HTTP liveness ---")
        headers_req = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        for idx, row in sample_rows:
            url = row[1].strip()
            try:
                req = urllib.request.Request(url, headers=headers_req)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    status = resp.status
                    body = resp.read(8192).decode("utf-8", errors="ignore").lower()
                    if status != 200:
                        errors.append(f"Row {idx}: URL returned HTTP {status}: {url}")
                    else:
                        for exp in EXPIRATION_PHRASES:
                            if exp in body:
                                errors.append(f"Row {idx}: URL appears expired/closed with '{exp}': {url}")
                                break
                        print(f"  [OK] HTTP 200: {url[:70]}")
            except Exception as e:
                print(f"  [WARN] Row {idx}: Network probing warning for {url}: {e}")

    return errors


def verify_directory_structure(dir_path):
    """Verify platform directory structure, markdown tables, and key coverage."""
    errors = []
    try:
        with open(dir_path, "r", encoding="utf-8") as f:
            content = f.read()

        content_lower = content.lower()

        # Check required terms
        for term in REQUIRED_DIR_TERMS:
            if term not in content_lower:
                errors.append(f"Directory markdown missing expected section/term: '{term}'")

        # Check sample platforms
        found_platforms = []
        for p in REQUIRED_PLATFORMS_SAMPLE:
            if p in content_lower:
                found_platforms.append(p)
        if len(found_platforms) < 2:
            errors.append(
                f"Directory markdown has sparse platform coverage. Found: {found_platforms}, expected at least {REQUIRED_PLATFORMS_SAMPLE}"
            )

        # Check for Markdown comparison table indicator
        if "|---" not in content and "|:--" not in content and "| ---" not in content:
            errors.append("Directory markdown does not contain a Markdown comparison table (|---|).")
        else:
            print("[OK] Platform directory contains valid Markdown comparison table.")

        print(f"[OK] Directory file verified ({len(content)} characters).")

    except Exception as e:
        errors.append(f"DIRECTORY VERIFICATION EXCEPTION: {e}")

    return errors


def verify_all(workspace=None, sample_urls=False, verbose=False):
    """Main verification orchestrator."""
    if not workspace:
        # Default to project root (directory containing this script's parent or current working dir)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        workspace = os.path.abspath(os.path.join(script_dir, ".."))

    csv_path = os.path.join(workspace, "alumnos_ciencias_exactas.csv")
    dir_path = os.path.join(workspace, "directorio_plataformas.md")

    print("================================================================")
    print("      STUDENT TUTOR DIRECTORY & DATABASE VERIFICATION AUDIT     ")
    print("================================================================")
    print(f"Workspace: {workspace}")
    print(f"CSV Path:  {csv_path}")
    print(f"Dir Path:  {dir_path}\n")

    all_errors = []

    # Step 1: File Existence
    print("--- [1/5] Verifying Deliverable Files Existence ---")
    exist_errors = verify_file_existence(csv_path, dir_path)
    all_errors.extend(exist_errors)

    if exist_errors:
        print("\n[FAIL] File existence checks failed. Halting further checks.")
        _print_summary(all_errors)
        return False

    # Step 2: UTF-8 BOM
    print("\n--- [2/5] Verifying Character Encoding & UTF-8 BOM ---")
    bom_errors = verify_utf8_bom(csv_path)
    all_errors.extend(bom_errors)

    # Step 3: CSV Structure and Headers
    print("\n--- [3/5] Verifying CSV RFC 4180 Structure & Headers ---")
    struct_errors, rows = verify_csv_structure(csv_path)
    all_errors.extend(struct_errors)

    # Step 4: Data Rows Taxonomy & Authenticity
    print("\n--- [4/5] Verifying Data Records, Taxonomy & Student Authenticity ---")
    if rows:
        row_errors = verify_data_rows(rows, sample_urls=sample_urls, verbose=verbose)
        all_errors.extend(row_errors)

    # Step 5: Platform Directory Document
    print("\n--- [5/5] Verifying Platform Directory Document Completeness ---")
    dir_errors = verify_directory_structure(dir_path)
    all_errors.extend(dir_errors)

    _print_summary(all_errors)
    return len(all_errors) == 0


def _print_summary(errors):
    print("\n================================================================")
    if errors:
        print(f"VERIFICATION RESULT: FAILED ({len(errors)} error(s) detected)")
        print("================================================================")
        for i, err in enumerate(errors[:30], 1):
            print(f"  {i}. {err}")
        if len(errors) > 30:
            print(f"  ... and {len(errors) - 30} additional errors.")
    else:
        print("VERIFICATION RESULT: PASSED (100% compliant with specifications)")
        print("================================================================")


def main():
    parser = argparse.ArgumentParser(
        description="Verify deliverables for Student Tutor Search & Platform Directory"
    )
    parser.add_argument(
        "--workspace",
        "-w",
        default=None,
        help="Workspace directory containing the deliverables (defaults to project root).",
    )
    parser.add_argument(
        "--sample-urls",
        action="store_true",
        help="Perform live network sampling of URLs for HTTP 200 and liveness.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output.",
    )
    args = parser.parse_args()

    success = verify_all(workspace=args.workspace, sample_urls=args.sample_urls, verbose=args.verbose)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
