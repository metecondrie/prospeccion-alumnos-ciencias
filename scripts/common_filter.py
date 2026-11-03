"""
common_filter.py
Deterministic intent classifier, subject normalizer, educational level normalizer,
date parser, and URL liveness validator for student tutor listings.
Adheres strictly to the specification defined in spec_miner_survey_3 handoff.md.
"""

import re
import sys
from datetime import datetime, date, timedelta
from typing import Optional, Tuple, List, Dict, Any
from urllib.parse import urlparse
import requests

# Canonical valid subjects and levels
VALID_SUBJECTS = {"Física", "Química", "Biología", "Matemáticas"}
VALID_LEVELS = {"Secundario", "Universitario"}

# Teacher Blacklist Patterns (spec_miner_survey_3 handoff § 5.4)
TEACHER_BLACKLIST_PATTERNS = [
    r"\bdoy clases\b",
    r"\bofrezco clases\b",
    r"\bimparto clases\b",
    r"\bprofesor con (?:amplia )?experiencia\b",
    r"\bprofesora con (?:amplia )?experiencia\b",
    r"\bdocente con (?:amplia )?experiencia\b",
    r"\blicenciad[oa] ofrece\b",
    r"\bgraduad[oa] ofrece\b",
    r"\bingenier[oa] ofrece\b",
    r"\bclases particulares a domicilio y online\b",
    r"\bprimera clase gratis\b",
    r"\b1ª clase gratis\b",
    r"\b1a clase gratis\b",
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
    r"\bprofesora de franc[eé]s nativa\b",
    r"\bprofesor particular titulado\b",
    r"\baprende y aprueba conmigo\b",
    r"\bexperiencia docente\b",
    r"\bprofesor[a]? especializada?\b",
    r"\bcon (?:amplia )?experiencia docente\b",
    r"\bclases amenas\b",
    r"\bclases individuales\b",
    r"\bbuenos resultados\b",
    r"\bexcelentes resultados\b",
    r"\bhorario flexible\b",
    r"\b[uú]nete a nuestro equipo\b",
    r"\bcoordinador de centro\b",
    r"\bforma parte de nuestro equipo\b",
    r"\bacademia gostudent\b",
    r"\bequipo educativo\b",
    r"\bselecci[oó]n de personal\b",
    r"\bcontrato\s*:",
    r"\btitulaci[oó]n\s+requerida\b",
    r"\baut[oó]nomo\s*/\s*freelance\b",
    r"/oferta-trabajo-",
    r"\boferta-trabajo\b",
    r"\bexperiencia:\s*\d+\s*a[ñn]o",
    r"\bbuscamos\s+profesor(?:es|as?)?\b",
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

# Student Whitelist Patterns (spec_miner_survey_3 handoff § 5.4)
STUDENT_WHITELIST_PATTERNS = [
    r"\bbusco profesor\b",
    r"\bbusco profesora\b",
    r"\bbusco profe\b",
    r"\bbusco docente\b",
    r"\bbusco maestro\b",
    r"\bbusco maestra\b",
    r"\bbusco tutor\b",
    r"\bbusco tutora\b",
    r"\bbusco particular\b",
    r"\bbusco a alguien que me enseñe\b",
    r"\bbusco ayuda con\b",
    r"\bestoy buscando\b",
    r"\bnecesito profesor\b",
    r"\bnecesito profesora\b",
    r"\bnecesito profe\b",
    r"\bnecesito clases\b",
    r"\bnecesito ayuda\b",
    r"\bnecesito apoyo\b",
    r"\bnecesito recibir clases\b",
    r"\bpreciso profesor\b",
    r"\bpreciso profesora\b",
    r"\bse busca profesor\b",
    r"\bse busca profesora\b",
    r"\bse necesita profesor\b",
    r"\bse necesita profesora\b",
    r"\bpara preparar examen\b",
    r"\bpara rendir\b",
    r"\bpara selectividad\b",
    r"\bpara ebau\b",
    r"\bpara evau\b",
    r"\bpara pau\b",
    r"\bpara el cbc\b",
    r"\bpara parcial\b",
    r"\bpara final\b",
    r"\bestoy cursando\b",
    r"\bestoy en (?:1º|2º|3º|4º|primer|segundo|tercer|cuarto)\b",
    r"\bvoy a (?:1º|2º|3º|4º|primer|segundo|tercer|cuarto)\b",
    r"\bvoy a rendir\b",
    r"\btengo que recuperar\b",
    r"\bme cuesta entender\b",
    r"\bmi hij[oa] necesita\b",
    r"\bpara un niño de\b",
    r"\bpara una niña de\b",
    r"\balguien que me explique\b",
    r"\bclases de apoyo\b",
    r"\bapoyo escolar\b",
    r"\brefuerzo escolar\b",
]

# Subject Keywords Mapping
SUBJECT_KEYWORDS = {
    "Matemáticas": [
        r"\bmatem[aá]ticas?\b",
        r"\bmates?\b",
        r"\b[aá]lgebra\b",
        r"\bc[aá]lculo\b",
        r"\bgeometr[ií]a\b",
        r"\btrigonometr[ií]a\b",
        r"\ban[aá]lisis matem[aá]tico\b",
        r"\bestad[ií]stica\b",
        r"\bprobabilidad\b",
        r"\bderivadas?\b",
        r"\bintegrales?\b",
        r"\bmatrices\b",
        r"\baritm[eé]tica\b",
        r"\bfunciones?\b",
        r"\bl[ií]mites?\b",
        r"\bmate 51\b",
        r"\bmate 66\b",
        r"\banalisis 66\b",
    ],
    "Física": [
        r"\bf[ií]sica\b",
        r"\bcinem[aá]tica\b",
        r"\bdin[aá]mica\b",
        r"\best[aá]tica\b",
        r"\btermodin[aá]mica\b",
        r"\belectromagnetismo\b",
        r"\bcircuitos el[eé]ctricos\b",
        r"\b[oó]ptica\b",
        r"\bondas\b",
        r"\bmec[aá]nica\b",
        r"\bbiof[ií]sica\b",
        r"\bfisica 03\b",
        r"\bm[aá]quinas hidr[aá]ulicas\b",
    ],
    "Química": [
        r"\bqu[ií]mica\b",
        r"\bquimica inorg[aá]nica\b",
        r"\bquimica org[aá]nica\b",
        r"\bestequiometr[ií]a\b",
        r"\bfisicoqu[ií]mica\b",
        r"\bbioqu[ií]mica\b",
        r"\bquimica 05\b",
        r"\bdisoluciones\b",
    ],
    "Biología": [
        r"\bbiolog[ií]a\b",
        r"\bgen[eé]tica\b",
        r"\bbiolog[ií]a celular\b",
        r"\bbiolog[ií]a molecular\b",
        r"\bmicrobiolog[ií]a\b",
        r"\bbot[aá]nica\b",
        r"\bzoolog[ií]a\b",
        r"\becolog[ií]a\b",
        r"\bfisiolog[ií]a\b",
        r"\banatom[ií]a\b",
        r"\bhistolog[ií]a\b",
    ]
}

# Educational Level Keywords
UNIVERSITARIO_KEYWORDS = [
    r"\buniversi",
    r"\bfacultad\b",
    r"\bgrado\s+universitari[oa]\b",
    r"\bgrado\s+en\b",
    r"\bt[ií]tulo\s+de\s+grado\b",
    r"\bestudios\s+de\s+grado\b",
    r"\blicenciatura\b",
    r"\bingenier[ií]a\b",
    r"\bcbc\b",
    r"\buba xxi\b",
    r"\bfiuba\b",
    r"\bfceyn\b",
    r"\butn\b",
    r"\buade\b",
    r"\bunc\b",
    r"\budelar\b",
    r"\bunam\b",
    r"\bpregrado\b",
    r"\bterciario\b",
    r"\bcarrera\b",
    r"\bm[aá]ster\b",
    r"\bparcial universitario\b",
    r"\bexamen final universitario\b",
    r"\ban[aá]lisis matem[aá]tico ii?\b",
    r"\bc[aá]lculo [i12]\b",
    r"\bc[aá]lculo diferencial\b",
    r"\bc[aá]lculo integral\b",
    r"\bc[aá]lculo multivariable\b",
]

SECUNDARIO_KEYWORDS = [
    r"\bsecundari",
    r"\bgrado\s+[1-9]\b",
    r"\bgrado\s+1[0-2]\b",
    r"\b(?:[1-9]|1[0-2])[º°]?\s+grado\b",
    r"\b\d+[ºo]?\s*(?:de\s*(?:la\s*)?)?eso\b",
    r"\b(?:1º|2º|3º|4º)\s*eso\b",
    r"\b(?:de\s+la\s+eso)\b",
    r"\b(?:educaci[oó]n\s+secundaria(?:\s+obligatoria)?)\b",
    r"\bbachillerato\b",
    r"\bbachi\b",
    r"\b\d+[ºo]?\s*(?:de\s*(?:el\s*)?)?bachillerato\b",
    r"\bselectividad\b",
    r"\bebau\b",
    r"\bevau\b",
    r"\bpau\b",
    r"\bpreparatoria\b",
    r"\bprepa\b",
    r"\bcch\b",
    r"\bvocacional\b",
    r"\benseñanza media\b",
    r"\beducaci[oó]n media\b",
    r"\bpolimodal\b",
    r"\bcolegio secundario\b",
    r"\bpaes\b",
    r"\bsaber 11\b",
    r"\bniñ[oa] de \d+ años\b",
    r"\bchico de \d+ años\b",
    r"\bchica de \d+ años\b",
    r"\btercer año del secundario\b",
    r"\bcuarto año del secundario\b",
    r"\bsegundo año del secundario\b",
    r"\bprimer año del secundario\b",
    r"\b3 año de secundaria\b",
]

def classify_intent(text: str, is_demanda_category: bool = False) -> Tuple[bool, str]:
    """
    Classify whether text represents a genuine student request vs teacher offer.
    Returns (is_student, reason).
    """
    text_lower = text.lower()

    # 1. Check Teacher Blacklist
    teacher_matches = []
    for pat in TEACHER_BLACKLIST_PATTERNS:
        if re.search(pat, text_lower):
            teacher_matches.append(pat)

    if teacher_matches:
        # If teacher matches found, strictly reject
        return False, f"Teacher pattern matched: {teacher_matches[0]}"

    # 2. Check Student Whitelist
    student_matches = []
    for pat in STUDENT_WHITELIST_PATTERNS:
        if re.search(pat, text_lower):
            student_matches.append(pat)

    if student_matches:
        return True, f"Student pattern matched: {student_matches[0]}"

    # 3. If in a verified category (e.g. ?demanda=1 or /alumnos/), absence of blacklist qualifies
    if is_demanda_category:
        return True, "Verified demanda category without teacher markers"

    return False, "No student intent patterns found"


def normalize_subject(text: str) -> Optional[str]:
    """
    Identifies exact science subject(s) in text.
    Returns canonical subject or compound string in {'Física', 'Química', 'Biología', 'Matemáticas'}.
    Returns None if no exact science is matched.
    """
    text_lower = text.lower()
    detected_subjects = []

    # Check for explicitly excluded domains (languages, translation, IT without math)
    excluded_patterns = [
        r"\bspanish tutor\b",
        r"\benglish to spanish\b",
        r"\btranslate\b",
        r"\btraducci[oó]n\b",
        r"\bclases de ingl[eé]s\b",
        r"\bprofesor de franc[eé]s\b",
        r"\bfutbol\b",
        r"\bguitarra\b",
        r"\bcam\b",
        r"\bcnc\b",
        r"\bfresa\b",
        r"\bfresadora\b",
        r"\btorno\b",
        r"\bmecanizado\b",
        r"\btorner[ií]a\b",
    ]
    for exp in excluded_patterns:
        if re.search(exp, text_lower):
            # Only allow if an exact science is genuinely mentioned and not just as category artifact
            if not any(re.search(pat, text_lower) for pat in [r"\bmatem[aá]ticas?\b", r"\bf[ií]sica\b", r"\bqu[ií]mica\b", r"\bbiolog[ií]a\b"]):
                return None

    # Check each subject category
    for canonical_name, patterns in SUBJECT_KEYWORDS.items():
        for pat in patterns:
            if re.search(pat, text_lower):
                detected_subjects.append(canonical_name)
                break

    if not detected_subjects:
        return None

    # Maintain canonical ordering: Matemáticas, Física, Química, Biología
    ordered_canonical = ["Matemáticas", "Física", "Química", "Biología"]
    sorted_detected = [s for s in ordered_canonical if s in detected_subjects]

    return ", ".join(sorted_detected)


def normalize_level(text: str) -> str:
    """
    Maps text to either 'Secundario' or 'Universitario'.
    Defaults to 'Secundario' if ambiguous or school context,
    'Universitario' if higher ed context found.
    """
    text_lower = text.lower()

    uni_score = sum(1 for pat in UNIVERSITARIO_KEYWORDS if re.search(pat, text_lower))
    sec_score = sum(1 for pat in SECUNDARIO_KEYWORDS if re.search(pat, text_lower))

    if uni_score > sec_score:
        return "Universitario"
    elif sec_score > 0:
        return "Secundario"

    # Secondary heuristic: look for university degree names or advanced subjects
    if any(k in text_lower for k in ["facultad", "universitari", "carrera", "licenciatura", "ingenier"]):
        return "Universitario"

    return "Secundario"


def parse_date(date_raw: str, reference_date: Optional[date] = None) -> str:
    """
    Parses various date formats and relative timestamps into ISO 8601 'YYYY-MM-DD'.
    Guarantees result <= today (no future dates).
    """
    if reference_date is None:
        ref_date = date.today()
    else:
        ref_date = reference_date

    clean_str = date_raw.strip().lower()

    # Case 1: Already YYYY-MM-DD
    match_iso = re.search(r"(\d{4})-(\d{2})-(\d{2})", clean_str)
    if match_iso:
        y, m, d = int(match_iso.group(1)), int(match_iso.group(2)), int(match_iso.group(3))
        try:
            parsed = date(y, m, d)
            if parsed <= ref_date:
                return parsed.isoformat()
            return ref_date.isoformat()
        except ValueError:
            pass

    # Case 2: DD/MM/YYYY or DD-MM-YYYY
    match_slash = re.search(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})", clean_str)
    if match_slash:
        d, m, y = int(match_slash.group(1)), int(match_slash.group(2)), int(match_slash.group(3))
        try:
            parsed = date(y, m, d)
            if parsed <= ref_date:
                return parsed.isoformat()
            return ref_date.isoformat()
        except ValueError:
            pass

    # Case 3: Relative dates: 'hace X días', 'hace X horas', 'ayer', 'hoy'
    if "hoy" in clean_str or "hace pocas horas" in clean_str or "minuto" in clean_str:
        return ref_date.isoformat()
    if "ayer" in clean_str:
        return (ref_date - timedelta(days=1)).isoformat()

    match_days = re.search(r"hace\s+(\d+)\s+d[ií]as?", clean_str)
    if match_days:
        num_days = int(match_days.group(1))
        return (ref_date - timedelta(days=num_days)).isoformat()

    match_hours = re.search(r"hace\s+(\d+)\s+horas?", clean_str)
    if match_hours:
        return ref_date.isoformat()

    match_weeks = re.search(r"hace\s+(\d+)\s+semanas?", clean_str)
    if match_weeks:
        num_weeks = int(match_weeks.group(1))
        return (ref_date - timedelta(days=num_weeks * 7)).isoformat()

    match_months = re.search(r"hace\s+(\d+)\s+mes(?:es)?", clean_str)
    if match_months:
        num_months = int(match_months.group(1))
        return (ref_date - timedelta(days=num_months * 30)).isoformat()

    # Case 4: Textual month e.g. "30 de octubre de 2026" or "30 oct 2026"
    month_map = {
        "enero": 1, "ene": 1, "febrero": 2, "feb": 2, "marzo": 3, "mar": 3,
        "abril": 4, "abr": 4, "mayo": 5, "may": 5, "junio": 6, "jun": 6,
        "julio": 7, "jul": 7, "agosto": 8, "ago": 8, "septiembre": 9, "sep": 9, "set": 9,
        "octubre": 10, "oct": 10, "noviembre": 11, "nov": 11, "diciembre": 12, "dic": 12
    }
    match_spanish = re.search(r"(\d{1,2})\s+(?:de\s+)?([a-z]+)\s+(?:de\s+)?(\d{4})", clean_str)
    if match_spanish:
        day = int(match_spanish.group(1))
        mon_str = match_spanish.group(2)
        year = int(match_spanish.group(3))
        if mon_str in month_map:
            try:
                parsed = date(year, month_map[mon_str], day)
                if parsed <= ref_date:
                    return parsed.isoformat()
                return ref_date.isoformat()
            except ValueError:
                pass

    return ref_date.isoformat()


def validate_url_liveness(url: str, timeout: int = 8) -> Tuple[bool, int, str]:
    """
    Verifies that a URL is alive (HTTP 200) and does not contain expired listing markers.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept-Language': 'es-ES,es;q=0.9',
    }
    try:
        resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        if resp.status_code != 200:
            return False, resp.status_code, f"Non-200 HTTP response: {resp.status_code}"

        text_lower = resp.text.lower()
        # Expiration markers
        expiration_phrases = [
            "ups! has llegado tarde",
            "este anuncio ha caducado",
            "solicitud finalizada",
            "anuncio ya no está disponible",
            "anuncio no disponible",
            "página no encontrada",
            "404 not found"
        ]
        for phrase in expiration_phrases:
            if phrase in text_lower:
                return False, resp.status_code, f"Expired listing phrase detected: '{phrase}'"

        return True, 200, "OK"
    except Exception as e:
        return False, 0, f"Connection error: {e}"


def sanitize_text(text: str) -> str:
    """
    Cleans raw unquoted newlines and excess whitespace from message descriptions.
    """
    text = re.sub(r"[\r\n\t]+", " ", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def validate_listing_record(record: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validates that a record dictionary satisfies all interface contracts:
    - plataforma: non-empty string
    - enlace_anuncio: valid HTTP/HTTPS URL
    - materia: valid exact science canonical string
    - nivel_educativo: 'Secundario' or 'Universitario'
    - pais_ubicacion: non-empty location string
    - fecha_publicacion: YYYY-MM-DD date <= today
    - mensaje_descripcion: > 15 chars
    - metodo_contacto_directo: > 8 chars
    """
    required_keys = [
        "plataforma", "enlace_anuncio", "materia", "nivel_educativo",
        "pais_ubicacion", "fecha_publicacion", "mensaje_descripcion",
        "metodo_contacto_directo"
    ]
    for k in required_keys:
        if k not in record or not record[k]:
            return False, f"Missing or empty required field: '{k}'"

    # URL
    url = record["enlace_anuncio"]
    parsed_url = urlparse(url)
    if not (parsed_url.scheme in ("http", "https") and parsed_url.netloc):
        return False, f"Invalid URL structure: '{url}'"

    # Materia
    materia = record["materia"]
    parts = [p.strip() for p in materia.split(",")]
    for p in parts:
        if p not in VALID_SUBJECTS:
            return False, f"Invalid subject component: '{p}'. Must be in {VALID_SUBJECTS}"

    # Nivel educativo
    nivel = record["nivel_educativo"]
    if nivel not in VALID_LEVELS:
        return False, f"Invalid educational level: '{nivel}'. Must be in {VALID_LEVELS}"

    # Fecha
    f_str = record["fecha_publicacion"]
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", f_str):
        return False, f"Date '{f_str}' does not match YYYY-MM-DD"
    try:
        f_date = datetime.strptime(f_str, "%Y-%m-%d").date()
        if f_date > date.today():
            return False, f"Future date detected: {f_str}"
    except ValueError:
        return False, f"Invalid date value: {f_str}"

    # Mensaje
    msg = record["mensaje_descripcion"]
    if len(msg) < 15:
        return False, f"Message description too short (<15 chars): '{msg}'"

    # Contacto
    contact = record["metodo_contacto_directo"]
    if len(contact) < 8:
        return False, f"Contact method too short (<8 chars): '{contact}'"

    return True, "Valid"
