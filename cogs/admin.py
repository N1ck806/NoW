"""
Админ-модуль Nightmare.
Управление модулями, help, botinfo, утилиты.
"""

import discord
from discord.ext import commands
import platform
import time

import config
from utils import embeds
from utils import database as db
from utils.checks import is_admin


# Полный список модулей — используется для reload
ALL_COGS = [
    "moderation", "economy", "activity", "roles",
    "welcome", "stats", "games", "utility", "admin",
    "shop", "quests", "reputation", "achievements",
    "voice", "analytics", "events",
]


class Admin(commands.Cog):
    """Админ-команды."""

    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()

    # ==================== RELOAD / LOAD / UNLOAD ====================

    @commands.command(name="reload")
    @is_admin()
    async def reload(self, ctx, cog: str = None):
        """Перезагрузить модуль или все модули."""
        if cog:
            cog = cog.replace("cogs.", "")
            if cog not in ALL_COGS:
                return await ctx.send(embed=embeds.error(
                    "Ошибка",
                    f"Модуль `{cog}` не найден.\nДоступные: {', '.join(ALL_COGS)}"
                ))
            try:
                await self.bot.reload_extension(f"cogs.{cog}")
                await ctx.send(embed=embeds.success("Перезагружено", f"Модуль `{cog}` перезагружен."))
            except Exception as e:
                await ctx.send(embed=embeds.error("Ошибка", f"```{e}```"))
        else:
            reloaded, failed = [], []
            for c in ALL_COGS:
                try:
                    await self.bot.reload_extension(f"cogs.{c}")
                    reloaded.append(c)
                except Exception as e:
                    failed.append(f"`{c}`: {e}")

            if failed:
                await ctx.send(embed=embeds.error(
                    "Ошибки при перезагрузке",
                    "\n".join(failed)
                ))
            await ctx.send(embed=embeds.success(
                "Перезагружено",
                f"✅ Успешно: {len(reloaded)}/{len(ALL_COGS)}\n"
                f"❌ Ошибок: {len(failed)}"
            ))

    @commands.command(name="load")
    @is_admin()
    async def load(self, ctx, cog: str):
        """Загрузить модуль."""
        cog = cog.replace("cogs.", "")
        try:
            await self.bot.load_extension(f"cogs.{cog}")
            await ctx.send(embed=embeds.success("Загружено", f"Модуль `{cog}` загружен."))
        except Exception as e:
            await ctx.send(embed=embeds.error("Ошибка", f"```{e}```"))

    @commands.command(name="unload")
    @is_admin()
    async def unload(self, ctx, cog: str):
        """Выгрузить модуль."""
        cog = cog.replace("cogs.", "")
        try:
            await self.bot.unload_extension(f"cogs.{cog}")
            await ctx.send(embed=embeds.success("Выгружено", f"Модуль `{cog}` выгружен."))
        except Exception as e:
            await ctx.send(embed=embeds.error("Ошибка", f"```{e}```"))

    @commands.command(name="cogs", aliases=["модули"])
    @is_admin()
    async def cogs_list(self, ctx):
        """Показать загруженные модули."""
        loaded = list(self.bot.cogs.keys())
        await ctx.send(embed=embeds.info(
            f"📦 Модули ({len(loaded)}/{len(ALL_COGS)})",
            "**Загружены:**\n" + ", ".join(f"`{c}`" for c in loaded)
        ))

    # ==================== SYNC SLASH ====================

    @commands.command(name="sync")
    @is_admin()
    async def sync(self, ctx):
        """Синхронизировать слэш-команды."""
        try:
            synced = await self.bot.tree.sync(guild=ctx.guild)
            await ctx.send(embed=embeds.success(
                "Синхронизация",
                f"Синхронизировано команд: **{len(synced)}**"
            ))
        except Exception as e:
            await ctx.send(embed=embeds.error("Ошибка", f"```{e}```"))

    # ==================== BOTINFO ====================

    @commands.command(name="botinfo", aliases=["about", "инфо"])
    async def botinfo(self, ctx):
        """Информация о боте."""
        uptime_sec = int(time.time() - self.start_time)
        days = uptime_sec // 86400
        hours = (uptime_sec % 86400) // 3600
        minutes = (uptime_sec % 3600) // 60
        seconds = uptime_sec % 60

        total_members = sum(g.member_count for g in self.bot.guilds)

        embed = embeds.info(
            f"🤖 {config.BOT_NAME}",
            f"Бот клана **{config.CLAN_NAME}**.\n\n"
            f"**Модулей:** {len(self.bot.cogs)}\n"
            f"**Команд:** {len(self.bot.commands)}\n"
            f"**Серверов:** {len(self.bot.guilds)}\n"
            f"**Участников:** {total_members:,}\n"
            f"**Задержка:** {round(self.bot.latency * 1000)} мс\n"
            f"**Аптайм:** {days}д {hours}ч {minutes}м {seconds}с\n"
            f"**Python:** {platform.python_version()}\n"
            f"**discord.py:** {discord.__version__}\n"
            f"**Префикс:** `{config.COMMAND_PREFIX}`"
        )
        if self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)
        await ctx.send(embed=embed)

    # ==================== UPTIME ====================

    @commands.command(name="uptime", aliases=["аптайм"])
    async def uptime(self, ctx):
        """Время работы бота."""
        uptime_sec = int(time.time() - self.start_time)
        days = uptime_sec // 86400
        hours = (uptime_sec % 86400) // 3600
        minutes = (uptime_sec % 3600) // 60
        seconds = uptime_sec % 60

        await ctx.send(embed=embeds.info(
            "⏱️ Аптайм",
            f"**{days}д {hours}ч {minutes}м {seconds}с**"
        ))

    # ==================== INVITE ====================

    @commands.command(name="invite", aliases=["пригласить"])
    async def invite(self, ctx):
        """Ссылка для приглашения бота."""
        url = discord.utils.oauth_url(
            self.bot.user.id,
            permissions=discord.Permissions(administrator=True),
            scopes=("bot", "applications.commands")
        )
        await ctx.send(embed=embeds.info(
            "🔗 Пригласить бота",
            f"[Нажми сюда]({url})"
        ))

    # ==================== HELP ====================

    @commands.command(name="help", aliases=["помощь", "хелп", "команды"])
    async def help(self, ctx, category: str = None):
        """Показать список команд."""
        p = config.COMMAND_PREFIX

        if category:
            cat = category.lower()
            sections = {
                "mod": ("🛡️ Модерация", (
                    f"`{p}warn @user причина` — предупреждение\n"
                    f"`{p}warnings @user` — список предупреждений\n"
                    f"`{p}clearwarns @user` — сбросить предупреждения\n"
                    f"`{p}mute @user 10m причина` — мут\n"
                    f"`{p}unmute @user` — снять мут\n"
                    f"`{p}kick @user причина` — кик\n"
                    f"`{p}ban @user причина` — бан\n"
                    f"`{p}softban @user причина` — софтбан\n"
                    f"`{p}unban ID` — разбан\n"
                    f"`{p}clear 50` — очистить чат\n"
                    f"`{p}clearuser @user 50` — очистить сообщения юзера\n"
                    f"`{p}slowmode 10` — слоумод\n"
                    f"`{p}lock` / `{p}unlock` — закрыть/открыть канал\n"
                    f"`{p}history @user` — история наказаний"
                )),
                "eco": ("💰 Экономика", (
                    f"`{p}balance [@user]` — баланс\n"
                    f"`{p}daily` — ежедневная награда (со стриками!)\n"
                    f"`{p}pay @user 100` — перевод (комиссия 2%)\n"
                    f"`{p}top` — топ богачей\n"
                    f"`{p}rich` — самый богатый\n"
                    f"`{p}transactions [@user]` — история транзакций\n"
                    f"`{p}economystats` — статистика экономики *(админ)*\n"
                    f"`{p}addcoins @user 100` — начислить *(админ)*\n"
                    f"`{p}removecoins @user 100` — списать *(админ)*\n"
                    f"`{p}setcoins @user 100` — установить *(админ)*"
                )),
                "act": ("📈 Активность", (
                    f"`{p}rank [@user]` — уровень и опыт\n"
                    f"`{p}leaderboard` — топ по уровням\n"
                    f"`{p}myrank` — твоя позиция в топах\n"
                    f"`{p}prestige` — престиж"
                )),
                "games": ("🎮 Игры", (
                    f"`{p}coinflip 100 орел` — монетка\n"
                    f"`{p}dice 100 [число]` — кубик\n"
                    f"`{p}slots 100` — слоты\n"
                    f"`{p}roulette 100 red` — рулетка\n"
                    f"`{p}blackjack 100` — блэкджек\n"
                    f"`{p}duel @user 100` — дуэль\n"
                    f"`{p}crash 100 2.0` — ракета\n"
                    f"`{p}wheel 100` — колесо фортуны"
                )),
                "profile": ("👤 Профиль", (
                    f"`{p}stats [@user]` — статистика\n"
                    f"`{p}card [@user]` — краткая карточка\n"
                    f"`{p}mygames [@user]` — статистика игр\n"
                    f"`{p}serverstats` — статистика сервера\n"
                    f"`{p}activitytop` — топ по сообщениям\n"
                    f"`{p}gametop` — топ игроков\n"
                    f"`{p}achievements [@user]` — достижения\n"
                    f"`{p}allach` — список всех достижений\n"
                    f"`{p}rep @user` — репутация\n"
                    f"`{p}myrep [@user]` — моя репутация\n"
                    f"`{p}reptop` — топ репутации"
                )),
                "util": ("⚙️ Утилиты", (
                    f"`{p}poll Вопрос? | Вар1 | Вар2` — опрос\n"
                    f"`{p}quickpoll Вопрос?` — быстрый опрос Да/Нет\n"
                    f"`{p}say текст` — сказать от бота\n"
                    f"`{p}embed Заголовок | Описание` — embed\n"
                    f"`{p}avatar [@user]` — аватар\n"
                    f"`{p}banner [@user]` — баннер\n"
                    f"`{p}userinfo [@user]` — инфо о юзере\n"
                    f"`{p}serverinfo` — инфо о сервере\n"
                    f"`{p}remind 10m текст` — напоминание\n"
                    f"`{p}choose вар1 | вар2` — выбор\n"
                    f"`{p}roll 2d20` — бросок кубика\n"
                    f"`{p}id` / `{p}channelid` / `{p}roleid` — ID"
                )),
                "roles": ("🎭 Роли *(админ)*", (
                    f"`{p}rolepanel Заголовок | Описание` — создать панель\n"
                    f"`{p}reactionrole ID эмодзи @роль` — привязать\n"
                    f"`{p}listrr ID` — список привязок\n"
                    f"`{p}removerr ID эмодзи` — удалить\n"
                    f"`{p}clearrr ID` — очистить все\n"
                    f"`{p}setlevelrole 5 @роль` — автороль по уровню\n"
                    f"`{p}listlevelroles` — список авторолей"
                )),
                "shop": ("🛒 Магазин", (
                    f"`{p}shop` — посмотреть магазин\n"
                    f"`{p}item ID` — инфо о товаре\n"
                    f"`{p}buy ID` — купить товар\n"
                    f"`{p}myitems` — мои покупки\n"
                    f"`{p}additem Название Цена [@роль] | Описание` — добавить *(админ)*\n"
                    f"`{p}removeitem Название` — удалить *(админ)*\n"
                    f"`{p}setstock ID Склад` — изменить склад *(админ)*"
                )),
                "quests": ("📜 Квесты", (
                    f"`{p}quests` — все квесты\n"
                    f"`{p}myquests [@user]` — мой прогресс\n"
                    f"`{p}claim ID` — забрать награду"
                )),
                "voice": ("🎙️ Войс", (
                    f"`{p}voicetime [@user]` — время в войсе\n"
                    f"`{p}voicetop` — топ по войсу\n"
                    f"`{p}voiceonline` — кто сейчас в войсе"
                )),
                "events": ("🎊 Ивенты", (
                    f"`{p}giveaway 1h 1 Приз` — розыгрыш\n"
                    f"`{p}reroll ID` — перевыбрать победителя\n"
                    f"`{p}endgiveaway ID` — завершить досрочно\n"
                    f"`{p}quiz` — викторина\n"
                    f"`{p}lottery 100` — лотерея\n"
                    f"`{p}buyticket 1` — купить билет\n"
                    f"`{p}events` — активные ивенты"
                )),
                "analytics": ("📊 Аналитика *(стафф)*", (
                    f"`{p}analytics [дней]` — общая аналитика\n"
                    f"`{p}activitychart [дней]` — график активности\n"
                    f"`{p}topactive [дней]` — топ активных\n"
                    f"`{p}report [дней]` — полный отчёт\n"
                    f"`{p}forecast [дней]` — прогноз экономики\n"
                    f"`{p}export users` — экспорт в CSV *(админ)*"
                )),
                "admin": ("🔧 Админ", (
                    f"`{p}reload [модуль]` — перезагрузить\n"
                    f"`{p}load модуль` — загрузить\n"
                    f"`{p}unload модуль` — выгрузить\n"
                    f"`{p}cogs` — список модулей\n"
                    f"`{p}sync` — синхронизировать слэш-команды\n"
                    f"`{p}botinfo` — инфо о боте\n"
                    f"`{p}uptime` — аптайм\n"
                    f"`{p}invite` — ссылка приглашения"
                )),
            }

            # Алиасы категорий
            aliases_map = {
                "moderation": "mod", "мод": "mod", "модерация": "mod",
                "economy": "eco", "эко": "eco", "экономика": "eco",
                "activity": "act", "актив": "act", "активность": "act",
                "game": "games", "игры": "games", "игра": "games",
                "prof": "profile", "профиль": "profile",
                "utils": "util", "утилиты": "util",
                "role": "roles", "роли": "roles",
                "магазин": "shop",
                "квесты": "quests", "quest": "quests",
                "голос": "voice", "войс": "voice",
                "ивент": "events", "события": "events",
                "аналитика": "analytics",
                "админка": "admin",
            }
            cat = aliases_map.get(cat, cat)

            for key, (title, content) in sections.items():
                if cat == key or cat in key or cat in title.lower():
                    await ctx.send(embed=embeds.info(title, content))
                    return

            return await ctx.send(embed=embeds.error(
                "Ошибка",
                f"Категория `{category}` не найдена.\n"
                f"Доступные: `mod`, `eco`, `act`, `games`, `profile`, `util`, "
                f"`roles`, `shop`, `quests`, `voice`, `events`, `analytics`, `admin`"
            ))

        # Полный help
        embed = embeds.info(
            f"📖 Команды {config.BOT_NAME}",
            f"Префикс: `{p}`\n"
            f"Клан: **{config.CLAN_NAME}**\n\n"
            f"Используй `{p}help <категория>` для подробностей."
        )

        embed.add_field(
            name="🛡️ Модерация",
            value=f"`{p}warn`, `{p}mute`, `{p}kick`, `{p}ban`\n`{p}help mod`",
            inline=True,
        )
        embed.add_field(
            name="💰 Экономика",
            value=f"`{p}balance`, `{p}daily`, `{p}pay`, `{p}top`\n`{p}help eco`",
            inline=True,
        )
        embed.add_field(
            name="📈 Активность",
            value=f"`{p}rank`, `{p}leaderboard`\n`{p}help act`",
            inline=True,
        )
        embed.add_field(
            name="🎮 Игры",
            value=f"`{p}coinflip`, `{p}dice`, `{p}slots`, `{p}crash`\n`{p}help games`",
            inline=True,
        )
        embed.add_field(
            name="👤 Профиль",
            value=f"`{p}stats`, `{p}achievements`, `{p}rep`\n`{p}help profile`",
            inline=True,
        )
        embed.add_field(
            name="⚙️ Утилиты",
            value=f"`{p}poll`, `{p}userinfo`, `{p}remind`\n`{p}help util`",
            inline=True,
        )
        embed.add_field(
            name="🎭 Роли",
            value=f"`{p}rolepanel`, `{p}reactionrole`\n`{p}help roles`",
            inline=True,
        )
        embed.add_field(
            name="🛒 Магазин",
            value=f"`{p}shop`, `{p}buy`, `{p}myitems`\n`{p}help shop`",
            inline=True,
        )
        embed.add_field(
            name="📜 Квесты",
            value=f"`{p}quests`, `{p}myquests`, `{p}claim`\n`{p}help quests`",
            inline=True,
        )
        embed.add_field(
            name="🎙️ Войс",
            value=f"`{p}voicetime`, `{p}voicetop`\n`{p}help voice`",
            inline=True,
        )
        embed.add_field(
            name="🎊 Ивенты",
            value=f"`{p}giveaway`, `{p}quiz`, `{p}lottery`\n`{p}help events`",
            inline=True,
        )
        embed.add_field(
            name="📊 Аналитика",
            value=f"`{p}analytics`, `{p}report`, `{p}export`\n`{p}help analytics`",
            inline=True,
        )
        embed.add_field(
            name="🔧 Админ",
            value=f"`{p}reload`, `{p}sync`, `{p}botinfo`\n`{p}help admin`",
            inline=True,
        )

        if self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Admin(bot))