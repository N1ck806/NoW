"""
Модуль квестов Nightmare.
Квесты хранятся в data/quests.json, прогресс — в БД.
"""

import json
import os
import discord
from discord.ext import commands
from datetime import datetime

import config
from utils import database as db
from utils import embeds
from utils import helpers
from utils.checks import is_admin


QUESTS_FILE = "data/quests.json"


def load_quests() -> dict:
    """Загружает квесты из JSON."""
    if not os.path.exists(QUESTS_FILE):
        return {}
    try:
        with open(QUESTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {q["id"]: q for q in data.get("quests", [])}
    except (json.JSONDecodeError, KeyError) as e:
        print(f"⚠️ Ошибка чтения {QUESTS_FILE}: {e}")
        return {}


def save_quests(quests: dict):
    """Сохраняет квесты в JSON."""
    os.makedirs("data", exist_ok=True)
    with open(QUESTS_FILE, "w", encoding="utf-8") as f:
        json.dump({"quests": list(quests.values())}, f, ensure_ascii=False, indent=2)


class Quests(commands.Cog):
    """Квесты и задания."""

    def __init__(self, bot):
        self.bot = bot

    # ==================== ПРОСМОТР ====================

    @commands.command(name="quests", aliases=["квесты", "задания"])
    async def quests(self, ctx):
        """Показать все доступные квесты."""
        quests = load_quests()
        if not quests:
            return await ctx.send(embed=embeds.info(
                "Квесты",
                "Пока квестов нет. Админ может добавить их в `data/quests.json`."
            ))

        progress_list = db.get_quest_progress(ctx.guild.id, ctx.author.id)
        progress_map = {p["id"]: p for p in progress_list}

        embed = embeds.info(
            f"📜 Квесты {config.CLAN_NAME}",
            f"Всего: **{len(quests)}**\n"
            f"Забрать награду: `{config.COMMAND_PREFIX}claim <id>`"
        )

        for qid, quest in list(quests.items())[:10]:
            prog = progress_map.get(qid, {})
            current = prog.get("progress", 0) or 0
            claimed = prog.get("claimed", 0) or 0
            completed = current >= quest["target"]

            status = "✅" if completed and not claimed else ("🎁" if claimed else "⏳")
            bar = helpers.progress_bar(current, quest["target"], 10)

            embed.add_field(
                name=f"{status} {quest['name']} `[{qid}]`",
                value=(
                    f"{quest['description']}\n"
                    f"`{bar}` {current}/{quest['target']}\n"
                    f"💰 {config.CURRENCY_EMOJI} {quest['reward']:,}"
                ),
                inline=False,
            )

        await ctx.send(embed=embed)

    # ==================== МОИ КВЕСТЫ ====================

    @commands.command(name="myquests", aliases=["мои_квесты"])
    async def myquests(self, ctx, member: discord.Member = None):
        """Прогресс по квестам участника."""
        member = member or ctx.author
        quests = load_quests()
        progress_list = db.get_quest_progress(ctx.guild.id, member.id)
        progress_map = {p["id"]: p for p in progress_list}

        if not progress_map:
            return await ctx.send(embed=embeds.info(
                "Мои квесты",
                f"У {member.mention} пока нет прогресса. Начни общаться и играть!"
            ))

        lines = []
        for qid, prog in progress_map.items():
            quest = quests.get(qid)
            if not quest:
                continue
            current = prog.get("progress", 0)
            target = quest["target"]
            completed = current >= target
            claimed = prog.get("claimed", 0)
            status = "🎁" if claimed else ("✅" if completed else "⏳")
            lines.append(f"{status} **{quest['name']}** — {current}/{target}")

        embed = embeds.info(f"📜 Прогресс {member.display_name}", "\n".join(lines[:15]))
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.send(embed=embed)

    # ==================== ЗАБРАТЬ НАГРАДУ ====================

    @commands.command(name="claim", aliases=["забрать", "получить"])
    async def claim(self, ctx, quest_id: str):
        """Забрать награду за выполненный квест."""
        quests = load_quests()
        quest = quests.get(quest_id)
        if not quest:
            return await ctx.send(embed=embeds.error("Ошибка", f"Квест `{quest_id}` не найден."))

        progress_list = db.get_quest_progress(ctx.guild.id, ctx.author.id)
        progress = next((p for p in progress_list if p["id"] == quest_id), None)

        if not progress or progress.get("progress", 0) < quest["target"]:
            current = progress.get("progress", 0) if progress else 0
            return await ctx.send(embed=embeds.error(
                "Не выполнен",
                f"Прогресс: **{current}/{quest['target']}**"
            ))

        if progress.get("claimed"):
            return await ctx.send(embed=embeds.warning("Уже забрано", "Ты уже получил награду за этот квест."))

        # Выдаём награду
        db.add_balance(ctx.guild.id, ctx.author.id, quest["reward"], config.START_BALANCE)
        db.mark_quest_claimed(ctx.guild.id, ctx.author.id, quest_id)

        await ctx.send(embed=embeds.success(
            "🎁 Награда получена!",
            f"**{quest['name']}**\n"
            f"+{config.CURRENCY_EMOJI} **{quest['reward']:,}** {config.CURRENCY_NAME}"
        ))

    # ==================== АДМИН: СПИСОК ====================

    @commands.command(name="reloadquests", aliases=["перезагрузить_квесты"])
    @is_admin()
    async def reloadquests(self, ctx):
        """Перезагрузить квесты из JSON."""
        quests = load_quests()
        await ctx.send(embed=embeds.success(
            "Квесты перезагружены",
            f"Загружено: **{len(quests)}** квестов."
        ))


async def setup(bot):
    await bot.add_cog(Quests(bot))