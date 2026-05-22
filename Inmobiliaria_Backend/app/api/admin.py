from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth.admin import AdminPrincipal, issue_token, require_admin
from app.storage import admin_users as users_repo
from app.storage import prompts as prompts_repo
from app.storage import settings as settings_repo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ----- Login --------------------------------------------------------------


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: str
    username: str


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest) -> LoginResponse:
    user = users_repo.authenticate(body.username, body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
    token, exp = issue_token(user.id, user.username)
    return LoginResponse(
        access_token=token,
        expires_at=exp.isoformat(),
        username=user.username,
    )


# ----- Prompts ------------------------------------------------------------


class PromptResponse(BaseModel):
    key: str
    content: str
    updated_by: str | None
    updated_at: str


class PromptUpdate(BaseModel):
    content: str = Field(..., min_length=1)


def _to_response(p: prompts_repo.Prompt) -> PromptResponse:
    return PromptResponse(
        key=p.key,
        content=p.content,
        updated_by=p.updated_by,
        updated_at=p.updated_at,
    )


@router.get("/prompts", response_model=list[PromptResponse])
async def list_prompts(
    _: AdminPrincipal = Depends(require_admin),
) -> list[PromptResponse]:
    return [_to_response(p) for p in prompts_repo.list_prompts()]


@router.get("/prompts/{key}", response_model=PromptResponse)
async def get_prompt(
    key: str, _: AdminPrincipal = Depends(require_admin)
) -> PromptResponse:
    p = prompts_repo._get(key)
    if p is None:
        raise HTTPException(status_code=404, detail=f"Prompt '{key}' no existe")
    return _to_response(p)


@router.put("/prompts/{key}", response_model=PromptResponse)
async def update_prompt(
    key: str,
    body: PromptUpdate,
    user: AdminPrincipal = Depends(require_admin),
) -> PromptResponse:
    if key == prompts_repo.CHAT_SYSTEM_KEY:
        missing = _missing_placeholders(body.content, prompts_repo.REQUIRED_PLACEHOLDERS)
        if missing:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Faltan estos placeholders en el prompt: {sorted(missing)}. "
                    f"Tienen que aparecer literalmente como {{nombre_de_placeholder}}."
                ),
            )

    p = prompts_repo.upsert_prompt(key, body.content, updated_by=user.username)
    logger.info("Prompt %s actualizado por %s", key, user.username)
    return _to_response(p)


def _missing_placeholders(content: str, required: set[str]) -> set[str]:
    return {p for p in required if "{" + p + "}" not in content}


# ----- Kill-switch global -------------------------------------------------


class AgentStatus(BaseModel):
    enabled: bool
    updated_by: str | None
    updated_at: str | None


class AgentStatusUpdate(BaseModel):
    enabled: bool


def _setting_to_status(s: settings_repo.Setting) -> AgentStatus:
    return AgentStatus(
        enabled=s.value.lower() == "true",
        updated_by=s.updated_by,
        updated_at=s.updated_at or None,
    )


@router.get("/agent-status", response_model=AgentStatus)
async def get_agent_status(
    _: AdminPrincipal = Depends(require_admin),
) -> AgentStatus:
    return _setting_to_status(settings_repo.get_agent_status())


@router.put("/agent-status", response_model=AgentStatus)
async def set_agent_status(
    body: AgentStatusUpdate,
    user: AdminPrincipal = Depends(require_admin),
) -> AgentStatus:
    s = settings_repo.set_agent_enabled(body.enabled, updated_by=user.username)
    logger.info(
        "Agent %s por %s",
        "ENCENDIDO" if body.enabled else "APAGADO",
        user.username,
    )
    return _setting_to_status(s)
