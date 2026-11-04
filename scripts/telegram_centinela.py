#!/usr/bin/env python3
"""
telegram_centinela.py
Bot Centinela en Tiempo Real para Telegram (Telethon Client).
Escucha mensajes en vivo en todos los grupos y supergrupos de estudiantes donde esté unida la cuenta,
detecta solicitudes de alumnos en ciencias exactas, audita con IA en 1 segundo y envía una alerta
push instantánea al celular del Prof. Alejo con el enlace para contactar al alumno.
"""

import os
import sys
import json
import time
import re
import asyncio
from typing import Dict, Any

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Ensure scripts dir is on sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from prospector import load_env_file, call_multiprovider_batch, normalize_item
from common_filter import normalize_subject, normalize_level, sanitize_text
from extract_telegram import send_telegram_notification

load_env_file()

DATA_APPROVED = os.path.join(PROJECT_ROOT, "data", "dataset_canonico_auditado.json")
SESSION_FILE = os.path.join(PROJECT_ROOT, "centinela_session")

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
    """Guarda el nuevo alumno en data/dataset_canonico_auditado.json de forma incremental."""
    os.makedirs(os.path.dirname(DATA_APPROVED), exist_ok=True)
    existing = []
    if os.path.exists(DATA_APPROVED):
        try:
            with open(DATA_APPROVED, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = []

    # Verificar si ya existe por ID o URL
    seen_ids = {it.get("id") for it in existing}
    if lead.get("id") in seen_ids:
        return

    existing.append(lead)
    with open(DATA_APPROVED, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    print(f"\n[CENTINELA] Base de datos actualizada: {len(existing)} alumnos registrados.")


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


async def main():
    print("=" * 70)
    print("   SISTEMA CENTINELA TELEGRAM EN TIEMPO REAL - PROF. ALEJO ONGARO")
    print("   Escucha continua de grupos de estudiantes con auditoría de IA en vivo")
    print("=" * 70)

    api_id = os.environ.get("TELEGRAM_API_ID")
    api_hash = os.environ.get("TELEGRAM_API_HASH")

    if not api_id or not api_hash:
        print("\n[CONFIGURACIÓN REQUERIDA]")
        print("Para escuchar grupos en tiempo real con tu cuenta, Telegram requiere:")
        print("1. Entrar en https://my.telegram.org y poner tu número de teléfono.")
        print("2. Ir a 'API development tools'.")
        print("3. Copiar tu 'App api_id' y 'App api_hash'.")
        print("4. Pegarlos en tu archivo .env como:")
        print("   TELEGRAM_API_ID=tu_api_id")
        print("   TELEGRAM_API_HASH=tu_api_hash\n")

        api_id_input = input("Ingresa tu TELEGRAM_API_ID (o presiona Enter para salir): ").strip()
        if not api_id_input:
            print("Operación cancelada. Configura TELEGRAM_API_ID en .env cuando quieras activarlo.")
            return

        api_hash_input = input("Ingresa tu TELEGRAM_API_HASH: ").strip()
        if not api_hash_input:
            print("Operación cancelada.")
            return

        api_id = api_id_input
        api_hash = api_hash_input

        # Guardar en .env
        env_path = os.path.join(PROJECT_ROOT, ".env")
        with open(env_path, "a", encoding="utf-8") as f:
            f.write(f"\nTELEGRAM_API_ID={api_id}\nTELEGRAM_API_HASH={api_hash}\n")
        print(f"[OK] Credenciales guardadas en {env_path}")

    from telethon import TelegramClient, events

    try:
        api_id_int = int(api_id)
    except ValueError:
        print(f"[ERROR] TELEGRAM_API_ID debe ser un número entero. Valor recibido: {api_id}")
        return

    print("\nIniciando cliente Telegram...")
    client = TelegramClient(SESSION_FILE, api_id_int, api_hash)
    await client.start()

    me = await client.get_me()
    print(f"\n[CENTINELA CONECTADO]")
    print(f"Cuenta autenticada: {me.first_name} (@{me.username or 'sin_username'})")
    print(f"ID de Usuario: {me.id}")
    print("\nEscuchando mensajes en vivo en todos tus grupos de estudiantes...")
    print("Presiona Ctrl + C en cualquier momento para detener.\n" + "-" * 70)

    @client.on(events.NewMessage)
    async def handler(event):
        # Ignorar mensajes de chats privados directos o enviados por uno mismo
        if event.is_private or event.out:
            return

        text = event.raw_text or ""
        if len(text) < 15:
            return

        # 1. Filtro rápido de regex para no gastar llamadas de IA innecesarias
        if not fast_match(text):
            return

        chat = await event.get_chat()
        chat_title = getattr(chat, 'title', 'Grupo Telegram')
        sender = await event.get_sender()
        sender_name = f"{getattr(sender, 'first_name', '')} {getattr(sender, 'last_name', '')}".strip() or "Estudiante"
        sender_user = getattr(sender, 'username', '')

        print(f"\n[DETECTADO EN VIVO] Grupo: '{chat_title}' | Autor: {sender_name} (@{sender_user})")
        print(f"Texto: \"{text[:120]}...\"")

        # 2. Construir payload y validar con Triple Motor de IA
        candidate_item = {
            "id": f"tg_live_{event.chat_id}_{event.id}",
            "plataforma": f"Telegram ({chat_title})",
            "materia": normalize_subject(text) or "Ciencias Exactas",
            "ubicacion": "Argentina / LATAM - Grupo Estudiantil Telegram",
            "mensaje": text,
            "enlace": f"https://t.me/c/{abs(event.chat_id)}/{event.id}" if not getattr(chat, 'username', None) else f"https://t.me/{chat.username}/{event.id}"
        }

        print("  -> Auditando intención con Inteligencia Artificial...")
        try:
            results = call_multiprovider_batch([candidate_item])
            if results and isinstance(results, list):
                res = results[0]
                if res.get("is_student") is True or res.get("decision_ia") == "Aprobado":
                    print(f"  [APROBADO POR IA] {res.get('justificacion_ia')}")

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
                    print(f"  [ALERTA ENVIADA] Notificación push entregada a tu celular con éxito.")
                else:
                    print(f"  [DESCARTADO POR IA] {res.get('justificacion_ia')}")
        except Exception as e:
            print(f"  [ERROR EN AUDITORÍA IA] {e}", file=sys.stderr)

    await client.run_until_disconnected()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[CENTINELA DETENIDO] Sesión cerrada correctamente.")
