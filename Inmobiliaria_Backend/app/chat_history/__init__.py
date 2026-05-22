"""Módulo de historial de conversación.

API pública: si más adelante quieres cambiar la implementación (Redis, archivo
local, otra DB), solo cambias el módulo importado abajo. El resto de la app
sigue llamando a `chat_history.get_messages` / `chat_history.add_turn` /
`chat_history.init_table`.
"""

from app.chat_history.postgres import (
    TABLE_NAME,
    add_turn,
    get_messages,
    init_table,
)

__all__ = ["TABLE_NAME", "add_turn", "get_messages", "init_table"]
