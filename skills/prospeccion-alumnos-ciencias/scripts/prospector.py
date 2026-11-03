#!/usr/bin/env python3
"""
Prospector CLI - Sistema Autónomo de Captación y Auditoría de Alumnos de Ciencias Exactas
Modelo IA: Gemini 3.6 Flash / Gemini 3.8 Flash
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

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

class RateLimitError(Exception):
    """Excepción cuando se recibe HTTP 429 de la API de Google."""
    pass

def call_gemini_batch(items, model="gemini-3.6-flash", api_key=None, max_retries=3):
    """
    Evalúa un lote de anuncios con Gemini 3.6 Flash (con fallback a gemini-3.8-flash).
    Forzado en modo responseMimeType: 'application/json'.
    """
    if not api_key:
        api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY no encontrada en variables de entorno.")

    models_to_try = [model, "gemini-3.8-flash", "gemini-3-flash-preview"]
    if model in models_to_try:
        models_to_try.remove(model)
    models_to_try.insert(0, model)

    prompt = f"""Eres un auditor estricto de anuncios clasificados educativos para un profesor particular de ciencias exactas.
Tu objetivo es discriminar con rigor si cada anuncio fue escrito por un ESTUDIANTE o PADRE REAL buscando contratar clases particulares (is_student: true), o si por el contrario es un INSTITUTO, ACADEMIA, OFERTA LABORAL o PROFESOR OFRECIENDO CLASES (is_student: false).

CRITERIOS ESTRICTOS DE EXCLUSIÓN (is_student: false):
- Si es una academia, instituto o colegio buscando profesores (ej. 'se busca docente', 'necesitamos profesor', academias en Valladolid).
- Si es una oferta de trabajo/empleo para profesores (ej. vacantes, 'oferta de trabajo').
- Si es un profesor particular ofreciendo sus servicios (ej. 'Doy clases particulares', 'Profesor con 10 años de experiencia').
- Si el texto está mezclado con menús web o índices de categorías.

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
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={api_key}"
        for attempt in range(1, max_retries + 1):
            start_time = time.monotonic()
            req = urllib.request.Request(endpoint, data=payload, headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    raw_text = resp_data["candidates"][0]["content"]["parts"][0]["text"]
                    results = json.loads(raw_text)
                    return results
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="replace")
                if e.code == 429:
                    backoff = attempt * 3.0
                    print(f"[RateLimit 429] Modelo {target_model} saturado. Reintentando en {backoff}s...", file=sys.stderr)
                    time.sleep(backoff)
                    last_error = RateLimitError(f"HTTP 429: {err_body}")
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

def normalize_item(item, idx=1):
    """Normaliza un lead asegurando campos compatibles con el CRM y la visualización."""
    url = item.get("enlace al anuncio") or item.get("enlace_anuncio") or item.get("enlace") or ""
    plat = item.get("plataforma") or "Desconocida"
    msg = item.get("mensaje/descripción") or item.get("mensaje_descripcion") or item.get("mensaje") or ""
    loc = item.get("país/ubicación") or item.get("pais_ubicacion") or item.get("ubicacion") or ""
    mat = item.get("materia") or "Ciencias Exactas"
    lvl = item.get("nivel educativo") or item.get("nivel_educativo") or "Secundario / Universitario"
    pub = item.get("fecha de publicación") or item.get("fecha_publicacion") or "2026-11-02"
    met = item.get("método de contacto directo") or item.get("metodo_contacto_directo") or "Formulario en plataforma"
    
    lid = item.get("id")
    if not lid:
        if "tusclases" in plat.lower() or "tusclasesparticulares" in plat.lower():
            m = re.search(r"-(\d{5,8})\.aspx", url)
            lid = f"tc_{m.group(1)}" if m else f"tc_lead_{idx}"
        elif "tablon" in plat.lower():
            m = re.search(r"-(\d{5,8})\.htm", url)
            lid = f"tablon_{m.group(1)}" if m else f"tablon_lead_{idx}"
        elif "cronoshare" in plat.lower():
            lid = f"cronoshare_lead_{idx}"
        elif "reddit" in plat.lower():
            lid = f"reddit_lead_{idx}"
        else:
            lid = f"lead_{idx}"

    pais = item.get("pais")
    if not pais:
        if any(w in loc for w in ["España", "Madrid", "Barcelona", "Lleida", "Galapagar", "Irun", "Lakuntza", "Benidorm"]):
            pais = "España"
        elif any(w in loc for w in ["Argentina", "Buenos Aires", "Rosario", "La Plata", "Wilde", "Cordoba", "San Justo", "Mendoza", "City Bell"]):
            pais = "Argentina"
        elif any(w in loc for w in ["Chile", "Santiago", "Vina", "Conchali", "Los Vilos", "Nunoa"]):
            pais = "Chile"
        elif any(w in loc for w in ["Colombia", "Bogota", "Manizales", "Subachoque"]):
            pais = "Colombia"
        elif any(w in loc for w in ["México", "Mexico", "CDMX"]):
            pais = "México"
        elif any(w in loc for w in ["Perú", "Peru", "Lima", "Chiclayo"]):
            pais = "Perú"
        else:
            pais = loc.split(" - ")[0] if " - " in loc else "Internacional"

    nombre = item.get("nombre") or "Estudiante"
    costo = item.get("costo_contacto")
    if not costo:
        if "cronoshare" in plat.lower():
            costo = "Requiere créditos pagos (Cronos)"
        elif "tusclases" in plat.lower():
            costo = "Gratuito con registro"
        else:
            costo = "Gratuito directo"

    modalidad = item.get("modalidad", "Online")
    alerta_modalidad = item.get("alerta_modalidad", "")
    elegible_virtual = item.get("elegible_virtual", True)
    if "presencial" in msg.lower() or "presencial" in loc.lower() or "domicilio" in msg.lower():
        if not alerta_modalidad:
            modalidad = "Presencial"
            elegible_virtual = False
            alerta_modalidad = "Pide presencial o a domicilio (Ofrecer pase a Online)"
    if "euskera" in msg.lower():
        elegible_virtual = False
        alerta_modalidad = "Incompatible: pide clases en Euskera"

    item.update({
        "id": lid,
        "plataforma": plat,
        "país/ubicación": loc,
        "pais": pais,
        "nombre": nombre,
        "persona_id": item.get("persona_id") or lid,
        "materia": mat,
        "nivel educativo": lvl,
        "modalidad": modalidad,
        "modalidad_solicitada": item.get("modalidad_solicitada") or f"Clases de {mat}",
        "elegible_virtual": elegible_virtual,
        "alerta_modalidad": alerta_modalidad,
        "idioma": item.get("idioma", "Español"),
        "costo_contacto": costo,
        "costo_detalle": item.get("costo_detalle", costo),
        "enlace al anuncio": url,
        "es_permalink": item.get("es_permalink", True if "cronoshare" not in plat.lower() else False),
        "fecha de publicación": pub,
        "mensaje/descripción": msg,
        "método de contacto directo": met
    })
    return item

def cmd_audit(args):
    """Clasifica los anuncios brutos usando Gemini 3.6/3.8 Flash y guarda las decisiones."""
    print(f"--> Iniciando auditoría semántica con modelo: {args.model}")
    with open(args.input, "r", encoding="utf-8") as f:
        raw_items = json.load(f)

    # Normalizar leads entrantes
    raw_items = [normalize_item(it, idx + 1) for idx, it in enumerate(raw_items)]

    print(f"Total anuncios a auditar: {len(raw_items)}")
    batch_size = args.batch_size
    approved = []
    discarded = []

    for i in range(0, len(raw_items), batch_size):
        batch = raw_items[i:i + batch_size]
        items_payload = []
        for idx_b, item in enumerate(batch):
            items_payload.append({
                "id": item.get("id") or f"lead_{i + idx_b + 1}",
                "plataforma": item.get("plataforma", ""),
                "materia": item.get("materia", ""),
                "ubicacion": item.get("país/ubicación", ""),
                "mensaje": item.get("mensaje/descripción", ""),
                "enlace": item.get("enlace al anuncio", "")
            })

        print(f"  Procesando lote {i // batch_size + 1} de {(len(raw_items) + batch_size - 1) // batch_size}...")
        try:
            results = call_gemini_batch(items_payload, model=args.model, api_key=args.api_key)
            result_map = {r["id"]: r for r in results if "id" in r}
            for item, payload in zip(batch, items_payload):
                res = result_map.get(payload["id"], {
                    "is_student": False,
                    "decision_ia": "Descartado",
                    "justificacion_ia": "No clasificado en la respuesta"
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

    # Save output files
    with open(args.output_approved, "w", encoding="utf-8") as f:
        json.dump(approved, f, ensure_ascii=False, indent=2)

    with open(args.output_discarded, "w", encoding="utf-8") as f:
        json.dump(discarded, f, ensure_ascii=False, indent=2)

    print(f"[OK] Auditoría completa. Aprobados: {len(approved)} | Descartados: {len(discarded)}")
    print(f"  Archivo aprobados: {args.output_approved}")
    print(f"  Archivo descartados: {args.output_discarded}")

def cmd_build(args):
    """Compila dashboard.html y los CSVs con los datos auditados más recientes."""
    print("--> Compilando Dashboard CRM y CSVs...")
    with open(args.approved, "r", encoding="utf-8") as f:
        approved_leads = json.load(f)

    # Asegurar normalización de claves y campos
    approved_leads = [normalize_item(it, idx + 1) for idx, it in enumerate(approved_leads)]

    discarded_leads = []
    if args.discarded and os.path.exists(args.discarded):
        with open(args.discarded, "r", encoding="utf-8") as f:
            discarded_leads = json.load(f)

    # 1. Generate canonical CSV
    canonical_headers = [
        "id", "plataforma", "país/ubicación", "pais", "nombre", "persona_id",
        "materia", "nivel educativo", "modalidad", "modalidad_solicitada",
        "elegible_virtual", "alerta_modalidad", "idioma", "costo_contacto",
        "enlace al anuncio", "es_permalink", "fecha de publicación",
        "mensaje/descripción", "método de contacto directo", "decision_ia", "justificacion_ia"
    ]

    def sanitize_csv(val):
        s = str(val or "")
        if s.startswith(("=", "+", "-", "@")):
            return "'" + s
        return s

    with open(args.output_csv, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=canonical_headers)
        writer.writeheader()
        for r in approved_leads:
            writer.writerow({k: sanitize_csv(r.get(k, "")) for k in canonical_headers})

    # 2. Generate dashboard_crm.csv
    crm_headers = [
        "ID_Prospecto", "Origen", "Nombre_Alumno", "Materia", "Nivel_Educativo",
        "Modalidad", "Costo_Contacto", "Estado_Gestion", "Link_Anuncio",
        "Anuncio_en_Si", "Forma_Contacto", "Fecha_Publicacion", "Criterio_IA"
    ]

    crm_rows = []
    for r in approved_leads:
        url = r.get("enlace al anuncio", "")
        link_formula = f'=HYPERLINK("{url}", "🔗 Abrir Anuncio")' if url.startswith(("http://", "https://")) else url
        mod_desc = r.get("modalidad", "Online")
        if r.get("alerta_modalidad"):
            mod_desc += f" ({r['alerta_modalidad']})"

        crm_rows.append({
            "ID_Prospecto": r.get("id", ""),
            "Origen": f"{r.get('plataforma','')} ({r.get('país/ubicación','')})",
            "Nombre_Alumno": r.get("nombre", "No especificado"),
            "Materia": r.get("materia", ""),
            "Nivel_Educativo": r.get("nivel educativo", ""),
            "Modalidad": mod_desc,
            "Costo_Contacto": r.get("costo_contacto", "Gratuito"),
            "Estado_Gestion": "Pendiente",
            "Link_Anuncio": link_formula,
            "Anuncio_en_Si": sanitize_csv(r.get("mensaje/descripción", "")),
            "Forma_Contacto": sanitize_csv(r.get("método de contacto directo", "")),
            "Fecha_Publicacion": r.get("fecha de publicación", ""),
            "Criterio_IA": sanitize_csv(r.get("justificacion_ia", ""))
        })

    crm_csv_path = args.output_csv.replace("alumnos_ciencias_exactas.csv", "dashboard_crm.csv")
    if crm_csv_path == args.output_csv:
        crm_csv_path = "dashboard_crm.csv"
    with open(crm_csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=crm_headers)
        writer.writeheader()
        writer.writerows(crm_rows)

    # 3. Generate HTML with Observability and Rescue Feature
    app_data = json.dumps(approved_leads, ensure_ascii=False)
    disc_data = json.dumps(discarded_leads, ensure_ascii=False)

    # Import generator logic or write HTML directly
    with open("dashboard.html", "r", encoding="utf-8") as f:
        current_html = f.read()

    # Inject data safely
    pattern = r"var RAW_DATA = .*?;\n"
    replacement = f"var RAW_DATA = {app_data};\n  var DISCARDED_DATA = {disc_data};\n"
    if "var RAW_DATA =" in current_html:
        new_html = re.sub(pattern, replacement, current_html, count=1)
    else:
        new_html = current_html

    with open(args.output_html, "w", encoding="utf-8") as f:
        f.write(new_html)

    print(f"[OK] Archivos generados con éxito: {args.output_html}, {args.output_csv}, {crm_csv_path}")

    # Desktop sync if requested (only if running outside Desktop folder)
    if args.desktop_sync:
        desktop = r"E:\OneDrive\Escritorio\Prospeccion_Alumnos_Ciencias"
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
    # 1. Fetch
    raw_path = "data/raw_extracted_leads.json"
    if not os.path.exists(raw_path):
        raw_path = "data/extracted_listings.json"
    
    # 2. Audit
    args.input = raw_path
    args.output_approved = "data/dataset_canonico_auditado.json"
    args.output_discarded = "data/descartados_auditoria.json"
    cmd_audit(args)

    # 3. Build
    args.approved = args.output_approved
    args.discarded = args.output_discarded
    args.output_html = "dashboard.html"
    args.output_csv = "alumnos_ciencias_exactas.csv"
    cmd_build(args)
    print("=== PIPELINE COMPLETADO EXITOSAMENTE ===")

def main():
    parser = argparse.ArgumentParser(description="CLI Prospector de Alumnos de Ciencias Exactas")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Audit
    p_audit = subparsers.add_parser("audit", help="Audita anuncios con Gemini 3.6/3.8 Flash")
    p_audit.add_argument("--input", required=True, help="Ruta al JSON de anuncios brutos")
    p_audit.add_argument("--model", default="gemini-3.6-flash", help="Modelo de Gemini (default: gemini-3.6-flash)")
    p_audit.add_argument("--batch-size", type=int, default=10, help="Tamaño de lote (default: 10)")
    p_audit.add_argument("--output-approved", required=True, help="Ruta para guardar alumnos aprobados")
    p_audit.add_argument("--output-discarded", required=True, help="Ruta para guardar anuncios descartados")
    p_audit.add_argument("--api-key", default=None, help="Clave de API Gemini (opcional si existe GEMINI_API_KEY)")
    p_audit.set_defaults(func=cmd_audit)

    # Build
    p_build = subparsers.add_parser("build", help="Compila dashboard.html y CSVs")
    p_build.add_argument("--approved", required=True, help="JSON de alumnos aprobados")
    p_build.add_argument("--discarded", default=None, help="JSON de anuncios descartados")
    p_build.add_argument("--output-html", default="dashboard.html", help="Ruta de salida HTML")
    p_build.add_argument("--output-csv", default="alumnos_ciencias_exactas.csv", help="Ruta de salida CSV")
    p_build.add_argument("--desktop-sync", action="store_true", help="Sincronizar automáticamente en el Escritorio")
    p_build.set_defaults(func=cmd_build)

    # Run
    p_run = subparsers.add_parser("run", help="Ejecuta todo el flujo de auditoría y compilación")
    p_run.add_argument("--model", default="gemini-3.6-flash", help="Modelo de Gemini")
    p_run.add_argument("--batch-size", type=int, default=10)
    p_run.add_argument("--api-key", default=None)
    p_run.add_argument("--desktop-sync", action="store_true", default=True)
    p_run.set_defaults(func=cmd_run)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
