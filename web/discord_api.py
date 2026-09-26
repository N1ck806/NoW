"""
Обёртка над Discord REST API для получения ников, аватаров и ролей.
Простой in-memory кэш (TTL 1 час).
"""

import time
import asyncio
import httpx
from typing import Optional

DISCORD_API = "https://discord.com/api/v10"

# Кэш: {key: (data, expires_at)}
_cache: dict = {}
CACHE_TTL = 3600  # 1 час

# Ограничиваем параллелизм, чтобы не поймать rate-limit
_semaphore = asyncio.Semaphore(5)


# ==================== ПОЛЬЗОВАТЕЛИ ====================

async def fetch_user(user_id: int, bot_token: str) -> Optional[dict]:
    """
    Получает данные пользователя из Discord API.

    Возвращает dict или None.
    Ключи: id, username, global_name, display_name, avatar_url, bot.
    """
    if not bot_token:
        return None

    now = time.time()
    cache_key = f"user:{user_id}"

    if cache_key in _cache:
        data, expires = _cache[cache_key]
        if now < expires:
            return data

    async with _semaphore:
        url = f"{DISCORD_API}/users/{user_id}"
        headers = {"Authorization": f"Bot {bot_token}"}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=headers)

                if resp.status_code == 404:
                    _cache[cache_key] = (None, now + CACHE_TTL)
                    return None

                if resp.status_code != 200:
                    return None

                data = resp.json()

        except (httpx.RequestError, httpx.TimeoutException):
            return None
        except Exception:
            return None

    # Собираем аватар
    avatar_hash = data.get("avatar")
    if avatar_hash:
        ext = "gif" if avatar_hash.startswith("a_") else "png"
        avatar_url = (
            f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.{ext}?size=128"
        )
    else:
        default_index = (user_id >> 22) % 6
        avatar_url = f"https://cdn.discordapp.com/embed/avatars/{default_index}.png"

    result = {
        "id": data["id"],
        "username": data.get("username", ""),
        "global_name": data.get("global_name"),
        "display_name": data.get("global_name") or data.get("username") or f"ID {user_id}",
        "avatar_url": avatar_url,
        "bot": data.get("bot", False),
    }

    _cache[cache_key] = (result, now + CACHE_TTL)
    return result


async def fetch_users(user_ids: list, bot_token: str) -> dict:
    """
    Получает данные для нескольких пользователей параллельно.
    Возвращает {user_id: data}. Пропускает недоступных.
    """
    if not user_ids:
        return {}

    unique_ids = list(dict.fromkeys(user_ids))

    tasks = [fetch_user(uid, bot_token) for uid in unique_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    output = {}
    for uid, res in zip(unique_ids, results):
        if isinstance(res, dict):
            output[uid] = res

    return output


# ==================== УЧАСТНИКИ ГИЛЬДИИ (с ролями) ====================

async def fetch_guild_member(
    user_id: int,
    guild_id: int,
    bot_token: str,
) -> Optional[dict]:
    """
    Получает участника гильдии (включая роли).
    Возвращает dict или None.
    """
    if not bot_token:
        return None

    now = time.time()
    cache_key = f"member:{guild_id}:{user_id}"

    if cache_key in _cache:
        data, expires = _cache[cache_key]
        if now < expires:
            return data

    async with _semaphore:
        url = f"{DISCORD_API}/guilds/{guild_id}/members/{user_id}"
        headers = {"Authorization": f"Bot {bot_token}"}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=headers)

                if resp.status_code != 200:
                    _cache[cache_key] = (None, now + CACHE_TTL)
                    return None

                data = resp.json()

        except (httpx.RequestError, httpx.TimeoutException):
            return None
        except Exception:
            return None

    _cache[cache_key] = (data, now + CACHE_TTL)
    return data


async def fetch_guild_members(
    user_ids: list,
    guild_id: int,
    bot_token: str,
) -> dict:
    """Получает участников гильдии параллельно."""
    if not user_ids:
        return {}

    unique_ids = list(dict.fromkeys(user_ids))
    tasks = [fetch_guild_member(uid, guild_id, bot_token) for uid in unique_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    output = {}
    for uid, res in zip(unique_ids, results):
        if isinstance(res, dict):
            output[uid] = res

    return output


# ==================== КЭШ (синхронные) ====================

def get_cached_name(user_id: int) -> str:
    """Имя из кэша или 'ID {uid}'."""
    entry = _cache.get(f"user:{user_id}")
    if entry and entry[0]:
        return entry[0]["display_name"]
    return f"ID {user_id}"


def get_cached_avatar(user_id: int) -> Optional[str]:
    """URL аватара из кэша или None."""
    entry = _cache.get(f"user:{user_id}")
    if entry and entry[0]:
        return entry[0]["avatar_url"]
    return None


def get_cached_user(user_id: int) -> Optional[dict]:
    """Полные данные пользователя из кэша или None."""
    entry = _cache.get(f"user:{user_id}")
    return entry[0] if entry else None


def get_cached_roles(user_id: int, guild_id: int) -> list:
    """Список ролей участника из кэша (пустой, если нет данных)."""
    entry = _cache.get(f"member:{guild_id}:{user_id}")
    if entry and entry[0]:
        return entry[0].get("roles", [])
    return []


def clear_cache():
    """Очистить весь кэш."""
    _cache.clear()


def cache_size() -> int:
    """Количество записей в кэше."""
    return len(_cache)