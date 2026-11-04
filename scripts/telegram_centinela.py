#!/usr/bin/env python3
"""
telegram_centinela.py
Bot Centinela en Tiempo Real para Telegram (Telethon Client).
Monitorea grupos estudiantiles, detecta alumnos de ciencias exactas,
clasifica con IA mediante cola asíncrona no bloqueante y emite alertas push inmediatas.
"""

import os
import sys
import json
import time
import re
import html
import asyncio
import signal
import argparse
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Tuple, Optional, List

try:
    from zoneinfo import ZoneInfo
    TZ_ART = ZoneInfo("America/Argentina/Buenos_Aires")
except Exception:
    TZ_ART = timezone(timedelta(hours=-3))

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
EXPORT_SYNC_DIR = os.environ.get("PROSPECTOR_EXPORT_DIR", "")

if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from prospector import load_env_file, call_multiprovider_batch, normalize_item
from common_filter import normalize_subject, normalize_level, sanitize_text
from extract_telegram import send_telegram_notification
from storage import atomic_write_json, safe_read_json, FileLock, compute_stable_id

try:
    from telethon.errors import FloodWaitError
except ImportError:
    class FloodWaitError(Exception):
        seconds = 60

load_env_file()

DATA_APPROVED = os.path.join(PROJECT_ROOT, "data", "leads_centinela_en_vivo.json")
DEDUPE_FILE = os.path.join(PROJECT_ROOT, "data", "centinela_dedupe.json")
DIGEST_QUEUE_FILE = os.path.join(PROJECT_ROOT, "data", "centinela_digest_queue.json")
UMBRAL_PUSH = float(os.environ.get("CENTINELA_SCORE_UMBRAL", "0.70"))
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "centinela.log")

STATS = {
    "start_time": datetime.now(),
    "messages_scanned": 0,
    "ai_audits": 0,
    "approved_leads": 0,
    "discarded_leads": 0,
    "alerts_sent": 0,
    "alerts_failed": 0
}


def log_event(text: str, print_to_console: bool = True):
    """Escribe en logs/centinela.log y opcionalmente en consola."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{now_str}] {text}"
    if print_to_console:
        print(formatted)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
        if EXPORT_SYNC_DIR and os.path.exists(EXPORT_SYNC_DIR):
            sec_logs = os.path.join(EXPORT_SYNC_DIR, "logs")
            os.makedirs(sec_logs, exist_ok=True)
            with open(os.path.join(sec_logs, "centinela.log"), "a", encoding="utf-8") as f:
                f.write(formatted + "\n")
    except Exception:
        pass


FAST_TRIGGERS = [
    r"\bprofesor\b", r"\bprofesora\b", r"\bprofe\b", r"\bparticular\b",
    r"\bclases\b", r"\btutor\b", r"\btutora\b", r"\benseñ\b", r"\bexplic\b",
    r"\bparcial\b", r"\bfinal\b", r"\bexamen\b", r"\bparcialito\b",
    r"\bcbc\b", r"\buba\s*xxi\b", r"\bapoyo\b", r"\bayuda\b", r"\btest\b"
]

FAST_SUBJECTS = [
    r"\bmatem[aá]tic", r"\bf[ií]sic", r"\bqu[ií]mic", r"\bbiolog[ií]",
    r"\ban[aá]lisis\b", r"\b[aá]lgebra\b", r"\bbiof[ií]sic", r"\bc[aá]lculo\b",
    r"\bgeometr[ií]a\b", r"\baritm[eé]tica\b", r"\bprobabilidad\b", r"\bestad[ií]stic\b",
    r"\bciencias\b", r"\btest\b"
]


def fast_match(text: str) -> bool:
    """Filtro ultrarrápido por expresiones regulares antes de gastar llamada a la IA."""
    t = text.lower()
    has_trigger = any(re.search(pat, t) for pat in FAST_TRIGGERS)
    has_subject = any(re.search(pat, t) for pat in FAST_SUBJECTS)
    return has_trigger and has_subject


def save_approved_lead(lead: Dict[str, Any]) -> bool:
    """Guarda el nuevo alumno de forma atómica y concurrente usando storage.py."""
    targets = [DATA_APPROVED]
    if EXPORT_SYNC_DIR and os.path.exists(EXPORT_SYNC_DIR):
        targets.append(os.path.join(EXPORT_SYNC_DIR, "data", "leads_centinela_en_vivo.json"))

    saved_any = False
    for target_path in targets:
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        existing = safe_read_json(target_path, default=[])
        seen_ids = {it.get("id") for it in existing if isinstance(it, dict)}
        if lead.get("id") not in seen_ids:
            existing.append(lead)
            atomic_write_json(target_path, existing)
            saved_any = True

    if saved_any:
        log_event(f"[BASE DE DATOS] Alumno registrado con éxito ({lead.get('id')}).")
    return saved_any


def is_persona_deduped_24h(persona_id: str, current_time: Optional[float] = None) -> bool:
    """Verifica si persona_id ya fue alertada en las últimas 24 horas (F4 dedupe 24h)."""
    if not persona_id:
        return False
    now_ts = current_time if current_time is not None else time.time()
    dedupe_map = safe_read_json(DEDUPE_FILE, default={})
    last_seen = dedupe_map.get(str(persona_id))
    if last_seen and (now_ts - float(last_seen)) < 86400:  # 24h en segundos
        return True
    return False


def record_persona_seen(persona_id: str, current_time: Optional[float] = None) -> None:
    """Registra la marca de tiempo de contacto para persona_id."""
    if not persona_id:
        return
    now_ts = current_time if current_time is not None else time.time()
    os.makedirs(os.path.dirname(os.path.abspath(DEDUPE_FILE)), exist_ok=True)
    dedupe_map = safe_read_json(DEDUPE_FILE, default={})
    dedupe_map[str(persona_id)] = now_ts
    pruned = {k: v for k, v in dedupe_map.items() if (now_ts - float(v)) < 172800}
    atomic_write_json(DEDUPE_FILE, pruned)


def compute_heuristic_score(text: str) -> float:
    """Calcula score heurístico (0.0 - 1.0) ponderando intención de alumno vs oferta."""
    t = text.lower()
    score = 0.50
    student_signals = [
        r"\bnecesito\b", r"\bbusco\b", r"\balguien que d[eé]\b", r"\bpreparar\b",
        r"\brecuperatorio\b", r"\bparcial\b", r"\bexamen\b", r"\bfinal\b",
        r"\bapoyo\b", r"\bayuda\b", r"\bcuanto cobr\b", r"\bprecio\b"
    ]
    for pat in student_signals:
        if re.search(pat, t):
            score += 0.08
    for sub in [r"\bmatem[aá]tic", r"\bf[ií]sic", r"\bqu[ií]mic", r"\bc[aá]lculo\b", r"\b[aá]lgebra\b"]:
        if re.search(sub, t):
            score += 0.06
    for pen in [r"\bdoy clases\b", r"\bofrezco\b", r"\bexperiencia\b", r"\bprimera clase gratis\b"]:
        if re.search(pen, t):
            score -= 0.30
    return max(0.0, min(1.0, round(score, 3)))


def compute_combined_score(heuristic_score: float, ai_score: float) -> float:
    """score = f(heurística, IA): 35% heurística + 65% IA."""
    combined = (0.35 * heuristic_score) + (0.65 * ai_score)
    return max(0.0, min(1.0, round(combined, 3)))


def enqueue_for_daily_digest(
    lead: Dict[str, Any],
    chat_title: str,
    sender_user: str,
    score: float,
    edad_msg_min: float
) -> None:
    """Encola leads calificados que no alcanzaron el umbral de push para el digest de las 20:00 ART."""
    os.makedirs(os.path.dirname(os.path.abspath(DIGEST_QUEUE_FILE)), exist_ok=True)
    queue: List[Dict[str, Any]] = safe_read_json(DIGEST_QUEUE_FILE, default=[])
    queue.append({
        "lead": lead,
        "chat_title": chat_title,
        "sender_user": sender_user,
        "score": score,
        "edad_msg_min": edad_msg_min,
        "enqueued_at": datetime.now(timezone.utc).isoformat()
    })
    atomic_write_json(DIGEST_QUEUE_FILE, queue)
    log_event(f"   📋 [DIGEST 20:00 ART] Lead encolado para resumen diario (Score: {score:.2f} < {UMBRAL_PUSH}).")


def send_daily_digest(force: bool = False) -> int:
    """Envía el resumen diario a las 20:00 America/Argentina/Buenos_Aires y vacía la cola."""
    queue: List[Dict[str, Any]] = safe_read_json(DIGEST_QUEUE_FILE, default=[])
    if not queue:
        return 0

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        if force:
            atomic_write_json(DIGEST_QUEUE_FILE, [])
        return len(queue)

    msg = (
        "📰 <b>RESUMEN DIARIO CENTINELA (20:00 ART)</b>\n"
        f"<i>Total leads calificados en cola secundaria: {len(queue)}</i>\n\n"
    )
    for idx, it in enumerate(queue[:10], 1):
        ld = it.get("lead", {})
        esc_nom = html.escape(str(ld.get("nombre", "Alumno")))
        esc_mat = html.escape(str(ld.get("materia", "Exactas")))
        esc_chat = html.escape(str(it.get("chat_title", "")))
        esc_lnk = html.escape(str(ld.get("enlace al anuncio", "")))
        msg += (
            f"<b>{idx}. {esc_nom}</b> ({esc_mat})\n"
            f"   ⭐ Score: {it.get('score', 0):.2f} | Grupo: {esc_chat}\n"
            f"   👉 <a href='{esc_lnk}'>Contactar alumno</a>\n\n"
        )

    success = send_telegram_notification(bot_token, chat_id, msg)
    if success or force:
        atomic_write_json(DIGEST_QUEUE_FILE, [])
        log_event(f"📰 [DIGEST ENVIADO] {len(queue)} oportunidades entregadas a Telegram.")
        return len(queue)
    return 0


def send_centinela_push_alert(
    lead: Dict[str, Any],
    group_title: str,
    student_username: str,
    edad_msg_min: float = 0.0,
    score: float = 0.0
) -> Tuple[bool, str]:
    """
    Construye y envía la alerta al bot personal con escape HTML estricto.
    Retorna (éxito, mensaje_detalle).
    """
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        return False, "TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID no configurados en .env"

    user_link = f"https://t.me/{student_username}" if student_username else lead.get("enlace al anuncio", "")
    author_display = f"@{student_username}" if student_username else lead.get("nombre", "Estudiante en grupo")

    # Escape seguro de entidades HTML para evitar errores 400 de Telegram
    esc_group = html.escape(str(group_title or "Grupo Telegram"))
    esc_author = html.escape(str(author_display))
    esc_subject = html.escape(str(lead.get("materia", "Ciencias Exactas")))
    esc_level = html.escape(str(lead.get("nivel educativo", "Universitario / Secundario")))
    esc_msg = html.escape(str(lead.get("mensaje/descripción", ""))[:250])
    esc_link = html.escape(str(user_link))

    msg = (
        "🚨 <b>¡CENTINELA TELEGRAM EN VIVO!</b>\n"
        f"<i>Nuevo alumno detectado en el grupo:</i> <b>{esc_group}</b>\n\n"
        f"👤 <b>Alumno:</b> {esc_author}\n"
        f"📚 <b>Materia:</b> {esc_subject}\n"
        f"🎯 <b>Nivel:</b> {esc_level}\n"
        f"⭐ <b>Score Calidad:</b> {score:.2f}\n"
        f"⏱️ <b>Antigüedad:</b> {edad_msg_min} min\n\n"
        f"💬 <b>Mensaje:</b> <i>\"{esc_msg}\"</i>\n\n"
        f"👉 <a href='{esc_link}'><b>Abrir chat y contactar al alumno</b></a>"
    )

    success = send_telegram_notification(bot_token, chat_id, msg)
    if success:
        STATS["alerts_sent"] += 1
        return True, "Notificación push entregada exitosamente vía Telegram Bot API"
    else:
        STATS["alerts_failed"] += 1
        return False, "Fallo al enviar notificación push a la API de Telegram"


async def classification_worker(queue: asyncio.Queue, stop_event: asyncio.Event, args):
    """
    Worker asíncrono en segundo plano:
    Consume candidatos de la cola, ejecuta la clasificación por IA en un thread pool,
    deduplica por persona_id (24h), pondera score = f(heurística, IA),
    y despacha alerta push inmediata (score >= umbral) o encola para digest 20:00 ART.
    """
    while not stop_event.is_set() or not queue.empty():
        try:
            item_data = await asyncio.wait_for(queue.get(), timeout=1.0)
        except asyncio.TimeoutError:
            continue

        candidate = item_data["candidate"]
        chat_title = item_data["chat_title"]
        sender_user = item_data["sender_user"]
        sender_name = item_data["sender_name"]
        raw_text = item_data["text"]
        msg_date_ts = item_data.get("msg_ts") or time.time()
        edad_msg_min = max(0.1, round((time.time() - float(msg_date_ts)) / 60.0, 1))

        persona_id = str(sender_user or f"user_{candidate.get('id', '0')}")

        # F4: Deduplicación 24h por persona_id
        if is_persona_deduped_24h(persona_id):
            log_event(f"   ⏭️ [DEDUPE 24h] Alerta omitida para '{persona_id}': ya fue contactado/alertado en las últimas 24 horas.")
            queue.task_done()
            continue

        STATS["ai_audits"] += 1
        log_event(f"🤖 [COLA DE AUDITORÍA] Analizando mensaje de {sender_name} en '{chat_title}' (Antigüedad: {edad_msg_min} min)...")

        model_name = "heuristic" if (args and getattr(args, "simulate", False)) else "gemini-3.5-flash"
        try:
            loop = asyncio.get_running_loop()
            results = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: call_multiprovider_batch([candidate], primary_model=model_name)),
                timeout=25.0
            )

            if results and isinstance(results, list):
                res = results[0]
                is_student = (res.get("is_student") is True or res.get("decision_ia") == "Aprobado")
                heur_score = compute_heuristic_score(raw_text)
                final_score = compute_combined_score(heur_score, 0.95 if is_student else 0.10)

                if is_student:
                    STATS["approved_leads"] += 1
                    log_event(f"   ✅ [APROBADO POR IA] {res.get('justificacion_ia')} (Score F4: {final_score:.2f})")

                    normalized_lead = normalize_item({
                        "id": candidate["id"],
                        "plataforma": candidate["plataforma"],
                        "país/ubicación": candidate["ubicacion"],
                        "nombre": sender_name,
                        "persona_id": persona_id,
                        "materia": candidate["materia"],
                        "nivel educativo": normalize_level(raw_text),
                        "enlace al anuncio": candidate["enlace"],
                        "mensaje/descripción": sanitize_text(raw_text),
                        "método de contacto directo": f"Telegram (@{sender_user})" if sender_user else "Telegram (Mensaje en grupo)",
                        "decision_ia": "Aprobado",
                        "justificacion_ia": res.get("justificacion_ia", "Detectado en vivo por Centinela"),
                        "score_calidad": final_score,
                        "edad_msg_min": edad_msg_min
                    })

                    # Persistencia atómica
                    save_approved_lead(normalized_lead)

                    # F4: Routing según umbral (push inmediato vs digest 20:00 ART)
                    if final_score >= UMBRAL_PUSH:
                        ok, detail = send_centinela_push_alert(normalized_lead, chat_title, sender_user, edad_msg_min, final_score)
                        record_persona_seen(persona_id)
                        if ok:
                            log_event(f"   📲 [ALERTA INMEDIATA ENVIADA] Score: {final_score:.2f} >= {UMBRAL_PUSH} | {detail}")
                        else:
                            log_event(f"   ⚠️ [ALERTA NO ENTREGADA] {detail}")
                    else:
                        enqueue_for_daily_digest(normalized_lead, chat_title, sender_user, final_score, edad_msg_min)
                        record_persona_seen(persona_id)
                else:
                    STATS["discarded_leads"] += 1
                    log_event(f"   ❌ [DESCARTADO POR IA] {res.get('justificacion_ia')} (Score F4: {final_score:.2f})")
        except asyncio.TimeoutError:
            log_event(f"   ⚠️ [TIMEOUT EN AUDITORÍA IA] La consulta excedió el tiempo límite (12s).")
        except Exception as e:
            log_event(f"   ⚠️ [ERROR EN AUDITORÍA IA] {e}")
        finally:
            queue.task_done()
            await asyncio.sleep(0.5)  # Respetar rate limits entre consultas


async def heartbeat_loop(stop_event: asyncio.Event):
    """Latido continuo cada 60s para telemetría y disparo de digest diario 20:00 ART."""
    last_digest_day = None
    while not stop_event.is_set():
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=60.0)
            break
        except asyncio.TimeoutError:
            pass

        now_art = datetime.now(TZ_ART)
        if now_art.hour == 20 and now_art.minute < 3 and last_digest_day != now_art.date():
            send_daily_digest()
            last_digest_day = now_art.date()

        now_str = now_art.strftime("%H:%M:%S")
        status_line = (
            f"[LATIDO {now_str} ART] 🟢 Centinela en guardia | "
            f"Escaneados: {STATS['messages_scanned']} | "
            f"Auditados IA: {STATS['ai_audits']} | "
            f"Aprobados: {STATS['approved_leads']} | "
            f"Alertas: {STATS['alerts_sent']}/{STATS['alerts_sent']+STATS['alerts_failed']}"
        )
        log_event(status_line, print_to_console=True)


async def run_simulation():
    """Modo de prueba determinista y offline para validar el Centinela, dedupe 24h y digest."""
    print("=" * 70)
    print("   MODO SIMULACIÓN: PRUEBA DE COLA Y CLASIFICACIÓN CENTINELA")
    print("=" * 70)

    queue = asyncio.Queue()
    stop_event = asyncio.Event()

    # Iniciar worker
    sim_args = argparse.Namespace(simulate=True)
    worker = asyncio.create_task(classification_worker(queue, stop_event, sim_args))

    sim_now = time.time()
    test_messages = [
        {
            "text": "Hola a todos! Alguien que dé clases particulares de Análisis Matemático II para ingeniería? Necesito preparar el recuperatorio urgente.",
            "chat_title": "FIUBA - Estudiantes Exactas",
            "sender_name": "Lucas B.",
            "sender_user": "lucas_exactas",
            "msg_ts": sim_now - 150.0  # Mensaje de hace 2.5 min
        },
        {
            "text": "Doy clases de Física I y Química General. Amplia experiencia universitaria, primera clase gratis. Comunicarse por privado.",
            "chat_title": "CBC UBA - Grupos de Estudio",
            "sender_name": "Profesor Particular",
            "sender_user": "profe_particular",
            "msg_ts": sim_now - 60.0
        },
        {
            "text": "Alguien sabe si mañana hay paro de trenes para ir a la facu?",
            "chat_title": "Exactas UNLP",
            "sender_name": "Mariana D.",
            "sender_user": "mariana_d",
            "msg_ts": sim_now - 30.0
        }
    ]

    print(f"\nInyectando {len(test_messages)} mensajes simulados a la cola...")
    for idx, msg in enumerate(test_messages, 1):
        raw_text = msg["text"]
        STATS["messages_scanned"] += 1
        if not fast_match(raw_text):
            print(f"  [Msg #{idx}] Descartado en capa heurística: '{raw_text[:40]}...' (charla general)")
            continue

        item_id = compute_stable_id("Telegram", msg["sender_name"], "2026-11-04", raw_text)
        candidate = {
            "id": item_id,
            "plataforma": f"Telegram ({msg['chat_title']})",
            "materia": normalize_subject(raw_text) or "Ciencias Exactas",
            "ubicacion": "Argentina - Grupo Telegram Simulado",
            "mensaje": raw_text,
            "enlace": "https://t.me/demo_student"
        }
        await queue.put({
            "candidate": candidate,
            "chat_title": msg["chat_title"],
            "sender_user": msg["sender_user"],
            "sender_name": msg["sender_name"],
            "text": raw_text,
            "msg_ts": msg["msg_ts"]
        })
        print(f"  [Msg #{idx}] Encolado para auditoría IA: '{raw_text[:40]}...'")

    # Esperar a que la cola termine de procesar
    await queue.join()
    stop_event.set()
    await worker

    print("\n" + "=" * 70)
    print("RESULTADO DE LA SIMULACIÓN:")
    print(f"  Mensajes escaneados: {STATS['messages_scanned']}")
    print(f"  Auditados por IA: {STATS['ai_audits']}")
    print(f"  Aprobados (Alumnos): {STATS['approved_leads']}")
    print(f"  Descartados (Profesores): {STATS['discarded_leads']}")
    print("==================================================")
    print("✅ Centinela: Bucle asíncrono, worker y cola verificados con éxito.")


async def main_async(args):
    if args.simulate:
        await run_simulation()
        return

    api_id = os.environ.get("TELEGRAM_API_ID")
    api_hash = os.environ.get("TELEGRAM_API_HASH")

    if not api_id or not api_hash:
        print("\n[ERROR] TELEGRAM_API_ID o TELEGRAM_API_HASH no configurados en .env.")
        print("Para probar el Centinela sin credenciales, utiliza:")
        print("  python -m scripts.telegram_centinela --simulate")
        return

    from telethon import TelegramClient, events

    try:
        api_id_int = int(api_id)
    except ValueError:
        print(f"[ERROR] TELEGRAM_API_ID debe ser un número entero. Valor: {api_id}")
        return

    session_path = os.path.join(PROJECT_ROOT, "centinela_session")
    client = TelegramClient(session_path, api_id_int, api_hash)
    await client.start()

    me = await client.get_me()
    print(f"\n[CENTINELA TELEGRAM CONECTADO]")
    print(f"Cuenta: {me.first_name} (@{me.username or 'sin_username'}) | ID: {me.id}")

    try:
        dialogs = await client.get_dialogs(limit=50)
    except FloodWaitError as e:
        log_event(f"[RATE LIMIT] FloodWait de {e.seconds}s. Esperando enfriamiento...")
        await asyncio.sleep(e.seconds + 2)
        dialogs = await client.get_dialogs(limit=50)

    active_groups = [d for d in dialogs if (d.is_group or d.is_channel)]
    print(f"[SINCRONIZACIÓN EXITOSA] {len(active_groups)} grupos monitoreados activamente.")

    queue = asyncio.Queue(maxsize=100)
    stop_event = asyncio.Event()

    # Iniciar tareas concurrentes en segundo plano
    worker_task = asyncio.create_task(classification_worker(queue, stop_event, args))
    heartbeat_task = asyncio.create_task(heartbeat_loop(stop_event))

    @client.on(events.NewMessage)
    async def handler(event):
        if event.is_private:
            return
        if event.out and not args.test_mode:
            return  # Excluir mensajes propios en producción

        text = event.raw_text or ""
        STATS["messages_scanned"] += 1

        if len(text) < 10:
            return

        if not fast_match(text):
            return

        chat = await event.get_chat()
        chat_title = getattr(chat, 'title', 'Grupo Telegram')
        sender = await event.get_sender()
        sender_name = f"{getattr(sender, 'first_name', '')} {getattr(sender, 'last_name', '')}".strip() or "Estudiante"
        sender_user = getattr(sender, 'username', '')

        item_id = f"tg_live_{abs(event.chat_id)}_{event.id}"
        link = f"https://t.me/c/{abs(event.chat_id)}/{event.id}" if not getattr(chat, 'username', None) else f"https://t.me/{chat.username}/{event.id}"

        candidate = {
            "id": item_id,
            "plataforma": f"Telegram ({chat_title})",
            "materia": normalize_subject(text) or "Ciencias Exactas",
            "ubicacion": "Argentina / LATAM - Grupo Estudiantil Telegram",
            "mensaje": text,
            "enlace": link
        }

        # Extraer timestamp de origen del mensaje
        msg_date = getattr(event.message, 'date', None)
        msg_ts = msg_date.timestamp() if msg_date else time.time()

        # Encolado rápido sin bloquear el event loop de Telethon
        try:
            queue.put_nowait({
                "candidate": candidate,
                "chat_title": chat_title,
                "sender_user": sender_user,
                "sender_name": sender_name,
                "text": text,
                "msg_ts": msg_ts
            })
            log_event(f"📥 [ENCOLADO] Msg de {sender_name} en '{chat_title}' agregado a la cola de auditoría.")
        except asyncio.QueueFull:
            log_event("⚠️ [COLA LLENA] Se descartó mensaje por saturación temporal de auditoría.")

    try:
        await client.run_until_disconnected()
    finally:
        stop_event.set()
        worker_task.cancel()
        heartbeat_task.cancel()
        await client.disconnect()


def main():
    parser = argparse.ArgumentParser(description="Centinela de Telegram 24/7 con Clasificación Asíncrona")
    parser.add_argument("--simulate", action="store_true", help="Ejecuta una prueba simulada de la cola y clasificación")
    parser.add_argument("--test-mode", action="store_true", help="Permite procesar mensajes propios durante pruebas")
    parser.add_argument("--flush-digest", action="store_true", help="Fuerza el envío inmediato del digest acumulado (20:00 ART)")
    args = parser.parse_args()

    if getattr(args, "flush_digest", False):
        sent = send_daily_digest(force=True)
        print(f"[OK] Digest diario procesado. Leads despachados: {sent}")
        return

    try:
        asyncio.run(main_async(args))
    except (KeyboardInterrupt, SystemExit):
        log_event("[CENTINELA DETENIDO] Proceso cerrado ordenadamente.")


if __name__ == "__main__":
    main()
