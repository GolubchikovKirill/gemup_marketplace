#!/bin/bash
set -e

echo "🚀 Режим продакшена"
echo "🔄 Ожидание готовности базы данных..."
while ! pg_isready -h ${POSTGRES_HOST:-db} -p ${POSTGRES_PORT:-5432} -U ${POSTGRES_USER:-gemup_user}; do
  echo "⏳ База данных не готова, ожидание..."
  sleep 2
done

echo "✅ База данных готова!"
echo "🚀 Запуск приложения..."

# Используем uv run вместо прямого вызова fastapi
exec uv run fastapi run app/core/main.py --host 0.0.0.0 --port 8001
