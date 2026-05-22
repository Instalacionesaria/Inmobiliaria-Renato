"""Implementación del historial de conversación sobre PostgreSQL.

Usa `langchain-postgres.PostgresChatMessageHistory`, que persiste cada
mensaje (HumanMessage / AIMessage) con su `session_id` (UUID derivado del
teléfono del cliente) en la tabla `inmobiliaria_chat_history`.

`langchain-postgres` requiere cursores en formato tupla (no dict_row), por
eso abrimos conexiones frescas con `psycopg.connect()` en lugar de usar el
pool del módulo `app.storage.db` (que usa dict_row para nuestras queries).
"""

from __future__ import annotations

import logging
import uuid

import psycopg
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_postgres import PostgresChatMessageHistory

from app.core.config import get_settings

logger = logging.getLogger(__name__)

TABLE_NAME = "inmobiliaria_chat_history"

# `langchain-postgres` usa session_id tipo UUID. Como nuestro identificador
# es el teléfono (string), lo convertimos a UUID determinístico con uuid5.
_NAMESPACE = uuid.UUID("c0a801ff-1234-5678-9abc-def012345678")


def _session_id_for(phone: str) -> str:
    return str(uuid.uuid5(_NAMESPACE, phone))


def _connect() -> psycopg.Connection:
    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError("Postgres no configurado (DB_USER/DB_PASSWORD/DB_HOST)")
    return psycopg.connect(settings.database_url)


def init_table() -> None:
    """Crea la tabla de historial si no existe (esquema langchain-postgres)."""
    with _connect() as conn:
        PostgresChatMessageHistory.create_tables(conn, TABLE_NAME)
    logger.info("Tabla de chat history verificada: %s", TABLE_NAME)


def get_messages(phone: str) -> list[BaseMessage]:
    """Devuelve todos los mensajes del cliente en orden cronológico."""
    with _connect() as conn:
        history = PostgresChatMessageHistory(
            TABLE_NAME, _session_id_for(phone), sync_connection=conn
        )
        return list(history.messages)


def add_turn(phone: str, user_text: str, assistant_text: str) -> None:
    """Persiste el turno (mensaje del usuario + respuesta del asistente)."""
    with _connect() as conn:
        history = PostgresChatMessageHistory(
            TABLE_NAME, _session_id_for(phone), sync_connection=conn
        )
        history.add_messages(
            [
                HumanMessage(content=user_text),
                AIMessage(content=assistant_text),
            ]
        )
