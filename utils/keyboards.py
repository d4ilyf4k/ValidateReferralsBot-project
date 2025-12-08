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

def get_bank_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🏦Т-Банк")],
            [KeyboardButton(text="🏦Альфа-Банк")]
        ],
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
            [KeyboardButton(text="ℹ️ Помощь"), KeyboardButton(text="📊 Статус заявки")],
            [KeyboardButton(text="🏦 Выбрать банк"), KeyboardButton(text="💰 Финансовый отчёт")],
            [KeyboardButton(text="✏️ Редактировать профиль"), KeyboardButton(text="🗑 Очистить историю")]
        ],
        resize_keyboard=True
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

def get_admin_main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статус заявки", callback_data="menu_status")],
        [InlineKeyboardButton(text="🔍 Отчёт по рефералу", callback_data="admin_finance_referral")],
        [InlineKeyboardButton(text="🔧 Админка", callback_data="menu_admin")]
    ])
    
def get_edit_profile_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ ФИО", callback_data="edit_full_name")],
        [InlineKeyboardButton(text="✏️ Номер", callback_data="edit_phone")],
        [InlineKeyboardButton(text="✏️ Банк", callback_data="edit_bank")],
        [InlineKeyboardButton(text="✏️ Активация карты", callback_data="edit_card_activated")],
        [InlineKeyboardButton(text="✏️ Первая покупка", callback_data="edit_purchase_made")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_edit")]
    ])

def get_yes_no_kb(prefix: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data=f"yesno_{prefix}_yes"),
            InlineKeyboardButton(text="❌ Нет", callback_data=f"yesno_{prefix}_no")
        ]
    ])
            
    
def get_admin_panel_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Полный отчёт (JSON)", callback_data="admin_report")],
        [InlineKeyboardButton(text="🔗 Обновить реф. ссылки", callback_data="admin_update_links")],
        [InlineKeyboardButton(text="🔍 Найти реферала", callback_data="admin_find_phone")],
        [InlineKeyboardButton(text="📨 Отправить напоминание", callback_data="admin_remind")],
        [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="admin_back")]
        ])

def get_agreement_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, согласен", callback_data="agree_conditions"),
            InlineKeyboardButton(text="📖 Подробнее", callback_data="show_details")
        ],
        [
            InlineKeyboardButton(text="❌ Нет, отклонить", callback_data="disagree_conditions")
        ]],
        resize_keyboard=True,
        one_time_keyboard=True                            
    )

def get_detailed_conditions_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Принимаю условия", callback_data="agree_conditions")],
        [InlineKeyboardButton(text="↩️ Назад к условиям", callback_data="back_to_main")]],
        resize_keyboard=True,
    )