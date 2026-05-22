"""UI de prueba para conversar con el agente sin WhatsApp.

Habla con el backend a través de `POST /api/chat/test`. Cada sesión usa un
`session_id` aislado para que el historial de prueba no se mezcle con
contactos reales en la base de datos.
"""

from __future__ import annotations

import os
import uuid

import httpx
import streamlit as st

BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000")
CHAT_ENDPOINT = f"{BACKEND_URL}/api/chat/test"
REQUEST_TIMEOUT = 60.0


st.set_page_config(page_title="Agente Inmobiliaria — Prueba", page_icon="🏢")
st.title("🏢 Agente Inmobiliaria — Modo prueba")
st.caption(
    "Esto NO usa WhatsApp. Habla directo con el backend en "
    f"`{BACKEND_URL}` usando un teléfono ficticio aislado."
)

if "session_id" not in st.session_state:
    st.session_state.session_id = uuid.uuid4().hex[:12]

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.subheader("Sesión")
    st.code(st.session_state.session_id, language="text")
    st.caption(
        "El backend te trata como un usuario nuevo. Empezarás por el "
        "onboarding: edificio, número de depto y nombre."
    )
    if st.button("🔄 Nueva sesión", use_container_width=True):
        st.session_state.session_id = uuid.uuid4().hex[:12]
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.caption(f"Backend: `{BACKEND_URL}`")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_text = st.chat_input("Escribe un mensaje…")
if user_text:
    st.session_state.messages.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.markdown(user_text)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.markdown("_Pensando…_")
        try:
            response = httpx.post(
                CHAT_ENDPOINT,
                json={
                    "session_id": st.session_state.session_id,
                    "text": user_text,
                },
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            reply = response.json()["reply"]
        except httpx.HTTPStatusError as exc:
            reply = f"❌ Error HTTP {exc.response.status_code}: {exc.response.text}"
        except httpx.RequestError as exc:
            reply = (
                f"❌ No pude contactar al backend en {BACKEND_URL}. "
                f"¿Está corriendo `uv run uvicorn app.main:app --reload`?\n\n"
                f"Detalle: {exc}"
            )
        except Exception as exc:
            reply = f"❌ Error inesperado: {exc}"

        placeholder.markdown(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})
