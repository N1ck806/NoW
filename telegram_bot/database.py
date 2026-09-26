"""
Обёртка над общей SQLite-базой data/economy.db.
Читает/пишет те же таблицы, что Discord-бот и сайт.

ВАЖНО: единый источник правды для Telegram-привязки — таблица web_users.
Бот читает/пишет telegram_id ТОЛЬКО туда.
"""
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import aiosqlite

from .config import config


class TelegramDB:
    def __init__(self, db_path: str):
        self.db_path = db_path

    # ============================================
    # НИЗКОУРОВНЕВЫЙ ХЕЛПЕР
    # ============================================

    def _connect(self) -> aiosqlite.Connection:
        """
        Возвращает НЕоткрытое соединение — aiosqlite.Connection,
        который сам откроется при входе в async with.

        ВАЖНО: здесь НЕ должно быть await.
        aiosqlite.connect() возвращает объект, который реализует
        __await__ и __aenter__. Если мы сделаем await сами — поток
        запустится дважды, и получим 'threads can only be started once'.
        """
        return aiosqlite.connect(self.db_path)

    # ============================================
    # WEB USERS (аккаунты сайта)
    # ============================================

    async def get_web_user_by_telegram_id(self, telegram_id: int) -> Optional[dict]:
        """Ищет аккаунт сайта по telegram_id."""
        async with self._connect() as conn:
            conn.row_factory = aiosqlite.Row
            cur = await conn.execute(
                "SELECT * FROM web_users WHERE telegram_id = ?",
                (telegram_id,),
            )
            row = await cur.fetchone()
            return dict(row) if row else None

    async def get_web_user_by_id(self, web_user_id: int) -> Optional[dict]:
        async with self._connect() as conn:
            conn.row_factory = aiosqlite.Row
            cur = await conn.execute(
                "SELECT * FROM web_users WHERE id = ?",
                (web_user_id,),
            )
            row = await cur.fetchone()
            return dict(row) if row else None

    async def link_telegram(
        self,
        web_user_id: int,
        telegram_id: int,
        telegram_username: Optional[str] = None,
    ) -> bool:
        """
        Привязать Telegram к аккаунту сайта (web_users.id).
        Возвращает False, если этот telegram_id уже привязан к другому аккаунту.
        """
        async with self._connect() as conn:
            conn.row_factory = aiosqlite.Row

            cur = await conn.execute(
                "SELECT id FROM web_users WHERE telegram_id = ?",
                (telegram_id,),
            )
            existing = await cur.fetchone()
            if existing and existing["id"] != web_user_id:
                return False

            await conn.execute(
                """UPDATE web_users
                   SET telegram_id = ?, telegram_username = ?
                   WHERE id = ?""",
                (telegram_id, telegram_username, web_user_id),
            )
            await conn.commit()
            return True

    async def unlink_telegram(self, telegram_id: int) -> bool:
        """Отвязать Telegram от аккаунта сайта."""
        async with self._connect() as conn:
            conn.row_factory = aiosqlite.Row

            cur = await conn.execute(
                "SELECT id FROM web_users WHERE telegram_id = ?",
                (telegram_id,),
            )
            row = await cur.fetchone()
            if not row:
                return False

            await conn.execute(
                "UPDATE web_users SET telegram_id = NULL, telegram_username = NULL "
                "WHERE telegram_id = ?",
                (telegram_id,),
            )
            await conn.commit()
            return True

    # ============================================
    # КОДЫ ПРИВЯЗКИ
    # ============================================

    async def consume_link_code(self, code: str) -> Optional[int]:
        """
        Проверить и удалить одноразовый код.
        Возвращает web_user_id или None.
        """
        async with self._connect() as conn:
            conn.row_factory = aiosqlite.Row

            cur = await conn.execute(
                "SELECT web_user_id, expires_at FROM telegram_link_codes WHERE code = ?",
                (code.upper(),),
            )
            row = await cur.fetchone()
            if not row:
                return None

            expires_at = datetime.fromisoformat(row["expires_at"])
            # Если в БД naive — приводим к aware
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)

            if expires_at < datetime.now(timezone.utc):
                await conn.execute(
                    "DELETE FROM telegram_link_codes WHERE code = ?",
                    (code.upper(),),
                )
                await conn.commit()
                return None

            await conn.execute(
                "DELETE FROM telegram_link_codes WHERE code = ?",
                (code.upper(),),
            )
            await conn.commit()
            return row["web_user_id"]

    async def create_link_code(self, web_user_id: int) -> str:
        """
        Создать одноразовый код для привязки (живёт 10 минут).
        Оставлено для совместимости — основной создатель кода всё равно сайт.
        """
        code = secrets.token_hex(3).upper()  # 6 символов
        expires_at = (
            datetime.now(timezone.utc) + timedelta(minutes=10)
        ).isoformat()

        async with self._connect() as conn:
            await conn.execute(
                """INSERT OR REPLACE INTO telegram_link_codes
                   (code, web_user_id, expires_at)
                   VALUES (?, ?, ?)""",
                (code, web_user_id, expires_at),
            )
            await conn.commit()
        return code

    # ============================================
    # ИГРОВАЯ СТАТИСТИКА (из таблицы users)
    # ============================================

    async def get_stats(self, guild_user_id: int) -> Optional[dict]:
        """Игровая статистика Discord-бота по guild_user_id."""
        async with self._connect() as conn:
            conn.row_factory = aiosqlite.Row

            cur = await conn.execute(
                """SELECT level, balance, messages, voice_minutes, reputation
                   FROM users WHERE guild_id = ? AND user_id = ?""",
                (config.GUILD_ID, guild_user_id),
            )
            row = await cur.fetchone()
            return dict(row) if row else None


db = TelegramDB(str(config.DB_PATH))