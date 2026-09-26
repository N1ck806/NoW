"""
Главная страница и общая статистика.
Доступ: открыт всем (даже без авторизации).
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from web import auth
from web import database as db
from web import discord_api
from web import roles
from web.config import BOT_NAME, CLAN_NAME, CURRENCY_EMOJI, BOT_TOKEN

router = APIRouter()

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    # Текущий пользователь (может быть None)
    current_user = auth.get_current_user(request)

    # === Данные для всех ===
    overview = db.get_overview()
    games = db.get_game_overview()

    # === Данные только для залогиненных ===
    top_balances = []
    top_levels = []
    users = {}
    daily_games = []

    if current_user:
        # Топы для главной
        top_balances = db.get_top_balances(10)
        top_levels = db.get_top_levels(10)

        # Собираем все user_id, чтобы одним запросом получить ники
        user_ids = set()
        for row in top_balances + top_levels:
            user_ids.add(row["user_id"])

        users = await discord_api.fetch_users(list(user_ids), BOT_TOKEN)

        # График игр за неделю
        daily_games = db.get_daily_games(7)

    # === Бейджи роли (для навбара) ===
    role_badge = roles.get_role_badge(current_user) if current_user else None
    system_badges = roles.get_system_badges(current_user) if current_user else []

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "bot_name": BOT_NAME,
            "clan_name": CLAN_NAME,
            "currency_emoji": CURRENCY_EMOJI,
            "current_user": current_user,
            "role_badge": role_badge,
            "system_badges": system_badges,
            "overview": overview,
            "games": games,
            "top_balances": top_balances,
            "top_levels": top_levels,
            "users": users,
            "daily_games": daily_games,
        }
    )