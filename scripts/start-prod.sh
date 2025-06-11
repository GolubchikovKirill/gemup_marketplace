#!/bin/bash
set -e

echo "🚀 Режим продакшена"

# Проверяем DATABASE_URL
if [ -z "$DATABASE_URL" ]; then
    echo "❌ DATABASE_URL not found!"
    exit 1
fi

echo "✅ DATABASE_URL найден: ${DATABASE_URL:0:30}..."


echo "🔄 Применение миграций..."
python migrate.py

echo "🚀 Запуск приложения..."
exec python main.py
