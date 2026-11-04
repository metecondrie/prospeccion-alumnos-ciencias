#!/usr/bin/env python3
"""
telegram_centinela.py
Bot Centinela en Tiempo Real para Telegram (Telethon Client).
Escucha mensajes en vivo en todos los grupos y supergrupos de estudiantes donde esté unida la cuenta,
detecta solicitudes de alumnos en ciencias exactas, audita con IA (Gemini / Groq / Mistral) en 1 segundo
y envía una alerta push instantánea al celular del Prof. Alejo con el enlace para contactar al alumno.
Incluye sistema de logging continuo a archivo (logs/centinela.log) y latido en vivo (heartbeat).
"""

import os
import sys
import json
import time
import re
import asyncio
from datetime import datetime
from typing import Dict, Any

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Ensure scripts dir is on sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
DESKTOP_DIR = r"E:\OneDrive\Escritorio\Prospeccion_Alumnos_Ciencias"

if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from prospector import load_env_file, call_multiprovider_batch, normalize_item
from common_filter import normalize_subject, normalize_level, sanitize_text
from extract_telegram import send_telegram_notification

load_env_file()

DATA_APPROVED = os.path.join(PROJECT_ROOT, "data", "dataset_canonico_auditado.json")
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "centinela.log")

STATS = {
    "start_time": datetime.now(),
    "messages_scanned": 0,
    "ai_audits": 0,
    "approved_leads": 0,
    "discarded_leads": 0
}


def log_event(text: str, print_to_console: bool = True):
    """Escribe en logs/centinela.log y opcionalmente en pantalla."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{now_str}] {text}"
    if print_to_console:
        print(formatted)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
        # Espejar en escritorio si existe la carpeta
        desktop_logs = os.path.join(DESKTOP_DIR, "logs")
        if os.path.exists(DESKTOP_DIR):
            os.makedirs(desktop_logs, exist_ok=True)
            with open(os.path.join(desktop_logs, "centinela.log"), "a", encoding="utf-8") as f:
                f.write(formatted + "\n")
    except Exception:
        pass


# Palabras clave de activación rápida (Fast Heuristic)
FAST_TRIGGERS = [
    r"\bprofesor\b", r"\bprofesora\b", r"\bprofe\b", r"\bparticular\b",
    r"\bclases\b", r"\btutor\b", r"\btutora\b", r"\benseñ\b", r"\bexplic\b",
    r"\bparcial\b", r"\bfinal\b", r"\bexamen\b", r"\bparcialito\b",
    r"\bcbc\b", r"\buba\s*xxi\b", r"\bapoyo\b", r"\bayuda\b"
]

FAST_SUBJECTS = [
    r"\bmatem[aá]tic", r"\bf[ií]sic", r"\bqu[ií]mic", r"\bbiolog[ií]",
    r"\ban[aá]lisis\b", r"\b[aá]lgebra\b", r"\bbiof[ií]sic", r"\bc[aá]lculo\b",
    r"\bgeometr[ií]a\b", r"\baritm[eé]tica\b", r"\bprobabilidad\b", r"\bestad[ií]stic\b"
]


def fast_match(text: str) -> bool:
    """Filtro ultrarrápido por expresiones regulares antes de gastar llamada a la IA."""
    t = text.lower()
    has_trigger = any(re.search(pat, t) for pat in FAST_TRIGGERS)
    has_subject = any(re.search(pat, t) for pat in FAST_SUBJECTS)
    return has_trigger and has_subject


def save_approved_lead(lead: Dict[str, Any]):
    """Guarda el nuevo alumno en data/dataset_canonico_auditado.json de forma incremental y sincronizada."""
    targets = [DATA_APPROVED]
    desktop_target = os.path.join(DESKTOP_DIR, "data", "dataset_canonico_auditado.json")
    if os.path.exists(os.path.dirname(desktop_target)):
        targets.append(desktop_target)

    for target_path in targets:
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        existing = []
        if os.path.exists(target_path):
            try:
                with open(target_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except Exception:
                existing = []

        seen_ids = {it.get("id") for it in existing}
        if lead.get("id") not in seen_ids:
            existing.append(lead)
            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)

    log_event(f"[BASE DE DATOS] Alumno registrado con éxito. Total acumulado: {len(existing)} alumnos.")


def send_centinela_push_alert(lead: Dict[str, Any], group_title: str, student_username: str):
    """Envía la alerta al bot de Telegram personal de Alejo."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        return

    user_link = f"https://t.me/{student_username}" if student_username else lead.get("enlace al anuncio", "")
    author_display = f"@{student_username}" if student_username else lead.get("nombre", "Estudiante en grupo")

    msg = (
        "🚨 <b>¡CENTINELA TELEGRAM EN VIVO!</b>\n"
        f"<i>Nuevo alumno detectado en el grupo:</i> <b>{group_title}</b>\n\n"
        f"👤 <b>Alumno:</b> {author_display}\n"
        f"📚 <b>Materia:</b> {lead.get('materia', 'Ciencias Exactas')}\n"
        f"🎯 <b>Nivel:</b> {lead.get('nivel educativo', 'Universitario / Secundario')}\n\n"
        f"💬 <b>Mensaje:</b> <i>\"{lead.get('mensaje/descripción', '')[:250]}\"</i>\n\n"
        f"👉 <a href='{user_link}'><b>Abrir chat y contactar al alumno</b></a>"
    )

    send_telegram_notification(bot_token, chat_id, msg)


async def heartbeat_loop(client):
    """Latido continuo cada 60s para mostrar en pantalla que el Centinela está 100% activo y saludable."""
    while True:
        await asyncio.sleep(60)
        now_str = datetime.now().strftime("%H:%M:%S")
        status_line = (
            f"[LATIDO {now_str}] 🟢 Centinela en guardia | "
            f"Msgs escaneados: {STATS['messages_scanned']} | "
            f"Auditados por IA: {STATS['ai_audits']} | "
            f"Alumnos aprobados: {STATS['approved_leads']}"
        )
        log_event(status_line, print_to_console=True)


async def main():
    print("=" * 70)
    print("   SISTEMA CENTINELA TELEGRAM EN TIEMPO REAL - PROF. ALEJO ONGARO")
    print("   Escucha continua de grupos de estudiantes con auditoría de IA en vivo")
    print("=" * 70)

    api_id = os.environ.get("TELEGRAM_API_ID")
    api_hash = os.environ.get("TELEGRAM_API_HASH")

    if not api_id or not api_hash:
        print("\n[ERROR] TELEGRAM_API_ID o TELEGRAM_API_HASH no configurados en .env.")
        return

    from telethon import TelegramClient, events

    try:
        api_id_int = int(api_id)
    except ValueError:
        print(f"[ERROR] TELEGRAM_API_ID debe ser un número entero. Valor: {api_id}")
        return

    # Buscar sesión en candidatos
    session_candidates = [
        os.path.join(PROJECT_ROOT, "centinela_session"),
        os.path.join(DESKTOP_DIR, "centinela_session"),
        os.path.join(os.getcwd(), "centinela_session")
    ]
    target_session = None
    for cand in session_candidates:
        if os.path.exists(cand + ".session"):
            target_session = cand
            break
    if not target_session:
        target_session = os.path.join(PROJECT_ROOT, "centinela_session")

    print(f"\nIniciando cliente Telegram con sesión: {target_session}.session")
    log_event(f"[INICIO] Arrancando Centinela con sesión {target_session}")

    client = TelegramClient(target_session, api_id_int, api_hash)
    await client.start()

    me = await client.get_me()
    print(f"\n[CENTINELA CONECTADO Y AUTENTICADO]")
    print(f"Cuenta: {me.first_name} (@{me.username or 'sin_username'}) | ID: {me.id}")
    print(f"Registro en tiempo real: {LOG_FILE}")
    print("\nEscuchando mensajes en vivo en todos tus grupos de estudiantes...")
    print("Emitiendo latido de actividad cada 60 segundos...")
    print("Presiona Ctrl + C en cualquier momento para detener.\n" + "-" * 70)

    log_event(f"[CONEXION EXITOSA] Usuario: {me.first_name} (@{me.username}) ID: {me.id}")

    # Iniciar tarea en segundo plano de latido (heartbeat)
    asyncio.create_task(heartbeat_loop(client))

    @client.on(events.NewMessage)
    async def handler(event):
        # Ignorar mensajes de chats privados directos o enviados por uno mismo
        if event.is_private or event.out:
            return

        text = event.raw_text or ""
        STATS["messages_scanned"] += 1

        # Registrar de forma silenciosa en el archivo cada 10 mensajes para auditoría
        if STATS["messages_scanned"] % 10 == 0:
            log_event(f"[AUDITORIA INTERNA] Total mensajes recibidos en grupos: {STATS['messages_scanned']}", print_to_console=False)

        if len(text) < 15:
            return

        # 1. Filtro rápido de regex para descartar charlas que no buscan profe
        if not fast_match(text):
            return

        STATS["ai_audits"] += 1
        chat = await event.get_chat()
        chat_title = getattr(chat, 'title', 'Grupo Telegram')
        sender = await event.get_sender()
        sender_name = f"{getattr(sender, 'first_name', '')} {getattr(sender, 'last_name', '')}".strip() or "Estudiante"
        sender_user = getattr(sender, 'username', '')

        log_event(f"\n🔥 [POTENCIAL ALUMNO DETECTADO] Grupo: '{chat_title}' | Autor: {sender_name} (@{sender_user})")
        print(f"   Mensaje: \"{text[:120]}...\"")
        print(f"   🤖 Consultando Triple Motor de IA (Gemini Flash Lite / Groq / Mistral)...")

        # 2. Construir payload y validar con Triple Motor de IA
        candidate_item = {
            "id": f"tg_live_{event.chat_id}_{event.id}",
            "plataforma": f"Telegram ({chat_title})",
            "materia": normalize_subject(text) or "Ciencias Exactas",
            "ubicacion": "Argentina / LATAM - Grupo Estudiantil Telegram",
            "mensaje": text,
            "enlace": f"https://t.me/c/{abs(event.chat_id)}/{event.id}" if not getattr(chat, 'username', None) else f"https://t.me/{chat.username}/{event.id}"
        }

        try:
            results = call_multiprovider_batch([candidate_item])
            if results and isinstance(results, list):
                res = results[0]
                if res.get("is_student") is True or res.get("decision_ia") == "Aprobado":
                    STATS["approved_leads"] += 1
                    log_event(f"   ✅ [APROBADO POR IA] {res.get('justificacion_ia')}")

                    normalized_lead = normalize_item({
                        "id": candidate_item["id"],
                        "plataforma": candidate_item["plataforma"],
                        "país/ubicación": candidate_item["ubicacion"],
                        "nombre": sender_name,
                        "persona_id": sender_user or f"user_{sender.id}",
                        "materia": candidate_item["materia"],
                        "nivel educativo": normalize_level(text),
                        "enlace al anuncio": candidate_item["enlace"],
                        "mensaje/descripción": sanitize_text(text),
                        "método de contacto directo": f"Telegram (@{sender_user})" if sender_user else "Telegram (Mensaje directo en grupo)",
                        "decision_ia": "Aprobado",
                        "justificacion_ia": res.get("justificacion_ia", "Detectado en vivo por Centinela")
                    })

                    # Guardar en base de datos incremental
                    save_approved_lead(normalized_lead)

                    # Enviar alerta push inmediata al celular
                    send_centinela_push_alert(normalized_lead, chat_title, sender_user)
                    log_event(f"   📲 [ALERTA ENVIADA] Notificación push entregada a tu celular con éxito.")
                else:
                    STATS["discarded_leads"] += 1
                    log_event(f"   ❌ [DESCARTADO POR IA] {res.get('justificacion_ia')}")
        except Exception as e:
            log_event(f"   ⚠️ [ERROR EN AUDITORÍA IA] {e}")

    await client.run_until_disconnected()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log_event("[CENTINELA DETENIDO] Sesión cerrada correctamente por el usuario.")
