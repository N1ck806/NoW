"""
Модуль автоивентов Nightmare.
Лотереи, викторины, розыгрыши, автоматические ивенты.
"""

import discord
import random
import asyncio
from discord.ext import commands, tasks
from datetime import datetime, timedelta

import config
from utils import database as db
from utils import embeds
from utils import helpers
from utils.checks import is_admin, is_staff


class Events(commands.Cog):
    """Автоматические ивенты и розыгрыши."""

    def __init__(self, bot):
        self.bot = bot
        self.active_giveaways = {}   # {message_id: {"prize": ..., "end_time": ..., "channel_id": ..., "host_id": ...}}
        self.active_quiz = None       # Текущая викторина
        self.auto_event_loop.start()

    def cog_unload(self):
        self.auto_event_loop.cancel()

    # ==================== РОЗЫГРЫШ ====================

    @commands.command(name="giveaway", aliases=["розыгрыш", "конкурс"])
    @is_staff()
    async def giveaway(self, ctx, duration: str, winners: int, *, prize: str):
        """
        Создать розыгрыш.
        !giveaway 1h 1 Приз
        !giveaway 30m 3 1000 монет
        """
        seconds = helpers.parse_duration(duration)
        if seconds is None:
            return await ctx.send(embed=embeds.error(
                "Ошибка",
                "Формат времени: `10m`, `1h`, `2d`"
            ))

        if winners < 1 or winners > 20:
            return await ctx.send(embed=embeds.error("Ошибка", "Победителей: от 1 до 20."))

        if seconds > 86400 * 7:
            return await ctx.send(embed=embeds.error("Ошибка", "Максимум 7 дней."))

        end_time = datetime.utcnow() + timedelta(seconds=seconds)

        embed = embeds.success(
            "🎉 Розыгрыш!",
            f"**Приз:** {prize}\n"
            f"**Победителей:** {winners}\n"
            f"**Окончание:** <t:{int(end_time.timestamp())}:R>\n\n"
            f"Реагируй на сообщение 🎉, чтобы участвовать!"
        )
        embed.set_footer(text=f"Организатор: {ctx.author.display_name}")

        msg = await ctx.send(embed=embed)
        await msg.add_reaction("🎉")

        # Сохраняем
        self.active_giveaways[msg.id] = {
            "prize": prize,
            "winners": winners,
            "end_time": end_time,
            "channel_id": ctx.channel.id,
            "host_id": ctx.author.id,
            "message_id": msg.id,
        }

        # Запускаем проверку окончания
        self.bot.loop.create_task(self._wait_giveaway(msg.id, seconds))

    async def _wait_giveaway(self, message_id: int, seconds: int):
        """Ждёт окончания розыгрыша и подводит итоги."""
        await asyncio.sleep(seconds)

        giveaway = self.active_giveaways.pop(message_id, None)
        if not giveaway:
            return

        channel = self.bot.get_channel(giveaway["channel_id"])
        if not channel:
            return

        try:
            msg = await channel.fetch_message(message_id)
        except discord.NotFound:
            return

        # Собираем участников
        participants = []
        for reaction in msg.reactions:
            if str(reaction.emoji) == "🎉":
                async for user in reaction.users():
                    if not user.bot:
                        participants.append(user)

        if not participants:
            await channel.send(embed=embeds.warning(
                "🎉 Розыгрыш окончен",
                f"**Приз:** {giveaway['prize']}\n\n"
                f"😢 Никто не участвовал."
            ))
            return

        # Выбираем победителей
        winner_count = min(giveaway["winners"], len(participants))
        winners = random.sample(participants, winner_count)

        winners_str = "\n".join(f"🏆 {w.mention}" for w in winners)

        embed = embeds.success(
            "🎉 Розыгрыш окончен!",
            f"**Приз:** {giveaway['prize']}\n\n"
            f"**Победители:**\n{winners_str}"
        )

        await channel.send(embed=embed)

        # Уведомления победителям
        for w in winners:
            try:
                await w.send(embed=embeds.success(
                    "🎉 Ты выиграл!",
                    f"**Приз:** {giveaway['prize']}\n"
                    f"**Сервер:** {channel.guild.name}"
                ))
            except discord.Forbidden:
                pass

    @commands.command(name="reroll", aliases=["перероллить"])
    @is_staff()
    async def reroll(self, ctx, message_id: int):
        """Перевыбрать победителя розыгрыша."""
        try:
            msg = await ctx.channel.fetch_message(message_id)
        except discord.NotFound:
            return await ctx.send(embed=embeds.error("Ошибка", "Сообщение не найдено."))

        participants = []
        for reaction in msg.reactions:
            if str(reaction.emoji) == "🎉":
                async for user in reaction.users():
                    if not user.bot:
                        participants.append(user)

        if not participants:
            return await ctx.send(embed=embeds.warning("Никто не участвовал", ""))

        winner = random.choice(participants)
        await ctx.send(embed=embeds.success(
            "🎉 Новый победитель",
            f"🏆 {winner.mention}"
        ))

    @commands.command(name="endgiveaway", aliases=["завершить_розыгрыш"])
    @is_staff()
    async def endgiveaway(self, ctx, message_id: int):
        """Завершить розыгрыш досрочно."""
        if message_id not in self.active_giveaways:
            return await ctx.send(embed=embeds.error("Ошибка", "Активный розыгрыш не найден."))

        giveaway = self.active_giveaways.pop(message_id)

        try:
            msg = await ctx.channel.fetch_message(message_id)
        except discord.NotFound:
            return await ctx.send(embed=embeds.error("Ошибка", "Сообщение розыгрыша не найдено."))

        participants = []
        for reaction in msg.reactions:
            if str(reaction.emoji) == "🎉":
                async for user in reaction.users():
                    if not user.bot:
                        participants.append(user)

        if not participants:
            return await ctx.send(embed=embeds.warning("Никто не участвовал", ""))

        winner_count = min(giveaway["winners"], len(participants))
        winners = random.sample(participants, winner_count)
        winners_str = "\n".join(f"🏆 {w.mention}" for w in winners)

        await ctx.send(embed=embeds.success(
            "🎉 Розыгрыш завершён досрочно!",
            f"**Приз:** {giveaway['prize']}\n\n{winners_str}"
        ))

    # ==================== ВИКТОРИНА ====================

    @commands.command(name="quiz", aliases=["викторина", "вопрос"])
    @is_staff()
    async def quiz(self, ctx):
        """Запустить викторину в текущем канале."""
        questions = self._get_questions()
        q = random.choice(questions)

        embed = embeds.info(
            "🧠 Викторина!",
            f"**Вопрос:** {q['question']}\n\n"
            f"Награда: {config.CURRENCY_EMOJI} **{q['reward']:,}**\n"
            f"Отвечай в чат! Первый правильный ответ побеждает."
        )
        await ctx.send(embed=embed)

        def check(m):
            return m.channel == ctx.channel and not m.author.bot

        try:
            while True:
                reply = await self.bot.wait_for("message", check=check, timeout=60.0)

                # Проверяем ответ
                answer = reply.content.strip().lower()
                accepted = [a.lower() for a in q["answers"]]

                if answer in accepted:
                    db.add_balance(ctx.guild.id, reply.author.id, q["reward"], config.START_BALANCE)
                    await ctx.send(embed=embeds.success(
                        "🎉 Правильный ответ!",
                        f"{reply.author.mention} получает {config.CURRENCY_EMOJI} **{q['reward']:,}**!\n\n"
                        f"**Правильный ответ:** {q['answers'][0]}"
                    ))
                    return

        except asyncio.TimeoutError:
            await ctx.send(embed=embeds.warning(
                "⏰ Время вышло",
                f"Правильный ответ: **{q['answers'][0]}**"
            ))

    def _get_questions(self):
        """Список вопросов для викторины."""
        return [
            {"question": "Сколько планет в Солнечной системе?", "answers": ["8", "восемь"], "reward": 500},
            {"question": "Столица Японии?", "answers": ["токио"], "reward": 500},
            {"question": "Сколько цветов у радуги?", "answers": ["7", "семь"], "reward": 500},
            {"question": "Какой газ преобладает в атмосфере Земли?", "answers": ["азот"], "reward": 700},
            {"question": "Кто написал 'Война и мир'?", "answers": ["толстой", "лев толстой"], "reward": 700},
            {"question": "Какой самый большой океан?", "answers": ["тихий", "тихий океан"], "reward": 500},
            {"question": "Сколько букв в русском алфавите?", "answers": ["33"], "reward": 500},
            {"question": "Что означает H2O?", "answers": ["вода"], "reward": 500},
            {"question": "Сколько минут в сутках?", "answers": ["1440"], "reward": 700},
            {"question": "Какой самый крупный материк?", "answers": ["евразия", "евразии"], "reward": 700},
        ]

    # ==================== ЛОТЕРЕЯ ====================

    @commands.command(name="lottery", aliases=["лотерея"])
    @is_staff()
    async def lottery(self, ctx, ticket_price: int = 100):
        """Запустить лотерею. !lottery 100"""
        if ticket_price < 10:
            return await ctx.send(embed=embeds.error("Ошибка", "Минимальная цена билета: 10."))

        embed = embeds.info(
            "🎰 Лотерея!",
            f"**Цена билета:** {config.CURRENCY_EMOJI} **{ticket_price:,}**\n"
            f"**Призовой фонд:** 80% от собранных монет\n\n"
            f"Для участия: `{config.COMMAND_PREFIX}buyticket`\n"
            f"Длительность: **5 минут**"
        )
        await ctx.send(embed=embed)

        # Ждём 5 минут
        await asyncio.sleep(300)

        # Считаем участников
        conn = db.get_connection()
        cur = conn.cursor()

        # Записываем участников в таблицу transactions с типом "lottery_ticket"
        cur.execute(
            "SELECT from_id, COUNT(*) as tickets FROM transactions "
            "WHERE guild_id = ? AND type = 'lottery_ticket' AND created_at >= ? "
            "GROUP BY from_id",
            (ctx.guild.id, (datetime.utcnow() - timedelta(minutes=5, seconds=30)).isoformat())
        )
        rows = cur.fetchall()
        conn.close()

        if not rows:
            return await ctx.send(embed=embeds.warning("Лотерея", "Никто не купил билеты."))

        # Формируем список для случайного выбора
        tickets = []
        total_pool = 0
        for row in rows:
            for _ in range(row["tickets"]):
                tickets.append(row["from_id"])
            total_pool += row["tickets"] * ticket_price

        prize = int(total_pool * 0.8)

        # Выбираем победителя
        winner_id = random.choice(tickets)
        db.add_balance(ctx.guild.id, winner_id, prize, config.START_BALANCE)

        await ctx.send(embed=embeds.success(
            "🎉 Лотерея окончена!",
            f"**Собрано:** {config.CURRENCY_EMOJI} {total_pool:,}\n"
            f"**Приз:** {config.CURRENCY_EMOJI} {prize:,}\n"
            f"**Победитель:** <@{winner_id}>"
        ))

    @commands.command(name="buyticket", aliases=["купить_билет"])
    async def buyticket(self, ctx, count: int = 1):
        """Купить билет в лотерею."""
        if count < 1 or count > 10:
            return await ctx.send(embed=embeds.error("Ошибка", "Билетов: от 1 до 10."))

        price = 100  # фиксированная цена для простоты
        total = price * count

        balance = db.get_balance(ctx.guild.id, ctx.author.id, config.START_BALANCE)
        if balance < total:
            return await ctx.send(embed=embeds.error(
                "Ошибка",
                f"Нужно {total:,}, у тебя только {balance:,}."
            ))

        db.remove_balance(ctx.guild.id, ctx.author.id, total, config.START_BALANCE)

        # Записываем билеты
        for _ in range(count):
            db.add_transaction(
                ctx.guild.id, ctx.author.id, None, price, "lottery_ticket", "Лотерейный билет"
            )

        await ctx.send(embed=embeds.success(
            "Билеты куплены",
            f"Куплено билетов: **{count}**\n"
            f"Списано: {config.CURRENCY_EMOJI} **{total:,}**"
        ))

    # ==================== АВТОИВЕНТЫ ====================

    @tasks.loop(hours=6)
    async def auto_event_loop(self):
        """Каждые 6 часов запускает случайный автоивент в указанном канале."""
        if not config.CHANNEL_EVENTS:
            return

        channel = self.bot.get_channel(config.CHANNEL_EVENTS)
        if not channel:
            return

        event_type = random.choice(["quiz", "bonus", "drop"])

        if event_type == "quiz":
            await self._auto_quiz(channel)
        elif event_type == "bonus":
            await self._auto_bonus(channel)
        elif event_type == "drop":
            await self._auto_drop(channel)

    async def _auto_quiz(self, channel):
        """Автоматическая викторина."""
        questions = self._get_questions()
        q = random.choice(questions)

        embed = embeds.info(
            "🧠 Авто-викторина!",
            f"**Вопрос:** {q['question']}\n\n"
            f"Награда: {config.CURRENCY_EMOJI} **{q['reward']:,}**\n"
            f"Отвечай в чат! 60 секунд."
        )
        await channel.send(embed=embed)

        def check(m):
            return m.channel == channel and not m.author.bot

        try:
            while True:
                reply = await self.bot.wait_for("message", check=check, timeout=60.0)
                answer = reply.content.strip().lower()
                if answer in [a.lower() for a in q["answers"]]:
                    db.add_balance(channel.guild.id, reply.author.id, q["reward"], config.START_BALANCE)
                    await channel.send(embed=embeds.success(
                        "🎉 Правильный ответ!",
                        f"{reply.author.mention} получает {config.CURRENCY_EMOJI} **{q['reward']:,}**!"
                    ))
                    return
        except asyncio.TimeoutError:
            await channel.send(embed=embeds.warning("⏰ Время вышло", f"Ответ: **{q['answers'][0]}**"))

    async def _auto_bonus(self, channel):
        """Автобонус: первый написавший получает награду."""
        reward = random.randint(500, 2000)
        embed = embeds.success(
            "⚡ Быстрый бонус!",
            f"Первый, кто напишет **{config.COMMAND_PREFIX}bonus**, получит "
            f"{config.CURRENCY_EMOJI} **{reward:,}**!"
        )
        await channel.send(embed=embed)

        def check(m):
            return m.channel == channel and m.content.lower() == f"{config.COMMAND_PREFIX}bonus"

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=60.0)
            db.add_balance(channel.guild.id, msg.author.id, reward, config.START_BALANCE)
            await channel.send(embed=embeds.success(
                "🎉 Бонус забран!",
                f"{msg.author.mention} получает {config.CURRENCY_EMOJI} **{reward:,}**!"
            ))
        except asyncio.TimeoutError:
            await channel.send(embed=embeds.warning("⏰ Никто не забрал", ""))

    async def _auto_drop(self, channel):
        """Автодроп: случайная сумма монет первому нажавшему."""
        reward = random.randint(100, 1000)
        embed = embeds.success(
            "💎 Дроп монет!",
            f"Первый, кто нажмёт на реакцию 💎, получит "
            f"{config.CURRENCY_EMOJI} **{reward:,}**!"
        )
        msg = await channel.send(embed=embed)
        await msg.add_reaction("💎")

        def check(reaction, user):
            return (
                reaction.message.id == msg.id
                and str(reaction.emoji) == "💎"
                and not user.bot
            )

        try:
            reaction, user = await self.bot.wait_for("reaction_add", check=check, timeout=60.0)
            db.add_balance(channel.guild.id, user.id, reward, config.START_BALANCE)
            await channel.send(embed=embeds.success(
                "🎉 Дроп забран!",
                f"{user.mention} получает {config.CURRENCY_EMOJI} **{reward:,}**!"
            ))
        except asyncio.TimeoutError:
            await channel.send(embed=embeds.warning("⏰ Никто не забрал", ""))

    @auto_event_loop.before_loop
    async def before_auto(self):
        await self.bot.wait_until_ready()

    # ==================== КОМАНДЫ ДЛЯ ИВЕНТОВ ====================

    @commands.command(name="bonus", aliases=["бонус"])
    async def bonus(self, ctx):
        """Проверить активный бонус."""
        await ctx.send(embed=embeds.info(
            "Бонус",
            "Бонус активируется автоматически в канале ивентов.\n"
            f"Следи за {config.CHANNEL_EVENTS and f'<#{config.CHANNEL_EVENTS}>' or 'каналом ивентов'}!"
        ))

    @commands.command(name="events", aliases=["ивенты", "события"])
    async def events(self, ctx):
        """Список активных ивентов."""
        lines = []

        # Активные розыгрыши
        if self.active_giveaways:
            for msg_id, g in self.active_giveaways.items():
                time_left = int((g["end_time"] - datetime.utcnow()).total_seconds())
                if time_left > 0:
                    lines.append(
                        f"🎉 **{g['prize']}** — "
                        f"окончание через {helpers.format_duration(time_left)}"
                    )

        if not lines:
            lines.append("Сейчас активных ивентов нет.")

        await ctx.send(embed=embeds.info(
            "🎊 Активные ивенты",
            "\n".join(lines)
        ))

    # ==================== АДМИН ====================

    @commands.command(name="seteventschannel", aliases=["канал_ивентов"])
    @is_admin()
    async def seteventschannel(self, ctx, channel: discord.TextChannel):
        """Установить канал для автоивентов."""
        config.CHANNEL_EVENTS = channel.id
        await ctx.send(embed=embeds.success(
            "Канал ивентов установлен",
            f"Автоивенты будут в {channel.mention}\n\n"
            f"⚠️ Не забудь обновить `CHANNEL_EVENTS` в `config.py`."
        ))


async def setup(bot):
    await bot.add_cog(Events(bot))