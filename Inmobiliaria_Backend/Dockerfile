# Dockerfile del backend FastAPI para deploy en EasyPanel / Docker.
#
# Build context: Inmobiliaria_Backend/  (no la raíz del monorepo)
# Puerto interno: 8000

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

# Instalar uv (gestor de paquetes Python)
RUN pip install --no-cache-dir uv==0.5.*

WORKDIR /app

# 1) Instalar dependencias primero (cache-friendly: solo se reinstala si cambia
#    pyproject.toml o uv.lock).
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# 2) Copiar el código de la app.
COPY app ./app

# 3) Instalar el proyecto mismo.
RUN uv sync --frozen --no-dev

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
