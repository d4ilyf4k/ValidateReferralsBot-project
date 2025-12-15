from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from utils.traffic_sources import TRAFFIC_SOURCES, DEFAULT_SOURCE
from database.db_manager import user_exists, create_user
from utils.validation import is_valid_full_name, normalize_phone
from utils.keyboards import (
    get_start_kb,
    get_user_main_menu_kb,
    get_admin_panel_kb,
    get_phone_kb
)
from config import settings

router = Router()


class Onboarding(StatesGroup):
    full_name = State()
    phone = State()



@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()

    is_registered = await user_exists(message.from_user.id)

    source_key = None
    source_data = DEFAULT_SOURCE

    if message.text and len(message.text.split()) > 1:
        raw = message.text.split(maxsplit=1)[1].lower()
        if raw in TRAFFIC_SOURCES:
            source_key = raw
            source_data = TRAFFIC_SOURCES[raw]

    if source_key:
        await state.update_data(traffic_source=source_key)


    if is_registered:
        if message.from_user.id in settings.ADMIN_IDS:
            await message.answer(
                "🛠 <b>Админ-меню</b>",
                reply_markup=get_admin_panel_kb(),
                parse_mode="HTML"
            )
        else:
            await message.answer(
                "👋 С возвращением!",
                reply_markup=get_user_main_menu_kb()
            )
        return

    text = (
        f"{source_data['intro']}\n\n"
        "<b>🤖 Что делает бот:</b>\n"
        "✅ Ведёт только на официальный сайт банка\n"
        "✅ Показывает условия до оформления\n"
        "✅ Помогает не потерять бонус\n\n"
        "<b>👉 Готов начать?</b>"
    )

    await message.answer(
        text,
        reply_markup=get_start_kb(),
        parse_mode="HTML"
    )

@router.message(F.text == "Начать регистрацию")
async def start_reg(message: types.Message, state: FSMContext):
    await state.set_state(Onboarding.full_name)
    await message.answer(
        "✍️ Введите ваше <b>ФИО</b> (как в паспорте):",
        parse_mode="HTML"
    )

@router.message(Onboarding.full_name)
async def process_name(message: types.Message, state: FSMContext):
    full_name = message.text.strip()

    if not is_valid_full_name(full_name):
        await message.answer(
            "❌ ФИО должно быть на русском языке, без цифр.\n"
            "Пример: <b>Иванов Иван</b>",
            parse_mode="HTML"
        )
        return

    await state.update_data(full_name=full_name)
    await state.set_state(Onboarding.phone)

    await message.answer(
        "📱 Телефон нужен, чтобы банк корректно засчитал заявку"
    )
    await message.answer(
        "Нажмите кнопку ниже, чтобы отправить номер:",
        reply_markup=get_phone_kb()
    )


@router.message(Onboarding.phone, F.contact)
async def process_phone(message: types.Message, state: FSMContext):
    if message.contact.user_id != message.from_user.id:
        await message.answer(
            "❌ Пожалуйста, отправьте <b>свой</b> номер телефона.",
            parse_mode="HTML"
        )
        return

    phone = normalize_phone(message.contact.phone_number)
    if not phone or len(phone) != 11:
        await message.answer("❌ Не удалось распознать номер телефона.")
        return

    data = await state.get_data()

    await create_user(
        user_id=message.from_user.id,
        full_name=data["full_name"],
        phone=phone,
        source=data.get("traffic_source")
    )

    await state.clear()

    await message.answer(
        "✅ <b>Регистрация завершена!</b>\n\n"
        "Теперь вы можете выбрать банк и продукт.",
        parse_mode="HTML",
        reply_markup=get_user_main_menu_kb()
    )