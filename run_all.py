"""
NoW_Bot — единая точка входа для Render.
Запускает сайт + Telegram-бот + Discord-бот в одном процессе.

ВАЖНО: каждая часть изолирована, падение одной не убивает остальные.
"""
import asyncio
import importlib
import logging
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv
load_dotenv(ROOT_DIR / ".env")

LOG_DIR = ROOT_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "run_all.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("run_all")


def _enabled(name: str) -> bool:
    """ENABLE_WEBSITE=0 / ENABLE_TELEGRAM=0 / ENABLE_DISCORD=0 / ENABLE_SELF_PING=0"""
    return os.getenv(f"ENABLE_{name.upper()}", "1") == "1"


# ============================================================
# 1. САЙТ (FastAPI / uvicorn)
# ============================================================

async def run_website():
    """Запускает FastAPI-сайт через uvicorn в текущем event loop."""
    import uvicorn

    port = int(os.getenv("PORT", os.getenv("WEB_PORT", "8000")))
    host = os.getenv("WEB_HOST", "0.0.0.0")

    config = uvicorn.Config(
        "web.app:app",
        host=host,
        port=port,
        log_level="info",
        loop="asyncio",
        reload=False,          # reload=True ломает запуск в одном процессе
        access_log=False,
    )
    server = uvicorn.Server(config)

    logger.info(f"🌐 Сайт: http://{host}:{port}")
    await server.serve()


# ============================================================
# 2. TELEGRAM-БОТ (aiogram)
# ============================================================

async def _telegram_once():
    """
    Один запуск Telegram-бота. Бросает исключение при падении.

    ВАЖНО: используем importlib.reload() на модулях хендлеров, чтобы получить
    СВЕЖИЕ Router-объекты. aiogram 3.x запрещает привязывать один Router
    к двум Dispatcher — без reload при перезапуске будет RuntimeError
    "Router is already attached to <Dispatcher>".
    """
    from aiogram import Bot, Dispatcher
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode

    from telegram_bot.config import config as tg_config

    # Свежие модули хендлеров — новые Router-объекты
    from telegram_bot.handlers import start, link, me, help as help_mod
    importlib.reload(start)
    importlib.reload(link)
    importlib.reload(me)
    importlib.reload(help_mod)

    bot = Bot(
        token=tg_config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(start.router)
    dp.include_router(link.router)
    dp.include_router(me.router)
    dp.include_router(help_mod.router)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("📱 Telegram-бот запущен (polling)")
        await dp.start_polling(bot)
    finally:
        try:
            await bot.session.close()
        except Exception:
            pass


async def run_telegram_bot():
    """Обёртка с авто-перезапуском при TelegramConflictError и других ошибках."""
    while True:
        try:
            await _telegram_once()
        except asyncio.CancelledError:
            logger.info("📱 Telegram-бот остановлен")
            raise
        except Exception as e:
            logger.error(f"❌ Telegram упал: {e!r}")
            logger.info("⏳ Перезапуск Telegram-бота через 15 сек...")
            await asyncio.sleep(15)


# ============================================================
# 3. DISCORD-БОТ (discord.py)
# ============================================================

async def _discord_once():
    """Один запуск Discord-бота. Бросает исключение при падении."""
    import config as dc_config
    from utils import database as db, logger as log_module, cache
    import discord
    from discord.ext import commands

    token = getattr(dc_config, "TOKEN", None) or os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN не задан")

    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    intents.reactions = True
    intents.voice_states = True

    bot = commands.Bot(
        command_prefix=dc_config.COMMAND_PREFIX,
        intents=intents,
        help_command=None,
    )

    @bot.event
    async def on_ready():
        logger.info("=" * 60)
        logger.info(f"✅ Discord-бот {dc_config.BOT_NAME} подключён")
        logger.info(f"Клан: {dc_config.CLAN_NAME}")
        logger.info(f"Серверов: {len(bot.guilds)}")
        for guild in bot.guilds:
            logger.info(f"  • {guild.name} (ID: {guild.id})")
        logger.info(f"Модулей: {len(bot.cogs)} | Команд: {len(bot.commands)}")
        logger.info("=" * 60)

        log_module.log.info(
            f"Discord-бот запущен. Модулей: {len(bot.cogs)}, команд: {len(bot.commands)}"
        )

        await bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{dc_config.COMMAND_PREFIX}help • {dc_config.CLAN_NAME}",
            )
        )

        bot.loop.create_task(_backup_db_loop(bot, log_module))
        bot.loop.create_task(cache.auto_cleanup(300))

    @bot.event
    async def on_command_error(ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        logger.error(f"❌ Ошибка команды {ctx.command}: {error}")
        try:
            log_module.log_exception(error, context=f"cmd={ctx.command}")
        except Exception:
            pass

    db.init_db()
    logger.info("📁 Discord БД инициализирована")

    COGS = [
        "cogs.moderation", "cogs.economy", "cogs.activity", "cogs.roles",
        "cogs.welcome", "cogs.stats", "cogs.games", "cogs.utility",
        "cogs.admin", "cogs.shop", "cogs.quests", "cogs.reputation",
        "cogs.achievements", "cogs.voice", "cogs.analytics", "cogs.events",
    ]
    loaded, failed = [], []
    for cog in COGS:
        try:
            await bot.load_extension(cog)
            loaded.append(cog)
        except Exception as e:
            failed.append(cog)
            logger.warning(f"⚠️ Cog {cog} не загружен: {e}")

    logger.info(f"📦 Discord cog'ов загружено: {len(loaded)}/{len(COGS)}")
    if failed:
        logger.warning(f"❌ Не загружено: {', '.join(failed)}")

    try:
        await bot.start(token)
    finally:
        try:
            await bot.close()
        except Exception:
            pass


async def run_discord_bot():
    """Обёртка с авто-перезапуском."""
    while True:
        try:
            await _discord_once()
        except asyncio.CancelledError:
            logger.info("💬 Discord-бот остановлен")
            raise
        except Exception as e:
            logger.error(f"❌ Discord упал: {e!r}")
            logger.info("⏳ Перезапуск Discord-бота через 15 сек...")
            await asyncio.sleep(15)


# ============================================================
# 4. БЭКАП SQLite
# ============================================================

async def _backup_db_loop(bot, log_module):
    """Бэкап data/economy.db каждые 6 часов."""
    import shutil
    from datetime import datetime, timezone

    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            backup_dir = ROOT_DIR / "data" / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)

            db_path = ROOT_DIR / "data" / "economy.db"
            if db_path.exists():
                ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                backup_path = backup_dir / f"economy_{ts}.db"
                shutil.copy2(db_path, backup_path)
                log_module.log.info(f"Бэкап БД: {backup_path}")

                backups = sorted(backup_dir.glob("*.db"), reverse=True)
                for old in backups[20:]:
                    try:
                        old.unlink()
                    except OSError:
                        pass
        except Exception as e:
            try:
                log_module.log_exception(e, context="backup_db_loop")
            except Exception:
                logger.error(f"❌ backup_db_loop: {e!r}")

        await asyncio.sleep(6 * 3600)


# ============================================================
# 5. SELF-PING (чтобы Render free не засыпал)
# ============================================================

async def run_self_ping():
    """
    Стучится в свой /health каждые 14 минут.
    Работает только если Render передал RENDER_EXTERNAL_URL.
    """
    url = os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/")
    if not url:
        logger.info("🔕 Self-ping: RENDER_EXTERNAL_URL не задан — пропуск")
        return

    import httpx

    logger.info(f"🔁 Self-ping: {url}/health каждые 14 мин")
    async with httpx.AsyncClient(timeout=10) as client:
        while True:
            await asyncio.sleep(14 * 60)
            try:
                r = await client.get(f"{url}/health")
                logger.debug(f"🔁 self-ping → {r.status_code}")
            except Exception as e:
                logger.warning(f"⚠️ self-ping ошибка: {e}")


# ============================================================
# ГЛАВНОЕ
# ============================================================

async def main():
    logger.info("🌑 Запуск NoW_Bot Cluster...")
    logger.info(f"📂 Корень: {ROOT_DIR}")

    tasks = []
    if _enabled("website"):
        tasks.append(asyncio.create_task(run_website(), name="website"))
    else:
        logger.info("🔕 Website отключён (ENABLE_WEBSITE=0)")

    if _enabled("telegram"):
        tasks.append(asyncio.create_task(run_telegram_bot(), name="telegram"))
    else:
        logger.info("🔕 Telegram отключён (ENABLE_TELEGRAM=0)")

    if _enabled("discord"):
        tasks.append(asyncio.create_task(run_discord_bot(), name="discord"))
    else:
        logger.info("🔕 Discord отключён (ENABLE_DISCORD=0)")

    if _enabled("self_ping"):
        tasks.append(asyncio.create_task(run_self_ping(), name="self_ping"))

    if not tasks:
        logger.error("❌ Нечего запускать — все части отключены")
        return

    try:
        # ВАЖНО: gather, а не wait(FIRST_EXCEPTION) —
        # падение одной задачи НЕ убивает остальные.
        await asyncio.gather(*tasks, return_exceptions=False)
    except (KeyboardInterrupt, SystemExit):
        logger.info("👋 Остановка...")
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
