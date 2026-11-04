#!/usr/bin/env python3
"""
auto_join_groups.py
Script seguro para unirse automáticamente a los grupos de discusión estudiantiles de ciencias exactas
(CBC, UBA, FIUBA, UTN) usando la sesión activa del Centinela de Telegram.
Aplica retrasos intencionales (rate-limiting) para proteger la cuenta contra FloodWait.
"""

import os
import sys
import json
import time
import asyncio
from telethon import TelegramClient, functions, errors

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from prospector import load_env_file
load_env_file()

CONFIG_PATH = os.path.join(PROJECT_ROOT, "data", "telegram_channels.json")
SESSION_FILE = os.path.join(PROJECT_ROOT, "centinela_session")

async def main():
    print("=" * 70)
    print("   UNIÓN AUTOMÁTICA SEGURA A GRUPOS DE ESTUDIANTES - TELEGRAM")
    print("   Ciencias Exactas: CBC UBA, FIUBA, Exactas y UTN")
    print("=" * 70)

    api_id = os.environ.get("TELEGRAM_API_ID")
    api_hash = os.environ.get("TELEGRAM_API_HASH")

    if not api_id or not api_hash:
        print("[ERROR] TELEGRAM_API_ID o TELEGRAM_API_HASH no configurados en .env.")
        return

    # Si la sesión está en el Escritorio, priorizarla
    session_candidates = [
        SESSION_FILE,
        r"E:\OneDrive\Escritorio\Prospeccion_Alumnos_Ciencias\centinela_session",
        os.path.join(os.getcwd(), "centinela_session")
    ]
    target_session = None
    for cand in session_candidates:
        if os.path.exists(cand + ".session"):
            target_session = cand
            break

    if not target_session:
        target_session = SESSION_FILE

    print(f"\nUsando archivo de sesión: {target_session}.session")
    client = TelegramClient(target_session, int(api_id), api_hash)
    await client.connect()

    if not await client.is_user_authorized():
        print("[ERROR] La sesión no está autorizada. Ejecuta primero Iniciar_Centinela_Telegram.bat.")
        await client.disconnect()
        return

    me = await client.get_me()
    print(f"[SESIÓN AUTORIZADA] Conectado como: {me.first_name} (@{me.username or 'sin_username'})")

    if not os.path.exists(CONFIG_PATH):
        print(f"[ERROR] No se encontró {CONFIG_PATH}")
        await client.disconnect()
        return

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    groups_to_join = data.get("discussion_groups_to_join", [])
    print(f"\nGrupos estudiantiles objetivo a conectar: {len(groups_to_join)}")
    joined_count = 0

    for idx, grp in enumerate(groups_to_join, 1):
        username = grp.get("username", "").strip().lstrip("@")
        title = grp.get("title", username)
        members = grp.get("members", "Varios")
        print(f"\n[{idx}/{len(groups_to_join)}] Evaluando: '{title}' (@{username}) - {members} miembros...")

        try:
            # Obtener entidad del canal/grupo
            entity = await client.get_entity(username)
            try:
                await client(functions.channels.JoinChannelRequest(channel=entity))
                print(f"  -> ✅ [UNIDO CON ÉXITO] Ya estás dentro del grupo '{title}'.")
                joined_count += 1
            except errors.UserAlreadyParticipantError:
                print(f"  -> ℹ️ [YA ERAS MIEMBRO] Ya pertenecías a este grupo.")
            except errors.FloodWaitError as e:
                print(f"  -> ⚠️ Telegram pide esperar {e.seconds}s. Pausando...")
                await asyncio.sleep(e.seconds)
            except Exception as e:
                print(f"  -> ⚠️ Alerta al unirse a @{username}: {e}")

            # Espera preventiva de 5 segundos entre grupos para proteger la cuenta
            if idx < len(groups_to_join):
                print("  (Pausa de seguridad de 5s entre grupos...)")
                await asyncio.sleep(5.0)

        except Exception as e:
            print(f"  -> ❌ Error buscando @{username}: {e}")

    await client.disconnect()

    print("\n" + "=" * 70)
    print(f"   [PROCESO COMPLETADO] Te has unido a los grupos estudiantiles.")
    print(f"   Tu Centinela ahora escuchará en vivo las consultas de estos chats.")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
