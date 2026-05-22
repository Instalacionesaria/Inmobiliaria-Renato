from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class HighLevelError(RuntimeError):
    """Error al hablar con la API de HighLevel."""


async def send_whatsapp_message(contact_id: str, text: str) -> dict[str, Any]:
    """Envía un mensaje de texto libre por WhatsApp a través de la API de HighLevel.

    Endpoint: POST {base}/conversations/messages
    Doc: https://highlevel.stoplight.io/docs/integrations/conversations-api

    Solo funciona dentro de la ventana de servicio de 24h de WhatsApp
    (la conversación ya fue iniciada por el cliente).
    """
    settings = get_settings()

    if not settings.highlevel_api_token:
        raise HighLevelError("HIGHLEVEL_API_TOKEN no configurado")
    if not settings.highlevel_location_id:
        raise HighLevelError("LOCATION_ID no configurado")

    url = f"{settings.highlevel_api_base_url}/conversations/messages"
    headers = {
        "Authorization": f"Bearer {settings.highlevel_api_token}",
        "Version": settings.highlevel_api_version,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {
        "type": "WhatsApp",
        "contactId": contact_id,
        "message": text,
        "locationId": settings.highlevel_location_id,
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(url, json=payload, headers=headers)

    if response.status_code >= 400:
        logger.error(
            "HighLevel API error %s for contact=%s: %s",
            response.status_code,
            contact_id,
            response.text,
        )
        raise HighLevelError(
            f"HighLevel API returned {response.status_code}: {response.text}"
        )

    data = response.json()
    logger.info("HighLevel message sent. contact=%s response=%s", contact_id, data)
    return data
