#!/usr/bin/env python3
"""
tests/test_features_f1_f5.py
Suite de pruebas exhaustivas para las nuevas funcionalidades F1 a F5:
- F1: CLI de etiquetado ciego, reanudabilidad y persistencia de predicciones
- F2: Embudo de conversión, reporte comercial, columnas canónicas de embudo.csv y exportación JSON
- F3: Monitoreo y registro de salud de fuentes extractoras (salud_fuentes.csv y FUENTE_ROTA)
- F4: Deduplicación 24h por persona_id, función de scoring, routing a push o digest y edad_msg_min
- F5: Regla de caducidad automática de prospectos (> 21 días) y preservación de estados activos
"""

import os
import sys
import json
import csv
import time
import unittest
import tempfile
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from etiquetar_cli import load_and_sample_listings, run_labeling_session
from prospector import (
    save_classifier_predictions,
    check_and_record_source_health,
    apply_lead_expiration,
    normalize_item
)
from reporte_embudo import build_funnel_metrics, generate_embudo_csv
from telegram_centinela import (
    is_persona_deduped_24h,
    record_persona_seen,
    compute_heuristic_score,
    compute_combined_score,
    enqueue_for_daily_digest,
    send_daily_digest,
    send_centinela_push_alert
)


class TestFeature1(unittest.TestCase):
    """F1: Etiquetado ciego, reanudabilidad y predicciones persistidas."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.test_dir)

    def test_sample_deterministic_100_items(self):
        raw_path = PROJECT_ROOT / "data" / "extracted_listings.json"
        sample = load_and_sample_listings(str(raw_path), sample_size=100, seed=42)
        self.assertEqual(len(sample), 100)
        # La semilla 42 debe retornar siempre el mismo primer elemento
        self.assertIn(sample[0]["id"], ["tc_pe_2450843", "tusclase_86dc3ac24a"])
        # Verificar que todos tienen ID
        self.assertTrue(all(bool(it.get("id")) for it in sample))

    def test_labeling_session_and_resumability(self):
        out_json = os.path.join(self.test_dir, "labels.json")
        sample_mock = [
            {"id": "lead_001", "plataforma": "TusClases", "materia": "Física", "mensaje": "busco profe"},
            {"id": "lead_002", "plataforma": "Tablón", "materia": "Química", "mensaje": "doy clases"},
            {"id": "lead_003", "plataforma": "Cronoshare", "materia": "Matemática", "mensaje": "necesito profe"}
        ]

        # Sesión 1: etiquetar 1, 0 y luego salir ('q')
        count1 = run_labeling_session(sample_mock, out_json, annotator="test_user", mock_inputs=["1", "0", "q"])
        self.assertEqual(count1, 2)

        with open(out_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["id"], "lead_001")
        self.assertEqual(data[0]["label"], 1)
        self.assertEqual(data[1]["id"], "lead_002")
        self.assertEqual(data[1]["label"], 0)
        self.assertEqual(data[0]["annotator"], "test_user")
        self.assertIn("ts", data[0])

        # Sesión 2 (reanudabilidad): debe detectar 2 ya hechos y procesar lead_003
        count2 = run_labeling_session(sample_mock, out_json, annotator="test_user", mock_inputs=["1", "q"])
        self.assertEqual(count2, 1)

        with open(out_json, "r", encoding="utf-8") as f:
            data_final = json.load(f)
        self.assertEqual(len(data_final), 3)
        self.assertEqual(data_final[2]["id"], "lead_003")

    def test_save_classifier_predictions(self):
        pred_file = os.path.join(self.test_dir, "predicciones.json")
        mock_leads = [
            {"id": "item_1", "decision_ia": "Aprobado", "justificacion_ia": "Demanda genuina", "is_student": True},
            {"id": "item_2", "decision_ia": "Descartado", "justificacion_ia": "Academia comercial", "is_student": False}
        ]
        total = save_classifier_predictions(mock_leads, output_path=pred_file, model_name="gemini-3.5-flash")
        self.assertEqual(total, 2)

        with open(pred_file, "r", encoding="utf-8") as f:
            saved = json.load(f)
        self.assertEqual(len(saved), 2)
        self.assertEqual(saved[0]["id"], "item_1")
        self.assertEqual(saved[0]["decision_ia"], "Aprobado")
        self.assertTrue(saved[0]["is_student"])
        self.assertEqual(saved[0]["modelo"], "gemini-3.5-flash")


class TestFeature2(unittest.TestCase):
    """F2: Embudo de conversión, reporte y data/embudo.csv."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.test_dir)

    def test_funnel_metrics_and_csv_generation(self):
        base_time = datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc)
        leads = [
            {
                "id": "1",
                "plataforma": "TusClases",
                "fecha_captura": base_time.isoformat(),
                "estado": "cerrado",
                "historial_estados": [
                    {"from": "nuevo", "to": "contactado", "estado": "contactado", "ts": (base_time + timedelta(hours=6)).isoformat()},
                    {"from": "contactado", "to": "respondio", "estado": "respondio", "ts": (base_time + timedelta(hours=10)).isoformat()},
                    {"from": "respondio", "to": "cerrado", "estado": "cerrado", "ts": (base_time + timedelta(hours=24)).isoformat()}
                ]
            },
            {
                "id": "2",
                "plataforma": "TusClases",
                "fecha_captura": base_time.isoformat(),
                "estado": "respondio",
                "historial_estados": [
                    {"from": "nuevo", "to": "contactado", "estado": "contactado", "ts": (base_time + timedelta(hours=12)).isoformat()},
                    {"from": "contactado", "to": "respondio", "estado": "respondio", "ts": (base_time + timedelta(hours=18)).isoformat()}
                ]
            },
            {
                "id": "3",
                "plataforma": "Cronoshare",
                "fecha_captura": base_time.isoformat(),
                "estado": "nuevo",
                "historial_estados": []
            }
        ]

        rows, total = build_funnel_metrics(leads)
        self.assertEqual(total["leads"], 3)
        self.assertEqual(total["contactados"], 2)
        self.assertEqual(total["respondieron"], 2)
        self.assertEqual(total["cerrados"], 1)
        self.assertEqual(total["tasa_resp"], 1.0)
        self.assertEqual(total["tasa_cierre"], 0.5)
        # Delays de TusClases: [6.0, 12.0] -> mediana = 9.0h
        self.assertEqual(total["mediana_h_deteccion_a_contacto"], 9.0)

        csv_path = os.path.join(self.test_dir, "embudo.csv")
        generate_embudo_csv(rows, total, csv_path)

        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            header = next(reader)
            expected_header = [
                "plataforma", "leads", "contactados", "respondieron",
                "cerrados", "tasa_resp", "tasa_cierre", "mediana_h_deteccion_a_contacto"
            ]
            self.assertEqual(header, expected_header)


class TestFeature3(unittest.TestCase):
    """F3: Monitoreo y salud de fuentes extractoras."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.test_dir)

    def test_salud_fuentes_alert_and_csv(self):
        csv_path = os.path.join(self.test_dir, "salud_fuentes.csv")

        # Sembrar historial de los últimos 7 días con 20 anuncios por día para TusClases
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["fecha", "fuente", "n"], lineterminator="\r\n")
            writer.writeheader()
            for d in range(1, 8):
                writer.writerow({"fecha": f"2026-10-{d:02d}", "fuente": "TusClases", "n": 20})
                writer.writerow({"fecha": f"2026-10-{d:02d}", "fuente": "Cronoshare", "n": 10})

        # Caso A: Hoy TusClases cae a 4 anuncios (< 0.3 * 20 = 6) -> ALERTA FUENTE_ROTA
        # Hoy Cronoshare tiene 8 anuncios (>= 0.3 * 10 = 3) -> SALUDABLE
        current_listings = [
            {"plataforma": "TusClases"} for _ in range(4)
        ] + [
            {"plataforma": "Cronoshare"} for _ in range(8)
        ]

        alerts = check_and_record_source_health(current_listings, output_csv=csv_path, today_str="2026-10-08")
        alert_fuentes = {a["fuente"] for a in alerts}

        self.assertIn("TusClases", alert_fuentes)
        self.assertNotIn("Cronoshare", alert_fuentes)
        self.assertIn("FUENTE_ROTA TusClases", alerts[0]["mensaje"])


class TestFeature4(unittest.TestCase):
    """F4: Telegram Centinela: Deduplicación 24h, Scoring, Routing y Antigüedad."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.test_dir)
        import telegram_centinela
        self.orig_dedupe = telegram_centinela.DEDUPE_FILE
        self.orig_queue = telegram_centinela.DIGEST_QUEUE_FILE
        telegram_centinela.DEDUPE_FILE = os.path.join(self.test_dir, "dedupe.json")
        telegram_centinela.DIGEST_QUEUE_FILE = os.path.join(self.test_dir, "digest.json")

    def tearDown(self):
        import telegram_centinela
        telegram_centinela.DEDUPE_FILE = self.orig_dedupe
        telegram_centinela.DIGEST_QUEUE_FILE = self.orig_queue

    def test_persona_deduplication_24h(self):
        now = time.time()
        # Inicialmente no deduplicada
        self.assertFalse(is_persona_deduped_24h("alumno_123", current_time=now))

        record_persona_seen("alumno_123", current_time=now)
        # Dentro de las 24h debe estar deduplicada
        self.assertTrue(is_persona_deduped_24h("alumno_123", current_time=now + 3600))  # 1h después
        self.assertTrue(is_persona_deduped_24h("alumno_123", current_time=now + 86399)) # 23h 59m después

        # Luego de 24h expira la deduplicación
        self.assertFalse(is_persona_deduped_24h("alumno_123", current_time=now + 86401))

    def test_scoring_function(self):
        # Texto de estudiante con alta intención y materia
        student_text = "Hola! Busco profesor particular urgente de Análisis Matemático y Álgebra para preparar el recuperatorio del parcial."
        score_heur = compute_heuristic_score(student_text)
        self.assertGreaterEqual(score_heur, 0.70)

        # Score combinado con IA positiva
        score_final = compute_combined_score(score_heur, 0.95)
        self.assertGreaterEqual(score_final, 0.75)

        # Texto de profesor ofreciendo clases
        teacher_text = "Doy clases de Física y Química. Amplia experiencia docente, primera clase gratis. Consultas al MD."
        score_teach_heur = compute_heuristic_score(teacher_text)
        self.assertLessEqual(score_teach_heur, 0.40)
        score_teach_final = compute_combined_score(score_teach_heur, 0.10)
        self.assertLessEqual(score_teach_final, 0.30)

    def test_daily_digest_queue_and_flush(self):
        lead_mock = {"id": "tg_001", "nombre": "Martín", "materia": "Física"}
        enqueue_for_daily_digest(lead_mock, "Exactas UBA", "martin_exactas", 0.65, 3.5)

        flushed = send_daily_digest(force=True)
        self.assertEqual(flushed, 1)

        # Después de flush la cola queda vacía
        self.assertEqual(send_daily_digest(force=True), 0)


class TestFeature5(unittest.TestCase):
    """F5: Caducidad automática (> 21 días) para leads en estado nuevo."""

    def test_apply_lead_expiration(self):
        ref_date = datetime(2026, 11, 4, 12, 0)
        leads = [
            # Caso 1: Nuevo con 25 días de antigüedad -> debe vencer
            {
                "id": "old_new",
                "fecha_captura": "2026-10-05",
                "estado": "nuevo",
                "historial_estados": []
            },
            # Caso 2: Nuevo con 10 días de antigüedad -> debe seguir nuevo
            {
                "id": "recent_new",
                "fecha_captura": "2026-10-28",
                "estado": "nuevo",
                "historial_estados": []
            },
            # Caso 3: Contactado con 30 días de antigüedad -> NO debe vencer (preservar CRM)
            {
                "id": "old_contacted",
                "fecha_captura": "2026-10-01",
                "estado": "contactado",
                "historial_estados": [{"estado": "contactado", "ts": "2026-10-02"}]
            }
        ]

        expired = apply_lead_expiration(leads, max_days=21, reference_date=ref_date)
        self.assertEqual(expired, 1)
        self.assertEqual(leads[0]["estado"], "vencido")
        self.assertEqual(leads[1]["estado"], "nuevo")
        self.assertEqual(leads[2]["estado"], "contactado")
        self.assertEqual(leads[0]["historial_estados"][-1]["to"], "vencido")


if __name__ == "__main__":
    unittest.main()
