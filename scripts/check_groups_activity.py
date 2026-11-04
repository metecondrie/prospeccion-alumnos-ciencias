import os
import sys
import asyncio
from datetime import datetime, timezone, timedelta

# Ensure scripts dir is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prospector import load_env_file

load_env_file()

api_id = int(os.environ.get('TELEGRAM_API_ID', 0))
api_hash = os.environ.get('TELEGRAM_API_HASH', '')

session_file = 'centinela_session'
if os.environ.get('PROSPECTOR_EXPORT_DIR') and os.path.exists(os.path.join(os.environ.get('PROSPECTOR_EXPORT_DIR'), 'centinela_session.session')):
    session_file = os.path.join(os.environ.get('PROSPECTOR_EXPORT_DIR'), 'centinela_session')

async def check():
    from telethon import TelegramClient
    client = TelegramClient(session_file, api_id, api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        print('Sesión no autorizada.')
        return

    print("Conectado con éxito. Analizando actividad de tus chats...")
    dialogs = await client.get_dialogs(limit=40)
    now = datetime.now(timezone.utc)

    for d in dialogs:
        if d.is_group or d.is_channel:
            uname = getattr(d.entity, 'username', None)
            uname_str = f"@{uname}" if uname else "grupo privado"
            last_date = d.date
            if last_date:
                days_ago = (now - last_date).days
                date_str = last_date.strftime('%Y-%m-%d %H:%M')
                status = "🟢 ACTIVO" if days_ago < 30 else f"⚠️ INACTIVO (hace {days_ago} días)"
            else:
                date_str = "Desconocida"
                status = "❓ Sin fecha"

            print(f"- [{status}] '{d.title}' ({uname_str}) | Último mensaje: {date_str}")

    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(check())
