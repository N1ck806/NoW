from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery

from ..database import db
from ..keyboards import main_menu_kb

router = Router()


@router.message(CommandStart(deep_link=True))
async def start_with_deeplink(message: Message, command: CommandStart):
    """
    Deep-link: t.me/NoW_Bot?start=<code>

    <code> — это одноразовый код привязки, который сайт создал
    в таблице telegram_link_codes. Бот его сразу потребляет.
    """
    payload = command.args
    if not payload:
        await start_plain(message)
        return

    code = "".join(payload.split()).upper()
    web_user_id = await db.consume_link_code(code)

    if not web_user_id:
        await message.answer(
            "❌ Код неверный или истёк.\n\n"
            "Получи новый на сайте: Настройки → Привязки → Telegram.",
            parse_mode="HTML",
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

    user = await db.get_web_user_by_id(web_user_id)
    name = (user or {}).get("display_name") or (user or {}).get("username") or "—"

    await message.answer(
        f"✅ Готово! Telegram привязан к аккаунту <b>{name}</b>.",
        parse_mode="HTML",
        reply_markup=main_menu_kb(),
    )


@router.message(CommandStart())
async def start_plain(message: Message):
    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        "Я бот <b>Nightmare of Whiners</b>.\n"
        "Помогу привязать Telegram к аккаунту на сайте и покажу статистику.\n\n"
        "Зайди на сайт → Настройки → Привязки → Telegram,\n"
        "получи код и отправь мне <code>/link КОД</code>.",
        parse_mode="HTML",
        reply_markup=main_menu_kb(),
    )


@router.callback_query(F.data == "menu:help")
async def cb_help(call: CallbackQuery):
    await call.message.edit_text(
        "📖 <b>Команды</b>\n\n"
        "/start — приветствие\n"
        "/link &lt;код&gt; — привязать Telegram\n"
        "/unlink — отвязать\n"
        "/me — мой профиль\n"
        "/stats — статистика\n"
        "/help — эта справка",
        parse_mode="HTML",
    )
    await call.answer()