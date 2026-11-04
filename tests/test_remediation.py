#!/usr/bin/env python3
"""
tests/test_remediation.py
Valida integralmente todas las directivas de remediación P0, P1 y P2:
- P0: Purga de referencias obsoletas (Gemini 2.5), registro único de proveedores, validación y logging.
- P1: Mitigación de fuga de datos en evaluación, enforcement de ground truth independiente,
      persistencia atómica read-modify-write y extracción fresca por defecto.
- P2: Verificación de telemetría de conversiones comerciales del piloto e integridad dataset/docs.
"""

import os
import sys
import json
import pytest
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai_providers import PROVIDER_REGISTRY, ProviderRegistry
from storage import atomic_modify_json, safe_read_json, atomic_write_json
from prospector import cmd_run
from evaluation.evaluar_clasificadores import run_evaluation


class TestP0ProviderRegistryAndObsoletePurge(unittest.TestCase):
    """P0: Purga de modelos obsoletos y registro único de proveedores."""

    def test_p0_validate_model_rejects_obsolete_models(self):
        obsolete_models = [
            "gemini-2.5-flash",
            "gemini-2.5",
            "gemini-1.5-flash",
            "gemini-1.0-pro"
        ]
        for m in obsolete_models:
            with self.assertRaises(ValueError, msg=f"El modelo {m} no fue rechazado por validate_model"):
                PROVIDER_REGISTRY.validate_model(m)

    def test_p0_validate_model_accepts_current_models(self):
        valid_models = [
            "gemini-3.5-flash",
            "gemini-3.6-flash",
            "gemini-3.8-flash",
            "llama-3.3-70b-versatile",
            "mistral-small-latest"
        ]
        for m in valid_models:
            try:
                res = PROVIDER_REGISTRY.validate_model(m)
                self.assertEqual(res, m)
            except ValueError as e:
                self.fail(f"Modelo válido {m} fue erróneamente rechazado: {e}")

    def test_p0_metricas_clasificador_has_no_gemini_2_5(self):
        json_path = PROJECT_ROOT / "evaluation" / "metricas_clasificador.json"
        self.assertTrue(json_path.exists())
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertNotIn("gemini_2_5_flash", data, "gemini_2_5_flash no debe existir en metricas_clasificador.json")
        self.assertNotIn("gemini-2.5-flash", str(data), "Referencias a gemini-2.5-flash prohibidas en metricas_clasificador.json")

    def test_p0_dispatch_logs_and_attaches_actual_provider_and_model(self):
        sample_items = [
            {"id": "rem_test_01", "mensaje": "busco profesor de matematicas para examen"}
        ]
        res = PROVIDER_REGISTRY.dispatch(sample_items, primary_model="gemini-3.5-flash", api_key="")
        self.assertEqual(len(res), 1)
        item = res[0]
        self.assertIn("actual_provider", item, "Falta 'actual_provider' en resultado de dispatch")
        self.assertIn("actual_model", item, "Falta 'actual_model' en resultado de dispatch")
        self.assertIn(item["actual_provider"], ["Google Gemini", "Cloudflare Workers AI", "Groq Cloud", "Mistral AI", "Heuristic Engine"])
        self.assertTrue(item["actual_model"])


class TestP1EvaluationAndDataIntegrity(unittest.TestCase):
    """P1: Evaluación sin fuga de datos, GT independiente, RMW atómico y extracción fresca."""

    def test_p1_atomic_modify_json_single_process(self):
        tmp_file = PROJECT_ROOT / "tests" / "tmp_test_atomic_modify.json"
        try:
            if tmp_file.exists():
                tmp_file.unlink()

            def init_data(data):
                if not isinstance(data, dict) or "count" not in data:
                    data = {"count": 0, "items": []}
                data["count"] += 1
                data["items"].append("first")
                return data

            atomic_modify_json(str(tmp_file), init_data, default={})
            res = safe_read_json(str(tmp_file), default={})
            self.assertEqual(res["count"], 1)
            self.assertEqual(res["items"], ["first"])

            def append_data(data):
                data["count"] += 10
                data["items"].append("second")
                return data

            atomic_modify_json(str(tmp_file), append_data, default={})
            res2 = safe_read_json(str(tmp_file), default={})
            self.assertEqual(res2["count"], 11)
            self.assertEqual(res2["items"], ["first", "second"])
        finally:
            if tmp_file.exists():
                tmp_file.unlink()

    def test_p1_require_independent_ground_truth(self):
        # run_evaluation con require_independent_gt=True debe funcionar cuando labels_humanos existe
        perf = run_evaluation(require_independent_gt=True)
        self.assertIn("evaluation_provenance", perf)
        prov = perf["evaluation_provenance"]
        self.assertTrue(prov["independent_ground_truth_enforced"])
        self.assertTrue(prov["data_leakage_prevented"])

    def test_p1_prospector_defaults_to_fresh_extraction(self):
        # Verificar que cmd_run invoca extracción fresca por defecto si cached=False
        args = MagicMock()
        args.cached = False
        args.skip_extraction = False

        with patch("subprocess.run") as mock_sub:
            mock_sub.return_value = MagicMock(returncode=0)
            with patch("prospector.cmd_audit"):
                with patch("prospector.cmd_build"):
                    cmd_run(args)
            mock_sub.assert_called_once()
            call_args = mock_sub.call_args[0][0]
            self.assertTrue(any("run_extraction.py" in str(arg) for arg in call_args))

        # Verificar que respeta el flag --cached y omite la extracción fresca
        args_cached = MagicMock()
        args_cached.cached = True
        args_cached.skip_extraction = False
        with patch("subprocess.run") as mock_sub:
            with patch("prospector.cmd_audit"):
                with patch("prospector.cmd_build"):
                    cmd_run(args_cached)
            mock_sub.assert_not_called()


class TestP2CommercialConversionsAndSync(unittest.TestCase):
    """P2: Verificación de conversiones comerciales del piloto y consistencia de documentos."""

    def test_p2_commercial_conversions_exist_in_canonical_dataset(self):
        feedback_path = PROJECT_ROOT / "data" / "feedback_piloto_conversion.json"
        canon_path = PROJECT_ROOT / "data" / "dataset_canonico_auditado.json"

        self.assertTrue(feedback_path.exists())
        self.assertTrue(canon_path.exists())

        with open(feedback_path, "r", encoding="utf-8") as f:
            feedback_data = json.load(f)
        with open(canon_path, "r", encoding="utf-8") as f:
            canon_data = json.load(f)

        canon_ids = {row["id"]: row for row in canon_data}
        conversions = feedback_data["detalle_conversiones_exitosas"]

        self.assertEqual(len(conversions), 3, "Debe haber exactamente 3 conversiones comerciales documentadas")
        for conv in conversions:
            lid = conv["lead_id"]
            self.assertIn(lid, canon_ids, f"Lead convertido {lid} no existe en dataset_canonico_auditado.json")
            canon_row = canon_ids[lid]
            self.assertEqual(canon_row["decision_ia"], "Aprobado", f"Lead {lid} debe estar Aprobado por la IA")

    def test_p2_funnel_numbers_mathematical_consistency(self):
        feedback_path = PROJECT_ROOT / "data" / "feedback_piloto_conversion.json"
        with open(feedback_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        m = data["metricas_generales"]
        fp = m["fase_piloto"]

        self.assertEqual(m["total_anuncios_extraidos"], 175)
        self.assertEqual(m["total_prospectos_calificados"], 41)
        self.assertEqual(fp["contactados"], 18)
        self.assertEqual(fp["respondieron"], 7)
        self.assertEqual(fp["convertidos_pagados"], 3)
        self.assertEqual(fp["descartados_post_contacto"], 4)
        self.assertEqual(fp["sin_respuesta_7_dias"], 11)
        self.assertEqual(fp["en_espera_lote_2"], 23)

        # Ecuaciones de balance del embudo
        self.assertEqual(fp["contactados"] + fp["en_espera_lote_2"], m["total_prospectos_calificados"])
        self.assertEqual(fp["convertidos_pagados"] + fp["descartados_post_contacto"], fp["respondieron"])
        self.assertEqual(fp["respondieron"] + fp["sin_respuesta_7_dias"], fp["contactados"])


if __name__ == "__main__":
    unittest.main()
