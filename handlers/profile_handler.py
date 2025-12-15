from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext

from database.db_manager import (
    get_user_full_data,
    update_user_field,
    update_user_phone
)

from config import settings
from utils.keyboards import (
    get_edit_profile_kb,
    get_phone_kb,
    get_user_main_menu_kb,
    get_admin_panel_kb
)
from utils.states import ProfileEdit

router = Router()


# =========================
# Профиль пользователя
# =========================

@router.message(F.text == "✏️ Редактировать профиль")
async def edit_profile(message: types.Message):
    user_data = await get_user_full_data(message.from_user.id)
    if not user_data:
        await message.answer("Сначала завершите регистрацию с помощью /start.")
        return

    profile_text = (
        "👤 <b>Ваш профиль</b>\n\n"
        f"ФИО: {user_data['full_name']}\n"
        f"Банк(и): {', '.join(user_data.get('banks', [])) or '—'}\n"
    )

    await message.answer(
        profile_text,
        reply_markup=get_edit_profile_kb(),
        parse_mode="HTML"
    )


# =========================
# Выбор поля для редактирования
# =========================

@router.callback_query(F.data.startswith("edit_"))
async def handle_edit_field(callback: types.CallbackQuery, state: FSMContext):
    field = callback.data[5:]

    if field == "full_name":
        await state.set_state(ProfileEdit.full_name)
        await callback.message.answer("Введите новое ФИО:")

    elif field == "phone":
        await state.set_state(ProfileEdit.phone)
        await callback.message.answer(
            "Отправьте свой номер телефона:",
            reply_markup=get_phone_kb()
        )

    elif field == "bank":
        await callback.message.answer(
            "Выбор банка осуществляется через меню «🏦 Выбрать банк»."
        )

    await callback.answer()


# =========================
# Обработка ФИО
# =========================

@router.message(ProfileEdit.full_name)
async def process_full_name(message: types.Message, state: FSMContext):
    full_name = message.text.strip()

    if len(full_name.split()) < 2:
        await message.answer("Введите корректное ФИО (минимум 2 слова).")
        return

    await update_user_field(message.from_user.id, "full_name", full_name)
    await _finalize_profile_edit(message, state)


# =========================
# Обработка телефона
# =========================

@router.message(ProfileEdit.phone, F.contact)
async def process_phone(message: types.Message, state: FSMContext):
    if message.contact.user_id != message.from_user.id:
        await message.answer(
            "❌ Пожалуйста, отправьте <b>свой</b> номер телефона.",
            parse_mode="HTML"
        )
        return

    success = await update_user_phone(
        message.from_user.id,
        message.contact.phone_number
    )

    if not success:
        await message.answer("❌ Не удалось сохранить номер. Попробуйте позже.")
        return

    await _finalize_profile_edit(message, state)


async def _finalize_profile_edit(obj, state: FSMContext):
    is_admin = obj.from_user.id in settings.ADMIN_IDS
    menu_kb = get_admin_panel_kb() if is_admin else get_user_main_menu_kb()

    if isinstance(obj, types.Message):
        await obj.answer("✅ Профиль обновлён!", reply_markup=menu_kb)
    else:
        await obj.message.answer("✅ Профиль обновлён!", reply_markup=menu_kb)

    await state.clear()
    
