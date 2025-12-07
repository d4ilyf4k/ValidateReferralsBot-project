from aiogram import Router, F, types
from database.db_manager import get_user_full_data, delete_user_all_data, add_user_bank, get_user_banks
from services.report_generator import generate_referral_text_report_with_conditions
from utils.keyboards import get_start_kb

router = Router()

@router.message(F.text == "🏦 Добавить банк")
async def add_bank_handler(message: types.Message):
    """Добавление второго банка пользователю."""
    user_id = message.from_user.id
    
    # Проверяем, какие банки уже выбраны
    user_banks = await get_user_banks(user_id)
    
    if len(user_banks) >= 2:
        await message.answer("Вы уже выбрали оба доступных банка.")
        return
    
    # Показываем доступные банки
    available_banks = []
    if "t-bank" not in user_banks:
        available_banks.append("Т-Банк")
    if "alpha" not in user_banks:
        available_banks.append("Альфа-Банк")
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(
                text="Т-Банк", 
                callback_data="select_bank_tbank"
            ) if "Т-Банк" in available_banks else None,
            types.InlineKeyboardButton(
                text="Альфа-Банк", 
                callback_data="select_bank_alpha"
            ) if "Альфа-Банк" in available_banks else None
        ]
    ])
    
    await message.answer(
        "Выберите дополнительный банк:",
        reply_markup=keyboard
    )

@router.callback_query(F.data.startswith("select_bank_"))
async def select_bank_callback(callback: types.CallbackQuery):
    """Обработчик выбора банка."""
    bank_map = {
        "select_bank_tbank": "t-bank",
        "select_bank_alpha": "alpha"
    }
    bank = bank_map.get(callback.data)
    if not bank:
        await callback.answer("Неизвестный банк")
        return
    user_id = callback.from_user.id
    await add_user_bank(user_id, bank)
    from services.bonus_calculator import recalculate_all_bonuses
    await recalculate_all_bonuses(user_id)
    await callback.answer(f"Банк {bank} добавлен!")
    await callback.message.answer(
        f"✅ Банк {bank} успешно добавлен!\n\n"
        "Теперь вы можете отслеживать прогресс по обоим банкам."
    )

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