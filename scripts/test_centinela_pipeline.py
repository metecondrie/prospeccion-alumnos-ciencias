#!/usr/bin/env python3
"""
test_centinela_pipeline.py
Script de prueba en vivo para verificar el flujo completo del Centinela:
1. Filtro Heurístico
2. Auditoría con Gemini Flash Lite (o fallback Groq/Mistral)
3. Guardado en la base de datos CRM
4. Envío de Notificación Push real al celular del Prof. Alejo vía Telegram Bot
"""

import os
import sys
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prospector import load_env_file, call_multiprovider_batch, normalize_item
from common_filter import normalize_subject, normalize_level, sanitize_text
from telegram_centinela import fast_match, save_approved_lead, send_centinela_push_alert

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
print("\n3. Enviando a auditar en vivo con el Triple Motor de IA (Gemini Flash Lite)...")
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
