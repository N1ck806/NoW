"""
Модуль статистики Nightmare.
"""

import discord
from discord.ext import commands
from datetime import datetime, timedelta

import config
from utils import database as db
from utils import embeds


class Stats(commands.Cog):
    """Статистика участников и клана."""

    def __init__(self, bot):
        self.bot = bot

    # ==================== ПРОФИЛЬ ====================

    @commands.command(name="stats", aliases=["стата", "профиль", "я"])
    async def stats(self, ctx, member: discord.Member = None):
        """Общая статистика участника."""
        member = member or ctx.author
        if member.bot:
            return await ctx.send(embed=embeds.error("Ошибка", "У ботов нет статистики."))

        data = db.get_user_data(ctx.guild.id, member.id)
        warns = db.count_warnings(ctx.guild.id, member.id)
        games = db.get_game_stats(ctx.guild.id, member.id)

        # Ранг в топе
        top_bal = db.get_top_balances(ctx.guild.id, 100)
        bal_rank = next((i + 1 for i, r in enumerate(top_bal) if r["user_id"] == member.id), "—")

        top_lvl = db.get_top_levels(ctx.guild.id, 100)
        lvl_rank = next((i + 1 for i, r in enumerate(top_lvl) if r["user_id"] == member.id), "—")

        # Winrate
        winrate = (games["wins"] / games["total"] * 100) if games["total"] > 0 else 0

        embed = embeds.info(
            f"📊 Профиль {member.display_name}",
            f"**Уровень:** {data['level']} ({data['xp']:,} XP)\n"
            f"**Сообщений:** {data['messages']:,}\n"
            f"**Баланс:** {config.CURRENCY_EMOJI} {data['balance']:,} (#{bal_rank})\n"
            f"**Предупреждений:** {warns}\n\n"
            f"**🎮 Игры:**\n"
            f"• Всего игр: {games['total']}\n"
            f"• Побед: {games['wins']} ({winrate:.1f}%)\n"
            f"• Профит: {config.CURRENCY_EMOJI} {games['total_profit']:,}"
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"ID: {member.id}")
        await ctx.send(embed=embed)

    # ==================== КРАТКАЯ КАРТОЧКА ====================

    @commands.command(name="card", aliases=["карточка"])
    async def card(self, ctx, member: discord.Member = None):
        """Краткая карточка участника."""
        member = member or ctx.author
        if member.bot:
            return await ctx.send(embed=embeds.error("Ошибка", "У ботов нет карточки."))

        data = db.get_user_data(ctx.guild.id, member.id)

        embed = embeds.info(
            member.display_name,
            f"Ур. **{data['level']}** • {config.CURRENCY_EMOJI} {data['balance']:,} • 💬 {data['messages']:,}"
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.send(embed=embed)

    # ==================== СТАТИСТИКА СЕРВЕРА ====================

    @commands.command(name="serverstats", aliases=["сервер", "серверстата"])
    async def serverstats(self, ctx):
        """Статистика сервера."""
        guild = ctx.guild
        total_members = guild.member_count
        bots = sum(1 for m in guild.members if m.bot)
        humans = total_members - bots

        online = sum(1 for m in guild.members if m.status != discord.Status.offline)

        # Топы
        top_bal = db.get_top_balances(guild.id, 1)
        top_lvl = db.get_top_levels(guild.id, 1)

        top_bal_str = "—"
        if top_bal:
            m = guild.get_member(top_bal[0]["user_id"])
            if m:
                top_bal_str = f"{m.display_name} ({top_bal[0]['balance']:,})"

        top_lvl_str = "—"
        if top_lvl:
            m = guild.get_member(top_lvl[0]["user_id"])
            if m:
                top_lvl_str = f"{m.display_name} (ур. {top_lvl[0]['level']})"

        # Всего монет в обороте
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT SUM(balance) as total FROM users WHERE guild_id = ?", (guild.id,))
        total_coins = cur.fetchone()["total"] or 0
        conn.close()

        # Дата создания
        created = guild.created_at.strftime("%d.%m.%Y")

        embed = embeds.info(
            f"📊 Статистика {guild.name}",
            f"**Участников:** {total_members:,}\n"
            f"• Людей: {humans:,}\n"
            f"• Ботов: {bots:,}\n"
            f"• Онлайн: {online:,}\n\n"
            f"**Экономика:**\n"
            f"• В обороте: {config.CURRENCY_EMOJI} {total_coins:,}\n"
            f"• Богач: {top_bal_str}\n\n"
            f"**Активность:**\n"
            f"• Топ по уровню: {top_lvl_str}\n\n"
            f"**Создан:** {created}"
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        await ctx.send(embed=embed)

    # ==================== ТОП АКТИВНОСТИ ====================

    @commands.command(name="activitytop", aliases=["активтоп", "топ_сообщений"])
    async def activitytop(self, ctx):
        """Топ-10 по количеству сообщений."""
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT user_id, messages, level FROM users "
            "WHERE guild_id = ? ORDER BY messages DESC LIMIT 10",
            (ctx.guild.id,)
        )
        rows = cur.fetchall()
        conn.close()

        if not rows:
            return await ctx.send(embed=embeds.info("Топ активности", "Пока нет данных."))

        lines = []
        medals = ["🥇", "🥈", "🥉"]
        for i, row in enumerate(rows, start=1):
            member = ctx.guild.get_member(row["user_id"])
            name = member.display_name if member else f"ID {row['user_id']}"
            prefix = medals[i - 1] if i <= 3 else f"`{i}.`"
            lines.append(f"{prefix} **{name}** — 💬 {row['messages']:,} (ур. {row['level']})")

        await ctx.send(embed=embeds.info("💬 Топ по активности", "\n".join(lines)))

    # ==================== ТОП ПО ИГРАМ ====================

    @commands.command(name="gametop", aliases=["игровой_топ", "топ_игроков"])
    async def gametop(self, ctx):
        """Топ-10 игроков по профиту."""
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT user_id, SUM(profit) as total_profit, COUNT(*) as games, "
            "SUM(CASE WHEN win = 1 THEN 1 ELSE 0 END) as wins "
            "FROM game_history WHERE guild_id = ? "
            "GROUP BY user_id ORDER BY total_profit DESC LIMIT 10",
            (ctx.guild.id,)
        )
        rows = cur.fetchall()
        conn.close()

        if not rows:
            return await ctx.send(embed=embeds.info("Игровой топ", "Пока нет данных."))

        lines = []
        medals = ["🥇", "🥈", "🥉"]
        for i, row in enumerate(rows, start=1):
            member = ctx.guild.get_member(row["user_id"])
            name = member.display_name if member else f"ID {row['user_id']}"
            prefix = medals[i - 1] if i <= 3 else f"`{i}.`"
            winrate = (row["wins"] / row["games"] * 100) if row["games"] > 0 else 0
            profit = row["total_profit"] or 0
            lines.append(
                f"{prefix} **{name}** — {config.CURRENCY_EMOJI} {profit:+,} "
                f"({row['games']} игр, {winrate:.0f}% побед)"
            )

        await ctx.send(embed=embeds.info("🎮 Топ игроков", "\n".join(lines)))

    # ==================== МОЯ СТАТИСТИКА ИГР ====================

    @commands.command(name="mygames", aliases=["мои_игры", "игростата"])
    async def mygames(self, ctx, member: discord.Member = None):
        """Подробная статистика игр."""
        member = member or ctx.author
        if member.bot:
            return await ctx.send(embed=embeds.error("Ошибка", "У ботов нет статистики."))

        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT game, COUNT(*) as plays, "
            "SUM(CASE WHEN win = 1 THEN 1 ELSE 0 END) as wins, "
            "SUM(profit) as profit "
            "FROM game_history WHERE guild_id = ? AND user_id = ? "
            "GROUP BY game ORDER BY profit DESC",
            (ctx.guild.id, member.id)
        )
        rows = cur.fetchall()
        conn.close()

        if not rows:
            return await ctx.send(embed=embeds.info(
                "Игры",
                f"У {member.mention} пока нет сыгранных игр."
            ))

        lines = []
        for row in rows:
            winrate = (row["wins"] / row["plays"] * 100) if row["plays"] > 0 else 0
            profit = row["profit"] or 0
            emoji = "📈" if profit > 0 else ("📉" if profit < 0 else "➖")
            lines.append(
                f"{emoji} **{row['game']}** — {row['plays']} игр, "
                f"{winrate:.0f}% побед, {config.CURRENCY_EMOJI} {profit:+,}"
            )

        embed = embeds.info(
            f"🎮 Игры {member.display_name}",
            "\n".join(lines)
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.send(embed=embed)

    # ==================== АКТИВНОСТЬ ЗА НЕДЕЛЮ ====================

    @commands.command(name="weekly", aliases=["неделя", "активность"])
    async def weekly(self, ctx):
        """Статистика активности за последние 7 дней."""
        since = (datetime.utcnow() - timedelta(days=7)).isoformat()

        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) as games FROM game_history "
            "WHERE guild_id = ? AND created_at >= ?",
            (ctx.guild.id, since)
        )
        games_week = cur.fetchone()["games"] or 0
        conn.close()

        await ctx.send(embed=embeds.info(
            "📅 Активность за неделю",
            f"**Игр сыграно:** {games_week}\n"
            f"**Активных участников:** —"
        ))


async def setup(bot):
    await bot.add_cog(Stats(bot))