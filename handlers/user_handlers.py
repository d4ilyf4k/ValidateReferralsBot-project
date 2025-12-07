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
    
    try:
        print(f"🔄 Попытка удаления данных для user_id: {user_id}")
        
        deleted = await delete_user_all_data(user_id)
        
        if deleted:
            print(f"✅ Данные пользователя {user_id} успешно удалены")
            
            await message.answer(
                "✅ <b>Ваши персональные данные успешно удалены!</b>\n\n"
                "В соответствии с ФЗ-152 «О персональных данных» все ваши данные были полностью удалены из нашей системы.\n\n"
                "Если вы хотите снова воспользоваться услугами бота, нажмите кнопку ниже:",
                parse_mode="HTML",
                reply_markup=types.InlineKeyboardMarkup(
                    inline_keyboard=[
                        [types.InlineKeyboardButton(text="🔄 Начать заново", callback_data="start_over")]
                    ]
                )
            )
        else:
            print(f"⚠️ Данные пользователя {user_id} не найдены")
            await message.answer(
                "📭 <b>Данные не найдены</b>\n\n"
                "Похоже, вы ещё не зарегистрированы или ваши данные уже были удалены ранее.",
                parse_mode="HTML",
                reply_markup=types.InlineKeyboardMarkup(
                    inline_keyboard=[
                        [types.InlineKeyboardButton(text="📝 Начать регистрацию", callback_data="start_registration")]
                    ]
                )
            )
            
    except Exception as e:
        print(f"❌ Критическая ошибка при удалении данных пользователя {user_id}: {e}")
        import traceback
        traceback.print_exc()
        
        await message.answer(
            "❌ <b>Произошла ошибка при удалении данных</b>\n\n"
            "Пожалуйста, попробуйте позже или свяжитесь с поддержкой.",
            parse_mode="HTML"
        )

@router.callback_query(F.data == "start_over")
async def start_over_callback(callback: types.CallbackQuery):
    """Обработчик кнопки начала заново после удаления данных."""
    await callback.message.answer(
        "🌟 <b>Добро пожаловать в бот «Рефералы Банков»!</b>\n\n"
        "Этот бот поможет вам:\n"
        "✅ Отслеживать статус ваших реферальных заявок\n"
        "✅ Получать персональные ссылки на выпуск карт Т-Банка и Альфа-Банка\n"
        "✅ Автоматически рассчитывать ваше вознаграждение\n\n"
        "Для начала работы пройдите короткую регистрацию 👇",
        parse_mode="HTML",
        reply_markup=get_start_kb()
    )
    await callback.answer()