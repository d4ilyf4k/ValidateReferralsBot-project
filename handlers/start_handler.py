from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup

from utils.traffic_sources import TRAFFIC_SOURCES, DEFAULT_SOURCE
from db.users import user_exists, create_user
from utils.validation import is_valid_full_name
from utils.keyboards import (
    get_start_kb,
    get_user_main_menu_kb,
    get_admin_panel_kb
)
from config import settings

router = Router()


class Onboarding(StatesGroup):
    full_name = State()


@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    # Очищаем предыдущий FSM
    await state.clear()

    is_registered = await user_exists(message.from_user.id)

    # ------------------------------
    # Определяем источник трафика
    # ------------------------------
    source_key = DEFAULT_SOURCE
    source_data = TRAFFIC_SOURCES.get(DEFAULT_SOURCE)

    # Deep-link передает source через /start source_key
    if message.text:
        parts = message.text.split(maxsplit=1)
        if len(parts) > 1:
            raw = parts[1].lower()
            if raw in TRAFFIC_SOURCES:
                source_key = raw
                source_data = TRAFFIC_SOURCES[raw]

    # Сохраняем source в FSM, чтобы потом использовать при генерации ссылок
    await state.update_data(traffic_source=source_key)

    # ------------------------------
    # Уже зарегистрированные пользователи
    # ------------------------------
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

    # ------------------------------
    # Новый пользователь: приветствие
    # ------------------------------
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

    # Сохраняем пользователя в БД вместе с источником трафика
    data = await state.get_data()
    await create_user(
        user_id=message.from_user.id,
        full_name=full_name,
        source=data.get("traffic_source", DEFAULT_SOURCE)
    )

    await state.clear()

    await message.answer(
        "✅ <b>Регистрация завершена!</b>\n\n"
        "Теперь вы можете выбрать банк и продукт.",
        parse_mode="HTML",
        reply_markup=get_user_main_menu_kb()
    )
