"""Orquesta la conversación con el cliente.

Hay dos sub-flujos:

1. **Onboarding** (`contact.verified == False`): pedimos edificio + número de
   departamento + nombre. Validamos contra el sheet (cada pestaña es un
   edificio) y si matchea, marcamos al contacto como verificado.

2. **Chat** (`contact.verified == True`): inyectamos la fila completa del
   sheet del edificio del cliente + historial reciente y dejamos que el LLM
   responda.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from rapidfuzz import fuzz
from unidecode import unidecode

from app import chat_history
from app.core.config import get_settings
from app.prompts import ONBOARDING_SYSTEM_PROMPT
from app.services.sheet_client import get_sheet_client
from app.storage import contacts as contacts_repo
from app.storage import prompts as prompts_repo

logger = logging.getLogger(__name__)

NAME_FUZZY_THRESHOLD = 70  # 0-100, partial_ratio
HISTORY_LIMIT = 20         # mensajes recientes a inyectar al LLM


_llm: ChatOpenAI | None = None


def _get_llm() -> ChatOpenAI:
    global _llm
    if _llm is None:
        settings = get_settings()
        _llm = ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=0.3,
        )
    return _llm


# ---------------------------------------------------------------------------
# Onboarding: extracción de edificio + depto + nombre
# ---------------------------------------------------------------------------


class OnboardingExtraction(BaseModel):
    edificio: str | None = Field(
        default=None,
        description="Nombre del edificio que el usuario menciona (ej: 'La Joya', 'Torre Sol'). None si no.",
    )
    depto: str | None = Field(
        default=None,
        description="Número de departamento de 3 dígitos (101-999) si lo mencionó. None si no.",
    )
    nombre: str | None = Field(
        default=None,
        description="Nombre y/o apellido del propietario si lo mencionó. None si no.",
    )


async def _extract_onboarding(text: str) -> OnboardingExtraction:
    llm = _get_llm().with_structured_output(OnboardingExtraction)
    return await llm.ainvoke(
        [SystemMessage(content=ONBOARDING_SYSTEM_PROMPT), HumanMessage(content=text)]
    )  # type: ignore[return-value]


def _names_match(declared: str, on_sheet: str) -> bool:
    a = unidecode(declared).lower().strip()
    b = unidecode(on_sheet).lower().strip()
    score = fuzz.partial_ratio(a, b)
    logger.debug("Name match: %r vs %r -> %s", declared, on_sheet, score)
    return score >= NAME_FUZZY_THRESHOLD


async def _handle_onboarding(phone: str, text: str) -> str:
    contact = contacts_repo.get_contact(phone)
    extraction = await _extract_onboarding(text)
    sheet = get_sheet_client()

    # Combina lo que llega ahora con lo guardado previamente.
    edificio_input = extraction.edificio or (contact.edificio if contact else None)
    depto = extraction.depto or (contact.depto if contact else None)
    nombre = extraction.nombre or (contact.nombre if contact else None)

    # Resolver edificio (fuzzy) si tenemos uno declarado.
    edificio_canonico: str | None = None
    if edificio_input:
        edificio_canonico = sheet.find_building(edificio_input)
        if edificio_canonico is None:
            edificios = ", ".join(sheet.list_buildings())
            return (
                f"No reconozco el edificio \"{edificio_input}\". "
                f"Los edificios que administramos son: {edificios}. "
                f"¿Puedes confirmarme el nombre?"
            )

    # Si no tenemos absolutamente nada, pedimos los tres datos.
    # No listamos los edificios para no exponer toda la cartera al primer
    # mensaje — si el cliente escribe uno que no reconocemos, ahí sí le
    # mostramos la lista como ayuda de corrección.
    if not edificio_canonico and not depto and not nombre:
        return (
            "¡Hola! Soy Denise, la asistente virtual de la administración. "
            "Para ayudarte necesito tres datos: tu edificio, tu número de "
            "departamento (ej: 101) y tu nombre."
        )

    # Pedir lo que falte.
    if not edificio_canonico:
        contacts_repo.upsert_contact(phone, depto=depto, nombre=nombre)
        return "¿De qué edificio eres?"

    if not depto:
        contacts_repo.upsert_contact(phone, edificio=edificio_canonico, nombre=nombre)
        return f"¿Cuál es tu número de departamento en {edificio_canonico}?"

    if not nombre:
        contacts_repo.upsert_contact(phone, edificio=edificio_canonico, depto=depto)
        return "Perfecto. ¿Y cuál es tu nombre, por favor?"

    # Tenemos los tres → validar contra la fila del sheet.
    sheet_row = sheet.get_row(edificio_canonico, depto)
    if sheet_row is None:
        contacts_repo.upsert_contact(phone, edificio=edificio_canonico, depto=None)
        deptos = ", ".join(sheet.list_deptos(edificio_canonico))
        return (
            f"No encuentro el departamento {depto} en {edificio_canonico}. "
            f"Los departamentos válidos son: {deptos}. ¿Puedes confirmarme tu número?"
        )

    nombre_sheet = sheet_row.get("Responsable de Pago / Propietario", "") or ""
    if not _names_match(nombre, nombre_sheet):
        return (
            f"El nombre que me das no coincide con el que figura para el "
            f"departamento {depto} de {edificio_canonico}. ¿Puedes confirmarme "
            f"tu nombre completo como aparece en el contrato?"
        )

    contacts_repo.upsert_contact(
        phone,
        edificio=edificio_canonico,
        depto=depto,
        nombre=nombre,
        nombre_sheet=nombre_sheet,
        verified=True,
    )
    logger.info(
        "Contacto verificado: %s -> %s / depto %s (%s)",
        phone, edificio_canonico, depto, nombre_sheet,
    )
    return (
        f"¡Listo, {nombre}! Te identifiqué como propietario/a del depto "
        f"{depto} del edificio {edificio_canonico}. ¿En qué puedo ayudarte?"
    )


# ---------------------------------------------------------------------------
# Chat: fila del sheet + historial Postgres
# ---------------------------------------------------------------------------
# El system prompt vive en la BD (tabla inmobiliaria_prompts) para que pueda
# editarse desde la UI de admin. Ver app/storage/prompts.py.


def _format_row_for_prompt(row: dict[str, Any]) -> str:
    return "\n".join(f"- {k}: {v}" for k, v in row.items())


async def _handle_chat(phone: str, text: str, prior_messages: list[BaseMessage]) -> str:
    contact = contacts_repo.get_contact(phone)
    assert contact is not None and contact.verified

    if not contact.edificio or not contact.depto:
        # No debería pasar si verified=True, pero por seguridad reseteamos.
        contacts_repo.upsert_contact(phone, verified=False)
        return (
            "Hubo un problema con tu sesión. Por favor dime tu edificio, "
            "número de departamento y nombre para identificarte de nuevo."
        )

    sheet_row = get_sheet_client().get_row(contact.edificio, contact.depto)
    if sheet_row is None:
        return (
            "Tuve un problema accediendo a tus datos. Por favor inténtalo de "
            "nuevo en unos minutos."
        )

    template = prompts_repo.get_chat_system_prompt()
    try:
        system = template.format(
            edificio=contact.edificio,
            depto=contact.depto,
            nombre=contact.nombre,
            nombre_sheet=contact.nombre_sheet,
            row_dump=_format_row_for_prompt(sheet_row),
        )
    except KeyError as exc:
        # El admin editó el prompt y agregó una variable que no existe.
        logger.error("Prompt con placeholder desconocido: %s", exc)
        system = prompts_repo.DEFAULT_CHAT_SYSTEM_PROMPT.format(
            edificio=contact.edificio,
            depto=contact.depto,
            nombre=contact.nombre,
            nombre_sheet=contact.nombre_sheet,
            row_dump=_format_row_for_prompt(sheet_row),
        )

    messages: list[BaseMessage] = [SystemMessage(content=system)]
    messages.extend(prior_messages[-HISTORY_LIMIT:])
    messages.append(HumanMessage(content=text))

    result = await _get_llm().ainvoke(messages)
    return result.content if hasattr(result, "content") else str(result)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


async def handle_message(phone: str, text: str, contact_id: str | None = None) -> str:
    """Procesa un mensaje entrante.

    `phone` es el identificador estable del cliente (lo usamos como PK).
    `contact_id` es el id de HighLevel — lo guardamos cada vez que llega para
    poder enviarle la respuesta vía API. Puede cambiar mes a mes si HighLevel
    recrea el contacto, pero el `phone` no.
    """
    if contact_id:
        contacts_repo.upsert_contact(phone, contact_id=contact_id)

    contact = contacts_repo.get_contact(phone)
    prior_messages = chat_history.get_messages(phone)

    if contact is None or not contact.verified:
        reply = await _handle_onboarding(phone, text)
    else:
        reply = await _handle_chat(phone, text, prior_messages)

    chat_history.add_turn(phone, user_text=text, assistant_text=reply)
    return reply
