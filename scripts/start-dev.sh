#!/bin/bash
set -e

echo "🔧 Режим разработки"
echo "📁 Проверка .env файла..."
ls -la .env || echo "❌ .env файл отсутствует"

echo "🔄 Проверка виртуального окружения..."
if [ ! -f ".venv/pyvenv.cfg" ] || ! .venv/bin/python --version >/dev/null 2>&1; then
    echo "🔄 Пересоздание виртуального окружения..."
    rm -rf .venv
    uv sync --frozen --no-cache
fi

echo "🔄 Ожидание готовности базы данных..."
while ! pg_isready -h ${POSTGRES_HOST:-db} -p ${POSTGRES_PORT:-5432} -U ${POSTGRES_USER:-gemup_user}; do
  echo "⏳ База данных не готова, ожидание..."
  sleep 2
done

echo "✅ База данных готова!"
echo "🚀 Запуск приложения в режиме разработки..."

# Используем uvicorn напрямую с uv run
exec uv run uvicorn app.core.main:app --host 0.0.0.0 --port 8000 --reload
