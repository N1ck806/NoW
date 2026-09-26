"""
Админ-панель Nightmare.
Одна страница /admin с вкладками:
  - dashboard  — сводка
  - users      — аккаунты сайта (web_users)
  - economy    — игровая экономика (users)
  - shop       — магазин (shop_items)
  - quests     — квесты (data/quests.json)
  - telegram   — Telegram-привязки
  - logs       — предупреждения / транзакции
  - games      — история игр

Доступ: только is_admin или is_coder.
"""

import json
import shutil
import secrets
from pathlib import Path

from fastapi import APIRouter, Request, Form, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from web import database as db
from web import auth
from web.config import BOT_NAME, CLAN_NAME, CURRENCY_EMOJI, GUILD_ID

router = APIRouter(prefix="/admin", tags=["admin"])

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
QUESTS_JSON = ROOT_DIR / "data" / "quests.json"

# Папка для загрузки картинок товаров
UPLOADS_DIR = Path(__file__).resolve().parent.parent / "static" / "uploads" / "shop"

# Допустимые MIME-типы и расширения
ALLOWED_IMAGE_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
MAX_IMAGE_SIZE = 2 * 1024 * 1024  # 2 МБ


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ
# ============================================================

def _ctx(request: Request, **extra) -> dict:
    """Общий контекст для шаблонов админки."""
    user = auth.get_current_user(request)
    base = {
        "bot_name": BOT_NAME,
        "clan_name": CLAN_NAME,
        "currency_emoji": CURRENCY_EMOJI,
        "current_user": user,
        "active_tab": extra.pop("active_tab", "dashboard"),
    }
    base.update(extra)
    return base


def _require_admin_or_coder(request: Request):
    """
    Возвращает (user, redirect). Если доступ разрешён — redirect=None.
    Доступ: is_admin ИЛИ is_coder.
    """
    user = auth.get_current_user(request)
    if not user:
        return None, RedirectResponse(f"/login?next={request.url.path}", status_code=302)
    if not (user.get("is_admin") or user.get("is_coder")):
        return None, RedirectResponse("/?error=need_admin", status_code=302)
    return user, None


def _load_quests() -> list:
    """Читает data/quests.json. Возвращает список квестов."""
    if not QUESTS_JSON.exists():
        return []
    try:
        with open(QUESTS_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data.get("quests", [])
        if isinstance(data, list):
            return data
        return []
    except (json.JSONDecodeError, IOError):
        return []


def _save_quests(quests: list):
    """Пишет data/quests.json."""
    QUESTS_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(QUESTS_JSON, "w", encoding="utf-8") as f:
        json.dump({"quests": quests}, f, ensure_ascii=False, indent=2)


async def _save_uploaded_image(image: UploadFile, item_id: int) -> str | None:
    """
    Сохраняет загруженную картинку в UPLOADS_DIR.
    Возвращает публичный URL (/static/uploads/shop/...) или None при ошибке.
    """
    if not image or not image.filename:
        return None

    if image.content_type not in ALLOWED_IMAGE_TYPES:
        return None

    # Читаем содержимое и проверяем размер
    contents = await image.read()
    if len(contents) > MAX_IMAGE_SIZE:
        return None

    # Уникальное имя файла, чтобы не залипало кеширование в браузере
    ext = ALLOWED_IMAGE_TYPES[image.content_type]
    token = secrets.token_hex(4)
    filename = f"{item_id}_{token}{ext}"

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    file_path = UPLOADS_DIR / filename

    with open(file_path, "wb") as f:
        f.write(contents)

    return f"/static/uploads/shop/{filename}"


def _delete_uploaded_image(image_url: str | None):
    """Удаляет файл картинки, если он лежит в UPLOADS_DIR."""
    if not image_url:
        return
    if not image_url.startswith("/static/uploads/shop/"):
        return

    filename = image_url.split("/")[-1]
    file_path = UPLOADS_DIR / filename

    try:
        if file_path.exists():
            file_path.unlink()
    except OSError:
        pass


# ============================================================
# ГЛАВНАЯ СТРАНИЦА АДМИНКИ
# ============================================================

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def admin_root(request: Request):
    """Редирект на вкладку dashboard."""
    user, redirect = _require_admin_or_coder(request)
    if redirect:
        return redirect
    return RedirectResponse("/admin/dashboard", status_code=302)


@router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """Сводная статистика."""
    user, redirect = _require_admin_or_coder(request)
    if redirect:
        return redirect

    overview = db.get_overview()
    games = db.get_game_overview()

    total_web_users = db.count_web_users()
    all_web_users = db.get_all_web_users(limit=1000)
    telegram_linked = sum(1 for u in all_web_users if u.get("telegram_id"))
    discord_linked = sum(1 for u in all_web_users if u.get("discord_id"))

    shop_items = db.admin_get_shop_items(GUILD_ID)

    return templates.TemplateResponse(
        request=request,
        name="admin/dashboard.html",
        context=_ctx(
            request,
            active_tab="dashboard",
            overview=overview,
            games=games,
            total_web_users=total_web_users,
            telegram_linked=telegram_linked,
            discord_linked=discord_linked,
            shop_count=len(shop_items),
        ),
    )


# ============================================================
# ПОЛЬЗОВАТЕЛИ САЙТА (web_users)
# ============================================================

@router.get("/users", response_class=HTMLResponse)
async def admin_users(request: Request, page: int = 1):
    user, redirect = _require_admin_or_coder(request)
    if redirect:
        return redirect

    per_page = 50
    offset = (page - 1) * per_page

    users_list = db.get_all_web_users(limit=per_page, offset=offset)
    total = db.count_web_users()
    total_pages = max(1, (total + per_page - 1) // per_page)

    return templates.TemplateResponse(
        request=request,
        name="admin/users.html",
        context=_ctx(
            request,
            active_tab="users",
            users=users_list,
            page=page,
            total_pages=total_pages,
            total=total,
        ),
    )


@router.get("/users/{user_id}", response_class=HTMLResponse)
async def admin_user_detail(request: Request, user_id: int):
    user, redirect = _require_admin_or_coder(request)
    if redirect:
        return redirect

    target = db.get_web_user_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    return templates.TemplateResponse(
        request=request,
        name="admin/user_detail.html",
        context=_ctx(
            request,
            active_tab="users",
            target=target,
        ),
    )


@router.post("/users/{user_id}/role")
async def admin_user_set_role(
    request: Request,
    user_id: int,
    role: str = Form(...),
):
    user, redirect = _require_admin_or_coder(request)
    if redirect:
        return redirect

    if not user.get("is_admin"):
        raise HTTPException(403, "Только админ может менять роль")

    if role in ("guest", "ghost"):
        db.set_user_role(user_id, role)
    return RedirectResponse(f"/admin/users/{user_id}?saved=role", status_code=302)


@router.post("/users/{user_id}/system-role")
async def admin_user_toggle_system(
    request: Request,
    user_id: int,
    role: str = Form(...),
    value: str = Form("0"),
):
    user, redirect = _require_admin_or_coder(request)
    if redirect:
        return redirect

    if not user.get("is_admin"):
        raise HTTPException(403, "Только админ может менять системные роли")

    if role in ("is_moderator", "is_coder", "is_admin"):
        db.toggle_system_role(user_id, role, value == "1")
    return RedirectResponse(f"/admin/users/{user_id}?saved=sys", status_code=302)


@router.post("/users/{user_id}/delete")
async def admin_user_delete(request: Request, user_id: int):
    user, redirect = _require_admin_or_coder(request)
    if redirect:
        return redirect

    if not user.get("is_admin"):
        raise HTTPException(403, "Только админ может удалять")

    if user["id"] == user_id:
        return RedirectResponse("/admin/users?error=self_delete", status_code=302)

    db.delete_web_user(user_id)
    return RedirectResponse("/admin/users?deleted=1", status_code=302)


# ============================================================
# ИГРОВАЯ ЭКОНОМИКА (users)
# ============================================================

@router.get("/economy", response_class=HTMLResponse)
async def admin_economy(request: Request, page: int = 1, q: str = ""):
    user, redirect = _require_admin_or_coder(request)
    if redirect:
        return redirect

    per_page = 50
    offset = (page - 1) * per_page

    players = db.admin_get_users(GUILD_ID, limit=per_page, offset=offset, search=q or None)
    total = db.admin_count_users(GUILD_ID, search=q or None)
    total_pages = max(1, (total + per_page - 1) // per_page)

    return templates.TemplateResponse(
        request=request,
        name="admin/economy.html",
        context=_ctx(
            request,
            active_tab="economy",
            players=players,
            page=page,
            total_pages=total_pages,
            total=total,
            query=q,
        ),
    )


@router.post("/economy/{user_id}/balance")
async def admin_economy_set_balance(
    request: Request,
    user_id: int,
    amount: int = Form(...),
    action: str = Form(...),  # set | add | remove
):
    user, redirect = _require_admin_or_coder(request)
    if redirect:
        return redirect

    if amount < 0:
        return RedirectResponse("/admin/economy?error=negative", status_code=302)

    if action == "set":
        db.admin_set_balance(GUILD_ID, user_id, amount)
    elif action == "add":
        db.admin_add_balance(GUILD_ID, user_id, amount)
    elif action == "remove":
        db.admin_remove_balance(GUILD_ID, user_id, amount)
    else:
        return RedirectResponse("/admin/economy?error=bad_action", status_code=302)

    return RedirectResponse(f"/admin/economy?ok=balance&u={user_id}", status_code=302)


@router.post("/economy/{user_id}/reset")
async def admin_economy_reset(
    request: Request,
    user_id: int,
    field: str = Form(...),  # level | reputation | warnings | voice | messages
):
    user, redirect = _require_admin_or_coder(request)
    if redirect:
        return redirect

    db.admin_reset_field(GUILD_ID, user_id, field)
    return RedirectResponse(f"/admin/economy?ok=reset&u={user_id}", status_code=302)


# ============================================================
# МАГАЗИН (shop_items)
# ============================================================

@router.get("/shop", response_class=HTMLResponse)
async def admin_shop(request: Request):
    user, redirect = _require_admin_or_coder(request)
    if redirect:
        return redirect

    items = db.admin_get_shop_items(GUILD_ID)

    return templates.TemplateResponse(
        request=request,
        name="admin/shop.html",
        context=_ctx(
            request,
            active_tab="shop",
            items=items,
        ),
    )


@router.post("/shop/add")
async def admin_shop_add(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    price: int = Form(...),
    role_id: str = Form(""),
    stock: int = Form(-1),
    icon: str = Form(""),
    image: UploadFile = File(None),
):
    user, redirect = _require_admin_or_coder(request)
    if redirect:
        return redirect

    if price <= 0:
        return RedirectResponse("/admin/shop?error=bad_price", status_code=302)

    role_id_int = int(role_id) if role_id.strip().isdigit() else None

    # Сначала создаём товар — получаем его ID
    item_id = db.admin_add_shop_item(
        GUILD_ID,
        name=name.strip(),
        description=description.strip() or None,
        price=price,
        role_id=role_id_int,
        stock=stock,
        icon=icon.strip() or None,
    )

    if not item_id:
        return RedirectResponse("/admin/shop?error=dup_name", status_code=302)

    # Затем, если есть картинка — сохраняем и обновляем товар
    if image and image.filename:
        image_url = await _save_uploaded_image(image, item_id)
        if image_url:
            db.admin_update_shop_item(
                GUILD_ID,
                item_id,
                name=name.strip(),
                description=description.strip() or None,
                price=price,
                stock=stock,
                role_id=role_id_int,
                icon=icon.strip() or None,
                image_url=image_url,
            )

    return RedirectResponse("/admin/shop?ok=added", status_code=302)


@router.post("/shop/{item_id}/update")
async def admin_shop_update(
    request: Request,
    item_id: int,
    name: str = Form(...),
    description: str = Form(""),
    price: int = Form(...),
    stock: int = Form(...),
    role_id: str = Form(""),
    icon: str = Form(""),
    image: UploadFile = File(None),
    remove_image: str = Form(""),
):
    user, redirect = _require_admin_or_coder(request)
    if redirect:
        return redirect

    role_id_int = int(role_id) if role_id.strip().isdigit() else None

    # Загружаем текущий товар, чтобы знать текущий image_url
    current = db.admin_get_shop_item(GUILD_ID, item_id)
    if not current:
        return RedirectResponse("/admin/shop?error=not_found", status_code=302)

    image_url = current.get("image_url")

    # Если попросили удалить — сносим файл и обнуляем
    if remove_image == "1":
        _delete_uploaded_image(image_url)
        image_url = None

    # Если загрузили новый файл — сохраняем
    if image and image.filename:
        new_url = await _save_uploaded_image(image, item_id)
        if new_url:
            # Старый файл удаляем
            _delete_uploaded_image(image_url)
            image_url = new_url

    db.admin_update_shop_item(
        GUILD_ID,
        item_id,
        name=name.strip(),
        description=description.strip() or None,
        price=price,
        stock=stock,
        role_id=role_id_int,
        icon=icon.strip() or None,
        image_url=image_url,
    )

    return RedirectResponse("/admin/shop?ok=updated", status_code=302)


@router.post("/shop/{item_id}/delete")
async def admin_shop_delete(request: Request, item_id: int):
    user, redirect = _require_admin_or_coder(request)
    if redirect:
        return redirect

    # Удаляем картинку с диска
    current = db.admin_get_shop_item(GUILD_ID, item_id)
    if current:
        _delete_uploaded_image(current.get("image_url"))

    db.admin_delete_shop_item(GUILD_ID, item_id)
    return RedirectResponse("/admin/shop?ok=deleted", status_code=302)


# ============================================================
# КВЕСТЫ (data/quests.json)
# ============================================================

@router.get("/quests", response_class=HTMLResponse)
async def admin_quests(request: Request):
    user, redirect = _require_admin_or_coder(request)
    if redirect:
        return redirect

    quests = _load_quests()

    return templates.TemplateResponse(
        request=request,
        name="admin/quests.html",
        context=_ctx(
            request,
            active_tab="quests",
            quests=quests,
        ),
    )


@router.post("/quests/add")
async def admin_quests_add(
    request: Request,
    id: str = Form(...),
    name: str = Form(...),
    description: str = Form(""),
    type_: str = Form(..., alias="type"),
    target: int = Form(...),
    reward: int = Form(...),
):
    user, redirect = _require_admin_or_coder(request)
    if redirect:
        return redirect

    quests = _load_quests()
    if any(q.get("id") == id for q in quests):
        return RedirectResponse("/admin/quests?error=dup_id", status_code=302)

    quests.append({
        "id": id.strip(),
        "name": name.strip(),
        "description": description.strip(),
        "type": type_.strip(),
        "target": target,
        "reward": reward,
    })
    _save_quests(quests)
    return RedirectResponse("/admin/quests?ok=added", status_code=302)


@router.post("/quests/{quest_id}/update")
async def admin_quests_update(
    request: Request,
    quest_id: str,
    name: str = Form(...),
    description: str = Form(""),
    type_: str = Form(..., alias="type"),
    target: int = Form(...),
    reward: int = Form(...),
):
    user, redirect = _require_admin_or_coder(request)
    if redirect:
        return redirect

    quests = _load_quests()
    for q in quests:
        if q.get("id") == quest_id:
            q["name"] = name.strip()
            q["description"] = description.strip()
            q["type"] = type_.strip()
            q["target"] = target
            q["reward"] = reward
            break
    _save_quests(quests)
    return RedirectResponse("/admin/quests?ok=updated", status_code=302)


@router.post("/quests/{quest_id}/delete")
async def admin_quests_delete(request: Request, quest_id: str):
    user, redirect = _require_admin_or_coder(request)
    if redirect:
        return redirect

    quests = [q for q in _load_quests() if q.get("id") != quest_id]
    _save_quests(quests)
    return RedirectResponse("/admin/quests?ok=deleted", status_code=302)


# ============================================================
# TELEGRAM-ПРИВЯЗКИ
# ============================================================

@router.get("/telegram", response_class=HTMLResponse)
async def admin_telegram(request: Request):
    user, redirect = _require_admin_or_coder(request)
    if redirect:
        return redirect

    linked = db.admin_get_telegram_links()

    return templates.TemplateResponse(
        request=request,
        name="admin/telegram.html",
        context=_ctx(
            request,
            active_tab="telegram",
            linked=linked,
        ),
    )


@router.post("/telegram/{web_user_id}/unlink")
async def admin_telegram_unlink(request: Request, web_user_id: int):
    user, redirect = _require_admin_or_coder(request)
    if redirect:
        return redirect

    db.update_web_user(web_user_id, telegram_id=None, telegram_username=None)
    return RedirectResponse("/admin/telegram?ok=unlinked", status_code=302)


# ============================================================
# ЛОГИ (предупреждения + транзакции)
# ============================================================

@router.get("/logs", response_class=HTMLResponse)
async def admin_logs(request: Request, tab: str = "warnings"):
    user, redirect = _require_admin_or_coder(request)
    if redirect:
        return redirect

    warnings = db.get_recent_warnings(100)
    transactions = db.get_recent_transactions(100)

    return templates.TemplateResponse(
        request=request,
        name="admin/logs.html",
        context=_ctx(
            request,
            active_tab="logs",
            logs_tab=tab,
            warnings=warnings,
            transactions=transactions,
        ),
    )


@router.post("/logs/warnings/{warning_id}/delete")
async def admin_warning_delete(request: Request, warning_id: int):
    """Удалить предупреждение по ID."""
    user, redirect = _require_admin_or_coder(request)
    if redirect:
        return redirect

    db.admin_delete_warning(warning_id)
    return RedirectResponse("/admin/logs?tab=warnings&ok=deleted", status_code=302)


# ============================================================
# ИГРЫ (game_history)
# ============================================================

@router.get("/games", response_class=HTMLResponse)
async def admin_games(request: Request, page: int = 1):
    user, redirect = _require_admin_or_coder(request)
    if redirect:
        return redirect

    per_page = 100
    offset = (page - 1) * per_page

    games = db.admin_get_game_history(GUILD_ID, limit=per_page, offset=offset)
    total = db.admin_count_game_history(GUILD_ID)
    total_pages = max(1, (total + per_page - 1) // per_page)

    return templates.TemplateResponse(
        request=request,
        name="admin/games.html",
        context=_ctx(
            request,
            active_tab="games",
            games=games,
            page=page,
            total_pages=total_pages,
            total=total,
        ),
    )