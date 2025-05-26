FROM python:3.12-slim AS base

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Установка uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Копирование файлов зависимостей
COPY pyproject.toml uv.lock ./

FROM base AS development

# Установка всех зависимостей (включая dev)
RUN uv sync --frozen --no-cache

# Копирование .env файла
COPY .env ./

# Копирование конфигурации Alembic
COPY alembic.ini ./
COPY alembic/ ./alembic/

# Копирование скриптов
COPY scripts/ ./scripts/

# Копирование кода приложения
COPY . .

EXPOSE 8000
CMD ["/app/scripts/start-dev.sh"]

FROM base AS production

# Установка только production зависимостей
RUN uv sync --frozen --no-cache --no-dev

# Копирование конфигурации Alembic
COPY alembic.ini ./
COPY alembic/ ./alembic/

# Копирование скриптов
COPY scripts/ ./scripts/

# Копирование только необходимых файлов приложения
COPY app/ ./app/

EXPOSE 8000
CMD ["/app/scripts/start-prod.sh"]

