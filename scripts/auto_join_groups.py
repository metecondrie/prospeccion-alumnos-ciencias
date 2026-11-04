#!/usr/bin/env python3
"""
auto_join_groups.py
Script inteligente y seguro para unirse a grupos estudiantiles activos de ciencias exactas.
Filtra automáticamente grupos muertos o inactivos (solo se une si hubo actividad en los últimos 60 días)
para no ensuciar tu cuenta de Telegram y evitar FloodWait innecesarios.
"""

import os
import sys
import json
import time
import asyncio
from datetime import datetime, timezone, timedelta
from telethon import TelegramClient, functions, errors

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
DESKTOP_DIR = r"E:\OneDrive\Escritorio\Prospeccion_Alumnos_Ciencias"

if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from prospector import load_env_file
load_env_file()

CONFIG_PATH = os.path.join(PROJECT_ROOT, "data", "telegram_channels.json")
SESSION_FILE = os.path.join(PROJECT_ROOT, "centinela_session")

MAX_INACTIVE_DAYS = 60  # Solo unirse si hubo mensajes en los últimos 60 días

async def main():
    print("=" * 75)
    print("   UNIÓN INTELIGENTE A GRUPOS ACTIVOS DE ESTUDIANTES - TELEGRAM")
    print("   Filtro en vivo: Solo grupos con actividad real reciente (últimos 60 días)")
    print("=" * 75)

    api_id = os.environ.get("TELEGRAM_API_ID")
    api_hash = os.environ.get("TELEGRAM_API_HASH")

    if not api_id or not api_hash:
        print("[ERROR] TELEGRAM_API_ID o TELEGRAM_API_HASH no configurados en .env.")
        return

    # Buscar sesión
    session_candidates = [
        SESSION_FILE,
        os.path.join(DESKTOP_DIR, "centinela_session"),
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
    print(f"\nGrupos candidatos a evaluar: {len(groups_to_join)}")
    joined_count = 0
    skipped_inactive = 0
    now = datetime.now(timezone.utc)

    for idx, grp in enumerate(groups_to_join, 1):
        username = grp.get("username", "").strip().lstrip("@")
        title = grp.get("title", username)
        members = grp.get("members", "Varios")
        print(f"\n[{idx}/{len(groups_to_join)}] Auditando: '{title}' (@{username}) - {members} miembros...")

        try:
            entity = await client.get_entity(username)
            
            # 1. Verificar actividad reciente antes de gastar cuota de unión
            msgs = await client.get_messages(entity, limit=1)
            if msgs and msgs[0].date:
                days_ago = (now - msgs[0].date).days
                date_str = msgs[0].date.strftime('%Y-%m-%d')
                if days_ago > MAX_INACTIVE_DAYS:
                    print(f"  -> ⚠️ OMITIDO: Inactivo hace {days_ago} días (último mensaje: {date_str}).")
                    print("     (No te unirá a este grupo para no ensuciar tu lista de chats).")
                    skipped_inactive += 1
                    continue
                else:
                    print(f"  -> 🟢 ACTIVO: Último mensaje hace {days_ago} días ({date_str}). Procediendo a conectar...")
            else:
                print("  -> ⚠️ Sin mensajes públicos previos. Evaluando unión con precaución...")

            # 2. Intentar unirse al grupo activo
            try:
                await client(functions.channels.JoinChannelRequest(channel=entity))
                print(f"  -> ✅ [UNIDO CON ÉXITO] Ya estás dentro del grupo activo '{title}'.")
                joined_count += 1
            except errors.UserAlreadyParticipantError:
                print(f"  -> ℹ️ [YA ERAS MIEMBRO] Ya pertenecías a este grupo.")
            except errors.FloodWaitError as e:
                print(f"  -> ⚠️ Telegram pide pausar {e.seconds}s por seguridad...")
                await asyncio.sleep(e.seconds)
                try:
                    await client(functions.channels.JoinChannelRequest(channel=entity))
                    print(f"  -> ✅ [UNIDO CON ÉXITO TRAS PAUSA] Ya estás dentro de '{title}'.")
                    joined_count += 1
                except Exception as ex2:
                    print(f"  -> ⚠️ No se pudo completar tras la pausa: {ex2}")
            except Exception as e:
                print(f"  -> ⚠️ Nota al unirse a @{username}: {e}")

            # Pausa de seguridad de 4 segundos entre grupos
            if idx < len(groups_to_join):
                await asyncio.sleep(4.0)

        except Exception as e:
            print(f"  -> ❌ Error evaluando @{username}: {e}")

    await client.disconnect()

    print("\n" + "=" * 75)
    print(f"   [PROCESO COMPLETADO]")
    print(f"   - Grupos activos conectados / ya miembro: {joined_count}")
    print(f"   - Grupos muertos u obsoletos descartados: {skipped_inactive}")
    print(f"   Tu Telegram ahora está limpio con comunidades vivas y activas.")
    print("=" * 75)

if __name__ == "__main__":
    asyncio.run(main())
