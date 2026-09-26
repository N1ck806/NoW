"""
Модуль мини-игр Nightmare.
Классные, атмосферные, с анимациями и связкой с квестами/достижениями.
"""

import discord
import random
import asyncio
from discord.ext import commands

import config
from utils import database as db
from utils import embeds


class Games(commands.Cog):
    """Мини-игры для заработка."""

    def __init__(self, bot):
        self.bot = bot

    # ==================== УТИЛИТЫ ====================

    def _check_bet(self, bet: int):
        if bet < config.GAME_MIN_BET:
            return f"Минимальная ставка: {config.GAME_MIN_BET} {config.CURRENCY_EMOJI}"
        if bet > config.GAME_MAX_BET:
            return f"Максимальная ставка: {config.GAME_MAX_BET} {config.CURRENCY_EMOJI}"
        return None

    def _get_balance(self, ctx):
        return db.get_balance(ctx.guild.id, ctx.author.id, config.START_BALANCE)

    async def _post_game(self, ctx, win: bool, profit: int, game_name: str):
        """Пост-обработка: квесты + достижения + лог игры."""
        from cogs.quests import load_quests
        try:
            quests = load_quests()
            for qid, q in quests.items():
                qtype = q.get("type")
                if qtype == "games":
                    db.progress_quest(ctx.guild.id, ctx.author.id, qid, 1)
                elif qtype == "wins" and win:
                    db.progress_quest(ctx.guild.id, ctx.author.id, qid, 1)
        except Exception:
            pass

        # Достижения
        cog = self.bot.get_cog("Achievements")
        if cog:
            try:
                await cog.check_all(ctx.guild, ctx.author.id)

                # Big win
                if win and profit >= 10000:
                    await cog._try_unlock(ctx.guild, ctx.author.id, "big_win")
            except Exception:
                pass

    # ==================== COINFLIP ====================

    @commands.command(name="coinflip", aliases=["cf", "монетка", "монета"])
    async def coinflip(self, ctx, bet: int, choice: str = None):
        """Орёл/решка. !cf 100 орел"""
        err = self._check_bet(bet)
        if err:
            return await ctx.send(embed=embeds.error("Ошибка", err))

        bal = self._get_balance(ctx)
        if bal < bet:
            return await ctx.send(embed=embeds.error("Ошибка", f"У тебя только {config.CURRENCY_EMOJI} {bal:,}."))

        if not choice or choice.lower() not in ("орел", "решка", "heads", "tails", "o", "r", "орёл"):
            return await ctx.send(embed=embeds.error("Ошибка", "Укажи: `орел` или `решка`."))

        choice_l = choice.lower()
        choice_norm = "орел" if choice_l in ("орел", "орёл", "heads", "o") else "решка"

        # Анимация
        msg = await ctx.send(embed=embeds.info("🪙 Монетка", "Подбрасываем...\n\n🪙"))
        await asyncio.sleep(0.6)
        await msg.edit(embed=embeds.info("🪙 Монетка", "Крутится...\n\n💫 🪙 💫"))
        await asyncio.sleep(0.6)
        await msg.edit(embed=embeds.info("🪙 Монетка", "Почти...\n\n✨ 🪙 ✨"))
        await asyncio.sleep(0.6)

        result = random.choice(["орел", "решка"])
        win = choice_norm == result

        if win:
            profit = bet
            new_bal = db.add_balance(ctx.guild.id, ctx.author.id, profit, config.START_BALANCE)
        else:
            profit = -bet
            new_bal = db.remove_balance(ctx.guild.id, ctx.author.id, bet, config.START_BALANCE)

        db.add_game_result(ctx.guild.id, ctx.author.id, "coinflip", bet, win, profit)

        coin = "🦅" if result == "орел" else "👑"
        embed = (embeds.success if win else embeds.error)(
            f"🪙 {coin} {result.upper()}",
            f"{'✅ Победа!' if win else '❌ Проигрыш'}"
        )
        embed.add_field(name="Профит", value=f"{'+' if profit > 0 else ''}{profit:,}", inline=True)
        embed.add_field(name="Баланс", value=f"{config.CURRENCY_EMOJI} {new_bal:,}", inline=True)
        await msg.edit(embed=embed)

        await self._post_game(ctx, win, profit, "coinflip")

    # ==================== DICE ====================

    @commands.command(name="dice", aliases=["кубик", "куб"])
    async def dice(self, ctx, bet: int, prediction: int = None):
        """Кубик. !dice 100 5 — точное число (x6) | !dice 100 — 4+ (x2)"""
        err = self._check_bet(bet)
        if err:
            return await ctx.send(embed=embeds.error("Ошибка", err))

        bal = self._get_balance(ctx)
        if bal < bet:
            return await ctx.send(embed=embeds.error("Ошибка", f"У тебя только {config.CURRENCY_EMOJI} {bal:,}."))

        if prediction is not None and not (1 <= prediction <= 6):
            return await ctx.send(embed=embeds.error("Ошибка", "Число должно быть от 1 до 6."))

        msg = await ctx.send(embed=embeds.info("🎲 Кубик", "Бросаем...\n\n🎲"))
        await asyncio.sleep(0.6)
        await msg.edit(embed=embeds.info("🎲 Кубик", "Крутится...\n\n💫 🎲 💫"))
        await asyncio.sleep(0.6)

        roll = random.randint(1, 6)

        if prediction is not None:
            win = roll == prediction
            multiplier = 6
        else:
            win = roll >= 4
            multiplier = 2

        if win:
            profit = bet * (multiplier - 1)
            new_bal = db.add_balance(ctx.guild.id, ctx.author.id, profit, config.START_BALANCE)
        else:
            profit = -bet
            new_bal = db.remove_balance(ctx.guild.id, ctx.author.id, bet, config.START_BALANCE)

        db.add_game_result(ctx.guild.id, ctx.author.id, "dice", bet, win, profit)

        dice_faces = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
        desc = f"Выпало: {dice_faces[roll - 1]} **{roll}**\n"
        if prediction is not None:
            desc += f"Твоя ставка: **{prediction}** (x{multiplier})\n"
        else:
            desc += f"Ставка: **4+** (x{multiplier})\n"
        desc += f"\n{'✅ Победа!' if win else '❌ Проигрыш'}"

        embed = (embeds.success if win else embeds.error)("🎲 Кубик", desc)
        embed.add_field(name="Профит", value=f"{'+' if profit > 0 else ''}{profit:,}", inline=True)
        embed.add_field(name="Баланс", value=f"{config.CURRENCY_EMOJI} {new_bal:,}", inline=True)
        await msg.edit(embed=embed)

        await self._post_game(ctx, win, profit, "dice")

    # ==================== SLOTS ====================

    @commands.command(name="slots", aliases=["слоты", "слот", "казино"])
    async def slots(self, ctx, bet: int):
        """Слоты. Три одинаковых — x5, два — x1.5"""
        err = self._check_bet(bet)
        if err:
            return await ctx.send(embed=embeds.error("Ошибка", err))

        bal = self._get_balance(ctx)
        if bal < bet:
            return await ctx.send(embed=embeds.error("Ошибка", f"У тебя только {config.CURRENCY_EMOJI} {bal:,}."))

        msg = await ctx.send(embed=embeds.info("🎰 Слоты", "╔═══════════╗\n║ 🎰 🎰 🎰 ║\n╚═══════════╝\n\nКрутим..."))
        await asyncio.sleep(0.6)

        symbols = ["🍒", "🍋", "🍇", "💎", "7️⃣", "⭐", "🔔"]

        # Анимация прокрутки
        for _ in range(3):
            temp = [random.choice(symbols) for _ in range(3)]
            await msg.edit(embed=embeds.info(
                "🎰 Слоты",
                f"╔═══════════╗\n║ {' '.join(temp)} ║\n╚═══════════╝\n\nКрутим..."
            ))
            await asyncio.sleep(0.4)

        result = [random.choice(symbols) for _ in range(3)]

        unique = len(set(result))
        if unique == 1:
            multiplier = 5
            win = True
            desc = "🎉 ДЖЕКПОТ! ТРИ ОДИНАКОВЫХ!"
        elif unique == 2:
            multiplier = 1.5
            win = True
            desc = "✨ Два одинаковых!"
        else:
            multiplier = 0
            win = False
            desc = "❌ Мимо..."

        if win:
            profit = int(bet * (multiplier - 1))
            new_bal = db.add_balance(ctx.guild.id, ctx.author.id, profit, config.START_BALANCE)
        else:
            profit = -bet
            new_bal = db.remove_balance(ctx.guild.id, ctx.author.id, bet, config.START_BALANCE)

        db.add_game_result(ctx.guild.id, ctx.author.id, "slots", bet, win, profit)

        embed = (embeds.success if win else embeds.error)(
            "🎰 Слоты",
            f"╔═══════════╗\n"
            f"║ {' '.join(result)} ║\n"
            f"╚═══════════╝\n\n"
            f"{desc}"
        )
        embed.add_field(name="Множитель", value=f"x{multiplier}", inline=True)
        embed.add_field(name="Профит", value=f"{'+' if profit > 0 else ''}{profit:,}", inline=True)
        embed.add_field(name="Баланс", value=f"{config.CURRENCY_EMOJI} {new_bal:,}", inline=True)
        await msg.edit(embed=embed)

        await self._post_game(ctx, win, profit, "slots")

    # ==================== ROULETTE ====================

    @commands.command(name="roulette", aliases=["рулетка"])
    async def roulette(self, ctx, bet: int, choice: str):
        """Рулетка. !roulette 100 red / black / green / число"""
        err = self._check_bet(bet)
        if err:
            return await ctx.send(embed=embeds.error("Ошибка", err))

        bal = self._get_balance(ctx)
        if bal < bet:
            return await ctx.send(embed=embeds.error("Ошибка", f"У тебя только {config.CURRENCY_EMOJI} {bal:,}."))

        choice_l = choice.lower()

        msg = await ctx.send(embed=embeds.info("🎡 Рулетка", "Крутим колесо...\n\n⚫🔴⚫🔴⚫"))
        await asyncio.sleep(0.8)
        await msg.edit(embed=embeds.info("🎡 Рулетка", "Крутим...\n\n🔴⚫🔴⚫🔴"))
        await asyncio.sleep(0.8)

        roll = random.randint(0, 36)

        if roll == 0:
            color = "green"
            color_ru = "зелёное"
        elif roll % 2 == 0:
            color = "black"
            color_ru = "чёрное"
        else:
            color = "red"
            color_ru = "красное"

        win = False
        multiplier = 0

        if choice_l in ("red", "красное", "к"):
            win = color == "red"
            multiplier = 2
        elif choice_l in ("black", "чёрное", "черное", "ч"):
            win = color == "black"
            multiplier = 2
        elif choice_l in ("green", "зелёное", "зеленое", "з"):
            win = color == "green"
            multiplier = 14
        else:
            try:
                num = int(choice_l)
                if 0 <= num <= 36:
                    win = roll == num
                    multiplier = 36
                else:
                    return await ctx.send(embed=embeds.error("Ошибка", "Число должно быть от 0 до 36."))
            except ValueError:
                return await ctx.send(embed=embeds.error("Ошибка", "Ставь на `red`, `black`, `green` или число 0-36."))

        if win:
            profit = bet * (multiplier - 1)
            new_bal = db.add_balance(ctx.guild.id, ctx.author.id, profit, config.START_BALANCE)
        else:
            profit = -bet
            new_bal = db.remove_balance(ctx.guild.id, ctx.author.id, bet, config.START_BALANCE)

        db.add_game_result(ctx.guild.id, ctx.author.id, "roulette", bet, win, profit)

        color_emoji = {"red": "🔴", "black": "⚫", "green": "🟢"}[color]

        embed = (embeds.success if win else embeds.error)(
            "🎡 Рулетка",
            f"{color_emoji} Выпало: **{roll}** ({color_ru})\n\n"
            f"{'✅ Победа!' if win else '❌ Проигрыш'}"
        )
        embed.add_field(name="Множитель", value=f"x{multiplier}", inline=True)
        embed.add_field(name="Профит", value=f"{'+' if profit > 0 else ''}{profit:,}", inline=True)
        embed.add_field(name="Баланс", value=f"{config.CURRENCY_EMOJI} {new_bal:,}", inline=True)
        await msg.edit(embed=embed)

        await self._post_game(ctx, win, profit, "roulette")

    # ==================== BLACKJACK ====================

    @commands.command(name="blackjack", aliases=["bj", "21", "блэкджек"])
    async def blackjack(self, ctx, bet: int):
        """Блэкджек."""
        err = self._check_bet(bet)
        if err:
            return await ctx.send(embed=embeds.error("Ошибка", err))

        bal = self._get_balance(ctx)
        if bal < bet:
            return await ctx.send(embed=embeds.error("Ошибка", f"У тебя только {config.CURRENCY_EMOJI} {bal:,}."))

        def draw():
            return random.randint(1, 11)

        def hand_value(hand):
            total = sum(hand)
            aces = hand.count(11)
            while total > 21 and aces:
                total -= 10
                aces -= 1
            return total

        player = [draw(), draw()]
        dealer = [draw(), draw()]

        player_total = hand_value(player)

        if player_total == 21:
            profit = int(bet * 1.5)
            new_bal = db.add_balance(ctx.guild.id, ctx.author.id, profit, config.START_BALANCE)
            db.add_game_result(ctx.guild.id, ctx.author.id, "blackjack", bet, True, profit)
            embed = embeds.success(
                "🃏 БЛЭКДЖЕК!",
                f"**Твои карты:** {player} = {player_total}\n"
                f"**Карты дилера:** {dealer[0]} + 🎴\n\n"
                f"🎉 Мгновенная победа! Профит: +{profit:,}"
            )
            embed.add_field(name="Баланс", value=f"{config.CURRENCY_EMOJI} {new_bal:,}", inline=False)
            await ctx.send(embed=embed)
            return await self._post_game(ctx, True, profit, "blackjack")

        await ctx.send(embed=embeds.info(
            "🃏 Блэкджек",
            f"**Твои карты:** {player} = **{player_total}**\n"
            f"**Карты дилера:** {dealer[0]} + 🎴\n\n"
            f"`взять` или `хватит`. 30 секунд."
        ))

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ("взять", "хватит", "ещё", "еще", "стоп")

        while player_total < 21:
            try:
                reply = await self.bot.wait_for("message", check=check, timeout=30.0)
            except asyncio.TimeoutError:
                await ctx.send(embed=embeds.warning("Время вышло", "Игра отменена."))
                return

            if reply.content.lower() in ("взять", "ещё", "еще"):
                player.append(draw())
                player_total = hand_value(player)
                if player_total > 21:
                    new_bal = db.remove_balance(ctx.guild.id, ctx.author.id, bet, config.START_BALANCE)
                    db.add_game_result(ctx.guild.id, ctx.author.id, "blackjack", bet, False, -bet)
                    embed = embeds.error(
                        "🃏 Перебор!",
                        f"**Твои карты:** {player} = **{player_total}**\n\n"
                        f"❌ Ты проиграл {bet:,}"
                    )
                    embed.add_field(name="Баланс", value=f"{config.CURRENCY_EMOJI} {new_bal:,}", inline=False)
                    await ctx.send(embed=embed)
                    await self._post_game(ctx, False, -bet, "blackjack")
                    return
                else:
                    await ctx.send(embed=embeds.info(
                        "🃏 Блэкджек",
                        f"**Твои карты:** {player} = **{player_total}**\n"
                        f"**Карты дилера:** {dealer[0]} + 🎴\n\n"
                        f"`взять` или `хватит`"
                    ))
            else:
                break

        while hand_value(dealer) < 17:
            dealer.append(draw())

        dealer_total = hand_value(dealer)
        player_total = hand_value(player)

        if dealer_total > 21 or player_total > dealer_total:
            profit = bet
            new_bal = db.add_balance(ctx.guild.id, ctx.author.id, profit, config.START_BALANCE)
            db.add_game_result(ctx.guild.id, ctx.author.id, "blackjack", bet, True, profit)
            result = f"✅ Ты победил! +{profit:,}"
            emb_fn = embeds.success
            win = True
        elif player_total == dealer_total:
            profit = 0
            new_bal = self._get_balance(ctx)
            db.add_game_result(ctx.guild.id, ctx.author.id, "blackjack", bet, False, 0)
            result = "🤝 Ничья. Ставка возвращена."
            emb_fn = embeds.info
            win = False
        else:
            profit = -bet
            new_bal = db.remove_balance(ctx.guild.id, ctx.author.id, bet, config.START_BALANCE)
            db.add_game_result(ctx.guild.id, ctx.author.id, "blackjack", bet, False, profit)
            result = f"❌ Ты проиграл {bet:,}"
            emb_fn = embeds.error
            win = False

        embed = emb_fn(
            "🃏 Блэкджек",
            f"**Твои карты:** {player} = **{player_total}**\n"
            f"**Карты дилера:** {dealer} = **{dealer_total}**\n\n"
            f"{result}"
        )
        embed.add_field(name="Баланс", value=f"{config.CURRENCY_EMOJI} {new_bal:,}", inline=False)
        await ctx.send(embed=embed)

        await self._post_game(ctx, win, profit, "blackjack")

    # ==================== ДУЭЛЬ ====================

    @commands.command(name="duel", aliases=["дуэль", "пвп"])
    async def duel(self, ctx, member: discord.Member, bet: int):
        """Дуэль 1 на 1. !duel @user 100"""
        if member.bot:
            return await ctx.send(embed=embeds.error("Ошибка", "С ботами не дуэлимся."))
        if member.id == ctx.author.id:
            return await ctx.send(embed=embeds.error("Ошибка", "Нельзя дуэлиться с собой."))

        err = self._check_bet(bet)
        if err:
            return await ctx.send(embed=embeds.error("Ошибка", err))

        bal_1 = self._get_balance(ctx)
        if bal_1 < bet:
            return await ctx.send(embed=embeds.error("Ошибка", f"У тебя только {config.CURRENCY_EMOJI} {bal_1:,}."))

        bal_2 = db.get_balance(ctx.guild.id, member.id, config.START_BALANCE)
        if bal_2 < bet:
            return await ctx.send(embed=embeds.error("Ошибка", f"У {member.display_name} только {config.CURRENCY_EMOJI} {bal_2:,}."))

        await ctx.send(embed=embeds.warning(
            "⚔️ Дуэль!",
            f"{ctx.author.mention} вызывает {member.mention} на дуэль!\n"
            f"**Ставка:** {config.CURRENCY_EMOJI} {bet:,}\n\n"
            f"{member.mention}, напиши `принять`. 60 секунд."
        ))

        def check(m):
            return m.author == member and m.channel == ctx.channel and m.content.lower() in ("принять", "accept", "да", "+")

        try:
            await self.bot.wait_for("message", check=check, timeout=60.0)
        except asyncio.TimeoutError:
            return await ctx.send(embed=embeds.warning("Дуэль отменена", f"{member.mention} не ответил."))

        msg = await ctx.send(embed=embeds.info("⚔️ Дуэль началась!", "Бросаем кубики...\n\n🎲 🎲"))
        await asyncio.sleep(1.0)
        await msg.edit(embed=embeds.info("⚔️ Дуэль", "Бросок...\n\n💫 🎲 💫"))
        await asyncio.sleep(1.0)

        dice = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
        roll_1 = random.randint(1, 6)
        roll_2 = random.randint(1, 6)

        while roll_1 == roll_2:
            roll_1 = random.randint(1, 6)
            roll_2 = random.randint(1, 6)

        winner = ctx.author if roll_1 > roll_2 else member
        loser = member if roll_1 > roll_2 else ctx.author

        db.remove_balance(ctx.guild.id, loser.id, bet, config.START_BALANCE)
        db.add_balance(ctx.guild.id, winner.id, bet, config.START_BALANCE)

        embed = embeds.success(
            "⚔️ Дуэль окончена!",
            f"{ctx.author.mention}: {dice[roll_1 - 1]} **{roll_1}**\n"
            f"{member.mention}: {dice[roll_2 - 1]} **{roll_2}**\n\n"
            f"🏆 Победитель: {winner.mention}\n"
            f"Забрал {config.CURRENCY_EMOJI} **{bet:,}**"
        )
        await msg.edit(embed=embed)

        # Квесты для обоих
        try:
            from cogs.quests import load_quests
            quests = load_quests()
            for qid, q in quests.items():
                if q.get("type") == "games":
                    db.progress_quest(ctx.guild.id, ctx.author.id, qid, 1)
                    db.progress_quest(ctx.guild.id, member.id, qid, 1)
                elif q.get("type") == "wins":
                    db.progress_quest(ctx.guild.id, winner.id, qid, 1)
        except Exception:
            pass

    # ==================== КРАШ ====================

    @commands.command(name="crash", aliases=["краш", "ракета"])
    async def crash(self, ctx, bet: int, target: float = 2.0):
        """Краш-игра: ракета взлетает, успей вывести до падения (x1.01 - x10)"""
        err = self._check_bet(bet)
        if err:
            return await ctx.send(embed=embeds.error("Ошибка", err))

        if target < 1.01 or target > 10.0:
            return await ctx.send(embed=embeds.error("Ошибка", "Множитель от 1.01 до 10.0"))

        bal = self._get_balance(ctx)
        if bal < bet:
            return await ctx.send(embed=embeds.error("Ошибка", f"У тебя только {config.CURRENCY_EMOJI} {bal:,}."))

        # Генерируем точку краха
        crash_point = round(random.uniform(1.0, 10.0), 2)

        msg = await ctx.send(embed=embeds.info(
            "🚀 Краш",
            f"Ракета взлетает...\n"
            f"Цель: **x{target}**\n"
            f"Ставка: {config.CURRENCY_EMOJI} **{bet:,}**"
        ))
        await asyncio.sleep(1.0)

        # Анимация
        multiplier = 1.0
        while multiplier < target and multiplier < crash_point:
            multiplier = round(multiplier + 0.1, 2)
            bar_len = int((multiplier - 1) * 5)
            bar = "█" * min(bar_len, 30)
            await msg.edit(embed=embeds.info(
                "🚀 Краш",
                f"x{multiplier:.2f} 📈\n"
                f"`{bar}`"
            ))
            await asyncio.sleep(0.15)

        # Проверяем результат
        if crash_point >= target:
            profit = int(bet * (target - 1))
            new_bal = db.add_balance(ctx.guild.id, ctx.author.id, profit, config.START_BALANCE)
            db.add_game_result(ctx.guild.id, ctx.author.id, "crash", bet, True, profit)
            embed = embeds.success(
                "🚀 Успел вывести!",
                f"Достигнуто: **x{target:.2f}**\n"
                f"Профит: +{profit:,}"
            )
            win = True
        else:
            profit = -bet
            new_bal = db.remove_balance(ctx.guild.id, ctx.author.id, bet, config.START_BALANCE)
            db.add_game_result(ctx.guild.id, ctx.author.id, "crash", bet, False, profit)
            embed = embeds.error(
                "💥 Ракета упала!",
                f"Крах на **x{crash_point:.2f}**\n"
                f"Ты не успел вывести на x{target:.2f}\n"
                f"Потеряно: -{bet:,}"
            )
            win = False

        embed.add_field(name="Баланс", value=f"{config.CURRENCY_EMOJI} {new_bal:,}", inline=False)
        await msg.edit(embed=embed)

        await self._post_game(ctx, win, profit, "crash")

    # ==================== КОЛЕСО ФОРТУНЫ ====================

    @commands.command(name="wheel", aliases=["колесо", "фортуна"])
    async def wheel(self, ctx, bet: int):
        """Колесо фортуны: шанс умножить ставку x0, x0.5, x1.5, x2, x3, x5, x10"""
        err = self._check_bet(bet)
        if err:
            return await ctx.send(embed=embeds.error("Ошибка", err))

        bal = self._get_balance(ctx)
        if bal < bet:
            return await ctx.send(embed=embeds.error("Ошибка", f"У тебя только {config.CURRENCY_EMOJI} {bal:,}."))

        msg = await ctx.send(embed=embeds.info(
            "🎡 Колесо фортуны",
            "╔═══════════════════╗\n"
            "║  x0  x0.5  x1.5  ║\n"
            "║  x2  x3  x5  x10  ║\n"
            "╚═══════════════════╝\n\n"
            "Крутим..."
        ))
        await asyncio.sleep(0.8)

        # Веса (чем выше множитель, тем реже)
        segments = [
            (0.0, 25),
            (0.5, 25),
            (1.5, 20),
            (2.0, 15),
            (3.0, 8),
            (5.0, 5),
            (10.0, 2),
        ]

        # Взвешенный выбор
        total = sum(w for _, w in segments)
        r = random.uniform(0, total)
        upto = 0
        multiplier = 0.0
        for val, w in segments:
            if upto + w >= r:
                multiplier = val
                break
            upto += w

        await asyncio.sleep(0.8)

        if multiplier == 0.0:
            profit = -bet
            new_bal = db.remove_balance(ctx.guild.id, ctx.author.id, bet, config.START_BALANCE)
            win = False
            title = "💀 x0 — Всё потеряно"
        elif multiplier < 1.0:
            profit = -int(bet * (1 - multiplier))
            new_bal = db.remove_balance(ctx.guild.id, ctx.author.id, profit, config.START_BALANCE)
            win = False
            title = f"📉 x{multiplier}"
        elif multiplier == 1.0:
            profit = 0
            new_bal = bal
            win = False
            title = "😐 x1"
        else:
            profit = int(bet * (multiplier - 1))
            new_bal = db.add_balance(ctx.guild.id, ctx.author.id, profit, config.START_BALANCE)
            win = True
            title = f"🎉 x{multiplier}"

        db.add_game_result(ctx.guild.id, ctx.author.id, "wheel", bet, win, profit)

        embed = (embeds.success if win else embeds.error)(
            "🎡 Колесо фортуны",
            f"**{title}**\n\n"
            f"{'✅ Победа!' if win else '❌ Проигрыш'}"
        )
        embed.add_field(name="Профит", value=f"{'+' if profit > 0 else ''}{profit:,}", inline=True)
        embed.add_field(name="Баланс", value=f"{config.CURRENCY_EMOJI} {new_bal:,}", inline=True)
        await msg.edit(embed=embed)

        await self._post_game(ctx, win, profit, "wheel")


async def setup(bot):
    await bot.add_cog(Games(bot))