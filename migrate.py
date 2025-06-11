#!/usr/bin/env python3
"""
Скрипт для применения миграций Alembic на Render
"""

import sys
import os


sys.path.insert(0, '/app')
sys.path.insert(0, '/app/app')
sys.path.insert(0, '.')


def run_migrations():
    """Применение миграций Alembic"""
    try:
        from alembic.config import Config
        from alembic import command

        # Ищем alembic.ini в разных местах
        alembic_ini_paths = [
            '/app/alembic.ini',
            '/app/app/alembic.ini',
            'alembic.ini'
        ]

        alembic_ini = None
        for path in alembic_ini_paths:
            if os.path.exists(path):
                alembic_ini = path
                break

        if not alembic_ini:
            print("❌ alembic.ini не найден!")
            return False

        print(f"✅ Используем alembic.ini: {alembic_ini}")

        # Создаем конфигурацию Alembic
        alembic_cfg = Config(alembic_ini)

        # Применяем миграции
        print("🔄 Применение миграций...")
        command.upgrade(alembic_cfg, 'head')
        print("✅ Миграции применены успешно!")

        return True

    except Exception as e:
        print(f"❌ Ошибка применения миграций: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_migrations()
    sys.exit(0 if success else 1)
