import asyncio
import sys
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

sys.path.insert(0, '/app')

from app.core.config import settings

from app.models.models import Base

def import_models():
    """Принудительный импорт всех моделей"""
    from app.models.models import (
        User, ProxyProduct, Order, OrderItem, Transaction,
        ProxyPurchase, ShoppingCart, Permission, Role, APIKey
    )
    print(f'Imported {len(Base.metadata.tables)} tables: {list(Base.metadata.tables.keys())}')

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Импортируем модели
import_models()

target_metadata = Base.metadata

def get_url():
    return settings.database_url

def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={'paramstyle': 'named'},
    )

    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration['sqlalchemy.url'] = get_url()

    connectable = async_engine_from_config(
        configuration,
        prefix='sqlalchemy.',
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
