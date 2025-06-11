"""
Модуль безопасности для проверки webhook подписей.
"""

import hashlib
import hmac


def verify_webhook_signature(
        payload: bytes,
        signature: str,
        secret: str
) -> bool:
    """
    Проверка подписи webhook.

    Args:
        payload: Тело запроса в байтах
        signature: Подпись из заголовка
        secret: Секретный ключ

    Returns:
        bool: True если подпись валидна
    """
    try:
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()

        # Убираем префиксы типа "sha256="
        if signature.startswith('sha256='):
            signature = signature[7:]

        return hmac.compare_digest(expected_signature, signature)
    except Exception:
        return False


def generate_webhook_signature(payload: bytes, secret: str) -> str:
    """
    Генерация подписи для webhook.

    Args:
        payload: Тело запроса в байтах
        secret: Секретный ключ

    Returns:
        str: Подпись
    """
    signature = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()

    return f"sha256={signature}"
