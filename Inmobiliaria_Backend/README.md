# Agente IA Inmobiliaria

Agente de IA para una empresa de gestión inmobiliaria. Recibe mensajes de
WhatsApp vía un workflow de **HighLevel**, los procesa con **LangChain + OpenAI**
y devuelve la respuesta para que HighLevel la envíe de vuelta al cliente.

> **Estado**: MVP — el agente responde de forma genérica para validar la
> conexión con HighLevel. Las consultas a Google Sheets (manutención, luz,
> agua, etc.) se conectan en una siguiente iteración.

## Stack

- Python 3.12
- FastAPI + Uvicorn
- LangChain + `langchain-openai`
- `uv` para gestión de dependencias

## Setup

```bash
# 1) Instalar dependencias
uv sync

# 2) Copiar variables de entorno y completar OPENAI_API_KEY
cp .env.example .env

# 3) Levantar el servidor en local
uv run uvicorn app.main:app --reload --port 8000
```

Endpoints:
- `GET  /health` — healthcheck
- `POST /api/highlevel/webhook` — recibe el webhook de HighLevel
- `GET  /docs` — Swagger UI

### Probar el webhook localmente

```bash
curl -X POST http://localhost:8000/api/highlevel/webhook \
  -H 'Content-Type: application/json' \
  -d '{"message": "Hola, ¿cuánto debo pagar este mes?", "contact_id": "abc123"}'
```

Respuesta esperada:

```json
{
  "respuesta_de_agente_ia": "Hola! Estoy revisando el sistema...",
  "contact_id": "abc123"
}
```

## Conectar con HighLevel

### 1) Exponer el endpoint

En desarrollo, expón tu `localhost:8000` con un túnel:

```bash
ngrok http 8000
# o
cloudflared tunnel --url http://localhost:8000
```

Te dará una URL pública tipo `https://abcd-1234.ngrok-free.app`.

### 2) Configurar el nodo Webhook en HighLevel

En el workflow que detecta mensajes entrantes de WhatsApp:

1. Añade un nodo **Custom Webhook** después del trigger.
2. **URL**: `https://<tu-tunel>/api/highlevel/webhook`
3. **Method**: `POST`
4. **Headers**: `Content-Type: application/json` (y opcionalmente
   `X-Webhook-Secret: <valor>` si pones `HIGHLEVEL_WEBHOOK_SECRET` en `.env`).
5. **Body** (JSON): incluir al menos `message` y `contact_id`. Puedes usar
   los Custom Values de HighLevel:
   ```json
   {
     "message": "{{message.body}}",
     "contact_id": "{{contact.id}}"
   }
   ```
6. **Response Mapping**: HighLevel permite mapear campos del JSON de respuesta
   a Custom Values del workflow. Mapea:
   - `respuesta_de_agente_ia` → un Custom Value, p. ej. `respuesta_ia`.

### 3) Enviar la respuesta por WhatsApp

Después del nodo Webhook, añade un nodo **Send WhatsApp Message** y usa el
Custom Value:

```
{{customValue.respuesta_ia}}
```

> **Nota sobre templates**: WhatsApp permite enviar texto libre dentro de la
> ventana de servicio de 24h que se abre cuando el cliente escribe primero.
> Como este flujo siempre responde a un mensaje entrante, no necesitas
> templates.

## Despliegue en DigitalOcean

(pendiente de iteración: `systemd` + `nginx` reverse proxy + HTTPS con
Certbot. Si quieres, lo armamos cuando el MVP esté validado).

## Estructura

```
app/
├── main.py              # FastAPI app factory
├── api/
│   └── highlevel.py     # POST /api/highlevel/webhook
├── agent/
│   └── chain.py         # LangChain + ChatOpenAI
└── core/
    └── config.py        # Settings desde .env
```
