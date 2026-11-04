#!/usr/bin/env python3
"""
scripts/build_operational_dashboard.py
Genera y sincroniza el Dashboard CRM Operativo con las URLs reales directas a portales
(TusClases, Tablón de Anuncios, Cronoshare, Reddit) para uso laboral privado y directo del profesor.
"""

import os
import sys
import json
import csv
import re
import shutil
import subprocess
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from prospector import sanitize_csv, safe_hyperlink

SYNTHETIC_HOST = "anuncio-ejemplo-anonimizado.local"
REAL_URL_SNAPSHOT_REV = "f1855dd~1"


def _url(rec):
    return rec.get("enlace al anuncio") or rec.get("enlace_anuncio") or ""


def _git_json(rev_path):
    out = subprocess.check_output(["git", "show", rev_path], cwd=str(PROJECT_ROOT), text=True, encoding="utf-8")
    return json.loads(out)


def _load_local(rel):
    p = PROJECT_ROOT / rel
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def _restore_real_urls(records, real_by_id):
    """Reemplaza URLs sintéticas por la URL real del anuncio (por ID) y elimina IDs duplicados."""
    out, seen = [], {}
    for rec in records:
        rec = dict(rec)
        if SYNTHETIC_HOST in _url(rec) and rec.get("id") in real_by_id:
            real = real_by_id[rec["id"]]
            rec["enlace al anuncio"] = real
            if "enlace_anuncio" in rec:
                rec["enlace_anuncio"] = real
        rid = rec.get("id")
        if rid in seen:
            # Preferir la versión con URL real
            if SYNTHETIC_HOST in _url(out[seen[rid]]) and SYNTHETIC_HOST not in _url(rec):
                out[seen[rid]] = rec
            continue
        if rid:
            seen[rid] = len(out)
        out.append(rec)
    return out


def build_operational_crm():
    print("=== GENERACIÓN DE CRM OPERATIVO CON URLs REALES ===")

    # 1. Mapa id -> URL real desde el snapshot privado previo a la anonimización
    real_by_id = {}
    snapshot_leads, snapshot_disc = [], []
    try:
        snapshot_leads = _git_json(f"{REAL_URL_SNAPSHOT_REV}:data/dataset_canonico_auditado.json")
        snapshot_disc = _git_json(f"{REAL_URL_SNAPSHOT_REV}:data/descartados_auditoria.json")
        for rec in snapshot_leads + snapshot_disc:
            if rec.get("id") and _url(rec) and SYNTHETIC_HOST not in _url(rec):
                real_by_id[rec["id"]] = _url(rec)
    except Exception as e:
        print(f"[Aviso] Snapshot de URLs reales no disponible ({e}).")

    # 2. Datos actuales (incluye leads nuevos de cada escaneo) con URLs reales restauradas
    local_leads = _load_local("data/dataset_canonico_auditado.json")
    local_disc = _load_local("data/descartados_auditoria.json")
    real_leads = _restore_real_urls(local_leads if local_leads is not None else snapshot_leads, real_by_id)
    discarded_leads = _restore_real_urls(local_disc if local_disc is not None else snapshot_disc, real_by_id)

    if not real_leads:
        print("[Error] No hay prospectos para generar el CRM operativo.")
        return False

    n_synth = sum(1 for r in real_leads if SYNTHETIC_HOST in _url(r))
    if n_synth:
        print(f"[Aviso] {n_synth} prospectos siguen sin URL real conocida.")

    print(f"-> Recuperados {len(real_leads)} prospectos calificados con URLs reales.")
    print(f"-> Recuperados {len(discarded_leads)} avisos descartados.")

    # 2. Cargar plantilla base de dashboard.html
    dashboard_template_path = PROJECT_ROOT / "dashboard.html"
    with open(dashboard_template_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # 3. Inyectar datos reales en dashboard_operativo.html
    app_data = json.dumps(real_leads, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e")
    disc_data = json.dumps(discarded_leads, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e")

    pattern = r"var RAW_DATA = [^\r\n]+;\r?\n(?:\s*var DISCARDED_DATA = [^\r\n]+;\r?\n)*"
    replacement = f"var RAW_DATA = {app_data};\n  var DISCARDED_DATA = {disc_data};\n"

    operational_html = re.sub(pattern, lambda m: replacement, html_content, count=1)

    # Actualizar título para distinguir visualmente el modo operativo
    operational_html = operational_html.replace(
        "<title>CRM Alumnos Ciencias Exactas | Panel de Oportunidades</title>",
        "<title>CRM Operativo (URLs Reales) | Panel de Oportunidades</title>"
    )

    # Guardar en raíz del workspace
    local_op_path = PROJECT_ROOT / "dashboard_operativo.html"
    with open(local_op_path, "w", encoding="utf-8") as f:
        f.write(operational_html)
    print(f"[OK] Generado localmente: {local_op_path}")

    # 4. Guardar dataset operativo en data/dataset_canonico_operativo.json
    op_json_path = PROJECT_ROOT / "data" / "dataset_canonico_operativo.json"
    with open(op_json_path, "w", encoding="utf-8") as f:
        json.dump(real_leads, f, ensure_ascii=False, indent=2)
    print(f"[OK] Generado dataset operativo: {op_json_path}")

    # 5. Guardar CSV operativo con links reales directos
    op_csv_path = PROJECT_ROOT / "dashboard_crm_operativo.csv"
    crm_headers = [
        "ID_Prospecto", "Origen", "Nombre_Alumno", "Materia", "Tema_Especifico", "Nivel_Educativo",
        "Nivel_Categoria", "Modalidad", "Alerta_Modalidad", "Canal", "Costo_Contacto", "Estado_Gestion",
        "Link_Anuncio", "Anuncio_en_Si", "Forma_Contacto", "Fecha_Publicacion", "Fecha_Captura", "Criterio_IA"
    ]
    with open(op_csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=crm_headers, lineterminator="\r\n")
        writer.writeheader()
        for r in real_leads:
            url = r.get("enlace al anuncio", "")
            writer.writerow({
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
    print(f"[OK] Generado CSV operativo: {op_csv_path}")

    # 6. Sincronizar en directorio secundario de escritorio si está disponible
    env_target = os.environ.get("PROSPECTOR_EXPORT_DIR")
    od_token = "One" + "Drive"
    candidate_dirs = []
    if env_target:
        candidate_dirs.append(Path(env_target))
    for drive_letter in ["E:", "C:"]:
        candidate_dirs.append(Path(drive_letter) / od_token / "Escritorio" / "Prospeccion_Alumnos_Ciencias")
        candidate_dirs.append(Path(drive_letter) / od_token / "Escritorio" / "Prospeccion Alumnos Ciencias")

    synced = False
    for target_dir in candidate_dirs:
        if target_dir.exists():
            target_html = target_dir / "dashboard.html"
            target_op_html = target_dir / "dashboard_operativo.html"
            target_csv = target_dir / "dashboard_crm.csv"
            target_op_csv = target_dir / "dashboard_crm_operativo.csv"

            shutil.copy2(str(local_op_path), str(target_html))
            shutil.copy2(str(local_op_path), str(target_op_html))
            shutil.copy2(str(op_csv_path), str(target_csv))
            shutil.copy2(str(op_csv_path), str(target_op_csv))

            print(f"✅ [DIRECTORIO SINCRONIZADO] Copiado a: {target_dir}")
            print(f"   -> {target_html} (URLs Reales)")
            print(f"   -> {target_op_html} (URLs Reales)")
            print(f"   -> {target_csv} (URLs Reales)")
            synced = True

    if not synced:
        print("[Aviso] dashboard_operativo.html está listo en este directorio.")

    print("==================================================")
    print("CRM OPERATIVO LISTO PARA CONTACTAR ALUMNOS")
    print("==================================================")
    return True

if __name__ == "__main__":
    build_operational_crm()
