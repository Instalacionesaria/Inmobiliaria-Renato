# Agente IA Inmobiliaria — Denise

Agente conversacional para administraciones de edificios. Atiende consultas de propietarios e inquilinos sobre su cuota mensual, montos y datos de su departamento, a través de **WhatsApp** (vía HighLevel) o de una **UI web de prueba** (Streamlit).

La agente se llama **Denise**. Lee los datos del cliente desde un **Google Sheet** (una pestaña por edificio) y conversa usando **GPT-4.1**, manteniendo el historial en **Postgres (Supabase)**.

---

## Arquitectura

Este repo es un **monorepo con 3 apps independientes**:

```
┌─────────────────────────────────────────────────────────────┐
│  Inmobiliaria_Backend  (FastAPI + LangChain)                │
│  ├─ /api/highlevel/webhook   ← mensajes de WhatsApp         │
│  ├─ /api/chat/test           ← endpoint del Streamlit       │
│  ├─ /api/admin/*             ← login + editor de prompt     │
│  └─ /health                                                  │
└──────────────┬──────────────────────────┬───────────────────┘
               │                          │
       ┌───────▼────────┐         ┌───────▼─────────────────┐
       │  Google Sheets │         │  Supabase Postgres      │
       │  (1 pestaña    │         │  - chat_history         │
       │   por edificio)│         │  - contacts             │
       └────────────────┘         │  - prompts (editable)   │
                                  │  - admin_users          │
                                  │  - settings             │
                                  └─────────────────────────┘

┌─────────────────────────────┐    ┌───────────────────────────┐
│  Inmobiliaria_Frontend      │    │  Inmobiliaria_Frontend_   │
│  (React + Vite + TS)        │    │  Streamlit (Python)       │
│                             │    │                           │
│  Panel admin:               │    │  UI de chat para que      │
│  - Login                    │    │  el cliente pruebe a      │
│  - Editor del prompt        │    │  Denise sin conectar      │
│  - Toggle global del agente │    │  WhatsApp                 │
└─────────────────────────────┘    └───────────────────────────┘
        ↓ habla con backend                ↓ habla con backend
```

---

## Stack

| Componente | Tecnología |
|---|---|
| Backend | Python 3.12, FastAPI, LangChain, OpenAI (GPT-4.1) |
| Frontend admin | React 18, Vite, TypeScript |
| Frontend de prueba | Streamlit |
| Base de datos | Postgres (Supabase) |
| Almacenamiento de datos del cliente | Google Sheets (vía service account) |
| Canal de mensajería | HighLevel (WhatsApp) |
| Gestión de dependencias Python | uv |
| Deploy | Docker + EasyPanel sobre DigitalOcean |

---

## Estructura del repo

```
.
├── Inmobiliaria_Backend/              # API FastAPI
│   ├── app/
│   │   ├── main.py                    # app factory
│   │   ├── agent/flow.py              # onboarding + chat
│   │   ├── api/
│   │   │   ├── highlevel.py           # webhook de WhatsApp
│   │   │   ├── chat.py                # endpoint para Streamlit
│   │   │   └── admin.py               # API del panel admin
│   │   ├── prompts/                   # prompts del agente
│   │   │   ├── chat_default.py        # semilla del prompt principal
│   │   │   └── onboarding.py          # prompt de extracción de datos
│   │   ├── services/
│   │   │   ├── sheet_client.py        # cliente de Google Sheets
│   │   │   └── highlevel_client.py    # cliente de HighLevel
│   │   └── storage/                   # capa de datos (Postgres)
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── prompt_para_copiar.md          # prompt versionable para Supabase
│
├── Inmobiliaria_Frontend/             # Panel admin (React)
│   ├── src/
│   │   ├── components/
│   │   │   ├── LoginPage.tsx
│   │   │   ├── PromptEditor.tsx
│   │   │   └── AgentToggle.tsx
│   │   └── lib/api.ts
│   └── package.json
│
└── Inmobiliaria_Frontend_Streamlit/   # UI de prueba
    ├── app.py
    ├── Dockerfile
    └── pyproject.toml
```

---

## Setup local

### Requisitos
- Python 3.12
- [uv](https://docs.astral.sh/uv/) (`brew install uv` en macOS)
- Node.js 20+ (solo si vas a correr el panel admin)

### Backend

```bash
cd Inmobiliaria_Backend
uv sync
cp .env.example .env
# Completar las variables en .env (ver sección "Variables de entorno")
uv run uvicorn app.main:app --reload --port 8000
```

API disponible en http://localhost:8000. Swagger en http://localhost:8000/docs.

### Streamlit (UI de prueba)

```bash
cd Inmobiliaria_Frontend_Streamlit
uv sync
uv run streamlit run app.py
```

UI en http://localhost:8501. Si el backend está en otro puerto:

```bash
BACKEND_URL=http://127.0.0.1:9000 uv run streamlit run app.py
```

### Panel admin (React)

```bash
cd Inmobiliaria_Frontend
npm install
cp .env.example .env
npm run dev
```

Panel en http://localhost:5173. Credenciales iniciales: `admin` / `admin` (configurables en `.env`).

---

## Variables de entorno (Backend)

Las variables están documentadas en `Inmobiliaria_Backend/.env.example`. Resumen:

| Variable | Obligatoria | Notas |
|---|---|---|
| `OPENAI_API_KEY` | ✅ | Key de OpenAI |
| `OPENAI_MODEL` | | Default `gpt-4o-mini`. En prod usamos `gpt-4.1` |
| `SHEET_ID` | ✅ | ID del Google Sheet con los datos por edificio |
| `GOOGLE_SERVICE_ACCOUNT_FILE` | (dev) | Path al JSON de la service account |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | (prod) | Contenido del JSON en una línea, o en base64 |
| `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME` | ✅ | Conexión a Supabase |
| `ADMIN_USERNAME`, `ADMIN_PASSWORD` | ✅ | Login inicial del admin (solo se usan la primera vez) |
| `ADMIN_JWT_SECRET` | ✅ | Secret para firmar JWT. Generar con `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `CORS_ALLOWED_ORIGINS` | | Lista CSV de orígenes permitidos para el panel admin |
| `HIGHLEVEL_API_TOKEN`, `LOCATION_ID`, `HIGHLEVEL_WEBHOOK_SECRET` | | Solo si conectas WhatsApp |

---

## Deploy en producción

El proyecto está pensado para correr en **EasyPanel sobre DigitalOcean**, pero cualquier plataforma que corra Docker funciona.

### Servicios a desplegar

| Servicio | Build context | Puerto |
|---|---|---|
| Backend | `/Inmobiliaria_Backend` | 8000 |
| Streamlit (opcional) | `/Inmobiliaria_Frontend_Streamlit` | 8501 |
| Panel admin (opcional) | `/Inmobiliaria_Frontend` | (deploy en Vercel) |

### Pasos en EasyPanel

1. Crear servicio APP con tipo **Dockerfile**, apuntando al repo y la ruta de compilación correcta.
2. Configurar las variables de entorno (ver tabla arriba).
3. Configurar el dominio con HTTPS, puerto interno según el servicio.
4. Deploy. EasyPanel construye desde el Dockerfile y arranca el container.

Para el Streamlit, además de las variables del backend, configurar:

```env
BACKEND_URL=https://<url-pública-del-backend>
```

---

## Editar el prompt del agente

El prompt principal del chat **vive en Supabase** (tabla `inmobiliaria_prompts`, key `chat_system`) y se edita desde el panel admin sin necesidad de redeploy. Cache de 30 segundos.

Para hacer rollback al default o ver el prompt actual:
- Ver `Inmobiliaria_Backend/prompt_para_copiar.md` (versión versionable)
- O `Inmobiliaria_Backend/app/prompts/chat_default.py` (semilla en código)

El prompt de **onboarding** (extracción de edificio/depto/nombre) **no es editable** y vive en `Inmobiliaria_Backend/app/prompts/onboarding.py`.

---

## Flujo de conversación

```
Cliente:  "Hola"
Denise:   "¡Hola! Soy Denise, la asistente virtual de la administración.
           Para ayudarte necesito tres datos: tu edificio, tu número de
           departamento (ej: 101) y tu nombre."

Cliente:  "Vivo en La Joya, depto 604, mi nombre es Kevin"
Denise:   [valida contra el sheet]
          "¡Listo, Kevin! Te identifiqué como propietario del depto 604
           del edificio La Joya. ¿En qué puedo ayudarte?"

Cliente:  "Cuánto debo pagar este mes?"
Denise:   [lee el sheet del cliente]
          "Tu cuota total de este mes es S/ 350,80. ¿Quieres que te
           detalle los conceptos?"
```

---

## Licencia

Privado — uso interno.
