from aiogram import Router, F, types
from aiogram.types import CallbackQuery
from services.user_report_generator import generate_user_finance_report
from utils.keyboards import get_user_main_menu_kb
from db.finance import (
    get_user_finance_summary,
    get_user_applications
)

router = Router()

@router.message(F.text == "💰 Финансовый отчёт")
async def finance_report(message: types.Message):
    user_id = message.from_user.id

    summary = await get_user_finance_summary(user_id)
    applications = await get_user_applications(user_id)

    approved = summary["approved_sum"]
    pending = summary["pending_sum"]
    total = approved + pending

    text = (
        f"💰 <b>Ваш финансовый отчёт</b>\n\n"
        f"✅ Подтверждено: <b>{approved} ₽</b>\n"
        f"⏳ В ожидании: <b>{pending} ₽</b>\n"
        f"📊 Всего: <b>{total} ₽</b>\n\n"
    )

    if not applications:
        text += "🗂 У вас пока нет заявок."
        return await message.answer(text, parse_mode="HTML")

    text += "🧾 <b>История заявок:</b>\n\n"

    for app in applications:
        status_emoji = {
            "approved": "✅",
            "pending": "⏳",
            "rejected": "❌"
        }.get(app["status"], "❔")

        text += (
            f"{status_emoji} <b>#{app['id']}</b> | "
            f"{app['bank_key']} / {app['product_key']}\n"
            f"💰 {app['gross_bonus']} ₽ | "
            f"📅 {app['created_at']}\n\n"
        )

    await message.answer(text, parse_mode="HTML")
    
    
@router.callback_query(F.data == "user:finance:show")
async def show_finance_report_callback(callback: CallbackQuery):
    text, keyboard = await generate_user_finance_report(callback.from_user.id)

    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer()


@router.callback_query(F.data == "user:finance:back")
async def finance_back(callback: CallbackQuery):
    await callback.message.edit_text(
        "Главное меню",
        reply_markup=get_user_main_menu_kb(),
        parse_mode="HTML"
    )
    await callback.answer()