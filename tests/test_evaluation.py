#!/usr/bin/env python3
"""
tests/test_evaluation.py
Verifica la reproducibilidad del benchmark de Machine Learning y consistencia de las métricas.
"""

import unittest
import json
from pathlib import Path
from evaluation.evaluar_clasificadores import compute_metrics, run_evaluation

PROJECT_ROOT = Path(__file__).resolve().parent.parent

class TestEvaluationBenchmark(unittest.TestCase):

    def test_compute_metrics_math_accuracy(self):
        # Caso perfecto: 10 TP, 0 FP, 10 TN, 0 FN
        res = compute_metrics(10, 0, 10, 0)
        self.assertEqual(res["accuracy"], 1.0)
        self.assertEqual(res["precision"], 1.0)
        self.assertEqual(res["recall"], 1.0)
        self.assertEqual(res["f1_score"], 1.0)

        # Caso con falsos positivos y negativos
        # TP=8, FP=2, TN=8, FN=2
        res2 = compute_metrics(8, 2, 8, 2)
        self.assertEqual(res2["precision"], 0.8)
        self.assertEqual(res2["recall"], 0.8)
        self.assertEqual(res2["f1_score"], 0.8)

    def test_run_evaluation_generates_valid_json_and_markdown(self):
        performance = run_evaluation()
        self.assertIn("baseline_regex", performance)
        self.assertIn("gemini_3_5_flash", performance)
        self.assertIn("by_platform", performance)

        json_path = PROJECT_ROOT / "evaluation" / "metricas_clasificador.json"
        md_path = PROJECT_ROOT / "evaluation" / "README.md"
        
        self.assertTrue(json_path.exists())
        self.assertTrue(md_path.exists())

        # Gemini debe tener recall de 100% y F1 superior al 95%
        gemini_f1 = performance["gemini_3_5_flash"]["metrics"]["f1_score"]
        regex_f1 = performance["baseline_regex"]["metrics"]["f1_score"]
        self.assertGreater(gemini_f1, regex_f1)
        self.assertGreater(gemini_f1, 0.95)

if __name__ == "__main__":
    unittest.main()
