from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from services.user_report_generator import generate_user_finance_report
from utils.keyboards import get_user_main_menu_kb
router = Router()

@router.message(F.text == "💰 Финансовый отчёт")
async def show_finance_report(message: Message):
    text = await generate_user_finance_report(message.from_user.id)
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