import unittest
import os
import sys

# Ensure scripts dir is on sys.path
SCRIPT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from prospector import (
    compute_stable_id,
    sanitize_csv,
    safe_hyperlink,
    strip_accents,
    normalize_item,
    parse_json_response,
    rule_based_audit,
    call_multiprovider_batch
)


class TestProspectorCore(unittest.TestCase):
    """Pruebas unitarias de las funciones nucleares del pipeline de prospección."""

    def test_strip_accents(self):
        self.assertEqual(strip_accents("Matemáticas"), "matematicas")
        self.assertEqual(strip_accents("Álgebra Lineal"), "algebra lineal")
        self.assertEqual(strip_accents("Física Cuántica"), "fisica cuantica")
        self.assertEqual(strip_accents(""), "")
        self.assertEqual(strip_accents(None), "")

    def test_sanitize_csv_formula_injection(self):
        # Evita fórmulas ejecutables en hojas de cálculo (CSV Injection / DDE)
        self.assertEqual(sanitize_csv("=SUM(A1:A10)"), "'=SUM(A1:A10)")
        self.assertEqual(sanitize_csv("+12345"), "'+12345")
        self.assertEqual(sanitize_csv("-100"), "'-100")
        self.assertEqual(sanitize_csv("@HYPERLINK"), "'@HYPERLINK")
        self.assertEqual(sanitize_csv("\tTabbed"), "'\tTabbed")
        self.assertEqual(sanitize_csv("\rCarriage"), "'\rCarriage")

        # Preserva textos normales y tipos primitivos
        self.assertEqual(sanitize_csv("Texto ordinario"), "Texto ordinario")
        self.assertEqual(sanitize_csv(True), "true")
        self.assertEqual(sanitize_csv(False), "false")
        self.assertEqual(sanitize_csv(None), "")

    def test_safe_hyperlink(self):
        valid_url = "https://www.tusclases.com.ar/anuncio-123.aspx"
        expected = '=HYPERLINK("https://www.tusclases.com.ar/anuncio-123.aspx", "🔗 Abrir Anuncio")'
        self.assertEqual(safe_hyperlink(valid_url), expected)

        # URL con comillas dobles debe escaparse
        url_with_quotes = 'https://ejemplo.com/path?param="test"'
        escaped_expected = '=HYPERLINK("https://ejemplo.com/path?param=""test""", "🔗 Abrir Anuncio")'
        self.assertEqual(safe_hyperlink(url_with_quotes), escaped_expected)

        # Payload no HTTP no debe generar fórmula
        self.assertEqual(safe_hyperlink("javascript:alert(1)"), "javascript:alert(1)")
        self.assertEqual(safe_hyperlink(""), "")

    def test_compute_stable_id_determinism(self):
        # TusClases Argentina
        id_tc_ar = compute_stable_id(
            "TusClases Argentina",
            "https://www.tusclases.com.ar/estudiante/buenos-aires/anuncio-9999001.aspx",
            "Busco docente"
        )
        self.assertEqual(id_tc_ar, "tc_ar_9999001")

        # TusClases Chile
        id_tc_cl = compute_stable_id(
            "TusClases Chile",
            "https://www.clasesparticulares.cl/estudiante/santiago/anuncio-9999002.aspx",
            "Busco profe física"
        )
        self.assertEqual(id_tc_cl, "tc_cl_9999002")

        # Tablón de Anuncios
        id_tablon = compute_stable_id(
            "Tablón de Anuncios",
            "https://www.tablondeanuncios.com/clases-particulares/anuncio-9999003.htm",
            "Cálculo"
        )
        self.assertEqual(id_tablon, "tablon_es_9999003")

        # Fallback criptográfico determinista
        h1 = compute_stable_id("Foro General", "https://ejemplo.com/lead1", "Mensaje de prueba")
        h2 = compute_stable_id("Foro General", "https://ejemplo.com/lead1", "Mensaje de prueba")
        self.assertEqual(h1, h2)
        self.assertTrue(h1.startswith("forogene_"))

    def test_normalize_item_countries(self):
        items = [
            ({"país/ubicación": "España - Madrid"}, "España"),
            ({"país/ubicación": "Argentina - Rosario"}, "Argentina"),
            ({"país/ubicación": "Chile - Santiago"}, "Chile"),
            ({"país/ubicación": "Colombia - Bogotá"}, "Colombia"),
            ({"país/ubicación": "México - CDMX"}, "México"),
            ({"país/ubicación": "Perú - Lima"}, "Perú"),
        ]
        for raw, expected_country in items:
            norm = normalize_item(raw)
            self.assertEqual(norm["pais"], expected_country)

    def test_normalize_item_education_categories(self):
        cases = [
            ("Universitario (Ingeniería)", "Universitario"),
            ("CBC UBA", "Universitario"),
            ("Pre-Universitario (PAES)", "Pre-Universitario"),
            ("Secundario (4to año)", "Secundario"),
            ("FP Superior", "Terciario / FP"),
            ("Acceso mayores 25", "Acceso"),
        ]
        for lvl_str, expected_cat in cases:
            norm = normalize_item({"nivel educativo": lvl_str})
            self.assertEqual(norm["nivel_categoria"], expected_cat)

    def test_parse_json_response(self):
        # Markdown fences JSON
        md_json = '```json\n[{"id": "test1", "is_student": true, "decision_ia": "Aprobado"}]\n```'
        parsed = parse_json_response(md_json)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["id"], "test1")

        # Objeto contenedor con 'results'
        obj_json = '{"results": [{"id": "test2", "is_student": false}]}'
        parsed_obj = parse_json_response(obj_json)
        self.assertEqual(len(parsed_obj), 1)
        self.assertEqual(parsed_obj[0]["id"], "test2")

    def test_rule_based_audit_fallback(self):
        # Lead legítimo de estudiante
        student_ad = {
            "id": "lead_101",
            "mensaje": "Hola, necesito clases particulares de análisis matemático 1 para preparar final en diciembre.",
            "enlace": "https://anuncio.com/1"
        }
        res_student = rule_based_audit(student_ad)
        self.assertTrue(res_student["is_student"])
        self.assertEqual(res_student["decision_ia"], "Aprobado")

        # Oferta docente / academia comercial (debe descartarse)
        teacher_ad = {
            "id": "lead_102",
            "mensaje": "Doy clases particulares de física y química, primera clase gratis, amplia experiencia.",
            "enlace": "https://anuncio.com/2"
        }
        res_teacher = rule_based_audit(teacher_ad)
        self.assertFalse(res_teacher["is_student"])
        self.assertEqual(res_teacher["decision_ia"], "Descartado")

        # Oferta laboral docente (debe descartarse)
        recruitment_ad = {
            "id": "lead_103",
            "mensaje": "Se busca docente de matemáticas para instituto secundario en zona norte.",
            "enlace": "https://cronoshare.com/empleo/clases-particulares-matematicas"
        }
        res_recruitment = rule_based_audit(recruitment_ad)
        self.assertFalse(res_recruitment["is_student"])
        self.assertEqual(res_recruitment["decision_ia"], "Descartado")

    def test_call_multiprovider_batch_fallback_without_keys(self):
        # Si se ejecuta sin claves, debe recurrir automáticamente al motor heurístico sin arrojar excepción
        leads = [
            {"id": "t1", "mensaje": "Busco profesor de álgebra urgente", "enlace": "https://test.com/1"},
            {"id": "t2", "mensaje": "Ofrezco clases de matemáticas avanzadas", "enlace": "https://test.com/2"}
        ]
        # Forzar un entorno sin claves para la prueba
        old_keys = {}
        for k in ["GEMINI_API_KEY", "CLOUDFLARE_API_TOKEN", "GROQ_API_KEY", "MISTRAL_API_KEY"]:
            old_keys[k] = os.environ.pop(k, None)

        try:
            results = call_multiprovider_batch(leads, api_key=None)
            self.assertEqual(len(results), 2)
            self.assertEqual(results[0]["decision_ia"], "Aprobado")
            self.assertEqual(results[1]["decision_ia"], "Descartado")
        finally:
            for k, v in old_keys.items():
                if v is not None:
                    os.environ[k] = v


    def test_feedback_conversion_metrics_consistency(self):
        # Valida que los datos de telemetría y métricas de conversión del piloto sean 100% consistentes
        feedback_path = os.path.join(os.path.dirname(__file__), "..", "data", "feedback_piloto_conversion.json")
        self.assertTrue(os.path.exists(feedback_path), "feedback_piloto_conversion.json debe existir")

        import json
        with open(feedback_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        m = data["metricas_generales"]
        fp = m["fase_piloto"]
        self.assertEqual(m["total_anuncios_extraidos"], 175)
        self.assertEqual(m["total_prospectos_calificados"], 41)
        self.assertEqual(fp["contactados"] + fp["en_espera_lote_2"], 41)
        self.assertEqual(fp["convertidos_pagados"] + fp["descartados_post_contacto"] + fp["sin_respuesta_7_dias"], fp["contactados"])
        self.assertEqual(fp["respondieron"], fp["convertidos_pagados"] + fp["descartados_post_contacto"])

        # Verificar que los alumnos convertidos existen en el dataset canónico
        data_canon_path = os.path.join(os.path.dirname(__file__), "..", "data", "dataset_canonico_auditado.json")
        with open(data_canon_path, "r", encoding="utf-8") as f:
            canon = json.load(f)
        canon_ids = {r["id"] for r in canon}

        for conv in data["detalle_conversiones_exitosas"]:
            self.assertIn(conv["lead_id"], canon_ids, f"El lead convertido {conv['lead_id']} debe existir en el dataset canónico")

    def test_evaluate_filter_benchmark_metrics(self):
        # Valida que el evaluador cuantitativo de datos funcione y certifique la superioridad sobre el baseline
        from evaluate_filter import evaluate_models
        gemini_m, regex_m, total, pos, neg = evaluate_models()
        self.assertEqual(total, 175)
        self.assertEqual(pos, 41)
        self.assertEqual(neg, 134)
        self.assertGreater(gemini_m["precision"], 0.90, "La precisión del filtro semántico debe superar el 90%")
        self.assertGreater(gemini_m["recall"], 0.90, "El recall del filtro semántico debe superar el 90%")
        self.assertGreater(gemini_m["f1_score"], 0.90, "El F1-Score debe superar el 90%")
        self.assertGreater(gemini_m["precision"], regex_m["precision"], "Gemini debe superar ampliamente al baseline regex")

if __name__ == "__main__":
    unittest.main()
