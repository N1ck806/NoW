"""
Шаблоны Embed-сообщений Nightmare.
"""

import discord
from datetime import datetime
import config


def _base(title: str, description: str, color: int, emoji: str = None) -> discord.Embed:
    """Базовый конструктор embed."""
    if emoji:
        title = f"{emoji} {title}"
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.utcnow(),
    )
    embed.set_footer(
        text=f"{config.BOT_NAME} • {config.CLAN_NAME}",
        icon_url=None,
    )
    return embed


# ==================== БАЗОВЫЕ ====================

def success(title: str, description: str = "") -> discord.Embed:
    """Зелёный — успех."""
    return _base(title, description, config.COLOR_SUCCESS, "✅")


def error(title: str, description: str = "") -> discord.Embed:
    """Красный — ошибка."""
    return _base(title, description, config.COLOR_ERROR, "❌")


def warning(title: str, description: str = "") -> discord.Embed:
    """Жёлтый — предупреждение."""
    return _base(title, description, config.COLOR_WARNING, "⚠️")


def info(title: str, description: str = "") -> discord.Embed:
    """Синий — информация."""
    return _base(title, description, config.COLOR_INFO, "ℹ️")


def moderation(title: str, description: str = "") -> discord.Embed:
    """Для логов модерации."""
    return _base(title, description, config.COLOR_MAIN, "🔨")


def economy(title: str, description: str = "") -> discord.Embed:
    """Для экономики."""
    return _base(title, description, config.COLOR_SUCCESS, config.CURRENCY_EMOJI)


# ==================== СПЕЦИАЛЬНЫЕ ====================

def level_up(member: discord.Member, level: int, reward: int) -> discord.Embed:
    """Поздравление с новым уровнем."""
    embed = discord.Embed(
        title="🎉 Новый уровень!",
        description=(
            f"{member.mention} достиг **{level}** уровня!\n\n"
            f"**Награда:** {config.CURRENCY_EMOJI} {reward:,} {config.CURRENCY_NAME}"
        ),
        color=config.COLOR_SUCCESS,
        timestamp=datetime.utcnow(),
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"{config.BOT_NAME} • {config.CLAN_NAME}")
    return embed


def game_result(
    game_name: str,
    win: bool,
    description: str,
    profit: int,
    new_balance: int,
    fields: dict = None,
) -> discord.Embed:
    """Результат игры."""
    emoji = "🎉" if win else "💀"
    color = config.COLOR_SUCCESS if win else config.COLOR_ERROR

    embed = discord.Embed(
        title=f"{emoji} {game_name}",
        description=description,
        color=color,
        timestamp=datetime.utcnow(),
    )

    if fields:
        for name, value in fields.items():
            embed.add_field(name=name, value=value, inline=True)

    profit_str = f"+{profit:,}" if profit > 0 else f"{profit:,}"
    embed.add_field(name="Профит", value=profit_str, inline=True)
    embed.add_field(name=f"Баланс", value=f"{config.CURRENCY_EMOJI} {new_balance:,}", inline=True)
    embed.set_footer(text=f"{config.BOT_NAME} • {config.CLAN_NAME}")
    return embed


def user_profile(
    member: discord.Member,
    level: int,
    xp: int,
    next_level_xp: int,
    balance: int,
    messages: int,
    warnings: int = 0,
    rank_pos: int = None,
) -> discord.Embed:
    """Профиль пользователя."""
    embed = discord.Embed(
        title=f"👤 {member.display_name}",
        color=config.COLOR_INFO,
        timestamp=datetime.utcnow(),
    )
    embed.set_thumbnail(url=member.display_avatar.url)

    # Прогресс-бар
    current_xp = xp - (next_level_xp - (next_level_xp - xp))  # упрощённо
    bar_length = 15
    filled = min(bar_length, max(0, int(bar_length * (xp % 1000) / 1000)))
    bar = "█" * filled + "░" * (bar_length - filled)

    rank_str = f" *(#{rank_pos})*" if rank_pos else ""
    embed.add_field(
        name="📊 Прогресс",
        value=(
            f"**Уровень:** {level}{rank_str}\n"
            f"**Опыт:** {xp:,} / {next_level_xp:,}\n"
            f"`{bar}`"
        ),
        inline=False,
    )
    embed.add_field(
        name="💰 Экономика",
        value=f"{config.CURRENCY_EMOJI} {balance:,} {config.CURRENCY_NAME}",
        inline=True,
    )
    embed.add_field(
        name="💬 Активность",
        value=f"{messages:,} сообщений",
        inline=True,
    )
    if warnings > 0:
        embed.add_field(
            name="⚠️ Предупреждения",
            value=f"{warnings}",
            inline=True,
        )

    embed.set_footer(text=f"ID: {member.id} • {config.BOT_NAME}")
    return embed


def top_list(title: str, entries: list, header: str = None) -> discord.Embed:
    """Список топа. entries — список строк."""
    description = ""
    if header:
        description += f"{header}\n\n"

    if not entries:
        description += "_Пусто_"
    else:
        description += "\n".join(entries)

    return _base(title, description, config.COLOR_INFO, "🏆")


def transaction_log(
    from_user: discord.Member,
    to_user: discord.Member,
    amount: int,
    commission: int = 0,
    reason: str = None,
) -> discord.Embed:
    """Лог транзакции."""
    desc = (
        f"**От:** {from_user.mention}\n"
        f"**Кому:** {to_user.mention}\n"
        f"**Сумма:** {config.CURRENCY_EMOJI} {amount:,}\n"
    )
    if commission:
        desc += f"**Комиссия:** {commission:,}\n"
    if reason:
        desc += f"**Причина:** {reason}"

    return _base("💸 Транзакция", desc, config.COLOR_INFO, "💸")


def shop_item_card(item: dict) -> discord.Embed:
    """Карточка товара в магазине."""
    stock_str = "∞" if item.get("stock", -1) == -1 else str(item["stock"])
    embed = discord.Embed(
        title=f"🛒 {item['name']}",
        description=item.get("description") or "_Без описания_",
        color=config.COLOR_SUCCESS,
        timestamp=datetime.utcnow(),
    )
    embed.add_field(
        name="Цена",
        value=f"{config.CURRENCY_EMOJI} {item['price']:,}",
        inline=True,
    )
    embed.add_field(name="В наличии", value=stock_str, inline=True)
    if item.get("role_id"):
        embed.add_field(
            name="Роль",
            value=f"<@&{item['role_id']}>",
            inline=True,
        )
    embed.set_footer(text=f"ID: {item['id']} • {config.BOT_NAME}")
    return embed


def quest_card(quest: dict, progress: int = 0) -> discord.Embed:
    """Карточка квеста."""
    target = quest["target"]
    percent = min(100, int(progress / target * 100)) if target > 0 else 0
    bar_len = 15
    filled = int(bar_len * percent / 100)
    bar = "█" * filled + "░" * (bar_len - filled)

    completed = progress >= target

    embed = discord.Embed(
        title=f"📜 {quest['name']}",
        description=quest.get("description") or "_Без описания_",
        color=config.COLOR_SUCCESS if completed else config.COLOR_INFO,
        timestamp=datetime.utcnow(),
    )
    embed.add_field(
        name="Прогресс",
        value=f"`{bar}` {progress}/{target}",
        inline=False,
    )
    embed.add_field(
        name="Награда",
        value=f"{config.CURRENCY_EMOJI} {quest['reward']:,}",
        inline=True,
    )
    if completed:
        embed.add_field(name="Статус", value="✅ Выполнен", inline=True)

    embed.set_footer(text=f"{config.BOT_NAME} • {config.CLAN_NAME}")
    return embed


def levelup_card(member: discord.Member, level: int) -> discord.Embed:
    """Простая карточка повышения уровня."""
    return _base(
        "🎉 Новый уровень!",
        f"{member.mention} достиг **{level}** уровня!",
        config.COLOR_SUCCESS,
        "🎉",
    )


def rep_card(from_user: discord.Member, to_user: discord.Member, new_rep: int) -> discord.Embed:
    """Карточка репутации."""
    return _base(
        "⭐ Репутация",
        f"{from_user.mention} повысил репутацию {to_user.mention}!\n\n"
        f"**Репутация {to_user.display_name}:** {new_rep}",
        config.COLOR_WARNING,
        "⭐",
    )