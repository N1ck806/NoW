"""
Точка входа Telegram-бота.
Запуск: python -m telegram_bot.main
"""
import asyncio
import logging
import sys
from pathlib import Path

# === Bootstrap для запуска как скрипта (python telegram_bot/main.py) ===
if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    __package__ = "telegram_bot"

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from .config import config
from .handlers import start, link, me, help

# Логи
config.LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(config.LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("telegram_bot")


async def main():
    logger.info("Запуск Telegram-бота...")
    logger.info(f"БД: {config.DB_PATH}")
    logger.info(f"Сайт: {config.SITE_URL}")
    logger.info(f"Guild ID: {config.GUILD_ID}")

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # Роутеры
    dp.include_router(start.router)
    dp.include_router(link.router)
    dp.include_router(me.router)
    dp.include_router(help.router)

    # Сбросить вебхуки и запустить polling
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Бот запущен. Polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен.")