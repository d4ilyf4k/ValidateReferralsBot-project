from aiogram import Router, F, types
from datetime import datetime
from aiogram.fsm.context import FSMContext
from database.db_manager import get_user_full_data, update_user_field, update_progress_field
from services.bonus_calculator import recalculate_all_bonuses
from config import settings
from utils.keyboards import (
    get_edit_profile_kb,
    get_phone_kb,
    get_bank_kb,
    get_yes_no_kb,
    get_user_main_menu_kb,
    get_admin_main_menu_kb
)
from utils.states import ProfileEdit
from .callback_handlers import _finalize_profile_edit

router = Router()

@router.message(F.text == "✏️ Редактировать профиль")
async def edit_profile(message: types.Message):
    user_data = await get_user_full_data(message.from_user.id)
    if not user_data:
        await message.answer("Сначала завершите регистрацию с помощью /start.")
        return

    profile_text = (
        "👤 <b>Ваш профиль</b>\n\n"
        f"ФИО: {user_data['full_name']}\n"
        f"Банк: {'Т-Банк' if user_data['bank'] == 't-bank' else 'Альфа-Банк'}\n"
        f"Карта активирована: {'✅' if user_data.get('card_activated') else '❌'}\n"
        f"Первая покупка: {'✅' if user_data.get('purchase_made') else '❌'}"
    )
    await message.answer(profile_text, reply_markup=get_edit_profile_kb(), parse_mode="HTML")

@router.callback_query(F.data.startswith("edit_"))
async def handle_edit_field(callback: types.CallbackQuery, state: FSMContext):
    field = callback.data[5:]
    if field == "full_name":
        await state.set_state(ProfileEdit.full_name)
        await callback.message.answer("Введите новое ФИО (например: Иванов Иван Иванович):")
    elif field == "phone":
        await state.set_state(ProfileEdit.phone)
        await callback.message.answer("Отправьте новый номер:", reply_markup=get_phone_kb())
    elif field == "bank":
        await state.set_state(ProfileEdit.bank)
        await callback.message.answer("Выберите банк:", reply_markup=get_bank_kb())
    elif field == "card_activated":
        await state.set_state(ProfileEdit.card_activated)
        await callback.message.answer("Карта активирована?", reply_markup=get_yes_no_kb("card_act"))
    elif field == "purchase_made":
        await state.set_state(ProfileEdit.purchase_made)
        await callback.message.answer("Первая покупка совершена?", reply_markup=get_yes_no_kb("purchase"))
    await callback.answer()

@router.message(ProfileEdit.full_name)
async def process_full_name(message: types.Message, state: FSMContext):
    full_name = message.text.strip()
    if len(full_name.split()) < 2:
        await message.answer("Некорректный формат. Укажите ФИО (минимум 2 слова, кириллица).")
        return
    await update_user_field(message.from_user.id, "full_name", full_name)
    await finalize_edit(message, state)

@router.message(ProfileEdit.phone, F.contact)
async def process_phone(message: types.Message, state: FSMContext):
    phone = message.contact.phone_number
    await update_user_field(message.from_user.id, "phone", phone)
    await finalize_edit(message, state)

@router.message(ProfileEdit.bank, F.text.in_({"🏦Т-Банк", "🏦Альфа-Банк"}))
async def process_bank(message: types.Message, state: FSMContext):
    bank_map = {"Т-Банк": "t-bank", "Альфа-Банк": "alpha"}
    bank = bank_map[message.text]
    await update_user_field(message.from_user.id, "bank", bank)
    await finalize_edit(message, state)

@router.callback_query(ProfileEdit.card_activated, F.data.startswith("yesno_card_act"))
async def process_card_activated(callback: types.CallbackQuery, state: FSMContext):
    value = callback.data == "yesno_card_act_yes"
    
    await update_progress_field(callback.from_user.id, "card_activated", value)
    
    if value:
        current_date = datetime.now().strftime("%d.%m.%Y")
        await update_progress_field(callback.from_user.id, "card_activated_date", current_date)
        print(f"✅ Установлена дата активации: {current_date} для user_id={callback.from_user.id}")
    
    await _finalize_profile_edit(callback, state)

@router.callback_query(ProfileEdit.purchase_made, F.data.startswith("yesno_purchase"))
async def process_purchase_made(callback: types.CallbackQuery, state: FSMContext):
    value = callback.data == "yesno_purchase_yes"
    
    await update_progress_field(callback.from_user.id, "purchase_made", value)
    
    if value:
        current_date = datetime.now().strftime("%d.%m.%Y")
        await update_progress_field(callback.from_user.id, "first_purchase_date", current_date)
        print(f"✅ Установлена дата покупки: {current_date} для user_id={callback.from_user.id}")
    
    await _finalize_profile_edit(callback, state)
    
@router.message(ProfileEdit.card_last4)
async def process_card_last4(message: types.Message, state: FSMContext):
    print(">>> ВВЕДЕНЫ 4 ЦИФРЫ:", message.text)
    text = message.text.strip()
    if not text.isdigit() or len(text) != 4:
        await message.answer("❌ Неверный формат. Введите ровно 4 цифры (например: 1234).")
        return
    await update_progress_field(message.from_user.id, "card_last4", text)
    await recalculate_all_bonuses(message.from_user.id)
    await message.answer("✅ Последние 4 цифры обновлены!", reply_markup=get_user_main_menu_kb())
    await state.clear()

async def finalize_edit(obj, state: FSMContext):
    is_admin = obj.from_user.id in settings.ADMIN_IDS
    menu_kb = get_admin_main_menu_kb() if is_admin else get_user_main_menu_kb()
    if isinstance(obj, types.Message):
        await obj.answer("✅ Профиль обновлён!", reply_markup=menu_kb)
    else:
        await obj.message.answer("✅ Профиль обновлён!", reply_markup=menu_kb)
    await state.clear()