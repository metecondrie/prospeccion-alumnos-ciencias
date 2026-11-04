"""
test_correcciones.py -- una prueba por correccion acordada.
Regla: una correccion esta HECHA solo si su test pasa. Nadie edita ni borra estos tests
para hacerlos pasar; solo se agregan nuevos (cada correccion nueva = test nuevo que falla primero).
"""
import json
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
ESTE = Path(__file__).resolve()
EXT = {".py", ".bat", ".md", ".html", ".yml", ".yaml", ".json", ".cjs", ".txt", ".ipynb"}


def archivos():
    for p in ROOT.rglob("*"):
        if p.is_file() and p.suffix in EXT and ".git" not in p.parts and p.resolve() != ESTE:
            yield p


def leer(rel):
    p = ROOT / rel
    return p.read_text(encoding="utf-8", errors="ignore") if p.exists() else ""


def rastreados():
    try:
        out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    except Exception:
        pytest.skip("git no disponible")
    return [ROOT / l for l in out.splitlines() if l]


# --- C1 rutas personales --------------------------------------------------------------
def test_c1_sin_rutas_onedrive():
    malos = [str(p.relative_to(ROOT)) for p in archivos() if "OneDrive" in p.read_text(encoding="utf-8", errors="ignore")]
    assert not malos, f"OneDrive en: {malos}"


# --- C2 metricas calculadas, no hardcodeadas ------------------------------------------
def test_c2_metricas_no_hardcodeadas():
    src = leer("evaluation/evaluar_clasificadores.py")
    assert src, "falta evaluation/evaluar_clasificadores.py"
    assert not re.search(r"\b[a-z]_(tp|fp|tn|fn)\s*=\s*\d+", src), "literales tp/fp/tn/fn"


def test_c2b_ground_truth_desde_etiquetas_humanas():
    assert "labels_humanos" in leer("evaluation/evaluar_clasificadores.py"), "gt no sale de labels_humanos.json"


# --- C3 coherencia interna del benchmark ----------------------------------------------
def _gt_positivos():
    for rel, campo in (("evaluation/labels_humanos.json", "label"),
                       ("evaluation/dataset_benchmark_etiquetado.json", "ground_truth_label")):
        p = ROOT / rel
        if p.exists():
            rows = json.loads(p.read_text(encoding="utf-8"))
            return len(rows), sum(1 for r in rows if int(r[campo]) == 1)
    pytest.skip("sin ground truth")


def test_c3_matriz_coincide_con_ground_truth():
    p = ROOT / "evaluation/metricas_clasificador.json"
    if not p.exists():
        pytest.skip("sin metricas")
    n, pos = _gt_positivos()
    m = json.loads(p.read_text(encoding="utf-8"))
    for modelo in ("baseline_regex", "gemini_2_5_flash"):
        if modelo not in m:
            continue
        cm = m[modelo]["metrics"]["confusion_matrix"]
        assert cm["tp"] + cm["fp"] + cm["tn"] + cm["fn"] == n, f"{modelo}: suma != n"
        assert cm["tp"] + cm["fn"] == pos, f"{modelo}: positivos {cm['tp'] + cm['fn']} != ground truth {pos}"


def test_c3b_readmes_muestran_mismas_metricas():
    pat = re.compile(r"\| \*\*(?:Precisi[oó]n|Sensibilidad|Especificidad)[^|]*\|\s*([\d.]+)%\s*\|\s*\*\*([\d.]+)%")
    a, b = pat.findall(leer("README.md")), pat.findall(leer("evaluation/README.md"))
    assert a == b, f"README.md {a} != evaluation/README.md {b}"


# --- C4 no afirmar etiquetado humano sin evidencia ------------------------------------
def test_c4_sin_afirmar_etiquetado_humano_sin_labels():
    if (ROOT / "evaluation/labels_humanos.json").exists():
        return
    frases = re.compile(r"evaluador humano|auditor.a humana|verificado manualmente|manually verified|human annotator", re.I)
    malos = [rel for rel in ("README.md", "README_EN.md", "evaluation/README.md",
                             "evaluation/protocolo_anotacion.md", "evaluation/evaluar_clasificadores.py")
             if frases.search(leer(rel))]
    assert not malos, f"afirma etiquetado humano sin labels_humanos.json: {malos}"


# --- C5 contacto inventado -------------------------------------------------------------
def test_c5_sin_mail_inventado():
    malos = [str(p.relative_to(ROOT)) for p in archivos() if "ciencias.org" in p.read_text(encoding="utf-8", errors="ignore")]
    assert not malos, f"mail inventado en: {malos}"


# --- C6 auto-join con tope --------------------------------------------------------------
def test_c6_autojoin_con_tope_y_actividad_real():
    src = leer("scripts/auto_join_groups.py")
    assert "MAX_JOINS_DIA" in src, "falta MAX_JOINS_DIA"
    assert "limit=1" not in src, "sigue mirando solo el ultimo mensaje"


# --- C7 afirmaciones del README ---------------------------------------------------------
def test_c7_readme_sin_sobreafirmaciones():
    assert "Programé" not in leer("README.md")
    assert "100% verde" not in leer("README.md") + leer(".github/workflows/ci.yml")


# --- C8 datos de prueba fuera del canonico -----------------------------------------------
def test_c8_sin_registros_de_prueba_en_canonico():
    rows = json.loads(leer("data/dataset_canonico_auditado.json") or "[]")
    malos = [r.get("id") for r in rows if str(r.get("id", "")).startswith("tg_test") or "Simulado" in str(r.get("nombre", ""))]
    assert not malos, f"registros de prueba: {malos}"


# --- C9 mensajes propios solo en modo prueba ---------------------------------------------
def test_c9_mensajes_propios_solo_en_test_mode():
    lineas = [l for l in leer("scripts/telegram_centinela.py").splitlines() if "event.out" in l]
    assert lineas and all("test_mode" in l for l in lineas), lineas


# --- C10 seguridad: secretos y sesion ----------------------------------------------------
def test_c10_sesion_y_env_no_rastreados():
    malos = [p.name for p in rastreados() if p.name == ".env" or ".session" in p.name or p.name.startswith("centinela_session")]
    assert not malos, malos


def test_c10b_gitignore_cubre_sesion_y_env():
    gi = leer(".gitignore")
    assert ".env" in gi and "*.session" in gi


def test_c10c_sin_claves_en_archivos_rastreados():
    pat = re.compile(r"AIza[0-9A-Za-z_\-]{35}|gsk_[0-9A-Za-z]{30,}|\b\d{8,10}:[A-Za-z0-9_\-]{35}\b|\bapi_hash\s*=\s*['\"][0-9a-f]{32}")
    malos = []
    for p in rastreados():
        if p.resolve() != ESTE and p.suffix in EXT and pat.search(p.read_text(encoding="utf-8", errors="ignore")):
            malos.append(p.name)
    assert not malos, f"posible clave en: {malos}"

# --- C11 URLs sintéticas y privacidad de slugs ----------------------------------------
def test_c11_urls_sinteticas_y_slugs_sin_pii():
    try:
        from tests.test_pii_security import FORBIDDEN_NAME_HASHES
    except ImportError:
        import sys
        sys.path.insert(0, str(ROOT))
        from tests.test_pii_security import FORBIDDEN_NAME_HASHES
    import hashlib

    pat_real_url = re.compile(r"tusclases|tablondeanuncios|cronoshare\.com|reddit\.com", re.I)
    token_split = re.compile(r"[/_\-?&=.]")

    malas_urls = []
    slug_tokens_pii = []

    # Recorrer datasets, entregables y archivos estructurados del árbol
    for p in ROOT.rglob("*"):
        if not p.is_file():
            continue
        if any(x in p.parts for x in [".git", ".venv", "node_modules", "scratch", ".pytest_cache", "audit_work"]):
            continue
        if p.suffix in {".json", ".csv", ".html"} or p.parent.name == "data":
            txt = p.read_text(encoding="utf-8", errors="ignore")
            # (a) 0 URLs reales (regex tusclases|tablondeanuncios|cronoshare.com|reddit.com)
            urls = re.findall(r"https?://[^\s\"\'<>]+", txt)
            for u in urls:
                if pat_real_url.search(u):
                    malas_urls.append((str(p.relative_to(ROOT)), u))
                # (b) 0 tokens de slugs cuyo sha256 coincida con el set prohibido de test_pii_security
                if "anuncio-ejemplo-anonimizado.local" in u:
                    slug_part = u.split("anuncio-ejemplo-anonimizado.local", 1)[1]
                    for tok in token_split.split(slug_part):
                        tok_clean = tok.strip().lower()
                        if tok_clean:
                            h = hashlib.sha256(tok_clean.encode("utf-8")).hexdigest()
                            if h in FORBIDDEN_NAME_HASHES:
                                slug_tokens_pii.append((str(p.relative_to(ROOT)), u, tok))

    assert not malas_urls, f"URLs reales detectadas: {malas_urls}"
    assert not slug_tokens_pii, f"Tokens de slugs con PII detectados: {slug_tokens_pii}"


test_c11 = test_c11_urls_sinteticas_y_slugs_sin_pii

