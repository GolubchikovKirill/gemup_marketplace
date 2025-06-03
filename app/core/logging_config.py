"""
Конфигурация системы логирования.

Настройка структурированного логирования с ротацией файлов,
различными форматами для разных окружений и интеграцией с внешними системами.
"""

import logging
import logging.config
import os

from app.core.config import settings


def setup_logging() -> None:
    """
    Настройка системы логирования для приложения.

    Конфигурирует различные обработчики в зависимости от окружения.
    """
    # Создаем директорию для логов если её нет
    log_dir = "/app/logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    # Определяем уровень логирования
    log_level = settings.effective_log_level

    # Упрощенная конфигурация для стабильной работы
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "detailed": {
                "format": "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "stream": "ext://sys.stdout"
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "detailed",
                "filename": f"{log_dir}/app.log",
                "maxBytes": 10 * 1024 * 1024,  # 10MB
                "backupCount": 5,
                "encoding": "utf-8"
            }
        },
        "loggers": {
            "app": {
                "handlers": ["console", "file"],
                "level": log_level,
                "propagate": False
            },
            "uvicorn": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False
            },
            "alembic": {
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False
            }
        },
        "root": {
            "handlers": ["console"],
            "level": log_level
        }
    }

    logging.config.dictConfig(logging_config)


def get_logger(name: str) -> logging.Logger:
    """
    Получение настроенного логгера.

    Args:
        name: Имя логгера (обычно __name__)

    Returns:
        logging.Logger: Настроенный логгер
    """
    return logging.getLogger(f"app.{name}")


# Безопасная глобальная настройка при импорте
try:
    if not logging.getLogger().handlers:
        setup_logging()
except Exception as logging_setup_error:
    # Fallback к базовому логированию
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    print(f"Warning: Failed to setup advanced logging: {logging_setup_error}")
