#!/usr/bin/env python3
"""
Prospector CLI - Sistema Autónomo de Captación y Auditoría de Alumnos de Ciencias Exactas
Modelos IA: gemini-2.5-flash / gemini-3-flash-preview / gemini-2.5-pro
Destinatario: Prof. Alejo Ongaro (alejoongaro@gmail.com)
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
from typing import List, Dict, Any

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

class RateLimitError(Exception):
    """Excepción cuando se recibe HTTP 429 de la API de Google."""
    pass

DEFAULT_MODELS = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.8-flash", "gemma-4-31b-it"]

def strip_accents(text: str) -> str:
    """Elimina diacríticos y acentos para comparaciones robustas."""
    return "".join(
        c for c in unicodedata.normalize("NFD", str(text or ""))
        if unicodedata.category(c) != "Mn"
    ).lower()

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
    s = str(val).strip()
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + s
    return s

def safe_hyperlink(url: str) -> str:
    """Construye una fórmula HYPERLINK segura para Excel/Sheets con comillas escapadas."""
    url_clean = str(url or "").strip()
    if not url_clean.startswith(("http://", "https://")):
        return sanitize_csv(url_clean)
    escaped = url_clean.replace('"', '""')
    return f'=HYPERLINK("{escaped}", "🔗 Abrir Anuncio")'

def call_gemini_batch(items: List[Dict[str, Any]], model: str = "gemini-3.5-flash-lite", api_key: str = None, max_retries: int = 3):
    """
    Evalúa un lote de anuncios con modelos oficiales de Google AI Studio.
    Forzado en modo responseMimeType: 'application/json'.
    """
    if not api_key:
        api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY no encontrada en variables de entorno ni en configuración.")

    models_to_try = [model] + [m for m in DEFAULT_MODELS if m != model]

    prompt = f"""Eres un auditor estricto de anuncios clasificados educativos para un profesor particular de ciencias exactas.
Tu objetivo es discriminar con rigor si cada anuncio fue escrito por un ESTUDIANTE o PADRE REAL buscando contratar clases particulares (is_student: true), o si por el contrario es un INSTITUTO, ACADEMIA, OFERTA LABORAL o PROFESOR OFRECIENDO CLASES (is_student: false).

CRITERIOS ESTRICTOS DE EXCLUSIÓN (is_student: false):
- Si es una academia, instituto o colegio buscando profesores (ej. 'se busca docente', 'necesitamos profesor').
- Si es una oferta de trabajo/empleo para profesores (ej. vacantes, 'oferta de trabajo').
- Si es un profesor particular ofreciendo sus servicios (ej. 'Doy clases particulares', 'Profesor con 10 años de experiencia').
- Si el texto está mezclado con menús web o índices de navegación por provincias/asignaturas.

CRITERIOS DE INCLUSIÓN (is_student: true):
- Estudiante que dice 'necesito clases', 'busco profesor', 'preparar examen de álgebra / análisis / física / biofísica', 'apoyo escolar', etc.
- Padre/madre buscando tutor para su hijo/a.

Evalúa esta lista de anuncios:
{json.dumps(items, ensure_ascii=False, indent=2)}

Devuelve estrictamente un JSON válido con esta estructura:
[
  {{
    "id": "identificador_del_anuncio",
    "is_student": true,
    "decision_ia": "Aprobado" | "Descartado",
    "justificacion_ia": "Explicación concisa y clara del motivo de la decisión"
  }}
]"""

    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"}
    }).encode("utf-8")

    last_error = None
    for target_model in models_to_try:
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent"
        for attempt in range(1, max_retries + 1):
            req = urllib.request.Request(
                endpoint,
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": api_key
                }
            )
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    raw_text = resp_data["candidates"][0]["content"]["parts"][0]["text"]
                    results = json.loads(raw_text)
                    if isinstance(results, list):
                        return results
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="replace")
                if e.code == 429:
                    backoff = attempt * 3.0
                    print(f"[RateLimit 429] Modelo {target_model} saturado. Reintentando en {backoff}s...", file=sys.stderr)
                    time.sleep(backoff)
                    last_error = RateLimitError(f"HTTP 429: {err_body}")
                elif e.code == 404:
                    print(f"[HTTP 404] Modelo {target_model} no disponible en este endpoint. Probando siguiente modelo...", file=sys.stderr)
                    last_error = e
                    break
                elif e.code in (500, 502, 503, 504):
                    backoff = attempt * 2.0
                    print(f"[HTTP {e.code}] Error temporal del servidor. Reintentando en {backoff}s...", file=sys.stderr)
                    time.sleep(backoff)
                    last_error = e
                else:
                    print(f"[HTTP {e.code}] Error en {target_model}: {err_body}", file=sys.stderr)
                    last_error = e
                    break
            except Exception as e:
                print(f"[Error de conexión] {str(e)}", file=sys.stderr)
                last_error = e
                time.sleep(2.0)

    raise RuntimeError(f"Fallo en la inferencia con todos los modelos Gemini evaluados. Último error: {last_error}")

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

def cmd_audit(args):
    """Clasifica los anuncios brutos usando Gemini Flash y guarda las decisiones."""
    print(f"--> Iniciando auditoría semántica con modelo: {args.model}")
    with open(args.input, "r", encoding="utf-8") as f:
        raw_items = json.load(f)

    # Normalizar leads entrantes con IDs deterministas
    raw_items = [normalize_item(it, idx + 1) for idx, it in enumerate(raw_items)]

    print(f"Total anuncios a auditar: {len(raw_items)}")
    batch_size = args.batch_size
    approved = []
    discarded = []

    for i in range(0, len(raw_items), batch_size):
        batch = raw_items[i:i + batch_size]
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

        print(f"  Procesando lote {i // batch_size + 1} de {(len(raw_items) + batch_size - 1) // batch_size}...")
        try:
            results = call_gemini_batch(items_payload, model=args.model, api_key=args.api_key)
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
                else:
                    discarded.append(item)
        except Exception as e:
            print(f"  [Error en lote] {e}. Registros del lote marcados para revisión manual.", file=sys.stderr)
            for item in batch:
                item["decision_ia"] = "Pendiente de revisión"
                item["justificacion_ia"] = f"Error en inferencia de IA: {e}"
                discarded.append(item)

        time.sleep(1.0)

    # Guardar salidas
    with open(args.output_approved, "w", encoding="utf-8") as f:
        json.dump(approved, f, ensure_ascii=False, indent=2)

    with open(args.output_discarded, "w", encoding="utf-8") as f:
        json.dump(discarded, f, ensure_ascii=False, indent=2)

    print(f"[OK] Auditoría completa. Aprobados: {len(approved)} | Descartados: {len(discarded)}")
    print(f"  Archivo aprobados: {args.output_approved}")
    print(f"  Archivo descartados: {args.output_discarded}")

def cmd_build(args):
    """Compila dashboard.html y los CSVs con los datos auditados más recientes de forma idempotente."""
    print("--> Compilando Dashboard CRM y CSVs...")
    with open(args.approved, "r", encoding="utf-8") as f:
        approved_leads = json.load(f)

    # Normalización consistente
    approved_leads = [normalize_item(it, idx + 1) for idx, it in enumerate(approved_leads)]

    discarded_leads = []
    if args.discarded and os.path.exists(args.discarded):
        with open(args.discarded, "r", encoding="utf-8") as f:
            discarded_leads = json.load(f)

    # 1. Generar alumnos_ciencias_exactas.csv
    canonical_headers = [
        "id", "plataforma", "país/ubicación", "pais", "nombre", "persona_id",
        "materia", "nivel educativo", "nivel_categoria", "tema", "modalidad", "modalidad_solicitada",
        "elegible_virtual", "alerta_modalidad", "idioma", "enlace_tipo", "canal",
        "costo_contacto", "enlace al anuncio", "es_permalink", "fecha de publicación",
        "fecha_captura", "mensaje/descripción", "método de contacto directo", "decision_ia", "justificacion_ia"
    ]

    with open(args.output_csv, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=canonical_headers)
        writer.writeheader()
        for r in approved_leads:
            writer.writerow({k: sanitize_csv(r.get(k, "")) for k in canonical_headers})

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
        writer = csv.DictWriter(f, fieldnames=crm_headers)
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

    with open(args.output_html, "w", encoding="utf-8") as f:
        f.write(new_html)

    print(f"[OK] Archivos generados con éxito: {args.output_html}, {args.output_csv}, {crm_csv_path}")

    # Sincronización en Escritorio (solo si se ejecuta fuera de él)
    if args.desktop_sync:
        desktop = os.environ.get("DESKTOP_DIR") or r"E:\OneDrive\Escritorio\Prospeccion_Alumnos_Ciencias"
        if os.path.exists(desktop):
            current_abs = os.path.abspath(".")
            desktop_abs = os.path.abspath(desktop)
            if current_abs.lower() != desktop_abs.lower():
                try:
                    shutil.copy2(args.output_html, f"{desktop}\\{os.path.basename(args.output_html)}")
                    shutil.copy2(args.output_csv, f"{desktop}\\{os.path.basename(args.output_csv)}")
                    shutil.copy2(crm_csv_path, f"{desktop}\\{os.path.basename(crm_csv_path)}")
                    print(f"[OK] Sincronizado en Escritorio: {desktop}")
                except Exception as e:
                    print(f"[Aviso] Sincronización en Escritorio omitida: {e}")

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
    p_audit.add_argument("--model", default="gemini-3.5-flash-lite")
    p_audit.add_argument("--batch-size", type=int, default=10)
    p_audit.add_argument("--api-key", default=None)
    p_audit.add_argument("--output-approved", default="data/dataset_canonico_auditado.json")
    p_audit.add_argument("--output-discarded", default="data/descartados_auditoria.json")
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
    p_run.add_argument("--model", default="gemini-3.5-flash-lite")
    p_run.add_argument("--batch-size", type=int, default=10)
    p_run.add_argument("--api-key", default=None)
    p_run.add_argument("--desktop-sync", action="store_true")
    p_run.set_defaults(func=cmd_run)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
