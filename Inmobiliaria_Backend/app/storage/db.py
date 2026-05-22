from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.core.config import get_settings

logger = logging.getLogger(__name__)


CONTACTS_TABLE = "inmobiliaria_contacts"
PROMPTS_TABLE = "inmobiliaria_prompts"
ADMIN_USERS_TABLE = "inmobiliaria_admin_users"
SETTINGS_TABLE = "inmobiliaria_settings"

CONTACTS_SCHEMA = f"""
CREATE TABLE IF NOT EXISTS {CONTACTS_TABLE} (
    phone        TEXT PRIMARY KEY,
    contact_id   TEXT,
    edificio     TEXT,
    depto        TEXT,
    nombre       TEXT,
    nombre_sheet TEXT,
    verified     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Migración para tablas creadas antes de añadir multi-edificio
ALTER TABLE {CONTACTS_TABLE} ADD COLUMN IF NOT EXISTS edificio TEXT;
-- Migración para auto-pausa cuando un humano interviene en la conversación
ALTER TABLE {CONTACTS_TABLE} ADD COLUMN IF NOT EXISTS paused_until TIMESTAMPTZ;
"""

PROMPTS_SCHEMA = f"""
CREATE TABLE IF NOT EXISTS {PROMPTS_TABLE} (
    key         TEXT PRIMARY KEY,
    content     TEXT NOT NULL,
    updated_by  TEXT,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

ADMIN_USERS_SCHEMA = f"""
CREATE TABLE IF NOT EXISTS {ADMIN_USERS_TABLE} (
    id            BIGSERIAL PRIMARY KEY,
    username      TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

SETTINGS_SCHEMA = f"""
CREATE TABLE IF NOT EXISTS {SETTINGS_TABLE} (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    updated_by  TEXT,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


_pool: ConnectionPool | None = None


def _get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        settings = get_settings()
        if not settings.database_url:
            raise RuntimeError(
                "Postgres no configurado. Faltan DB_USER / DB_PASSWORD / DB_HOST en .env"
            )
        _pool = ConnectionPool(
            settings.database_url,
            min_size=1,
            max_size=5,
            kwargs={"row_factory": dict_row},
            open=True,
        )
        logger.info("Postgres pool inicializado (host=%s)", settings.db_host)
    return _pool


def init_db() -> None:
    """Crea las tablas de dominio (contactos). El historial se crea aparte
    desde `app.chat_history.init_table()`."""
    pool = _get_pool()
    with pool.connection() as conn:
        conn.execute(CONTACTS_SCHEMA)
        conn.execute(PROMPTS_SCHEMA)
        conn.execute(ADMIN_USERS_SCHEMA)
        conn.execute(SETTINGS_SCHEMA)
    logger.info(
        "Tablas verificadas: %s, %s, %s, %s",
        CONTACTS_TABLE, PROMPTS_TABLE, ADMIN_USERS_TABLE, SETTINGS_TABLE,
    )


@contextmanager
def get_conn() -> Iterator[psycopg.Connection]:
    """Devuelve una conexión del pool. El context manager hace commit/rollback."""
    pool = _get_pool()
    with pool.connection() as conn:
        yield conn
