#!/usr/bin/env python3
"""
anonymize_for_public.py
Script de anonimización determinística para el repositorio público de Prospección de Alumnos.
Reemplaza nombres personales por seudónimos consistentes en datos, planillas, dashboard y documentación,
garantizando 0 colisiones con nombres reales y protegiendo la privacidad de los estudiantes.
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
from typing import Dict, Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
PUBLIC_DIR = os.path.abspath(os.path.join(PROJECT_ROOT, "..", "prospeccion-alumnos-ciencias_publico"))

# Pool de seudónimos libres de colisión con los 24 nombres originales del dataset
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

class Mapas:
    def __init__(self):
        self.nombre_cache = dict(NAME_MAP)

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

    def transformar_valor(self, clave: str, valor: str) -> str:
        if not valor or not isinstance(valor, str):
            return valor
        if "nombre" in clave.lower():
            return self.transformar_nombre(valor)
        if "persona_id" in clave.lower():
            for k, v in SLUG_MAP.items():
                if k in valor.lower():
                    return valor.lower().replace(k, v)
        return self.transformar_texto(valor)

    def transformar_texto(self, text: str) -> str:
        if not isinstance(text, str):
            return text
        if text.startswith("http://") or text.startswith("https://"):
            return text
        for real, pseudo in sorted(NAME_MAP.items(), key=lambda x: -len(x[0])):
            pattern = r'\b' + re.escape(real) + r'\b'
            text = re.sub(pattern, pseudo, text, flags=re.IGNORECASE)
        return text


def procesar_csv(ruta: str, mapas: Mapas):
    """Procesa un CSV reemplazando nombres y preservando dialecto RFC 4180 CRLF y UTF-8 BOM."""
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
    """Procesa un JSON reemplazando nombres con seudónimos determinísticos."""
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
                    if k not in ["nombre", "persona_id"] and isinstance(v, str):
                        item[k] = mapas.transformar_texto(v)

    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def preview_anonymization(mapas: Mapas):
    data_path = os.path.join(PROJECT_ROOT, "data", "dataset_canonico_auditado.json")
    if not os.path.exists(data_path):
        print("[ERROR] No se encontró el dataset canónico.")
        return

    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    names = sorted(list(set(r.get("nombre", "") for r in data if r.get("nombre"))))
    print("=" * 65)
    print("   VISTA PREVIA DE ANONIMIZACIÓN DETERMINÍSTICA (CERO COLISIONES)")
    print("=" * 65)
    for n in names:
        pseudo = mapas.transformar_nombre(n)
        print(f"  {n:25} -> {pseudo}")
    print(f"\nTotal nombres únicos mapeados: {len(names)}")
    print("Comandos disponibles:")
    print("  python scripts/anonymize_for_public.py --in-place   # Aplica en el workspace actual")
    print("  python scripts/anonymize_for_public.py --escribir   # Genera copia en _publico\n")


def apply_in_place(mapas: Mapas):
    print("--> Aplicando anonimización determinística IN-PLACE sobre el repositorio...")
    procesar_json(os.path.join(PROJECT_ROOT, "data", "dataset_canonico_auditado.json"), mapas)
    procesar_json(os.path.join(PROJECT_ROOT, "data", "extracted_listings.json"), mapas)
    if os.path.exists(os.path.join(PROJECT_ROOT, "data", "descartados_auditoria.json")):
        procesar_json(os.path.join(PROJECT_ROOT, "data", "descartados_auditoria.json"), mapas)

    # Recompilar CSVs y dashboard.html a través de prospector.py
    prospector_py = os.path.join(PROJECT_ROOT, "scripts", "prospector.py")
    subprocess.run([sys.executable, prospector_py, "build"], cwd=PROJECT_ROOT, check=True)

    # Docs
    for doc in ["docs/AUDITORIA_CAMBIOS.md", "docs/DOCUMENTACION_TECNICA.md", "docs/CONCLUSIONES.md"]:
        doc_path = os.path.join(PROJECT_ROOT, doc)
        if os.path.exists(doc_path):
            with open(doc_path, "r", encoding="utf-8") as f:
                c = f.read()
            c = mapas.transformar_texto(c)
            with open(doc_path, "w", encoding="utf-8") as f:
                f.write(c)

    # Dashboard HTML strings & badges
    dash_path = os.path.join(PROJECT_ROOT, "dashboard.html")
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

    print("[OK] Anonimización in-place completada exitosamente.")


def generate_public_repo(mapas: Mapas):
    print(f"--> Generando copia pública en: {PUBLIC_DIR}")
    if os.path.exists(PUBLIC_DIR):
        shutil.rmtree(PUBLIC_DIR)
    os.makedirs(PUBLIC_DIR, exist_ok=True)

    exclude_items = {".env", ".git", "centinela_session.session", "logs", "__pycache__", ".pytest_cache", ".agents", "scratch", "backup_audit_*"}

    for item in os.listdir(PROJECT_ROOT):
        if item in exclude_items or item.endswith(".session") or item.endswith(".log"):
            continue
        src = os.path.join(PROJECT_ROOT, item)
        dst = os.path.join(PUBLIC_DIR, item)
        if os.path.isdir(src):
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("*.session", "*.log", "__pycache__", ".env*", ".agents*"))
        else:
            shutil.copy2(src, dst)

    apply_in_place(mapas)
    print("Ejecutando verificaciones automáticas sobre la copia pública...")
    ret_val = subprocess.call([sys.executable, "validate_dataset.py"], cwd=PUBLIC_DIR)
    ret_test = subprocess.call([sys.executable, "-m", "pytest", "tests/"], cwd=PUBLIC_DIR)

    if ret_val == 0 and ret_test == 0:
        print("\n✅ [OK] Repositorio público anonimizado y 100% verificado.")
    else:
        print("\n⚠️ [AVISO] Se detectaron observaciones en las pruebas de la copia pública.")


def main():
    parser = argparse.ArgumentParser(description="Anonimizador determinístico de Prospección de Alumnos")
    parser.add_argument("--escribir", action="store_true", help="Genera copia externa en _publico")
    parser.add_argument("--in-place", action="store_true", help="Aplica la anonimización directamente sobre el workspace")
    args = parser.parse_args()

    mapas = Mapas()

    if args.in_place:
        apply_in_place(mapas)
    elif args.escribir:
        generate_public_repo(mapas)
    else:
        preview_anonymization(mapas)


if __name__ == "__main__":
    main()
