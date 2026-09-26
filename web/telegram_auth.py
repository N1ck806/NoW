"""
Верификация данных Telegram Login Widget.
"""

import hashlib
import hmac
import time
from typing import Optional


def verify_telegram_auth(data: dict, bot_token: str) -> bool:
    """
    Проверяет подпись данных, полученных от Telegram Login Widget.

    data — dict с полями: id, first_name, last_name, username, photo_url, auth_date, hash
    bot_token — токен бота из BotFather
    """
    if not data or not bot_token:
        return False

    received_hash = data.get("hash")
    if not received_hash:
        return False

    # Собираем data_check_string
    check_data = {k: v for k, v in data.items() if k != "hash" and v is not None}

    # Сортируем по алфавиту
    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(check_data.items())
    )

    # Секретный ключ — SHA256 от токена бота
    secret_key = hashlib.sha256(bot_token.encode()).digest()

    # Считаем HMAC-SHA256
    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()

    # Сравниваем хэши
    if not hmac.compare_digest(calculated_hash, received_hash):
        return False

    # Проверяем время (не старше 24 часов)
    auth_date = data.get("auth_date")
    if auth_date:
        try:
            auth_timestamp = int(auth_date)
            if time.time() - auth_timestamp > 86400:
                return False
        except (ValueError, TypeError):
            return False

    return True