"""
Личный кабинет, магазин, настройки.
Магазин работает через shop.json.
Доступ: только для Призраков (ghost) и выше.
"""

import json
from pathlib import Path

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from web import database as db
from web import auth
from web import roles
from web.config import BOT_NAME, CLAN_NAME, CURRENCY_EMOJI, GUILD_ID

router = APIRouter()

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Путь к JSON магазина
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
SHOP_JSON = ROOT_DIR / "data" / "shop.json"


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ
# ============================================================

def _ctx(request: Request, user: dict, **extra) -> dict:
    """Общий контекст для шаблонов кабинета."""
    base = {
        "bot_name": BOT_NAME,
        "clan_name": CLAN_NAME,
        "currency_emoji": CURRENCY_EMOJI,
        "user": user,
        "current_user": user,
    }
    base.update(extra)
    return base


def _require_user(request: Request):
    """Возвращает user или RedirectResponse, если не залогинен."""
    user = auth.get_current_user(request)
    if not user:
        return None, RedirectResponse("/login", status_code=302)
    return user, None


def _require_ghost(request: Request):
    """
    Возвращает user или RedirectResponse:
    - если не залогинен → /login
    - если гость → /?error=need_ghost
    """
    redirect = roles.redirect_if_not_ghost(request)
    if redirect:
        return None, redirect
    return auth.get_current_user(request), None


def load_shop_items():
    """Загружает предметы из shop.json. Возвращает список."""
    if not SHOP_JSON.exists():
        return []

    try:
        with open(SHOP_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        items = data.get("items", [])
        # Оставляем только доступные (не скрытые)
        return [i for i in items if not i.get("hidden", False)]
    except (json.JSONDecodeError, IOError) as e:
        print(f"⚠️ Ошибка чтения {SHOP_JSON}: {e}")
        return []


def find_shop_item(item_id: str):
    """Находит товар по ID."""
    items = load_shop_items()
    return next((i for i in items if i.get("id") == item_id), None)


# ============================================================
# DASHBOARD
# ============================================================

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    user, redirect = _require_ghost(request)
    if redirect:
        return redirect

    bot_stats = None
    user_warnings = []
    user_transactions = []
    user_achievements = []
    game_stats = {"total": 0, "wins": 0, "total_profit": 0}

    if user.get("guild_user_id"):
        bot_stats = db.get_user(user["guild_user_id"])
        if bot_stats:
            user_warnings = db.get_user_warnings(user["guild_user_id"], 10)
            user_transactions = db.get_user_transactions(user["guild_user_id"], 10)
            user_achievements = db.get_user_achievements(user["guild_user_id"])
            game_stats = db.get_user_games_stats(user["guild_user_id"])

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context=_ctx(
            request, user,
            bot_stats=bot_stats,
            warnings=user_warnings,
            transactions=user_transactions,
            achievements=user_achievements,
            game_stats=game_stats,
        )
    )


# ============================================================
# SETTINGS
# ============================================================

@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    user, redirect = _require_ghost(request)
    if redirect:
        return redirect

    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context=_ctx(request, user)
    )


@router.post("/settings/profile")
async def settings_profile(
    request: Request,
    display_name: str = Form(...),
    email: str = Form(""),
):
    user, redirect = _require_ghost(request)
    if redirect:
        return redirect

    display_name = display_name.strip()
    if not display_name or len(display_name) > 64:
        return RedirectResponse("/settings?error=bad_name", status_code=302)

    db.update_web_user(
        user["id"],
        display_name=display_name,
        email=email.strip() or None,
    )
    return RedirectResponse("/settings?saved=profile", status_code=302)


@router.post("/settings/password")
async def settings_password(
    request: Request,
    old_password: str = Form(...),
    new_password: str = Form(...),
    new_password2: str = Form(...),
):
    user, redirect = _require_ghost(request)
    if redirect:
        return redirect

    if not auth.verify_password(old_password, user["password_hash"]):
        return RedirectResponse("/settings?error=wrong_old", status_code=302)
    if new_password != new_password2:
        return RedirectResponse("/settings?error=mismatch", status_code=302)
    if len(new_password) < 6:
        return RedirectResponse("/settings?error=short", status_code=302)

    db.update_web_user(
        user["id"],
        password_hash=auth.hash_password(new_password),
    )
    return RedirectResponse("/settings?saved=password", status_code=302)


@router.post("/settings/unlink")
async def settings_unlink(request: Request, service: str = Form(...)):
    user, redirect = _require_ghost(request)
    if redirect:
        return redirect

    if service == "discord":
        db.update_web_user(
            user["id"],
            discord_id=None,
            discord_username=None,
            discord_avatar=None,
            guild_user_id=None,
        )
    elif service == "telegram":
        db.update_web_user(
            user["id"],
            telegram_id=None,
            telegram_username=None,
        )
    else:
        return RedirectResponse("/settings?error=unknown_service", status_code=302)

    return RedirectResponse("/settings?unlinked=" + service, status_code=302)


@router.post("/settings/delete")
async def settings_delete(request: Request):
    """Удаляет аккаунт и все связанные данные."""
    user, redirect = _require_ghost(request)
    if redirect:
        return redirect

    db.delete_web_user(user["id"])
    return auth.logout_response_redirect("/")


# ============================================================
# SHOP
# ============================================================

@router.get("/shop", response_class=HTMLResponse)
async def shop_page(request: Request):
    user, redirect = _require_ghost(request)
    if redirect:
        return redirect

    items = load_shop_items()

    balance = 0
    my_items = []
    if user.get("guild_user_id"):
        balance = db.get_balance(GUILD_ID, user["guild_user_id"], 0)
        my_items = db.get_user_items(GUILD_ID, user["guild_user_id"])

    return templates.TemplateResponse(
        request=request,
        name="shop.html",
        context=_ctx(
            request, user,
            items=items,
            balance=balance,
            my_items=my_items,
        )
    )


# ============================================================
# SHOP — ПОКУПКА
# ============================================================

@router.post("/shop/buy/{item_id}")
async def shop_buy(request: Request, item_id: str):
    """Покупка предмета из shop.json."""
    user, redirect = _require_ghost(request)
    if redirect:
        return redirect

    # Нужен Discord для покупок (привязка к игровому аккаунту)
    if not user.get("guild_user_id"):
        return RedirectResponse("/shop?error=no_discord", status_code=302)

    # Находим товар
    item = find_shop_item(item_id)
    if not item:
        return RedirectResponse("/shop?error=not_found", status_code=302)

    # Проверка склада
    stock = item.get("stock", -1)
    if stock == 0:
        return RedirectResponse("/shop?error=no_stock", status_code=302)

    # Проверка баланса
    price = int(item.get("price", 0))
    balance = db.get_balance(GUILD_ID, user["guild_user_id"], 0)
    if balance < price:
        return RedirectResponse("/shop?error=not_enough", status_code=302)

    # Списываем монеты
    db.remove_balance(GUILD_ID, user["guild_user_id"], price, 0)

    # Записываем покупку
    db.buy_item(
        guild_id=GUILD_ID,
        user_id=user["guild_user_id"],
        item_id=item.get("id"),
        item_name=item.get("name"),
        price=price,
    )

    # Логируем транзакцию
    db.add_transaction(
        guild_id=GUILD_ID,
        from_id=user["guild_user_id"],
        to_id=None,
        amount=price,
        type_="shop",
        reason=item.get("name"),
    )

    # Возвращаемся в магазин с сообщением
    return RedirectResponse(
        f"/shop?bought={item.get('name')}",
        status_code=302,
    )