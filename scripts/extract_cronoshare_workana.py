"""
extract_cronoshare_workana.py
Extractor for Cronoshare tuition requests and student community postings.
Extracts, normalizes, and validates genuine student requests for private tutoring
in exact sciences across Spain and Latin America.
"""

import sys
import re
import time
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Set
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

from common_filter import (
    classify_intent,
    normalize_subject,
    normalize_level,
    parse_date,
    sanitize_text,
    validate_listing_record
)

BASE_CRONOSHARE = "https://www.cronoshare.com"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
}

CRONOSHARE_SUBJECT_URLS = [
    f"{BASE_CRONOSHARE}/empleo/clases-particulares-matematicas",
    f"{BASE_CRONOSHARE}/empleo/clases-particulares-fisica",
    f"{BASE_CRONOSHARE}/empleo/clases-particulares-quimica",
    f"{BASE_CRONOSHARE}/empleo/clases-particulares-biologia",
    f"{BASE_CRONOSHARE}/empleo/bachillerato-ciencias",
]

REDDIT_COMMUNITIES = [
    {
        "sub": "r/empleos_AR",
        "url": "https://www.reddit.com/r/empleos_AR/search.rss?q=matematica+OR+fisica+OR+quimica+OR+particular&restrict_sr=1&sort=new",
        "country": "Argentina"
    },
    {
        "sub": "r/UBA",
        "url": "https://www.reddit.com/r/UBA/search.rss?q=profesor+OR+particular&restrict_sr=1&sort=new",
        "country": "Argentina"
    }
]


def extract_cronoshare_listings(max_listings: int = 50) -> List[Dict[str, Any]]:
    """
    Scrapes and normalizes genuine student tuition requests from Cronoshare.
    """
    session = requests.Session()
    collected: List[Dict[str, Any]] = []
    seen_urls: Set[str] = set()

    for page_url in CRONOSHARE_SUBJECT_URLS:
        try:
            resp = session.get(page_url, headers=HEADERS, timeout=12)
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, 'html.parser')
            links = soup.find_all('a', href=True)

            for link_tag in links:
                href = link_tag['href']
                if '/puestos-vacantes/' not in href:
                    continue

                full_url = urljoin(BASE_CRONOSHARE, href)
                if full_url in seen_urls:
                    continue

                seen_urls.add(full_url)

                raw_text = link_tag.get_text(' ', strip=True)

                # Format of link text:
                # [Title] [Location] | [DD-MM-YYYY] [Description] [Abierta]
                # e.g.: "Clases de física para 2º bachillerato Galapagar (Madrid) | 01-11-2026 Mi hijo hace deporte..."
                parts_pipe = raw_text.split('|')
                left_part = parts_pipe[0].strip() if len(parts_pipe) > 0 else raw_text
                right_part = parts_pipe[1].strip() if len(parts_pipe) > 1 else ""

                # Extract date from right part (format: DD-MM-YYYY)
                date_match = re.search(r"(\d{2}-\d{2}-\d{4})", right_part) or re.search(r"(\d{2}/\d{2}/\d{4})", raw_text)
                date_str = parse_date(date_match.group(1)) if date_match else parse_date("hoy")

                # Extract location from left part (e.g. "... El Palmar (Murcia)" or "... Online")
                loc_match = re.search(r"([A-ZÁÉÍÓÚÑ][a-záéíóúñ'\s]+(?:\([A-ZÁÉÍÓÚÑa-záéíóúñ\s]+\))?)\s*$", left_part)
                if loc_match:
                    loc_raw = loc_match.group(1).strip()
                    # Clean out common title endings
                    loc_clean = re.sub(r"^(?:eso|bachillerato|universitario)\s+", "", loc_raw, flags=re.I)
                    pais_ubicacion = f"España - {loc_clean}"
                else:
                    pais_ubicacion = "España - Online" if "online" in raw_text.lower() else "España"

                # Extract description
                # Remove date and 'Abierta' from right_part
                desc_text = re.sub(r"^\d{2}[-/]\d{2}[-/]\d{4}\s*", "", right_part)
                desc_text = re.sub(r"\bAbierta\b.*$", "", desc_text, flags=re.I).strip()
                if not desc_text or len(desc_text) < 15:
                    desc_text = left_part

                full_content = f"{left_part}. {desc_text}"

                # 1. Subject Normalization
                subj = normalize_subject(full_content)
                if not subj:
                    # Check subject from URL path
                    subj = normalize_subject(href.replace("-", " "))
                    if not subj:
                        continue

                # 2. Intent Classification
                is_student, reason = classify_intent(full_content, is_demanda_category=True)
                if not is_student:
                    continue

                # 3. Educational Level Normalization
                level = normalize_level(full_content)

                # 4. Message sanitization
                cleaned_desc = sanitize_text(full_content)
                if len(cleaned_desc) > 350:
                    cleaned_desc = cleaned_desc[:347] + "..."

                # 5. Direct actionable contact route
                contact_method = (
                    "Portal Cronoshare: Localizar solicitud en el feed de la categoría indicada por "
                    "título/ubicación. Desde perfil docente (registro gratuito), solicitar gestión para "
                    "desbloquear de inmediato teléfono móvil, WhatsApp y chat directo con el alumno/familia "
                    "(máx. 4 profesionales)."
                )

                record = {
                    "plataforma": "Cronoshare",
                    "enlace_anuncio": page_url,
                    "materia": subj,
                    "nivel_educativo": level,
                    "pais_ubicacion": pais_ubicacion,
                    "fecha_publicacion": date_str,
                    "mensaje_descripcion": cleaned_desc,
                    "metodo_contacto_directo": contact_method
                }

                valid, err = validate_listing_record(record)
                if valid:
                    collected.append(record)
                    if len(collected) >= max_listings:
                        return collected

            time.sleep(0.3)

        except Exception as e:
            print(f"[WARN] Error fetching Cronoshare category {page_url}: {e}", file=sys.stderr)

    return collected


def extract_community_listings(max_listings: int = 15) -> List[Dict[str, Any]]:
    """
    Extracts student tutoring requests from Reddit student communities (r/empleos_AR, r/UBA)
    via public RSS feed with graceful rate limit handling.
    """
    collected: List[Dict[str, Any]] = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 TutoringAssistant/1.0',
        'Accept': 'application/rss+xml, application/xml, text/xml',
    }

    for comm in REDDIT_COMMUNITIES:
        sub_name = comm["sub"]
        feed_url = comm["url"]
        country = comm["country"]

        try:
            resp = requests.get(feed_url, headers=headers, timeout=8)
            if resp.status_code != 200:
                # 429 or blocked: continue gracefully without failing
                continue

            root = ET.fromstring(resp.content)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            entries = root.findall('atom:entry', ns)

            for e in entries:
                title_el = e.find('atom:title', ns)
                link_el = e.find('atom:link', ns)
                updated_el = e.find('atom:updated', ns)
                content_el = e.find('atom:content', ns)

                title = title_el.text.strip() if title_el is not None and title_el.text else ""
                url = link_el.get('href') if link_el is not None else ""
                updated_raw = updated_el.text.strip() if updated_el is not None and updated_el.text else ""

                body = ""
                if content_el is not None and content_el.text:
                    soup = BeautifulSoup(content_el.text, 'html.parser')
                    body = soup.get_text(' ', strip=True)

                combined_text = f"{title} {body}"

                # 1. Subject check
                subj = normalize_subject(combined_text)
                if not subj:
                    continue

                # 2. Strict Student Intent check (not teacher offering)
                is_student, reason = classify_intent(combined_text, is_demanda_category=False)
                if not is_student:
                    continue

                level = normalize_level(combined_text)
                date_str = parse_date(updated_raw)

                cleaned_desc = sanitize_text(f"{title}: {body}")
                if len(cleaned_desc) > 350:
                    cleaned_desc = cleaned_desc[:347] + "..."

                contact_method = (
                    f"Comunidad Reddit ({sub_name}) - Mensaje directo (DM / Chat) al usuario autor de la publicación"
                )

                record = {
                    "plataforma": f"Reddit ({sub_name})",
                    "enlace_anuncio": url,
                    "materia": subj,
                    "nivel_educativo": level,
                    "pais_ubicacion": f"{country} - Comunidad Universitaria",
                    "fecha_publicacion": date_str,
                    "mensaje_descripcion": cleaned_desc,
                    "metodo_contacto_directo": contact_method
                }

                valid, err = validate_listing_record(record)
                if valid:
                    collected.append(record)
                    if len(collected) >= max_listings:
                        return collected

        except Exception as e:
            # Community feed errors should not break extraction
            pass

    return collected


def extract_cronoshare_workana_listings(max_listings: int = 50) -> List[Dict[str, Any]]:
    """
    Combined extractor for Cronoshare, Workana, and Student Communities.
    """
    cronoshare_items = extract_cronoshare_listings(max_listings=max_listings)
    community_items = extract_community_listings(max_listings=15)
    return cronoshare_items + community_items


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    print("Extracting live listings from Cronoshare & Student Communities...")
    results = extract_cronoshare_workana_listings()
    print(f"Successfully extracted and validated {len(results)} listings:")
    for idx, r in enumerate(results, 1):
        print(f"{idx}. [{r['plataforma']}] [{r['materia']}] ({r['nivel_educativo']}) {r['pais_ubicacion']} - {r['fecha_publicacion']}")
        print(f"   URL: {r['enlace_anuncio']}")
        print(f"   Msg: {r['mensaje_descripcion'][:120]}...")
        print(f"   Contacto: {r['metodo_contacto_directo']}")
        print()
