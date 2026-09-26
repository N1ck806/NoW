"""
Модуль утилит Nightmare.
"""

import discord
import random
import asyncio
from discord.ext import commands
from datetime import datetime, timedelta

import config
from utils import embeds
from utils import database as db
from utils.checks import is_staff, is_admin


class Utility(commands.Cog):
    """Опросы, напоминания, утилиты."""

    def __init__(self, bot):
        self.bot = bot
        self.reminders = {}  # {user_id: [(time, text), ...]}

    # ==================== ОПРОС ====================

    @commands.command(name="poll", aliases=["опрос"])
    @is_staff()
    async def poll(self, ctx, *, text: str):
        """Создать опрос. !poll Вопрос? | Вар1 | Вар2 | Вар3"""
        parts = [p.strip() for p in text.split("|")]
        if len(parts) < 3:
            return await ctx.send(embed=embeds.error("Ошибка", "Формат: `!poll Вопрос? | Вариант1 | Вариант2`"))
        question = parts[0]
        options = parts[1:]

        if len(options) > 10:
            return await ctx.send(embed=embeds.error("Ошибка", "Максимум 10 вариантов."))

        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        desc = "\n".join(f"{emojis[i]} {opt}" for i, opt in enumerate(options))

        embed = embeds.info(f"📊 {question}", desc)
        embed.set_footer(text=f"Опрос от {ctx.author.display_name}")
        msg = await ctx.send(embed=embed)
        for i in range(len(options)):
            await msg.add_reaction(emojis[i])

        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

    # ==================== БЫСТРЫЙ ОПРОС ====================

    @commands.command(name="quickpoll", aliases=["квик_опрос", "да_нет"])
    @is_staff()
    async def quickpoll(self, ctx, *, question: str):
        """Быстрый опрос Да/Нет."""
        embed = embeds.info(f"📊 {question}", "✅ Да  /  ❌ Нет")
        embed.set_footer(text=f"Опрос от {ctx.author.display_name}")
        msg = await ctx.send(embed=embed)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")

        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

    # ==================== SAY ====================

    @commands.command(name="say", aliases=["сказать", "эхо"])
    @is_staff()
    async def say(self, ctx, *, text: str):
        """Сказать что-то от имени бота."""
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass
        await ctx.send(text)

    @commands.command(name="embed", aliases=["эмбед"])
    @is_staff()
    async def embed(self, ctx, title: str, *, description: str):
        """Отправить embed. !embed Заголовок | Описание"""
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass
        await ctx.send(embed=embeds.info(title, description))

    # ==================== АВАТАР ====================

    @commands.command(name="avatar", aliases=["ава", "аватар"])
    async def avatar(self, ctx, member: discord.Member = None):
        """Показать аватар."""
        member = member or ctx.author
        embed = embeds.info(f"Аватар {member.display_name}", "")
        embed.set_image(url=member.display_avatar.url)
        await ctx.send(embed=embed)

    # ==================== БАННЕР ====================

    @commands.command(name="banner", aliases=["баннер"])
    async def banner(self, ctx, member: discord.Member = None):
        """Показать баннер пользователя."""
        member = member or ctx.author
        user = await self.bot.fetch_user(member.id)

        if not user.banner:
            return await ctx.send(embed=embeds.info("Баннер", f"У {member.mention} нет баннера."))

        embed = embeds.info(f"Баннер {member.display_name}", "")
        embed.set_image(url=user.banner.url)
        await ctx.send(embed=embed)

    # ==================== USERINFO ====================

    @commands.command(name="userinfo", aliases=["ui", "юзер"])
    async def userinfo(self, ctx, member: discord.Member = None):
        """Информация о пользователе."""
        member = member or ctx.author

        roles = [r.mention for r in member.roles if r.name != "@everyone"]
        roles_str = " ".join(roles[:15]) if roles else "—"
        if len(roles) > 15:
            roles_str += f" и ещё {len(roles) - 15}"

        # Статус
        status_map = {
            discord.Status.online: "🟢 Онлайн",
            discord.Status.idle: "🟡 Не активен",
            discord.Status.dnd: "🔴 Не беспокоить",
            discord.Status.offline: "⚫ Оффлайн",
        }
        status = status_map.get(member.status, "⚫ Оффлайн")

        data = db.get_user_data(ctx.guild.id, member.id)

        embed = embeds.info(f"👤 {member.display_name}", "")
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="ID", value=f"`{member.id}`", inline=True)
        embed.add_field(name="Ник", value=str(member), inline=True)
        embed.add_field(name="Бот", value="Да" if member.bot else "Нет", inline=True)
        embed.add_field(name="Статус", value=status, inline=True)
        embed.add_field(name="Создан", value=member.created_at.strftime("%d.%m.%Y"), inline=True)
        embed.add_field(name="Присоединился", value=member.joined_at.strftime("%d.%m.%Y") if member.joined_at else "—", inline=True)

        if not member.bot:
            embed.add_field(
                name="Прогресс",
                value=f"Ур. {data['level']} • {config.CURRENCY_EMOJI} {data['balance']:,} • 💬 {data['messages']:,}",
                inline=False,
            )

        embed.add_field(name=f"Роли ({len(roles)})", value=roles_str, inline=False)
        await ctx.send(embed=embed)

    # ==================== SERVERINFO ====================

    @commands.command(name="serverinfo", aliases=["си", "сервер_инфо"])
    async def serverinfo(self, ctx):
        """Информация о сервере."""
        guild = ctx.guild

        total = guild.member_count
        bots = sum(1 for m in guild.members if m.bot)
        humans = total - bots

        online = sum(1 for m in guild.members if m.status != discord.Status.offline)

        channels_text = len(guild.text_channels)
        channels_voice = len(guild.voice_channels)
        channels_cat = len(guild.categories)

        owner = guild.owner.mention if guild.owner else "—"

        embed = embeds.info(f"🏠 {guild.name}", "")
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        if guild.banner:
            embed.set_image(url=guild.banner.url)

        embed.add_field(name="Владелец", value=owner, inline=True)
        embed.add_field(name="ID", value=f"`{guild.id}`", inline=True)
        embed.add_field(name="Регион", value=str(guild.preferred_locale), inline=True)

        embed.add_field(
            name="Участники",
            value=f"Всего: {total:,}\nЛюдей: {humans:,}\nБотов: {bots:,}\nОнлайн: {online:,}",
            inline=True,
        )
        embed.add_field(
            name="Каналы",
            value=f"Текстовых: {channels_text}\nГолосовых: {channels_voice}\nКатегорий: {channels_cat}",
            inline=True,
        )
        embed.add_field(
            name="Прочее",
            value=f"Ролей: {len(guild.roles)}\nЭмодзи: {len(guild.emojis)}\nБуст: {guild.premium_tier} (x{guild.premium_subscription_count})",
            inline=True,
        )
        embed.add_field(name="Создан", value=guild.created_at.strftime("%d.%m.%Y в %H:%M"), inline=False)
        await ctx.send(embed=embed)

    # ==================== НАПОМИНАНИЕ ====================

    @commands.command(name="remind", aliases=["напомни", "напоминание"])
    async def remind(self, ctx, time: str, *, text: str):
        """Напоминание. !remind 10m Выпить воды"""
        seconds = self._parse_duration(time)
        if seconds is None:
            return await ctx.send(embed=embeds.error(
                "Ошибка",
                "Формат: `10s`, `5m`, `1h`, `2d`\nПример: `!remind 10m Проверить почту`"
            ))

        if seconds > 86400 * 7:
            return await ctx.send(embed=embeds.error("Ошибка", "Максимум 7 дней."))

        await ctx.send(embed=embeds.success(
            "Напоминание установлено",
            f"Напомню через **{self._format_duration(seconds)}**:\n_{text}_"
        ))

        await asyncio.sleep(seconds)

        try:
            await ctx.author.send(embed=embeds.info(
                "⏰ Напоминание",
                f"_{text}_\n\n**Сервер:** {ctx.guild.name}"
            ))
        except discord.Forbidden:
            try:
                await ctx.send(f"{ctx.author.mention} ⏰ Напоминание: **{text}**")
            except discord.Forbidden:
                pass

    # ==================== ПОГОДА (заглушка) ====================

    @commands.command(name="ping", aliases=["пинг"])
    async def ping(self, ctx):
        """Проверка задержки."""
        latency = round(self.bot.latency * 1000)
        await ctx.send(embed=embeds.info(
            "🏓 Понг!",
            f"**Задержка:** {latency} мс"
        ))

    # ==================== ID ====================

    @commands.command(name="id", aliases=["ид"])
    async def id_cmd(self, ctx, member: discord.Member = None):
        """Показать ID пользователя."""
        member = member or ctx.author
        await ctx.send(embed=embeds.info(
            "🆔 ID",
            f"**{member.display_name}:** `{member.id}`"
        ))

    @commands.command(name="channelid", aliases=["cid"])
    async def channelid(self, ctx, channel: discord.TextChannel = None):
        """Показать ID канала."""
        channel = channel or ctx.channel
        await ctx.send(embed=embeds.info(
            "🆔 ID канала",
            f"**{channel.mention}:** `{channel.id}`"
        ))

    @commands.command(name="roleid", aliases=["rid"])
    @is_admin()
    async def roleid(self, ctx, *, role_name: str):
        """Показать ID роли по имени."""
        role = discord.utils.find(lambda r: r.name.lower() == role_name.lower(), ctx.guild.roles)
        if not role:
            return await ctx.send(embed=embeds.error("Ошибка", "Роль не найдена."))
        await ctx.send(embed=embeds.info(
            "🆔 ID роли",
            f"**{role.name}:** `{role.id}`"
        ))

    # ==================== ЭМОДЗИ ====================

    @commands.command(name="emoji", aliases=["эмодзи"])
    @is_staff()
    async def emoji(self, ctx, *, emoji_name: str):
        """Показать эмодзи в увеличенном виде."""
        emoji = discord.utils.find(
            lambda e: e.name.lower() == emoji_name.lower().strip(":"),
            ctx.guild.emojis
        )
        if not emoji:
            return await ctx.send(embed=embeds.error("Ошибка", "Эмодзи не найден."))

        embed = embeds.info(f"Эмодзи {emoji.name}", f"`<{'a' if emoji.animated else ''}:{emoji.name}:{emoji.id}>`")
        embed.set_image(url=emoji.url)
        await ctx.send(embed=embed)

    # ==================== ПОДСЧЁТ ====================

    @commands.command(name="count", aliases=["подсчёт"])
    async def count(self, ctx, *, text: str):
        """Подсчёт символов и слов."""
        words = len(text.split())
        chars = len(text)
        chars_no_space = len(text.replace(" ", ""))
        await ctx.send(embed=embeds.info(
            "📝 Подсчёт",
            f"**Символов:** {chars}\n"
            f"**Без пробелов:** {chars_no_space}\n"
            f"**Слов:** {words}"
        ))

    # ==================== ВЫБОР ====================

    @commands.command(name="choose", aliases=["выбери", "рандом"])
    async def choose(self, ctx, *, options: str):
        """Случайный выбор. !choose пицца | суши | бургер"""
        parts = [p.strip() for p in options.split("|")]
        if len(parts) < 2:
            return await ctx.send(embed=embeds.error("Ошибка", "Формат: `!choose вариант1 | вариант2`"))

        choice = random.choice(parts)
        await ctx.send(embed=embeds.success(
            "🎲 Выбор",
            f"Мой выбор: **{choice}**"
        ))

    # ==================== КУБИК ДЛЯ РЕШЕНИЯ ====================

    @commands.command(name="roll", aliases=["бросок"])
    async def roll(self, ctx, dice: str = "1d6"):
        """Бросок кубика. !roll 2d20"""
        try:
            count, sides = dice.lower().split("d")
            count = int(count)
            sides = int(sides)
            if count < 1 or count > 20 or sides < 2 or sides > 1000:
                raise ValueError
        except ValueError:
            return await ctx.send(embed=embeds.error("Ошибка", "Формат: `1d6`, `2d20`, `3d10`"))

        results = [random.randint(1, sides) for _ in range(count)]
        total = sum(results)

        await ctx.send(embed=embeds.info(
            f"🎲 Бросок {dice}",
            f"**Результаты:** {', '.join(map(str, results))}\n"
            f"**Сумма:** {total}"
        ))

    # ==================== HELPERS ====================

    @staticmethod
    def _parse_duration(duration: str):
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
        if seconds >= 86400:
            return f"{seconds // 86400}д"
        if seconds >= 3600:
            return f"{seconds // 3600}ч"
        if seconds >= 60:
            return f"{seconds // 60}м"
        return f"{seconds}с"


async def setup(bot):
    await bot.add_cog(Utility(bot))