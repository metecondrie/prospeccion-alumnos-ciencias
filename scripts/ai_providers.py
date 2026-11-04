#!/usr/bin/env python3
"""
ai_providers.py
Módulo de integración con proveedores de Inteligencia Artificial para auditoría semántica.
Soporta:
1. Google AI Studio (Google Gemini 3.5 Flash / Gemini 3.6 Flash)
2. Cloudflare Workers AI (Llama 3.1 8B Instruct Fast)
3. Groq (Llama 3.1 8B Instant / Llama 3.3 70B Versatile)
4. Mistral AI (Mistral Small Latest)
5. Clasificador heurístico determinista local (Fallback offline sin costo)
"""

import os
import sys
import json
import re
import time
import unicodedata
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional, Callable

class RateLimitError(Exception):
    """Excepción cuando se recibe HTTP 429 de la API de Google."""
    pass

DEFAULT_MODELS = ["gemini-3.5-flash", "gemini-3.6-flash"]
OBSOLETE_MODELS = {
    "gemini-2.5-flash",
    "gemini-2.5",
    "gemini-1.5-flash",
    "gemini-1.0-pro"
}

def strip_accents(text: str) -> str:
    """Elimina diacríticos y acentos para comparaciones robustas."""
    return "".join(
        c for c in unicodedata.normalize("NFD", str(text or ""))
        if unicodedata.category(c) != "Mn"
    ).lower()

def get_audit_prompt(items: List[Dict[str, Any]]) -> str:
    """Genera el prompt canónico de auditoría para cualquier proveedor de IA."""
    return f"""Eres un auditor estricto de anuncios clasificados educativos para un profesor particular de ciencias exactas.
Tu objetivo es discriminar con rigor si cada anuncio fue escrito por un ESTUDIANTE o PADRE REAL buscando contratar clases particulares (is_student: true), o si por el contrario es un INSTITUTO, ACADEMIA, OFERTA LABORAL o PROFESOR OFRECIENDO CLASES (is_student: false).

CRITERIOS ESTRICTOS DE EXCLUSIÓN (is_student: false):
- Si es una academia, instituto o colegio buscando profesores (ej. 'se busca docente', 'necesitamos profesor').
- Si es una oferta de trabajo/empleo para profesores (ej. vacantes, 'oferta de trabajo').
- Si es un profesor particular ofreciendo sus servicios (ej. 'Doy clases particulares', 'Profesor con 10 años de experiencia').
- Si el texto está mezclado con menús web o índices de navegación por provincias/asignaturas.

CRITERIOS DE INCLUSIÓN (is_student: true):
- Estudiante que dice 'necesito clases', 'busco profesor', 'preparar examen de álgebra / análisis / física / biofísica', 'apoyo escolar', etc.
- Padre/madre buscando tutor para su hijo/a.

Evalúa esta lista de anuncios:
{json.dumps(items, ensure_ascii=False, indent=2)}

Devuelve estrictamente un JSON válido con esta estructura:
[
  {{
    "id": "identificador_del_anuncio",
    "is_student": true,
    "decision_ia": "Aprobado" | "Descartado",
    "justificacion_ia": "Explicación concisa y clara del motivo de la decisión"
  }}
]"""

def parse_json_response(raw: str) -> List[Dict[str, Any]]:
    """Limpia markdown y extrae la lista de resultados JSON de cualquier modelo LLM."""
    raw_clean = str(raw or "").strip()
    if raw_clean.startswith("```"):
        raw_clean = re.sub(r"^```(?:json)?\s*", "", raw_clean)
        raw_clean = re.sub(r"\s*```$", "", raw_clean)
    parsed = json.loads(raw_clean)
    if isinstance(parsed, dict):
        for k in ("results", "data", "items", "anuncios", "evaluaciones", "evaluacion"):
            if k in parsed and isinstance(parsed[k], list):
                return parsed[k]
        if "id" in parsed or "decision_ia" in parsed or "is_student" in parsed:
            return [parsed]
    if isinstance(parsed, list):
        return parsed
    raise ValueError(f"La respuesta no contiene una lista JSON de anuncios evaluados: {raw_clean[:120]}")

def call_gemini_batch(items: List[Dict[str, Any]], model: str = "gemini-3.5-flash", api_key: str = None, max_retries: int = 3) -> List[Dict[str, Any]]:
    """Evalúa un lote de anuncios con modelos de Google AI Studio (responseMimeType: application/json)."""
    PROVIDER_REGISTRY.validate_model(model)
    if not api_key:
        api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY no encontrada.")

    models_to_try = [model] + [m for m in DEFAULT_MODELS if m != model]
    prompt = get_audit_prompt(items)
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"}
    }).encode("utf-8")

    last_error = None
    for target_model in models_to_try:
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent"
        for attempt in range(1, max_retries + 1):
            req = urllib.request.Request(
                endpoint,
                data=payload,
                headers={"Content-Type": "application/json", "x-goog-api-key": api_key}
            )
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    raw_text = resp_data["candidates"][0]["content"]["parts"][0]["text"]
                    results = parse_json_response(raw_text)
                    for r in results:
                        if isinstance(r, dict):
                            r["actual_provider"] = "Google Gemini"
                            r["actual_model"] = target_model
                            r["provider"] = "Google Gemini"
                            r["modelo"] = target_model
                    return results
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="replace")
                if e.code == 429:
                    backoff = attempt * 2.5
                    print(f"    [RateLimit 429] Gemini {target_model} saturado. Reintentando en {backoff}s...", file=sys.stderr)
                    time.sleep(backoff)
                    last_error = RateLimitError(f"HTTP 429: {err_body}")
                elif e.code == 404:
                    last_error = e
                    break
                elif e.code in (500, 502, 503, 504):
                    time.sleep(attempt * 2.0)
                    last_error = e
                else:
                    last_error = e
                    break
            except Exception as e:
                last_error = e
                time.sleep(1.5)

    raise RuntimeError(f"Fallo en Gemini ({last_error})")

def call_cloudflare_batch(items: List[Dict[str, Any]], account_id: str, api_token: str, model: str = "@cf/meta/llama-3.1-8b-instruct-fp8-fast", max_retries: int = 2) -> List[Dict[str, Any]]:
    """Suplente 1: Evalúa lote con Cloudflare Workers AI (10.000 neuronas/día gratis)."""
    PROVIDER_REGISTRY.validate_model(model)
    prompt = get_audit_prompt(items)
    endpoint = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1/chat/completions"
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": "Eres un auditor estricto de anuncios educativos. Responde estrictamente con un JSON válido."},
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"}
    }).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=payload,
        headers={"Authorization": f"Bearer {api_token}", "Content-Type": "application/json", "User-Agent": "ProspeccionAlumnos/1.0"}
    )
    for attempt in range(1, max_retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                raw_text = data["choices"][0]["message"]["content"]
                results = parse_json_response(raw_text)
                for r in results:
                    if isinstance(r, dict):
                        r["actual_provider"] = "Cloudflare Workers AI"
                        r["actual_model"] = model
                        r["provider"] = "Cloudflare Workers AI"
                        r["modelo"] = model
                return results
        except Exception as e:
            if attempt == max_retries:
                raise e
            time.sleep(1.5)

def call_groq_batch(items: List[Dict[str, Any]], api_key: str, model: str = "llama-3.1-8b-instant", max_retries: int = 2) -> List[Dict[str, Any]]:
    """Suplente 2: Evalúa lote con Groq (inferencia ultra-rápida, compatible con OpenAI)."""
    PROVIDER_REGISTRY.validate_model(model)
    prompt = get_audit_prompt(items)
    endpoint = "https://api.groq.com/openai/v1/chat/completions"
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": "Eres un auditor estricto de anuncios educativos. Responde estrictamente con un JSON válido."},
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.1
    }).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "User-Agent": "ProspeccionAlumnos/1.0"}
    )
    for attempt in range(1, max_retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                raw_text = data["choices"][0]["message"]["content"]
                time.sleep(10.0)  # Pausa preventiva para respetar 8K TPM de Groq
                results = parse_json_response(raw_text)
                for r in results:
                    if isinstance(r, dict):
                        r["actual_provider"] = "Groq"
                        r["actual_model"] = model
                        r["provider"] = "Groq"
                        r["modelo"] = model
                return results
        except urllib.error.HTTPError as e:
            if e.code == 429 and model != "llama-3.3-70b-versatile":
                return call_groq_batch(items, api_key, model="llama-3.3-70b-versatile", max_retries=1)
            if attempt == max_retries:
                raise e
            time.sleep(attempt * 3.0)
        except Exception as e:
            if attempt == max_retries:
                raise e
            time.sleep(2.0)

def call_mistral_batch(items: List[Dict[str, Any]], api_key: str, model: str = "mistral-small-latest", max_retries: int = 2) -> List[Dict[str, Any]]:
    """Suplente 3: Evalúa lote con Mistral AI (alta fidelidad léxica en español)."""
    PROVIDER_REGISTRY.validate_model(model)
    prompt = get_audit_prompt(items)
    endpoint = "https://api.mistral.ai/v1/chat/completions"
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": "Eres un auditor estricto de anuncios educativos. Responde estrictamente con un JSON válido."},
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.1
    }).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "User-Agent": "ProspeccionAlumnos/1.0"}
    )
    for attempt in range(1, max_retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                raw_text = data["choices"][0]["message"]["content"]
                time.sleep(1.0)
                results = parse_json_response(raw_text)
                for r in results:
                    if isinstance(r, dict):
                        r["actual_provider"] = "Mistral AI"
                        r["actual_model"] = model
                        r["provider"] = "Mistral AI"
                        r["modelo"] = model
                return results
        except Exception as e:
            if attempt == max_retries:
                raise e
            time.sleep(2.0)

def rule_based_audit(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Clasificador heurístico determinista de respaldo (Fallback sin conexión / sin API key).
    Evalúa patrones léxicos de intenciones educativas sin requerir inferencia LLM externa.
    """
    msg = strip_accents(str(item.get("mensaje", "") or item.get("mensaje/descripción", "")))
    url = str(item.get("enlace", "") or item.get("enlace al anuncio", "")).lower()

    # Patrones de exclusión (docentes, ofertas de trabajo, academias)
    teacher_patterns = [
        r"\bdoy clases\b", r"\bofrezco clases\b", r"\bimparto clases\b",
        r"\bprimera clase gratis\b", r"\bprofesor con \d+\b", r"\bdocente con experiencia\b",
        r"\bse busca docente\b", r"\bbuscamos profesor\b", r"\boferta de trabajo\b",
        r"\bvacante\b", r"\bacaddemia\b", r"\bcolegio\b", r"\binstituto\b",
        r"/empleo/", r"estudiantes/ingles/"
    ]
    is_teacher = any(re.search(pat, msg) for pat in teacher_patterns) or "/empleo/" in url

    # Patrones de inclusión (estudiantes / familias buscando profesor)
    student_patterns = [
        r"\bnecesito clases\b", r"\bnecesito profesor\b", r"\bnecesito profe\b",
        r"\bbusco profesor\b", r"\bbusco docente\b", r"\bbusco clases\b",
        r"\bclases particulares de\b", r"\bpreparar examen\b", r"\bpreparar final\b",
        r"\bapoyo escolar\b", r"\bsoy alumno\b", r"\bsoy estudiante\b",
        r"\bestoy cursando\b", r"\bpara mi hij[oa]\b", r"\bapoyo en\b", r"\bayuda con\b"
    ]
    is_student = any(re.search(pat, msg) for pat in student_patterns)

    item_id = item.get("id", "item")
    if is_teacher:
        return {
            "id": item_id,
            "is_student": False,
            "decision_ia": "Descartado",
            "justificacion_ia": "Descartado por regla heurística: detectado patrón de docente, oferta de empleo o academia comercial.",
            "actual_provider": "Heuristic",
            "actual_model": "deterministic-rules",
            "provider": "Heuristic",
            "modelo": "deterministic-rules"
        }
    elif is_student:
        return {
            "id": item_id,
            "is_student": True,
            "decision_ia": "Aprobado",
            "justificacion_ia": "Aprobado por regla heurística: detectada demanda genuina de estudiante o padre buscando profesor particular.",
            "actual_provider": "Heuristic",
            "actual_model": "deterministic-rules",
            "provider": "Heuristic",
            "modelo": "deterministic-rules"
        }
    else:
        return {
            "id": item_id,
            "is_student": False,
            "decision_ia": "Descartado",
            "justificacion_ia": "Descartado por regla heurística: el mensaje no contiene demanda explícita de contratación de clases de ciencias exactas.",
            "actual_provider": "Heuristic",
            "actual_model": "deterministic-rules",
            "provider": "Heuristic",
            "modelo": "deterministic-rules"
        }


class ProviderConfig:
    """Configuración descriptiva de un proveedor en el registro unificado."""
    def __init__(
        self,
        name: str,
        default_model: str,
        supported_models: List[str],
        priority: int
    ):
        self.name = name
        self.default_model = default_model
        self.supported_models = supported_models
        self.priority = priority


class ProviderRegistry:
    """
    Registro canónico unificado de proveedores de Inteligencia Artificial.
    Administra la validación de modelos, la conmutación en caso de fallo (failover)
    y el registro riguroso del proveedor y modelo efectivo utilizado en cada inferencia.
    """
    def __init__(self):
        self._providers: Dict[str, ProviderConfig] = {}
        self._register_defaults()

    def _register_defaults(self):
        self.register(ProviderConfig("Google Gemini", "gemini-3.5-flash", ["gemini-3.5-flash", "gemini-3.6-flash"], priority=1))
        self.register(ProviderConfig("Cloudflare Workers AI", "@cf/meta/llama-3.1-8b-instruct-fp8-fast", ["@cf/meta/llama-3.1-8b-instruct-fp8-fast", "@cf/meta/llama-3.1-8b-instruct"], priority=2))
        self.register(ProviderConfig("Groq", "llama-3.1-8b-instant", ["llama-3.1-8b-instant", "llama-3.3-70b-versatile"], priority=3))
        self.register(ProviderConfig("Mistral AI", "mistral-small-latest", ["mistral-small-latest", "open-mistral-7b"], priority=4))
        self.register(ProviderConfig("Heuristic", "deterministic-rules", ["deterministic-rules", "heuristic"], priority=5))

    def register(self, config: ProviderConfig) -> None:
        self._providers[config.name] = config

    def get(self, name: str) -> Optional[ProviderConfig]:
        return self._providers.get(name)

    def list_providers(self) -> List[ProviderConfig]:
        return sorted(self._providers.values(), key=lambda p: p.priority)

    def validate_model(self, model: str) -> str:
        """Valida que el modelo no pertenezca a versiones deprecadas u obsoletas."""
        if not model:
            return "gemini-3.5-flash"
        m_clean = model.strip().lower()
        if m_clean in OBSOLETE_MODELS:
            raise ValueError(
                f"El modelo '{model}' ha sido revocado y declarado OBSOLETO. "
                f"Utilice 'gemini-3.5-flash' o 'gemini-3.6-flash'."
            )
        return model

    def dispatch(
        self,
        items: List[Dict[str, Any]],
        primary_model: str = "gemini-3.5-flash",
        api_key: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Ejecuta la auditoría en lote contra la cadena de proveedores activos.
        Estampa actual_provider y actual_model en cada registro evaluado y emite log unificado.
        """
        valid_model = self.validate_model(primary_model)
        if valid_model == "heuristic":
            return [rule_based_audit(it) for it in items]

        # Cadena activa de proveedores configurados
        active_chain = []
        g_key = api_key or os.environ.get("GEMINI_API_KEY")
        if g_key:
            active_chain.append(("Google Gemini", lambda it: call_gemini_batch(it, model=valid_model, api_key=g_key), valid_model))

        cf_acc = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
        cf_tok = os.environ.get("CLOUDFLARE_API_TOKEN")
        if cf_acc and cf_tok:
            active_chain.append(("Cloudflare Workers AI", lambda it: call_cloudflare_batch(it, cf_acc, cf_tok), "@cf/meta/llama-3.1-8b-instruct-fp8-fast"))

        groq_k = os.environ.get("GROQ_API_KEY")
        if groq_k:
            active_chain.append(("Groq", lambda it: call_groq_batch(it, groq_k), "llama-3.1-8b-instant"))

        mis_k = os.environ.get("MISTRAL_API_KEY")
        if mis_k:
            active_chain.append(("Mistral AI", lambda it: call_mistral_batch(it, mis_k), "mistral-small-latest"))

        if not active_chain:
            print("    [Aviso] No se detectaron claves de API de IA. Activando motor de auditoría heurística determinista...")
            return [rule_based_audit(it) for it in items]

        errors = []
        for prov_name, prov_fn, model_used in active_chain:
            try:
                results = prov_fn(items)
                if results and isinstance(results, list):
                    print(f"    [IA OK] Lote resuelto por proveedor='{prov_name}' con modelo='{model_used}'")
                    for r in results:
                        if isinstance(r, dict):
                            r["actual_provider"] = prov_name
                            r["actual_model"] = model_used
                            r["provider"] = prov_name
                            r["modelo"] = model_used
                    return results
            except Exception as e:
                print(f"    [Failover] {prov_name} falló ({e}). Conmutando al siguiente proveedor...", file=sys.stderr)
                errors.append((prov_name, str(e)))

        print("    [Fallback] Todos los proveedores externos fallaron. Activando motor de auditoría heurística determinista...")
        return [rule_based_audit(it) for it in items]


# Instancia única canónica del registro de proveedores
PROVIDER_REGISTRY = ProviderRegistry()


def call_multiprovider_batch(items: List[Dict[str, Any]], primary_model: str = "gemini-3.5-flash", api_key: str = None) -> List[Dict[str, Any]]:
    """
    Despachador multiproveedor con failover automático en cascada gobernado por PROVIDER_REGISTRY.
    """
    return PROVIDER_REGISTRY.dispatch(items, primary_model=primary_model, api_key=api_key)
