"""Mini key/value store para flags globales del sistema.

Hoy lo usamos para el kill-switch del agente (`agent_enabled`). Mañana
podríamos meter más flags (modo mantenimiento, etc.) sin agregar tablas.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass

from app.storage.db import SETTINGS_TABLE, get_conn

logger = logging.getLogger(__name__)


AGENT_ENABLED_KEY = "agent_enabled"
DEFAULT_AGENT_ENABLED = "true"

PAUSE_HOURS_KEY = "pause_on_human_hours"
DEFAULT_PAUSE_HOURS = "2"

CACHE_TTL_SECONDS = 10.0


@dataclass
class Setting:
    key: str
    value: str
    updated_by: str | None
    updated_at: str


def get_setting(key: str) -> Setting | None:
    with get_conn() as conn:
        row = conn.execute(
            f"SELECT key, value, updated_by, updated_at FROM {SETTINGS_TABLE} "
            f"WHERE key = %s",
            (key,),
        ).fetchone()
    if row is None:
        return None
    return Setting(
        key=row["key"],
        value=row["value"],
        updated_by=row["updated_by"],
        updated_at=str(row["updated_at"]),
    )


def upsert_setting(key: str, value: str, updated_by: str | None) -> Setting:
    with get_conn() as conn:
        row = conn.execute(
            f"""
            INSERT INTO {SETTINGS_TABLE} (key, value, updated_by)
            VALUES (%s, %s, %s)
            ON CONFLICT (key) DO UPDATE SET
                value      = EXCLUDED.value,
                updated_by = EXCLUDED.updated_by,
                updated_at = NOW()
            RETURNING key, value, updated_by, updated_at
            """,
            (key, value, updated_by),
        ).fetchone()
    invalidate_cache(key)
    return Setting(
        key=row["key"],
        value=row["value"],
        updated_by=row["updated_by"],
        updated_at=str(row["updated_at"]),
    )


# ----- Agent enabled (kill-switch) ----------------------------------------

_lock = threading.Lock()
_cached: dict[str, tuple[str, float]] = {}  # key -> (value, cached_at)


def _get_cached(key: str, default: str) -> str:
    with _lock:
        entry = _cached.get(key)
        if entry is not None and time.monotonic() - entry[1] < CACHE_TTL_SECONDS:
            return entry[0]

        s = get_setting(key)
        value = s.value if s is not None else default
        _cached[key] = (value, time.monotonic())
        return value


def invalidate_cache(key: str | None = None) -> None:
    with _lock:
        if key is None:
            _cached.clear()
        else:
            _cached.pop(key, None)


def is_agent_enabled() -> bool:
    return _get_cached(AGENT_ENABLED_KEY, DEFAULT_AGENT_ENABLED).lower() == "true"


def set_agent_enabled(enabled: bool, updated_by: str | None) -> Setting:
    return upsert_setting(
        AGENT_ENABLED_KEY,
        "true" if enabled else "false",
        updated_by=updated_by,
    )


def get_agent_status() -> Setting:
    """Devuelve el estado actual con metadata. Si nunca se seteó, default true."""
    s = get_setting(AGENT_ENABLED_KEY)
    if s is not None:
        return s
    # Aún no se persistió. Devolvemos un Setting "virtual" con default.
    return Setting(
        key=AGENT_ENABLED_KEY,
        value=DEFAULT_AGENT_ENABLED,
        updated_by=None,
        updated_at="",
    )


# ----- Pausa por intervención humana --------------------------------------


def get_pause_hours() -> float:
    """Cuántas horas dura la auto-pausa cuando un humano responde manualmente."""
    raw = _get_cached(PAUSE_HOURS_KEY, DEFAULT_PAUSE_HOURS)
    try:
        return float(raw)
    except ValueError:
        return float(DEFAULT_PAUSE_HOURS)


def set_pause_hours(hours: float, updated_by: str | None) -> Setting:
    return upsert_setting(PAUSE_HOURS_KEY, str(hours), updated_by=updated_by)
