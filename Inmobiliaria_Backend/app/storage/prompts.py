"""Repositorio de prompts editables.

El system prompt principal del agente vive en la tabla `inmobiliaria_prompts`
para que pueda editarse desde una UI sin redeployar.

Hay un valor por defecto (`DEFAULT_CHAT_SYSTEM_PROMPT`) que se inserta la
primera vez. Si el usuario lo edita, queda sobreescrito.

Cache: el prompt se mantiene en memoria por `CACHE_TTL_SECONDS`. Tras una
edición vía API, llamar a `invalidate_cache()` para refrescar de inmediato.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass

from app.prompts import DEFAULT_CHAT_SYSTEM_PROMPT
from app.storage.db import PROMPTS_TABLE, get_conn

logger = logging.getLogger(__name__)


CHAT_SYSTEM_KEY = "chat_system"

CACHE_TTL_SECONDS = 30.0


__all__ = ["DEFAULT_CHAT_SYSTEM_PROMPT", "Prompt", "REQUIRED_PLACEHOLDERS"]


# Variables {} que el chat_system DEBE conservar para que el flow funcione.
REQUIRED_PLACEHOLDERS = {"edificio", "depto", "nombre", "nombre_sheet", "row_dump"}


@dataclass
class Prompt:
    key: str
    content: str
    updated_by: str | None
    updated_at: str  # iso timestamp


def _get(key: str) -> Prompt | None:
    with get_conn() as conn:
        row = conn.execute(
            f"SELECT key, content, updated_by, updated_at "
            f"FROM {PROMPTS_TABLE} WHERE key = %s",
            (key,),
        ).fetchone()
    if row is None:
        return None
    return Prompt(
        key=row["key"],
        content=row["content"],
        updated_by=row["updated_by"],
        updated_at=str(row["updated_at"]),
    )


def list_prompts() -> list[Prompt]:
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT key, content, updated_by, updated_at FROM {PROMPTS_TABLE} ORDER BY key"
        ).fetchall()
    return [
        Prompt(
            key=r["key"],
            content=r["content"],
            updated_by=r["updated_by"],
            updated_at=str(r["updated_at"]),
        )
        for r in rows
    ]


def upsert_prompt(key: str, content: str, updated_by: str | None) -> Prompt:
    with get_conn() as conn:
        row = conn.execute(
            f"""
            INSERT INTO {PROMPTS_TABLE} (key, content, updated_by)
            VALUES (%s, %s, %s)
            ON CONFLICT (key) DO UPDATE SET
                content    = EXCLUDED.content,
                updated_by = EXCLUDED.updated_by,
                updated_at = NOW()
            RETURNING key, content, updated_by, updated_at
            """,
            (key, content, updated_by),
        ).fetchone()
    invalidate_cache()
    return Prompt(
        key=row["key"],
        content=row["content"],
        updated_by=row["updated_by"],
        updated_at=str(row["updated_at"]),
    )


def seed_defaults_if_missing() -> None:
    """Inserta prompts por defecto si la tabla está vacía. Idempotente."""
    if _get(CHAT_SYSTEM_KEY) is None:
        upsert_prompt(CHAT_SYSTEM_KEY, DEFAULT_CHAT_SYSTEM_PROMPT, updated_by="seed")
        logger.info("Prompt %s insertado con valor por defecto", CHAT_SYSTEM_KEY)


# ----- Cache en memoria del prompt actual -----

_lock = threading.Lock()
_cached_chat_system: str | None = None
_cached_at: float = 0.0


def get_chat_system_prompt() -> str:
    """Devuelve el contenido actual del CHAT_SYSTEM, cacheado por TTL."""
    global _cached_chat_system, _cached_at
    with _lock:
        if (
            _cached_chat_system is None
            or time.monotonic() - _cached_at > CACHE_TTL_SECONDS
        ):
            prompt = _get(CHAT_SYSTEM_KEY)
            _cached_chat_system = (
                prompt.content if prompt is not None else DEFAULT_CHAT_SYSTEM_PROMPT
            )
            _cached_at = time.monotonic()
        return _cached_chat_system


def invalidate_cache() -> None:
    global _cached_chat_system, _cached_at
    with _lock:
        _cached_chat_system = None
        _cached_at = 0.0
