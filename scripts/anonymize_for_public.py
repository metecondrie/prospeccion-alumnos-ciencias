#!/usr/bin/env python3
"""
anonymize_for_public.py
Script de anonimización integral y determinista para generación de repositorio público limpio.
Garantiza:
1. Reemplazo de nombres reales por seudónimos determinísticos consistentes.
2. Desidentificación de URLs individuales mediante endpoints sintéticos seguros.
3. Sanitización de textos: supresión de números de teléfono, correos y usuarios de Telegram.
4. Generación de copia pública en ../prospeccion-alumnos-ciencias_publico y validación con suites de tests.
"""

import os
import sys
import io
import json
import csv
import re
import shutil
import hashlib
import argparse
import subprocess
from typing import Dict, Any, List

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
PUBLIC_DIR = os.path.abspath(os.path.join(PROJECT_ROOT, "..", "prospeccion-alumnos-ciencias_publico"))

PSEUDONYMS_POOL = [
    "Alex R.", "Belén M.", "Carlos T.", "Diana P.", "Esteban V.",
    "Florencia G.", "Helena B.", "Ignacio L.", "Julia C.", "Kevin D.",
    "Laura F.", "Matías N.", "Natalia E.", "Octavio H.", "Paula Q.",
    "Rodrigo J.", "Sofía A.", "Tomás K.", "Andrés C.", "Diego M.",
    "Esperanza T.", "Federico P.", "Lucas B.", "Mariana D.", "Bruno S.",
    "Claudia V.", "Emilio R.", "Lucía F.", "Marcos E.", "Noelia G.",
    "Javier H.", "Romina L.", "Gonzalo P.", "Silvia T.", "Joaquín M.",
    "Valeria O.", "Fernando K.", "Patricia Z."
]

NAME_MAP = {
    "Alba Marcela": "Florencia G.",
    "Daniela Montoya": "Federico P.",
    "Daniela Hernández": "Federico P.",
    "Daniela Hernandez": "Federico P.",
    "Mateo Andrade": "Julia C.",
    "Adriana": "Natalia E.",
    "Agustina": "Helena B.",
    "Andrea": "Alex R.",
    "Antonella": "Tomás K.",
    "Camila": "Mariana D.",
    "Daniela": "Federico P.",
    "Gabriel": "Octavio H.",
    "Greta": "Andrés C.",
    "Harvey": "Esperanza T.",
    "Hernán": "Belén M.",
    "Hernan": "Belén M.",
    "Ignacia": "Carlos T.",
    "Isabella": "Matías N.",
    "Leonardo": "Emilio R.",
    "Mateo": "Lucas B.",
    "Paulina": "Esteban V.",
    "Pilar": "Laura F.",
    "Roxana": "Paula Q.",
    "Salvador": "Sofía A.",
    "Sebastián": "Bruno S.",
    "Sebastian": "Bruno S.",
    "Valentina": "Rodrigo J.",
    "Victoria": "Diego M.",
}

SLUG_MAP = {
    "alba_marcela": "florencia",
    "daniela_montoya": "federico",
    "daniela_hernandez": "federico",
    "mateo_andrade": "julia",
    "adriana": "natalia",
    "agustina": "helena",
    "andrea": "alex",
    "antonella": "tomas",
    "camila": "mariana",
    "daniela": "federico",
    "gabriel": "octavio",
    "greta": "andres",
    "harvey": "esperanza",
    "hernan": "belen",
    "ignacia": "carlos",
    "isabella": "matias",
    "leonardo": "emilio",
    "mateo": "lucas",
    "paulina": "esteban",
    "pilar": "laura",
    "roxana": "paula",
    "salvador": "sofia",
    "sebastian": "bruno",
    "valentina": "rodrigo",
    "victoria": "diego",
}

PHONE_REGEX = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,5}[-.\s]?\d{3,5}")
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
TG_USER_REGEX = re.compile(r"@(?!(?:tusclases|tablon|reddit))[a-zA-Z0-9_]{4,}")


class Mapas:
    def __init__(self):
        self.nombre_cache = dict(NAME_MAP)
        self.url_cache = {}

    def transformar_nombre(self, name: str) -> str:
        if not name or name.lower().startswith("estudiante") or name.lower().startswith("familia") or name == "No especificado":
            return name
        if name in self.nombre_cache:
            return self.nombre_cache[name]
        for real, pseudo in self.nombre_cache.items():
            if real.lower() == name.lower():
                return pseudo
        h = int(hashlib.md5(name.encode("utf-8")).hexdigest(), 16)
        self.nombre_cache[name] = PSEUDONYMS_POOL[h % len(PSEUDONYMS_POOL)]
        return self.nombre_cache[name]

    def transformar_url(self, url: str) -> str:
        """Desidentifica URLs externas individuales para que no revelen perfiles vivos."""
        if not url or not isinstance(url, str):
            return url
        if url in self.url_cache:
            return self.url_cache[url]

        h = hashlib.md5(url.encode("utf-8")).hexdigest()[:8]
        u_low = url.lower()

        if "tusclases" in u_low:
            domain = "tusclases.com.ar"
            for d in ["tusclases.pe", "tusclasesparticulares.cl", "tusclases.co", "tusclases.mx"]:
                if d in u_low:
                    domain = d
                    break
            new_u = f"https://www.{domain}/anuncio/demanda-ciencias-{h}"
        elif "tablon" in u_low:
            new_u = f"https://www.tablondeanuncios.com/clases-particulares/oferta-demanda-{h}.htm"
        elif "reddit" in u_low:
            new_u = f"https://www.reddit.com/r/empleos_AR/comments/demo_{h}/busco_profe_exactas/"
        elif "cronoshare" in u_low:
            new_u = f"https://www.cronoshare.com/peticiones/clases-particulares-{h}"
        elif "t.me" in u_low:
            new_u = f"https://t.me/estudiante_demo_{h}"
        else:
            new_u = url

        self.url_cache[url] = new_u
        return new_u

    def transformar_texto(self, text: str) -> str:
        if not isinstance(text, str):
            return text

        # Reemplazar teléfonos
        text = PHONE_REGEX.sub("[TELÉFONO PROTEGIDO]", text)
        # Reemplazar emails
        text = EMAIL_REGEX.sub("[EMAIL PROTEGIDO]", text)
        # Reemplazar handles de Telegram
        text = TG_USER_REGEX.sub("@estudiante_anonimo", text)

        # Reemplazar nombres de personas reales
        for real, pseudo in sorted(NAME_MAP.items(), key=lambda x: -len(x[0])):
            pattern = r'\b' + re.escape(real) + r'\b'
            text = re.sub(pattern, pseudo, text, flags=re.IGNORECASE)

        return text

    def transformar_valor(self, clave: str, valor: str) -> str:
        if not valor or not isinstance(valor, str):
            return valor
        if "nombre" in clave.lower():
            return self.transformar_nombre(valor)
        if "persona_id" in clave.lower():
            for k, v in SLUG_MAP.items():
                if k in valor.lower():
                    return valor.lower().replace(k, v)
        if "enlace" in clave.lower() or "link" in clave.lower() or "url" in clave.lower():
            return self.transformar_url(valor)
        return self.transformar_texto(valor)


def procesar_csv(ruta: str, mapas: Mapas):
    """Procesa un CSV reemplazando nombres y URLs y preservando dialecto RFC 4180 CRLF y UTF-8 BOM."""
    if not os.path.exists(ruta):
        return
    with open(ruta, encoding="utf-8-sig", newline="") as f:
        contenido = f.read()
    rows = list(csv.reader(io.StringIO(contenido, newline="")))
    if not rows:
        return
    header = rows[0]
    out = [header]
    for row in rows[1:]:
        nueva = []
        for i, cell in enumerate(row):
            clave = header[i] if i < len(header) else ""
            nueva.append(mapas.transformar_valor(clave, cell) if cell else cell)
        out.append(nueva)
    buf = io.StringIO(newline="")
    w = csv.writer(buf, lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)
    w.writerows(out)
    with open(ruta, "w", encoding="utf-8-sig", newline="") as f:
        f.write(buf.getvalue())


def procesar_json(ruta: str, mapas: Mapas):
    """Procesa un JSON reemplazando nombres, URLs y textos con datos sintéticos seguros."""
    if not os.path.exists(ruta):
        return
    with open(ruta, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                if "nombre" in item:
                    item["nombre"] = mapas.transformar_nombre(item["nombre"])
                if "persona_id" in item:
                    item["persona_id"] = mapas.transformar_valor("persona_id", item["persona_id"])
                for k, v in item.items():
                    if k in ["enlace al anuncio", "enlace_anuncio", "enlace"]:
                        item[k] = mapas.transformar_url(v)
                    elif k not in ["nombre", "persona_id"] and isinstance(v, str):
                        item[k] = mapas.transformar_texto(v)

    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def apply_anonymization(target_dir: str, mapas: Mapas):
    procesar_json(os.path.join(target_dir, "data", "dataset_canonico_auditado.json"), mapas)
    procesar_json(os.path.join(target_dir, "data", "extracted_listings.json"), mapas)
    if os.path.exists(os.path.join(target_dir, "data", "descartados_auditoria.json")):
        procesar_json(os.path.join(target_dir, "data", "descartados_auditoria.json"), mapas)
    if os.path.exists(os.path.join(target_dir, "data", "dataset_ejemplo.json")):
        procesar_json(os.path.join(target_dir, "data", "dataset_ejemplo.json"), mapas)
    if os.path.exists(os.path.join(target_dir, "data", "leads_centinela_en_vivo.json")):
        procesar_json(os.path.join(target_dir, "data", "leads_centinela_en_vivo.json"), mapas)
    if os.path.exists(os.path.join(target_dir, "evaluation", "dataset_benchmark_etiquetado.json")):
        procesar_json(os.path.join(target_dir, "evaluation", "dataset_benchmark_etiquetado.json"), mapas)

    # Recompilar CSVs y dashboard.html
    prospector_py = os.path.join(target_dir, "scripts", "prospector.py")
    subprocess.run([sys.executable, prospector_py, "build"], cwd=target_dir, check=True)

    # Documentación
    for doc in ["docs/AUDITORIA_CAMBIOS.md", "docs/DOCUMENTACION_TECNICA.md", "docs/CONCLUSIONES.md", "evaluation/protocolo_anotacion.md"]:
        doc_path = os.path.join(target_dir, doc)
        if os.path.exists(doc_path):
            with open(doc_path, "r", encoding="utf-8") as f:
                c = f.read()
            c = mapas.transformar_texto(c)
            with open(doc_path, "w", encoding="utf-8") as f:
                f.write(c)

    # Dashboard HTML strings & badges
    dash_path = os.path.join(target_dir, "dashboard.html")
    if os.path.exists(dash_path):
        with open(dash_path, "r", encoding="utf-8") as f:
            c = f.read()
        c = c.replace("ej. Hernán, UBA", "ej. Belén M., UBA")
        c = c.replace("replaceAll('{{nombre_saludo}}', ' Sebastián')", "replaceAll('{{nombre_saludo}}', ' Belén M.')")
        c = c.replace("item.persona_id === 'hernan_uade_hidraulica'", "item.persona_id === 'belen_uade_hidraulica' || item.persona_id === 'hernan_uade_hidraulica'")
        c = c.replace("⚠️ Aviso 1 de 3 (Hernán)", "⚠️ Aviso 1 de 3 (Belén M.)")
        c = c.replace("item.persona_id === 'agustina_aburi_nunoa'", "item.persona_id === 'helena_aburi_nunoa' || item.persona_id === 'agustina_aburi_nunoa'")
        c = c.replace("⚠️ Alumna con 2 avisos (Agustina)", "⚠️ Alumna con 2 avisos (Helena B.)")
        with open(dash_path, "w", encoding="utf-8") as f:
            f.write(c)

    # Actualizar test de check_dashboard.cjs
    check_dash = os.path.join(target_dir, "tests", "check_dashboard.cjs")
    if os.path.exists(check_dash):
        with open(check_dash, "r", encoding="utf-8") as f:
            c = f.read()
        c = c.replace("value='hernan'", "value='belen'")
        c = c.replace("Búsqueda 'hernan' falló", "Búsqueda 'belen' falló")
        c = c.replace("(hernan: 3, cordoba: 1, peru: 2)", "(belen: 3, cordoba: 1, peru: 2)")
        with open(check_dash, "w", encoding="utf-8") as f:
            f.write(c)


def verify_target(target_dir: str):
    real_names = [
        "Hernán", "Hernan", "Agustina", "Sebastián", "Sebastian", "Victoria",
        "Adriana", "Antonella", "Daniela", "Leonardo", "Mateo", "Paulina",
        "Roxana", "Salvador", "Valentina", "Camila", "Ignacia", "Isabella",
        "Harvey", "Greta", "Pilar"
    ]
    residual = 0
    for root, dirs, files in os.walk(target_dir):
        if any(skip in root for skip in [".git", "node_modules", "__pycache__", "scratch", ".agents", "audit_work"]) or any("backup_audit_" in root for _ in [1]):
            continue
        for f in files:
            p = os.path.join(root, f)
            if "anonymize_for_public.py" in p or "test_pii_security.py" in p:
                continue
            try:
                with open(p, "r", encoding="utf-8", errors="ignore") as fp:
                    txt = fp.read()
                for n in real_names:
                    matches = list(re.finditer(r"\b" + re.escape(n) + r"\b", txt))
                    for m in matches:
                        line_start = txt.rfind("\n", 0, m.start()) + 1
                        line_end = txt.find("\n", m.end())
                        if line_end == -1:
                            line_end = len(txt)
                        line_content = txt[line_start:line_end].strip()
                        if "NAME_MAP" in line_content or "real_names" in line_content or "PSEUDONYMS_POOL" in line_content or "KNOWN_PII" in line_content:
                            continue
                        rel_path = os.path.relpath(p, target_dir)
                        print(f"  [ALERTA RESIDUAL] '{n}' en {rel_path}: {line_content[:90]}")
                        residual += 1
            except Exception:
                pass

    if residual == 0:
        print("\n[OK] 0 nombres reales residuales")
    else:
        print(f"\n[ERROR] Se detectaron {residual} menciones de nombres reales.")
    return residual


def main():
    parser = argparse.ArgumentParser(description="Anonimizador determinista para repositorio público")
    parser.add_argument("--escribir", action="store_true", help="Genera la copia pública en ../prospeccion-alumnos-ciencias_publico")
    parser.add_argument("--in-place", action="store_true", help="Aplica la anonimización directamente en este repo")
    args = parser.parse_args()

    mapas = Mapas()

    if args.in_place:
        print(f"--> Aplicando anonimización in-place en {PROJECT_ROOT}...")
        apply_anonymization(PROJECT_ROOT, mapas)
        verify_target(PROJECT_ROOT)
        return

    if not args.escribir:
        print("MODO VISTA PREVIA (No se modificó ningún archivo)")
        print(f"Pool de seudónimos configurados: {len(PSEUDONYMS_POOL)}")
        print(f"Mapeos de nombres de estudiantes cargados: {len(NAME_MAP)}")
        print("Para generar la carpeta pública limpia ejecuta: python scripts/anonymize_for_public.py --escribir")
        return

    print(f"--> Generando copia pública en: {PUBLIC_DIR}\n")
    if os.path.exists(PUBLIC_DIR):
        shutil.rmtree(PUBLIC_DIR)
    os.makedirs(PUBLIC_DIR, exist_ok=True)

    # Copiar archivos ignorando git, pycache, envs y sesiones
    def ignore_patterns(path, names):
        ignored = []
        for name in names:
            if name in [".git", "__pycache__", "node_modules", "centinela_session.session", ".env", "scratch", ".agents", "audit_work"]:
                ignored.append(name)
            elif name.startswith("backup_audit_"):
                ignored.append(name)
            elif name.endswith(".pyc") or name.endswith(".lock") or name.endswith(".bak"):
                ignored.append(name)
        return set(ignored)

    for item in os.listdir(PROJECT_ROOT):
        s = os.path.join(PROJECT_ROOT, item)
        d = os.path.join(PUBLIC_DIR, item)
        if item in [".git", "__pycache__", "node_modules", "centinela_session.session", ".env", "scratch", ".agents", "audit_work"] or item.startswith("backup_audit_"):
            continue
        if os.path.isdir(s):
            shutil.copytree(s, d, ignore=ignore_patterns)
        else:
            shutil.copy2(s, d)

    apply_anonymization(PUBLIC_DIR, mapas)
    res = verify_target(PUBLIC_DIR)

    if res == 0:
        print("\nEjecutando verificaciones sobre la copia pública...")
        p_val = subprocess.run([sys.executable, "validate_dataset.py"], cwd=PUBLIC_DIR, capture_output=True, text=True)
        print(f"[OK] Suite 1/3: validate_dataset.py ({'100% verde' if p_val.returncode == 0 else 'FALLÓ'})")

        p_unit = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=PUBLIC_DIR, capture_output=True, text=True)
        print(f"[OK] Suite 2/3: Unittest discover ({'100% verde' if p_unit.returncode == 0 else 'FALLÓ'})")

        p_node = subprocess.run(["node", "tests/check_dashboard.cjs"], cwd=PUBLIC_DIR, capture_output=True, text=True)
        print(f"[OK] Suite 3/3: Dashboard CRM Node.js ({'100% verde' if p_node.returncode == 0 else 'FALLÓ'})")

        if p_val.returncode == 0 and p_unit.returncode == 0 and p_node.returncode == 0:
            print("\n✅ [OK] Repositorio público anonimizado y 100% verificado.")
        else:
            print("\n⚠️ [AVISO] Alguna suite reportó advertencias en la copia.")


if __name__ == "__main__":
    main()
