from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from utils.keyboards import get_phone_kb, get_bank_kb
from utils.states import Onboarding

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
