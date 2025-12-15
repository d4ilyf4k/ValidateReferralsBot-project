from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
    )

def get_start_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Начать регистрацию")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_phone_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Отправить номер", request_contact=True)]],
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

def get_bank_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🏦Т-Банк")],
            [KeyboardButton(text="🏦Альфа-Банк")]
        ],
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
        [InlineKeyboardButton(text="📊 Дашборд", callback_data="admin_dashboard")],
        [InlineKeyboardButton(text="📤 Полный отчёт (JSON)", callback_data="admin_report")],
        [InlineKeyboardButton(text="🔗 Обновить реф. ссылки", callback_data="admin_update_links")]
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
        [
            InlineKeyboardButton(text="❌ Нет, отклонить", callback_data="disagree_conditions")
        ]
    ])

def get_detailed_conditions_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Принимаю условия", callback_data="agree_conditions")],
        [InlineKeyboardButton(text="↩️ Назад к условиям", callback_data="back_to_main")]],
    )