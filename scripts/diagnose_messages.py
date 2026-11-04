import os
import sys
import asyncio
from datetime import datetime, timezone
from telethon import TelegramClient

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prospector import load_env_file
load_env_file()

api_id = int(os.environ.get('TELEGRAM_API_ID', 0))
api_hash = os.environ.get('TELEGRAM_API_HASH', '')
session_file = 'centinela_session'

async def check():
    client = TelegramClient(session_file, api_id, api_hash)
    await client.connect()
    dialogs = await client.get_dialogs(limit=25)
    now = datetime.now(timezone.utc)
    print(f"Hora actual UTC: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print("Últimos mensajes en tus chats:")
    for d in dialogs:
        if d.is_group or d.is_channel:
            msgs = await client.get_messages(d.entity, limit=1)
            if msgs:
                m = msgs[0]
                m_date = m.date
                diff = (now - m_date).total_seconds() / 60.0
                txt = (m.raw_text or '')[:55].replace('\n', ' ')
                action = getattr(m, 'action', None)
                act_str = f"[{type(action).__name__}]" if action else ""
                print(f"- {d.title[:30]:30} | {m_date.strftime('%H:%M:%S')} (hace {diff:5.1f} min) | {act_str} {txt}")
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(check())
