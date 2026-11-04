#!/usr/bin/env python3
"""
Prospector CLI - Sistema Autónomo de Captación y Auditoría de Alumnos de Ciencias Exactas
Modelos IA: Google Gemini 3.5 / 3.6 Flash / Groq LPU
Destinatario: Docente de Ciencias Exactas
"""

import os
import sys
import json
import csv
import time
import urllib.request
import urllib.error
import argparse
import shutil
import re
import hashlib
import unicodedata
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

try:
    from storage import (
        atomic_write_json,
        safe_read_json,
        atomic_write_text,
        merge_crm_tracking,
        compute_stable_id as storage_stable_id
    )
except ImportError:
    from scripts.storage import (
        atomic_write_json,
        safe_read_json,
        atomic_write_text,
        merge_crm_tracking,
        compute_stable_id as storage_stable_id
    )

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

def load_env_file():
    """Carga variables desde el archivo .env si no están presentes en el entorno."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(os.getcwd(), ".env"),
        os.path.join(script_dir, ".env"),
        os.path.join(script_dir, "..", ".env"),
    ]
    for p in candidates:
        abs_p = os.path.abspath(p)
        if os.path.exists(abs_p):
            try:
                with open(abs_p, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k, v = k.strip(), v.strip().strip('"').strip("'")
                            if k and k not in os.environ:
                                os.environ[k] = v
                break
            except Exception:
                pass

load_env_file()

# Módulo desacoplado de Inteligencia Artificial (Gemini, Cloudflare, Groq, Mistral y Fallback)
from ai_providers import (
    RateLimitError,
    DEFAULT_MODELS,
    strip_accents,
    get_audit_prompt,
    parse_json_response,
    call_gemini_batch,
    call_cloudflare_batch,
    call_groq_batch,
    call_mistral_batch,
    rule_based_audit,
    call_multiprovider_batch,
)

def compute_stable_id(plat: str, url: str, msg: str) -> str:
    """Calcula un ID determinista e inmutable basado en la entidad, no en la posición."""
    plat_low = strip_accents(plat)
    if "tusclases" in plat_low:
        m = re.search(r"-(\d{5,9})(?:\.aspx)?/?$", url)
        if m:
            prefix = "tc_ar" if ".com.ar" in url else ("tc_cl" if "particulares.cl" in url else ("tc_mx" if ".mx" in url else ("tc_co" if ".co" in url else ("tc_pe" if ".pe" in url else "tc_es"))))
            return f"{prefix}_{m.group(1)}"
    elif "tablon" in plat_low:
        m = re.search(r"-(\d{5,9})\.htm", url)
        if m:
            return f"tablon_es_{m.group(1)}"
    elif "cronoshare" in plat_low:
        m = re.search(r"-(\d{5,9})/?$", url)
        if m:
            return f"cronoshare_{m.group(1)}"
    elif "reddit" in plat_low:
        m = re.search(r"comments/([a-z0-9]+)", url)
        if m:
            return f"reddit_{m.group(1)}"

    # Fallback criptográfico SHA-256 truncado del contenido
    digest = hashlib.sha256(f"{plat.strip()}|{url.strip()}|{msg[:120].strip()}".encode("utf-8")).hexdigest()[:10]
    prefix = re.sub(r"[^a-z0-9]", "", plat_low)[:8] or "lead"
    return f"{prefix}_{digest}"

def sanitize_csv(val) -> str:
    """Sanitiza campos contra inyección de fórmulas CSV preservando booleanos reales."""
    if val is None:
        return ""
    if isinstance(val, bool):
        return "true" if val else "false"
    s = str(val)
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + s
    return s.strip()

def safe_hyperlink(url: str) -> str:
    """Construye una fórmula HYPERLINK segura para Excel/Sheets con comillas escapadas."""
    url_clean = str(url or "").strip()
    if not url_clean.startswith(("http://", "https://")):
        return sanitize_csv(url_clean)
    escaped = url_clean.replace('"', '""')
    return f'=HYPERLINK("{escaped}", "🔗 Abrir Anuncio")'

def normalize_item(item: Dict[str, Any], idx: int = 1) -> Dict[str, Any]:
    """Normaliza un lead asegurando campos compatibles con el CRM y la visualización."""
    url = item.get("enlace al anuncio") or item.get("enlace_anuncio") or item.get("enlace") or ""
    plat = item.get("plataforma") or "Desconocida"
    msg = item.get("mensaje/descripción") or item.get("mensaje_descripcion") or item.get("mensaje") or ""
    loc = item.get("país/ubicación") or item.get("pais_ubicacion") or item.get("ubicacion") or ""
    mat = item.get("materia") or "Ciencias Exactas"
    lvl = item.get("nivel educativo") or item.get("nivel_educativo") or "Secundario / Universitario"
    pub = item.get("fecha de publicación") or item.get("fecha_publicacion") or ""
    cap = item.get("fecha_captura") or "2026-11-01"
    met = item.get("método de contacto directo") or item.get("metodo_contacto_directo") or "Formulario en plataforma"
    
    lid = item.get("id") or compute_stable_id(plat, url, msg)
    loc_norm = strip_accents(loc)
    msg_norm = strip_accents(msg)
    plat_norm = strip_accents(plat)

    # Detección determinista de País
    pais = item.get("pais")
    if not pais:
        if any(w in loc_norm for w in ["espana", "madrid", "barcelona", "lleida", "galapagar", "irun", "lakuntza", "benidorm"]):
            pais = "España"
        elif any(w in loc_norm for w in ["argentina", "buenos aires", "rosario", "la plata", "wilde", "cordoba", "san justo", "mendoza", "city bell", "bahia blanca"]):
            pais = "Argentina"
        elif any(w in loc_norm for w in ["chile", "santiago", "vina", "conchali", "los vilos", "nunoa"]):
            pais = "Chile"
        elif any(w in loc_norm for w in ["colombia", "bogota", "manizales", "subachoque", "la calera"]):
            pais = "Colombia"
        elif any(w in loc_norm for w in ["mexico", "cdmx"]):
            pais = "México"
        elif any(w in loc_norm for w in ["peru", "lima", "chiclayo"]):
            pais = "Perú"
        else:
            pais = loc.split(" - ")[0] if " - " in loc else "Internacional"

    lvl_norm = strip_accents(lvl)
    lvl_low = lvl_norm
    # Detección de nivel_categoria cerrado
    lvl_cat = item.get("nivel_categoria")
    if not lvl_cat:
        if "primaria" in lvl_low:
            lvl_cat = "Primaria"
        elif "pre" in lvl_low or "paes" in lvl_low or "cambridge" in lvl_low:
            lvl_cat = "Pre-Universitario"
        elif "universitario" in lvl_low or "cbc" in lvl_low or "uade" in lvl_low or "pucp" in lvl_low or "facultad" in lvl_low:
            lvl_cat = "Universitario"
        elif "fp" in lvl_low or "terciario" in lvl_low:
            lvl_cat = "Terciario / FP"
        elif "acceso" in lvl_low or "+25" in lvl_low:
            lvl_cat = "Acceso"
        else:
            lvl_cat = "Secundario"

    # Canal y costo
    is_crono = "cronoshare" in plat_norm
    canal = item.get("canal") or ("creditos" if is_crono else "directo")
    enlace_tipo = item.get("enlace_tipo") or ("categoria" if is_crono else "ficha_individual")
    es_permalink = item.get("es_permalink", False if is_crono else True)
    costo = item.get("costo_contacto") or ("Requiere créditos pagos (Cronos)" if is_crono else ("Gratuito con registro" if "tusclases" in plat_norm else "Gratuito directo"))

    modalidad = item.get("modalidad")
    if not modalidad:
        if "presencial" in msg_norm or "presencial" in loc_norm or "domicilio" in msg_norm:
            modalidad = "Presencial"
        elif "online" in msg_norm or "virtual" in msg_norm or "online" in loc_norm or "online" in url.lower():
            modalidad = "Online"
        else:
            modalidad = "A convenir"

    alerta_modalidad = item.get("alerta_modalidad", "")
    elegible_virtual = item.get("elegible_virtual")
    if elegible_virtual is None:
        elegible_virtual = (modalidad != "Presencial" and "euskera" not in msg_norm and "primaria" not in lvl_norm)

    item.update({
        "id": lid,
        "plataforma": plat,
        "país/ubicación": loc,
        "pais": pais,
        "nombre": item.get("nombre") or "",
        "persona_id": item.get("persona_id") or lid,
        "materia": mat,
        "nivel educativo": lvl,
        "nivel_categoria": lvl_cat,
        "tema": item.get("tema") or mat,
        "modalidad": modalidad,
        "modalidad_solicitada": item.get("modalidad_solicitada") or f"Clases de {mat}",
        "elegible_virtual": elegible_virtual,
        "alerta_modalidad": alerta_modalidad,
        "idioma": item.get("idioma", "Español"),
        "enlace_tipo": enlace_tipo,
        "canal": canal,
        "canal_detalle": item.get("canal_detalle") or costo,
        "costo_contacto": costo,
        "costo_detalle": item.get("costo_detalle", costo),
        "enlace al anuncio": url,
        "es_permalink": es_permalink,
        "fecha de publicación": pub,
        "fecha_captura": cap,
        "mensaje/descripción": msg,
        "método de contacto directo": met
    })
    return item

def notify_telegram_lead(lead: Dict[str, Any]):
    """Envía una alerta instantánea a Telegram si las claves están en .env."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        return
    msg = (
        "🎓 <b>¡NUEVO ALUMNO DE CIENCIAS EXACTAS!</b>\n\n"
        f"📚 <b>Materia:</b> {lead.get('materia', 'No especificada')}\n"
        f"📍 <b>Ubicación:</b> {lead.get('país/ubicación', 'No especificada')}\n"
        f"🎯 <b>Nivel:</b> {lead.get('nivel educativo', 'A convenir')}\n\n"
        f"💬 <b>Mensaje:</b> <i>{lead.get('mensaje/descripción', '')[:250]}</i>\n\n"
        f"🔗 <a href='{lead.get('enlace al anuncio', '')}'>Abrir y Contactar Alumno</a>"
    )
    try:
        from extract_telegram import send_telegram_notification
        send_telegram_notification(bot_token, chat_id, msg)
    except Exception:
        pass

def save_classifier_predictions(
    items: List[Dict[str, Any]],
    output_path: str = "data/predicciones_clasificador.json",
    model_name: str = "gemini-3.5-flash"
) -> int:
    """Persiste las predicciones de la IA en data/predicciones_clasificador.json de forma acumulativa y atómica."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    existing: List[Dict[str, Any]] = safe_read_json(output_path, default=[])
    preds_by_id = {p.get("id"): p for p in existing if isinstance(p, dict) and "id" in p}

    now_iso = datetime.now(timezone.utc).isoformat()
    for it in items:
        lid = it.get("id")
        if not lid:
            continue
        dec = it.get("decision_ia", "")
        just = it.get("justificacion_ia", "")
        is_stud = it.get("is_student", dec == "Aprobado")

        preds_by_id[lid] = {
            "id": lid,
            "decision_ia": dec,
            "justificacion_ia": just,
            "is_student": is_stud,
            "modelo": model_name,
            "timestamp": now_iso
        }

    atomic_write_json(output_path, list(preds_by_id.values()))
    return len(preds_by_id)


def check_and_record_source_health(
    listings: List[Dict[str, Any]],
    output_csv: str = "data/salud_fuentes.csv",
    today_str: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Monitorea la salud de cada fuente/plataforma extractora (F3):
    Registra data/salud_fuentes.csv(fecha,fuente,n)
    Si n == 0 o n < 0.3 * mediana_ult7, dispara alerta: FUENTE_ROTA <fuente>.
    """
    import statistics
    from collections import Counter

    fecha = today_str or datetime.now().strftime("%Y-%m-%d")
    os.makedirs(os.path.dirname(os.path.abspath(output_csv)), exist_ok=True)

    # Leer historial previo
    history_by_fuente: Dict[str, List[int]] = {}
    existing_rows = []
    if os.path.exists(output_csv):
        try:
            with open(output_csv, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    existing_rows.append(r)
                    f_name = r.get("fuente", "").strip()
                    try:
                        n_val = int(r.get("n", 0))
                        history_by_fuente.setdefault(f_name, []).append(n_val)
                    except ValueError:
                        pass
        except Exception:
            pass

    # Conteo actual por fuente
    current_counts = Counter()
    for it in listings:
        plat = it.get("plataforma") or "Desconocida"
        current_counts[plat] += 1

    all_fuentes = sorted(set(list(history_by_fuente.keys()) + list(current_counts.keys())))
    if not all_fuentes:
        all_fuentes = ["TusClases", "Tablón de Anuncios", "Cronoshare", "Reddit", "Telegram"]

    alerts = []
    new_records = []

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    for fuente in all_fuentes:
        n = current_counts.get(fuente, 0)
        past_n = history_by_fuente.get(fuente, [])
        recent_7 = past_n[-7:] if past_n else []
        mediana_ult7 = float(statistics.median(recent_7)) if recent_7 else float(n)

        # Regla estricta: n == 0 OR n < 0.3 * mediana_ult7
        is_broken = (n == 0) or (mediana_ult7 > 0 and n < 0.3 * mediana_ult7)

        if is_broken:
            alert_msg = f"FUENTE_ROTA {fuente} (n={n}, mediana_ult7={mediana_ult7:.1f})"
            alerts.append({
                "fuente": fuente,
                "n": n,
                "mediana_ult7": mediana_ult7,
                "mensaje": alert_msg
            })
            print(f"🚨 [ALERTA FUENTE] {alert_msg}", file=sys.stderr)
            if bot_token and chat_id:
                try:
                    from extract_telegram import send_telegram_notification
                    send_telegram_notification(bot_token, chat_id, f"🚨 <b>FUENTE_ROTA</b> {fuente}\nExtracción: {n} anuncios (Mediana 7d: {mediana_ult7:.1f})")
                except Exception:
                    pass

        new_records.append({"fecha": fecha, "fuente": fuente, "n": n})

    seen_keys = {(r.get("fecha"), r.get("fuente")) for r in existing_rows}
    file_exists = os.path.exists(output_csv) and os.path.getsize(output_csv) > 0
    with open(output_csv, "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["fecha", "fuente", "n"], lineterminator="\r\n")
        if not file_exists:
            writer.writeheader()
        for rec in new_records:
            if (rec["fecha"], rec["fuente"]) not in seen_keys:
                writer.writerow(rec)

    return alerts


def apply_lead_expiration(
    leads: List[Dict[str, Any]],
    max_days: int = 21,
    reference_date: Optional[datetime] = None
) -> int:
    """
    F5 Caducidad automática:
    fecha_captura > 21d AND estado == 'nuevo' -> estado := 'vencido'.
    Retorna la cantidad de leads marcados como vencidos.
    """
    ref_dt = reference_date or datetime.now()
    expired_count = 0

    for item in leads:
        current_state = (item.get("estado") or item.get("estado_contacto") or "nuevo").strip().lower()
        if current_state not in ["nuevo", "pendiente"]:
            continue

        cap_str = item.get("fecha_captura") or item.get("fecha de publicación") or item.get("fecha_publicacion") or ""
        m = re.search(r"(\d{4}-\d{2}-\d{2})", str(cap_str))
        if not m:
            continue

        try:
            lead_dt = datetime.strptime(m.group(1), "%Y-%m-%d")
            diff_days = (ref_dt.date() - lead_dt.date()).days
            if diff_days > max_days:
                item["estado"] = "vencido"
                hist = item.get("historial_estados") or []
                now_iso = ref_dt.isoformat()
                hist.append({
                    "from": current_state,
                    "to": "vencido",
                    "estado": "vencido",
                    "ts": now_iso,
                    "motivo": f"Caducidad automática por inactividad ({diff_days} días > {max_days} días)"
                })
                item["historial_estados"] = hist
                item["ts_estado"] = now_iso
                expired_count += 1
        except Exception:
            pass

    return expired_count


def cmd_audit(args):
    """Clasifica de forma incremental los nuevos anuncios brutos usando el Triple Motor de IA."""
    print(f"--> Iniciando auditoría semántica con modelo: {args.model}")
    with open(args.input, "r", encoding="utf-8") as f:
        raw_items = json.load(f)

    # Normalizar leads entrantes con IDs deterministas
    raw_items = [normalize_item(it, idx + 1) for idx, it in enumerate(raw_items)]

    # 0. Monitoreo y registro de salud de fuentes (F3)
    check_and_record_source_health(raw_items)

    # 1. Cargar históricos ya auditados de manera segura y concurrente
    existing_approved = safe_read_json(args.output_approved, default=[])
    existing_discarded = safe_read_json(args.output_discarded, default=[])
    approved = list(existing_approved)
    discarded = list(existing_discarded)

    audited_ids = {it["id"] for it in approved + discarded if "id" in it}
    audited_urls = {it.get("enlace al anuncio") or it.get("enlace_anuncio") for it in approved + discarded if it.get("enlace al anuncio") or it.get("enlace_anuncio")}

    pending_items = [
        it for it in raw_items
        if it["id"] not in audited_ids and (it.get("enlace al anuncio") or it.get("enlace_anuncio")) not in audited_urls
    ]

    print(f"Total anuncios: {len(raw_items)} | Previamente auditados: {len(audited_ids)} | Nuevos a auditar: {len(pending_items)}")

    if not pending_items:
        print("[OK] No hay nuevos anuncios pendientes de clasificar. Base de datos al día.")
        save_classifier_predictions(approved + discarded, getattr(args, "output_predictions", "data/predicciones_clasificador.json"), model_name=args.model)
        return

    batch_size = args.batch_size
    new_approved_count = 0

    for i in range(0, len(pending_items), batch_size):
        batch = pending_items[i:i + batch_size]
        items_payload = []
        for item in batch:
            items_payload.append({
                "id": item.get("id"),
                "plataforma": item.get("plataforma", ""),
                "materia": item.get("materia", ""),
                "ubicacion": item.get("país/ubicación", ""),
                "mensaje": item.get("mensaje/descripción", ""),
                "enlace": item.get("enlace al anuncio", "")
            })

        print(f"  Procesando lote {i // batch_size + 1} de {(len(pending_items) + batch_size - 1) // batch_size}...")
        try:
            results = call_multiprovider_batch(items_payload, primary_model=args.model, api_key=args.api_key)
            result_map = {r["id"]: r for r in results if isinstance(r, dict) and "id" in r}
            for item in batch:
                res = result_map.get(item["id"], {
                    "is_student": False,
                    "decision_ia": "Descartado",
                    "justificacion_ia": "No clasificado en la respuesta de la IA"
                })
                item["decision_ia"] = res.get("decision_ia", "Aprobado" if res.get("is_student") else "Descartado")
                item["justificacion_ia"] = res.get("justificacion_ia", "")
                if res.get("is_student") is True:
                    approved.append(item)
                    new_approved_count += 1
                    notify_telegram_lead(item)
                else:
                    discarded.append(item)
        except Exception as e:
            print(f"  [Error en lote] {e}. Registros del lote marcados para revisión manual.", file=sys.stderr)
            for item in batch:
                item["decision_ia"] = "Pendiente de revisión"
                item["justificacion_ia"] = f"Error en inferencia de IA: {e}"
                discarded.append(item)

        time.sleep(1.0)

    # Preservar el seguimiento del CRM (notas, estados de contacto) y guardar atómicamente
    approved = merge_crm_tracking(approved, existing_approved)
    atomic_write_json(args.output_approved, approved)
    atomic_write_json(args.output_discarded, discarded)

    # Persistir predicciones del clasificador (F1)
    save_classifier_predictions(approved + discarded, getattr(args, "output_predictions", "data/predicciones_clasificador.json"), model_name=args.model)

    print(f"[OK] Auditoría completada. Nuevos alumnos aprobados: {new_approved_count} | Total en base de datos: {len(approved)}")
    print(f"  Archivo aprobados: {args.output_approved}")
    print(f"  Archivo descartados: {args.output_discarded}")

def cmd_build(args):
    """Compila dashboard.html y los CSVs con los datos auditados más recientes de forma idempotente."""
    print("--> Compilando Dashboard CRM y CSVs...")
    with open(args.approved, "r", encoding="utf-8") as f:
        approved_leads = json.load(f)

    # Normalización consistente y evaluación de caducidad automática (> 21d) (F5)
    approved_leads = [normalize_item(it, idx + 1) for idx, it in enumerate(approved_leads)]
    expired_count = apply_lead_expiration(approved_leads)
    if expired_count > 0:
        print(f"  [Caducidad F5] {expired_count} leads antiguos marcados como vencidos (>21 días).")
        atomic_write_json(args.approved, approved_leads)

    discarded_leads = []
    if args.discarded and os.path.exists(args.discarded):
        with open(args.discarded, "r", encoding="utf-8") as f:
            discarded_leads = json.load(f)

    # 1. Generar alumnos_ciencias_exactas.csv (Formato Canónico Estricto de 8 columnas según especificación)
    canonical_headers = [
        "plataforma",
        "enlace al anuncio",
        "materia",
        "nivel educativo",
        "país/ubicación",
        "fecha de publicación",
        "mensaje/descripción",
        "método de contacto directo",
    ]

    with open(args.output_csv, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=canonical_headers, lineterminator="\r\n")
        writer.writeheader()
        for r in approved_leads:
            # Normalizar nivel al contrato canónico: 'Secundario' o 'Universitario'
            raw_cat = r.get("nivel_categoria", "")
            if raw_cat in ["Universitario", "Pre-Universitario", "Terciario / FP", "Acceso"]:
                canonical_level = "Universitario"
            else:
                canonical_level = "Secundario"

            writer.writerow({
                "plataforma": sanitize_csv(r.get("plataforma", "")),
                "enlace al anuncio": sanitize_csv(r.get("enlace al anuncio", "")),
                "materia": sanitize_csv(r.get("materia", "")),
                "nivel educativo": canonical_level,
                "país/ubicación": sanitize_csv(r.get("país/ubicación", "")),
                "fecha de publicación": sanitize_csv(r.get("fecha de publicación") or r.get("fecha_captura") or "2026-11-01"),
                "mensaje/descripción": sanitize_csv(r.get("mensaje/descripción", "")),
                "método de contacto directo": sanitize_csv(r.get("método de contacto directo", ""))
            })

    # 2. Generar dashboard_crm.csv con TODAS las columnas protegidas contra inyección
    crm_headers = [
        "ID_Prospecto", "Origen", "Nombre_Alumno", "Materia", "Tema_Especifico", "Nivel_Educativo",
        "Nivel_Categoria", "Modalidad", "Alerta_Modalidad", "Canal", "Costo_Contacto", "Estado_Gestion",
        "Link_Anuncio", "Anuncio_en_Si", "Forma_Contacto", "Fecha_Publicacion", "Fecha_Captura", "Criterio_IA"
    ]

    crm_rows = []
    for r in approved_leads:
        url = r.get("enlace al anuncio", "")
        crm_rows.append({
            "ID_Prospecto": sanitize_csv(r.get("id", "")),
            "Origen": sanitize_csv(f"{r.get('plataforma','')} ({r.get('país/ubicación','')})"),
            "Nombre_Alumno": sanitize_csv(r.get("nombre") or "No especificado"),
            "Materia": sanitize_csv(r.get("materia", "")),
            "Tema_Especifico": sanitize_csv(r.get("tema", "")),
            "Nivel_Educativo": sanitize_csv(r.get("nivel educativo", "")),
            "Nivel_Categoria": sanitize_csv(r.get("nivel_categoria", "")),
            "Modalidad": sanitize_csv(r.get("modalidad", "Online")),
            "Alerta_Modalidad": sanitize_csv(r.get("alerta_modalidad", "")),
            "Canal": sanitize_csv(r.get("canal", "directo")),
            "Costo_Contacto": sanitize_csv(r.get("costo_contacto", "Gratuito")),
            "Estado_Gestion": "Pendiente",
            "Link_Anuncio": safe_hyperlink(url),
            "Anuncio_en_Si": sanitize_csv(r.get("mensaje/descripción", "")),
            "Forma_Contacto": sanitize_csv(r.get("método de contacto directo", "")),
            "Fecha_Publicacion": sanitize_csv(r.get("fecha de publicación", "")),
            "Fecha_Captura": sanitize_csv(r.get("fecha_captura", "")),
            "Criterio_IA": sanitize_csv(r.get("justificacion_ia", ""))
        })

    crm_csv_path = args.output_csv.replace("alumnos_ciencias_exactas.csv", "dashboard_crm.csv")
    if crm_csv_path == args.output_csv:
        crm_csv_path = "dashboard_crm.csv"
    with open(crm_csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=crm_headers, lineterminator="\r\n")
        writer.writeheader()
        writer.writerows(crm_rows)

    # 3. Inyección idempotente en dashboard.html (con escape de tags HTML)
    app_data = json.dumps(approved_leads, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e")
    disc_data = json.dumps(discarded_leads, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e")

    with open("dashboard.html", "r", encoding="utf-8") as f:
        current_html = f.read()

    # Reemplazo idempotente que consume toda la línea de RAW_DATA y DISCARDED_DATA sin romperse con punto y coma internos
    pattern = r"var RAW_DATA = [^\r\n]+;\r?\n(?:\s*var DISCARDED_DATA = [^\r\n]+;\r?\n)*"
    replacement = f"var RAW_DATA = {app_data};\n  var DISCARDED_DATA = {disc_data};\n"
    if re.search(pattern, current_html):
        new_html = re.sub(pattern, lambda m: replacement, current_html, count=1)
    else:
        new_html = current_html

    atomic_write_text(args.output_html, new_html, encoding="utf-8")

    print(f"[OK] Archivos generados con éxito: {args.output_html}, {args.output_csv}, {crm_csv_path}")

    # Sincronización en directorio secundario opcional (vía variable de entorno)
    if args.desktop_sync:
        export_target = os.environ.get("PROSPECTOR_EXPORT_DIR")
        if export_target and os.path.exists(export_target):
            current_abs = os.path.abspath(".")
            target_abs = os.path.abspath(export_target)
            if current_abs.lower() != target_abs.lower():
                try:
                    shutil.copy2(args.output_html, os.path.join(export_target, os.path.basename(args.output_html)))
                    shutil.copy2(args.output_csv, os.path.join(export_target, os.path.basename(args.output_csv)))
                    shutil.copy2(crm_csv_path, os.path.join(export_target, os.path.basename(crm_csv_path)))
                    print(f"[OK] Sincronizado en directorio secundario: {export_target}")
                except Exception as e:
                    print(f"[Aviso] Sincronización secundaria omitida: {e}")

def cmd_run(args):
    """Ejecuta el pipeline completo de prospección y compilación."""
    print("=== EJECUCIÓN DEL PIPELINE COMPLETO PROSPECTOR ===")
    raw_path = "data/extracted_listings.json"
    
    # Si no existe o se pide refresh, invocar extractor web
    if not os.path.exists(raw_path):
        print("-> data/extracted_listings.json no encontrado. Iniciando extracción web...")
        import subprocess
        subprocess.run([sys.executable, "scripts/run_extraction.py"], check=True)

    args.input = raw_path
    args.output_approved = "data/dataset_canonico_auditado.json"
    args.output_discarded = "data/descartados_auditoria.json"
    
    if os.environ.get("GEMINI_API_KEY"):
        cmd_audit(args)
    else:
        print("[Aviso] GEMINI_API_KEY no detectada. Usando dataset_canonico_auditado.json existente.")
    
    args.approved = args.output_approved
    args.discarded = args.output_discarded
    args.output_html = "dashboard.html"
    args.output_csv = "alumnos_ciencias_exactas.csv"
    cmd_build(args)

def main():
    parser = argparse.ArgumentParser(description="CLI Prospector de Alumnos de Ciencias Exactas")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # Subcomando audit
    p_audit = subparsers.add_parser("audit", help="Audita anuncios con Gemini Flash")
    p_audit.add_argument("--input", default="data/extracted_listings.json")
    p_audit.add_argument("--model", default="gemini-3.5-flash")
    p_audit.add_argument("--batch-size", type=int, default=10)
    p_audit.add_argument("--api-key", default=None)
    p_audit.add_argument("--output-approved", default="data/dataset_canonico_auditado.json")
    p_audit.add_argument("--output-discarded", default="data/descartados_auditoria.json")
    p_audit.add_argument("--output-predictions", default="data/predicciones_clasificador.json")
    p_audit.set_defaults(func=cmd_audit)

    # Subcomando build
    p_build = subparsers.add_parser("build", help="Compila dashboard.html y CSVs")
    p_build.add_argument("--approved", default="data/dataset_canonico_auditado.json")
    p_build.add_argument("--discarded", default="data/descartados_auditoria.json")
    p_build.add_argument("--output-html", default="dashboard.html")
    p_build.add_argument("--output-csv", default="alumnos_ciencias_exactas.csv")
    p_build.add_argument("--desktop-sync", action="store_true")
    p_build.set_defaults(func=cmd_build)

    # Subcomando run
    p_run = subparsers.add_parser("run", help="Ejecuta todo el flujo de auditoría y compilación")
    p_run.add_argument("--model", default="gemini-3.5-flash")
    p_run.add_argument("--batch-size", type=int, default=10)
    p_run.add_argument("--api-key", default=None)
    p_run.add_argument("--desktop-sync", action="store_true")
    p_run.set_defaults(func=cmd_run)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
