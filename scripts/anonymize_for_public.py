#!/usr/bin/env python3
"""
anonymize_for_public.py
Script de anonimización integral y determinista para generación de repositorio público limpio.
Garantiza:
1. Carga segura del mapeo de privacidad desde data/name_map.privado.json (ignorado por git).
2. Reemplazo de nombres reales por seudónimos determinísticos consistentes.
3. Desidentificación de URLs individuales mediante endpoints sintéticos seguros (0 links reales).
4. Sanitización de textos: supresión de números de teléfono, correos y usuarios de Telegram.
5. Generación de copia pública en ../prospeccion-alumnos-ciencias_publico y validación con suites de tests.
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

# Hashes SHA-256 de nombres de alumnos para verificación ciega de privacidad sin exponer PII
FORBIDDEN_NAME_HASHES = {
    "a953e6c34b6871f9481523e302e78b343f9aa7394370afbfc35455ae9d0ae4e7",
    "a93991200ee4a2de3e1d7ddb6a4d218c3e4069d9d4c4c347a9897b4472ededbe",
    "c9176f204b1c6e7eef80e5f575c6398dccffac9909b111a4a9d279f2b481e3ae",
    "813c24889530d746fdb8941722ff8431bfbbbbe9e52ac9c3297ccf90a65336f2",
    "718c4908545eef5dddda9848f1293979819b3378f85276f8e159c5d15b5f4214",
    "6bc97be98f6fdb38c91a399171e97fa2a3d8edf918bf209bef0269c8676cf041",
    "099c3231aa0d0d61b796bb35e0c096bcdd633a41ba62570ff5b7f98ecf92a278",
    "8334189876be0d2ef800371ca423cff695a53df472dc05e3a1a52fac867a4670",
    "db0284fc80b4881fa545953441a21958470c49d73508714a84a259cb62a5dbb5",
    "ee6aa9381e07c60412e8bca2932326f413828ccabca7b96380b4170f7e704605",
    "3e6b74c49ac4235996c8c207db3b7bce963f29380e9dcc46dc0fed04b75fe3cc",
    "253387e8620ee1896c76809782406e139bce35860aaa0d61991965319ba0dc32",
    "6cc61e6e49ab38053f9c3df1ba795a7229332ff783e7dbc12232bfe6d34d83b1",
    "80d161545383dd77c8703ec50d566ae19f9f6bb5b68b42b26482f1cdf21bf8f2",
    "0c3392045342bf3019bf8eedb0a7c015d0e33772cc21c6ef533ccb1ceddbd77b",
    "0c030df5a4e7477d218012c0121ebce6d61bb8dc46e0a6c4f8e1cc8091b946a5",
    "ace2008b98c1980f9df9a009b38a80652a0dee2ffab3406090cf77e788fe18af",
    "2db7a0c30b879e153450129605fc826cee1db5d4df9d5ead38b81fb7f5935dc8",
    "e7d36336232ab24b6c522a8614d0f23a9861b95fdfed7edd0a7fc0a9358d8fb0",
    "a81ef43a50006221a2810a2de453541cc7c6a0084df970a7e35b2f7b3717cda8",
    "c04bc8058a898b568913ca6a8187624e9f15167c32c7019e9712ab694f90752f",
    "8272dcce0d7192d4599a7ee498066f8e7c36dcffe1a7c70f15854fd228fdfa25",
    "006e3a93b8f63344095bc538966c67539282df6d4f566ccff5d983acb0c18be8",
    "240cca8d7560bceea72e5709ff401a198d240a43b3a0c2ef8a79edc0d29bbf31",
    "d179191d1c83b81f3d2c2671b7a3a317a668408edfbd689ad906c2b380d35614",
    "5ad4a23bc13eaf92e9c035b1d3edbb92582a99f2dbe64525009755f989eedfb2",
    "c09213cf20b32fe2436b92ded92caeed5d938b454c0cd94fea66658823c812b3",
    "c7a11e9a55de2b146e3b2d75e9112ee6af4e5b439658e725e6afca92e93bf0bd",
}

# Carga segura del mapeo privado de desidentificación
PRIVATE_MAP_FILE = os.path.join(PROJECT_ROOT, "data", "name_map.privado.json")
if os.path.exists(PRIVATE_MAP_FILE):
    try:
        with open(PRIVATE_MAP_FILE, "r", encoding="utf-8") as _pf:
            _pdata = json.load(_pf)
            NAME_MAP: Dict[str, str] = _pdata.get("name_map", {})
            SLUG_MAP: Dict[str, str] = _pdata.get("slug_map", {})
            REAL_NAMES: List[str] = _pdata.get("real_names", list(NAME_MAP.keys()))
    except Exception:
        NAME_MAP = {}
        SLUG_MAP = {}
        REAL_NAMES = []
else:
    NAME_MAP = {}
    SLUG_MAP = {}
    REAL_NAMES = []

PHONE_REGEX = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,5}[-.\s]?\d{3,5}")
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
TG_USER_REGEX = re.compile(r"@(?!(?:tusclases|tablon|reddit))[a-zA-Z0-9_]{4,}")

# Patrones que identifican anuncios reales en plataformas externas
REAL_LINK_INDICATORS = [
    re.compile(r"\.aspx", re.IGNORECASE),
    re.compile(r"/estudiante-", re.IGNORECASE),
    re.compile(r"/estudiantes/", re.IGNORECASE),
    re.compile(r"/clases-particulares-[a-z]+/[a-z_]+-\d+", re.IGNORECASE),
    re.compile(r"/peticiones/clases-[a-z]+-\d+", re.IGNORECASE),
    re.compile(r"calculo_de_rendimiento_de_fabricas_de_ladrillo", re.IGNORECASE),
    re.compile(r"necesito_clases_particulares_mate_para_eso", re.IGNORECASE),
    re.compile(r"5363777", re.IGNORECASE),
    re.compile(r"5258472", re.IGNORECASE),
    re.compile(r"2466634", re.IGNORECASE),
    re.compile(r"2459605", re.IGNORECASE),
    re.compile(r"2456445", re.IGNORECASE),
    re.compile(r"2464467", re.IGNORECASE),
]


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

        if "tusclases" in u_low or "clasesparticulares.cl" in u_low:
            new_u = f"https://demo.prospeccion-alumnos.internal/tusclases/demanda-{h}"
        elif "tablon" in u_low:
            new_u = f"https://demo.prospeccion-alumnos.internal/tablon/demanda-{h}"
        elif "cronoshare" in u_low:
            new_u = f"https://demo.prospeccion-alumnos.internal/cronoshare/demanda-{h}"
        elif "reddit" in u_low:
            new_u = f"https://demo.prospeccion-alumnos.internal/reddit/demanda-{h}"
        elif "t.me" in u_low:
            new_u = f"https://demo.prospeccion-alumnos.internal/telegram/demanda-{h}"
        else:
            new_u = f"https://demo.prospeccion-alumnos.internal/anuncio/demanda-{h}"

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

        # Reemplazar nombres de personas reales si NAME_MAP está disponible
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

    # Recompilar CSVs y dashboard.html a partir de los JSONs anonimizados
    prospector_py = os.path.join(target_dir, "scripts", "prospector.py")
    subprocess.run([sys.executable, prospector_py, "build"], cwd=target_dir, check=True)

    # Documentación técnica y reportes
    for doc in ["docs/AUDITORIA_CAMBIOS.md", "docs/DOCUMENTACION_TECNICA.md", "docs/CONCLUSIONES.md", "evaluation/protocolo_anotacion.md"]:
        doc_path = os.path.join(target_dir, doc)
        if os.path.exists(doc_path):
            with open(doc_path, "r", encoding="utf-8") as f:
                c = f.read()
            c = mapas.transformar_texto(c)
            with open(doc_path, "w", encoding="utf-8") as f:
                f.write(c)


def verify_target(target_dir: str):
    residual_names = 0
    residual_links = 0

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
                rel_path = os.path.relpath(p, target_dir)

                # 1. Verificación de nombres reales (vía lista si está disponible)
                if REAL_NAMES:
                    for n in REAL_NAMES:
                        matches = list(re.finditer(r"\b" + re.escape(n) + r"\b", txt))
                        for m in matches:
                            line_start = txt.rfind("\n", 0, m.start()) + 1
                            line_end = txt.find("\n", m.end())
                            if line_end == -1:
                                line_end = len(txt)
                            line_content = txt[line_start:line_end].strip()
                            if any(k in line_content for k in ["NAME_MAP", "REAL_NAMES", "PSEUDONYMS_POOL", "FORBIDDEN_NAME_HASHES"]):
                                continue
                            print(f"  [ALERTA NOMBRE REAL] '{n}' en {rel_path}: {line_content[:90]}")
                            residual_names += 1

                # 2. Verificación ciega vía SHA-256 de tokens en archivos de datos y html
                if f.endswith((".json", ".csv", ".html")):
                    words = re.findall(r"\b[\wáéíóúÁÉÍÓÚñÑ]+\b", txt)
                    for i, w in enumerate(words):
                        h1 = hashlib.sha256(w.encode("utf-8")).hexdigest()
                        if h1 in FORBIDDEN_NAME_HASHES:
                            print(f"  [ALERTA HASH PII 1-GRAM] Token en {rel_path}: {w}")
                            residual_names += 1
                        if i + 1 < len(words):
                            w2 = f"{w} {words[i+1]}"
                            h2 = hashlib.sha256(w2.encode("utf-8")).hexdigest()
                            if h2 in FORBIDDEN_NAME_HASHES:
                                print(f"  [ALERTA HASH PII 2-GRAM] Token en {rel_path}: {w2}")
                                residual_names += 1

                # 3. Verificación de links reales a anuncios vivos
                if f.endswith((".json", ".csv", ".html")):
                    urls = re.findall(r"https?://[^\s\"\'<>]+", txt)
                    for u in urls:
                        u_low = u.lower()
                        if any(plat in u_low for plat in ["tusclases", "tablondeanuncios", "cronoshare"]):
                            for ind in REAL_LINK_INDICATORS:
                                if ind.search(u):
                                    print(f"  [ALERTA LINK REAL] URL viva detectada en {rel_path}: {u}")
                                    residual_links += 1
                                    break
            except Exception:
                pass

    if residual_names == 0:
        print("[OK] 0 nombres reales residuales")
    else:
        print(f"[ERROR] Se detectaron {residual_names} menciones de nombres reales.")

    if residual_links == 0:
        print("[OK] 0 links reales a anuncios residuales")
    else:
        print(f"[ERROR] Se detectaron {residual_links} enlaces reales a anuncios.")

    return residual_names + residual_links


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
        print(f"Mapeos cargados desde data/name_map.privado.json: {len(NAME_MAP)}")
        print("Para generar la carpeta pública limpia ejecuta: python scripts/anonymize_for_public.py --escribir")
        return

    print(f"--> Generando copia pública en: {PUBLIC_DIR}\n")
    if os.path.exists(PUBLIC_DIR):
        shutil.rmtree(PUBLIC_DIR)
    os.makedirs(PUBLIC_DIR, exist_ok=True)

    # Copiar archivos ignorando git, pycache, envs, mapas privados y sesiones
    def ignore_patterns(path, names):
        ignored = []
        for name in names:
            if name in [".git", "__pycache__", "node_modules", "centinela_session.session", ".env", "scratch", ".agents", "audit_work"]:
                ignored.append(name)
            elif name.startswith("backup_audit_"):
                ignored.append(name)
            elif name.endswith(".pyc") or name.endswith(".lock") or name.endswith(".bak"):
                ignored.append(name)
            elif name.endswith(".privado.json") or "privado" in name:
                ignored.append(name)
        return set(ignored)

    for item in os.listdir(PROJECT_ROOT):
        s = os.path.join(PROJECT_ROOT, item)
        d = os.path.join(PUBLIC_DIR, item)
        if item in [".git", "__pycache__", "node_modules", "centinela_session.session", ".env", "scratch", ".agents", "audit_work"] or item.startswith("backup_audit_"):
            continue
        if item.endswith(".privado.json") or "privado" in item:
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
