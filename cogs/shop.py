"""
Модуль магазина Nightmare.
"""

import discord
from discord.ext import commands

import config
from utils import database as db
from utils import embeds
from utils import helpers
from utils.checks import is_admin


class Shop(commands.Cog):
    """Магазин клана."""

    def __init__(self, bot):
        self.bot = bot

    # ==================== ПРОСМОТР ====================

    @commands.command(name="shop", aliases=["магазин", "лавка"])
    async def shop(self, ctx):
        """Показать товары магазина."""
        items = db.get_shop_items(ctx.guild.id)
        if not items:
            return await ctx.send(embed=embeds.info(
                "Магазин пуст",
                "Администраторы пока не добавили товары."
            ))

        embed = embeds.info(
            f"🛒 Магазин {config.CLAN_NAME}",
            f"Товаров: **{len(items)}**\n"
            f"Купить: `{config.COMMAND_PREFIX}buy <ID>`"
        )

        for item in items[:10]:
            stock_str = "∞" if item["stock"] == -1 else str(item["stock"])
            role_str = f" • <@&{item['role_id']}>" if item["role_id"] else ""
            embed.add_field(
                name=f"[{item['id']}] {item['name']}",
                value=(
                    f"{item.get('description') or '_Без описания_'}\n"
                    f"💰 {config.CURRENCY_EMOJI} **{item['price']:,}** • Склад: {stock_str}{role_str}"
                ),
                inline=False,
            )

        if len(items) > 10:
            embed.set_footer(text=f"Показано 10 из {len(items)} • {config.BOT_NAME}")

        await ctx.send(embed=embed)

    # ==================== ИНФО О ТОВАРЕ ====================

    @commands.command(name="item", aliases=["товар", "предмет"])
    async def item(self, ctx, item_id: int):
        """Информация о товаре."""
        item = db.get_shop_item(ctx.guild.id, item_id)
        if not item:
            return await ctx.send(embed=embeds.error("Ошибка", f"Товар с ID `{item_id}` не найден."))

        await ctx.send(embed=embeds.shop_item_card(item))

    # ==================== КУПИТЬ ====================

    @commands.command(name="buy", aliases=["купить"])
    async def buy(self, ctx, item_id: int):
        """Купить товар из магазина."""
        item = db.get_shop_item(ctx.guild.id, item_id)
        if not item:
            return await ctx.send(embed=embeds.error("Ошибка", f"Товар с ID `{item_id}` не найден."))

        # Проверка склада
        if item["stock"] == 0:
            return await ctx.send(embed=embeds.error("Ошибка", "Товар закончился."))

        # Проверка баланса
        balance = db.get_balance(ctx.guild.id, ctx.author.id, config.START_BALANCE)
        if balance < item["price"]:
            return await ctx.send(embed=embeds.error(
                "Недостаточно средств",
                f"Товар стоит {config.CURRENCY_EMOJI} **{item['price']:,}**.\n"
                f"У тебя только **{balance:,}**."
            ))

        # Проверка роли (если уже есть)
        if item["role_id"]:
            role = ctx.guild.get_role(item["role_id"])
            if not role:
                return await ctx.send(embed=embeds.error("Ошибка", "Роль товара не найдена на сервере."))
            if role in ctx.author.roles:
                return await ctx.send(embed=embeds.error("Ошибка", f"У тебя уже есть роль {role.mention}."))

        # Списываем
        db.remove_balance(ctx.guild.id, ctx.author.id, item["price"], config.START_BALANCE)

        # Уменьшаем склад
        if item["stock"] > 0:
            db.update_shop_stock(ctx.guild.id, item_id, item["stock"] - 1)

        # Выдаём роль
        role_msg = ""
        if item["role_id"]:
            role = ctx.guild.get_role(item["role_id"])
            if role and role < ctx.guild.me.top_role:
                try:
                    await ctx.author.add_roles(role, reason=f"Покупка: {item['name']}")
                    role_msg = f"\n🎭 Выдана роль: {role.mention}"
                except discord.Forbidden:
                    role_msg = "\n⚠️ Не удалось выдать роль (обратись к админам)."

        # Записываем покупку
        db.buy_item(ctx.guild.id, ctx.author.id, item_id)
        db.add_transaction(
            ctx.guild.id, ctx.author.id, None,
            item["price"], "shop", f"Покупка: {item['name']}"
        )

        await ctx.send(embed=embeds.success(
            "Покупка совершена",
            f"🛒 **{item['name']}**\n"
            f"Списано: {config.CURRENCY_EMOJI} **{item['price']:,}**{role_msg}"
        ))

    # ==================== МОИ ПОКУПКИ ====================

    @commands.command(name="myitems", aliases=["мои_товары", "инвентарь"])
    async def myitems(self, ctx, member: discord.Member = None):
        """Показать купленные товары."""
        member = member or ctx.author
        items = db.get_user_items(ctx.guild.id, member.id)

        if not items:
            return await ctx.send(embed=embeds.info(
                "Инвентарь пуст",
                f"У {member.mention} нет купленных товаров."
            ))

        embed = embeds.info(
            f"🎒 Инвентарь {member.display_name}",
            f"Товаров: **{len(items)}**"
        )
        for item in items[:15]:
            embed.add_field(
                name=item["name"],
                value=f"💰 {item['price']:,}",
                inline=True,
            )

        await ctx.send(embed=embed)

    # ==================== АДМИН: ДОБАВИТЬ ====================

    @commands.command(name="additem", aliases=["добавить_товар"])
    @is_admin()
    async def additem(self, ctx, name: str, price: int, role: discord.Role = None, *, description: str = "Без описания"):
        """
        Добавить товар в магазин.
        !additem Название Цена [@роль] | Описание
        """
        if price <= 0:
            return await ctx.send(embed=embeds.error("Ошибка", "Цена должна быть больше нуля."))

        if role and role >= ctx.guild.me.top_role:
            return await ctx.send(embed=embeds.error(
                "Ошибка",
                f"Роль {role.mention} выше роли бота. Бот не сможет её выдать."
            ))

        item_id = db.add_shop_item(
            ctx.guild.id,
            name=name,
            description=description,
            price=price,
            role_id=role.id if role else None,
            stock=-1,
        )

        if item_id is None:
            return await ctx.send(embed=embeds.error("Ошибка", f"Товар `{name}` уже существует."))

        await ctx.send(embed=embeds.success(
            "Товар добавлен",
            f"**[{item_id}]** {name}\n"
            f"💰 Цена: {config.CURRENCY_EMOJI} {price:,}\n"
            f"🎭 Роль: {role.mention if role else '—'}\n"
            f"📦 Склад: ∞"
        ))

    # ==================== АДМИН: УДАЛИТЬ ====================

    @commands.command(name="removeitem", aliases=["удалить_товар"])
    @is_admin()
    async def removeitem(self, ctx, *, name: str):
        """Удалить товар из магазина."""
        deleted = db.remove_shop_item(ctx.guild.id, name)
        if deleted:
            await ctx.send(embed=embeds.success("Удалено", f"Товар `{name}` удалён."))
        else:
            await ctx.send(embed=embeds.error("Ошибка", f"Товар `{name}` не найден."))

    # ==================== АДМИН: СКЛАД ====================

    @commands.command(name="setstock", aliases=["склад"])
    @is_admin()
    async def setstock(self, ctx, item_id: int, stock: int):
        """Установить склад товара (-1 = бесконечно)."""
        item = db.get_shop_item(ctx.guild.id, item_id)
        if not item:
            return await ctx.send(embed=embeds.error("Ошибка", "Товар не найден."))

        if stock < -1:
            return await ctx.send(embed=embeds.error("Ошибка", "Склад: -1 (∞) или ≥ 0."))

        db.update_shop_stock(ctx.guild.id, item_id, stock)
        stock_str = "∞" if stock == -1 else str(stock)
        await ctx.send(embed=embeds.success(
            "Склад обновлён",
            f"**{item['name']}** → {stock_str}"
        ))


async def setup(bot):
    await bot.add_cog(Shop(bot))