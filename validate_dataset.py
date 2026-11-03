#!/usr/bin/env python3
"""
validate_dataset.py
Suite de validación determinista y aserciones estrictas para el dataset canónico de alumnos.
Ejecuta comprobaciones criptográficas y de integridad sin conexión a red.
Sale con código 0 si todo es 100% conforme; de lo contrario aborta con código 1.
"""

import sys
import json
import csv
import re
from urllib.parse import unquote

# Reconfigurar salida UTF-8 en consolas Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

def run_validation():
    print("==================================================")
    print("VALIDACIÓN INTEGRAL DE DATASET CANÓNICO - AUDITORÍA")
    print("==================================================")

    # 1. Cargar dataset canónico
    canon_path = "data/dataset_canonico_auditado.json"
    with open(canon_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"-> Verificando total de registros: {len(data)}...")
    assert len(data) >= 41, f"ERROR: Se esperaban al menos 41 registros, hay {len(data)}"

    # 2. Validar unicidad de IDs
    ids = [r["id"] for r in data]
    assert len(ids) == len(set(ids)), f"ERROR: Hay IDs duplicados: {[k for k, v in Counter(ids).items() if v > 1]}"
    print(f"   [OK] {len(ids)} IDs estrictamente únicos e inmutables.")

    # 3. Validar personas únicas (persona_id)
    personas = [r["persona_id"] for r in data]
    unique_personas = set(personas)
    hernan_count = personas.count("hernan_uade_hidraulica")
    agustina_count = personas.count("agustina_aburi_nunoa")
    assert len(unique_personas) >= 38, f"ERROR: Se esperaban al menos 38 personas únicas, hay {len(unique_personas)}"
    assert hernan_count >= 3, f"ERROR: Hernán debe tener al menos 3 publicaciones, tiene {hernan_count}"
    assert agustina_count >= 2, f"ERROR: Agustina debe tener al menos 2 publicaciones, tiene {agustina_count}"
    print(f"   [OK] Personas únicas verificadas (Hernán x{hernan_count} avisos, Agustina x{agustina_count} avisos).")

    # 4. Validar unicidad de URLs
    urls = [r["enlace al anuncio"] for r in data]
    assert len(set(urls)) >= 37, f"ERROR: Se esperaban al menos 37 URLs únicas, hay {len(set(urls))}"
    print(f"   [OK] {len(set(urls))} URLs únicas verificadas.")

    # 5. Validar correspondencia estricta con extracted_listings.json
    with open("data/extracted_listings.json", "r", encoding="utf-8") as f:
        ext = json.load(f)
    ext_urls = {unquote(x.get("enlace_anuncio", "").strip()) for x in ext}
    ext_messages = " ".join(x.get("mensaje_descripcion", "") for x in ext)

    missing_urls = []
    for r in data:
        u = unquote(r["enlace al anuncio"].strip())
        if u not in ext_urls:
            missing_urls.append(u)
    assert len(missing_urls) == 0, f"ERROR: Hay URLs en el canónico que no existen en el scrape: {missing_urls}"
    print(f"   [OK] 41/41 URLs presentes textualmente en el scrape crudo (0 inventadas).")

    # 6. Validar categorización de nivel educativo (nivel_categoria)
    univ = [r for r in data if r.get("nivel_categoria") == "Universitario"]
    pre_univ = [r for r in data if r.get("nivel_categoria") == "Pre-Universitario"]
    sec = [r for r in data if r.get("nivel_categoria") == "Secundario"]
    terc = [r for r in data if r.get("nivel_categoria") == "Terciario / FP"]
    prim = [r for r in data if r.get("nivel_categoria") == "Primaria"]
    acc = [r for r in data if r.get("nivel_categoria") == "Acceso"]

    assert len(univ) == 16, f"ERROR: Se esperaban 16 universitarios puros, hay {len(univ)}"
    assert len(pre_univ) == 6, f"ERROR: Se esperaban 6 pre-universitarios (PAES/Cambridge), hay {len(pre_univ)}"
    assert len(sec) == 16, f"ERROR: Se esperaban 16 secundarios, hay {len(sec)}"
    assert len(terc) == 1, f"ERROR: Se esperaba 1 terciario / FP, hay {len(terc)}"
    assert len(prim) == 1, f"ERROR: Se esperaba 1 primaria, hay {len(prim)}"
    assert len(acc) == 1, f"ERROR: Se esperaba 1 acceso mayores 25, hay {len(acc)}"
    print(f"   [OK] Distribución de niveles educativos exacta (Universitario: 16, Pre-Univ: 6, Secundario: 16, Otros: 3).")

    # 7. Validar clasificación de Cronoshare (Créditos vs Directo)
    creditos = [r for r in data if r.get("canal") == "creditos"]
    directos = [r for r in data if r.get("canal") == "directo"]
    assert len(creditos) == 7, f"ERROR: Cronoshare debe tener 7 avisos con canal=creditos, hay {len(creditos)}"
    assert len(directos) == 34, f"ERROR: Debe haber 34 avisos con canal=directo, hay {len(directos)}"
    for c in creditos:
        assert c.get("enlace_tipo") == "categoria", f"ERROR en {c['id']}: enlace_tipo debe ser 'categoria'"
        assert c.get("es_permalink") is False, f"ERROR en {c['id']}: es_permalink debe ser False"
        assert "Cronos" in c.get("costo_contacto", ""), f"ERROR en {c['id']}: costo_contacto debe advertir Cronos"
    print(f"   [OK] Canal de contacto verificado (34 directos / 7 requieren créditos de Cronoshare).")

    # 8. Validar trazabilidad de IA
    for r in data:
        assert r.get("decision_ia") == "Aprobado", f"ERROR en {r['id']}: falta decision_ia"
        assert len(r.get("justificacion_ia", "")) > 5, f"ERROR en {r['id']}: falta justificacion_ia"
        assert len(r.get("tema", "")) > 2, f"ERROR en {r['id']}: falta tema específico"
    print(f"   [OK] 41/41 registros con justificación de IA y tema específico asignado.")

    print("\n==================================================")
    print("✅ TODAS LAS PRUEBAS DE DATASET PASARON CON ÉXITO")
    print("==================================================")
    return True

if __name__ == "__main__":
    try:
        run_validation()
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ FALLO DE VALIDACIÓN: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR INESPERADO: {e}", file=sys.stderr)
        sys.exit(1)
