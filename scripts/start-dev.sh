# scripts/start-dev.sh
#!/bin/bash
set -e

echo "🔧 Режим разработки"
echo "🔄 Ожидание готовности базы данных..."
while ! pg_isready -h ${POSTGRES_HOST:-db} -p ${POSTGRES_PORT:-5432} -U ${POSTGRES_USER:-gemup_user}; do
  echo "⏳ База данных не готова, ожидание..."
  sleep 2
done

echo "✅ База данных готова!"

# Проверяем, нужны ли миграции
echo "🔄 Проверка миграций..."
CURRENT_REV=$(/app/.venv/bin/alembic current 2>/dev/null | grep -o '[a-f0-9]\{12\}' || echo "none")
HEAD_REV=$(/app/.venv/bin/alembic heads 2>/dev/null | grep -o '[a-f0-9]\{12\}' || echo "none")

if [ "$CURRENT_REV" != "$HEAD_REV" ]; then
    echo "🔄 Применение миграций..."
    /app/.venv/bin/alembic upgrade head
    echo "✅ Миграции применены!"
else
    echo "✅ Миграции актуальны"
fi

echo "🚀 Запуск приложения..."
exec uv run uvicorn app.core.main:app --host 0.0.0.0 --port 8000 --reload
