"""Auth del admin: emite y valida JWTs propios.

Flujo:
- Frontend hace POST /api/admin/login con {username, password}.
- Si las credenciales matchean (bcrypt), devolvemos un JWT firmado HS256 con
  `ADMIN_JWT_SECRET`.
- El frontend lo manda en Authorization: Bearer <token> a los demás endpoints.
- `require_admin` valida la firma y la expiración.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)

JWT_ALG = "HS256"


@dataclass
class AdminPrincipal:
    user_id: int
    username: str


def _secret() -> str:
    settings = get_settings()
    if not settings.admin_jwt_secret:
        raise HTTPException(
            status_code=500,
            detail="ADMIN_JWT_SECRET no está configurado en el backend",
        )
    return settings.admin_jwt_secret


def issue_token(user_id: int, username: str) -> tuple[str, datetime]:
    """Emite un JWT con sub=user_id y devuelve (token, expires_at)."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=settings.admin_jwt_ttl_hours)
    payload = {
        "sub": str(user_id),
        "username": username,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    token = jwt.encode(payload, _secret(), algorithm=JWT_ALG)
    return token, exp


async def require_admin(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AdminPrincipal:
    if creds is None or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization: Bearer <token>",
        )

    try:
        payload = jwt.decode(creds.credentials, _secret(), algorithms=[JWT_ALG])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError as exc:
        logger.info("JWT inválido: %s", exc)
        raise HTTPException(status_code=401, detail="Token inválido") from exc

    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Token sin sub válido")

    return AdminPrincipal(user_id=user_id, username=payload.get("username", ""))
