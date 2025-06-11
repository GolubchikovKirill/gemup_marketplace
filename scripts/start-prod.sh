#!/bin/bash
set -e

echo "🚀 Режим продакшена"

# Проверяем наличие DATABASE_URL от Render
if [ -z "$DATABASE_URL" ]; then
    echo "❌ DATABASE_URL not found! Render должен предоставить его автоматически."
    exit 1
fi

echo "✅ DATABASE_URL найден: ${DATABASE_URL:0:30}..."

# Ждем готовности базы данных через DATABASE_URL
echo "🔄 Ожидание готовности базы данных..."
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if python -c "
import os
import psycopg2
try:
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    conn.close()
    print('✅ База данных готова!')
    exit(0)
except Exception as e:
    print(f'❌ Ошибка подключения: {e}')
    exit(1)
"; then
        echo "✅ Подключение к базе данных успешно!"
        break
    else
        echo "⏳ База данных не готова, попытка $((attempt + 1))/$max_attempts..."
        sleep 5
        attempt=$((attempt + 1))
    fi
done

if [ $attempt -eq $max_attempts ]; then
    echo "❌ Превышено время ожидания базы данных!"
    exit 1
fi

# Применение миграций
echo "🔄 Применение миграций..."
python -m alembic upgrade head

# Запуск приложения
echo "🚀 Запуск приложения..."
exec python main.py
