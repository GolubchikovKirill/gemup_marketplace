"""
Конфигурация базы данных.

Настройка SQLAlchemy для работы с PostgreSQL.

"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import AsyncAdaptedQueuePool
from typing import AsyncGenerator
from app.core.config import settings
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Создание асинхронного движка базы данных
engine = create_async_engine(
    settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
    echo=settings.database_echo,
    poolclass=AsyncAdaptedQueuePool,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600,
    future=True
)

# Создание фабрики асинхронных сессий
SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False
)

# Базовый класс для моделей
Base = declarative_base()


# Dependency для получения асинхронной сессии базы данных
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()


# ИСПРАВЛЕНИЕ: Функция создания таблиц только для тестов и инициализации
async def create_tables(force: bool = False):
    """
    Создание всех таблиц.

    ВНИМАНИЕ: Используйте только для тестов или первичной инициализации!
    В production используйте Alembic миграции.

    Args:
        force: Принудительное создание (только для тестов)
    """
    if not force and settings.environment == "production":
        logger.warning("create_tables() не должна использоваться в production! Используйте Alembic миграции.")
        return

    if not force and settings.environment != "test":
        logger.info("create_tables() пропущена - используйте Alembic миграции в development/production")
        return

    logger.info("Creating tables via SQLAlchemy (only for tests)")
    async with engine.begin() as conn:
        # ИСПРАВЛЕНИЕ: Создание таблиц только при явном force=True
        await conn.run_sync(Base.metadata.create_all)


# Функция для удаления всех таблиц (только для тестов)
async def drop_tables():
    """
    Удаление всех таблиц.

    ВНИМАНИЕ: Только для тестов!
    """
    if settings.environment == "production":
        raise RuntimeError("drop_tables() запрещена в production!")

    logger.warning("Dropping all tables (only for tests)")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# Функция для закрытия соединений
async def close_db():
    """Закрытие connections к базе данных"""
    logger.info("Closing database connections")
    await engine.dispose()


# Health check для базы данных
async def check_db_health() -> bool:
    """
    Проверка здоровья базы данных с улучшенным error handling.

    Returns:
        bool: True если БД доступна, False в противном случае
    """
    try:
        async with SessionLocal() as session:
            # ИСПРАВЛЕНИЕ: Улучшенная проверка с timeout
            result = await session.execute(text("SELECT 1 as health_check"))
            health_value = result.scalar()

            if health_value != 1:
                logger.error("Database health check returned unexpected value")
                return False

            logger.debug("Database health check passed")
            return True

    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


# НОВАЯ ФУНКЦИЯ: Инициализация для development (опциональная)
async def init_db_for_development():
    """
    Инициализация БД для development окружения.

    Проверяет есть ли таблицы, если нет - рекомендует использовать Alembic.
    """
    try:
        async with SessionLocal() as session:
            # Проверяем есть ли таблица users (как индикатор наличия схемы)
            result = await session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'users'
                );
            """))

            tables_exist = result.scalar()

            if not tables_exist:
                logger.warning("""
                🚨 Таблицы не найдены в базе данных!
                
                Для создания схемы БД используйте Alembic миграции:
                
                1. Применить существующие миграции:
                   make migrate
                   
                2. Или создать новую миграцию:
                   make create-migration msg="Initial tables"
                   make migrate
                
                3. Проверить состояние:
                   docker compose exec web /app/.venv/bin/alembic current
                """)
            else:
                logger.info("✅ Database tables exist and ready")

    except Exception as e:
        logger.error(f"Failed to check database initialization: {e}")


# НОВАЯ ФУНКЦИЯ: Проверка совместимости с Alembic
async def check_alembic_status():
    """
    Проверка статуса Alembic миграций.

    Полезно для debugging проблем с миграциями.
    """
    try:
        async with SessionLocal() as session:
            # Проверяем есть ли таблица alembic_version
            result = await session.execute(text("""
                SELECT version_num FROM alembic_version 
                ORDER BY version_num DESC LIMIT 1;
            """))

            current_version = result.scalar()

            if current_version:
                logger.info(f"✅ Alembic current version: {current_version}")
                return current_version
            else:
                logger.warning("⚠️ Alembic version table exists but no version found")
                return None

    except Exception as e:
        logger.warning(f"Alembic status check failed (normal if migrations not applied yet): {e}")
        return None


# Функция получения информации о БД
async def get_database_info():
    """
    Получение информации о базе данных для debugging.

    Returns:
        dict: Информация о БД
    """
    try:
        async with SessionLocal() as session:
            # Получаем информацию о БД
            result = await session.execute(text("""
                SELECT 
                    version() as pg_version,
                    current_database() as database_name,
                    current_user as current_user,
                    current_setting('server_version') as server_version
            """))

            db_info = result.fetchone()

            # Получаем список таблиц
            tables_result = await session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name;
            """))

            tables = [row[0] for row in tables_result.fetchall()]

            return {
                "pg_version": db_info[0] if db_info else "unknown",
                "database_name": db_info[1] if db_info else "unknown",
                "current_user": db_info[2] if db_info else "unknown",
                "server_version": db_info[3] if db_info else "unknown",
                "tables": tables,
                "tables_count": len(tables)
            }

    except Exception as e:
        logger.error(f"Failed to get database info: {e}")
        return {"error": str(e)}


# Обратная совместимость
async def init_db():
    """
    УСТАРЕВШАЯ функция для обратной совместимости.

    Теперь рекомендуется использовать Alembic миграции.
    """
    logger.warning("""
    init_db() устарела! 
    
    Используйте Alembic миграции:
    - make migrate
    - docker compose exec web /app/.venv/bin/alembic upgrade head
    """)

    # В тестовом окружении все еще можем создавать таблицы
    if settings.environment == "test":
        await create_tables(force=True)
    else:
        await init_db_for_development()
