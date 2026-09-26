"""
Роуты авторизации: регистрация, вход, выход, привязка Discord/Telegram.
"""

import re
import secrets
import httpx
from datetime import datetime, timezone

from fastapi import APIRouter, Request, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from web import database as db
from web import auth
from web.telegram_auth import verify_telegram_auth
from web.config import (
    BOT_NAME,
    CLAN_NAME,
    DISCORD_CLIENT_ID,
    DISCORD_CLIENT_SECRET,
    DISCORD_REDIRECT_URI,
    TELEGRAM_BOT_USERNAME,
    TELEGRAM_BOT_TOKEN,
)

router = APIRouter()

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _now_iso() -> str:
    """Единый aware-UTC ISO формат времени."""
    return datetime.now(timezone.utc).isoformat()


# ==================== ВАЛИДАЦИЯ ====================

def _validate_username(username: str) -> str:
    if not username or len(username) < 3 or len(username) > 32:
        return "Ник: от 3 до 32 символов"
    if not re.match(r"^[a-zA-Z0-9_]+$", username):
        return "Ник: только латиница, цифры и _"
    return ""


def _validate_password(password: str) -> str:
    if not password or len(password) < 6:
        return "Пароль: минимум 6 символов"
    return ""


def _ctx(request: Request, **extra) -> dict:
    base = {
        "bot_name": BOT_NAME,
        "clan_name": CLAN_NAME,
        "current_user": auth.get_current_user(request),
    }
    base.update(extra)
    return base


# ==================== РЕГИСТРАЦИЯ ====================

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    if auth.get_current_user(request):
        return RedirectResponse("/dashboard", status_code=302)

    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context=_ctx(request),
    )


@router.post("/register")
async def register_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    password2: str = Form(...),
    display_name: str = Form(...),
    email: str = Form(""),
):
    form = {
        "username": username,
        "display_name": display_name,
        "email": email,
    }

    err = _validate_username(username) or _validate_password(password)
    if err:
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context=_ctx(request, error=err, form=form),
            status_code=400,
        )

    if password != password2:
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context=_ctx(request, error="Пароли не совпадают", form=form),
            status_code=400,
        )

    if db.get_web_user_by_username(username):
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context=_ctx(request, error="Ник уже занят", form=form),
            status_code=400,
        )

    pwd_hash = auth.hash_password(password)
    user_id = db.create_web_user(
        username=username,
        password_hash=pwd_hash,
        display_name=display_name,
        email=email or None,
        role="guest",
    )

    if not user_id:
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context=_ctx(request, error="Не удалось создать аккаунт", form=form),
            status_code=500,
        )

    db.update_web_user(user_id, last_login=_now_iso())

    return auth.login_response_redirect(user_id, "/dashboard")


# ==================== ВХОД ====================

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if auth.get_current_user(request):
        return RedirectResponse("/dashboard", status_code=302)

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context=_ctx(request),
    )


@router.post("/login")
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    user = db.get_web_user_by_username(username)
    if not user or not auth.verify_password(password, user["password_hash"]):
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context=_ctx(request, error="Неверный ник или пароль"),
            status_code=401,
        )

    db.update_web_user(user["id"], last_login=_now_iso())

    next_url = request.query_params.get("next") or "/dashboard"
    return auth.login_response_redirect(user["id"], next_url)


# ==================== ВЫХОД ====================

@router.get("/logout")
async def logout(request: Request):
    return auth.logout_response_redirect("/")


# ==================== DISCORD OAUTH ====================

@router.get("/auth/discord")
async def auth_discord(request: Request, mode: str = "login"):
    """
    Редирект на Discord OAuth2.
    mode=login — войти через Discord,
    mode=link — привязать Discord к текущему аккаунту.
    """
    if not DISCORD_CLIENT_ID:
        raise HTTPException(500, "DISCORD_CLIENT_ID не настроен в .env")

    state = f"{mode}:{secrets.token_urlsafe(16)}"

    url = (
        "https://discord.com/oauth2/authorize"
        f"?client_id={DISCORD_CLIENT_ID}"
        f"&redirect_uri={DISCORD_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=identify"
        f"&state={state}"
    )

    response = RedirectResponse(url, status_code=302)
    response.set_cookie(
        "oauth_state",
        state,
        max_age=600,
        httponly=True,
        samesite="lax",
    )
    return response


@router.get("/auth/callback")
async def auth_callback(
    request: Request,
    code: str = None,
    state: str = None,
    error: str = None,
):
    """Обработка callback от Discord OAuth2."""

    if error or not code:
        return RedirectResponse("/login?error=discord_denied", status_code=302)

    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.post(
            "https://discord.com/api/oauth2/token",
            data={
                "client_id": DISCORD_CLIENT_ID,
                "client_secret": DISCORD_CLIENT_SECRET,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": DISCORD_REDIRECT_URI,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if r.status_code != 200:
            return RedirectResponse("/login?error=discord_token", status_code=302)
        token_data = r.json()

        r2 = await client.get(
            "https://discord.com/api/users/@me",
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )
        if r2.status_code != 200:
            return RedirectResponse("/login?error=discord_user", status_code=302)
        duser = r2.json()

    discord_id = int(duser["id"])
    discord_username = duser.get("username", "")

    avatar_hash = duser.get("avatar")
    if avatar_hash:
        ext = "gif" if avatar_hash.startswith("a_") else "png"
        discord_avatar = (
            f"https://cdn.discordapp.com/avatars/"
            f"{discord_id}/{avatar_hash}.{ext}?size=128"
        )
    else:
        discord_avatar = None

    mode = (state or "").split(":")[0] if state else "login"

    # === Привязка к текущему аккаунту ===
    if mode == "link":
        current = auth.get_current_user(request)
        if not current:
            return RedirectResponse("/login", status_code=302)

        existing = db.get_web_user_by_discord(discord_id)
        if existing and existing["id"] != current["id"]:
            return RedirectResponse("/settings?error=discord_taken", status_code=302)

        db.update_web_user(
            current["id"],
            discord_id=discord_id,
            discord_username=discord_username,
            discord_avatar=discord_avatar,
            guild_user_id=discord_id,
        )
        return RedirectResponse("/settings?linked=discord", status_code=302)

    # === Обычный вход / регистрация через Discord ===
    user = db.get_web_user_by_discord(discord_id)

    if not user:
        auto_username = f"dc_{discord_id}"
        user_id = db.create_web_user(
            username=auto_username,
            password_hash=auth.hash_password(secrets.token_urlsafe(24)),
            display_name=duser.get("global_name") or discord_username,
            role="guest",
        )
        db.update_web_user(
            user_id,
            discord_id=discord_id,
            discord_username=discord_username,
            discord_avatar=discord_avatar,
            guild_user_id=discord_id,
        )
        user = db.get_web_user_by_id(user_id)

    db.update_web_user(user["id"], last_login=_now_iso())
    return auth.login_response_redirect(user["id"], "/dashboard")


# ==================== TELEGRAM LOGIN WIDGET ====================

@router.get("/auth/telegram")
async def auth_telegram(request: Request):
    """
    Страница с Telegram Login Widget.
    Работает как для входа, так и для привязки (если current_user есть).
    """
    return templates.TemplateResponse(
        request=request,
        name="telegram_link.html",
        context=_ctx(
            request,
            telegram_bot_username=TELEGRAM_BOT_USERNAME,
        ),
    )


@router.get("/auth/telegram/callback")
async def telegram_callback(
    request: Request,
    id: int = Query(None),
    first_name: str = Query(None),
    last_name: str = Query(None),
    username: str = Query(None),
    photo_url: str = Query(None),
    auth_date: int = Query(None),
    hash: str = Query(None),
):
    """
    Callback от Telegram Login Widget.
    Telegram редиректит сюда с данными пользователя + hash.
    """
    if not TELEGRAM_BOT_TOKEN:
        return RedirectResponse("/login?error=telegram_no_token", status_code=302)

    tg_data = {
        "id": id,
        "first_name": first_name,
        "last_name": last_name,
        "username": username,
        "photo_url": photo_url,
        "auth_date": auth_date,
        "hash": hash,
    }

    if not verify_telegram_auth(tg_data, TELEGRAM_BOT_TOKEN):
        return RedirectResponse("/login?error=telegram_invalid", status_code=302)

    parts = [p for p in (first_name, last_name) if p]
    display_name = " ".join(parts).strip() or username or f"TG {id}"

    existing = db.get_web_user_by_telegram(id)
    current = auth.get_current_user(request)

    # === Привязка к текущему аккаунту ===
    if current:
        if existing and existing["id"] != current["id"]:
            return RedirectResponse("/settings?error=telegram_taken", status_code=302)

        db.update_web_user(
            current["id"],
            telegram_id=id,
            telegram_username=username,
        )
        return RedirectResponse("/settings?linked=telegram", status_code=302)

    # === Обычный вход / регистрация через Telegram ===
    if not existing:
        auto_username = f"tg_{id}"
        user_id = db.create_web_user(
            username=auto_username,
            password_hash=auth.hash_password(secrets.token_urlsafe(24)),
            display_name=display_name,
            role="guest",
        )
        db.update_web_user(
            user_id,
            telegram_id=id,
            telegram_username=username,
        )
        existing = db.get_web_user_by_id(user_id)

    db.update_web_user(existing["id"], last_login=_now_iso())
    return auth.login_response_redirect(existing["id"], "/dashboard")


# ==================== TELEGRAM BOT LINK ====================

@router.get("/auth/telegram/bot", response_class=HTMLResponse)
async def auth_telegram_bot(request: Request):
    """
    Страница привязки через Telegram-бота.
    Генерирует одноразовый код и показывает ссылку t.me/...?start=<код>.
    """
    current = auth.get_current_user(request)
    if not current:
        return RedirectResponse("/login?next=/auth/telegram/bot", status_code=302)

    # Если Telegram уже привязан — покажем страницу с текущим статусом
    if current.get("telegram_id"):
        return RedirectResponse("/settings?linked=telegram", status_code=302)

    code = db.create_telegram_link_code(current["id"])
    bot_username = (TELEGRAM_BOT_USERNAME or "").lstrip("@")
    bot_link = f"https://t.me/{bot_username}?start={code}" if bot_username else ""

    return templates.TemplateResponse(
        request=request,
        name="telegram_bot_link.html",
        context=_ctx(
            request,
            bot_link=bot_link,
            code=code,
            bot_username=bot_username,
        ),
    )