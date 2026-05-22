"""Repositorio del usuario admin (login para editar prompts).

Tabla `inmobiliaria_admin_users` con (username, password_hash). Las passwords
se hashean con bcrypt antes de guardar; nunca se persisten en texto plano.

Para la primera puesta en marcha hay un seeder (`seed_admin_user_if_missing`)
que lee `ADMIN_USERNAME` y `ADMIN_PASSWORD` del `.env` y crea el primer
usuario si no existe ninguno.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import bcrypt

from app.core.config import get_settings
from app.storage.db import ADMIN_USERS_TABLE, get_conn

logger = logging.getLogger(__name__)


@dataclass
class AdminUser:
    id: int
    username: str


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def get_by_username(username: str) -> tuple[AdminUser, str] | None:
    """Devuelve (AdminUser, password_hash) o None si no existe."""
    with get_conn() as conn:
        row = conn.execute(
            f"SELECT id, username, password_hash FROM {ADMIN_USERS_TABLE} "
            f"WHERE username = %s",
            (username,),
        ).fetchone()
    if row is None:
        return None
    return AdminUser(id=row["id"], username=row["username"]), row["password_hash"]


def authenticate(username: str, password: str) -> AdminUser | None:
    """Devuelve el AdminUser si las credenciales son válidas, o None si no."""
    found = get_by_username(username)
    if not found:
        return None
    user, hashed = found
    if not _verify(password, hashed):
        return None
    return user


def create_user(username: str, password: str) -> AdminUser:
    with get_conn() as conn:
        row = conn.execute(
            f"""
            INSERT INTO {ADMIN_USERS_TABLE} (username, password_hash)
            VALUES (%s, %s)
            RETURNING id, username
            """,
            (username, _hash(password)),
        ).fetchone()
    logger.info("Admin user creado: %s", username)
    return AdminUser(id=row["id"], username=row["username"])


def set_password(user_id: int, new_password: str) -> None:
    with get_conn() as conn:
        conn.execute(
            f"""
            UPDATE {ADMIN_USERS_TABLE}
            SET password_hash = %s, updated_at = NOW()
            WHERE id = %s
            """,
            (_hash(new_password), user_id),
        )


def count_users() -> int:
    with get_conn() as conn:
        row = conn.execute(f"SELECT COUNT(*) AS n FROM {ADMIN_USERS_TABLE}").fetchone()
    return int(row["n"])


def seed_admin_user_if_missing() -> None:
    """Si no hay ningún admin, crea uno con ADMIN_USERNAME/ADMIN_PASSWORD del .env.

    Solo se ejecuta UNA vez (cuando la tabla está vacía). Si más adelante
    cambias `ADMIN_PASSWORD` en el .env, no afecta al usuario ya creado;
    para cambiar password hay que usar `set_password()` o un endpoint futuro.
    """
    if count_users() > 0:
        return

    settings = get_settings()
    if not settings.admin_username or not settings.admin_password:
        logger.warning(
            "No hay admin user en %s y faltan ADMIN_USERNAME / ADMIN_PASSWORD en .env. "
            "El login no funcionará hasta que crees uno.",
            ADMIN_USERS_TABLE,
        )
        return

    create_user(settings.admin_username, settings.admin_password)
