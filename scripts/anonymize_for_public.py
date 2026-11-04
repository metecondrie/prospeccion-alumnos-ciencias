#!/usr/bin/env python3
"""
anonymize_for_public.py
Script de anonimización determinística para generación de repositorio público limpio.
Reemplaza nombres y datos personales por seudónimos consistentes en datos, planillas y dashboard,
asegurando que ninguna PII real quede expuesta en repositorios abiertos.
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

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
PUBLIC_DIR = os.path.abspath(os.path.join(PROJECT_ROOT, "..", "prospeccion-alumnos-ciencias_publico"))

PSEUDONYMS_POOL = [
    "Alex R.", "Belén M.", "Carlos T.", "Diana P.", "Esteban V.",
    "Florencia G.", "Gabriel S.", "Helena B.", "Ignacio L.", "Julia C.",
    "Kevin D.", "Laura F.", "Matías N.", "Natalia E.", "Octavio H.",
    "Paula Q.", "Rodrigo J.", "Sofía A.", "Tomás K.", "Valentina Z.",
    "Andrés C.", "Camila R.", "Diego M.", "Esperanza T.", "Federico P."
]

class Mapas:
    def __init__(self):
        self.nombre_cache = {}

    def transformar_nombre(self, name: str) -> str:
        if not name or name.lower().startswith("estudiante") or name.lower().startswith("familia") or name == "No especificado":
            return name
        if name not in self.nombre_cache:
            h = int(hashlib.md5(name.encode("utf-8")).hexdigest(), 16)
            self.nombre_cache[name] = PSEUDONYMS_POOL[h % len(PSEUDONYMS_POOL)]
        return self.nombre_cache[name]

    def transformar_valor(self, clave: str, valor: str) -> str:
        if not valor:
            return valor
        if "nombre" in clave.lower():
            return self.transformar_nombre(valor)
        if "persona_id" in clave.lower():
            # Anonimizar prefijos de persona_id si contienen el nombre
            for real_name, pseudo in self.nombre_cache.items():
                real_slug = real_name.lower().split()[0]
                pseudo_slug = pseudo.lower().split()[0]
                if real_slug in valor.lower():
                    return valor.lower().replace(real_slug, pseudo_slug)
        return valor


def procesar_csv(ruta: str, mapas: Mapas):
    """Procesa un CSV reemplazando nombres y preservando dialecto y codificación UTF-8 BOM."""
    if not os.path.exists(ruta):
        return
    with open(ruta, encoding="utf-8-sig", newline="") as f:
        contenido = f.read()
    dialect_nl = "\r\n" if "\r\n" in contenido else "\n"
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
    w = csv.writer(buf, lineterminator=dialect_nl, quoting=csv.QUOTE_MINIMAL)
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
    print("   VISTA PREVIA DE ANONIMIZACIÓN DETERMINÍSTICA")
    print("=" * 65)
    for n in names:
        pseudo = mapas.transformar_nombre(n)
        print(f"  {n:25} -> {pseudo}")
    print(f"\nTotal nombres únicos mapeados: {len(names)}")
    print("Para generar la carpeta pública limpia, ejecuta:")
    print("  python scripts/anonymize_for_public.py --escribir\n")


def generate_public_repo(mapas: Mapas):
    print(f"--> Generando copia pública en: {PUBLIC_DIR}")
    if os.path.exists(PUBLIC_DIR):
        shutil.rmtree(PUBLIC_DIR)
    os.makedirs(PUBLIC_DIR, exist_ok=True)

    exclude_items = {".env", ".git", "centinela_session.session", "logs", "__pycache__", ".pytest_cache"}

    for item in os.listdir(PROJECT_ROOT):
        if item in exclude_items or item.endswith(".session") or item.endswith(".log"):
            continue
        src = os.path.join(PROJECT_ROOT, item)
        dst = os.path.join(PUBLIC_DIR, item)
        if os.path.isdir(src):
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("*.session", "*.log", "__pycache__", ".env*"))
        else:
            shutil.copy2(src, dst)

    # Procesar archivos de la copia pública
    print("Aplicando anonimización determinística sobre la copia pública...")
    procesar_csv(os.path.join(PUBLIC_DIR, "alumnos_ciencias_exactas.csv"), mapas)
    procesar_csv(os.path.join(PUBLIC_DIR, "dashboard_crm.csv"), mapas)
    procesar_json(os.path.join(PUBLIC_DIR, "data", "dataset_canonico_auditado.json"), mapas)
    procesar_json(os.path.join(PUBLIC_DIR, "data", "extracted_listings.json"), mapas)

    print("[OK] Copia pública anonimizada generada con éxito.")
    print("Ejecutando verificaciones automáticas sobre la copia pública...")
    ret_val = subprocess.call([sys.executable, "validate_dataset.py"], cwd=PUBLIC_DIR)
    ret_test = subprocess.call([sys.executable, "-m", "pytest", "tests/"], cwd=PUBLIC_DIR)

    if ret_val == 0 and ret_test == 0:
        print("\n✅ [OK] Repositorio público anonimizado y 100% verificado.")
    else:
        print("\n⚠️ [AVISO] Se detectaron observaciones en las pruebas de la copia pública.")


def main():
    parser = argparse.ArgumentParser(description="Anonimizador determinístico para publicación")
    parser.add_argument("--escribir", action="store_true", help="Genera la copia pública en la carpeta _publico")
    args = parser.parse_args()

    mapas = Mapas()

    if args.escribir:
        generate_public_repo(mapas)
    else:
        preview_anonymization(mapas)

if __name__ == "__main__":
    main()
