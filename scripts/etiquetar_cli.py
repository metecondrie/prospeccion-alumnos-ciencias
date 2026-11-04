#!/usr/bin/env python3
"""
scripts/etiquetar_cli.py
Herramienta CLI interactiva y reanudable para el etiquetado humano ciego (blind labeling)
de muestras de anuncios de alumnos de ciencias exactas.

Toma una muestra determinista sample(n=100, seed=42) de data/extracted_listings.json,
oculta estrictamente cualquier decisión o justificación previa de IA para evitar sesgos,
y registra las anotaciones humanas en evaluation/labels_humanos.json.
"""

import os
import sys
import json
import random
import argparse
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from prospector import normalize_item
from storage import atomic_write_json, safe_read_json


def load_and_sample_listings(
    input_path: str,
    sample_size: int = 100,
    seed: int = 42
) -> List[Dict[str, Any]]:
    """Carga data/extracted_listings.json, normaliza con IDs estables y toma muestra determinista."""
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Archivo de anuncios crudos no encontrado: {input_path}")

    with open(input_path, "r", encoding="utf-8") as f:
        raw_items = json.load(f)

    # Asignar IDs normalizados y deterministas
    normalized = [normalize_item(it, idx + 1) for idx, it in enumerate(raw_items)]

    rng = random.Random(seed)
    sampled = rng.sample(normalized, min(sample_size, len(normalized)))
    return sampled


def display_blind_item(item: Dict[str, Any], current_idx: int, total_items: int) -> None:
    """Muestra los datos del anuncio SIN exhibir inferencias previas de IA."""
    print("\n" + "=" * 70)
    print(f"  ANUNCIO [{current_idx}/{total_items}] | ID: {item.get('id', 'N/A')}")
    print("=" * 70)
    print(f"🏢 Plataforma: {item.get('plataforma', 'N/A')}")
    print(f"📍 Ubicación:  {item.get('país/ubicación', item.get('pais_ubicacion', 'N/A'))}")
    print(f"📚 Materia:    {item.get('materia', 'N/A')}")
    print(f"🎓 Nivel:      {item.get('nivel educativo', item.get('nivel_educativo', 'N/A'))}")
    print(f"🔗 Enlace:     {item.get('enlace al anuncio', item.get('enlace_anuncio', 'N/A'))}")
    print("-" * 70)
    print("💬 Mensaje / Solicitud:")
    msg = item.get("mensaje/descripción") or item.get("mensaje_descripcion") or item.get("mensaje") or ""
    print(f"  {msg.strip()}")
    print("=" * 70)


def run_labeling_session(
    sample_items: List[Dict[str, Any]],
    output_path: str,
    annotator: str = "humano",
    mock_inputs: Optional[List[str]] = None
) -> int:
    """
    Ejecuta el ciclo de etiquetado CLI interactivo o mockeado.
    Retorna el número de nuevos elementos etiquetados.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    existing_labels: List[Dict[str, Any]] = safe_read_json(output_path, default=[])
    labeled_ids = {entry.get("id") for entry in existing_labels if isinstance(entry, dict) and "id" in entry}

    pending_items = [it for it in sample_items if it.get("id") not in labeled_ids]

    print("\n=======================================================")
    print("   ETIQUETADO HUMANO CIEGO - EVALUACIÓN DE CLASIFICADOR")
    print("=======================================================")
    print(f"  Total muestra objetivo:       {len(sample_items)}")
    print(f"  Previamente etiquetados:      {len(labeled_ids)}")
    print(f"  Pendientes en esta sesión:    {len(pending_items)}")
    print(f"  Destino de persistencia:      {output_path}")
    print("=======================================================\n")

    if not pending_items:
        print("✓ ¡Todos los anuncios de la muestra ya han sido etiquetados!")
        return 0

    new_count = 0
    mock_idx = 0

    for idx, item in enumerate(pending_items, 1):
        display_blind_item(item, idx, len(pending_items))

        while True:
            prompt_text = "Clasificación [1: Alumno | 0: Descartado | s: Saltear | q: Guardar y Salir]: "
            if mock_inputs is not None:
                if mock_idx < len(mock_inputs):
                    user_input = mock_inputs[mock_idx].strip().lower()
                    mock_idx += 1
                    print(f"{prompt_text}{user_input}")
                else:
                    user_input = "q"
                    print(f"{prompt_text}{user_input}")
            else:
                try:
                    user_input = input(prompt_text).strip().lower()
                except (KeyboardInterrupt, EOFError):
                    print("\n\nSesión interrumpida por el usuario. Guardando estado...")
                    user_input = "q"

            if user_input == "1":
                new_entry = {
                    "id": item["id"],
                    "label": 1,
                    "annotator": annotator,
                    "ts": datetime.now(timezone.utc).isoformat()
                }
                existing_labels.append(new_entry)
                atomic_write_json(output_path, existing_labels)
                new_count += 1
                print(f"  -> [OK] Guardado como ALUMNO (1). Total sesión: {new_count}")
                break

            elif user_input == "0":
                new_entry = {
                    "id": item["id"],
                    "label": 0,
                    "annotator": annotator,
                    "ts": datetime.now(timezone.utc).isoformat()
                }
                existing_labels.append(new_entry)
                atomic_write_json(output_path, existing_labels)
                new_count += 1
                print(f"  -> [OK] Guardado como DESCARTADO (0). Total sesión: {new_count}")
                break

            elif user_input == "s":
                print("  -> [SALTEADO] Anuncio pospuesto.")
                break

            elif user_input == "q":
                print(f"\n[SALIDA] Sesión finalizada. {new_count} nuevas etiquetas guardadas en {output_path}.")
                return new_count

            else:
                print("  [Opción no válida] Por favor ingrese 1, 0, s o q.")

    print(f"\n✓ Ronda completada. {new_count} nuevas etiquetas guardadas en {output_path}.")
    return new_count


def main():
    parser = argparse.ArgumentParser(description="CLI de Etiquetado Humano Ciego para Calidad de Datos")
    parser.add_argument(
        "--input",
        default=os.path.join(PROJECT_ROOT, "data", "extracted_listings.json"),
        help="Ruta al archivo de anuncios crudos extraídos"
    )
    parser.add_argument(
        "--output",
        default=os.path.join(PROJECT_ROOT, "evaluation", "labels_humanos.json"),
        help="Ruta al archivo JSON de persistencia de etiquetas humanas"
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=100,
        help="Tamaño de la muestra determinista (default: 100)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Semilla aleatoria determinista (default: 42)"
    )
    parser.add_argument(
        "--annotator",
        default="humano",
        help="Identificador del anotador (default: humano)"
    )
    parser.add_argument(
        "--mock-inputs",
        nargs="*",
        default=None,
        help="Entradas simuladas para pruebas automatizadas (ej: 1 0 s q)"
    )

    args = parser.parse_args()

    sample = load_and_sample_listings(args.input, sample_size=args.sample_size, seed=args.seed)
    run_labeling_session(
        sample,
        output_path=args.output,
        annotator=args.annotator,
        mock_inputs=args.mock_inputs
    )


if __name__ == "__main__":
    main()
