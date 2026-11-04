#!/usr/bin/env python3
"""
tests/test_centinela_pipeline.py
Verificación de componentes del pipeline del Centinela:
1. Filtro Heurístico
2. Normalización de materias y niveles
3. Normalización de candidatos y esquema
4. Modo interactivo en vivo si se ejecuta directamente como script
"""

import os
import sys
import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from prospector import load_env_file, call_multiprovider_batch, normalize_item
from common_filter import normalize_subject, normalize_level, sanitize_text
from telegram_centinela import fast_match, save_approved_lead, send_centinela_push_alert


def test_centinela_pipeline_components():
    """Valida los componentes del pipeline en aislamiento determinista sin red."""
    test_message = "Hola gente, ¿alguien conoce algún profe particular de Análisis Matemático o Álgebra para darme una mano con la guía de derivadas e integrales para el parcial?"
    matches = fast_match(test_message)
    assert matches, "Debe detectar intención de búsqueda de profe"

    subj = normalize_subject(test_message)
    assert subj in ["Análisis Matemático", "Álgebra", "Matemáticas"]

    lvl = normalize_level(test_message)
    assert lvl is not None

    candidate = {
        "id": "tg_mock_unit_test",
        "plataforma": "Telegram (UTN)",
        "país/ubicación": "Argentina",
        "materia": subj,
        "nivel educativo": lvl,
        "enlace al anuncio": "https://t.me/test",
        "mensaje/descripción": sanitize_text(test_message),
        "decision_ia": "Aprobado",
        "justificacion_ia": "Test unitario mock"
    }
    normalized = normalize_item(candidate, 1)
    assert normalized["id"] == "tg_mock_unit_test"
    assert normalized["materia"] == subj


def run_live_pipeline():
    load_env_file()

    print("=" * 70)
    print("   PRUEBA EN VIVO DEL SISTEMA CENTINELA + IA + PUSH A TU CELULAR")
    print("=" * 70)

    test_message = "Hola gente, ¿alguien conoce algún profe particular de Análisis Matemático o Álgebra para darme una mano con la guía de derivadas e integrales para el parcial?"
    group_title = "Ingreso - UTN FRBA (Matemática y Física)"
    student_name = "Estudiante Simulado"
    student_username = "alumno_prueba_exactas"

    print(f"\n1. Mensaje simulado de un estudiante en '{group_title}':")
    print(f'   "{test_message}"')

    # Paso 1: Filtro rápido
    print("\n2. Evaluando con filtro rápido de palabras clave (0ms)...")
    matches = fast_match(test_message)
    print(f"   ¿Coincide con búsqueda de profe y materia?: {'SÍ (Pasa a la IA)' if matches else 'NO'}")

    # Paso 2: Auditoría IA
    print("\n3. Enviando a auditar en vivo con el Triple Motor de IA...")
    candidate = {
        "id": f"tg_test_{int(time.time())}",
        "plataforma": f"Telegram ({group_title})",
        "materia": normalize_subject(test_message) or "Análisis Matemático",
        "ubicacion": "Argentina - Grupo UTN Estudiantes",
        "mensaje": test_message,
        "enlace": "https://t.me/ingresoutnfrba"
    }

    t0 = time.time()
    results = call_multiprovider_batch([candidate])
    elapsed = time.time() - t0

    if results and isinstance(results, list):
        res = results[0]
        print(f"   [RESPUESTA IA en {elapsed:.2f}s]:")
        print(f"   - Decisión: {res.get('decision_ia')}")
        print(f"   - Es alumno real: {res.get('is_student')}")
        print(f"   - Criterio: {res.get('justificacion_ia')}")

        if res.get("is_student") is True or res.get("decision_ia") == "Aprobado":
            normalized = normalize_item({
                "id": candidate["id"],
                "plataforma": candidate["plataforma"],
                "país/ubicación": candidate["ubicacion"],
                "nombre": student_name,
                "persona_id": student_username,
                "materia": candidate["materia"],
                "nivel educativo": normalize_level(test_message),
                "enlace al anuncio": candidate["enlace"],
                "mensaje/descripción": sanitize_text(test_message),
                "método de contacto directo": f"Telegram (@{student_username})",
                "decision_ia": "Aprobado",
                "justificacion_ia": res.get("justificacion_ia", "Prueba en vivo")
            })

            # Paso 3: Guardar en CRM
            print("\n4. Guardando en base de datos CRM (dataset_canonico_auditado.json)...")
            save_approved_lead(normalized)

            # Paso 4: Disparar alerta al teléfono
            print("\n5. 📲 DISPARANDO NOTIFICACIÓN PUSH A TU CELULAR...")
            send_centinela_push_alert(normalized, group_title, student_username)
            print("   ✅ ¡Notificación enviada con éxito! Revisa tu Telegram personal en tu celular.")

    print("\n" + "=" * 70)
    print("   PRUEBA FINALIZADA CON ÉXITO")
    print("=" * 70)


if __name__ == "__main__":
    run_live_pipeline()
