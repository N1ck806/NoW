"""
Nightmare — бот клана Nightmare of Whiners.
Точка входа.
"""

import discord
from discord.ext import commands
import asyncio
import os
import shutil
from datetime import datetime, timezone

import config
from utils import database as db
from utils import logger as log_module
from utils import cache


intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True
intents.voice_states = True


bot = commands.Bot(
    command_prefix=config.COMMAND_PREFIX,
    intents=intents,
    help_command=None,
)


COGS = [
    "cogs.moderation",
    "cogs.economy",
    "cogs.activity",
    "cogs.roles",
    "cogs.welcome",
    "cogs.stats",
    "cogs.games",
    "cogs.utility",
    "cogs.admin",
    "cogs.shop",
    "cogs.quests",
    "cogs.reputation",
    "cogs.achievements",
    "cogs.voice",
    "cogs.analytics",
    "cogs.events",
]


# ==================== СОБЫТИЯ ====================

@bot.event
async def on_ready():
    print("=" * 60)
    print(f"✅ {config.BOT_NAME} подключён!")
    print(f"Клан: {config.CLAN_NAME}")
    print(f"Серверов: {len(bot.guilds)}")
    for guild in bot.guilds:
        print(f"  • {guild.name} (ID: {guild.id})")
    print(f"Модулей: {len(bot.cogs)}")
    print(f"Команд: {len(bot.commands)}")
    print("=" * 60)

    log_module.log.info(
        f"Бот запущен. Модулей: {len(bot.cogs)}, команд: {len(bot.commands)}"
    )

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{config.COMMAND_PREFIX}help • {config.CLAN_NAME}",
        )
    )

    bot.loop.create_task(backup_db_loop())
    bot.loop.create_task(cache.auto_cleanup(300))


@bot.event
async def on_command_error(ctx: commands.Context, error):
    """Обработка ошибок команд."""
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("⛔ У тебя нет прав для этой команды.")

    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ Участник не найден.")

    elif isinstance(error, commands.RoleNotFound):
        await ctx.send("❌ Роль не найдена.")

    elif isinstance(error, commands.ChannelNotFound):
        await ctx.send("❌ Канал не найден.")

    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Не хватает аргумента: `{error.param.name}`")

    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Неверный аргумент: `{error}`")

    elif isinstance(error, commands.CommandNotFound):
        pass  # игнорируем

    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ Подожди {error.retry_after:.1f} сек.")

    elif isinstance(error, commands.CheckFailure):
        await ctx.send("⛔ У тебя нет доступа к этой команде.")

    else:
        print(f"❌ Ошибка в команде {ctx.command}: {error}")
        log_module.log_exception(error, context=f"cmd={ctx.command}")
        try:
            await ctx.send(f"⚠️ Произошла ошибка: `{error}`")
        except discord.Forbidden:
            pass


@bot.event
async def on_command(ctx: commands.Context):
    """Логирует использование команд."""
    log_module.log.log_command(ctx)


# ==================== ФОНОВЫЕ ЗАДАЧИ ====================

async def backup_db_loop():
    """Каждые 6 часов создаёт бэкап БД."""
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            os.makedirs("data/backups", exist_ok=True)

            if os.path.exists("data/economy.db"):
                # Обновлено: используем timezone-aware datetime
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                backup_path = f"data/backups/economy_{timestamp}.db"
                shutil.copy2("data/economy.db", backup_path)
                log_module.log.info(f"Бэкап БД создан: {backup_path}")

                backups = sorted(
                    [f for f in os.listdir("data/backups") if f.endswith(".db")],
                    reverse=True
                )
                for old in backups[20:]:
                    try:
                        os.remove(f"data/backups/{old}")
                    except OSError:
                        pass

        except Exception as e:
            log_module.log_exception(e, context="backup_db_loop")

        await asyncio.sleep(6 * 3600)


# ==================== ЗАПУСК ====================

async def main():
    db.init_db()
    print("📁 База данных инициализирована.")
    log_module.log.info("База данных инициализирована.")

    log_module.cleanup_old_logs(days=30)

    async with bot:
        loaded, failed = [], []
        for cog in COGS:
            try:
                await bot.load_extension(cog)
                loaded.append(cog)
                print(f"📦 Загружен: {cog}")
            except Exception as e:
                failed.append(cog)
                print(f"⚠️ Не удалось загрузить {cog}: {e}")
                log_module.log_exception(e, context=f"load {cog}")

        print(f"\n✅ Загружено модулей: {len(loaded)}/{len(COGS)}")
        if failed:
            print(f"❌ Не загружено: {', '.join(failed)}")

        log_module.log.info(f"Загружено модулей: {len(loaded)}/{len(COGS)}")

        try:
            await bot.start(config.TOKEN)
        except KeyboardInterrupt:
            print("\n⏹️ Остановка бота...")
        except Exception as e:
            log_module.log_exception(e, context="bot.start")
            raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен.")