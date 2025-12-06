from database.db_manager import get_user_full_data, update_financial_field

"""
Модуль для расчёта реферальных бонусов по программам Т-Банка и Альфа-Банка.
Содержит бизнес-логику, независимую от Telegram и базы данных.
"""

PAYMENT_RULES = {
    "t-bank": {
        "referrer_bonus": 500,
        "referral_bonus": 1000,
        "conditions": {
            "card_activated": True,
            "purchase_made": True
        }
    },
    "alpha": {
        "referrer_bonus": 700,
        "referral_bonus": 1500,
        "conditions": {
            "card_activated": True,
            "purchase_made": False  # Покупка не требуется
        }
    }
}


def calculate_your_bonus(bank: str) -> int:
    """
    Возвращает размер вашего вознаграждения (реферера) в зависимости от банка.
    
    Args:
        bank (str): Код банка ('t-bank' или 'alpha').
    
    Returns:
        int: Сумма бонуса в рублях.
    """
    return PAYMENT_RULES.get(bank, {}).get("referrer_bonus", 0)


def is_bonus_confirmed(bank: str, card_activated: bool, purchase_made: bool) -> bool:
    if bank == "t-bank":
        return card_activated and purchase_made
    elif bank == "alpha":
        return card_activated
    return False

def calculate_your_bonus(bank: str) -> int:
    return 500 if bank == "t-bank" else 500

async def recalculate_bonus(user_id: int) -> None:
    user_data = await get_user_full_data(user_id)
    if not user_data:
        return  # Пользователь не найден

    bank = user_data["bank"]
    card_activated = bool(user_data.get("card_activated", False))
    purchase_made = bool(user_data.get("purchase_made", False))

    bonus_amount = calculate_your_bonus(bank)
    bonus_confirmed = is_bonus_confirmed(bank, card_activated, purchase_made)
    bonus_status = "confirmed" if bonus_confirmed else "pending"

    # Сохраняем ОБЕ суммы: и для реферала, и для вас
    await update_financial_field(user_id, "your_bonus_amount", bonus_amount)
    await update_financial_field(user_id, "your_bonus_status", bonus_status)

    # (Опционально) Обновите и бонус реферала
    referral_bonus = get_referral_bonus(bank)
    await update_financial_field(user_id, "referral_bonus_amount", referral_bonus)

def get_referral_bonus(bank: str) -> int:
    """
    Возвращает размер бонуса реферала в зависимости от банка.
    
    Args:
        bank (str): Код банка ('t-bank' или 'alpha').
    
    Returns:
        int: Сумма бонуса реферала в рублях.
    """
    return PAYMENT_RULES.get(bank, {}).get("referral_bonus", 0)