"""
Модуль модерации Nightmare.
"""

import discord
from discord.ext import commands
from datetime import timedelta

import config
from utils import database as db
from utils import embeds
from utils.checks import is_staff, is_admin


class Moderation(commands.Cog):
    """Модерация клана NoW."""

    def __init__(self, bot):
        self.bot = bot

    async def log_action(self, guild, embed):
        if not config.CHANNEL_LOGS:
            return
        channel = guild.get_channel(config.CHANNEL_LOGS)
        if channel:
            try:
                await channel.send(embed=embed)
            except discord.Forbidden:
                pass

    # ==================== WARN ====================

    @commands.command(name="warn", aliases=["пред"])
    @is_staff()
    async def warn(self, ctx, member: discord.Member, *, reason: str = "Без причины"):
        """Выдать предупреждение."""
        if member.bot:
            return await ctx.send(embed=embeds.error("Ошибка", "Боту нельзя выдать предупреждение."))
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send(embed=embeds.error("Ошибка", "Нельзя предупредить участника с равной или высшей ролью."))

        warn_id = db.add_warning(ctx.guild.id, member.id, ctx.author.id, reason)
        count = db.count_warnings(ctx.guild.id, member.id)

        # Автоматические действия при N предупреждений
        auto_action = None
        if count == 3:
            auto_action = "mute"
            try:
                await member.timeout(timedelta(hours=1), reason="Автомут: 3 предупреждения")
            except discord.Forbidden:
                pass
        elif count == 5:
            auto_action = "kick"
            try:
                await member.kick(reason="Автокик: 5 предупреждений")
            except discord.Forbidden:
                pass
        elif count >= 7:
            auto_action = "ban"
            try:
                await member.ban(reason="Автобан: 7+ предупреждений", delete_message_days=1)
            except discord.Forbidden:
                pass

        embed = embeds.warning(
            "Предупреждение выдано",
            f"{member.mention} получил предупреждение.\n"
            f"**Причина:** {reason}\n"
            f"**Всего:** {count}"
        )
        if auto_action:
            auto_text = {"mute": "🔇 Автомут на 1 час (3 предупреждения)",
                         "kick": "👢 Автокик (5 предупреждений)",
                         "ban": "🔨 Автобан (7+ предупреждений)"}[auto_action]
            embed.add_field(name="Автодействие", value=auto_text, inline=False)

        await ctx.send(embed=embed)

        log = embeds.moderation(
            "Warn",
            f"**Участник:** {member.mention} (`{member.id}`)\n"
            f"**Модератор:** {ctx.author.mention}\n"
            f"**Причина:** {reason}\n"
            f"**ID:** {warn_id}\n"
            f"**Всего:** {count}"
            + (f"\n**Автодействие:** {auto_action}" if auto_action else "")
        )
        await self.log_action(ctx.guild, log)

        try:
            await member.send(embed=embeds.warning(
                "Вам выдано предупреждение",
                f"**Сервер:** {ctx.guild.name}\n"
                f"**Причина:** {reason}\n"
                f"**Всего предупреждений:** {count}"
            ))
        except discord.Forbidden:
            pass

    # ==================== WARNINGS ====================

    @commands.command(name="warnings", aliases=["warns", "преды"])
    @is_staff()
    async def warnings(self, ctx, member: discord.Member):
        """Показать предупреждения участника."""
        warns = db.get_warnings(ctx.guild.id, member.id)
        if not warns:
            return await ctx.send(embed=embeds.info("Предупреждения", f"У {member.mention} нет предупреждений."))

        lines = []
        for w in warns[:20]:
            date = w["created_at"][:10] if w["created_at"] else "—"
            lines.append(f"`#{w['id']}` [{date}] — {w['reason']} *(мод: <@{w['moderator_id']}>)*")

        embed = embeds.info(
            f"Предупреждения {member.display_name}",
            "\n".join(lines) + f"\n\n**Всего:** {len(warns)}"
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.send(embed=embed)

    # ==================== CLEARWARNS ====================

    @commands.command(name="clearwarns", aliases=["сброс_предов"])
    @is_admin()
    async def clearwarns(self, ctx, member: discord.Member):
        """Сбросить все предупреждения участника."""
        deleted = db.clear_warnings(ctx.guild.id, member.id)
        await ctx.send(embed=embeds.success("Сброшено", f"У {member.mention} удалено: **{deleted}**"))
        log = embeds.moderation(
            "ClearWarns",
            f"**Участник:** {member.mention}\n**Модератор:** {ctx.author.mention}\n**Удалено:** {deleted}"
        )
        await self.log_action(ctx.guild, log)

    # ==================== MUTE ====================

    @commands.command(name="mute", aliases=["мут"])
    @is_staff()
    async def mute(self, ctx, member: discord.Member, duration: str = "10m", *, reason: str = "Без причины"):
        """Замьютить участника. Пример: !mute @user 10m спам"""
        if member.bot:
            return await ctx.send(embed=embeds.error("Ошибка", "Боту нельзя выдать мут."))
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send(embed=embeds.error("Ошибка", "Нельзя замьютить участника с равной или высшей ролью."))

        seconds = self._parse_duration(duration)
        if seconds is None:
            return await ctx.send(embed=embeds.error("Ошибка", "Неверный формат. Примеры: `10m`, `1h`, `1d`"))

        try:
            await member.timeout(timedelta(seconds=seconds), reason=reason)
        except discord.Forbidden:
            return await ctx.send(embed=embeds.error("Ошибка", "У бота нет прав на мут."))

        await ctx.send(embed=embeds.success(
            "Мут выдан",
            f"{member.mention} замьючен на **{self._format_duration(seconds)}**.\n**Причина:** {reason}"
        ))
        log = embeds.moderation(
            "Mute",
            f"**Участник:** {member.mention}\n**Модератор:** {ctx.author.mention}\n"
            f"**Длительность:** {self._format_duration(seconds)}\n**Причина:** {reason}"
        )
        await self.log_action(ctx.guild, log)

        try:
            await member.send(embed=embeds.warning(
                "Вы замьючены",
                f"**Сервер:** {ctx.guild.name}\n"
                f"**Длительность:** {self._format_duration(seconds)}\n"
                f"**Причина:** {reason}"
            ))
        except discord.Forbidden:
            pass

    # ==================== UNMUTE ====================

    @commands.command(name="unmute", aliases=["размут"])
    @is_staff()
    async def unmute(self, ctx, member: discord.Member):
        """Снять мут."""
        try:
            await member.timeout(None)
        except discord.Forbidden:
            return await ctx.send(embed=embeds.error("Ошибка", "У бота нет прав."))

        await ctx.send(embed=embeds.success("Мут снят", f"{member.mention} размьючен."))
        log = embeds.moderation(
            "Unmute",
            f"**Участник:** {member.mention}\n**Модератор:** {ctx.author.mention}"
        )
        await self.log_action(ctx.guild, log)

        try:
            await member.send(embed=embeds.success("Мут снят", f"С тебя снят мут на сервере **{ctx.guild.name}**."))
        except discord.Forbidden:
            pass

    # ==================== KICK ====================

    @commands.command(name="kick", aliases=["кик"])
    @is_staff()
    async def kick(self, ctx, member: discord.Member, *, reason: str = "Без причины"):
        """Кикнуть участника."""
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send(embed=embeds.error("Ошибка", "Нельзя кикнуть участника с равной или высшей ролью."))

        try:
            await member.send(embed=embeds.error(
                "Вы кикнуты",
                f"**Сервер:** {ctx.guild.name}\n**Причина:** {reason}"
            ))
        except discord.Forbidden:
            pass

        try:
            await member.kick(reason=reason)
        except discord.Forbidden:
            return await ctx.send(embed=embeds.error("Ошибка", "У бота нет прав на кик."))

        await ctx.send(embed=embeds.success("Кик", f"{member} кикнут.\n**Причина:** {reason}"))
        log = embeds.moderation(
            "Kick",
            f"**Участник:** {member} (`{member.id}`)\n"
            f"**Модератор:** {ctx.author.mention}\n**Причина:** {reason}"
        )
        await self.log_action(ctx.guild, log)

    # ==================== BAN ====================

    @commands.command(name="ban", aliases=["бан"])
    @is_admin()
    async def ban(self, ctx, member: discord.Member, *, reason: str = "Без причины"):
        """Забанить участника."""
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send(embed=embeds.error("Ошибка", "Нельзя забанить участника с равной или высшей ролью."))

        try:
            await member.send(embed=embeds.error(
                "Вы забанены",
                f"**Сервер:** {ctx.guild.name}\n**Причина:** {reason}"
            ))
        except discord.Forbidden:
            pass

        try:
            await member.ban(reason=reason, delete_message_days=1)
        except discord.Forbidden:
            return await ctx.send(embed=embeds.error("Ошибка", "У бота нет прав на бан."))

        await ctx.send(embed=embeds.success("Бан", f"{member} забанен.\n**Причина:** {reason}"))
        log = embeds.moderation(
            "Ban",
            f"**Участник:** {member} (`{member.id}`)\n"
            f"**Модератор:** {ctx.author.mention}\n**Причина:** {reason}"
        )
        await self.log_action(ctx.guild, log)

    # ==================== SOFTBAN ====================

    @commands.command(name="softban", aliases=["софтбан"])
    @is_admin()
    async def softban(self, ctx, member: discord.Member, *, reason: str = "Без причины"):
        """Софтбан: бан + мгновенный разбан для очистки сообщений."""
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send(embed=embeds.error("Ошибка", "Нельзя софтбанить участника с равной или высшей ролью."))

        try:
            await member.ban(reason=f"Softban: {reason}", delete_message_days=7)
            await ctx.guild.unban(member, reason="Softban: разбан")
        except discord.Forbidden:
            return await ctx.send(embed=embeds.error("Ошибка", "У бота нет прав."))

        await ctx.send(embed=embeds.success(
            "Софтбан",
            f"{member} софтбанен (сообщения удалены).\n**Причина:** {reason}"
        ))
        log = embeds.moderation(
            "Softban",
            f"**Участник:** {member} (`{member.id}`)\n"
            f"**Модератор:** {ctx.author.mention}\n**Причина:** {reason}"
        )
        await self.log_action(ctx.guild, log)

    # ==================== UNBAN ====================

    @commands.command(name="unban", aliases=["разбан"])
    @is_admin()
    async def unban(self, ctx, user_id: int, *, reason: str = "Без причины"):
        """Разбанить по ID."""
        try:
            user = await self.bot.fetch_user(user_id)
            await ctx.guild.unban(user, reason=reason)
        except discord.NotFound:
            return await ctx.send(embed=embeds.error("Ошибка", "Пользователь не найден в бане."))
        except discord.Forbidden:
            return await ctx.send(embed=embeds.error("Ошибка", "У бота нет прав."))

        await ctx.send(embed=embeds.success("Разбан", f"{user} разбанен.\n**Причина:** {reason}"))
        log = embeds.moderation(
            "Unban",
            f"**Участник:** {user} (`{user.id}`)\n"
            f"**Модератор:** {ctx.author.mention}\n**Причина:** {reason}"
        )
        await self.log_action(ctx.guild, log)

    # ==================== CLEAR ====================

    @commands.command(name="clear", aliases=["purge", "очистить"])
    @is_staff()
    async def clear(self, ctx, amount: int = 10):
        """Удалить N сообщений в текущем канале."""
        if amount < 1 or amount > 100:
            return await ctx.send(embed=embeds.error("Ошибка", "Количество: от 1 до 100."), delete_after=5)
        deleted = await ctx.channel.purge(limit=amount + 1)
        await ctx.send(embed=embeds.success("Очистка", f"Удалено: **{len(deleted) - 1}**"), delete_after=5)

    @commands.command(name="clearuser", aliases=["очистить_юзера"])
    @is_staff()
    async def clearuser(self, ctx, member: discord.Member, amount: int = 50):
        """Удалить N сообщений конкретного пользователя."""
        if amount < 1 or amount > 100:
            return await ctx.send(embed=embeds.error("Ошибка", "Количество: от 1 до 100."), delete_after=5)

        def check(m):
            return m.author.id == member.id

        deleted = await ctx.channel.purge(limit=amount, check=check)
        await ctx.send(embed=embeds.success(
            "Очистка",
            f"Удалено сообщений {member.mention}: **{len(deleted)}**"
        ), delete_after=5)

    # ==================== SLOWMODE ====================

    @commands.command(name="slowmode", aliases=["слоумод"])
    @is_staff()
    async def slowmode(self, ctx, seconds: int = 0):
        """Установить слоумод в канале (0 = выключить)."""
        if seconds < 0 or seconds > 21600:
            return await ctx.send(embed=embeds.error("Ошибка", "Значение: от 0 до 21600 секунд (6 часов)."))

        try:
            await ctx.channel.edit(slowmode_delay=seconds)
        except discord.Forbidden:
            return await ctx.send(embed=embeds.error("Ошибка", "У бота нет прав."))

        if seconds == 0:
            await ctx.send(embed=embeds.success("Слоумод выключен", f"Канал {ctx.channel.mention} свободен."))
        else:
            await ctx.send(embed=embeds.success(
                "Слоумод установлен",
                f"Задержка: **{seconds} сек** в {ctx.channel.mention}"
            ))
        log = embeds.moderation(
            "Slowmode",
            f"**Канал:** {ctx.channel.mention}\n"
            f"**Модератор:** {ctx.author.mention}\n**Задержка:** {seconds} сек"
        )
        await self.log_action(ctx.guild, log)

    # ==================== LOCK / UNLOCK ====================

    @commands.command(name="lock", aliases=["лок", "закрыть"])
    @is_staff()
    async def lock(self, ctx, channel: discord.TextChannel = None):
        """Закрыть канал (запретить писать @everyone)."""
        channel = channel or ctx.channel
        try:
            await channel.set_permissions(
                ctx.guild.default_role,
                send_messages=False,
                reason=f"Lock by {ctx.author}"
            )
        except discord.Forbidden:
            return await ctx.send(embed=embeds.error("Ошибка", "У бота нет прав."))

        await ctx.send(embed=embeds.success("Канал закрыт", f"{channel.mention} заблокирован."))
        log = embeds.moderation(
            "Lock",
            f"**Канал:** {channel.mention}\n**Модератор:** {ctx.author.mention}"
        )
        await self.log_action(ctx.guild, log)

    @commands.command(name="unlock", aliases=["разлок", "открыть"])
    @is_staff()
    async def unlock(self, ctx, channel: discord.TextChannel = None):
        """Открыть канал."""
        channel = channel or ctx.channel
        try:
            await channel.set_permissions(
                ctx.guild.default_role,
                send_messages=None,
                reason=f"Unlock by {ctx.author}"
            )
        except discord.Forbidden:
            return await ctx.send(embed=embeds.error("Ошибка", "У бота нет прав."))

        await ctx.send(embed=embeds.success("Канал открыт", f"{channel.mention} разблокирован."))
        log = embeds.moderation(
            "Unlock",
            f"**Канал:** {channel.mention}\n**Модератор:** {ctx.author.mention}"
        )
        await self.log_action(ctx.guild, log)

    # ==================== HISTORY ====================

    @commands.command(name="history", aliases=["история"])
    @is_staff()
    async def history(self, ctx, member: discord.Member = None):
        """История наказаний участника."""
        member = member or ctx.author

        warns = db.get_warnings(ctx.guild.id, member.id)

        # История из БД (warnings уже есть)
        embed = embeds.info(
            f"История наказаний {member.display_name}",
            f"**Предупреждений:** {len(warns)}"
        )

        if warns:
            lines = []
            for w in warns[:10]:
                date = w["created_at"][:10] if w["created_at"] else "—"
                lines.append(f"`#{w['id']}` [{date}] {w['reason']}")
            embed.add_field(name="Последние предупреждения", value="\n".join(lines), inline=False)

        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.send(embed=embed)

    # ==================== HELPERS ====================

    @staticmethod
    def _parse_duration(duration: str):
        """Парсит '10m', '1h', '1d' в секунды."""
        units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        if not duration or duration[-1].lower() not in units:
            return None
        try:
            value = int(duration[:-1])
            return value * units[duration[-1].lower()]
        except ValueError:
            return None

    @staticmethod
    def _format_duration(seconds: int) -> str:
        """Форматирует секунды в читаемый вид."""
        if seconds >= 86400:
            return f"{seconds // 86400}д"
        if seconds >= 3600:
            return f"{seconds // 3600}ч"
        if seconds >= 60:
            return f"{seconds // 60}м"
        return f"{seconds}с"


async def setup(bot):
    await bot.add_cog(Moderation(bot))