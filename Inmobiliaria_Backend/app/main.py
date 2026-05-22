from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.admin import router as admin_router
from app.api.chat import router as chat_router
from app.api.highlevel import router as highlevel_router
from app.chat_history import init_table as init_chat_history_table
from app.core.config import get_settings
from app.storage.admin_users import seed_admin_user_if_missing
from app.storage.db import init_db
from app.storage.prompts import seed_defaults_if_missing

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    init_chat_history_table()
    seed_defaults_if_missing()
    seed_admin_user_if_missing()
    logger.info("App lista")
    yield


def create_app() -> FastAPI:
    settings = get_settings()

    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    app = FastAPI(
        title="Agente IA Inmobiliaria",
        version="0.1.0",
        description="Webhook para HighLevel que responde mensajes de WhatsApp con LangChain + OpenAI.",
        lifespan=lifespan,
    )

    if settings.cors_allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_allowed_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["*"],
        )

    app.include_router(highlevel_router)
    app.include_router(admin_router)
    app.include_router(chat_router)

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "model": settings.openai_model}

    return app


app = create_app()
