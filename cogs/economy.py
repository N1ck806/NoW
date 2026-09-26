"""
Модуль экономики Nightmare.
Интеграция с квестами, достижениями, daily streak.
"""

import discord
from discord.ext import commands
from datetime import datetime

import config
from utils import database as db
from utils import embeds
from utils.checks import is_admin, is_staff


class Economy(commands.Cog):
    """Экономика клана."""

    def __init__(self, bot):
        self.bot = bot

    # ==================== БАЛАНС ====================

    @commands.command(name="balance", aliases=["bal", "баланс", "б"])
    async def balance(self, ctx, member: discord.Member = None):
        """Показать баланс."""
        member = member or ctx.author
        if member.bot:
            return await ctx.send(embed=embeds.error("Ошибка", "У ботов нет баланса."))

        bal = db.get_balance(ctx.guild.id, member.id, config.START_BALANCE)
        data = db.get_user_data(ctx.guild.id, member.id)

        # Позиция в топе
        top = db.get_top_balances(ctx.guild.id, 100)
        rank_pos = next((i + 1 for i, r in enumerate(top) if r["user_id"] == member.id), "—")

        embed = embeds.economy(
            f"Баланс {member.display_name}",
            f"{config.CURRENCY_EMOJI} **{bal:,}** {config.CURRENCY_NAME}\n\n"
            f"**Уровень:** {data['level']}\n"
            f"**Позиция в топе:** #{rank_pos}"
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.send(embed=embed)

    # ==================== DAILY ====================

    @commands.command(name="daily", aliases=["дейли", "д"])
    async def daily(self, ctx):
        """Забрать ежедневную награду с системой стриков."""
        can, seconds_left = db.can_claim_daily(ctx.guild.id, ctx.author.id, 24)
        if not can:
            hours = seconds_left // 3600
            minutes = (seconds_left % 3600) // 60
            seconds = seconds_left % 60
            return await ctx.send(embed=embeds.warning(
                "Уже забрано",
                f"Следующая награда через **{hours}ч {minutes}м {seconds}с**."
            ))

        # Стрик
        last_streak = db.get_daily_streak(ctx.guild.id, ctx.author.id)
        # Проверяем, не пропустил ли день (упрощённо — если daily был больше 48ч назад, сбрасываем)
        # В продакшене лучше через last_daily смотреть
        streak = db.increment_daily_streak(ctx.guild.id, ctx.author.id)

        # Бонусы
        data = db.get_user_data(ctx.guild.id, ctx.author.id)
        level_bonus = data["level"] * 10
        streak_bonus = min(streak, 30) * 20  # макс +600

        total = config.DAILY_REWARD + level_bonus + streak_bonus

        new_balance = db.claim_daily(ctx.guild.id, ctx.author.id, total)

        embed = embeds.success(
            "Ежедневная награда",
            f"Ты получил {config.CURRENCY_EMOJI} **{total:,}** {config.CURRENCY_NAME}!\n\n"
            f"**Базовая:** {config.DAILY_REWARD:,}\n"
            f"**Бонус за уровень ({data['level']}):** +{level_bonus:,}\n"
            f"**Бонус за стрик ({streak}🔥):** +{streak_bonus:,}\n"
            f"**Баланс:** {new_balance:,}"
        )
        await ctx.send(embed=embed)

        # Квесты (daily_streak)
        await self._update_daily_quests(ctx, streak)

        # Достижения
        await self._check_achievements(ctx, ctx.author)

    async def _update_daily_quests(self, ctx, streak: int):
        """Обновляет прогресс квестов daily_streak."""
        try:
            from cogs.quests import load_quests
            quests = load_quests()
            for qid, q in quests.items():
                if q.get("type") == "daily_streak":
                    db.set_quest_progress(ctx.guild.id, ctx.author.id, qid, streak)
        except Exception:
            pass

    async def _check_achievements(self, ctx, member):
        """Проверяет достижения."""
        cog = self.bot.get_cog("Achievements")
        if cog and hasattr(cog, "check_all"):
            try:
                await cog.check_all(ctx.guild, member.id)

                # Daily streak достижения
                streak = db.get_daily_streak(ctx.guild.id, member.id)
                if streak >= 7:
                    await cog._try_unlock(ctx.guild, member.id, "daily_7")
                if streak >= 30:
                    await cog._try_unlock(ctx.guild, member.id, "daily_30")
            except Exception:
                pass

    # ==================== PAY ====================

    @commands.command(name="pay", aliases=["перевод", "перевести", "п"])
    async def pay(self, ctx, member: discord.Member, amount: str):
        """Перевести монеты другому участнику."""
        if member.bot:
            return await ctx.send(embed=embeds.error("Ошибка", "Ботам нельзя переводить."))
        if member.id == ctx.author.id:
            return await ctx.send(embed=embeds.error("Ошибка", "Нельзя переводить самому себе."))

        sender_bal = db.get_balance(ctx.guild.id, ctx.author.id, config.START_BALANCE)
        if amount.lower() in ("all", "все", "всё"):
            amount = sender_bal
        elif amount.lower() in ("half", "половина"):
            amount = sender_bal // 2
        else:
            try:
                amount = int(amount)
            except ValueError:
                return await ctx.send(embed=embeds.error("Ошибка", "Укажи сумму числом, `all` или `half`."))

        if amount <= 0:
            return await ctx.send(embed=embeds.error("Ошибка", "Сумма должна быть больше нуля."))
        if sender_bal < amount:
            return await ctx.send(embed=embeds.error(
                "Недостаточно средств",
                f"У тебя только {config.CURRENCY_EMOJI} **{sender_bal:,}**."
            ))

        commission = int(amount * 0.02)
        final_amount = amount - commission

        db.remove_balance(ctx.guild.id, ctx.author.id, amount, config.START_BALANCE)
        db.add_balance(ctx.guild.id, member.id, final_amount, config.START_BALANCE)
        db.add_transaction(ctx.guild.id, ctx.author.id, member.id, amount, "transfer", None)

        new_bal = db.get_balance(ctx.guild.id, ctx.author.id, config.START_BALANCE)

        await ctx.send(embed=embeds.success(
            "Перевод выполнен",
            f"{ctx.author.mention} → {member.mention}\n\n"
            f"**Отправлено:** {config.CURRENCY_EMOJI} {amount:,}\n"
            f"**Комиссия (2%):** {commission:,}\n"
            f"**Получено:** {config.CURRENCY_EMOJI} {final_amount:,}\n"
            f"**Твой баланс:** {new_bal:,}"
        ))

        try:
            await member.send(embed=embeds.economy(
                "Перевод получен",
                f"От **{ctx.author.display_name}** пришло {config.CURRENCY_EMOJI} **{final_amount:,}**!"
            ))
        except discord.Forbidden:
            pass

    # ==================== TOP ====================

    @commands.command(name="top", aliases=["топ", "богачи", "рейтинг"])
    async def top(self, ctx):
        """Топ-10 богачей клана."""
        rows = db.get_top_balances(ctx.guild.id, 10)
        if not rows:
            return await ctx.send(embed=embeds.info("Топ", "Пока ни у кого нет монет."))

        lines = []
        medals = ["🥇", "🥈", "🥉"]
        for i, row in enumerate(rows, start=1):
            member = ctx.guild.get_member(row["user_id"])
            name = member.display_name if member else f"ID {row['user_id']}"
            prefix = medals[i - 1] if i <= 3 else f"`{i}.`"
            lines.append(f"{prefix} **{name}** — {config.CURRENCY_EMOJI} {row['balance']:,}")

        embed = embeds.info("💰 Топ богачей клана", "\n".join(lines))
        embed.set_footer(text=f"{config.BOT_NAME} • {config.CLAN_NAME}")
        await ctx.send(embed=embed)

    @commands.command(name="rich", aliases=["богатый"])
    async def rich(self, ctx):
        """Показать самого богатого участника."""
        rows = db.get_top_balances(ctx.guild.id, 1)
        if not rows:
            return await ctx.send(embed=embeds.info("Богач", "Пока ни у кого нет монет."))

        member = ctx.guild.get_member(rows[0]["user_id"])
        name = member.mention if member else f"ID {rows[0]['user_id']}"
        await ctx.send(embed=embeds.economy(
            "💎 Самый богатый",
            f"{name} — {config.CURRENCY_EMOJI} **{rows[0]['balance']:,}**"
        ))

    # ==================== ТРАНЗАКЦИИ ====================

    @commands.command(name="transactions", aliases=["транзакции", "история_переводов"])
    async def transactions(self, ctx, member: discord.Member = None):
        """История транзакций участника."""
        member = member or ctx.author
        rows = db.get_transactions(ctx.guild.id, member.id, 15)

        if not rows:
            return await ctx.send(embed=embeds.info(
                "Транзакции",
                f"У {member.mention} нет истории транзакций."
            ))

        lines = []
        for r in rows:
            if r["type"] == "transfer":
                if r["from_id"] == member.id:
                    lines.append(f"📤 → <@{r['to_id']}> — {config.CURRENCY_EMOJI} {r['amount']:,}")
                else:
                    lines.append(f"📥 ← <@{r['from_id']}> — {config.CURRENCY_EMOJI} {r['amount']:,}")
            elif r["type"] == "shop":
                lines.append(f"🛒 {r['reason'] or 'Покупка'} — {config.CURRENCY_EMOJI} {r['amount']:,}")
            elif r["type"] == "lottery_ticket":
                lines.append(f"🎰 Лотерейный билет — {config.CURRENCY_EMOJI} {r['amount']:,}")
            else:
                lines.append(f"💸 {r['type']} — {config.CURRENCY_EMOJI} {r['amount']:,}")

        embed = embeds.info(
            f"💸 Транзакции {member.display_name}",
            "\n".join(lines)
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.send(embed=embed)

    # ==================== ADMINS ====================

    @commands.command(name="addcoins", aliases=["выдать", "начислить"])
    @is_admin()
    async def addcoins(self, ctx, member: discord.Member, amount: int):
        """Начислить монеты участнику."""
        if amount <= 0:
            return await ctx.send(embed=embeds.error("Ошибка", "Сумма должна быть больше нуля."))

        new_bal = db.add_balance(ctx.guild.id, member.id, amount, config.START_BALANCE)
        db.add_transaction(ctx.guild.id, None, member.id, amount, "admin_add", "Админ-начисление")

        await ctx.send(embed=embeds.success(
            "Начислено",
            f"{member.mention} получил {config.CURRENCY_EMOJI} **{amount:,}**.\n"
            f"Баланс: **{new_bal:,}**"
        ))

        try:
            await member.send(embed=embeds.economy(
                "Начисление",
                f"Тебе начислено {config.CURRENCY_EMOJI} **{amount:,}**!"
            ))
        except discord.Forbidden:
            pass

        await self._check_achievements(ctx, member)

    @commands.command(name="removecoins", aliases=["списать", "снять"])
    @is_admin()
    async def removecoins(self, ctx, member: discord.Member, amount: int):
        """Списать монеты у участника."""
        if amount <= 0:
            return await ctx.send(embed=embeds.error("Ошибка", "Сумма должна быть больше нуля."))

        new_bal = db.remove_balance(ctx.guild.id, member.id, amount, config.START_BALANCE)
        db.add_transaction(ctx.guild.id, member.id, None, amount, "admin_remove", "Админ-списание")

        await ctx.send(embed=embeds.success(
            "Списано",
            f"У {member.mention} снято {config.CURRENCY_EMOJI} **{amount:,}**.\n"
            f"Баланс: **{new_bal:,}**"
        ))

    @commands.command(name="setcoins", aliases=["установить"])
    @is_admin()
    async def setcoins(self, ctx, member: discord.Member, amount: int):
        """Установить точный баланс участника."""
        if amount < 0:
            return await ctx.send(embed=embeds.error("Ошибка", "Баланс не может быть отрицательным."))

        db.set_balance(ctx.guild.id, member.id, amount, config.START_BALANCE)
        await ctx.send(embed=embeds.success(
            "Баланс установлен",
            f"{member.mention} → {config.CURRENCY_EMOJI} **{amount:,}**"
        ))

    @commands.command(name="reseteco", aliases=["сброс_экономики"])
    @is_admin()
    async def reseteco(self, ctx, confirm: str = None):
        """Сбросить экономику сервера (необратимо)."""
        if confirm != "confirm":
            return await ctx.send(embed=embeds.warning(
                "Подтверждение",
                f"Это сбросит ВСЕ балансы на сервере.\n"
                f"Напиши `{config.COMMAND_PREFIX}reseteco confirm` для подтверждения."
            ))

        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE users SET balance = 0 WHERE guild_id = ?", (ctx.guild.id,))
        conn.commit()
        conn.close()

        await ctx.send(embed=embeds.success("Сброс", "Все балансы сброшены до 0."))

    # ==================== СТАТИСТИКА ====================

    @commands.command(name="economystats", aliases=["экостата"])
    @is_staff()
    async def economystats(self, ctx):
        """Общая статистика экономики сервера."""
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) as users, SUM(balance) as total, MAX(balance) as max_bal, "
            "AVG(balance) as avg_bal FROM users WHERE guild_id = ?",
            (ctx.guild.id,)
        )
        row = cur.fetchone()
        conn.close()

        total = row["total"] or 0
        users = row["users"] or 0
        avg = int(row["avg_bal"] or 0)

        embed = embeds.info(
            "📊 Статистика экономики",
            f"**Всего монет в обороте:** {config.CURRENCY_EMOJI} {total:,}\n"
            f"**Участников с балансом:** {users:,}\n"
            f"**Средний баланс:** {config.CURRENCY_EMOJI} {avg:,}\n"
            f"**Максимальный баланс:** {config.CURRENCY_EMOJI} {row['max_bal'] or 0:,}"
        )
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Economy(bot))