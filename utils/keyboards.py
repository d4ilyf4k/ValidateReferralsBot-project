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

def get_skip_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Пропустить")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_user_main_menu_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🏦 Выбрать банк")],
            [KeyboardButton(text="ℹ️ Помощь"), KeyboardButton(text="💰 Финансовый отчёт")],
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
    
def get_bank_selection_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🏦Т-Банк")],
            [KeyboardButton(text="🏦Альфа-Банк")],
            [KeyboardButton(text="↩️ Назад в меню")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_edit_profile_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ ФИО", callback_data="edit_full_name")],
        [InlineKeyboardButton(text="✏️ Номер", callback_data="edit_phone")],
        [InlineKeyboardButton(text="✏️ Банк", callback_data="edit_bank")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_edit")]
    ])


def get_admin_panel_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Дашборд", callback_data="admin_dashboard"),
        InlineKeyboardButton(text="📤 Полный отчёт (JSON)", callback_data="admin_report")],
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users"),
        InlineKeyboardButton(text="🧩 Управление каталогом", callback_data="admin:catalog")],
        [InlineKeyboardButton(text="🔗 Обновить реф. ссылки", callback_data="admin_update_links")]
    ])


# =========================
# Главное меню продукта
# =========================
def admin_product_menu(bank_key: str, product_key: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🎯 Офферы продукта", callback_data=f"admin_offer:open:product:{product_key}")
    kb.button(text="🧩 Варианты", callback_data=f"admin_variant:list:{product_key}")
    kb.button(text="⬅️ Назад", callback_data=f"admin_bank:open:{bank_key}")
    kb.adjust(1)  # 1 кнопка в ряд
    return kb.as_markup()

# =========================
# Главное меню варианта
# =========================
def admin_variant_menu(product_key: str, variant_key: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🎯 Офферы варианта", callback_data=f"admin_offer:open:variant:{variant_key}")
    kb.button(text="⬅️ Назад", callback_data=f"admin_product:open:{product_key}")
    kb.adjust(1)
    return kb.as_markup()


def get_admin_products_kb(bank_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить продукт", callback_data=f"admin_product:add:{bank_key}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:catalog:banks")]
    ])


def get_products_toggle_kb(products: list[dict], bank_key: str) -> InlineKeyboardMarkup:
    keyboard = []

    for p in products:
        status = "🟢" if p["is_active"] else "🔴"
        keyboard.append([
            InlineKeyboardButton(
                text=f"{status} {p['product_name']} / {p['product_key']}",
                callback_data=f"admin_product:open:{p['product_key']}"  # открывает конкретный продукт
            )
        ])

    keyboard.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data=f"admin_bank:open:{bank_key}")
    ])


def get_admin_dashboard_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Финансы", callback_data="admin:finance")],
        [InlineKeyboardButton(text="📈 Трафик", callback_data="admin:traffic")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")]
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

        
def get_tbank_product_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔷 Т-Банк Black", callback_data="tbank_black")],
        [InlineKeyboardButton(text="🏆 Premium", callback_data="tbank_premium")],
        [InlineKeyboardButton(text="🚗 Drive", callback_data="tbank_drive")],
        [InlineKeyboardButton(text="📱 T-Мобайл", callback_data="tbank_mobile")],
        [InlineKeyboardButton(text="↩️ Назад к выбору банка", callback_data="back_to_banks")]
    ])

def get_black_subtype_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔷 Классическая", callback_data="black_classic")],
        [InlineKeyboardButton(text="🌸 Аромакарта", callback_data="black_aroma")],
        [InlineKeyboardButton(text="🎓 Молодёжная", callback_data="black_youth")],
        [InlineKeyboardButton(text="📼 Ретро", callback_data="black_retro")],
    ])
    
def get_agreement_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, согласен", callback_data="agree_conditions"),
            InlineKeyboardButton(text="📖 Подробнее", callback_data="show_details")
        ],
        [InlineKeyboardButton(text="❌ Нет, отклонить", callback_data="disagree_conditions")]
    ])

def get_detailed_conditions_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Принимаю условия", callback_data="agree_conditions")],
        [InlineKeyboardButton(text="↩️ Назад к условиям", callback_data="back_to_main")]],
    )

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
    
def get_admin_offers_list_kb(offers: list[dict]) -> InlineKeyboardMarkup:
    keyboard = []

    for o in offers:
        status = "🟢" if o["is_active"] else "🔴"
        keyboard.append([
            InlineKeyboardButton(
                text=f"{status} {o['offer_title']}",
                callback_data=f"admin_offer:view:{o['id']}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(text="➕ Добавить оффер", callback_data="admin_offer:add")
    ])
    keyboard.append([
        InlineKeyboardButton(text="⬅️ Назад к варианту", callback_data="admin:back")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_admin_offer_card_kb(offer_id: int, is_active: bool) -> InlineKeyboardMarkup:
    toggle_text = "🔴 Выключить" if is_active else "🟢 Включить"

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"admin_offer:edit:{offer_id}")],
        [InlineKeyboardButton(text=toggle_text, callback_data=f"admin_offer:toggle:{offer_id}")],
        [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"admin_offer:delete:{offer_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_offer:back")]
    ])


def variants_keyboard(variants: list[dict]):
    kb = InlineKeyboardBuilder()
    for v in variants:
        status = "🟢" if v["is_active"] else "🔴"
        kb.button(
            text=f"{status} {v['title']}",
            callback_data=f"admin_variant:view:{v['variant_key']}"
        )
    kb.button(text="➕ Добавить вариант", callback_data="admin_variant:add")
    add_back_button(kb)
    kb.adjust(1)
    return kb.as_markup()

def variant_view_keyboard(variant: dict) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🎯 Офферы", callback_data="admin_offer:list")
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
