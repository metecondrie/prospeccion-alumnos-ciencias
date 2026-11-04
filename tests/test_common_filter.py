import unittest
from datetime import date, timedelta
import sys
import os

# Add scripts directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))

from common_filter import (
    classify_intent,
    normalize_subject,
    normalize_level,
    parse_date,
    sanitize_text,
    validate_listing_record,
    VALID_SUBJECTS,
    VALID_LEVELS
)

class TestCommonFilter(unittest.TestCase):

    def test_teacher_blacklist_filtering(self):
        # Teacher offers must be strictly rejected
        teacher_phrases = [
            "Doy clases de matemáticas y física a domicilio y online",
            "Ofrezco clases particulares de química orgánica, primera clase gratis",
            "Profesor con amplia experiencia imparte clases de análisis matemático",
            "Licenciada ofrece apoyo escolar y preparación de exámenes",
            "Tarifa: 15€/hora, metodología propia y excelentes resultados",
            "Profesora con experiencia en física y química para todos los niveles",
            "Mis tarifas son accesibles, enseño a estudiantes de secundaria",
        ]
        for phrase in teacher_phrases:
            is_student, reason = classify_intent(phrase)
            self.assertFalse(is_student, f"Expected reject for teacher phrase: '{phrase}' (got: {reason})")

    def test_student_whitelist_filtering(self):
        # Genuine student requests must be accepted
        student_phrases = [
            "Busco profesor de matemáticas para preparar examen final de cálculo",
            "Necesito profesora de física para 2º de bachillerato",
            "Estoy cursando álgebra en la facultad y necesito ayuda con matrices",
            "Busco a alguien que me enseñe análisis matemático para el CBC",
            "Necesito recibir clases de apoyo de mate en 2 de la ESO",
            "Se busca profesor de química orgánica para rendir parcial",
            "Voy a rendir biofísica en la UBA y me cuesta entender termodinámica",
        ]
        for phrase in student_phrases:
            is_student, reason = classify_intent(phrase)
            self.assertTrue(is_student, f"Expected accept for student phrase: '{phrase}' (got: {reason})")

    def test_subject_normalization(self):
        self.assertEqual(normalize_subject("Clases de análisis matemático y álgebra"), "Matemáticas")
        self.assertEqual(normalize_subject("Apoyo en cinemática y dinámica"), "Física")
        self.assertEqual(normalize_subject("Necesito ayuda con química orgánica y estequiometría"), "Química")
        self.assertEqual(normalize_subject("Tutor para biología celular y genética"), "Biología")
        # Compound subjects
        self.assertEqual(normalize_subject("Clases de física y química para bachillerato"), "Física, Química")
        self.assertEqual(normalize_subject("Refuerzo en matemáticas, física y química"), "Matemáticas, Física, Química")
        # Non-exact sciences should return None
        self.assertIsNone(normalize_subject("Clases particulares de inglés y francés"))
        self.assertIsNone(normalize_subject("Aprender a programar en Python y desarrollo web"))
        self.assertIsNone(normalize_subject("Clases de historia del arte y literatura"))

    def test_level_normalization(self):
        self.assertEqual(normalize_level("Alumno de 2º de la ESO necesita profesor"), "Secundario")
        self.assertEqual(normalize_level("Preparación para selectividad / EBAU"), "Secundario")
        self.assertEqual(normalize_level("Estudiante de 1º de bachillerato"), "Secundario")
        self.assertEqual(normalize_level("Tercer año de secundaria"), "Secundario")
        self.assertEqual(normalize_level("Preparatoria UNAM segundo semestre"), "Secundario")
        self.assertEqual(normalize_level("Análisis Matemático I en la Facultad de Ingeniería"), "Universitario")
        self.assertEqual(normalize_level("Preparando el CBC de la UBA"), "Universitario")
        self.assertEqual(normalize_level("Grado en Biotecnología primer año"), "Universitario")
        self.assertEqual(normalize_level("Licenciatura en Química UBA"), "Universitario")
        self.assertEqual(normalize_level("Eso, para química 005 uba xxi"), "Universitario")

    def test_date_parsing(self):
        today = date.today()
        # ISO format
        self.assertEqual(parse_date("2026-10-15"), "2026-10-15")
        # Slash format
        self.assertEqual(parse_date("30/10/2026"), "2026-10-30")
        # Spanish textual date
        self.assertEqual(parse_date("28 de octubre de 2026"), "2026-10-28")
        # Relative date
        expected_2_days_ago = (today - timedelta(days=2)).isoformat()
        self.assertEqual(parse_date("hace 2 días"), expected_2_days_ago)
        # Future date capping
        future_str = (today + timedelta(days=5)).isoformat()
        self.assertEqual(parse_date(future_str), today.isoformat())

    def test_record_validation(self):
        valid_record = {
            "plataforma": "Tablón de Anuncios",
            "enlace_anuncio": "https://www.tablondeanuncios.com/clases-particulares/demanda-ciencias-demo.htm",
            "materia": "Matemáticas",
            "nivel_educativo": "Secundario",
            "pais_ubicacion": "España - Lakuntza (Navarra)",
            "fecha_publicacion": "2026-10-30",
            "mensaje_descripcion": "Necesito recibir clases de apoyo de mate en 2 de la ESO.",
            "metodo_contacto_directo": "Formulario web directo en Tablón de Anuncios (botón 'Contactar')"
        }
        is_valid, msg = validate_listing_record(valid_record)
        self.assertTrue(is_valid, f"Validation failed: {msg}")

        # Invalid: missing field
        invalid_rec = dict(valid_record)
        del invalid_rec["materia"]
        is_valid, msg = validate_listing_record(invalid_rec)
        self.assertFalse(is_valid)

        # Invalid: non-canonical subject
        invalid_subj = dict(valid_record, materia="Inglés")
        is_valid, msg = validate_listing_record(invalid_subj)
        self.assertFalse(is_valid)

        # Invalid: non-canonical level
        invalid_lvl = dict(valid_record, nivel_educativo="Primario")
        is_valid, msg = validate_listing_record(invalid_lvl)
        self.assertFalse(is_valid)

if __name__ == "__main__":
    unittest.main()
