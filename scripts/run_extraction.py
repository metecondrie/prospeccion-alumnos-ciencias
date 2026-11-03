"""
run_extraction.py
Unified extraction runner for Milestone 1.
Collects, validates, deduplicates, and saves verified live student listings
from all surveyed platforms to `data/extracted_listings.json`.
"""

import os
import sys
import json
import codecs
from typing import List, Dict, Any, Set
from collections import Counter

# Ensure scripts dir is on sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
sys.path.insert(0, SCRIPT_DIR)

from common_filter import validate_listing_record, validate_url_liveness
from extract_tablon import extract_tablon_listings
from extract_tusclases import extract_tusclases_listings
from extract_cronoshare_workana import extract_cronoshare_workana_listings

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
OUTPUT_JSON_PATH = os.path.join(DATA_DIR, "extracted_listings.json")


def run_full_pipeline() -> List[Dict[str, Any]]:
    print("=" * 60)
    print("STARTING LIVE EXTRACTION ENGINE — MILESTONE 1")
    print("=" * 60)

    all_raw_listings: List[Dict[str, Any]] = []

    # 1. Tablón de Anuncios Spain
    print("\n[1/3] Extracting from Tablón de Anuncios (?demanda=1)...")
    try:
        tablon_items = extract_tablon_listings(max_listings=25)
        print(f" -> Tablón de Anuncios returned {len(tablon_items)} verified listings.")
        all_raw_listings.extend(tablon_items)
    except Exception as e:
        print(f" -> [ERROR] Tablón extraction failed: {e}", file=sys.stderr)

    # 2. TusClases Network (Spain, Argentina, Mexico, Colombia, Chile, Peru)
    print("\n[2/3] Extracting from TusClases Network (Spain & LATAM)...")
    try:
        tusclases_items = extract_tusclases_listings(max_listings=150, max_per_target=25)
        print(f" -> TusClases Network returned {len(tusclases_items)} verified listings.")
        all_raw_listings.extend(tusclases_items)
    except Exception as e:
        print(f" -> [ERROR] TusClases extraction failed: {e}", file=sys.stderr)

    # 3. Cronoshare & Student Communities
    print("\n[3/3] Extracting from Cronoshare & Student Communities...")
    try:
        crono_items = extract_cronoshare_workana_listings(max_listings=50)
        print(f" -> Cronoshare & Communities returned {len(crono_items)} verified listings.")
        all_raw_listings.extend(crono_items)
    except Exception as e:
        print(f" -> [ERROR] Cronoshare/Communities extraction failed: {e}", file=sys.stderr)

    print("\n" + "=" * 60)
    print(f"RAW EXTRACTED TOTAL: {len(all_raw_listings)} listings")
    print("=" * 60)

    # 4. Deduplication & Final Schema Validation
    seen_keys: Set[Any] = set()
    verified_listings: List[Dict[str, Any]] = []

    for item in all_raw_listings:
        url = item.get("enlace_anuncio", "").strip()
        plat = item.get("plataforma", "").strip()
        msg = item.get("mensaje_descripcion", "").strip()
        dedup_key = (plat, url, msg[:50])
        if not url or dedup_key in seen_keys:
            continue

        valid, err = validate_listing_record(item)
        if not valid:
            print(f"[REJECTED] {url}: {err}")
            continue

        seen_keys.add(dedup_key)
        verified_listings.append(item)

    print(f"\nDEDUPLICATED & STRICTLY VALIDATED: {len(verified_listings)} listings")

    # 5. Save to data/extracted_listings.json
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(verified_listings, f, ensure_ascii=False, indent=2)

    print(f"[SAVED] File created at: {OUTPUT_JSON_PATH} ({os.path.getsize(OUTPUT_JSON_PATH)} bytes)")

    # 6. Quality Metrics Summary
    platforms = Counter(r["plataforma"] for r in verified_listings)
    subjects = Counter(r["materia"] for r in verified_listings)
    levels = Counter(r["nivel_educativo"] for r in verified_listings)
    countries = Counter(r["pais_ubicacion"].split(" - ")[0] for r in verified_listings)

    print("\n--- DISTRIBUTION BY PLATFORM ---")
    for p, c in platforms.most_common():
        print(f"  {p}: {c}")

    print("\n--- DISTRIBUTION BY SUBJECT ---")
    for s, c in subjects.most_common():
        print(f"  {s}: {c}")

    print("\n--- DISTRIBUTION BY EDUCATIONAL LEVEL ---")
    for l, c in levels.most_common():
        print(f"  {l}: {c}")

    print("\n--- DISTRIBUTION BY COUNTRY ---")
    for k, c in countries.most_common():
        print(f"  {k}: {c}")

    print("\n" + "=" * 60)
    print("MILESTONE 1 EXTRACTION COMPLETED SUCCESSFULLY")
    print("=" * 60)

    return verified_listings


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    run_full_pipeline()
