"""
Логи модерации и транзакций.

Доступ:
- /logs         — только для модераторов, кодеров и админов
- /transactions — для всех Призраков (ghost) и выше
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from web import auth
from web import database as db
from web import discord_api
from web import roles
from web.config import BOT_NAME, CLAN_NAME, BOT_TOKEN

router = APIRouter()

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# ==================== ЛОГИ МОДЕРАЦИИ (для модеров+) ====================

@router.get("/logs", response_class=HTMLResponse)
async def logs(request: Request):
    # === Защита: только модератор / кодер / админ ===
    redirect = roles.redirect_if_not_moderator(request)
    if redirect:
        return redirect

    warnings = db.get_recent_warnings(100)

    user_ids = set()
    for w in warnings:
        user_ids.add(w["user_id"])
        user_ids.add(w["moderator_id"])
    users = await discord_api.fetch_users(list(user_ids), BOT_TOKEN)

    return templates.TemplateResponse(
        request=request,
        name="logs.html",
        context={
            "bot_name": BOT_NAME,
            "clan_name": CLAN_NAME,
            "current_user": auth.get_current_user(request),
            "warnings": warnings,
            "users": users,
        }
    )


# ==================== ТРАНЗАКЦИИ (для призраков+) ====================

@router.get("/transactions", response_class=HTMLResponse)
async def transactions(request: Request):
    # === Защита: только для залогиненных + роль ghost ===
    redirect = roles.redirect_if_not_ghost(request)
    if redirect:
        return redirect

    trans = db.get_recent_transactions(100)

    user_ids = set()
    for t in trans:
        if t.get("from_id"):
            user_ids.add(t["from_id"])
        if t.get("to_id"):
            user_ids.add(t["to_id"])
    users = await discord_api.fetch_users(list(user_ids), BOT_TOKEN)

    return templates.TemplateResponse(
        request=request,
        name="transactions.html",
        context={
            "bot_name": BOT_NAME,
            "clan_name": CLAN_NAME,
            "current_user": auth.get_current_user(request),
            "transactions": trans,
            "users": users,
        }
    )