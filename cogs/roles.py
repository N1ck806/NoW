"""
Модуль реакционных ролей Nightmare.
"""

import discord
from discord.ext import commands

import config
from utils import database as db
from utils import embeds
from utils.checks import is_admin


class Roles(commands.Cog):
    """Реакционные роли и автороли."""

    def __init__(self, bot):
        self.bot = bot

    # ==================== СОЗДАНИЕ ПАНЕЛИ ====================

    @commands.command(name="rolepanel", aliases=["панель", "роли_панель"])
    @is_admin()
    async def rolepanel(self, ctx, title: str = "🎭 Выбери свои роли", *, description: str = "Нажми на реакцию, чтобы получить роль.\nСнять реакцию — убрать роль."):
        """Создать панель реакционных ролей. !rolepanel Заголовок | Описание"""
        embed = embeds.info(title, description)
        embed.set_footer(text=f"{config.BOT_NAME} • {config.CLAN_NAME}")
        msg = await ctx.send(embed=embed)
        await ctx.send(embed=embeds.success(
            "Панель создана",
            f"ID сообщения: `{msg.id}`\n\n"
            f"Теперь добавь роли:\n"
            f"`{config.COMMAND_PREFIX}reactionrole {msg.id} 🎮 @Игровая`"
        ))

    # ==================== ДОБАВЛЕНИЕ РОЛИ ====================

    @commands.command(name="reactionrole", aliases=["rr", "роль"])
    @is_admin()
    async def reactionrole(self, ctx, message_id: int, emoji: str, role: discord.Role):
        """Привязать эмодзи к роли. Использование: !rr <message_id> <emoji> <role>"""
        # Проверка иерархии
        if role >= ctx.guild.me.top_role:
            return await ctx.send(embed=embeds.error(
                "Ошибка",
                f"Роль {role.mention} выше или равна роли бота. Бот не сможет её выдать."
            ))

        try:
            msg = await ctx.channel.fetch_message(message_id)
        except discord.NotFound:
            return await ctx.send(embed=embeds.error("Ошибка", "Сообщение не найдено в этом канале."))

        db.add_reaction_role(message_id, emoji, role.id)

        try:
            await msg.add_reaction(emoji)
        except discord.HTTPException:
            return await ctx.send(embed=embeds.error("Ошибка", "Не удалось поставить реакцию. Проверь эмодзи."))

        await ctx.send(embed=embeds.success(
            "Реакционная роль",
            f"Эмодзи {emoji} → {role.mention}\n"
            f"Сообщение: [перейти]({msg.jump_url})"
        ))

    # ==================== УДАЛЕНИЕ РОЛИ ====================

    @commands.command(name="removerr", aliases=["удалить_роль"])
    @is_admin()
    async def removerr(self, ctx, message_id: int, emoji: str):
        """Убрать привязку эмодзи к роли."""
        deleted = db.remove_reaction_role(message_id, emoji)
        if deleted:
            # Пытаемся убрать реакцию с сообщения
            try:
                msg = await ctx.channel.fetch_message(message_id)
                await msg.clear_reaction(emoji)
            except (discord.NotFound, discord.HTTPException):
                pass

            await ctx.send(embed=embeds.success("Удалено", f"Привязка {emoji} удалена."))
        else:
            await ctx.send(embed=embeds.error("Ошибка", "Привязка не найдена."))

    # ==================== СПИСОК РОЛЕЙ ====================

    @commands.command(name="listrr", aliases=["список_ролей"])
    @is_admin()
    async def listrr(self, ctx, message_id: int):
        """Показать все роли для сообщения."""
        rows = db.get_reaction_roles(message_id)
        if not rows:
            return await ctx.send(embed=embeds.info("Реакционные роли", "Для этого сообщения привязок нет."))

        lines = []
        for r in rows:
            role = ctx.guild.get_role(r["role_id"])
            role_name = role.mention if role else f"`удалена ({r['role_id']})`"
            lines.append(f"{r['emoji']} → {role_name}")

        await ctx.send(embed=embeds.info(f"Роли для сообщения {message_id}", "\n".join(lines)))

    # ==================== ОЧИСТКА ВСЕХ ПРИВЯЗОК ====================

    @commands.command(name="clearrr", aliases=["очистить_роли"])
    @is_admin()
    async def clearrr(self, ctx, message_id: int):
        """Удалить все привязки ролей для сообщения."""
        rows = db.get_reaction_roles(message_id)
        if not rows:
            return await ctx.send(embed=embeds.info("Реакционные роли", "Привязок нет."))

        for r in rows:
            db.remove_reaction_role(message_id, r["emoji"])

        try:
            msg = await ctx.channel.fetch_message(message_id)
            await msg.clear_reactions()
        except (discord.NotFound, discord.HTTPException):
            pass

        await ctx.send(embed=embeds.success("Очищено", f"Удалено привязок: **{len(rows)}**"))

    # ==================== ОБРАБОТЧИКИ РЕАКЦИЙ ====================

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.member and payload.member.bot:
            return
        if not payload.guild_id:
            return

        emoji = str(payload.emoji)
        role_id = db.get_reaction_role(payload.message_id, emoji)
        if not role_id:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        role = guild.get_role(role_id)
        member = guild.get_member(payload.user_id)
        if not role or not member:
            return

        # Проверка иерархии
        if role >= guild.me.top_role:
            return

        try:
            await member.add_roles(role, reason="Реакционная роль")
        except discord.Forbidden:
            pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if not payload.guild_id:
            return

        emoji = str(payload.emoji)
        role_id = db.get_reaction_role(payload.message_id, emoji)
        if not role_id:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        role = guild.get_role(role_id)
        member = guild.get_member(payload.user_id)
        if not role or not member:
            return

        if role >= guild.me.top_role:
            return

        try:
            await member.remove_roles(role, reason="Реакционная роль снята")
        except discord.Forbidden:
            pass

    # ==================== АВТОРОЛИ ПО УРОВНЮ ====================

    @commands.command(name="setlevelrole", aliases=["автороль_уровень"])
    @is_admin()
    async def setlevelrole(self, ctx, level: int, role: discord.Role):
        """Выдавать роль при достижении уровня. !setlevelrole 5 @Активный"""
        if level < 1 or level > 500:
            return await ctx.send(embed=embeds.error("Ошибка", "Уровень должен быть от 1 до 500."))
        if role >= ctx.guild.me.top_role:
            return await ctx.send(embed=embeds.error("Ошибка", "Роль выше или равна роли бота."))

        db.add_level_role(ctx.guild.id, level, role.id)
        await ctx.send(embed=embeds.success(
            "Автороль по уровню",
            f"При достижении **{level}** уровня будет выдана роль {role.mention}"
        ))

    @commands.command(name="removelevelrole", aliases=["удалить_автороль"])
    @is_admin()
    async def removelevelrole(self, ctx, level: int):
        """Убрать автороль для уровня."""
        deleted = db.remove_level_role(ctx.guild.id, level)
        if deleted:
            await ctx.send(embed=embeds.success("Удалено", f"Автороль для уровня {level} убрана."))
        else:
            await ctx.send(embed=embeds.error("Ошибка", "Автороль для этого уровня не найдена."))

    @commands.command(name="listlevelroles", aliases=["список_авторолей"])
    @is_admin()
    async def listlevelroles(self, ctx):
        """Список всех авторолей по уровням."""
        rows = db.get_level_roles(ctx.guild.id)
        if not rows:
            return await ctx.send(embed=embeds.info("Автороли", "Автороли по уровням не настроены."))

        lines = []
        for r in sorted(rows, key=lambda x: x["level"]):
            role = ctx.guild.get_role(r["role_id"])
            role_name = role.mention if role else f"`удалена`"
            lines.append(f"**Ур. {r['level']}** → {role_name}")

        await ctx.send(embed=embeds.info("Автороли по уровням", "\n".join(lines)))


async def setup(bot):
    await bot.add_cog(Roles(bot))