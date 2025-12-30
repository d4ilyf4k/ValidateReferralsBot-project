from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove
import logging

from db.users import (
    delete_user_all_data
)
from utils.keyboards import (
    get_start_kb,
    get_user_main_menu_kb
)

router = Router()
logger = logging.getLogger(__name__)

# =========================
# 🗑 УДАЛЕНИЕ ДАННЫХ
# =========================
@router.message(F.text == "🗑 Очистить историю")
async def clear_history(message: types.Message):
    user_id = message.from_user.id
    logger.info("User %s requested data deletion", user_id)

    try:
        deleted = await delete_user_all_data(user_id)

        if deleted:
            logger.info("User %s data deleted successfully", user_id)
            await message.answer(    
                "✅ <b>Ваши данные успешно удалены</b>\n\n"
                "Все данные полностью удалены из системы.\n\n"
                "Вы можете начать заново:",
                parse_mode="HTML",
                reply_markup=types.InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            types.InlineKeyboardButton(
                                text="🔄 Начать заново",
                                callback_data="start_over"
                            )
                        ]
                    ]
                )
            )
        else:
            logger.info("User %s has no data to delete", user_id)
            await message.answer(
                "📭 <b>Данные не найдены</b>\n\n"
                "Похоже, вы ещё не зарегистрированы.",
                parse_mode="HTML",
                reply_markup=types.InlineKeyboardMarkup(
                    inline_keyboard=[
                        [types.InlineKeyboardButton(text="📝 Начать регистрацию", callback_data="start_registration")]
                    ]
                )
            )

    except Exception as e:
        logger.exception(
            "Error while deleting data for user %s",
            user_id
        )        
        await message.answer(
            "❌ <b>Ошибка при удалении данных</b>\n\n"
            "Пожалуйста, попробуйте позже.",
            parse_mode="HTML"
        )


# =========================
# 🔄 НАЧАТЬ ЗАНОВО
# =========================
@router.callback_query(F.data == "start_over")
async def start_over_callback(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    logger.info("User %s started over", user_id)
    await state.clear()
    await callback.message.answer(
        "🌟 <b>Добро пожаловать в бот «Рефералы Банков»!</b>\n\n"
        "Этот бот поможет вам:\n"
        "✅ Получать партнёрские ссылки\n"
        "✅ Отслеживать статус заявок\n"
        "✅ Видеть расчёт бонусов\n\n"
        "Для начала работы нажмите кнопку ниже 👇",
        parse_mode="HTML",
        reply_markup=get_start_kb()
    )
    await callback.answer()

@router.callback_query(F.data == "cancel_edit")
async def cancel_edit_profile(callback: types.CallbackQuery, state: FSMContext):
    # Сбрасываем состояние FSM
    await state.clear()

    # Отправляем пользователя в главное меню
    await callback.message.answer(
        "Вы вернулись в главное меню:",
        reply_markup=get_user_main_menu_kb()
    )
    await callback.answer()