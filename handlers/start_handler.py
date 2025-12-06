from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from database.db_manager import user_exists, create_user
from utils.keyboards import (
    get_start_kb,
    get_user_main_menu_kb,
    get_admin_main_menu_kb,
    get_phone_kb,
    get_bank_kb
)
from config import settings

router = Router()

class Onboarding(StatesGroup):
    full_name = State()
    phone = State()
    bank = State()

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    is_registered = await user_exists(message.from_user.id)
    
    if is_registered:
        if message.from_user.id in settings.ADMIN_IDS:
            await message.answer("🛠 <b>Админ-меню</b>", reply_markup=get_admin_main_menu_kb(), parse_mode="HTML")
        else:
            await message.answer("👋 Добро пожаловать!\nВыберите действие:", reply_markup=get_user_main_menu_kb())
    else:
        welcome_text = (
            "<b>🌟Привет! Твой друг, Артур, делится с тобой выгодой от банков 💰</b>\n\n"
            "Он участвует в программе Т-Банка и Альфа-Банка. Если ты оформишь карту по его ссылке, <b>то получишь от него гарантированный бонус</b>, а он — вознаграждение от банка. Все в плюсе!\n\n"
            
            "<b>🤖 Бот помогает всё сделать честно и автоматически:</b>\n"
            "✅ <b>Даст тебе правильную ссылку</b>, чтобы банк засчитал заявку другу.\n"
            "✅ <b>Покажет все условия</b> для получения бонуса <b>до</b> оформления.\n"
            "✅ <b>Проконтролирует</b>, чтобы твой бонус от друга был выплачен сразу после активации карты.\n\n"
            
            "<b>🚀 Как это будет:</b>\n"
            "1. <b>Быстрая регистрация в боте</b> (чтобы привязать тебя к приглашению друга и считать бонусы).\n"
            "2. <b>Выбор банка</b> — Тинькофф или Альфа-Банк.\n"
            "3. <b>Изучение условий</b> — бот покажет, что именно нужно сделать для бонуса (например, потратить определённую сумму).\n"
            "4. <b>Оформление карты</b> — переход на официальный сайт банка.\n"
            "5. <b>Получение бонуса</b> — автоматический расчёт и напоминание другу о выплате.\n\n"
            
            "<i>Бонусы выплачиваются только при соблюдении условий банка. Не волнуйся — бот всё подробно объяснит на этапе выбора!</i>\n\n"
            
            "<b>👉 Готов получить карту и бонус? Первый шаг — быстрая регистрация в боте!</b>"

        )
        await message.answer(welcome_text, reply_markup=get_start_kb(), parse_mode="HTML")

@router.message(F.text == "Начать регистрацию")
async def start_reg(message: types.Message, state: FSMContext):
    await state.set_state(Onboarding.full_name)
    await message.answer("Введите ваше ФИО (например: Иванов Иван Иванович):")

@router.message(Onboarding.full_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(full_name=message.text.strip())
    await state.set_state(Onboarding.phone)
    await message.answer("Нажмите кнопку ниже, чтобы отправить номер телефона:", reply_markup=get_phone_kb())

@router.message(Onboarding.phone, F.contact)
async def process_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.contact.phone_number)
    await state.set_state(Onboarding.bank)
    await message.answer("Выберите банк:", reply_markup=get_bank_kb())

@router.message(Onboarding.bank, F.text.in_({"Т-Банк", "Альфа-Банк"}))
async def process_bank(message: types.Message, state: FSMContext):
    data = await state.get_data()
    bank_map = {"Т-Банк": "t-bank", "Альфа-Банк": "alpha"}
    bank = bank_map[message.text]
    await create_user(message.from_user.id, data["full_name"], data["phone"], bank)
    await state.clear()
    if message.from_user.id in settings.ADMIN_IDS:
        await message.answer("✅ Регистрация завершена!", reply_markup=get_admin_main_menu_kb())
    else:
        await message.answer("✅ Регистрация завершена!", reply_markup=get_user_main_menu_kb())
