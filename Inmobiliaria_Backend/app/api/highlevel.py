from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request
from pydantic import BaseModel

from app.agent.flow import handle_message
from app.core.config import get_settings
from app.services.highlevel_client import HighLevelError, send_whatsapp_message
from app.storage import contacts as contacts_repo
from app.storage.contacts import normalize_phone
from app.storage.settings import get_pause_hours, is_agent_enabled

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/highlevel", tags=["highlevel"])

# Tag en HighLevel que pausa la IA. Si el contacto lo tiene, el webhook
# devuelve 200 sin invocar al agente. Para reactivar, el admin quita el tag.
PAUSE_TAG = "ia_pausada"


class WebhookAck(BaseModel):
    status: str = "accepted"
    contact_id: str | None = None


def _extract_message_text(raw: dict[str, Any]) -> str | None:
    custom = raw.get("customData") or raw.get("custom_data")
    if isinstance(custom, dict):
        value = custom.get("message_body")
        if isinstance(value, str) and value.strip():
            return value

    message = raw.get("message")
    if isinstance(message, dict):
        body = message.get("body")
        if isinstance(body, str) and body.strip():
            return body

    if isinstance(message, str) and message.strip():
        return message

    for key in ("body", "text", "last_message"):
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            return value

    return None


def _extract_contact_id(raw: dict[str, Any]) -> str | None:
    for key in ("contact_id", "contactId"):
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            return value

    contact = raw.get("contact")
    if isinstance(contact, dict):
        for key in ("id", "contact_id", "contactId"):
            value = contact.get(key)
            if isinstance(value, str) and value.strip():
                return value

    return None


def _extract_tags(raw: dict[str, Any]) -> list[str]:
    """Devuelve los tags del contacto en lowercase y sin espacios.

    HighLevel manda los tags como string separado por comas (ej: "vip, ia_pausada"),
    aunque a veces aparece como array — toleramos ambos.
    """
    def _normalize(value: Any) -> list[str]:
        if isinstance(value, str):
            return [t.strip().lower() for t in value.split(",") if t.strip()]
        if isinstance(value, list):
            return [str(t).strip().lower() for t in value if t]
        return []

    tags = _normalize(raw.get("tags"))
    if tags:
        return tags

    contact = raw.get("contact")
    if isinstance(contact, dict):
        return _normalize(contact.get("tags"))

    return []


def _extract_phone(raw: dict[str, Any]) -> str | None:
    """Busca el teléfono en distintas rutas del payload de HighLevel."""
    for key in ("phone", "phoneNumber"):
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            return value

    contact = raw.get("contact")
    if isinstance(contact, dict):
        for key in ("phone", "phoneNumber"):
            value = contact.get(key)
            if isinstance(value, str) and value.strip():
                return value

    custom = raw.get("customData") or raw.get("custom_data")
    if isinstance(custom, dict):
        value = custom.get("contact_phone")
        if isinstance(value, str) and value.strip():
            return value

    return None


async def _process_and_reply(message_text: str, phone: str, contact_id: str) -> None:
    """Procesa el mensaje (auth/chat) y envía la respuesta vía HighLevel.

    Se ejecuta en background — el webhook ya devolvió 200 al workflow.
    """
    try:
        answer = await handle_message(
            phone=phone, text=message_text, contact_id=contact_id
        )
        logger.info("Agent reply for phone=%s: %s", phone, answer)
        await send_whatsapp_message(contact_id=contact_id, text=answer)
    except HighLevelError as exc:
        logger.error("Failed to send WhatsApp via HighLevel: %s", exc)
    except Exception:
        logger.exception("Unexpected error processing inbound message")


@router.post("/webhook", response_model=WebhookAck)
async def highlevel_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_webhook_secret: str | None = Header(default=None, alias="X-Webhook-Secret"),
) -> WebhookAck:
    settings = get_settings()

    if settings.webhook_secret and x_webhook_secret != settings.webhook_secret:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    try:
        raw: dict[str, Any] = await request.json()
    except Exception as exc:
        logger.warning("No pude parsear JSON del webhook: %s", exc)
        raise HTTPException(status_code=400, detail="Body must be valid JSON") from exc

    if not isinstance(raw, dict):
        raise HTTPException(status_code=400, detail="Body must be a JSON object")

    logger.info("Inbound HighLevel webhook payload: %s", raw)

    message_text = _extract_message_text(raw)
    contact_id = _extract_contact_id(raw)
    phone = normalize_phone(_extract_phone(raw))
    tags = _extract_tags(raw)

    # Kill-switch global: si el agente está apagado desde el panel admin,
    # ackeamos 200 silencioso y no invocamos a OpenAI ni a HighLevel.
    if not is_agent_enabled():
        logger.info("Agente globalmente pausado — no respondemos a %s", contact_id)
        return WebhookAck(status="globally_paused", contact_id=contact_id)

    if PAUSE_TAG in tags:
        logger.info(
            "Contacto %s tiene tag '%s' — IA pausada, no respondemos",
            contact_id, PAUSE_TAG,
        )
        return WebhookAck(status="paused", contact_id=contact_id)

    # Auto-pausa: si un humano intervino recientemente, no respondemos hasta
    # que expire el cooldown configurado.
    if phone:
        existing = contacts_repo.get_contact(phone)
        if existing and existing.is_paused():
            logger.info(
                "Contacto %s en auto-pausa hasta %s — no respondemos",
                phone, existing.paused_until,
            )
            return WebhookAck(status="human_active", contact_id=contact_id)

    if not message_text:
        raise HTTPException(
            status_code=400,
            detail=(
                "No message text found. Buscamos en: customData.message_body, "
                "message.body, message (string), body, text, last_message."
            ),
        )

    if not contact_id:
        raise HTTPException(
            status_code=400,
            detail="No contact_id found in payload (root.contact_id, root.contactId, contact.id).",
        )

    if not phone:
        raise HTTPException(
            status_code=400,
            detail="No phone found in payload (root.phone, contact.phone, customData.contact_phone).",
        )

    background_tasks.add_task(_process_and_reply, message_text, phone, contact_id)

    return WebhookAck(contact_id=contact_id)


class OutboundAck(BaseModel):
    status: str = "paused"
    contact_id: str | None = None
    paused_until: str | None = None


@router.post("/outbound", response_model=OutboundAck)
async def highlevel_outbound(
    request: Request,
    x_webhook_secret: str | None = Header(default=None, alias="X-Webhook-Secret"),
) -> OutboundAck:
    """Recibe el aviso de que un humano (admin) acaba de responder manualmente.

    Configurás en HighLevel un workflow con trigger "Outbound Message" filtrado
    a **Manual Message** (no Workflow ni API), y ese workflow llama a este
    endpoint. El contacto queda en auto-pausa por las horas configuradas.
    """
    settings = get_settings()
    if settings.webhook_secret and x_webhook_secret != settings.webhook_secret:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    try:
        raw: dict[str, Any] = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Body must be valid JSON") from exc

    if not isinstance(raw, dict):
        raise HTTPException(status_code=400, detail="Body must be a JSON object")

    logger.info("Outbound HighLevel webhook payload: %s", raw)

    contact_id = _extract_contact_id(raw)
    phone = normalize_phone(_extract_phone(raw))

    if not phone:
        raise HTTPException(
            status_code=400,
            detail="No phone found in payload.",
        )

    hours = get_pause_hours()
    until = contacts_repo.pause_contact(phone, hours=hours, contact_id=contact_id)
    logger.info(
        "Auto-pausa para %s por %.1fh (hasta %s)", phone, hours, until.isoformat()
    )

    return OutboundAck(
        status="paused",
        contact_id=contact_id,
        paused_until=until.isoformat(),
    )
