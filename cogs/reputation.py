"""
Модуль репутации Nightmare.
"""

import discord
from discord.ext import commands

import config
from utils import database as db
from utils import embeds
from utils import helpers


class Reputation(commands.Cog):
    """Система репутации."""

    def __init__(self, bot):
        self.bot = bot

    # ==================== ДАТЬ РЕПУТАЦИЮ ====================

    @commands.command(name="rep", aliases=["реп", "репутация"])
    async def rep(self, ctx, member: discord.Member = None):
        """Повысить репутацию участнику. !rep @user"""
        if member is None:
            data = db.get_user_data(ctx.guild.id, ctx.author.id)
            return await ctx.send(embed=embeds.info(
                "⭐ Твоя репутация",
                f"**Репутация:** {data.get('reputation', 0)}"
            ))

        if member.bot:
            return await ctx.send(embed=embeds.error("Ошибка", "Ботам нельзя дать репутацию."))
        if member.id == ctx.author.id:
            return await ctx.send(embed=embeds.error("Ошибка", "Нельзя дать репутацию самому себе."))

        # Проверка кулдауна
        can, seconds_left = db.can_give_rep(ctx.guild.id, ctx.author.id, cooldown_hours=24)
        if not can:
            time_str = helpers.format_duration(seconds_left)
            return await ctx.send(embed=embeds.warning(
                "Кулдаун",
                f"Следующая репутация через **{time_str}**."
            ))

        # Начисляем
        new_rep = db.add_reputation(ctx.guild.id, member.id, 1)
        db.set_last_rep_time(ctx.guild.id, ctx.author.id)

        await ctx.send(embed=embeds.rep_card(ctx.author, member, new_rep))

        # Уведомление получателю
        try:
            await member.send(embed=embeds.info(
                "⭐ Тебе повысили репутацию!",
                f"**От:** {ctx.author.display_name}\n"
                f"**Твоя репутация:** {new_rep}"
            ))
        except discord.Forbidden:
            pass

    # ==================== ТОП РЕПУТАЦИИ ====================

    @commands.command(name="reptop", aliases=["топ_реп", "рептоп"])
    async def reptop(self, ctx):
        """Топ-10 по репутации."""
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT user_id, reputation FROM users "
            "WHERE guild_id = ? AND reputation > 0 "
            "ORDER BY reputation DESC LIMIT 10",
            (ctx.guild.id,)
        )
        rows = cur.fetchall()
        conn.close()

        if not rows:
            return await ctx.send(embed=embeds.info("Топ репутации", "Пока ни у кого нет репутации."))

        lines = []
        medals = ["🥇", "🥈", "🥉"]
        for i, row in enumerate(rows, start=1):
            member = ctx.guild.get_member(row["user_id"])
            name = member.display_name if member else f"ID {row['user_id']}"
            prefix = medals[i - 1] if i <= 3 else f"`{i}.`"
            lines.append(f"{prefix} **{name}** — ⭐ {row['reputation']}")

        await ctx.send(embed=embeds.info("⭐ Топ репутации", "\n".join(lines)))

    # ==================== МОЯ РЕПУТАЦИЯ ====================

    @commands.command(name="myrep", aliases=["моя_реп"])
    async def myrep(self, ctx, member: discord.Member = None):
        """Показать репутацию участника."""
        member = member or ctx.author
        if member.bot:
            return await ctx.send(embed=embeds.error("Ошибка", "У ботов нет репутации."))

        data = db.get_user_data(ctx.guild.id, member.id)
        rep = data.get("reputation", 0)

        # Позиция в топе
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) + 1 FROM users "
            "WHERE guild_id = ? AND reputation > ?",
            (ctx.guild.id, rep)
        )
        rank_pos = cur.fetchone()[0]
        conn.close()

        # Следующая реп доступна?
        can, seconds_left = db.can_give_rep(ctx.guild.id, ctx.author.id, 24)
        if can:
            cooldown_str = "✅ Доступна"
        else:
            cooldown_str = f"⏳ через {helpers.format_duration(seconds_left)}"

        embed = embeds.info(
            f"⭐ Репутация {member.display_name}",
            f"**Всего:** {rep}\n"
            f"**Позиция в топе:** #{rank_pos}\n"
            f"**Следующая выдача:** {cooldown_str}"
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.send(embed=embed)

    # ==================== АДМИН: СБРОС ====================

    @commands.command(name="resetrep", aliases=["сброс_реп"])
    @commands.has_permissions(administrator=True)
    async def resetrep(self, ctx, member: discord.Member):
        """Сбросить репутацию участника."""
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET reputation = 0 WHERE guild_id = ? AND user_id = ?",
            (ctx.guild.id, member.id)
        )
        conn.commit()
        conn.close()

        await ctx.send(embed=embeds.success("Сброшено", f"Репутация {member.mention} обнулена."))

    # ==================== АДМИН: ВЫДАТЬ ====================

    @commands.command(name="setrep", aliases=["выдать_реп"])
    @commands.has_permissions(administrator=True)
    async def setrep(self, ctx, member: discord.Member, amount: int):
        """Установить точное значение репутации."""
        if amount < 0:
            return await ctx.send(embed=embeds.error("Ошибка", "Репутация не может быть отрицательной."))

        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET reputation = ? WHERE guild_id = ? AND user_id = ?",
            (amount, ctx.guild.id, member.id)
        )
        conn.commit()
        conn.close()

        await ctx.send(embed=embeds.success(
            "Установлено",
            f"Репутация {member.mention} → ⭐ **{amount}**"
        ))


async def setup(bot):
    await bot.add_cog(Reputation(bot))