from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from ..database import db

router = Router()


async def _build_profile_text(telegram_id: int) -> str:
    user = await db.get_web_user_by_telegram_id(telegram_id)
    if not user:
        return (
            "🔗 <b>Telegram не привязан</b>\n\n"
            "Чтобы привязать:\n"
            "1. Зайди на сайт\n"
            "2. Настройки → Привязки → Telegram\n"
            "3. Нажми «Привязать через бота»\n"
            "4. Отправь мне код: <code>/link КОД</code>"
        )

    name = user.get("display_name") or user.get("username") or "—"
    guild_user_id = user.get("guild_user_id")

    # Игровая статистика есть только если привязан Discord
    if guild_user_id:
        stats = await db.get_stats(guild_user_id) or {}
        guild_line = f"🎮 Guild ID: <code>{guild_user_id}</code>\n\n"
        stats_block = (
            f"📈 Уровень: <b>{stats.get('level', 0)}</b>\n"
            f"💰 Баланс: <b>{stats.get('balance', 0):,}</b>\n"
            f"💬 Сообщений: <b>{stats.get('messages', 0):,}</b>\n"
            f"🎙 Войс: <b>{stats.get('voice_minutes', 0)} мин</b>\n"
            f"⭐ Репутация: <b>{stats.get('reputation', 0)}</b>"
        ).replace(",", " ")
    else:
        guild_line = "🎮 Discord: <i>не привязан</i>\n\n"
        stats_block = (
            "<i>Игровая статистика появится, "
            "когда привяжешь Discord на сайте.</i>"
        )

    return (
        f"👤 <b>{name}</b>\n"
        f"✈️ Telegram: <code>{user.get('telegram_id')}</code>\n"
        f"{guild_line}"
        f"{stats_block}"
    )


@router.message(Command("me"))
async def cmd_me(message: Message):
    text = await _build_profile_text(message.from_user.id)
    await message.answer(text, parse_mode="HTML")


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    text = await _build_profile_text(message.from_user.id)
    await message.answer(text, parse_mode="HTML")


@router.callback_query(F.data == "menu:profile")
async def cb_profile(call: CallbackQuery):
    text = await _build_profile_text(call.from_user.id)
    await call.message.edit_text(text, parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "menu:stats")
async def cb_stats(call: CallbackQuery):
    text = await _build_profile_text(call.from_user.id)
    await call.message.edit_text(text, parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "menu:link")
async def cb_link(call: CallbackQuery):
    await call.message.edit_text(
        "🔗 <b>Привязка Telegram</b>\n\n"
        "1. Открой сайт → Настройки → Привязки\n"
        "2. Нажми «Привязать через бота»\n"
        "3. Отправь мне полученный код:\n"
        "<code>/link ТВОЙ_КОД</code>",
        parse_mode="HTML",
    )
    await call.answer()