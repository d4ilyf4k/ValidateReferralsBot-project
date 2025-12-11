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
            "<b>🌟 Привет! Я — официальный партнёр Т‑Банка</b> (Альфа-Банк — уже в разработке! 🤫)\n\n"

            "Оформи дебетовую карту по моей партнёрской ссылке — и <b>получи бонус напрямую от банка</b>:\n"
            "• <b>До 3000 ₽</b> — за Молодёжную карту (14–25 лет)\n"
            "• <b>2000 ₽</b> — за карту Drive при тратах от 5000 ₽ в первые 30 дней (по промокоду)\n"
            "• <b>500 ₽ + участие в розыгрыше до 5 000 000 ₽</b> — за классическую Tinkoff Black (акция «Золотой Билет»)\n\n"

            "<b>🤖 Бот поможет честно и без обмана:</b>\n"
            "✅ Подберёт <b>подходящую карту</b>: Black, Drive, Молодёжная, Аромакарта, Ретро, Premium\n"
            "✅ Покажет <b>точные условия</b> бонуса <b>до оформления</b>\n"
            "✅ Выдаст <b>персональную ссылку</b> с UTM — чтобы банк засчитал заявку\n"
            "✅ Напомнит о сроках — чтобы <b>ты не потерял бонус</b>\n\n"

            "<b>🚀 Как это работает:</b>\n"
            "1️⃣ <b>Зарегистрируйся</b> — 30 секунд\n"
            "2️⃣ <b>Выбери карту</b> — Black, Drive, Молодёжная и др.\n"
            "3️⃣ <b>Прочитай условия</b> — всё честно, без скрытых условий\n"
            "4️⃣ <b>Оформи карту</b> — переход на официальный сайт Т‑Банка\n"
            "5️⃣ <b>Выполни условия</b> — активация + покупка\n"
            "6️⃣ 💰 <b>Бонус приходит автоматически</b> — от самого банка!\n\n"

            "<i>⚠️ Бонусы выплачиваются Т‑Банком при соблюдении условий оффера. "
            "Бот не участвует в начислениях — он лишь помогает не упустить выгоду.</i>\n\n"

            "<b>👉 Готов получить карту и бонус? Начни с регистрации!</b>"
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

@router.message(Onboarding.bank, F.text.in_(["🏦Т-Банк", "🏦Альфа-Банк"]))
async def process_bank(message: types.Message, state: FSMContext):
    data = await state.get_data()
    bank_map = {"🏦Т-Банк": "t-bank", "🏦Альфа-Банк": "alpha"}
    bank = bank_map[message.text]
    await create_user(message.from_user.id, data["full_name"], data["phone"], bank)
    await state.clear()
    if message.from_user.id in settings.ADMIN_IDS:
        await message.answer("✅ Регистрация завершена!", reply_markup=get_admin_main_menu_kb())
    else:
        await message.answer("✅ Регистрация завершена!", reply_markup=get_user_main_menu_kb())
