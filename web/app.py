"""
Nightmare Web Dashboard.
FastAPI-приложение для просмотра статистики клана.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from web import auth
from web import database as db
from web import roles
from web.config import BOT_NAME, CLAN_NAME, WEB_HOST, WEB_PORT
from web.routers import (
    main,
    profiles,
    tops,
    logs,
    auth as auth_router,
    dashboard,
    admin,
)


# ==================== LIFESPAN ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Инициализация при старте, очистка при остановке."""
    # Startup
    db.init_web_tables()
    db.cleanup_sessions()
    db.cleanup_telegram_link_codes()
    print("✅ Таблицы веб-пользователей инициализированы")
    print(f"🌑 {BOT_NAME} • {CLAN_NAME}")
    yield
    # Shutdown
    print("👋 Сервер остановлен")


# ==================== APP ====================

app = FastAPI(
    title=f"{BOT_NAME} Dashboard",
    description=f"Веб-панель клана {CLAN_NAME}",
    version="2.0.0",
    lifespan=lifespan,
)

# ==================== STATIC & TEMPLATES ====================

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# ==================== ГЛОБАЛЬНЫЙ КОНТЕКСТ ШАБЛОНОВ ====================

def _template_context(request: Request, **extra) -> dict:
    """
    Базовый контекст для всех шаблонов.
    Автоматически подставляет:
    - bot_name, clan_name
    - current_user (или None)
    - role_badge, system_badges
    """
    current_user = getattr(request.state, "current_user", None)

    ctx = {
        "bot_name": BOT_NAME,
        "clan_name": CLAN_NAME,
        "current_user": current_user,
        "role_badge": roles.get_role_badge(current_user) if current_user else None,
        "system_badges": roles.get_system_badges(current_user) if current_user else [],
    }
    ctx.update(extra)
    return ctx


# Прокидываем helper в Jinja2, чтобы в шаблонах можно было звать
templates.env.globals["get_role_badge"] = roles.get_role_badge
templates.env.globals["get_system_badges"] = roles.get_system_badges
templates.env.globals["get_all_badges"] = roles.get_all_badges


# ==================== MIDDLEWARE ====================

@app.middleware("http")
async def inject_current_user(request: Request, call_next):
    """Прокидывает current_user в request.state для всех роутов."""
    request.state.current_user = auth.get_current_user(request)
    response = await call_next(request)
    return response


# ==================== ROUTERS ====================

app.include_router(main.router, tags=["main"])
app.include_router(profiles.router, tags=["profiles"])
app.include_router(tops.router, tags=["tops"])
app.include_router(logs.router, tags=["logs"])
app.include_router(auth_router.router, tags=["auth"])
app.include_router(dashboard.router, tags=["dashboard"])
app.include_router(admin.router, tags=["admin"])


# ==================== HEALTH ====================

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "bot": BOT_NAME,
        "clan": CLAN_NAME,
        "version": "2.0.0",
    }


# ==================== ERROR HANDLERS ====================

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return templates.TemplateResponse(
        request=request,
        name="404.html",
        context=_template_context(request),
        status_code=404,
    )


@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    return templates.TemplateResponse(
        request=request,
        name="500.html",
        context=_template_context(request),
        status_code=500,
    )


@app.exception_handler(403)
async def forbidden_handler(request: Request, exc):
    """Страница «доступ запрещён» — для гостей, которые лезут куда не надо."""
    return templates.TemplateResponse(
        request=request,
        name="403.html",
        context=_template_context(request, message=getattr(exc, "detail", None)),
        status_code=403,
    )


@app.exception_handler(401)
async def unauthorized_handler(request: Request, exc):
    """Если не залогинен — редирект на /login."""
    from fastapi.responses import RedirectResponse
    next_url = str(request.url.path)
    return RedirectResponse(f"/login?next={next_url}", status_code=302)


# ==================== RUN ====================

if __name__ == "__main__":
    import uvicorn
    print(f"🌐 Запуск {BOT_NAME} Dashboard на http://{WEB_HOST}:{WEB_PORT}")
    uvicorn.run("web.app:app", host=WEB_HOST, port=WEB_PORT, reload=True)