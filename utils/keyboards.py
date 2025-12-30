from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
    )

from aiogram.utils.keyboard import InlineKeyboardBuilder
from db.banks import get_active_banks
from typing import Union

def get_start_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Начать регистрацию")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_user_main_menu_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🏦 Выбрать банк"), KeyboardButton(text="ℹ️ Помощь")],
            [KeyboardButton(text="✏️ Редактировать профиль"), KeyboardButton(text="🗑 Очистить историю")]
        ],
        resize_keyboard=True
    )

async def get_user_bank_kb() -> ReplyKeyboardMarkup:
    banks = await get_active_banks()
    if not banks:
        return ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="🏦 Банки отсутствуют")]],
            resize_keyboard=True,
            one_time_keyboard=True
        )

    keyboard = []
    for bank in banks:
        keyboard.append([KeyboardButton(text=f"🏦 {bank['bank_title']}")])

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    
def get_edit_profile_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ ФИО", callback_data="edit_full_name")],
        [InlineKeyboardButton(text="✏️ Банк", callback_data="edit_bank")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_edit")]
    ])


def get_admin_panel_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Дашборд", callback_data="admin_dashboard"),
        InlineKeyboardButton(text="🔗 Обновить реф. ссылки", callback_data="admin_update_links")],
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users"),
        InlineKeyboardButton(text="🧩 Управление каталогом", callback_data="admin:catalog")],
        [InlineKeyboardButton(text="📑 Отчёты", callback_data="admin_reports"),
        InlineKeyboardButton(text="📋 Управление условиями", callback_data="admin_conditions")]
    ])


def get_admin_dashboard_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Финансы", callback_data="admin:finance")],
        [InlineKeyboardButton(text="📈 Трафик", callback_data="admin:traffic")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")]
    ])


def get_admin_reports_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 JSON-отчёт", callback_data="admin:report:json")],
        [InlineKeyboardButton(text="📄 PDF-отчёт", callback_data="admin:report:pdf")],
        [InlineKeyboardButton(text="📆 Еженедельная аналитика", callback_data="admin:report:weekly")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")],
    ])


def get_admin_finance_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Сводка", callback_data="admin:finance:summary")],
        [InlineKeyboardButton(text="📄 Детальный отчёт", callback_data="admin:finance:details")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_dashboard")]
    ])


def get_admin_traffic_filter_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Все", callback_data="admin:traffic:all"),
            InlineKeyboardButton(text="🎵 TikTok", callback_data="admin:traffic:tiktok"),
        ],
        [
            InlineKeyboardButton(text="▶️ YouTube", callback_data="admin:traffic:yt"),
            InlineKeyboardButton(text="✈️ Telegram", callback_data="admin:traffic:tg"),
        ],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_dashboard")]
    ])


def get_admin_users_list_kb(users: list[dict]) -> InlineKeyboardMarkup:
    keyboard = []
    for u in users:
        label = f"{u['user_id']}"
        if u.get("username"):
            label += f" @{u['username']}"
        elif u.get("first_name"):
            label += f" {u['first_name']}"
        label += f" · {u['applications_count']} заявок"
        keyboard.append([
            InlineKeyboardButton(text=label, callback_data=f"admin:user:{u['user_id']}")
        ])

    keyboard.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_admin_user_card_kb(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 Заявки пользователя", callback_data=f"admin:user:{user_id}:apps")],
        [InlineKeyboardButton(text="🗑 Удалить данные", callback_data=f"admin:user:{user_id}:delete")],
        [InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="admin_users")]
    ])
    
def get_admin_users_list_kb(users, page: int):
    kb = []
    for u in users:
        label = f"{u['user_id']}"
        if u.get("username"):
            label += f" @{u['username']}"
        elif u.get("first_name"):
            label += f" {u['first_name']}"
        label += f" · {u['applications_count']} заявок"
        kb.append([InlineKeyboardButton(text=label, callback_data=f"admin:user:{u['user_id']}")
        ])

    nav = []

    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"admin:users:page:{page - 1}"))

    if len(users) == 10:
        nav.append(InlineKeyboardButton(text="➡️ Далее", callback_data=f"admin:users:page:{page + 1}"))

    if nav:
        kb.append(nav)

    kb.append([
        InlineKeyboardButton(text="⬅️ В админку", callback_data="admin_panel")
    ])

    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_user_apps_kb(user_id: int, page: int, count: int):
    nav = []

    if page > 0:
        nav.append(
            InlineKeyboardButton(text="⬅️ Назад", callback_data=f"admin:user:{user_id}:apps:{page - 1}"))

    if count == 5:
        nav.append(
            InlineKeyboardButton(text="➡️ Далее", callback_data=f"admin:user:{user_id}:apps:{page + 1}"))

    return InlineKeyboardMarkup(inline_keyboard=[
        nav,
        [InlineKeyboardButton(text="⬅️ К пользователю", callback_data=f"admin:user:{user_id}")]
    ])


def variant_view_keyboard(variant: dict) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ Редактировать", callback_data=f"admin_variant:edit:{variant['variant_key']}")
    toggle_to = 0 if variant["is_active"] else 1
    toggle_text = "🔴 Выключить" if variant["is_active"] else "🟢 Включить"
    kb.button(text=toggle_text, callback_data=f"admin_variant:toggle:{variant['variant_key']}:{toggle_to}")
    add_back_button(kb)
    kb.adjust(1)
    return kb.as_markup()


def confirm_keyboard(builder: InlineKeyboardBuilder):
    builder.button(text="✅ Да", callback_data="confirm_yes")
    builder.button(text="❌ Отмена", callback_data="confirm_no")
    builder.adjust(2)
    return builder


def add_back_button(kb: Union[InlineKeyboardMarkup, InlineKeyboardBuilder], back_data: str = "admin:back") -> InlineKeyboardMarkup:
    if isinstance(kb, InlineKeyboardBuilder):
        kb.button(text="⬅️ Назад", callback_data=back_data)
        kb.adjust(1)
        return kb.as_markup()
    
    builder = InlineKeyboardBuilder.from_markup(kb)
    builder.button(text="⬅️ Назад", callback_data=back_data)
    builder.adjust(1)
    return builder.as_markup()
