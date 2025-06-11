#!/bin/bash
# scripts/start-render.sh

echo "🚀 Starting on Render..."

# Проверяем DATABASE_URL
if [ -z "$DATABASE_URL" ]; then
    echo "❌ DATABASE_URL not found!"
    exit 1
fi

echo "✅ DATABASE_URL found"

# Применяем миграции
echo "🔄 Running migrations..."
python -m alembic upgrade head

# Запускаем приложение
echo "🚀 Starting application..."
exec python main.py
