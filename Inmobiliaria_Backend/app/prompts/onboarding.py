"""Prompt del sub-flujo de onboarding.

Se usa con `ChatOpenAI.with_structured_output(OnboardingExtraction)` para
extraer edificio, depto y nombre de un mensaje libre del usuario.

NO es editable por el admin — vive solo en código.
"""

ONBOARDING_SYSTEM_PROMPT = """Eres un extractor de datos. Lee el mensaje del usuario y \
devuelve, en JSON, su edificio, número de departamento (3 dígitos) y nombre, \
si los menciona. Si solo menciona algunos, deja los faltantes en null. No \
inventes."""
