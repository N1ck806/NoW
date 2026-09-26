"""
Модуль приветствия Nightmare.
"""

import discord
from discord.ext import commands
from datetime import datetime

import config
from utils import database as db
from utils import embeds


class Welcome(commands.Cog):
    """Приветствие новичков и прощание."""

    def __init__(self, bot):
        self.bot = bot

    # ==================== ВХОД ====================

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild

        # Автовыдача роли новобранца
        if config.ROLE_RECRUIT:
            role = guild.get_role(config.ROLE_RECRUIT)
            if role:
                try:
                    await member.add_roles(role, reason="Автороль при входе")
                except discord.Forbidden:
                    pass

        # Приветствие в канале
        channel = None
        if config.CHANNEL_WELCOME:
            channel = guild.get_channel(config.CHANNEL_WELCOME)
        if not channel:
            channel = guild.system_channel

        if channel:
            # Считаем, сколько участников
            member_count = guild.member_count
            position = self._get_join_position(guild, member)

            embed = embeds.info(
                f"👋 Добро пожаловать в {config.CLAN_NAME}!",
                f"{member.mention}, рады видеть тебя в клане!\n\n"
                f"**Ты {position}-й участник**\n\n"
                f"📜 Прочитай правила\n"
                f"💬 Представься в чате\n"
                f"🎭 Выбери роли\n"
                f"🎮 Присоединяйся к играм\n\n"
                f"Если что-то непонятно — спроси у админов!"
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"Всего участников: {member_count}")
            try:
                await channel.send(f"{member.mention}", embed=embed)
            except discord.Forbidden:
                pass

        # ЛС новичку
        try:
            await member.send(embed=embeds.info(
                f"Добро пожаловать в {config.CLAN_NAME}!",
                f"Привет, **{member.display_name}**!\n\n"
                f"Ты попал на сервер **{guild.name}**.\n\n"
                f"Что делать дальше:\n"
                f"• Прочитай правила сервера\n"
                f"• Представься в общем чате\n"
                f"• Выбери роли (если есть панель)\n"
                f"• Общайся и зарабатывай {config.CURRENCY_EMOJI} {config.CURRENCY_NAME}\n\n"
                f"Приятного общения!"
            ))
        except discord.Forbidden:
            pass

    # ==================== ВЫХОД ====================

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        guild = member.guild

        # Логируем выход в канал логов
        if config.CHANNEL_LOGS:
            channel = guild.get_channel(config.CHANNEL_LOGS)
            if channel:
                # Сколько был на сервере
                if member.joined_at:
                    delta = datetime.utcnow() - member.joined_at.replace(tzinfo=None)
                    days = delta.days
                    time_str = f"{days} дн." if days > 0 else "меньше дня"
                else:
                    time_str = "—"

                embed = embeds.warning(
                    "👋 Участник покинул сервер",
                    f"**{member}** (`{member.id}`)\n"
                    f"**Был на сервере:** {time_str}"
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                try:
                    await channel.send(embed=embed)
                except discord.Forbidden:
                    pass

    # ==================== БУСТ ====================

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        # Буст сервера
        if before.premium_since is None and after.premium_since is not None:
            guild = after.guild

            # Награда за буст
            reward = 5000
            db.add_balance(guild.id, after.id, reward, config.START_BALANCE)

            channel = None
            if config.CHANNEL_WELCOME:
                channel = guild.get_channel(config.CHANNEL_WELCOME)
            if not channel:
                channel = guild.system_channel

            if channel:
                embed = embeds.success(
                    "💎 Новый бустер!",
                    f"{after.mention} забустил сервер!\n\n"
                    f"**Награда:** {config.CURRENCY_EMOJI} {reward:,} {config.CURRENCY_NAME}\n"
                    f"**Спасибо за поддержку!**"
                )
                embed.set_thumbnail(url=after.display_avatar.url)
                try:
                    await channel.send(embed=embed)
                except discord.Forbidden:
                    pass

    # ==================== ХЕЛПЕРЫ ====================

    @staticmethod
    def _get_join_position(guild: discord.Guild, member: discord.Member) -> int:
        """Определяет, каким по счёту участник зашёл (по дате joined_at)."""
        try:
            members_sorted = sorted(
                [m for m in guild.members if m.joined_at],
                key=lambda m: m.joined_at
            )
            return members_sorted.index(member) + 1
        except (ValueError, AttributeError):
            return guild.member_count


async def setup(bot):
    await bot.add_cog(Welcome(bot))