#!/bin/bash
set -e

echo "🧪 Запуск тестов..."
/app/.venv/bin/pytest -v
echo "✅ Тесты завершены!"
