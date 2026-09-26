"""
Конфигурация веб-дашборда.
Импортирует общие настройки из корневого config.py.
"""

import os
import importlib.util
from pathlib import Path

from dotenv import load_dotenv


# ===== Пути =====
ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT_DIR / "config.py"

# ===== Загружаем .env =====
load_dotenv(ROOT_DIR / ".env")


# ===== Динамически загружаем корневой config.py =====
_spec = importlib.util.spec_from_file_location("root_config", CONFIG_PATH)
if _spec is None or _spec.loader is None:
    raise ImportError(f"Не удалось загрузить корневой config.py из {CONFIG_PATH}")

root_config = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(root_config)


# ===== Общие настройки из корневого config.py =====
BOT_NAME = root_config.BOT_NAME
CLAN_NAME = root_config.CLAN_NAME
CURRENCY_NAME = root_config.CURRENCY_NAME
CURRENCY_EMOJI = root_config.CURRENCY_EMOJI
GUILD_ID = root_config.GUILD_ID

# ===== Web-настройки =====
WEB_HOST = os.getenv("WEB_HOST", "127.0.0.1")
WEB_PORT = int(os.getenv("WEB_PORT", "8000"))
WEB_SECRET_KEY = os.getenv("WEB_SECRET_KEY", "change-me-in-production")

# ===== Discord OAuth2 =====
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "")
DISCORD_REDIRECT_URI = os.getenv(
    "DISCORD_REDIRECT_URI",
    f"http://{WEB_HOST}:{WEB_PORT}/auth/callback",
)

# ===== Discord Bot Token (для получения ников и аватаров) =====
BOT_TOKEN = os.getenv("DISCORD_TOKEN", "")

# ===== БД =====
DB_PATH = ROOT_DIR / "data" / "economy.db"

# ===== Telegram =====
# @username бота БЕЗ собаки (например "NoW_Bot"), для Telegram Login Widget
TELEGRAM_BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME", "").lstrip("@")
# Токен бота из BotFather — для верификации hash от Login Widget
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")