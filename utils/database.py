"""
Работа с базой данных (SQLite).
Хранит предупреждения, балансы, опыт, уровни, статистику.
"""

import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = "data/economy.db"


def _ensure_data_dir():
    os.makedirs("data", exist_ok=True)


def get_connection():
    _ensure_data_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Создаёт все таблицы."""
    conn = get_connection()
    cur = conn.cursor()

    # Предупреждения
    cur.execute("""
        CREATE TABLE IF NOT EXISTS warnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            moderator_id INTEGER NOT NULL,
            reason TEXT,
            created_at TEXT NOT NULL
        )
    """)

    # Пользователи
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            balance INTEGER DEFAULT 0,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 0,
            last_daily TEXT,
            last_xp TEXT,
            messages INTEGER DEFAULT 0,
            voice_minutes INTEGER DEFAULT 0,
            reputation INTEGER DEFAULT 0,
            last_rep TEXT,
            daily_streak INTEGER DEFAULT 0,
            PRIMARY KEY (guild_id, user_id)
        )
    """)

    # Реакционные роли
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reaction_roles (
            message_id INTEGER NOT NULL,
            emoji TEXT NOT NULL,
            role_id INTEGER NOT NULL,
            PRIMARY KEY (message_id, emoji)
        )
    """)

    # Автороли по уровню
    cur.execute("""
        CREATE TABLE IF NOT EXISTS level_roles (
            guild_id INTEGER NOT NULL,
            level INTEGER NOT NULL,
            role_id INTEGER NOT NULL,
            PRIMARY KEY (guild_id, level)
        )
    """)

    # История игр
    cur.execute("""
        CREATE TABLE IF NOT EXISTS game_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            game TEXT NOT NULL,
            bet INTEGER NOT NULL,
            win INTEGER NOT NULL,
            profit INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # История транзакций
    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            from_id INTEGER,
            to_id INTEGER,
            amount INTEGER NOT NULL,
            type TEXT NOT NULL,
            reason TEXT,
            created_at TEXT NOT NULL
        )
    """)

    # Магазин (товары)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS shop_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            price INTEGER NOT NULL,
            role_id INTEGER,
            stock INTEGER DEFAULT -1,
            UNIQUE (guild_id, name)
        )
    """)

    # Купленные товары
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            purchased_at TEXT NOT NULL
        )
    """)

    # Достижения
    cur.execute("""
        CREATE TABLE IF NOT EXISTS achievements (
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            achievement TEXT NOT NULL,
            unlocked_at TEXT NOT NULL,
            PRIMARY KEY (guild_id, user_id, achievement)
        )
    """)

    # Квесты (метаданные)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS quests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            quest_type TEXT NOT NULL,
            target INTEGER NOT NULL,
            reward INTEGER NOT NULL,
            UNIQUE (guild_id, name)
        )
    """)

    # Прогресс квестов
    cur.execute("""
        CREATE TABLE IF NOT EXISTS quest_progress (
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            quest_id TEXT NOT NULL,
            progress INTEGER DEFAULT 0,
            completed INTEGER DEFAULT 0,
            claimed INTEGER DEFAULT 0,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (guild_id, user_id, quest_id)
        )
    """)

    # Голосовые сессии
    cur.execute("""
        CREATE TABLE IF NOT EXISTS voice_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            joined_at TEXT NOT NULL,
            left_at TEXT,
            minutes INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()


# ==================== ПРЕДУПРЕЖДЕНИЯ ====================

def add_warning(guild_id, user_id, moderator_id, reason):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO warnings (guild_id, user_id, moderator_id, reason, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (guild_id, user_id, moderator_id, reason, datetime.utcnow().isoformat())
    )
    warn_id = cur.lastrowid
    conn.commit()
    conn.close()
    return warn_id


def get_warnings(guild_id, user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM warnings WHERE guild_id = ? AND user_id = ? ORDER BY id DESC",
        (guild_id, user_id)
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def count_warnings(guild_id, user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM warnings WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id)
    )
    count = cur.fetchone()[0]
    conn.close()
    return count


def clear_warnings(guild_id, user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM warnings WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id)
    )
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    return deleted


# ==================== ПОЛЬЗОВАТЕЛИ ====================

def _ensure_user(cur, guild_id, user_id, start_balance=0):
    cur.execute(
        "INSERT OR IGNORE INTO users (guild_id, user_id, balance) VALUES (?, ?, ?)",
        (guild_id, user_id, start_balance)
    )


def get_user_data(guild_id, user_id):
    conn = get_connection()
    cur = conn.cursor()
    _ensure_user(cur, guild_id, user_id)
    conn.commit()
    cur.execute(
        "SELECT * FROM users WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id)
    )
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


# ==================== ЭКОНОМИКА ====================

def get_balance(guild_id, user_id, start_balance=0):
    conn = get_connection()
    cur = conn.cursor()
    _ensure_user(cur, guild_id, user_id, start_balance)
    conn.commit()
    cur.execute(
        "SELECT balance FROM users WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id)
    )
    row = cur.fetchone()
    conn.close()
    return row["balance"] if row else 0


def set_balance(guild_id, user_id, amount, start_balance=0):
    conn = get_connection()
    cur = conn.cursor()
    _ensure_user(cur, guild_id, user_id, start_balance)
    cur.execute(
        "UPDATE users SET balance = ? WHERE guild_id = ? AND user_id = ?",
        (amount, guild_id, user_id)
    )
    conn.commit()
    conn.close()


def add_balance(guild_id, user_id, amount, start_balance=0):
    conn = get_connection()
    cur = conn.cursor()
    _ensure_user(cur, guild_id, user_id, start_balance)
    cur.execute(
        "UPDATE users SET balance = balance + ? WHERE guild_id = ? AND user_id = ?",
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


def remove_balance(guild_id, user_id, amount, start_balance=0):
    conn = get_connection()
    cur = conn.cursor()
    _ensure_user(cur, guild_id, user_id, start_balance)
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


def get_top_balances(guild_id, limit=10):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT user_id, balance FROM users WHERE guild_id = ? ORDER BY balance DESC LIMIT ?",
        (guild_id, limit)
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ==================== DAILY ====================

def can_claim_daily(guild_id, user_id, cooldown_hours=24):
    conn = get_connection()
    cur = conn.cursor()
    _ensure_user(cur, guild_id, user_id)
    conn.commit()
    cur.execute(
        "SELECT last_daily FROM users WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id)
    )
    row = cur.fetchone()
    conn.close()

    if not row or not row["last_daily"]:
        return True, 0

    last = datetime.fromisoformat(row["last_daily"])
    next_claim = last + timedelta(hours=cooldown_hours)
    now = datetime.utcnow()

    if now >= next_claim:
        return True, 0
    return False, int((next_claim - now).total_seconds())


def claim_daily(guild_id, user_id, amount):
    conn = get_connection()
    cur = conn.cursor()
    _ensure_user(cur, guild_id, user_id)
    cur.execute(
        "UPDATE users SET balance = balance + ?, last_daily = ? "
        "WHERE guild_id = ? AND user_id = ?",
        (amount, datetime.utcnow().isoformat(), guild_id, user_id)
    )
    conn.commit()
    cur.execute(
        "SELECT balance FROM users WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id)
    )
    new_balance = cur.fetchone()["balance"]
    conn.close()
    return new_balance


def get_daily_streak(guild_id, user_id):
    conn = get_connection()
    cur = conn.cursor()
    _ensure_user(cur, guild_id, user_id)
    conn.commit()
    cur.execute(
        "SELECT daily_streak FROM users WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id)
    )
    row = cur.fetchone()
    conn.close()
    return row["daily_streak"] if row else 0


def increment_daily_streak(guild_id, user_id):
    conn = get_connection()
    cur = conn.cursor()
    _ensure_user(cur, guild_id, user_id)
    cur.execute(
        "UPDATE users SET daily_streak = daily_streak + 1 WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id)
    )
    conn.commit()
    cur.execute(
        "SELECT daily_streak FROM users WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id)
    )
    streak = cur.fetchone()["daily_streak"]
    conn.close()
    return streak


def reset_daily_streak(guild_id, user_id):
    conn = get_connection()
    cur = conn.cursor()
    _ensure_user(cur, guild_id, user_id)
    cur.execute(
        "UPDATE users SET daily_streak = 0 WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id)
    )
    conn.commit()
    conn.close()


# ==================== ОПЫТ И УРОВНИ ====================

def xp_for_level(level: int) -> int:
    if level <= 0:
        return 0
    return 5 * (level ** 2) + 50 * level + 100


def add_xp(guild_id, user_id, amount: int):
    conn = get_connection()
    cur = conn.cursor()
    _ensure_user(cur, guild_id, user_id)
    conn.commit()

    cur.execute(
        "SELECT xp, level FROM users WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id)
    )
    row = cur.fetchone()
    old_xp = row["xp"]
    old_level = row["level"]

    new_xp = old_xp + amount
    new_level = old_level
    while new_xp >= xp_for_level(new_level + 1):
        new_level += 1

    cur.execute(
        "UPDATE users SET xp = ?, level = ?, messages = messages + 1 "
        "WHERE guild_id = ? AND user_id = ?",
        (new_xp, new_level, guild_id, user_id)
    )
    conn.commit()
    conn.close()

    return new_xp, new_level, new_level > old_level


def get_last_xp_time(guild_id, user_id):
    conn = get_connection()
    cur = conn.cursor()
    _ensure_user(cur, guild_id, user_id)
    conn.commit()
    cur.execute(
        "SELECT last_xp FROM users WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id)
    )
    row = cur.fetchone()
    conn.close()
    return row["last_xp"] if row else None


def set_last_xp_time(guild_id, user_id):
    conn = get_connection()
    cur = conn.cursor()
    _ensure_user(cur, guild_id, user_id)
    cur.execute(
        "UPDATE users SET last_xp = ? WHERE guild_id = ? AND user_id = ?",
        (datetime.utcnow().isoformat(), guild_id, user_id)
    )
    conn.commit()
    conn.close()


def get_top_levels(guild_id, limit=10):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT user_id, level, xp FROM users "
        "WHERE guild_id = ? ORDER BY level DESC, xp DESC LIMIT ?",
        (guild_id, limit)
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ==================== РЕАКЦИОННЫЕ РОЛИ ====================

def add_reaction_role(message_id: int, emoji: str, role_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO reaction_roles (message_id, emoji, role_id) VALUES (?, ?, ?)",
        (message_id, emoji, role_id)
    )
    conn.commit()
    conn.close()


def get_reaction_role(message_id: int, emoji: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT role_id FROM reaction_roles WHERE message_id = ? AND emoji = ?",
        (message_id, emoji)
    )
    row = cur.fetchone()
    conn.close()
    return row["role_id"] if row else None


def get_reaction_roles(message_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT emoji, role_id FROM reaction_roles WHERE message_id = ?",
        (message_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def remove_reaction_role(message_id: int, emoji: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM reaction_roles WHERE message_id = ? AND emoji = ?",
        (message_id, emoji)
    )
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    return deleted


# ==================== АВТОРОЛИ ПО УРОВНЮ ====================

def add_level_role(guild_id: int, level: int, role_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO level_roles (guild_id, level, role_id) VALUES (?, ?, ?)",
        (guild_id, level, role_id)
    )
    conn.commit()
    conn.close()


def remove_level_role(guild_id: int, level: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM level_roles WHERE guild_id = ? AND level = ?",
        (guild_id, level)
    )
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    return deleted


def get_level_roles(guild_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT level, role_id FROM level_roles WHERE guild_id = ? ORDER BY level ASC",
        (guild_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ==================== ИСТОРИЯ ИГР ====================

def add_game_result(guild_id, user_id, game: str, bet: int, win: bool, profit: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO game_history (guild_id, user_id, game, bet, win, profit, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (guild_id, user_id, game, bet, 1 if win else 0, profit, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()


def get_game_stats(guild_id, user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) as total, "
        "SUM(CASE WHEN win = 1 THEN 1 ELSE 0 END) as wins, "
        "SUM(profit) as total_profit "
        "FROM game_history WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id)
    )
    row = cur.fetchone()
    conn.close()
    return {
        "total": row["total"] or 0,
        "wins": row["wins"] or 0,
        "total_profit": row["total_profit"] or 0,
    }


def get_top_players(guild_id, limit=10):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT user_id, SUM(profit) as total_profit, COUNT(*) as games "
        "FROM game_history WHERE guild_id = ? "
        "GROUP BY user_id ORDER BY total_profit DESC LIMIT ?",
        (guild_id, limit)
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ==================== ТРАНЗАКЦИИ ====================

def add_transaction(guild_id, from_id, to_id, amount, type_, reason=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO transactions (guild_id, from_id, to_id, amount, type, reason, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (guild_id, from_id, to_id, amount, type_, reason, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()


def get_transactions(guild_id, user_id, limit=20):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM transactions WHERE guild_id = ? AND (from_id = ? OR to_id = ?) "
        "ORDER BY id DESC LIMIT ?",
        (guild_id, user_id, user_id, limit)
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ==================== РЕПУТАЦИЯ ====================

def add_reputation(guild_id, user_id, amount=1):
    conn = get_connection()
    cur = conn.cursor()
    _ensure_user(cur, guild_id, user_id)
    cur.execute(
        "UPDATE users SET reputation = reputation + ? WHERE guild_id = ? AND user_id = ?",
        (amount, guild_id, user_id)
    )
    conn.commit()
    cur.execute(
        "SELECT reputation FROM users WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id)
    )
    new_rep = cur.fetchone()["reputation"]
    conn.close()
    return new_rep


def can_give_rep(guild_id, user_id, cooldown_hours=24):
    conn = get_connection()
    cur = conn.cursor()
    _ensure_user(cur, guild_id, user_id)
    conn.commit()
    cur.execute(
        "SELECT last_rep FROM users WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id)
    )
    row = cur.fetchone()
    conn.close()

    if not row or not row["last_rep"]:
        return True, 0

    last = datetime.fromisoformat(row["last_rep"])
    next_rep = last + timedelta(hours=cooldown_hours)
    now = datetime.utcnow()

    if now >= next_rep:
        return True, 0
    return False, int((next_rep - now).total_seconds())


def set_last_rep_time(guild_id, user_id):
    conn = get_connection()
    cur = conn.cursor()
    _ensure_user(cur, guild_id, user_id)
    cur.execute(
        "UPDATE users SET last_rep = ? WHERE guild_id = ? AND user_id = ?",
        (datetime.utcnow().isoformat(), guild_id, user_id)
    )
    conn.commit()
    conn.close()


# ==================== ДОСТИЖЕНИЯ ====================

def unlock_achievement(guild_id, user_id, achievement: str):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO achievements (guild_id, user_id, achievement, unlocked_at) "
            "VALUES (?, ?, ?, ?)",
            (guild_id, user_id, achievement, datetime.utcnow().isoformat())
        )
        conn.commit()
        result = True
    except sqlite3.IntegrityError:
        result = False
    conn.close()
    return result


def get_achievements(guild_id, user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT achievement, unlocked_at FROM achievements "
        "WHERE guild_id = ? AND user_id = ? ORDER BY unlocked_at DESC",
        (guild_id, user_id)
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ==================== ГОЛОСОВАЯ АКТИВНОСТЬ ====================

def start_voice_session(guild_id, user_id, channel_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO voice_sessions (guild_id, user_id, channel_id, joined_at) "
        "VALUES (?, ?, ?, ?)",
        (guild_id, user_id, channel_id, datetime.utcnow().isoformat())
    )
    session_id = cur.lastrowid
    conn.commit()
    conn.close()
    return session_id


def end_voice_session(guild_id, user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, joined_at FROM voice_sessions "
        "WHERE guild_id = ? AND user_id = ? AND left_at IS NULL "
        "ORDER BY id DESC LIMIT 1",
        (guild_id, user_id)
    )
    row = cur.fetchone()
    if not row:
        conn.close()
        return 0

    session_id = row["id"]
    joined = datetime.fromisoformat(row["joined_at"])
    now = datetime.utcnow()
    minutes = int((now - joined).total_seconds() / 60)

    cur.execute(
        "UPDATE voice_sessions SET left_at = ?, minutes = ? WHERE id = ?",
        (now.isoformat(), minutes, session_id)
    )
    cur.execute(
        "UPDATE users SET voice_minutes = voice_minutes + ? "
        "WHERE guild_id = ? AND user_id = ?",
        (minutes, guild_id, user_id)
    )
    conn.commit()
    conn.close()
    return minutes


def get_voice_minutes(guild_id, user_id):
    conn = get_connection()
    cur = conn.cursor()
    _ensure_user(cur, guild_id, user_id)
    conn.commit()
    cur.execute(
        "SELECT voice_minutes FROM users WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id)
    )
    row = cur.fetchone()
    conn.close()
    return row["voice_minutes"] if row else 0


# ==================== МАГАЗИН ====================

def add_shop_item(guild_id, name, description, price, role_id=None, stock=-1):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO shop_items (guild_id, name, description, price, role_id, stock) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (guild_id, name, description, price, role_id, stock)
        )
        conn.commit()
        item_id = cur.lastrowid
    except sqlite3.IntegrityError:
        item_id = None
    conn.close()
    return item_id


def remove_shop_item(guild_id, name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM shop_items WHERE guild_id = ? AND name = ?",
        (guild_id, name)
    )
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    return deleted


def get_shop_items(guild_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM shop_items WHERE guild_id = ? ORDER BY price ASC",
        (guild_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_shop_item(guild_id, item_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM shop_items WHERE guild_id = ? AND id = ?",
        (guild_id, item_id)
    )
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def update_shop_stock(guild_id: int, item_id: int, stock: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE shop_items SET stock = ? WHERE guild_id = ? AND id = ?",
        (stock, guild_id, item_id)
    )
    conn.commit()
    conn.close()


def buy_item(guild_id, user_id, item_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO user_items (guild_id, user_id, item_id, purchased_at) "
        "VALUES (?, ?, ?, ?)",
        (guild_id, user_id, item_id, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()


def get_user_items(guild_id, user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT si.* FROM shop_items si "
        "JOIN user_items ui ON si.id = ui.item_id "
        "WHERE ui.guild_id = ? AND ui.user_id = ?",
        (guild_id, user_id)
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ==================== КВЕСТЫ ====================

def add_quest(guild_id, name, description, quest_type, target, reward):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO quests (guild_id, name, description, quest_type, target, reward) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (guild_id, name, description, quest_type, target, reward)
        )
        conn.commit()
        quest_id = cur.lastrowid
    except sqlite3.IntegrityError:
        quest_id = None
    conn.close()
    return quest_id


def get_quests(guild_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM quests WHERE guild_id = ?", (guild_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_quest_progress(guild_id, user_id):
    """Возвращает список прогрессов с id квеста."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT quest_id as id, progress, completed, claimed FROM quest_progress "
        "WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id)
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_quest_claimed(guild_id, user_id, quest_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE quest_progress SET claimed = 1, updated_at = ? "
        "WHERE guild_id = ? AND user_id = ? AND quest_id = ?",
        (datetime.utcnow().isoformat(), guild_id, user_id, quest_id)
    )
    conn.commit()
    conn.close()


def progress_quest(guild_id, user_id, quest_id, amount=1):
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()

    cur.execute(
        "SELECT progress FROM quest_progress "
        "WHERE guild_id = ? AND user_id = ? AND quest_id = ?",
        (guild_id, user_id, quest_id)
    )
    row = cur.fetchone()

    if row:
        cur.execute(
            "UPDATE quest_progress SET progress = progress + ?, updated_at = ? "
            "WHERE guild_id = ? AND user_id = ? AND quest_id = ?",
            (amount, now, guild_id, user_id, quest_id)
        )
    else:
        cur.execute(
            "INSERT INTO quest_progress (guild_id, user_id, quest_id, progress, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (guild_id, user_id, quest_id, amount, now)
        )

    conn.commit()
    conn.close()


def set_quest_progress(guild_id, user_id, quest_id, value):
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()

    cur.execute(
        "SELECT progress FROM quest_progress "
        "WHERE guild_id = ? AND user_id = ? AND quest_id = ?",
        (guild_id, user_id, quest_id)
    )
    row = cur.fetchone()

    if row:
        cur.execute(
            "UPDATE quest_progress SET progress = ?, updated_at = ? "
            "WHERE guild_id = ? AND user_id = ? AND quest_id = ?",
            (value, now, guild_id, user_id, quest_id)
        )
    else:
        cur.execute(
            "INSERT INTO quest_progress (guild_id, user_id, quest_id, progress, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (guild_id, user_id, quest_id, value, now)
        )

    conn.commit()
    conn.close()


def reset_repeatable_quests(guild_id, user_id, quest_ids: list):
    if not quest_ids:
        return
    conn = get_connection()
    cur = conn.cursor()
    placeholders = ",".join("?" * len(quest_ids))
    cur.execute(
        f"UPDATE quest_progress SET progress = 0, completed = 0, claimed = 0, updated_at = ? "
        f"WHERE guild_id = ? AND user_id = ? AND quest_id IN ({placeholders})",
        (datetime.utcnow().isoformat(), guild_id, user_id, *quest_ids)
    )
    conn.commit()
    conn.close()