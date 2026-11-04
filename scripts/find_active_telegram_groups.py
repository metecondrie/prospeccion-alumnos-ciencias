#!/usr/bin/env python3
import os
import sys
import asyncio
from datetime import datetime, timezone, timedelta
from telethon import TelegramClient, functions

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prospector import load_env_file

load_env_file()

api_id = int(os.environ.get('TELEGRAM_API_ID', 0))
api_hash = os.environ.get('TELEGRAM_API_HASH', '')
session_file = 'centinela_session'
if not os.path.exists(session_file + '.session'):
    session_file = r'E:\OneDrive\Escritorio\Prospeccion_Alumnos_Ciencias\centinela_session'

now = datetime.now(timezone.utc)

async def search_active():
    client = TelegramClient(session_file, api_id, api_hash)
    await client.connect()
    
    queries = [
        'FIUBA', 'Fisica FIUBA', 'Quimica FIUBA', 'Analisis Matematico', 
        'Algebra CBC', 'CBC UBA', 'UBA XXI', 'UTN FRBA', 'UNLP', 
        'Medicina UNLP', 'Clases particulares matematica', 'Exactas'
    ]
    seen = set()
    active_groups = []
    inactive_groups = []

    print("Buscando en vivo en los servidores de Telegram...")

    for q in queries:
        try:
            res = await client(functions.contacts.SearchRequest(q=q, limit=15))
            for chat in res.chats:
                uname = getattr(chat, 'username', None)
                if uname and uname not in seen:
                    seen.add(uname)
                    try:
                        msgs = await client.get_messages(chat, limit=1)
                        if msgs and msgs[0].date:
                            days_ago = (now - msgs[0].date).days
                            participants = getattr(chat, 'participants_count', 0) or 0
                            info = {
                                'username': uname,
                                'title': chat.title,
                                'members': participants,
                                'days_ago': days_ago,
                                'last_date': msgs[0].date.strftime('%Y-%m-%d'),
                                'is_megagroup': getattr(chat, 'megagroup', False),
                                'broadcast': getattr(chat, 'broadcast', False)
                            }
                            if days_ago <= 45 and participants >= 20:
                                active_groups.append(info)
                            else:
                                inactive_groups.append(info)
                    except Exception:
                        pass
        except Exception as e:
            print(f"Error buscando '{q}': {e}")

    await client.disconnect()

    print("\n" + "=" * 75)
    print(f"GRUPOS ACTIVOS ENCONTRADOS (Última actividad en los últimos 45 días): {len(active_groups)}")
    print("=" * 75)
    for g in sorted(active_groups, key=lambda x: (x['days_ago'], -x['members'])):
        tipo = "Canal" if g['broadcast'] else "Grupo"
        print(f"[{tipo}] @{g['username']:24} | {g['members']:4} miembros | Hace {g['days_ago']:2} días ({g['last_date']}) | {g['title']}")

    return active_groups

if __name__ == '__main__':
    asyncio.run(search_active())
