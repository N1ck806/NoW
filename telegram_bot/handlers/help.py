from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📖 <b>Nightmare Bot — команды</b>\n\n"
        "/start — приветствие\n"
        "/link &lt;код&gt; — привязать Telegram\n"
        "/unlink — отвязать Telegram\n"
        "/me — мой профиль\n"
        "/stats — игровая статистика\n"
        "/help — эта справка\n\n"
        "🔗 Код для привязки берётся на сайте:\n"
        "<b>Настройки → Привязки → Telegram</b>",
        parse_mode="HTML",
    )