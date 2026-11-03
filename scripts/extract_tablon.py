"""
extract_tablon.py
Live extractor for Tablón de Anuncios (Spain) using ?demanda=1.
Extracts, parses, and validates real student listings seeking tutors in exact sciences.
"""

import sys
import re
import time
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

BASE_URL = "https://www.tablondeanuncios.com"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
}

CATEGORY_URLS = [
    f"{BASE_URL}/clases-particulares/profesor-de-matematicas.htm?demanda=1",
    f"{BASE_URL}/clases-particulares/profesor-de-fisica.htm?demanda=1",
    f"{BASE_URL}/clases-particulares/profesor-de-quimica.htm?demanda=1",
    f"{BASE_URL}/clases-particulares/profesor-de-biologia.htm?demanda=1",
    f"{BASE_URL}/clases-particulares/clases-universitarias.htm?demanda=1",
    f"{BASE_URL}/clases-particulares/bachillerato.htm?demanda=1",
    f"{BASE_URL}/clases-particulares/apoyo-escolar.htm?demanda=1",
    f"{BASE_URL}/clases-particulares/?demanda=1",
]


def extract_ad_details(url: str, session: requests.Session) -> Dict[str, Any]:
    """
    Fetches the detail page of a Tablón listing to extract clean article text, contact options,
    and verify the ad is still active.
    """
    try:
        resp = session.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return {"active": False, "error": f"Status {resp.status_code}"}

        soup = BeautifulSoup(resp.text, 'html.parser')
        page_text = soup.get_text(' ', strip=True)

        # Check expiration marker
        if "ups! has llegado tarde" in page_text.lower() or "este anuncio ha caducado" in page_text.lower():
            return {"active": False, "error": "Expired ad"}

        article_elem = soup.select_one('article')
        if not article_elem:
            return {"active": False, "error": "No article content"}

        # Extract only the actual body of the ad, omitting social share links and footer menus
        body_text = article_elem.get_text(' ', strip=True)
        # Strip trailing breadcrumbs or site navigation in article
        body_text = re.sub(r"Volver al anuncio.*", "", body_text, flags=re.I)
        body_text = re.sub(r"Denunciar spam o fraude.*", "", body_text, flags=re.I)
        body_text = re.sub(r"Añadir a Mis Favoritos.*", "", body_text, flags=re.I)

        # Check if direct phone/whatsapp is in text
        contact_method = "Formulario web directo en Tablón de Anuncios (botón 'Contactar con el anunciante' - notificación inmediata al alumno)"
        m_phone = re.search(r"\b(?:tel[eé]fono|m[oó]vil|whatsapp):\s*([0-9\s+-]{9,15})\b", body_text, re.I)
        if m_phone:
            contact_method = f"Teléfono / WhatsApp directo facilitado por el alumno: {m_phone.group(1).strip()}"

        return {
            "active": True,
            "body": body_text,
            "contact_method": contact_method
        }
    except Exception as e:
        return {"active": False, "error": str(e)}


def extract_tablon_listings(max_listings: int = 25) -> List[Dict[str, Any]]:
    """
    Extracts live student listings from Tablón de Anuncios across exact sciences.
    """
    session = requests.Session()
    collected_listings: List[Dict[str, Any]] = []
    seen_urls: Set[str] = set()

    for cat_url in CATEGORY_URLS:
        try:
            resp = session.get(cat_url, headers=HEADERS, timeout=12)
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, 'html.parser')
            items = soup.select('article.result-item')

            for it in items:
                link_tag = it.find('a', href=True)
                if not link_tag:
                    continue

                raw_href = link_tag['href']
                full_url = urljoin(BASE_URL, raw_href)

                if full_url in seen_urls or not re.search(r"-\d+\.htm", full_url):
                    continue

                seen_urls.add(full_url)

                title_tag = it.find('h2') or it.find('h3') or link_tag
                title_text = title_tag.get_text(strip=True) if title_tag else ""

                # Card text
                card_text = it.get_text(' ', strip=True)

                # Fetch ad details first to get the genuine announcement body
                details = extract_ad_details(full_url, session)
                if not details.get("active"):
                    continue

                full_desc = details.get("body", "")
                combined_content = f"{title_text} {full_desc}"

                # 1. Deterministic Student vs Teacher Classification
                is_student, reason = classify_intent(combined_content, is_demanda_category=True)
                if not is_student:
                    continue

                # 2. Strict Subject Normalization on actual listing text
                subj = normalize_subject(combined_content)
                if not subj:
                    continue

                # Reject listings that are solely about informatics or languages
                non_exact = [r"\binform[aá]tica\b", r"\blinux\b", r"\bredes\b", r"\bguitarra\b", r"\bfranc[eé]s\b", r"\bdan[eé]s\b"]
                if any(re.search(p, title_text.lower()) for p in non_exact):
                    # Only accept if exact science is explicitly in title or body
                    if not any(k in title_text.lower() for k in ["mat", "fisic", "quim", "biol", "calcul", "algebra"]):
                        continue

                # Extract date from card or body (format: DD/MM/YYYY)
                date_match = re.search(r"(\d{2}/\d{2}/\d{4})", full_desc) or re.search(r"(\d{2}/\d{2}/\d{4})", card_text)
                date_str = parse_date(date_match.group(1)) if date_match else parse_date("hoy")

                # Extract city / region
                loc_match = re.search(r"en el Tablón de Anuncios de\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*)", full_desc)
                if not loc_match:
                    loc_match = re.search(r"Clases particulares en\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*)", full_desc)
                if not loc_match:
                    loc_match = re.search(r"en\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*)", card_text)
                
                location = loc_match.group(1).strip() if loc_match else "España"
                location = re.sub(r"\s+Precio.*", "", location, flags=re.I).strip()
                # Exclude false positives like 'Anuncios' or 'Precio'
                if location in ("Anuncios", "Precio", "El Tablón", "Tablón", ""):
                    location = "Navarra / España"
                pais_ubicacion = f"España - {location}"

                level = normalize_level(combined_content)
                contact_method = details.get(
                    "contact_method",
                    "Formulario web directo en Tablón de Anuncios (botón 'Contactar con el anunciante' - notificación inmediata al alumno)"
                )

                # Format clean message description
                cleaned_desc = sanitize_text(full_desc)
                if len(cleaned_desc) > 350:
                    cleaned_desc = cleaned_desc[:347] + "..."

                record = {
                    "plataforma": "Tablón de Anuncios",
                    "enlace_anuncio": full_url,
                    "materia": subj,
                    "nivel_educativo": level,
                    "pais_ubicacion": pais_ubicacion,
                    "fecha_publicacion": date_str,
                    "mensaje_descripcion": cleaned_desc,
                    "metodo_contacto_directo": contact_method
                }

                valid, err = validate_listing_record(record)
                if valid:
                    collected_listings.append(record)
                    if len(collected_listings) >= max_listings:
                        return collected_listings

                time.sleep(0.4)

        except Exception as e:
            print(f"[WARN] Error fetching Tablon category {cat_url}: {e}", file=sys.stderr)

    return collected_listings


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    print("Extracting live listings from Tablón de Anuncios...")
    results = extract_tablon_listings()
    print(f"Successfully extracted and validated {len(results)} listings:")
    for idx, r in enumerate(results, 1):
        print(f"{idx}. [{r['materia']}] ({r['nivel_educativo']}) {r['pais_ubicacion']} - {r['fecha_publicacion']}")
        print(f"   URL: {r['enlace_anuncio']}")
        print(f"   Msg: {r['mensaje_descripcion'][:120]}...")
        print(f"   Contacto: {r['metodo_contacto_directo']}")
        print()
