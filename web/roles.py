"""
Утилиты для проверки ролей пользователей.
Две независимые категории:

1. Общая роль (одна из двух):
   - guest (гость) — зарегистрирован, но не участник клана
   - ghost (призрак) — участник клана, полный доступ к сайту

2. Системные роли (флаги, можно комбинировать):
   - is_moderator — следит за порядком (доступ к логам)
   - is_coder — разработчик (технические разделы)
   - is_admin — полный доступ, управление ролями
"""

from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse

from web import auth


# ============================================================
# КОНСТАНТЫ
# ============================================================

ROLE_GUEST = "guest"
ROLE_GHOST = "ghost"

ROLE_LABELS = {
    "guest": {"name": "Гость", "icon": "👤", "color": "#8a92a6"},
    "ghost": {"name": "Призрак", "icon": "👻", "color": "#7f5af0"},
}

SYSTEM_ROLE_LABELS = {
    "is_moderator": {"name": "Модератор", "icon": "🛡️", "color": "#fbbf24"},
    "is_coder":     {"name": "Coder",     "icon": "💻", "color": "#00e5ff"},
    "is_admin":     {"name": "Admin",     "icon": "👑", "color": "#ff0033"},
}


# ============================================================
# ПРОВЕРКИ РОЛЕЙ
# ============================================================

def is_ghost(user: dict) -> bool:
    """Участник клана (полный доступ к сайту, кроме системных разделов)."""
    if not user:
        return False
    return user.get("role") == ROLE_GHOST


def is_moderator(user: dict) -> bool:
    if not user:
        return False
    return bool(user.get("is_moderator"))


def is_coder(user: dict) -> bool:
    if not user:
        return False
    return bool(user.get("is_coder"))


def is_admin(user: dict) -> bool:
    if not user:
        return False
    return bool(user.get("is_admin"))


# ============================================================
# ФОРМИРОВАНИЕ БЕЙДЖЕЙ
# ============================================================

def get_role_badge(user: dict) -> dict:
    """
    Возвращает dict с информацией о главной роли пользователя.
    """
    if not user:
        return {"name": "Не залогинен", "icon": "🚪", "color": "#4a3d55", "key": "none"}

    role_key = user.get("role") or ROLE_GUEST
    info = ROLE_LABELS.get(role_key, ROLE_LABELS[ROLE_GUEST])
    return {**info, "key": role_key}


def get_system_badges(user: dict) -> list:
    """
    Возвращает список системных ролей пользователя.
    Приоритет: admin > coder > moderator.
    """
    if not user:
        return []

    badges = []
    if user.get("is_admin"):
        info = SYSTEM_ROLE_LABELS["is_admin"]
        badges.append({**info, "key": "is_admin"})
    if user.get("is_coder"):
        info = SYSTEM_ROLE_LABELS["is_coder"]
        badges.append({**info, "key": "is_coder"})
    if user.get("is_moderator"):
        info = SYSTEM_ROLE_LABELS["is_moderator"]
        badges.append({**info, "key": "is_moderator"})

    return badges


def get_all_badges(user: dict) -> list:
    """Главная роль + все системные — для отображения в профиле."""
    badges = [get_role_badge(user)]
    badges.extend(get_system_badges(user))
    return [b for b in badges if b.get("key") != "none"]


# ============================================================
# ЗАЩИТА РОУТОВ
# ============================================================

def require_ghost(request: Request) -> dict:
    """
    Требует авторизации + роль ghost.
    Если гость — редиректит на главную с ошибкой.
    """
    user = auth.get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Требуется вход")
    if not is_ghost(user):
        raise HTTPException(status_code=403, detail="Требуется статус Призрака")
    return user


def require_moderator(request: Request) -> dict:
    """Требует системную роль модератора (или выше)."""
    user = auth.get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Требуется вход")

    if is_admin(user) or is_coder(user) or is_moderator(user):
        return user

    raise HTTPException(status_code=403, detail="Требуется роль Модератора")


def require_coder(request: Request) -> dict:
    """Требует роль кодера (или админа)."""
    user = auth.get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Требуется вход")

    if is_admin(user) or is_coder(user):
        return user

    raise HTTPException(status_code=403, detail="Требуется роль Coder")


def require_admin(request: Request) -> dict:
    """Требует роль админа."""
    user = auth.get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Требуется вход")

    if is_admin(user):
        return user

    raise HTTPException(status_code=403, detail="Требуется роль Admin")


# ============================================================
# РЕДИРЕКТЫ (мягкая защита)
# ============================================================

def redirect_if_not_ghost(request: Request) -> RedirectResponse | None:
    """
    Мягкая проверка — если не ghost, вернуть редирект на главную.
    Использование:
        redirect = redirect_if_not_ghost(request)
        if redirect: return redirect
    """
    user = auth.get_current_user(request)

    if not user:
        return RedirectResponse("/login?next=" + str(request.url.path), status_code=302)

    if not is_ghost(user):
        return RedirectResponse("/?error=need_ghost", status_code=302)

    return None


def redirect_if_not_moderator(request: Request) -> RedirectResponse | None:
    user = auth.get_current_user(request)
    if not user:
        return RedirectResponse("/login?next=" + str(request.url.path), status_code=302)
    if not (is_admin(user) or is_coder(user) or is_moderator(user)):
        return RedirectResponse("/?error=need_moderator", status_code=302)
    return None


def redirect_if_not_coder(request: Request) -> RedirectResponse | None:
    user = auth.get_current_user(request)
    if not user:
        return RedirectResponse("/login?next=" + str(request.url.path), status_code=302)
    if not (is_admin(user) or is_coder(user)):
        return RedirectResponse("/?error=need_coder", status_code=302)
    return None


def redirect_if_not_admin(request: Request) -> RedirectResponse | None:
    user = auth.get_current_user(request)
    if not user:
        return RedirectResponse("/login?next=" + str(request.url.path), status_code=302)
    if not is_admin(user):
        return RedirectResponse("/?error=need_admin", status_code=302)
    return None