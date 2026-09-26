"""
Авторизация: хеширование паролей, сессии, проверки.
"""

import hashlib
import secrets
from typing import Optional

from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse

from web import database as db


# ==================== КОНСТАНТЫ ====================

SESSION_COOKIE = "nightmare_session"
SESSION_HOURS = 72


# ==================== ПАРОЛИ ====================

def hash_password(password: str) -> str:
    """
    Хеширует пароль через PBKDF2-HMAC-SHA256.
    Формат: pbkdf2$<salt_hex>$<hash_hex>
    """
    salt = secrets.token_bytes(16)
    pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return f"pbkdf2${salt.hex()}${pwd_hash.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Проверяет пароль по сохранённому хешу."""
    try:
        algo, salt_hex, hash_hex = stored.split("$")
        if algo != "pbkdf2":
            return False
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
        pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
        return secrets.compare_digest(pwd_hash, expected)
    except Exception:
        return False


# ==================== СЕССИИ ====================

def create_user_session(user_id: int) -> str:
    """Создаёт сессию, возвращает токен."""
    token = secrets.token_urlsafe(32)
    db.create_session(token, user_id, hours=SESSION_HOURS)
    return token


def get_current_user(request: Request) -> Optional[dict]:
    """Возвращает dict пользователя или None."""
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None

    session = db.get_session(token)
    if not session:
        return None

    return db.get_web_user_by_id(session["user_id"])


def login_response_redirect(
    user_id: int,
    redirect_to: str = "/dashboard",
) -> RedirectResponse:
    """Создаёт сессию и возвращает редирект с cookie."""
    token = create_user_session(user_id)
    response = RedirectResponse(url=redirect_to, status_code=302)
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_HOURS * 3600,
        httponly=True,
        samesite="lax",
    )
    return response


def logout_response_redirect(redirect_to: str = "/") -> RedirectResponse:
    """Удаляет cookie и редиректит."""
    response = RedirectResponse(url=redirect_to, status_code=302)
    response.delete_cookie(SESSION_COOKIE)
    return response


# ==================== ЗАЩИТА РОУТОВ ====================

def require_login(request: Request) -> dict:
    """
    Проверка на вход внутри роута.
    Если не залогинен — HTTPException(401).
    """
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Требуется вход")
    return user


def require_admin(request: Request) -> dict:
    """
    Проверка на админа (старая функция — оставлена для совместимости).
    Рекомендуется использовать web.roles.require_admin().
    """
    user = require_login(request)
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Только для админов")
    return user