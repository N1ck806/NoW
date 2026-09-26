"""
Логирование Nightmare.
Пишет логи в файл + консоль.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime


LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "bot.log")


def _ensure_log_dir():
    os.makedirs(LOG_DIR, exist_ok=True)


def setup_logger(name: str = "nightmare", level: int = logging.INFO) -> logging.Logger:
    """
    Настраивает логгер:
    - Файл с ротацией (5 МБ, 5 бэкапов)
    - Консольный вывод
    """
    _ensure_log_dir()

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # уже настроен

    logger.setLevel(level)

    # Формат
    fmt = logging.Formatter(
        "[{asctime}] [{levelname}] [{name}] {message}",
        style="{",
        datefmt="%d.%m.%Y %H:%M:%S",
    )

    # Файл
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)
    file_handler.setLevel(level)

    # Консоль
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)
    console_handler.setLevel(level)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.propagate = False

    return logger


# ==================== ОБЁРТКА ====================

class BotLogger:
    """Удобная обёртка для логирования."""

    def __init__(self, name: str = "nightmare"):
        self.logger = setup_logger(name)

    def info(self, msg: str, *args, **kwargs):
        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs):
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs):
        self.logger.error(msg, *args, **kwargs)

    def debug(self, msg: str, *args, **kwargs):
        self.logger.debug(msg, *args, **kwargs)

    def exception(self, msg: str, *args, **kwargs):
        self.logger.exception(msg, *args, **kwargs)

    def log_command(self, ctx, extra: str = None):
        """Логирует использование команды."""
        guild = ctx.guild.name if ctx.guild else "ЛС"
        user = f"{ctx.author} ({ctx.author.id})"
        msg = f"CMD [{guild}] {user}: {ctx.message.content}"
        if extra:
            msg += f" | {extra}"
        self.logger.info(msg)

    def log_moderation(self, action: str, moderator, target, reason: str = None):
        """Логирует действие модерации."""
        guild = target.guild.name if hasattr(target, "guild") else "?"
        msg = (
            f"MOD [{guild}] {action}: "
            f"модератор={moderator} ({getattr(moderator, 'id', '?')}), "
            f"цель={target} ({getattr(target, 'id', '?')})"
        )
        if reason:
            msg += f" | причина: {reason}"
        self.logger.info(msg)

    def log_transaction(self, guild_id, from_id, to_id, amount, type_):
        """Логирует транзакцию."""
        self.logger.info(
            f"ECO [guild={guild_id}] {type_}: {from_id} → {to_id} | {amount}"
        )


# ==================== ГЛОБАЛЬНЫЙ ЛОГГЕР ====================

log = BotLogger("nightmare")


# ==================== ЗАПИСЬ ОШИБОК ====================

def log_exception(exc: Exception, context: str = None):
    """Записывает исключение с контекстом."""
    msg = f"Исключение"
    if context:
        msg += f" [{context}]"
    msg += f": {type(exc).__name__}: {exc}"
    log.exception(msg)


# ==================== ОЧИСТКА СТАРЫХ ЛОГОВ ====================

def cleanup_old_logs(days: int = 30):
    """Удаляет лог-файлы старше N дней."""
    if not os.path.exists(LOG_DIR):
        return
    now = datetime.utcnow()
    for filename in os.listdir(LOG_DIR):
        path = os.path.join(LOG_DIR, filename)
        if not os.path.isfile(path):
            continue
        mtime = datetime.utcfromtimestamp(os.path.getmtime(path))
        if (now - mtime).days > days:
            try:
                os.remove(path)
                log.info(f"Удалён старый лог: {filename}")
            except OSError as e:
                log.warning(f"Не удалось удалить {filename}: {e}")