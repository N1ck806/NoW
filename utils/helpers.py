"""
Общие вспомогательные функции Nightmare.
"""

import re
import random
import string
from datetime import datetime, timedelta


# ==================== ВРЕМЯ ====================

def parse_duration(duration: str) -> int:
    """
    Парсит '10s', '5m', '1h', '2d' в секунды.
    Возвращает None, если формат неверный.
    """
    if not duration:
        return None
    match = re.match(r"^(\d+)([smhd])$", duration.lower().strip())
    if not match:
        return None
    value = int(match.group(1))
    unit = match.group(2)
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    return value * units[unit]


def format_duration(seconds: int) -> str:
    """Форматирует секунды в 'Xд Xч Xм Xс'."""
    if seconds <= 0:
        return "0с"
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    parts = []
    if days:
        parts.append(f"{days}д")
    if hours:
        parts.append(f"{hours}ч")
    if minutes:
        parts.append(f"{minutes}м")
    if secs or not parts:
        parts.append(f"{secs}с")
    return " ".join(parts)


def format_timedelta(delta: timedelta) -> str:
    """Форматирует timedelta."""
    return format_duration(int(delta.total_seconds()))


def utcnow_iso() -> str:
    """Текущее время в ISO (UTC)."""
    return datetime.utcnow().isoformat()


def time_ago(dt_str: str) -> str:
    """Человекопонятное 'N назад'."""
    try:
        dt = datetime.fromisoformat(dt_str)
    except (ValueError, TypeError):
        return "неизвестно"

    delta = datetime.utcnow() - dt
    seconds = int(delta.total_seconds())

    if seconds < 60:
        return "только что"
    if seconds < 3600:
        return f"{seconds // 60} мин назад"
    if seconds < 86400:
        return f"{seconds // 3600} ч назад"
    if seconds < 2592000:
        return f"{seconds // 86400} дн назад"
    if seconds < 31536000:
        return f"{seconds // 2592000} мес назад"
    return f"{seconds // 31536000} г назад"


# ==================== ЧИСЛА ====================

def format_number(n: int) -> str:
    """Форматирует число с разделителями тысяч."""
    return f"{n:,}".replace(",", " ")


def short_number(n: int) -> str:
    """Сокращает: 1500 → 1.5K, 1500000 → 1.5M."""
    n = int(n)
    if abs(n) < 1000:
        return str(n)
    if abs(n) < 1_000_000:
        return f"{n / 1000:.1f}K".replace(".0K", "K")
    if abs(n) < 1_000_000_000:
        return f"{n / 1_000_000:.1f}M".replace(".0M", "M")
    return f"{n / 1_000_000_000:.1f}B".replace(".0B", "B")


def parse_amount(text: str, max_value: int = None) -> int:
    """
    Парсит '100', '1k', '1.5k', 'all', 'half'.
    Возвращает None, если не удалось.
    """
    if not text:
        return None
    text = text.lower().strip()

    if text in ("all", "все", "всё") and max_value is not None:
        return max_value
    if text in ("half", "половина") and max_value is not None:
        return max_value // 2

    multipliers = {"k": 1000, "к": 1000, "m": 1_000_000, "м": 1_000_000}
    if text[-1] in multipliers:
        try:
            return int(float(text[:-1]) * multipliers[text[-1]])
        except ValueError:
            return None

    try:
        return int(text)
    except ValueError:
        return None


# ==================== ТЕКСТ ====================

def truncate(text: str, length: int = 100, suffix: str = "...") -> str:
    """Обрезает строку."""
    if not text:
        return ""
    if len(text) <= length:
        return text
    return text[:length - len(suffix)] + suffix


def random_string(length: int = 8) -> str:
    """Случайная строка."""
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(length))


def progress_bar(current: int, total: int, length: int = 15, filled: str = "█", empty: str = "░") -> str:
    """Создаёт прогресс-бар."""
    if total <= 0:
        return empty * length
    filled_len = min(length, max(0, int(length * current / total)))
    return filled * filled_len + empty * (length - filled_len)


def pluralize(n: int, one: str, few: str, many: str) -> str:
    """Русская плюрализация: 1 монета, 2 монеты, 5 монет."""
    n = abs(n) % 100
    if 11 <= n <= 19:
        return many
    n = n % 10
    if n == 1:
        return one
    if 2 <= n <= 4:
        return few
    return many


# ==================== DISCORD ====================

def member_display(member) -> str:
    """Безопасное имя участника."""
    if member is None:
        return "Неизвестный"
    return getattr(member, "display_name", str(member))


def role_mention(role_id: int) -> str:
    """Упоминание роли."""
    return f"<@&{role_id}>"


def user_mention(user_id: int) -> str:
    """Упоминание пользователя."""
    return f"<@{user_id}>"


def channel_mention(channel_id: int) -> str:
    """Упоминание канала."""
    return f"<#{channel_id}>"


# ==================== РАНДОМ ====================

def weighted_choice(choices: list) -> any:
    """
    Выбор с весами. choices = [(item, weight), ...]
    """
    total = sum(w for _, w in choices)
    r = random.uniform(0, total)
    upto = 0
    for item, weight in choices:
        if upto + weight >= r:
            return item
        upto += weight
    return choices[-1][0]


def chance(percent: float) -> bool:
    """Случайное событие с шансом в процентах."""
    return random.random() * 100 < percent


# ==================== ВАЛИДАЦИЯ ====================

def is_valid_emoji(emoji: str) -> bool:
    """Проверяет, что строка похожа на эмодзи."""
    if not emoji:
        return False
    # Юникод-эмодзи (упрощённая проверка)
    if len(emoji) <= 8 and not emoji.isalnum():
        return True
    # Кастомный эмодзи <:name:id> или <a:name:id>
    return bool(re.match(r"^<a?:\w+:\d+>$", emoji))


def is_valid_url(url: str) -> bool:
    """Проверяет URL."""
    if not url:
        return False
    return bool(re.match(r"^https?://\S+$", url))


# ==================== ФАЙЛЫ ====================

def ensure_dir(path: str):
    """Создаёт папку, если её нет."""
    import os
    os.makedirs(path, exist_ok=True)