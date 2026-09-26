from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from ..database import db
from ..keyboards import main_menu_kb

router = Router()


@router.message(Command("link"))
async def cmd_link(message: Message):
    """Привязка через код с сайта: /link ABC123"""
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "❌ Использование: <code>/link ABC123</code>\n\n"
            "Код можно получить на сайте в разделе <b>Настройки → Привязки → Telegram</b>.",
            parse_mode="HTML",
        )
        return

    # Убираем все пробелы внутри кода на всякий случай
    code = "".join(parts[1].split()).upper()
    web_user_id = await db.consume_link_code(code)

    if not web_user_id:
        await message.answer(
            "❌ Код неверный или истёк.\n"
            "Получи новый на сайте."
        )
        return

    ok = await db.link_telegram(
        web_user_id=web_user_id,
        telegram_id=message.from_user.id,
        telegram_username=message.from_user.username,
    )

    if not ok:
        await message.answer(
            "⚠️ Этот Telegram уже привязан к другому аккаунту.\n"
            "Сначала отвяжи через /unlink."
        )
        return

    await message.answer(
        "✅ Telegram успешно привязан к твоему аккаунту на сайте!",
        reply_markup=main_menu_kb(),
    )


@router.message(Command("unlink"))
async def cmd_unlink(message: Message):
    ok = await db.unlink_telegram(message.from_user.id)
    if ok:
        await message.answer("✅ Telegram отвязан от аккаунта на сайте.")
    else:
        await message.answer("ℹ️ Твой Telegram и так не привязан.")