"""
extract_telegram.py
Extractor y monitor de canales y grupos públicos de Telegram para estudiantes de ciencias exactas.
Permite rastrear publicaciones en canales públicos de Telegram (vía vista web oficial https://t.me/s/)
y enviar notificaciones instantáneas de nuevos prospectos a un bot/chat de Telegram.
"""

import os
import sys
import json
import time
from typing import List, Dict, Any, Set
from urllib.parse import urljoin
import urllib.request
import urllib.error
import requests
from bs4 import BeautifulSoup

# Ensure scripts directory is on sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from common_filter import (
    classify_intent,
    normalize_subject,
    normalize_level,
    parse_date,
    sanitize_text,
    validate_listing_record
)

CONFIG_PATH = os.path.join(PROJECT_ROOT, "data", "telegram_channels.json")
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
}


def load_channels_config() -> List[Dict[str, Any]]:
    """Carga los canales configurados en data/telegram_channels.json o devuelve defaults."""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [c for c in data.get("channels", []) if c.get("active", True)]
        except Exception as e:
            print(f"[Telegram] Error leyendo configuración: {e}", file=sys.stderr)

    return [
        {"username": "clasesparticulares", "name": "Clases Particulares", "country": "España / LATAM"},
        {"username": "profesoresparticulares", "name": "Profesores y Clases", "country": "Argentina / Uruguay"},
        {"username": "comunidad_cbc", "name": "Comunidad CBC", "country": "Argentina"}
    ]


def extract_telegram_listings(max_listings: int = 30) -> List[Dict[str, Any]]:
    """
    Rastrea canales y grupos públicos de Telegram vía vista web oficial (https://t.me/s/<channel>).
    Extrae solicitudes genuinas de alumnos buscando profesor particular en ciencias exactas.
    """
    channels = load_channels_config()
    session = requests.Session()
    collected: List[Dict[str, Any]] = []
    seen_urls: Set[str] = set()

    for ch in channels:
        if len(collected) >= max_listings:
            break

        username = ch.get("username", "").strip().lstrip("@")
        country = ch.get("country", "Hispanoamérica")
        channel_name = ch.get("name", username)
        if not username:
            continue

        url = f"https://t.me/s/{username}"
        try:
            time.sleep(1.0)
            resp = session.get(url, headers=HEADERS, timeout=10)
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, 'html.parser')
            msg_wraps = soup.find_all('div', class_='tgme_widget_message_wrap')

            for wrap in msg_wraps:
                if len(collected) >= max_listings:
                    break

                text_div = wrap.find('div', class_='tgme_widget_message_text')
                if not text_div:
                    continue

                raw_text = text_div.get_text(' ', strip=True)
                if not raw_text or len(raw_text) < 15:
                    continue

                # Enlace permanente al mensaje
                date_anchor = wrap.find('a', class_='tgme_widget_message_date')
                msg_url = date_anchor['href'] if date_anchor and date_anchor.has_attr('href') else f"https://t.me/{username}"
                if msg_url in seen_urls:
                    continue
                seen_urls.add(msg_url)

                # Fecha del mensaje
                time_tag = wrap.find('time')
                raw_date = time_tag.get('datetime', '') if time_tag else ""
                parsed_date = parse_date(raw_date)

                # 1. Materia de ciencias exactas
                subj = normalize_subject(raw_text)
                if not subj:
                    continue

                # 2. Intención del estudiante (no profesor vendiendo)
                is_student, reason = classify_intent(raw_text, is_demanda_category=False)
                if not is_student:
                    continue

                # 3. Nivel educativo
                level = normalize_level(raw_text)

                cleaned_desc = sanitize_text(raw_text)
                if len(cleaned_desc) > 350:
                    cleaned_desc = cleaned_desc[:347] + "..."

                record = {
                    "plataforma": f"Telegram (@{username})",
                    "enlace_anuncio": msg_url,
                    "materia": subj,
                    "nivel_educativo": level,
                    "pais_ubicacion": f"{country} - Canal Estudiantil",
                    "fecha_publicacion": parsed_date,
                    "mensaje_descripcion": cleaned_desc,
                    "metodo_contacto_directo": f"Telegram (@{username}) - Mensaje privado o respuesta al post en el canal"
                }

                valid, err = validate_listing_record(record)
                if valid:
                    collected.append(record)

        except Exception as e:
            print(f"[Telegram] Error al consultar @{username}: {e}", file=sys.stderr)

    return collected


def send_telegram_notification(bot_token: str, chat_id: str, message: str) -> bool:
    """
    Envía un mensaje o alerta push al chat de Telegram personal del usuario
    usando la API oficial de bots (https://api.telegram.org/bot<token>/sendMessage).
    """
    if not bot_token or not chat_id:
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = json.dumps({
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"[Telegram Alert] Error enviando notificación: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    print("Probando extractor de Telegram...")
    items = extract_telegram_listings(max_listings=10)
    print(f"Resultados encontrados: {len(items)}")
    for it in items:
        print(it)
