from aiogram import Router, F, types
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.db_manager import create_user, get_referral_link
from utils.keyboards import (
    get_phone_kb, 
    get_bank_kb,
    get_user_main_menu_kb
)

class Onboarding(StatesGroup):
    full_name = State()
    phone = State()
    bank = State()

router = Router()

@router.message(F.text == "Начать регистрацию")
async def start_reg(message: Message, state: FSMContext):
    await message.answer("Введите ваше ФИО (например: Иванов Иван Иванович):")
    await state.set_state(Onboarding.full_name)

@router.message(Onboarding.full_name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(full_name=message.text.strip())
    await message.answer("Нажмите кнопку ниже, чтобы отправить номер телефона:", reply_markup=get_phone_kb())
    await state.set_state(Onboarding.phone)

@router.message(Onboarding.phone, F.contact)
async def process_phone(message: Message, state: FSMContext):
    phone = message.contact.phone_number
    await state.update_data(phone=phone)
    await message.answer("Выберите банк:", reply_markup=get_bank_kb())
    await state.set_state(Onboarding.bank)

@router.message(Onboarding.bank, F.text.in_(["🏦Т-Банк", "🏦Альфа-Банк"]))
async def process_bank(message: types.Message, state: FSMContext):
    bank_key = "t-bank" if message.text == "🏦Т-Банк" else "alpha"
    await state.update_data(bank=bank_key)

    data = await state.get_data()
    await create_user(message.from_user.id, data["full_name"], data["phone"], bank_key)
    await message.answer("✅ Регистрация завершена!", reply_markup=get_user_main_menu_kb())
    await state.clear()

async def send_ref_link(message: types.Message, bank_text: str):
    bank_key = "t-bank" if bank_text == "🏦Т-Банк" else "alpha"
    link = await get_referral_link(bank_key)
    if link:
        bank_name = "Т-Банка" if bank_key == "t-bank" else "Альфа-Банка"
        await message.answer(f"📎 Ваша реферальная ссылка для {bank_name}:\n{link}")
    else:
        await message.answer("⚠️ Ссылка пока не настроена.")

@router.message(Onboarding.bank, F.text.in_(["🏦Т-Банк", "🏦Альфа-Банк"]))
async def process_bank_in_registration(message: types.Message, state: FSMContext):
    await state.update_data(bank="t-bank" if message.text == "🏦Т-Банк" else "alpha")
    await send_ref_link(message, message.text)
    data = await state.get_data()
    if data.get("full_name") and data.get("phone"):
        await create_user(message.from_user.id, data["full_name"], data["phone"], data["bank"])
        await message.answer("✅ Регистрация завершена!", reply_markup=get_user_main_menu_kb())
        await state.clear()