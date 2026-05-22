"""Prompts del agente.

Centralizamos aquí los system prompts para que sean fáciles de leer y editar.

- `ONBOARDING_SYSTEM_PROMPT`: hardcoded, se usa siempre tal cual.
- `DEFAULT_CHAT_SYSTEM_PROMPT`: semilla inicial para la tabla
  `inmobiliaria_prompts`. En producción, el prompt vivo del chat se edita
  desde el panel admin y se persiste en BD; este archivo solo sirve como
  valor por defecto la primera vez (o como fallback si el placeholder de
  la BD trae una variable inválida).
"""

from app.prompts.chat_default import DEFAULT_CHAT_SYSTEM_PROMPT
from app.prompts.onboarding import ONBOARDING_SYSTEM_PROMPT

__all__ = ["DEFAULT_CHAT_SYSTEM_PROMPT", "ONBOARDING_SYSTEM_PROMPT"]
