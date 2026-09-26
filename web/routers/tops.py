"""
Страница со всеми топами.
Доступ: только для Призраков (ghost) и выше.
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


@router.get("/tops", response_class=HTMLResponse)
async def tops(request: Request):
    # === Защита: только для залогиненных + роль ghost ===
    redirect = roles.redirect_if_not_ghost(request)
    if redirect:
        return redirect

    top_balances = db.get_top_balances(20)
    top_levels = db.get_top_levels(20)
    top_reputation = db.get_top_reputation(20)
    top_voice = db.get_top_voice(20)
    top_players = db.get_top_players(20)

    user_ids = set()
    for lst in (top_balances, top_levels, top_reputation, top_voice, top_players):
        for row in lst:
            user_ids.add(row["user_id"])

    users = await discord_api.fetch_users(list(user_ids), BOT_TOKEN)

    return templates.TemplateResponse(
        request=request,
        name="top.html",
        context={
            "bot_name": BOT_NAME,
            "clan_name": CLAN_NAME,
            "currency_emoji": CURRENCY_EMOJI,
            "current_user": auth.get_current_user(request),
            "top_balances": top_balances,
            "top_levels": top_levels,
            "top_reputation": top_reputation,
            "top_voice": top_voice,
            "top_players": top_players,
            "users": users,
        }
    )