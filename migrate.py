#!/usr/bin/env python3
"""
Скрипт для применения миграций Alembic
"""

import sys
import os
from alembic.config import Config
from alembic import command


def run_migrations():
    """Применение миграций Alembic"""
    try:
        # Добавляем текущую директорию в Python path
        sys.path.insert(0, os.getcwd())

        # Создаем конфигурацию Alembic
        alembic_cfg = Config('alembic.ini')

        # Применяем миграции
        print("🔄 Применение миграций...")
        command.upgrade(alembic_cfg, 'head')
        print("✅ Миграции применены успешно!")

        return True

    except Exception as e:
        print(f"❌ Ошибка применения миграций: {e}")
        return False


if __name__ == "__main__":
    success = run_migrations()
    sys.exit(0 if success else 1)
