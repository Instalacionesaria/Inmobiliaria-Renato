# Dockerfile del frontend Streamlit para deploy en EasyPanel / Docker.
#
# Build context: Inmobiliaria_Frontend_Streamlit/  (no la raíz del monorepo)
# Puerto interno: 8501
#
# Variable de entorno requerida:
#   BACKEND_URL = https://api-de-tu-backend.easypanel.host
#                 (URL pública del Inmobiliaria_Backend)

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

RUN pip install --no-cache-dir uv==0.5.*

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY app.py ./

RUN uv sync --frozen --no-dev

EXPOSE 8501

# Flags de Streamlit en producción:
# - headless: no intenta abrir browser
# - address 0.0.0.0: escucha en todas las interfaces
# - gatherUsageStats false: no manda telemetría a Streamlit
# - enableCORS / enableXsrfProtection: deshabilitados para que funcione
#   detrás del proxy de EasyPanel sin warnings
CMD ["uv", "run", "streamlit", "run", "app.py", \
     "--server.address=0.0.0.0", \
     "--server.port=8501", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false", \
     "--server.enableCORS=false", \
     "--server.enableXsrfProtection=false"]
