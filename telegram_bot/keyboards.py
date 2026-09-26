from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from .config import config


def _site_url_is_public() -> bool:
    """True, если URL сайта подходит для Telegram-кнопки."""
    url = (config.SITE_URL or "").strip()
    if not url.startswith("https://"):
        return False
    if "localhost" in url or "127.0.0.1" in url:
        return False
    return True


def main_menu_kb() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text="👤 Мой профиль",
                callback_data="menu:profile",
            ),
            InlineKeyboardButton(
                text="📊 Статистика",
                callback_data="menu:stats",
            ),
        ],
        [
            InlineKeyboardButton(
                text="🔗 Привязать аккаунт",
                callback_data="menu:link",
            ),
        ],
    ]

    # Кнопку «Открыть сайт» показываем только если URL публичный и HTTPS
    if _site_url_is_public():
        rows[1].append(
            InlineKeyboardButton(
                text="🌐 Открыть сайт",
                url=config.SITE_URL,
            )
        )

    rows.append([
        InlineKeyboardButton(
            text="❓ Помощь",
            callback_data="menu:help",
        ),
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)