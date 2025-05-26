#!/bin/bash
set -e

echo "🔄 Ожидание готовности базы данных..."
while ! pg_isready -h ${POSTGRES_HOST:-db} -p ${POSTGRES_PORT:-5432} -U ${POSTGRES_USER:-gemup_user}; do
  echo "⏳ База данных не готова, ожидание..."
  sleep 2
done

echo "✅ База данных готова!"
echo "🔄 Применение миграций..."
/app/.venv/bin/alembic upgrade head
echo "✅ Миграции применены!"
