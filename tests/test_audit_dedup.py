"""
tests/test_audit_dedup.py
Regresión: el escaneo no debe duplicar leads en el CRM.
- Copias anonimizadas (URL sintética) nunca se re-auditan.
- IDs repetidos se consolidan prefiriendo la URL real.
- Si hay IA configurada pero todos los proveedores fallan, los avisos se posponen
  (no se persiste una decisión heurística ni se descartan como 'Pendiente').
"""
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import prospector  # noqa: E402
from prospector import dedupe_records_by_id, is_synthetic_url  # noqa: E402

SYN = "https://anuncio-ejemplo-anonimizado.local/tus-clases/abc1234567"
REAL = "https://www.tusclases.mx/estudiantes/matematicas/puebla/busco-clases-2463817"


def _lead(lid, url, msg="Busco profesor de matematicas para mi hijo"):
    return {"id": lid, "plataforma": "TusClases México", "enlace al anuncio": url,
            "materia": "Matemáticas", "mensaje/descripción": msg}


def test_dedupe_prefers_real_url_and_keeps_crm_state():
    a = dict(_lead("tc_mx_1", SYN), estado_contacto="Contactado")
    b = _lead("tc_mx_1", REAL)
    out = dedupe_records_by_id([a, b, _lead("tc_mx_2", REAL + "x")])
    assert [r["id"] for r in out] == ["tc_mx_1", "tc_mx_2"]
    assert out[0]["enlace al anuncio"] == REAL
    assert out[0]["estado_contacto"] == "Contactado"
    assert is_synthetic_url(SYN) and not is_synthetic_url(REAL)


def _run_audit(tmp_path, raw, approved, dispatch_result, env):
    inp = tmp_path / "raw.json"
    ap = tmp_path / "ap.json"
    di = tmp_path / "di.json"
    pr = tmp_path / "pr.json"
    inp.write_text(json.dumps(raw), encoding="utf-8")
    ap.write_text(json.dumps(approved), encoding="utf-8")
    di.write_text("[]", encoding="utf-8")
    args = SimpleNamespace(input=str(inp), model="gemini-3.5-flash", batch_size=10, api_key=None,
                           output_approved=str(ap), output_discarded=str(di), output_predictions=str(pr))
    clean_env = {k: v for k, v in os.environ.items()
                 if k not in ("GEMINI_API_KEY", "GROQ_API_KEY", "MISTRAL_API_KEY", "CLOUDFLARE_API_TOKEN")}
    clean_env.update(env)
    with patch.dict(os.environ, clean_env, clear=True), \
         patch.object(prospector, "call_multiprovider_batch", side_effect=dispatch_result) as m, \
         patch.object(prospector, "check_and_record_source_health"), \
         patch.object(prospector, "notify_telegram_lead"), \
         patch.object(prospector.time, "sleep"):
        prospector.cmd_audit(args)
    return json.loads(ap.read_text(encoding="utf-8")), json.loads(di.read_text(encoding="utf-8")), m


def test_audit_skips_synthetic_copies_and_never_duplicates(tmp_path):
    existing = [_lead("tc_mx_1", SYN)]
    raw = [_lead("tc_mx_1", SYN), _lead("tc_mx_1", REAL), _lead("tusclase_ffff", SYN.replace("abc", "zzz"))]

    def ok(items, **kw):
        return [{"id": it["id"], "is_student": True, "actual_provider": "Google Gemini"} for it in items]

    ap, di, m = _run_audit(tmp_path, raw, existing, ok, {"GEMINI_API_KEY": "x"})
    ids = [r["id"] for r in ap]
    assert len(ids) == len(set(ids)), f"IDs duplicados: {ids}"
    assert not m.called, "No debía auditar copias sintéticas ni IDs ya auditados"


def test_audit_postpones_when_all_providers_fail(tmp_path):
    raw = [_lead("tc_mx_9", REAL)]

    def heuristic(items, **kw):
        return [{"id": it["id"], "is_student": True, "actual_provider": "Heuristic Engine"} for it in items]

    ap, di, _ = _run_audit(tmp_path, raw, [], heuristic, {"GEMINI_API_KEY": "x"})
    assert ap == [] and di == [], "Con IA configurada caída, el aviso debe quedar pendiente"

    def boom(items, **kw):
        raise RuntimeError("HTTP 429")

    ap, di, _ = _run_audit(tmp_path, raw, [], boom, {"GEMINI_API_KEY": "x"})
    assert ap == [] and di == []
