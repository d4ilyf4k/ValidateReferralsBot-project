from aiogram import Router, F, types
from database.db_manager import get_user_full_data, delete_user_all_data
from services.report_generator import generate_referral_text_report_with_conditions
from utils.keyboards import get_start_kb

router = Router()

@router.message(F.text == "💰 Финансовый отчёт")
async def user_finance_report(message: types.Message):
    user_data = await get_user_full_data(message.from_user.id)
    if not user_data:
        await message.answer("Сначала завершите регистрацию.")
        return
    report = generate_referral_text_report_with_conditions(user_data)
    await message.answer(report, parse_mode="HTML")

@router.message(F.text == "↩️ Назад в меню")
async def back_to_menu(message: types.Message):
    from utils.keyboards import get_user_main_menu_kb
    await message.answer("Главное меню:", reply_markup=get_user_main_menu_kb())
    
@router.message(F.text == "🗑 Очистить историю")
async def clear_history(message: types.Message):
    user_id = message.from_user.id

    deleted = await delete_user_all_data(user_id)

    if deleted:
        welcome_text = (
            "🌟 <b>Добро пожаловать в бот «Рефералы Банков»!</b>\n\n"
            "Этот бот поможет вам:\n"
            "✅ Отслеживать статус ваших реферальных заявок\n"
            "✅ Получать персональные ссылки на выпуск карт Т-Банка и Альфа-Банка\n"
            "✅ Автоматически рассчитывать ваше вознаграждение\n\n"
            "Для начала работы пройдите короткую регистрацию 👇"
        )
        await message.answer(welcome_text, reply_markup=get_start_kb(), parse_mode="HTML")
    else:
        await message.answer(
            "Вы ещё не зарегистрированы. Нажмите «Начать регистрацию»:",
            reply_markup=get_start_kb()
        )