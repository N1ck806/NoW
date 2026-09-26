"""
Работа с БД для веб-дашборда.
Использует ту же SQLite, что и бот.

ВАЖНО: единый источник правды для Telegram-привязки — таблица web_users.
Сайт создаёт одноразовые коды в telegram_link_codes с web_user_id,
бот их потребляет и пишет telegram_id в web_users.

Магазин читается из БД (таблица shop_items) — единый источник
и для Discord-бота, и для сайта.
"""

import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

from web.config import DB_PATH, GUILD_ID


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _now_iso() -> str:
    """Единый формат времени — aware UTC ISO."""
    return datetime.now(timezone.utc).isoformat()


# ============================================================
# ОБЩАЯ СТАТИСТИКА
# ============================================================

def get_overview():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) as total_users, "
        "SUM(balance) as total_coins, "
        "AVG(balance) as avg_coins, "
        "MAX(balance) as max_coins, "
        "SUM(messages) as total_messages, "
        "SUM(voice_minutes) as total_voice, "
        "SUM(reputation) as total_rep "
        "FROM users WHERE guild_id = ?",
        (GUILD_ID,)
    )
    row = cur.fetchone()
    conn.close()

    return {
        "total_users": row["total_users"] or 0,
        "total_coins": row["total_coins"] or 0,
        "avg_coins": int(row["avg_coins"] or 0),
        "max_coins": row["max_coins"] or 0,
        "total_messages": row["total_messages"] or 0,
        "total_voice": row["total_voice"] or 0,
        "total_rep": row["total_rep"] or 0,
    }


def get_game_overview():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) as total_games, "
        "SUM(bet) as total_bets, "
        "SUM(profit) as total_profit, "
        "SUM(CASE WHEN win = 1 THEN 1 ELSE 0 END) as total_wins "
        "FROM game_history WHERE guild_id = ?",
        (GUILD_ID,)
    )
    row = cur.fetchone()
    conn.close()

    total = row["total_games"] or 0
    wins = row["total_wins"] or 0

    return {
        "total_games": total,
        "total_bets": row["total_bets"] or 0,
        "total_profit": row["total_profit"] or 0,
        "total_wins": wins,
        "winrate": round(wins / total * 100, 1) if total > 0 else 0,
    }


# ============================================================
# ТОПЫ
# ============================================================

def get_top_balances(limit: int = 10):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT user_id, balance FROM users WHERE guild_id = ? "
        "ORDER BY balance DESC LIMIT ?",
        (GUILD_ID, limit)
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_top_levels(limit: int = 10):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT user_id, level, xp, messages FROM users WHERE guild_id = ? "
        "ORDER BY level DESC, xp DESC LIMIT ?",
        (GUILD_ID, limit)
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_top_reputation(limit: int = 10):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT user_id, reputation FROM users "
        "WHERE guild_id = ? AND reputation > 0 "
        "ORDER BY reputation DESC LIMIT ?",
        (GUILD_ID, limit)
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_top_voice(limit: int = 10):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT user_id, voice_minutes FROM users "
        "WHERE guild_id = ? AND voice_minutes > 0 "
        "ORDER BY voice_minutes DESC LIMIT ?",
        (GUILD_ID, limit)
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_top_players(limit: int = 10):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT user_id, SUM(profit) as total_profit, COUNT(*) as games, "
        "SUM(CASE WHEN win = 1 THEN 1 ELSE 0 END) as wins "
        "FROM game_history WHERE guild_id = ? "
        "GROUP BY user_id ORDER BY total_profit DESC LIMIT ?",
        (GUILD_ID, limit)
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


# ============================================================
# ПРОФИЛЬ (данные из бота)
# ============================================================

def get_user(user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM users WHERE guild_id = ? AND user_id = ?",
        (GUILD_ID, user_id)
    )
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_warnings(user_id: int, limit: int = 20):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM warnings WHERE guild_id = ? AND user_id = ? "
        "ORDER BY id DESC LIMIT ?",
        (GUILD_ID, user_id, limit)
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_user_transactions(user_id: int, limit: int = 20):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM transactions "
        "WHERE guild_id = ? AND (from_id = ? OR to_id = ?) "
        "ORDER BY id DESC LIMIT ?",
        (GUILD_ID, user_id, user_id, limit)
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_user_achievements(user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT achievement, unlocked_at FROM achievements "
        "WHERE guild_id = ? AND user_id = ? "
        "ORDER BY unlocked_at DESC",
        (GUILD_ID, user_id)
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_user_games_stats(user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) as total, "
        "SUM(CASE WHEN win = 1 THEN 1 ELSE 0 END) as wins, "
        "SUM(profit) as total_profit "
        "FROM game_history WHERE guild_id = ? AND user_id = ?",
        (GUILD_ID, user_id)
    )
    row = cur.fetchone()
    conn.close()
    return {
        "total": row["total"] or 0,
        "wins": row["wins"] or 0,
        "total_profit": row["total_profit"] or 0,
    }


# ============================================================
# ЭКОНОМИКА
# ============================================================

def get_balance(guild_id: int, user_id: int, start_balance: int = 0) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO users (guild_id, user_id, balance) VALUES (?, ?, ?)",
        (guild_id, user_id, start_balance)
    )
    conn.commit()
    cur.execute(
        "SELECT balance FROM users WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id)
    )
    row = cur.fetchone()
    conn.close()
    return row["balance"] if row else 0


def remove_balance(guild_id: int, user_id: int, amount: int, start_balance: int = 0) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO users (guild_id, user_id, balance) VALUES (?, ?, ?)",
        (guild_id, user_id, start_balance)
    )
    cur.execute(
        "UPDATE users SET balance = MAX(0, balance - ?) WHERE guild_id = ? AND user_id = ?",
        (amount, guild_id, user_id)
    )
    conn.commit()
    cur.execute(
        "SELECT balance FROM users WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id)
    )
    new_balance = cur.fetchone()["balance"]
    conn.close()
    return new_balance


def add_transaction(guild_id, from_id, to_id, amount, type_, reason=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO transactions (guild_id, from_id, to_id, amount, type, reason, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (guild_id, from_id, to_id, amount, type_, reason, _now_iso())
    )
    conn.commit()
    conn.close()


# ============================================================
# МАГАЗИН — для пользователя
# ============================================================

def get_user_items(guild_id: int, user_id: int):
    """Купленные предметы пользователя (из user_items)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM user_items WHERE guild_id = ? AND user_id = ? "
        "ORDER BY purchased_at DESC",
        (guild_id, user_id)
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def buy_item(guild_id: int, user_id: int, item_id: str, item_name: str = None, price: int = 0):
    """
    Записывает покупку предмета.
    item_id — строковый ID (приводим к str для совместимости).
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO user_items (guild_id, user_id, item_id, item_name, price, purchased_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (guild_id, user_id, str(item_id), item_name, price, _now_iso())
    )
    conn.commit()
    conn.close()


# ============================================================
# МАГАЗИН — АДМИН (shop_items)
# ============================================================

def admin_get_shop_items(guild_id: int):
    """Все товары из shop_items."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT * FROM shop_items WHERE guild_id = ? ORDER BY id ASC",
            (guild_id,)
        )
        rows = [dict(r) for r in cur.fetchall()]
    except sqlite3.OperationalError:
        rows = []
    conn.close()
    return rows


def admin_get_shop_item(guild_id: int, item_id: int):
    """Один товар по ID."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT * FROM shop_items WHERE guild_id = ? AND id = ?",
            (guild_id, item_id)
        )
        row = cur.fetchone()
    except sqlite3.OperationalError:
        row = None
    conn.close()
    return dict(row) if row else None


def admin_add_shop_item(
    guild_id: int,
    name: str,
    description: str = None,
    price: int = 0,
    role_id: int = None,
    stock: int = -1,
    icon: str = None,
    image_url: str = None,
):
    """Добавить товар. Возвращает ID нового или None, если имя занято."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO shop_items "
            "(guild_id, name, description, price, role_id, stock, icon, image_url) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (guild_id, name, description, price, role_id, stock, icon, image_url)
        )
        conn.commit()
        item_id = cur.lastrowid
    except sqlite3.IntegrityError:
        item_id = None
    conn.close()
    return item_id


def admin_update_shop_item(
    guild_id: int,
    item_id: int,
    name: str,
    description: str = None,
    price: int = 0,
    stock: int = -1,
    role_id: int = None,
    icon: str = None,
    image_url: str = None,
):
    """Обновить товар (включая icon и image_url)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE shop_items "
        "SET name = ?, description = ?, price = ?, stock = ?, role_id = ?, "
        "icon = ?, image_url = ? "
        "WHERE guild_id = ? AND id = ?",
        (name, description, price, stock, role_id, icon, image_url, guild_id, item_id)
    )
    conn.commit()
    conn.close()


def admin_delete_shop_item(guild_id: int, item_id: int):
    """Удалить товар."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM shop_items WHERE guild_id = ? AND id = ?",
        (guild_id, item_id)
    )
    conn.commit()
    conn.close()


# ============================================================
# ЛОГИ
# ============================================================

def get_recent_warnings(limit: int = 50):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM warnings WHERE guild_id = ? "
        "ORDER BY id DESC LIMIT ?",
        (GUILD_ID, limit)
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_recent_transactions(limit: int = 50):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM transactions WHERE guild_id = ? "
        "ORDER BY id DESC LIMIT ?",
        (GUILD_ID, limit)
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def admin_delete_warning(warning_id: int):
    """Удаляет предупреждение по ID (для админки)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM warnings WHERE id = ?", (warning_id,))
    conn.commit()
    conn.close()


# ============================================================
# ГРАФИКИ
# ============================================================

def get_daily_games(days: int = 7):
    conn = get_connection()
    cur = conn.cursor()

    result = []
    for i in range(days):
        day_start = (datetime.now(timezone.utc) - timedelta(days=days - i - 1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        day_end = day_start + timedelta(days=1)

        cur.execute(
            "SELECT COUNT(*) FROM game_history "
            "WHERE guild_id = ? AND created_at >= ? AND created_at < ?",
            (GUILD_ID, day_start.isoformat(), day_end.isoformat())
        )
        count = cur.fetchone()[0] or 0
        result.append({
            "date": day_start.strftime("%d.%m"),
            "count": count,
        })

    conn.close()
    return result


# ============================================================
# WEB USERS — ИНИЦИАЛИЗАЦИЯ
# ============================================================

def init_web_tables():
    """Создаёт таблицы для веб-пользователей, сессий и кодов привязки."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS web_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            display_name TEXT NOT NULL,
            email TEXT,

            discord_id INTEGER UNIQUE,
            discord_username TEXT,
            discord_avatar TEXT,
            telegram_id INTEGER UNIQUE,
            telegram_username TEXT,
            guild_user_id INTEGER UNIQUE,

            role TEXT DEFAULT 'guest',
            is_moderator INTEGER DEFAULT 0,
            is_coder INTEGER DEFAULT 0,
            is_admin INTEGER DEFAULT 0,

            created_at TEXT NOT NULL,
            last_login TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS web_sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES web_users(id) ON DELETE CASCADE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            item_id TEXT NOT NULL,
            item_name TEXT,
            price INTEGER DEFAULT 0,
            purchased_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS telegram_link_codes (
            code TEXT PRIMARY KEY,
            web_user_id INTEGER NOT NULL,
            expires_at TEXT NOT NULL,
            FOREIGN KEY (web_user_id) REFERENCES web_users(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()


# ============================================================
# WEB USERS — CRUD
# ============================================================

def create_web_user(username, password_hash, display_name, email=None, role="guest"):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO web_users "
            "(username, password_hash, display_name, email, role, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (username, password_hash, display_name, email, role, _now_iso())
        )
        conn.commit()
        user_id = cur.lastrowid
    except sqlite3.IntegrityError:
        user_id = None
    conn.close()
    return user_id


def get_web_user_by_username(username):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM web_users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_web_user_by_id(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM web_users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_web_user_by_discord(discord_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM web_users WHERE discord_id = ?", (discord_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_web_user_by_telegram(telegram_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM web_users WHERE telegram_id = ?", (telegram_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def update_web_user(user_id, **fields):
    """Обновляет поля web_users."""
    if not fields:
        return

    allowed = {
        "display_name", "email", "password_hash",
        "discord_id", "discord_username", "discord_avatar",
        "telegram_id", "telegram_username",
        "guild_user_id",
        "role", "is_moderator", "is_coder", "is_admin",
        "last_login",
    }
    fields = {k: v for k, v in fields.items() if k in allowed}
    if not fields:
        return

    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [user_id]

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"UPDATE web_users SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()


# ============================================================
# WEB USERS — РОЛИ
# ============================================================

def get_all_web_users(limit: int = 100, offset: int = 0):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, username, display_name, email, role, "
        "is_moderator, is_coder, is_admin, "
        "discord_id, discord_username, telegram_id, telegram_username, "
        "created_at, last_login "
        "FROM web_users ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (limit, offset)
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def count_web_users():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM web_users")
    count = cur.fetchone()[0] or 0
    conn.close()
    return count


def set_user_role(user_id: int, role: str):
    """Устанавливает общую роль: 'guest' или 'ghost'."""
    if role not in ("guest", "ghost"):
        return False
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE web_users SET role = ? WHERE id = ?", (role, user_id))
    conn.commit()
    conn.close()
    return True


def toggle_system_role(user_id: int, role: str, value: bool):
    """
    Включает/выключает системную роль.
    role: 'is_moderator' | 'is_coder' | 'is_admin'
    """
    if role not in ("is_moderator", "is_coder", "is_admin"):
        return False
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"UPDATE web_users SET {role} = ? WHERE id = ?", (1 if value else 0, user_id))
    conn.commit()
    conn.close()
    return True


def delete_web_user(user_id: int):
    """Удаляет пользователя и все его сессии/коды."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM web_sessions WHERE user_id = ?", (user_id,))
    cur.execute("DELETE FROM telegram_link_codes WHERE web_user_id = ?", (user_id,))
    cur.execute("DELETE FROM web_users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()


# ============================================================
# ИГРОВАЯ ЭКОНОМИКА — АДМИН
# ============================================================

def admin_get_users(guild_id: int, limit: int = 50, offset: int = 0, search: str = None):
    """Список игроков из users с пагинацией и поиском по user_id."""
    conn = get_connection()
    cur = conn.cursor()

    if search and search.isdigit():
        cur.execute(
            "SELECT * FROM users WHERE guild_id = ? AND user_id = ? "
            "ORDER BY balance DESC LIMIT ? OFFSET ?",
            (guild_id, int(search), limit, offset)
        )
    else:
        cur.execute(
            "SELECT * FROM users WHERE guild_id = ? "
            "ORDER BY balance DESC LIMIT ? OFFSET ?",
            (guild_id, limit, offset)
        )

    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def admin_count_users(guild_id: int, search: str = None) -> int:
    conn = get_connection()
    cur = conn.cursor()

    if search and search.isdigit():
        cur.execute(
            "SELECT COUNT(*) FROM users WHERE guild_id = ? AND user_id = ?",
            (guild_id, int(search))
        )
    else:
        cur.execute(
            "SELECT COUNT(*) FROM users WHERE guild_id = ?",
            (guild_id,)
        )

    count = cur.fetchone()[0] or 0
    conn.close()
    return count


def admin_set_balance(guild_id: int, user_id: int, amount: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO users (guild_id, user_id, balance) VALUES (?, ?, 0)",
        (guild_id, user_id)
    )
    cur.execute(
        "UPDATE users SET balance = ? WHERE guild_id = ? AND user_id = ?",
        (amount, guild_id, user_id)
    )
    conn.commit()
    conn.close()


def admin_add_balance(guild_id: int, user_id: int, amount: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO users (guild_id, user_id, balance) VALUES (?, ?, 0)",
        (guild_id, user_id)
    )
    cur.execute(
        "UPDATE users SET balance = balance + ? WHERE guild_id = ? AND user_id = ?",
        (amount, guild_id, user_id)
    )
    conn.commit()
    conn.close()


def admin_remove_balance(guild_id: int, user_id: int, amount: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO users (guild_id, user_id, balance) VALUES (?, ?, 0)",
        (guild_id, user_id)
    )
    cur.execute(
        "UPDATE users SET balance = MAX(0, balance - ?) WHERE guild_id = ? AND user_id = ?",
        (amount, guild_id, user_id)
    )
    conn.commit()
    conn.close()


def admin_reset_field(guild_id: int, user_id: int, field: str):
    """Сбросить поле игрока: level | reputation | warnings | voice | messages."""
    allowed = {
        "level": "level = 0, xp = 0",
        "reputation": "reputation = 0",
        "voice": "voice_minutes = 0",
        "messages": "messages = 0",
    }

    if field == "warnings":
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM warnings WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id)
        )
        conn.commit()
        conn.close()
        return

    if field not in allowed:
        return

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        f"UPDATE users SET {allowed[field]} WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id)
    )
    conn.commit()
    conn.close()


# ============================================================
# ИГРЫ — АДМИН
# ============================================================

def admin_get_game_history(guild_id: int, limit: int = 100, offset: int = 0):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM game_history WHERE guild_id = ? "
        "ORDER BY id DESC LIMIT ? OFFSET ?",
        (guild_id, limit, offset)
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def admin_count_game_history(guild_id: int) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM game_history WHERE guild_id = ?",
        (guild_id,)
    )
    count = cur.fetchone()[0] or 0
    conn.close()
    return count


# ============================================================
# TELEGRAM — АДМИН
# ============================================================

def admin_get_telegram_links():
    """Список web_users с привязанным Telegram."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, username, display_name, telegram_id, telegram_username, "
        "guild_user_id, created_at "
        "FROM web_users WHERE telegram_id IS NOT NULL "
        "ORDER BY created_at DESC"
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


# ============================================================
# TELEGRAM LINK CODES
# ============================================================

def create_telegram_link_code(web_user_id: int) -> str:
    """Создаёт одноразовый код для привязки Telegram через бота."""
    code = secrets.token_hex(3).upper()
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM telegram_link_codes WHERE web_user_id = ?", (web_user_id,))
    cur.execute(
        "INSERT INTO telegram_link_codes (code, web_user_id, expires_at) VALUES (?, ?, ?)",
        (code, web_user_id, expires_at),
    )
    conn.commit()
    conn.close()
    return code


def cleanup_telegram_link_codes():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM telegram_link_codes WHERE expires_at < ?",
        (datetime.now(timezone.utc).isoformat(),),
    )
    conn.commit()
    conn.close()


# ============================================================
# SESSIONS
# ============================================================

def create_session(token, user_id, hours=72):
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=hours)
    cur.execute(
        "INSERT INTO web_sessions (token, user_id, created_at, expires_at) "
        "VALUES (?, ?, ?, ?)",
        (token, user_id, now.isoformat(), expires.isoformat())
    )
    conn.commit()
    conn.close()


def get_session(token):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM web_sessions WHERE token = ? AND expires_at > ?",
        (token, datetime.now(timezone.utc).isoformat())
    )
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def delete_session(token):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM web_sessions WHERE token = ?", (token,))
    conn.commit()
    conn.close()


def cleanup_sessions():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM web_sessions WHERE expires_at < ?",
        (datetime.now(timezone.utc).isoformat(),)
    )
    conn.commit()
    conn.close()