"""
Модуль голосовой активности Nightmare.
Учёт времени в войсе, XP за минуты, приватные комнаты, интеграция с квестами и достижениями.
"""

import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta

import config
from utils import database as db
from utils import embeds
from utils import helpers
from utils.checks import is_admin


class Voice(commands.Cog):
    """Голосовая активность."""

    def __init__(self, bot):
        self.bot = bot
        # {user_id: {guild_id, channel_id, joined_at}}
        self.active_sessions = {}
        # {channel_id: owner_id} — приватные комнаты
        self.private_rooms = {}

        self.voice_reward_loop.start()

    def cog_unload(self):
        self.voice_reward_loop.cancel()

    # ==================== УЧЁТ ВРЕМЕНИ ====================

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot:
            return

        guild_id = member.guild.id
        user_id = member.id

        # Зашёл в войс
        if before.channel is None and after.channel is not None:
            self.active_sessions[user_id] = {
                "guild_id": guild_id,
                "channel_id": after.channel.id,
                "joined_at": datetime.utcnow(),
            }
            db.start_voice_session(guild_id, user_id, after.channel.id)

        # Вышел из войса
        elif before.channel is not None and after.channel is None:
            session = self.active_sessions.pop(user_id, None)
            if session:
                minutes = db.end_voice_session(guild_id, user_id)
                if minutes > 0:
                    await self._reward_voice(member, minutes)

        # Перешёл между каналами
        elif before.channel != after.channel and after.channel is not None:
            session = self.active_sessions.get(user_id)
            if session:
                minutes = db.end_voice_session(guild_id, user_id)
                if minutes > 0:
                    await self._reward_voice(member, minutes)

            self.active_sessions[user_id] = {
                "guild_id": guild_id,
                "channel_id": after.channel.id,
                "joined_at": datetime.utcnow(),
            }
            db.start_voice_session(guild_id, user_id, after.channel.id)

        # Приватные комнаты
        await self._handle_private_rooms(member, before, after)

    # ==================== НАГРАДА ЗА ВОЙС ====================

    async def _reward_voice(self, member: discord.Member, minutes: int):
        """Начисляет XP и монеты за минуты в войсе."""
        guild_id = member.guild.id
        user_id = member.id

        xp_amount = minutes * config.VOICE_XP_PER_MINUTE
        coin_amount = minutes * config.VOICE_COINS_PER_MINUTE

        new_xp, new_level, leveled_up = db.add_xp(guild_id, user_id, xp_amount)
        db.add_balance(guild_id, user_id, coin_amount, config.START_BALANCE)

        if leveled_up:
            reward = config.LEVEL_REWARD_BASE * new_level
            db.add_balance(guild_id, user_id, reward, config.START_BALANCE)

            embed = embeds.level_up(member, new_level, reward + coin_amount)

            target = None
            if config.CHANNEL_LEVELUPS:
                target = member.guild.get_channel(config.CHANNEL_LEVELUPS)

            if target:
                try:
                    await target.send(embed=embed)
                except discord.Forbidden:
                    pass

        # Прогресс квестов типа voice_minutes
        await self._update_voice_quests(guild_id, user_id, minutes)

        # Достижения
        cog = self.bot.get_cog("Achievements")
        if cog:
            try:
                await cog.check_all(member.guild, user_id)
            except Exception:
                pass

    async def _update_voice_quests(self, guild_id: int, user_id: int, minutes: int):
        """Обновляет прогресс квестов на голос."""
        try:
            from cogs.quests import load_quests
        except ImportError:
            return

        quests = load_quests()
        if not quests:
            return

        total_minutes = db.get_voice_minutes(guild_id, user_id)

        for qid, q in quests.items():
            qtype = q.get("type")
            if qtype == "voice_minutes":
                # Устанавливаем точное значение = общее время в войсе
                db.set_quest_progress(guild_id, user_id, qid, total_minutes)

    # ==================== ФОНОВАЯ НАГРАДА ====================

    @tasks.loop(minutes=10)
    async def voice_reward_loop(self):
        """Каждые 10 минут начисляет награды активным участникам."""
        for user_id, session in list(self.active_sessions.items()):
            guild = self.bot.get_guild(session["guild_id"])
            if not guild:
                continue

            member = guild.get_member(user_id)
            if not member or not member.voice or not member.voice.channel:
                self.active_sessions.pop(user_id, None)
                continue

            minutes = 10
            xp_amount = minutes * config.VOICE_XP_PER_MINUTE
            coin_amount = minutes * config.VOICE_COINS_PER_MINUTE

            db.add_xp(guild.id, user_id, xp_amount)
            db.add_balance(guild.id, user_id, coin_amount, config.START_BALANCE)

            # Обновляем БД voice_minutes тоже, чтобы статистика шла
            conn = db.get_connection()
            cur = conn.cursor()
            cur.execute(
                "UPDATE users SET voice_minutes = voice_minutes + ? "
                "WHERE guild_id = ? AND user_id = ?",
                (minutes, guild.id, user_id)
            )
            conn.commit()
            conn.close()

            # Обновляем квесты
            await self._update_voice_quests(guild.id, user_id, minutes)

    @voice_reward_loop.before_loop
    async def before_voice_loop(self):
        await self.bot.wait_until_ready()

    # ==================== ПРИВАТНЫЕ КОМНАТЫ ====================

    async def _handle_private_rooms(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if not config.VOICE_CREATE_CHANNEL:
            return

        # Создание
        if after.channel and after.channel.id == config.VOICE_CREATE_CHANNEL:
            guild = member.guild
            category = after.channel.category

            try:
                new_channel = await guild.create_voice_channel(
                    name=f"🔊 {member.display_name}",
                    category=category,
                    reason=f"Приватная комната для {member}",
                )
                self.private_rooms[new_channel.id] = member.id

                await new_channel.set_permissions(
                    member,
                    connect=True,
                    manage_channels=True,
                    move_members=True,
                )

                await member.move_to(new_channel)

                try:
                    await member.send(embed=embeds.info(
                        "🎙️ Приватная комната создана",
                        f"**Канал:** {new_channel.mention}\n"
                        f"Ты владелец — можешь управлять доступом."
                    ))
                except discord.Forbidden:
                    pass

            except discord.Forbidden:
                pass

        # Удаление пустой
        if before.channel and before.channel.id in self.private_rooms:
            channel = before.channel
            if len(channel.members) == 0:
                try:
                    await channel.delete(reason="Приватная комната пуста")
                    self.private_rooms.pop(channel.id, None)
                except discord.NotFound:
                    self.private_rooms.pop(channel.id, None)
                except discord.Forbidden:
                    pass

    # ==================== КОМАНДЫ ====================

    @commands.command(name="voicetime", aliases=["войстайм", "время_в_войсе"])
    async def voicetime(self, ctx, member: discord.Member = None):
        """Показать время в голосовых каналах."""
        member = member or ctx.author
        if member.bot:
            return await ctx.send(embed=embeds.error("Ошибка", "У ботов нет статистики войса."))

        minutes = db.get_voice_minutes(ctx.guild.id, member.id)
        hours = minutes // 60
        mins = minutes % 60

        await ctx.send(embed=embeds.info(
            f"🎙️ Время в войсе {member.display_name}",
            f"**Всего:** {hours}ч {mins}м\n"
            f"**В минутах:** {minutes:,}"
        ))

    @commands.command(name="voicetop", aliases=["войстоп", "топ_войса"])
    async def voicetop(self, ctx):
        """Топ-10 по времени в войсе."""
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT user_id, voice_minutes FROM users "
            "WHERE guild_id = ? AND voice_minutes > 0 "
            "ORDER BY voice_minutes DESC LIMIT 10",
            (ctx.guild.id,)
        )
        rows = cur.fetchall()
        conn.close()

        if not rows:
            return await ctx.send(embed=embeds.info("Топ войса", "Пока нет данных."))

        lines = []
        medals = ["🥇", "🥈", "🥉"]
        for i, row in enumerate(rows, start=1):
            member = ctx.guild.get_member(row["user_id"])
            name = member.display_name if member else f"ID {row['user_id']}"
            prefix = medals[i - 1] if i <= 3 else f"`{i}.`"
            m = row["voice_minutes"]
            lines.append(f"{prefix} **{name}** — {m // 60}ч {m % 60}м")

        await ctx.send(embed=embeds.info("🎙️ Топ по войсу", "\n".join(lines)))

    @commands.command(name="voiceonline", aliases=["кто_в_войсе", "войсонлайн"])
    async def voiceonline(self, ctx):
        """Кто сейчас в голосовых каналах."""
        lines = []
        for channel in ctx.guild.voice_channels:
            if channel.members:
                members = ", ".join(m.display_name for m in channel.members)
                lines.append(f"**🔊 {channel.name}** ({len(channel.members)}): {members}")

        if not lines:
            return await ctx.send(embed=embeds.info("Голосовые каналы", "Сейчас никто не в войсе."))

        await ctx.send(embed=embeds.info("🎙️ Кто в войсе", "\n\n".join(lines)))

    # ==================== АДМИН ====================

    @commands.command(name="resetvoice", aliases=["сброс_войса"])
    @is_admin()
    async def resetvoice(self, ctx, member: discord.Member):
        """Сбросить время в войсе участника."""
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET voice_minutes = 0 WHERE guild_id = ? AND user_id = ?",
            (ctx.guild.id, member.id)
        )
        conn.commit()
        conn.close()

        await ctx.send(embed=embeds.success("Сброшено", f"Время в войсе {member.mention} обнулено."))

    @commands.command(name="addvoicetime", aliases=["начислить_войс"])
    @is_admin()
    async def addvoicetime(self, ctx, member: discord.Member, minutes: int):
        """Начислить минуты войса вручную."""
        if minutes <= 0:
            return await ctx.send(embed=embeds.error("Ошибка", "Минуты должны быть больше нуля."))

        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET voice_minutes = voice_minutes + ? WHERE guild_id = ? AND user_id = ?",
            (minutes, ctx.guild.id, member.id)
        )
        conn.commit()
        conn.close()

        await ctx.send(embed=embeds.success(
            "Начислено",
            f"{member.mention} +**{minutes}** мин в войсе."
        ))


async def setup(bot):
    await bot.add_cog(Voice(bot))