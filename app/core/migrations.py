"""
Управление миграциями базы данных.

Интеграция с Alembic для автоматического выполнения миграций
при запуске приложения и управления версиями схемы БД.
"""

import asyncio
import logging
import os
from typing import Optional, List, Dict, Any
from concurrent.futures import ThreadPoolExecutor

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import text, create_engine
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings

logger = logging.getLogger(__name__)


class MigrationManager:
    """
    Менеджер миграций для управления версиями схемы базы данных.

    Обеспечивает автоматическое выполнение миграций, проверку версий
    и создание новых миграций в development окружении.
    """

    def __init__(self):
        """Инициализация менеджера миграций."""
        self.alembic_cfg: Optional[Config] = None
        self.alembic_ini_path = self._find_alembic_ini()

    @staticmethod
    def _find_alembic_ini() -> str:
        """
        Поиск файла alembic.ini в проекте.

        Returns:
            str: Путь к файлу alembic.ini
        """
        # Возможные пути к alembic.ini
        possible_paths = [
            "alembic.ini",
            "../alembic.ini",
            "../../alembic.ini",
            "/app/alembic.ini",
            os.path.join(os.path.dirname(__file__), "..", "..", "alembic.ini")
        ]

        for path in possible_paths:
            if os.path.exists(path):
                logger.debug(f"Found alembic.ini at: {path}")
                return os.path.abspath(path)

        # Если не найден, создаем путь по умолчанию
        default_path = "/app/alembic.ini"
        logger.warning(f"alembic.ini not found, using default path: {default_path}")
        return default_path

    def get_alembic_config(self) -> Config:
        """
        Получение конфигурации Alembic.

        Returns:
            Config: Объект конфигурации Alembic
        """
        if self.alembic_cfg is None:
            try:
                self.alembic_cfg = Config(self.alembic_ini_path)

                # Настройка URL базы данных (синхронный для Alembic)
                database_url = settings.database_url
                if database_url.startswith("postgresql+asyncpg://"):
                    database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")

                self.alembic_cfg.set_main_option("sqlalchemy.url", database_url)

                # Настройка путей
                script_location = self.alembic_cfg.get_main_option("script_location")
                if script_location and not os.path.isabs(script_location):
                    base_dir = os.path.dirname(self.alembic_ini_path)
                    script_location = os.path.join(base_dir, script_location)
                    self.alembic_cfg.set_main_option("script_location", script_location)

                logger.debug("Alembic configuration loaded successfully")

            except Exception as config_error:
                logger.error(f"Failed to load Alembic configuration: {config_error}")
                raise

        return self.alembic_cfg

    async def check_migration_status(self) -> Dict[str, Any]:
        """
        Проверка статуса миграций.

        Returns:
            Dict[str, Any]: Информация о текущем состоянии миграций
        """
        try:
            config = self.get_alembic_config()

            # Используем синхронный движок для совместимости с Alembic
            sync_database_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
            engine = create_engine(sync_database_url)

            def check_status():
                """Синхронная проверка статуса миграций."""
                try:
                    with engine.begin() as conn:
                        migration_context = MigrationContext.configure(conn)
                        current_revision = migration_context.get_current_revision()

                        script_dir = ScriptDirectory.from_config(config)
                        head_revision = script_dir.get_current_head()
                        revisions = list(script_dir.walk_revisions())

                        return {
                            "current_revision": current_revision,
                            "head_revision": head_revision,
                            "is_up_to_date": current_revision == head_revision,
                            "total_revisions": len(revisions),
                            "needs_upgrade": current_revision != head_revision
                        }
                finally:
                    engine.dispose()

            # Выполняем в thread pool
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                status = await loop.run_in_executor(executor, check_status)

            logger.info(f"Migration status: {status}")
            return status

        except Exception as status_error:
            logger.error(f"Error checking migration status: {status_error}")
            return {
                "error": str(status_error),
                "current_revision": None,
                "head_revision": None,
                "is_up_to_date": False,
                "needs_upgrade": False
            }

    async def run_migrations(self, target_revision: str = "head") -> bool:
        """
        Выполнение миграций до указанной ревизии.

        Args:
            target_revision: Целевая ревизия (по умолчанию "head")

        Returns:
            bool: True если миграции выполнены успешно
        """
        try:
            logger.info(f"🔄 Running migrations to revision: {target_revision}")

            config = self.get_alembic_config()

            def run_upgrade():
                """Синхронное выполнение upgrade."""
                command.upgrade(config, target_revision)

            # Выполняем в thread pool чтобы избежать greenlet ошибки
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                await loop.run_in_executor(executor, run_upgrade)

            logger.info("✅ Migrations completed successfully")
            return True

        except Exception as migration_error:
            logger.error(f"❌ Migration failed: {migration_error}")

            if settings.is_development():
                logger.exception("Migration traceback:")

            return False

    async def downgrade_migrations(self, target_revision: str) -> bool:
        """
        Откат миграций до указанной ревизии.

        Args:
            target_revision: Целевая ревизия для отката

        Returns:
            bool: True если откат выполнен успешно
        """
        try:
            logger.warning(f"⚠️ Downgrading migrations to revision: {target_revision}")

            config = self.get_alembic_config()

            def run_downgrade():
                """Синхронное выполнение downgrade."""
                command.downgrade(config, target_revision)

            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                await loop.run_in_executor(executor, run_downgrade)

            logger.info("✅ Migration downgrade completed")
            return True

        except Exception as downgrade_error:
            logger.error(f"❌ Migration downgrade failed: {downgrade_error}")
            return False

    def create_migration(self, migration_message: str, auto_generate: bool = True) -> bool:
        """
        Создание новой миграции.

        Args:
            migration_message: Сообщение для миграции
            auto_generate: Автоматическая генерация изменений

        Returns:
            bool: True если миграция создана успешно
        """
        try:
            if not settings.is_development():
                logger.error("Migration creation is only allowed in development environment")
                return False

            logger.info(f"Creating new migration: {migration_message}")

            config = self.get_alembic_config()

            if auto_generate:
                command.revision(config, message=migration_message, autogenerate=True)
            else:
                command.revision(config, message=migration_message)

            logger.info("✅ Migration created successfully")
            return True

        except Exception as create_error:
            logger.error(f"❌ Failed to create migration: {create_error}")
            return False

    async def get_migration_history(self) -> List[Dict[str, Any]]:
        """
        Получение истории миграций.

        Returns:
            List[Dict[str, Any]]: Список миграций с информацией
        """
        try:
            config = self.get_alembic_config()
            script_dir = ScriptDirectory.from_config(config)

            revisions = []
            for rev in script_dir.walk_revisions():
                revision_info = {
                    "revision": rev.revision,
                    "down_revision": rev.down_revision,
                    "branch_labels": getattr(rev, 'branch_labels', None),
                    "doc": rev.doc,
                    "path": rev.path if hasattr(rev, 'path') else str(rev.module)
                }
                revisions.append(revision_info)

            return revisions

        except Exception as history_error:
            logger.error(f"Error getting migration history: {history_error}")
            return []

    @staticmethod
    async def check_alembic_table() -> bool:
        """
        Проверка существования таблицы alembic_version.

        Returns:
            bool: True если таблица существует
        """
        try:
            engine = create_async_engine(settings.database_url)

            async with engine.begin() as conn:
                result = await conn.execute(text(
                    "SELECT EXISTS (SELECT FROM information_schema.tables "
                    "WHERE table_name = 'alembic_version')"
                ))
                exists = result.scalar()

            await engine.dispose()
            return bool(exists)

        except Exception as check_error:
            logger.error(f"Error checking alembic table: {check_error}")
            return False


# Глобальный экземпляр менеджера миграций
migration_manager = MigrationManager()


async def init_alembic() -> None:
    """
    Инициализация Alembic и выполнение миграций.

    Выполняется при запуске приложения для обеспечения
    актуальности схемы базы данных.
    """
    try:
        logger.info("🔄 Initializing Alembic migrations...")

        # Проверяем существование таблицы alembic_version
        if not await migration_manager.check_alembic_table():
            logger.info("📦 Alembic version table not found, initializing...")

            config = migration_manager.get_alembic_config()

            def stamp_head():
                """Синхронная инициализация."""
                command.stamp(config, "head")

            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                await loop.run_in_executor(executor, stamp_head)

            logger.info("✅ Alembic initialized with current head")
            return

        # Проверяем статус миграций
        status = await migration_manager.check_migration_status()

        if "error" in status:
            logger.error(f"❌ Migration check failed: {status['error']}")
            return

        # Выполняем миграции если необходимо
        if status.get("needs_upgrade", False):
            logger.info("📦 Database schema needs update, running migrations...")

            success = await migration_manager.run_migrations()

            if success:
                logger.info("✅ Database migrations completed successfully")
            else:
                logger.error("❌ Database migrations failed")

                if settings.is_production():
                    raise Exception("Critical: Database migrations failed in production")
        else:
            logger.info("✅ Database schema is up to date")

    except Exception as init_error:
        logger.error(f"❌ Alembic initialization failed: {init_error}")

        if settings.is_production():
            raise
        else:
            logger.warning("⚠️ Continuing startup without migrations (development mode)")


async def create_migration_async(message: str, auto_generate: bool = True) -> bool:
    """
    Асинхронное создание миграции.

    Args:
        message: Сообщение для миграции
        auto_generate: Автоматическая генерация

    Returns:
        bool: True если создано успешно
    """
    return migration_manager.create_migration(message, auto_generate)


async def check_migrations_status() -> Dict[str, Any]:
    """
    Асинхронная проверка статуса миграций.

    Returns:
        Dict[str, Any]: Статус миграций
    """
    return await migration_manager.check_migration_status()
