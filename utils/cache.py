"""
Кэш для тяжёлых запросов Nightmare.
Простой in-memory кэш с TTL.
"""

import time
import asyncio
from typing import Any, Optional, Callable


class TTLCache:
    """Кэш с временем жизни записей."""

    def __init__(self, default_ttl: int = 60):
        self._data: dict = {}
        self._default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        """Получить значение из кэша."""
        entry = self._data.get(key)
        if not entry:
            return None
        value, expires_at = entry
        if time.time() > expires_at:
            del self._data[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl: int = None) -> None:
        """Установить значение."""
        if ttl is None:
            ttl = self._default_ttl
        self._data[key] = (value, time.time() + ttl)

    def delete(self, key: str) -> None:
        """Удалить запись."""
        self._data.pop(key, None)

    def clear(self) -> None:
        """Очистить весь кэш."""
        self._data.clear()

    def cleanup(self) -> int:
        """Удаляет истёкшие записи. Возвращает количество удалённых."""
        now = time.time()
        expired = [k for k, (_, exp) in self._data.items() if now > exp]
        for k in expired:
            del self._data[k]
        return len(expired)

    def size(self) -> int:
        """Количество записей."""
        return len(self._data)


# ==================== ГЛОБАЛЬНЫЕ КЭШИ ====================

# Кэш балансов (TTL 5 сек)
balance_cache = TTLCache(default_ttl=5)

# Кэш данных пользователей (TTL 10 сек)
user_cache = TTLCache(default_ttl=10)

# Кэш топов (TTL 30 сек)
top_cache = TTLCache(default_ttl=30)

# Кэш настроек сервера (TTL 5 мин)
config_cache = TTLCache(default_ttl=300)

# Кэш тяжёлых вычислений
misc_cache = TTLCache(default_ttl=60)


# ==================== ДЕКОРАТОР ====================

def cached(cache: TTLCache, key_func: Callable = None, ttl: int = None):
    """
    Декоратор для кэширования результатов async-функции.

    Пример:
        @cached(balance_cache, key_func=lambda g, u: f"bal:{g}:{u}")
        async def get_balance(guild_id, user_id):
            ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                key = f"{func.__name__}:{args}:{tuple(sorted(kwargs.items()))}"

            cached_value = cache.get(key)
            if cached_value is not None:
                return cached_value

            result = await func(*args, **kwargs)
            if result is not None:
                cache.set(key, result, ttl)
            return result

        return wrapper
    return decorator


# ==================== ФОНОВЫЙ ОЧИСТИТЕЛЬ ====================

async def auto_cleanup(interval: int = 300):
    """Фоновая задача: очищает истёкшие записи каждые N секунд."""
    all_caches = [balance_cache, user_cache, top_cache, config_cache, misc_cache]
    while True:
        await asyncio.sleep(interval)
        total = sum(c.cleanup() for c in all_caches)
        if total:
            print(f"🧹 Кэш: очищено {total} истёкших записей.")