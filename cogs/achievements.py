"""
Модуль достижений Nightmare.
"""

import discord
from discord.ext import commands

import config
from utils import database as db
from utils import embeds
from utils import helpers


# ==================== СПИСОК ДОСТИЖЕНИЙ ====================

ACHIEVEMENTS = {
    # Активность
    "first_message": {
        "name": "Первое слово",
        "description": "Написать первое сообщение",
        "emoji": "💬",
        "reward": 100,
    },
    "chatty_100": {
        "name": "Болтун",
        "description": "Написать 100 сообщений",
        "emoji": "🗣️",
        "reward": 500,
    },
    "chatty_1000": {
        "name": "Голос клана",
        "description": "Написать 1000 сообщений",
        "emoji": "📢",
        "reward": 5000,
    },
    "chatty_10000": {
        "name": "Легенда чата",
        "description": "Написать 10000 сообщений",
        "emoji": "🏆",
        "reward": 50000,
    },

    # Уровни
    "level_5": {
        "name": "Начало пути",
        "description": "Достичь 5 уровня",
        "emoji": "⭐",
        "reward": 500,
    },
    "level_10": {
        "name": "Опытный",
        "description": "Достичь 10 уровня",
        "emoji": "🌟",
        "reward": 1500,
    },
    "level_25": {
        "name": "Ветеран",
        "description": "Достичь 25 уровня",
        "emoji": "💫",
        "reward": 5000,
    },
    "level_50": {
        "name": "Мастер",
        "description": "Достичь 50 уровня",
        "emoji": "👑",
        "reward": 20000,
    },

    # Экономика
    "first_coins": {
        "name": "Первая монета",
        "description": "Заработать первую монету",
        "emoji": "🪙",
        "reward": 100,
    },
    "rich_1k": {
        "name": "Тысячник",
        "description": "Накопить 1000 монет",
        "emoji": "💰",
        "reward": 200,
    },
    "rich_10k": {
        "name": "Десятка",
        "description": "Накопить 10000 монет",
        "emoji": "💎",
        "reward": 2000,
    },
    "rich_100k": {
        "name": "Сотка",
        "description": "Накопить 100000 монет",
        "emoji": "💍",
        "reward": 20000,
    },
    "rich_1m": {
        "name": "Миллионер",
        "description": "Накопить 1000000 монет",
        "emoji": "🏦",
        "reward": 200000,
    },

    # Игры
    "first_game": {
        "name": "Первая ставка",
        "description": "Сыграть первую игру",
        "emoji": "🎲",
        "reward": 100,
    },
    "games_100": {
        "name": "Азартный",
        "description": "Сыграть 100 игр",
        "emoji": "🎰",
        "reward": 2000,
    },
    "games_1000": {
        "name": "Игорный барон",
        "description": "Сыграть 1000 игр",
        "emoji": "🎯",
        "reward": 20000,
    },
    "big_win": {
        "name": "Большой куш",
        "description": "Выиграть 10000 за одну игру",
        "emoji": "💥",
        "reward": 1000,
    },
    "lucky_streak": {
        "name": "Полоса везения",
        "description": "Выиграть 5 игр подряд",
        "emoji": "🍀",
        "reward": 3000,
    },

    # Репутация
    "rep_10": {
        "name": "Уважаемый",
        "description": "Получить 10 репутации",
        "emoji": "⭐",
        "reward": 1000,
    },
    "rep_50": {
        "name": "Авторитет",
        "description": "Получить 50 репутации",
        "emoji": "🌟",
        "reward": 5000,
    },
    "rep_100": {
        "name": "Икона клана",
        "description": "Получить 100 репутации",
        "emoji": "👑",
        "reward": 15000,
    },

    # Голос
    "voice_60": {
        "name": "Голос клана",
        "description": "Провести 60 минут в войсе",
        "emoji": "🎙️",
        "reward": 500,
    },
    "voice_600": {
        "name": "Голосовой мастер",
        "description": "Провести 600 минут в войсе",
        "emoji": "🎧",
        "reward": 5000,
    },

    # Социальные
    "daily_7": {
        "name": "Верный клану",
        "description": "Забрать daily 7 дней подряд",
        "emoji": "📅",
        "reward": 2000,
    },
    "daily_30": {
        "name": "Преданный",
        "description": "Забрать daily 30 дней подряд",
        "emoji": "🗓️",
        "reward": 10000,
    },

    # Особые
    "night_owl": {
        "name": "Полуночник",
        "description": "Написать сообщение после 3:00 ночи",
        "emoji": "🦉",
        "reward": 500,
    },
    "early_bird": {
        "name": "Ранняя пташка",
        "description": "Написать сообщение до 6:00 утра",
        "emoji": "🐦",
        "reward": 500,
    },
}


class Achievements(commands.Cog):
    """Достижения участников."""

    def __init__(self, bot):
        self.bot = bot

    # ==================== СПИСОК ====================

    @commands.command(name="achievements", aliases=["ach", "достижения", "ачивки"])
    async def achievements(self, ctx, member: discord.Member = None):
        """Показать достижения участника."""
        member = member or ctx.author
        if member.bot:
            return await ctx.send(embed=embeds.error("Ошибка", "У ботов нет достижений."))

        unlocked = db.get_achievements(ctx.guild.id, member.id)
        unlocked_ids = {a["achievement"] for a in unlocked}

        total = len(ACHIEVEMENTS)
        done = len(unlocked_ids)
        percent = int(done / total * 100) if total else 0

        bar = helpers.progress_bar(done, total, 20)

        embed = embeds.info(
            f"🏅 Достижения {member.display_name}",
            f"**Открыто:** {done}/{total} ({percent}%)\n"
            f"`{bar}`"
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        # Показываем открытые
        if unlocked_ids:
            lines = []
            for ach_id in list(unlocked_ids)[:10]:
                ach = ACHIEVEMENTS.get(ach_id)
                if ach:
                    lines.append(f"{ach['emoji']} **{ach['name']}** — {ach['description']}")
            embed.add_field(name="✅ Открытые", value="\n".join(lines), inline=False)

        await ctx.send(embed=embed)

    # ==================== ВСЕ ДОСТИЖЕНИЯ ====================

    @commands.command(name="allach", aliases=["все_ачивки", "список_ачивок"])
    async def allach(self, ctx):
        """Показать все существующие достижения."""
        embed = embeds.info(
            f"🏅 Все достижения ({len(ACHIEVEMENTS)})",
            "Полный список доступных достижений."
        )

        # Группируем по категориям
        categories = {
            "💬 Активность": ["first_message", "chatty_100", "chatty_1000", "chatty_10000"],
            "📈 Уровни": ["level_5", "level_10", "level_25", "level_50"],
            "💰 Экономика": ["first_coins", "rich_1k", "rich_10k", "rich_100k", "rich_1m"],
            "🎮 Игры": ["first_game", "games_100", "games_1000", "big_win", "lucky_streak"],
            "⭐ Репутация": ["rep_10", "rep_50", "rep_100"],
            "🎙️ Голос": ["voice_60", "voice_600"],
            "📅 Социальные": ["daily_7", "daily_30"],
            "🦉 Особые": ["night_owl", "early_bird"],
        }

        for cat_name, ach_ids in categories.items():
            lines = []
            for ach_id in ach_ids:
                ach = ACHIEVEMENTS.get(ach_id)
                if ach:
                    lines.append(
                        f"{ach['emoji']} **{ach['name']}** — {ach['description']} "
                        f"({config.CURRENCY_EMOJI} {ach['reward']:,})"
                    )
            if lines:
                embed.add_field(name=cat_name, value="\n".join(lines), inline=False)

        await ctx.send(embed=embed)

    # ==================== ВЫДАТЬ ====================

    async def unlock(self, guild_id: int, user_id: int, ach_id: str) -> bool:
        """
        Пытается выдать достижение. Возвращает True, если выдано впервые.
        Автоматически начисляет награду.
        """
        ach = ACHIEVEMENTS.get(ach_id)
        if not ach:
            return False

        if not db.unlock_achievement(guild_id, user_id, ach_id):
            return False  # уже было

        # Награда
        db.add_balance(guild_id, user_id, ach["reward"], config.START_BALANCE)
        return True

    async def notify(self, guild: discord.Guild, user_id: int, ach_id: str):
        """Отправляет уведомление о достижении."""
        ach = ACHIEVEMENTS.get(ach_id)
        if not ach:
            return

        member = guild.get_member(user_id)
        if not member:
            return

        # Уведомление в ЛС
        try:
            await member.send(embed=embeds.success(
                f"{ach['emoji']} Достижение открыто!",
                f"**{ach['name']}**\n"
                f"{ach['description']}\n\n"
                f"Награда: {config.CURRENCY_EMOJI} **{ach['reward']:,}**"
            ))
        except discord.Forbidden:
            pass

    # ==================== ПРОВЕРКА ====================

    async def check_all(self, guild: discord.Guild, user_id: int):
        """Проверяет все достижения для пользователя."""
        data = db.get_user_data(guild.id, user_id)
        if not data:
            return

        # Активность
        if data["messages"] >= 1:
            await self._try_unlock(guild, user_id, "first_message")
        if data["messages"] >= 100:
            await self._try_unlock(guild, user_id, "chatty_100")
        if data["messages"] >= 1000:
            await self._try_unlock(guild, user_id, "chatty_1000")
        if data["messages"] >= 10000:
            await self._try_unlock(guild, user_id, "chatty_10000")

        # Уровни
        if data["level"] >= 5:
            await self._try_unlock(guild, user_id, "level_5")
        if data["level"] >= 10:
            await self._try_unlock(guild, user_id, "level_10")
        if data["level"] >= 25:
            await self._try_unlock(guild, user_id, "level_25")
        if data["level"] >= 50:
            await self._try_unlock(guild, user_id, "level_50")

        # Экономика
        if data["balance"] >= 1:
            await self._try_unlock(guild, user_id, "first_coins")
        if data["balance"] >= 1000:
            await self._try_unlock(guild, user_id, "rich_1k")
        if data["balance"] >= 10000:
            await self._try_unlock(guild, user_id, "rich_10k")
        if data["balance"] >= 100000:
            await self._try_unlock(guild, user_id, "rich_100k")
        if data["balance"] >= 1000000:
            await self._try_unlock(guild, user_id, "rich_1m")

        # Репутация
        rep = data.get("reputation", 0)
        if rep >= 10:
            await self._try_unlock(guild, user_id, "rep_10")
        if rep >= 50:
            await self._try_unlock(guild, user_id, "rep_50")
        if rep >= 100:
            await self._try_unlock(guild, user_id, "rep_100")

        # Голос
        voice = data.get("voice_minutes", 0)
        if voice >= 60:
            await self._try_unlock(guild, user_id, "voice_60")
        if voice >= 600:
            await self._try_unlock(guild, user_id, "voice_600")

        # Игры
        games = db.get_game_stats(guild.id, user_id)
        if games["total"] >= 1:
            await self._try_unlock(guild, user_id, "first_game")
        if games["total"] >= 100:
            await self._try_unlock(guild, user_id, "games_100")
        if games["total"] >= 1000:
            await self._try_unlock(guild, user_id, "games_1000")

    async def _try_unlock(self, guild: discord.Guild, user_id: int, ach_id: str):
        """Пытается выдать и уведомить."""
        unlocked = await self.unlock(guild.id, user_id, ach_id)
        if unlocked:
            await self.notify(guild, user_id, ach_id)

    # ==================== АДМИН: ВЫДАТЬ ВРУЧНУЮ ====================

    @commands.command(name="grantach", aliases=["выдать_ачивку"])
    @commands.has_permissions(administrator=True)
    async def grantach(self, ctx, member: discord.Member, ach_id: str):
        """Выдать достижение вручную."""
        if ach_id not in ACHIEVEMENTS:
            return await ctx.send(embed=embeds.error(
                "Ошибка",
                f"Достижение `{ach_id}` не найдено. Посмотри `{config.COMMAND_PREFIX}allach`."
            ))

        unlocked = await self.unlock(ctx.guild.id, member.id, ach_id)
        if unlocked:
            await ctx.send(embed=embeds.success(
                "Достижение выдано",
                f"{member.mention} получил **{ACHIEVEMENTS[ach_id]['name']}**"
            ))
            await self.notify(ctx.guild, member.id, ach_id)
        else:
            await ctx.send(embed=embeds.warning("Уже есть", f"У {member.mention} уже есть эта ачивка."))

    # ==================== АДМИН: СБРОС ====================

    @commands.command(name="resetach", aliases=["сброс_ачивок"])
    @commands.has_permissions(administrator=True)
    async def resetach(self, ctx, member: discord.Member):
        """Сбросить все достижения участника."""
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM achievements WHERE guild_id = ? AND user_id = ?",
            (ctx.guild.id, member.id)
        )
        deleted = cur.rowcount
        conn.commit()
        conn.close()

        await ctx.send(embed=embeds.success(
            "Сброшено",
            f"У {member.mention} удалено достижений: **{deleted}**"
        ))

    # ==================== СЛУШАТЕЛЬ ====================

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Проверяет достижения при сообщениях."""
        if message.author.bot or not message.guild:
            return
        if message.content.startswith(config.COMMAND_PREFIX):
            return

        # Полуночник / Ранняя пташка
        from datetime import datetime
        hour = datetime.utcnow().hour + 3  # примерный MSK
        if hour >= 24:
            hour -= 24

        if 3 <= hour < 6:
            await self._try_unlock(message.guild, message.author.id, "night_owl")
        elif 5 <= hour < 6:
            await self._try_unlock(message.guild, message.author.id, "early_bird")

        # Раз в N сообщений проверяем всё остальное
        data = db.get_user_data(message.guild.id, message.author.id)
        if data and data["messages"] % 10 == 0:
            await self.check_all(message.guild, message.author.id)


async def setup(bot):
    await bot.add_cog(Achievements(bot))