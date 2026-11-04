#!/usr/bin/env python3
"""
storage.py
Capa de almacenamiento seguro, concurrente y atómico para el sistema de prospección.
Garantiza persistencia ACID en archivos JSON/CSV, protección contra escrituras
simultáneas entre procesos (FileLock) y preservación del historial comercial del CRM.
"""

import os
import sys
import json
import time
import shutil
import hashlib
from pathlib import Path
from contextlib import contextmanager
from typing import Any, Callable, Dict, List, Optional

# Directorio raíz del proyecto
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class FileLock:
    """
    Bloqueo de archivo cross-platform con timeout y recuperación ante bloqueos huérfanos.
    Evita colisiones cuando múltiples procesos (ej. Centinela y Scraper) escriben al mismo tiempo.
    """
    def __init__(self, lock_path: str, timeout: float = 10.0, poll_interval: float = 0.05):
        self.lock_path = lock_path
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.fd: Optional[int] = None

    def __enter__(self):
        start_time = time.time()
        lock_dir = os.path.dirname(self.lock_path)
        if lock_dir:
            os.makedirs(lock_dir, exist_ok=True)

        while True:
            try:
                # O_CREAT | O_EXCL garantiza atomicidad a nivel del kernel del SO
                self.fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_RDWR)
                # Escribir PID del proceso titular
                os.write(self.fd, f"{os.getpid()}:{time.time()}".encode("utf-8"))
                return self
            except OSError:
                # Comprobar si el lock está huérfano (más viejo que el timeout)
                if os.path.exists(self.lock_path):
                    try:
                        mtime = os.path.getmtime(self.lock_path)
                        if time.time() - mtime > self.timeout * 2:
                            # Romper lock muerto
                            try:
                                os.remove(self.lock_path)
                            except OSError:
                                pass
                    except OSError:
                        pass

                if time.time() - start_time >= self.timeout:
                    raise TimeoutError(f"Tiempo de espera agotado al adquirir bloqueo: {self.lock_path}")
                time.sleep(self.poll_interval)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.fd is not None:
            try:
                os.close(self.fd)
            except OSError:
                pass
            self.fd = None
        if os.path.exists(self.lock_path):
            try:
                os.remove(self.lock_path)
            except OSError:
                pass


def compute_stable_id(platform: str, author: str, date: str, message: str) -> str:
    """
    Genera un identificador inmutable y determinista para un aviso.
    Previene duplicados sin depender del orden o del índice de la lista.
    """
    clean_p = (platform or "").strip().lower()
    clean_a = (author or "").strip().lower()
    clean_d = (date or "").strip()
    clean_m = " ".join((message or "").strip().lower().split()[:25])
    raw_sig = f"{clean_p}|{clean_a}|{clean_d}|{clean_m}"
    h = hashlib.sha256(raw_sig.encode("utf-8")).hexdigest()[:12]
    
    # Prefijo mnemotécnico por plataforma
    prefix = "lead"
    if "telegram" in clean_p:
        prefix = "tg"
    elif "tusclases" in clean_p:
        prefix = "tc"
    elif "tablon" in clean_p or "tablón" in clean_p:
        prefix = "tb"
    elif "reddit" in clean_p:
        prefix = "rd"
    elif "cronoshare" in clean_p:
        prefix = "cr"

    return f"{prefix}_{h}"


def atomic_write_json(file_path: str, data: Any, indent: int = 2) -> None:
    """
    Escribe un archivo JSON de forma atómica:
    1. Guarda en un archivo temporal .tmp en el mismo directorio.
    2. Realiza fsync para asegurar persistencia en disco físico.
    3. Realiza os.replace (operación atómica en POSIX y Windows).
    4. Mantiene una copia de respaldo .bak del archivo anterior válido.
    """
    path = Path(file_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    
    lock_file = path.with_suffix(path.suffix + ".lock")
    with FileLock(str(lock_file)):
        tmp_file = path.with_suffix(f".tmp_{os.getpid()}_{time.time_ns()}")
        bak_file = path.with_suffix(path.suffix + ".bak")

        # Serializar y escribir
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)
            f.flush()
            os.fsync(f.fileno())

        # Si el archivo original existía y era válido, respaldar
        if path.exists() and path.stat().st_size > 0:
            try:
                shutil.copy2(str(path), str(bak_file))
            except Exception:
                pass

        # Reemplazo atómico
        os.replace(str(tmp_file), str(path))


@contextmanager
def locked_path(file_path: str, timeout: float = 10.0):
    """Context manager que retiene FileLock sobre un archivo durante una operación compuesta."""
    path = Path(file_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_file = path.with_suffix(path.suffix + ".lock")
    with FileLock(str(lock_file), timeout=timeout):
        yield path


def atomic_modify_json(
    file_path: str,
    modifier_fn: Callable[[Any], Any],
    default: Any = None,
    indent: int = 2,
    timeout: float = 10.0
) -> Any:
    """
    Ejecuta un ciclo atómico completo Read-Modify-Write bajo un mismo FileLock exclusivo.
    Garantiza que ningún otro proceso pueda intercalar lecturas o escrituras intermedias,
    previniendo condiciones de carrera y pérdida de datos.
    """
    path = Path(file_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_file = path.with_suffix(path.suffix + ".lock")

    with FileLock(str(lock_file), timeout=timeout):
        current_data = safe_read_json(str(path), default=default)
        updated_data = modifier_fn(current_data)

        tmp_file = path.with_suffix(f".tmp_{os.getpid()}_{time.time_ns()}")
        bak_file = path.with_suffix(path.suffix + ".bak")

        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(updated_data, f, ensure_ascii=False, indent=indent)
            f.flush()
            os.fsync(f.fileno())

        if path.exists() and path.stat().st_size > 0:
            try:
                shutil.copy2(str(path), str(bak_file))
            except Exception:
                pass

        os.replace(str(tmp_file), str(path))
        return updated_data


def safe_read_json(file_path: str, default: Any = None) -> Any:
    """
    Lee un archivo JSON con tolerancia a fallos. Si el archivo está corrupto
    o truncado por una desconexión, intenta recuperarlo desde su copia de respaldo .bak.
    """
    path = Path(file_path).resolve()
    if not path.exists():
        return default if default is not None else []

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        bak_file = path.with_suffix(path.suffix + ".bak")
        if bak_file.exists():
            try:
                with open(bak_file, "r", encoding="utf-8") as f:
                    recovered = json.load(f)
                # Restaurar el archivo principal
                shutil.copy2(str(bak_file), str(path))
                return recovered
            except Exception:
                pass
        return default if default is not None else []


def atomic_write_text(file_path: str, content: str, encoding: str = "utf-8") -> None:
    """Escribe texto a disco de manera atómica con .tmp y os.replace."""
    path = Path(file_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    
    lock_file = path.with_suffix(path.suffix + ".lock")
    with FileLock(str(lock_file)):
        tmp_file = path.with_suffix(f".tmp_{os.getpid()}_{time.time_ns()}")
        with open(tmp_file, "w", encoding=encoding, newline="") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(str(tmp_file), str(path))


def merge_crm_tracking(new_leads: List[Dict[str, Any]], existing_leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Preserva el estado de gestión comercial y notas del CRM.
    Si un lead ya fue contactado, descartado o tiene notas manuales, estos campos
    NUNCA se pierden al volver a extraer o reauditar datos.
    """
    existing_map = {item.get("id"): item for item in existing_leads if isinstance(item, dict) and "id" in item}
    
    merged = []
    for lead in new_leads:
        lead_id = lead.get("id")
        if lead_id in existing_map:
            prev = existing_map[lead_id]
            # Conservar campos de seguimiento comercial
            for track_field in ["estado_contacto", "notas_seguimiento", "fecha_contacto", "canal_respuesta", "precio_acordado"]:
                if track_field in prev and prev[track_field] is not None:
                    lead[track_field] = prev[track_field]
        merged.append(lead)
    return merged
