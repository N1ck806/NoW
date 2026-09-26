"""
Модуль активности Nightmare.
Опыт, уровни, интеграция с квестами и достижениями.
"""

import discord
import random
from discord.ext import commands
from datetime import datetime

import config
from utils import database as db
from utils import embeds


class Activity(commands.Cog):
    """Опыт и уровни."""

    def __init__(self, bot):
        self.bot = bot

    # ==================== НАЧИСЛЕНИЕ XP ====================

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        if message.content.startswith(config.COMMAND_PREFIX):
            return

        guild_id = message.guild.id
        user_id = message.author.id

        # Проверка кулдауна
        last = db.get_last_xp_time(guild_id, user_id)
        if last:
            last_dt = datetime.fromisoformat(last)
            if (datetime.utcnow() - last_dt).total_seconds() < config.XP_COOLDOWN:
                # Даже если XP на кулдауне — прогресс квестов «messages» всё равно капает
                self._update_message_quests(guild_id, user_id)
                return

        # Случайный бонус XP
        xp_amount = config.XP_PER_MESSAGE
        if random.random() < 0.1:
            xp_amount *= 2

        old_level = db.get_user_data(guild_id, user_id)["level"]
        new_xp, new_level, leveled_up = db.add_xp(guild_id, user_id, xp_amount)
        db.set_last_xp_time(guild_id, user_id)

        # Прогресс квестов на сообщения
        self._update_message_quests(guild_id, user_id)

        # Повышение уровня
        if leveled_up:
            reward = config.LEVEL_REWARD_BASE * new_level
            db.add_balance(guild_id, user_id, reward, config.START_BALANCE)

            # Автороли по уровню
            await self._check_level_roles(message.guild, message.author, new_level)

            # Уведомление
            embed = embeds.success(
                "🎉 Новый уровень!",
                f"{message.author.mention} достиг **{new_level}** уровня!\n"
                f"Награда: {config.CURRENCY_EMOJI} **{reward:,}** {config.CURRENCY_NAME}"
            )
            embed.set_thumbnail(url=message.author.display_avatar.url)

            target = message.channel
            if config.CHANNEL_LEVELUPS:
                ch = message.guild.get_channel(config.CHANNEL_LEVELUPS)
                if ch:
                    target = ch

            try:
                await target.send(embed=embed)
            except discord.Forbidden:
                pass

            # Проверка достижений
            await self._check_achievements(message.guild, message.author.id)

        # Проверка прочих достижений (ночные/утренние, раз в N сообщений)
        await self._check_message_achievements(message)

    # ==================== КВЕСТЫ: ПРОГРЕСС ====================

    def _update_message_quests(self, guild_id: int, user_id: int):
        """Обновляет прогресс всех квестов типа messages/level/balance."""
        try:
            from cogs.quests import load_quests
        except ImportError:
            return

        quests = load_quests()
        if not quests:
            return

        data = db.get_user_data(guild_id, user_id)

        for qid, q in quests.items():
            qtype = q.get("type")

            if qtype == "messages":
                db.progress_quest(guild_id, user_id, qid, 1)
            elif qtype == "level":
                # Прогресс = текущий уровень
                if data["level"] > 0:
                    db.set_quest_progress(guild_id, user_id, qid, data["level"])
            elif qtype == "balance":
                if data["balance"] > 0:
                    db.set_quest_progress(guild_id, user_id, qid, data["balance"])

    # ==================== ДОСТИЖЕНИЯ ====================

    async def _check_achievements(self, guild: discord.Guild, user_id: int):
        """Проверяет все достижения через модуль achievements."""
        cog = self.bot.get_cog("Achievements")
        if cog and hasattr(cog, "check_all"):
            await cog.check_all(guild, user_id)

    async def _check_message_achievements(self, message: discord.Message):
        """Проверка ачивок «полуночник» / «ранняя пташка» и др."""
        cog = self.bot.get_cog("Achievements")
        if not cog:
            return

        from datetime import datetime as dt
        hour = (dt.utcnow().hour + 3) % 24  # примерный MSK

        try:
            if 3 <= hour < 6:
                await cog._try_unlock(message.guild, message.author.id, "night_owl")
            elif 5 <= hour < 7:
                await cog._try_unlock(message.guild, message.author.id, "early_bird")
        except Exception:
            pass

        # Раз в 10 сообщений — полная проверка
        data = db.get_user_data(message.guild.id, message.author.id)
        if data and data["messages"] % 10 == 0:
            await self._check_achievements(message.guild, message.author.id)

    # ==================== АВТОРОЛИ ПО УРОВНЮ ====================

    async def _check_level_roles(self, guild: discord.Guild, member: discord.Member, level: int):
        """Выдаёт автороли по уровню."""
        try:
            rows = db.get_level_roles(guild.id)
        except AttributeError:
            return

        for row in rows:
            if row["level"] <= level:
                role = guild.get_role(row["role_id"])
                if role and role < guild.me.top_role and role not in member.roles:
                    try:
                        await member.add_roles(role, reason=f"Автороль за уровень {row['level']}")
                    except discord.Forbidden:
                        pass

    # ==================== RANK ====================

    @commands.command(name="rank", aliases=["level", "ранг", "уровень", "лвл"])
    async def rank(self, ctx, member: discord.Member = None):
        """Показать уровень и опыт."""
        member = member or ctx.author
        if member.bot:
            return await ctx.send(embed=embeds.error("Ошибка", "У ботов нет уровня."))

        data = db.get_user_data(ctx.guild.id, member.id)
        xp, level, messages = data["xp"], data["level"], data["messages"]

        current_level_xp = db.xp_for_level(level)
        next_level_xp = db.xp_for_level(level + 1)
        progress = xp - current_level_xp
        needed = next_level_xp - current_level_xp
        bar_length = 20
        filled = int(bar_length * progress / needed) if needed > 0 else 0
        bar = "█" * filled + "░" * (bar_length - filled)

        # Позиция в топе
        top = db.get_top_levels(ctx.guild.id, 100)
        rank_pos = next((i + 1 for i, r in enumerate(top) if r["user_id"] == member.id), "—")

        embed = embeds.info(
            f"📊 Ранг {member.display_name}",
            f"**Уровень:** {level} *(#{rank_pos} в топе)*\n"
            f"**Опыт:** {xp:,} / {next_level_xp:,}\n"
            f"**Сообщений:** {messages:,}\n\n"
            f"`{bar}` {progress}/{needed}"
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.send(embed=embed)

    # ==================== LEADERBOARD ====================

    @commands.command(name="leaderboard", aliases=["lb", "топ_уровней", "топ_лвл"])
    async def leaderboard(self, ctx):
        """Топ-10 по уровню."""
        rows = db.get_top_levels(ctx.guild.id, 10)
        if not rows:
            return await ctx.send(embed=embeds.info("Топ уровней", "Пока ни у кого нет опыта."))

        lines = []
        medals = ["🥇", "🥈", "🥉"]
        for i, row in enumerate(rows, start=1):
            member = ctx.guild.get_member(row["user_id"])
            name = member.display_name if member else f"ID {row['user_id']}"
            prefix = medals[i - 1] if i <= 3 else f"`{i}.`"
            lines.append(f"{prefix} **{name}** — ур. {row['level']} ({row['xp']:,} XP)")

        embed = embeds.info("📈 Топ по уровням", "\n".join(lines))
        await ctx.send(embed=embed)

    # ==================== MY RANK ====================

    @commands.command(name="myrank", aliases=["мой_ранг", "моя_позиция"])
    async def myrank(self, ctx):
        """Твоя позиция в топах."""
        top_lvl = db.get_top_levels(ctx.guild.id, 100)
        lvl_pos = next((i + 1 for i, r in enumerate(top_lvl) if r["user_id"] == ctx.author.id), "—")

        top_bal = db.get_top_balances(ctx.guild.id, 100)
        bal_pos = next((i + 1 for i, r in enumerate(top_bal) if r["user_id"] == ctx.author.id), "—")

        data = db.get_user_data(ctx.guild.id, ctx.author.id)

        await ctx.send(embed=embeds.info(
            "📊 Твои позиции",
            f"**По уровню:** #{lvl_pos} (ур. {data['level']})\n"
            f"**По балансу:** #{bal_pos} ({config.CURRENCY_EMOJI} {data['balance']:,})"
        ))

    # ==================== ПРЕСТИЖ ====================

    @commands.command(name="prestige", aliases=["престиж"])
    async def prestige(self, ctx):
        """Показать уровень престижа (уровень // 50)."""
        data = db.get_user_data(ctx.guild.id, ctx.author.id)
        prestige = data["level"] // 50
        progress_to_next = data["level"] % 50

        await ctx.send(embed=embeds.info(
            "🌟 Престиж",
            f"**Престиж:** {prestige}\n"
            f"**До следующего:** {progress_to_next}/50 уровней"
        ))


async def setup(bot):
    await bot.add_cog(Activity(bot))