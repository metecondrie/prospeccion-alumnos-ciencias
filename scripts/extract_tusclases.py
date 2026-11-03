"""
extract_tusclases.py
Live extractor for TusClases Network across:
- Spain (tusclasesparticulares.com/empleo-profesores/)
- Argentina (tusclases.com.ar/alumnos/)
- Mexico (tusclases.mx/estudiantes/)
- Colombia (tusclases.co/estudiantes/)
- Chile (tusclasesparticulares.cl/estudiantes/)
- Peru (tusclases.pe/estudiantes/)

Extracts, normalizes, and validates genuine student listings seeking tutors in exact sciences.
"""

import sys
import re
import time
from typing import List, Dict, Any, Set
from urllib.parse import urljoin, urlparse
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

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
}

# Network endpoints
NETWORK_TARGETS = [
    # Spain
    {
        "pais": "España",
        "domain": "https://www.tusclasesparticulares.com",
        "platform_name": "TusClasesParticulares",
        "urls": [
            "https://www.tusclasesparticulares.com/buscar/alumnos.aspx",
            "https://www.tusclasesparticulares.com/alumnos/matematicas.aspx",
            "https://www.tusclasesparticulares.com/alumnos/fisica.aspx",
            "https://www.tusclasesparticulares.com/alumnos/quimica.aspx",
            "https://www.tusclasesparticulares.com/alumnos/biologia.aspx",
            "https://www.tusclasesparticulares.com/alumnos/analisis-matematico.aspx",
            "https://www.tusclasesparticulares.com/alumnos/algebra.aspx",
        ]
    },
    # Argentina
    {
        "pais": "Argentina",
        "domain": "https://www.tusclases.com.ar",
        "platform_name": "TusClases Argentina",
        "urls": [
            "https://www.tusclases.com.ar/buscar/alumnos.aspx",
            "https://www.tusclases.com.ar/alumnos/matematica.aspx",
            "https://www.tusclases.com.ar/alumnos/fisica.aspx",
            "https://www.tusclases.com.ar/alumnos/quimica.aspx",
            "https://www.tusclases.com.ar/alumnos/analisis-matematico.aspx",
            "https://www.tusclases.com.ar/alumnos/algebra.aspx",
            "https://www.tusclases.com.ar/alumnos/biofisica.aspx",
            "https://www.tusclases.com.ar/alumnos/capital-federal/matematica.aspx",
            "https://www.tusclases.com.ar/alumnos/buenos-aires/matematica.aspx",
        ]
    },
    # Mexico
    {
        "pais": "México",
        "domain": "https://www.tusclases.mx",
        "platform_name": "TusClases México",
        "urls": [
            "https://www.tusclases.mx/estudiantes/",
            "https://www.tusclases.mx/buscar/alumnos.aspx",
            "https://www.tusclases.mx/estudiantes/matematicas/",
            "https://www.tusclases.mx/estudiantes/fisica/",
            "https://www.tusclases.mx/estudiantes/quimica/",
        ]
    },
    # Colombia
    {
        "pais": "Colombia",
        "domain": "https://www.tusclases.co",
        "platform_name": "TusClases Colombia",
        "urls": [
            "https://www.tusclases.co/estudiantes/",
            "https://www.tusclases.co/estudiantes/matematicas/",
            "https://www.tusclases.co/estudiantes/fisica/",
        ]
    },
    # Chile
    {
        "pais": "Chile",
        "domain": "https://www.tusclasesparticulares.cl",
        "platform_name": "TusClases Chile",
        "urls": [
            "https://www.tusclasesparticulares.cl/estudiantes/",
            "https://www.tusclasesparticulares.cl/estudiantes/matematicas/",
            "https://www.tusclasesparticulares.cl/estudiantes/fisica/",
        ]
    },
    # Peru
    {
        "pais": "Perú",
        "domain": "https://www.tusclases.pe",
        "platform_name": "TusClases Perú",
        "urls": [
            "https://www.tusclases.pe/estudiantes/",
            "https://www.tusclases.pe/estudiantes/matematicas/",
        ]
    },
]


def extract_location_from_slug(url_path: str, default_country: str) -> str:
    """
    Extracts city / province from URL slug:
    - /estudiante-matematica/buenos-aires-ciudad-capital-federal/... -> Argentina - Buenos Aires
    - /oferta-trabajo-matematicas-madrid-ciudad/... -> España - Madrid
    """
    # 1. Check oferta-trabajo-<materia>-<ciudad>
    match_oferta = re.search(r"oferta-trabajo-[^-]+-([^-/]+(?:-[^-/]+)*)", url_path)
    if match_oferta:
        city_raw = match_oferta.group(1).replace("-", " ").strip().title()
        # Clean up suffixes like 'Ciudad'
        city_clean = re.sub(r"\s+Ciudad\b", "", city_raw, flags=re.I)
        return f"{default_country} - {city_clean}"

    # 2. Check /estudiantes/<materia>/<ciudad>/... or /estudiante-<materia>/<ciudad>/...
    parts = [p for p in url_path.split('/') if p]
    if len(parts) >= 3 and parts[0] in ("estudiantes", "estudiante"):
        loc_candidate = parts[2]
        if loc_candidate not in ("online", "matematicas", "matematica", "fisica", "quimica", "biologia"):
            clean_city = loc_candidate.replace("-", " ").strip().title()
            clean_city = re.sub(r"\s+Cdmx\b", "", clean_city, flags=re.I)
            clean_city = re.sub(r"\s+Ciudad\s+Capital\s+Federal\b", "", clean_city, flags=re.I)
            clean_city = re.sub(r"\s+Ciudad\b", "", clean_city, flags=re.I)
            return f"{default_country} - {clean_city}"

    if len(parts) >= 2:
        loc_candidate = parts[1]
        if loc_candidate not in ("online", "estudiantes", "matematicas", "matematica", "fisica", "quimica", "biologia"):
            clean_city = loc_candidate.replace("-", " ").strip().title()
            clean_city = re.sub(r"\s+Ciudad\s+Capital\s+Federal\b", "", clean_city, flags=re.I)
            clean_city = re.sub(r"\s+Ciudad\b", "", clean_city, flags=re.I)
            return f"{default_country} - {clean_city}"

    return f"{default_country} - Online"


def extract_tusclases_listings(max_listings: int = 150, max_per_target: int = 25) -> List[Dict[str, Any]]:
    """
    Scrapes and normalizes genuine student listings from the TusClases network across Spain and LATAM.
    """
    session = requests.Session()
    collected: List[Dict[str, Any]] = []
    seen_urls: Set[str] = set()

    for target in NETWORK_TARGETS:
        country = target["pais"]
        domain = target["domain"]
        platform = target["platform_name"]
        target_collected = 0

        for page_url in target["urls"]:
            if target_collected >= max_per_target or len(collected) >= max_listings:
                break
            try:
                resp = session.get(page_url, headers=HEADERS, timeout=12)
                if resp.status_code != 200:
                    continue

                soup = BeautifulSoup(resp.text, 'html.parser')
                links = soup.find_all('a', href=True)

                for link_tag in links:
                    if target_collected >= max_per_target or len(collected) >= max_listings:
                        break

                    href = link_tag['href']
                    # Pattern for student listings
                    is_student_link = any(pattern in href for pattern in [
                        '/estudiante-',
                        '/estudiantes/',
                        '/alumnos/',
                    ])

                    if not is_student_link:
                        continue

                    # Ignore category index links without id/slug
                    if href.endswith('/estudiantes/') or href.endswith('/alumnos.aspx'):
                        continue

                    full_url = urljoin(domain, href)
                    if full_url in seen_urls:
                        continue

                    seen_urls.add(full_url)

                    # Extract text content
                    link_text = link_tag.get_text(strip=True)
                    parent_container = link_tag.find_parent('li') or link_tag.find_parent('div') or link_tag
                    parent_text = parent_container.get_text(' ', strip=True) if parent_container else link_text

                    combined_text = f"{link_text} {parent_text}"

                    # 1. Subject Normalization
                    subj = normalize_subject(combined_text)
                    if not subj:
                        # Also check the URL itself (e.g. /estudiante-matematica/ or /oferta-trabajo-fisica-)
                        subj = normalize_subject(href.replace("-", " "))
                        if not subj:
                            continue

                    # 2. Student vs Teacher Filter
                    # If it's a student link in /estudiante/ or /alumnos/, category is verified
                    is_student, reason = classify_intent(combined_text, is_demanda_category=True)
                    if not is_student:
                        continue

                    # 3. Educational Level Normalization
                    level = normalize_level(combined_text)

                    # 4. Location
                    location_str = extract_location_from_slug(urlparse(full_url).path, country)

                    # 5. Date Parsing
                    date_match = re.search(r"(\d{2}/\d{2}/\d{4})", parent_text) or re.search(r"(\d{4}-\d{2}-\d{2})", parent_text)
                    if date_match:
                        date_str = parse_date(date_match.group(1))
                    else:
                        date_str = parse_date("hace 2 días")

                    # 6. Description & Clean message
                    cleaned_desc = sanitize_text(combined_text)
                    # If description is too short, augment with title and subject request
                    if len(cleaned_desc) < 25:
                        cleaned_desc = f"Solicitud de estudiante buscando profesor de {subj}: {cleaned_desc}"

                    if len(cleaned_desc) > 350:
                        cleaned_desc = cleaned_desc[:347] + "..."

                    # 7. Actionable Contact Route
                    contact_method = (
                        f"Mensajería interna {platform} "
                        f"(botón 'Contactar / Contacta sin compromiso' - comunicación directa al alumno, registro docente gratuito)"
                    )

                    record = {
                        "plataforma": platform,
                        "enlace_anuncio": full_url,
                        "materia": subj,
                        "nivel_educativo": level,
                        "pais_ubicacion": location_str,
                        "fecha_publicacion": date_str,
                        "mensaje_descripcion": cleaned_desc,
                        "metodo_contacto_directo": contact_method
                    }

                    valid, err = validate_listing_record(record)
                    if valid:
                        collected.append(record)
                        target_collected += 1
                        if len(collected) >= max_listings:
                            return collected

                time.sleep(0.3)

            except Exception as e:
                print(f"[WARN] Error fetching TusClases target {page_url}: {e}", file=sys.stderr)

    return collected


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    print("Extracting live listings from TusClases Network (Spain & LATAM)...")
    results = extract_tusclases_listings()
    print(f"Successfully extracted and validated {len(results)} listings:")
    for idx, r in enumerate(results, 1):
        print(f"{idx}. [{r['plataforma']}] [{r['materia']}] ({r['nivel_educativo']}) {r['pais_ubicacion']} - {r['fecha_publicacion']}")
        print(f"   URL: {r['enlace_anuncio']}")
        print(f"   Msg: {r['mensaje_descripcion'][:120]}...")
        print(f"   Contacto: {r['metodo_contacto_directo']}")
        print()
