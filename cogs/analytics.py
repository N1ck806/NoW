"""
Модуль аналитики Nightmare.
Статистика, графики, экспорт данных.
"""

import discord
import io
import csv
from discord.ext import commands
from datetime import datetime, timedelta

import config
from utils import database as db
from utils import embeds
from utils import helpers
from utils.checks import is_admin, is_staff


class Analytics(commands.Cog):
    """Аналитика и отчёты."""

    def __init__(self, bot):
        self.bot = bot

    # ==================== ОБЩАЯ АНАЛИТИКА ====================

    @commands.command(name="analytics", aliases=["аналитика", "статсервер"])
    @is_staff()
    async def analytics(self, ctx, days: int = 7):
        """Общая аналитика сервера за N дней."""
        if days < 1 or days > 90:
            return await ctx.send(embed=embeds.error("Ошибка", "Период: от 1 до 90 дней."))

        since = (datetime.utcnow() - timedelta(days=days)).isoformat()
        conn = db.get_connection()
        cur = conn.cursor()

        # Активные пользователи
        cur.execute(
            "SELECT COUNT(DISTINCT user_id) FROM users WHERE guild_id = ? AND last_xp >= ?",
            (ctx.guild.id, since)
        )
        active_users = cur.fetchone()[0] or 0

        # Новые пользователи (появились за период)
        cur.execute(
            "SELECT COUNT(*) FROM users WHERE guild_id = ? AND last_xp >= ?",
            (ctx.guild.id, since)
        )
        new_users = cur.fetchone()[0] or 0

        # Сообщения (всего в системе)
        cur.execute(
            "SELECT SUM(messages) FROM users WHERE guild_id = ?",
            (ctx.guild.id,)
        )
        total_messages = cur.fetchone()[0] or 0

        # Игры за период
        cur.execute(
            "SELECT COUNT(*), SUM(bet), SUM(profit) FROM game_history "
            "WHERE guild_id = ? AND created_at >= ?",
            (ctx.guild.id, since)
        )
        games_row = cur.fetchone()
        games_count = games_row[0] or 0
        games_bet = games_row[1] or 0
        games_profit = games_row[2] or 0

        # Модерация за период
        cur.execute(
            "SELECT COUNT(*) FROM warnings WHERE guild_id = ? AND created_at >= ?",
            (ctx.guild.id, since)
        )
        warns_count = cur.fetchone()[0] or 0

        # Экономика
        cur.execute(
            "SELECT SUM(balance), AVG(balance) FROM users WHERE guild_id = ?",
            (ctx.guild.id,)
        )
        eco_row = cur.fetchone()
        total_coins = eco_row[0] or 0
        avg_coins = int(eco_row[1] or 0)

        conn.close()

        embed = embeds.info(
            f"📊 Аналитика за {days} дней",
            f"**Период:** с {(datetime.utcnow() - timedelta(days=days)).strftime('%d.%m.%Y')}"
        )

        embed.add_field(
            name="👥 Участники",
            value=(
                f"Активных: **{active_users}**\n"
                f"Новых: **{new_users}**\n"
                f"Сообщений всего: **{total_messages:,}**"
            ),
            inline=True,
        )
        embed.add_field(
            name="🎮 Игры",
            value=(
                f"Сыграно: **{games_count:,}**\n"
                f"Ставок: {config.CURRENCY_EMOJI} **{games_bet:,}**\n"
                f"Профит игроков: {config.CURRENCY_EMOJI} **{games_profit:+,}**"
            ),
            inline=True,
        )
        embed.add_field(
            name="💰 Экономика",
            value=(
                f"В обороте: {config.CURRENCY_EMOJI} **{total_coins:,}**\n"
                f"Средний баланс: {config.CURRENCY_EMOJI} **{avg_coins:,}**"
            ),
            inline=True,
        )
        embed.add_field(
            name="🛡️ Модерация",
            value=f"Предупреждений: **{warns_count}**",
            inline=True,
        )

        await ctx.send(embed=embed)

    # ==================== АКТИВНОСТЬ ПО ДНЯМ ====================

    @commands.command(name="activitychart", aliases=["график", "активность_график"])
    @is_staff()
    async def activitychart(self, ctx, days: int = 7):
        """График активности по дням (ASCII)."""
        if days < 1 or days > 30:
            return await ctx.send(embed=embeds.error("Ошибка", "Период: от 1 до 30 дней."))

        conn = db.get_connection()
        cur = conn.cursor()

        # Считаем игры по дням
        result = {}
        for i in range(days):
            day_start = (datetime.utcnow() - timedelta(days=days - i - 1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            day_end = day_start + timedelta(days=1)

            cur.execute(
                "SELECT COUNT(*) FROM game_history "
                "WHERE guild_id = ? AND created_at >= ? AND created_at < ?",
                (ctx.guild.id, day_start.isoformat(), day_end.isoformat())
            )
            count = cur.fetchone()[0] or 0
            result[day_start.strftime("%d.%m")] = count

        conn.close()

        if not result:
            return await ctx.send(embed=embeds.info("График", "Нет данных."))

        max_val = max(result.values()) or 1
        lines = []
        for day, count in result.items():
            bar_len = int(count / max_val * 20) if max_val > 0 else 0
            bar = "█" * bar_len + "░" * (20 - bar_len)
            lines.append(f"`{day}` {bar} **{count}**")

        await ctx.send(embed=embeds.info(
            f"📈 Активность за {days} дней (игры)",
            "\n".join(lines)
        ))

    # ==================== ТОП АКТИВНЫХ ====================

    @commands.command(name="topactive", aliases=["топ_активных", "активтоп10"])
    @is_staff()
    async def topactive(self, ctx, days: int = 7):
        """Топ активных за период."""
        since = (datetime.utcnow() - timedelta(days=days)).isoformat()

        conn = db.get_connection()
        cur = conn.cursor()

        # По XP за период (по last_xp)
        cur.execute(
            "SELECT user_id, level, xp, messages, balance FROM users "
            "WHERE guild_id = ? AND last_xp >= ? "
            "ORDER BY xp DESC LIMIT 10",
            (ctx.guild.id, since)
        )
        rows = cur.fetchall()
        conn.close()

        if not rows:
            return await ctx.send(embed=embeds.info("Топ", f"Нет данных за {days} дней."))

        lines = []
        medals = ["🥇", "🥈", "🥉"]
        for i, row in enumerate(rows, start=1):
            member = ctx.guild.get_member(row["user_id"])
            name = member.display_name if member else f"ID {row['user_id']}"
            prefix = medals[i - 1] if i <= 3 else f"`{i}.`"
            lines.append(
                f"{prefix} **{name}** — ур. {row['level']} • "
                f"💬 {row['messages']:,} • {config.CURRENCY_EMOJI} {row['balance']:,}"
            )

        await ctx.send(embed=embeds.info(f"🔥 Топ активных за {days} дней", "\n".join(lines)))

    # ==================== ЭКСПОРТ ДАННЫХ ====================

    @commands.command(name="export", aliases=["экспорт", "выгрузка"])
    @is_admin()
    async def export(self, ctx, table: str = "users"):
        """Экспорт таблицы в CSV. Таблицы: users, warnings, game_history, transactions."""
        allowed = ["users", "warnings", "game_history", "transactions"]
        if table not in allowed:
            return await ctx.send(embed=embeds.error(
                "Ошибка",
                f"Доступные таблицы: {', '.join(allowed)}"
            ))

        conn = db.get_connection()
        cur = conn.cursor()

        if table == "users":
            cur.execute("SELECT * FROM users WHERE guild_id = ?", (ctx.guild.id,))
        elif table == "warnings":
            cur.execute("SELECT * FROM warnings WHERE guild_id = ?", (ctx.guild.id,))
        elif table == "game_history":
            cur.execute("SELECT * FROM game_history WHERE guild_id = ?", (ctx.guild.id,))
        elif table == "transactions":
            cur.execute("SELECT * FROM transactions WHERE guild_id = ?", (ctx.guild.id,))

        rows = cur.fetchall()
        conn.close()

        if not rows:
            return await ctx.send(embed=embeds.info("Экспорт", f"Таблица `{table}` пуста."))

        # Пишем в CSV в памяти
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(rows[0].keys())
        for row in rows:
            writer.writerow(list(row))

        buffer.seek(0)
        file = discord.File(
            io.BytesIO(buffer.getvalue().encode("utf-8")),
            filename=f"{table}_{ctx.guild.id}_{datetime.utcnow().strftime('%Y%m%d')}.csv"
        )

        await ctx.send(
            embed=embeds.success(
                "Экспорт готов",
                f"Таблица: **{table}**\n"
                f"Записей: **{len(rows)}**"
            ),
            file=file,
        )

    # ==================== ОТЧЁТ ДЛЯ АДМИНА ====================

    @commands.command(name="report", aliases=["отчёт", "отчет"])
    @is_admin()
    async def report(self, ctx, days: int = 7):
        """Полный отчёт для админов."""
        since = (datetime.utcnow() - timedelta(days=days)).isoformat()

        conn = db.get_connection()
        cur = conn.cursor()

        # Модерация
        cur.execute(
            "SELECT moderator_id, COUNT(*) as cnt FROM warnings "
            "WHERE guild_id = ? AND created_at >= ? "
            "GROUP BY moderator_id ORDER BY cnt DESC LIMIT 5",
            (ctx.guild.id, since)
        )
        top_mods = cur.fetchall()

        # Нарушители
        cur.execute(
            "SELECT user_id, COUNT(*) as cnt FROM warnings "
            "WHERE guild_id = ? AND created_at >= ? "
            "GROUP BY user_id ORDER BY cnt DESC LIMIT 5",
            (ctx.guild.id, since)
        )
        top_offenders = cur.fetchall()

        # Игроки
        cur.execute(
            "SELECT user_id, SUM(profit) as profit FROM game_history "
            "WHERE guild_id = ? AND created_at >= ? "
            "GROUP BY user_id ORDER BY profit DESC LIMIT 5",
            (ctx.guild.id, since)
        )
        top_winners = cur.fetchall()

        cur.execute(
            "SELECT user_id, SUM(profit) as profit FROM game_history "
            "WHERE guild_id = ? AND created_at >= ? "
            "GROUP BY user_id ORDER BY profit ASC LIMIT 5",
            (ctx.guild.id, since)
        )
        top_losers = cur.fetchall()

        conn.close()

        embed = embeds.info(
            f"📋 Отчёт за {days} дней",
            f"Админ-сводка по активности."
        )

        # Топ модераторов
        if top_mods:
            lines = []
            for row in top_mods:
                member = ctx.guild.get_member(row["moderator_id"])
                name = member.display_name if member else f"ID {row['moderator_id']}"
                lines.append(f"**{name}** — {row['cnt']}")
            embed.add_field(name="🛡️ Активные модераторы", value="\n".join(lines), inline=True)

        # Топ нарушителей
        if top_offenders:
            lines = []
            for row in top_offenders:
                member = ctx.guild.get_member(row["user_id"])
                name = member.display_name if member else f"ID {row['user_id']}"
                lines.append(f"**{name}** — {row['cnt']}")
            embed.add_field(name="⚠️ Нарушители", value="\n".join(lines), inline=True)

        # Топ выигравших
        if top_winners:
            lines = []
            for row in top_winners:
                member = ctx.guild.get_member(row["user_id"])
                name = member.display_name if member else f"ID {row['user_id']}"
                lines.append(f"**{name}** — {config.CURRENCY_EMOJI} {row['profit']:+,}")
            embed.add_field(name="🏆 Топ выигравших", value="\n".join(lines), inline=True)

        # Топ проигравших
        if top_losers:
            lines = []
            for row in top_losers:
                member = ctx.guild.get_member(row["user_id"])
                name = member.display_name if member else f"ID {row['user_id']}"
                lines.append(f"**{name}** — {config.CURRENCY_EMOJI} {row['profit']:+,}")
            embed.add_field(name="💀 Топ проигравших", value="\n".join(lines), inline=True)

        await ctx.send(embed=embed)

    # ==================== ПРОГНОЗ ====================

    @commands.command(name="forecast", aliases=["прогноз"])
    @is_staff()
    async def forecast(self, ctx, days: int = 30):
        """Прогноз экономики на N дней вперёд."""
        conn = db.get_connection()
        cur = conn.cursor()

        # Средний прирост баланса за последние 7 дней (приблизительно)
        week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()

        cur.execute(
            "SELECT COUNT(*), SUM(profit) FROM game_history "
            "WHERE guild_id = ? AND created_at >= ?",
            (ctx.guild.id, week_ago)
        )
        row = cur.fetchone()
        games_count = row[0] or 0
        games_sum = row[1] or 0

        cur.execute(
            "SELECT SUM(balance) FROM users WHERE guild_id = ?",
            (ctx.guild.id,)
        )
        total_balance = cur.fetchone()[0] or 0

        conn.close()

        # Прогноз: средний прирост в день × days
        avg_daily = games_sum / 7 if games_count > 0 else 0
        forecast = total_balance + int(avg_daily * days)

        embed = embeds.info(
            f"📈 Прогноз экономики на {days} дней",
            f"**Текущий оборот:** {config.CURRENCY_EMOJI} {total_balance:,}\n"
            f"**Средний прирост/день:** {config.CURRENCY_EMOJI} {int(avg_daily):+,}\n"
            f"**Прогноз через {days} дней:** {config.CURRENCY_EMOJI} {forecast:,}\n\n"
            f"_Прогноз приблизительный, основан на активности за 7 дней._"
        )
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Analytics(bot))