"""
Конфиг Telegram-бота.
Читает общий .env из корня проекта.
"""
import os
import importlib.util
from pathlib import Path

from dotenv import load_dotenv

# Корень проекта = на уровень выше telegram_bot/
ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT_DIR / ".env"
CONFIG_PATH = ROOT_DIR / "config.py"

load_dotenv(ENV_PATH)


# ===== Динамически загружаем корневой config.py =====
_spec = importlib.util.spec_from_file_location("root_config", CONFIG_PATH)
if _spec is None or _spec.loader is None:
    raise ImportError(f"Не удалось загрузить корневой config.py из {CONFIG_PATH}")

root_config = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(root_config)


class Config:
    # === Telegram ===
    BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    BOT_USERNAME: str = os.getenv("TELEGRAM_BOT_USERNAME", "NoW_Bot").lstrip("@")

    # === База ===
    DB_PATH: Path = ROOT_DIR / "data" / "economy.db"

    # === Общие настройки из корневого config.py ===
    GUILD_ID: int = root_config.GUILD_ID
    BOT_NAME: str = root_config.BOT_NAME
    CLAN_NAME: str = root_config.CLAN_NAME

    # === Сайт (для ссылок на настройки) ===
    SITE_URL: str = os.getenv("SITE_URL", "http://localhost:8000")

    # === Логи ===
    LOG_PATH: Path = ROOT_DIR / "logs" / "telegram_bot.log"

    # === Роли ===
    ADMIN_IDS: list[int] = [
        int(x) for x in os.getenv("TELEGRAM_ADMIN_IDS", "").split(",")
        if x.strip().isdigit()
    ]


config = Config()

if not config.BOT_TOKEN:
    raise RuntimeError(
        "TELEGRAM_BOT_TOKEN не задан в .env. "
        "Получи токен у @BotFather и добавь в корневой .env"
    )