"""
Страницы профилей участников.
Определяет статус (тир) для хоррор-эффектов.
Доступ: только для Призраков (ghost) и выше.
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from web import auth
from web import database as db
from web import discord_api
from web import roles
from web.config import (
    BOT_NAME,
    CLAN_NAME,
    CURRENCY_EMOJI,
    BOT_TOKEN,
    GUILD_ID,
    root_config,
)

router = APIRouter()

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# ==================== ТИРЫ (УРОВНИ ЖУТИ) ====================

# Тир определяет уровень хоррор-оформления профиля:
# 0 — обычный гость / призрак без ролей
# 1 — новобранец
# 2 — участник клана
# 3 — младший персонал
# 4 — старший персонал
# 5 — власть (админ / владелец)

TIER_LABELS = {
    0: {"name": "Призрак",         "icon": "👻", "color": "#8a92a6"},
    1: {"name": "Новобранец",      "icon": "🌱", "color": "#4ade80"},
    2: {"name": "Участник клана",  "icon": "⚔️", "color": "#7f5af0"},
    3: {"name": "Маленький админ", "icon": "🛡️", "color": "#fbbf24"},
    4: {"name": "Админ клана",     "icon": "💀", "color": "#ff0033"},
    5: {"name": "Администратор",   "icon": "👑", "color": "#ff0033"},
}


def _resolve_tier(role_ids: set) -> int:
    """Определяет тир по набору ID ролей."""
    checks = [
        (root_config.ROLE_ADMIN, 5),
        (root_config.ROLE_CLAN_ADMIN, 4),
        (root_config.ROLE_SMALL_ADMIN, 3),
        (root_config.ROLE_MEMBER, 2),
        (root_config.ROLE_RECRUIT, 1),
    ]
    for role_id, tier in checks:
        if role_id and role_id in role_ids:
            return tier
    return 0


async def _get_user_roles(user_id: int) -> set:
    """Получает роли пользователя через Discord API."""
    guild_member = await discord_api.fetch_guild_member(user_id, GUILD_ID, BOT_TOKEN)
    if not guild_member:
        return set()
    return set(guild_member.get("roles", []))


# ==================== ПРОФИЛЬ ====================

@router.get("/profile/{user_id}", response_class=HTMLResponse)
async def profile(request: Request, user_id: int):
    # === Защита: только для залогиненных + роль ghost ===
    redirect = roles.redirect_if_not_ghost(request)
    if redirect:
        return redirect

    user = db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Участник не найден")

    # Discord-данные
    discord_user = await discord_api.fetch_user(user_id, BOT_TOKEN)
    if discord_user:
        user_name = discord_user["display_name"]
        avatar_url = discord_user["avatar_url"]
    else:
        user_name = f"ID {user_id}"
        avatar_url = None

    # Роли → тир
    role_ids = await _get_user_roles(user_id)
    tier = _resolve_tier(role_ids)
    tier_info = TIER_LABELS[tier]

    # Данные профиля
    warnings = db.get_user_warnings(user_id, 20)
    transactions = db.get_user_transactions(user_id, 20)
    achievements = db.get_user_achievements(user_id)
    game_stats = db.get_user_games_stats(user_id)

    # Ники связанных пользователей
    tx_user_ids = set()
    for t in transactions:
        if t.get("from_id"):
            tx_user_ids.add(t["from_id"])
        if t.get("to_id"):
            tx_user_ids.add(t["to_id"])
    tx_users = await discord_api.fetch_users(list(tx_user_ids), BOT_TOKEN)

    mod_ids = set(w["moderator_id"] for w in warnings)
    mod_users = await discord_api.fetch_users(list(mod_ids), BOT_TOKEN)

    # Текущий пользователь (для навбара)
    current_user = auth.get_current_user(request)

    return templates.TemplateResponse(
        request=request,
        name="profile.html",
        context={
            "bot_name": BOT_NAME,
            "clan_name": CLAN_NAME,
            "currency_emoji": CURRENCY_EMOJI,
            "current_user": current_user,
            "user": user,
            "user_id": user_id,
            "user_name": user_name,
            "avatar_url": avatar_url,
            "discord_user": discord_user,
            "tier": tier,
            "tier_info": tier_info,
            "warnings": warnings,
            "transactions": transactions,
            "achievements": achievements,
            "game_stats": game_stats,
            "tx_users": tx_users,
            "mod_users": mod_users,
        }
    )