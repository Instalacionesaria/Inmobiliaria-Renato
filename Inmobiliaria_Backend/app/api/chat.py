"""Endpoint de prueba para clientes locales (Streamlit, scripts, etc).

A diferencia de `/api/highlevel/webhook` — que recibe mensajes de HighLevel y
responde por WhatsApp — este endpoint devuelve la respuesta del agente
directamente en el HTTP response. Sirve para probar el comportamiento del
agente sin depender de la integración con HighLevel.

Las sesiones de prueba usan un prefijo de teléfono `+000streamlit-` para
mantenerlas aisladas de los contactos reales en la base de datos.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agent.flow import handle_message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat-test"])

TEST_PHONE_PREFIX = "+000streamlit-"


class ChatTestRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=64)
    text: str = Field(..., min_length=1)


class ChatTestResponse(BaseModel):
    reply: str
    phone: str


@router.post("/test", response_model=ChatTestResponse)
async def chat_test(payload: ChatTestRequest) -> ChatTestResponse:
    phone = f"{TEST_PHONE_PREFIX}{payload.session_id}"
    try:
        reply = await handle_message(phone=phone, text=payload.text, contact_id=None)
    except Exception:
        logger.exception("Error en chat_test session=%s", payload.session_id)
        raise HTTPException(status_code=500, detail="Error procesando el mensaje")
    return ChatTestResponse(reply=reply, phone=phone)
