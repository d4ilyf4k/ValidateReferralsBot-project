from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext

from database.db_manager import (
    get_user_full_data,
    delete_user_all_data
)
from services.user_report_generator import (generate_user_finance_report)
from utils.keyboards import (
    get_start_kb,
    get_user_main_menu_kb
)
from utils.states import BankAgreement

router = Router()


# =========================
# 🏦 ДОБАВИТЬ БАНК / ПРОДУКТ
# =========================
@router.message(F.text == "🏦 Добавить банк")
async def add_bank_entry(message: types.Message, state: FSMContext):
    """
    Точка входа в bank_handler.
    Пользователь может выбрать новый банк или продукт
    в любой момент времени.
    """
    await state.set_state(BankAgreement.choosing_bank)
    await message.answer(
        "Выберите банк или продукт:",
        reply_markup=None  # клавиатура будет выдана bank_handler'ом
    )


# =========================
# ↩️ НАЗАД В МЕНЮ
# =========================
@router.message(F.text == "↩️ Назад в меню")
async def back_to_menu(message: types.Message):
    await message.answer(
        "Главное меню:",
        reply_markup=get_user_main_menu_kb()
    )


# =========================
# 🗑 УДАЛЕНИЕ ДАННЫХ
# =========================
@router.message(F.text == "🗑 Очистить историю")
async def clear_history(message: types.Message):
    user_id = message.from_user.id

    try:
        deleted = await delete_user_all_data(user_id)

        if deleted:
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
            await message.answer(
                "📭 <b>Данные не найдены</b>\n\n"
                "Похоже, вы ещё не зарегистрированы.",
                parse_mode="HTML",
                reply_markup=types.InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            types.InlineKeyboardButton(
                                text="📝 Начать регистрацию",
                                callback_data="start_registration"
                            )
                        ]
                    ]
                )
            )

    except Exception as e:
        await message.answer(
            "❌ <b>Ошибка при удалении данных</b>\n\n"
            "Пожалуйста, попробуйте позже.",
            parse_mode="HTML"
        )
        raise e


# =========================
# 🔄 НАЧАТЬ ЗАНОВО
# =========================
@router.callback_query(F.data == "start_over")
async def start_over_callback(callback: types.CallbackQuery):
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
