from database.db_manager import get_user_banks, update_financial_field

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

async def recalculate_all_bonuses(user_id: int):
    """
    Пересчитывает бонусы по ВСЕМ выбранным банкам пользователя.
    """
    banks = await get_user_banks(user_id)
    
    total_referral_bonus = 0
    total_your_bonus = 0
    all_confirmed = True

    bonus_details = {}

    for bank in banks:
        from database.db_manager import get_user_full_data
        user_data = await get_user_full_data(user_id)
        if not user_data:
            continue

        card_activated = bool(user_data.get("card_activated"))
        purchase_made = bool(user_data.get("purchase_made"))

        referral_bonus = get_referral_bonus(bank)
        your_bonus = calculate_your_bonus(bank)
        confirmed = is_bonus_confirmed(bank, card_activated, purchase_made)

        bonus_details[bank] = {
            "referral_bonus": referral_bonus,
            "your_bonus": your_bonus,
            "confirmed": confirmed
        }

        total_referral_bonus += referral_bonus
        total_your_bonus += your_bonus
        if not confirmed:
            all_confirmed = False

    await update_financial_field(user_id, "total_referral_bonus", total_referral_bonus)
    await update_financial_field(user_id, "total_your_bonus", total_your_bonus)
    await update_financial_field(user_id, "total_bonus_status", "confirmed" if all_confirmed else "pending")

    import json
    await update_financial_field(user_id, "bonus_details", json.dumps(bonus_details))

def get_referral_bonus(bank: str) -> int:
    """
    Возвращает размер бонуса реферала в зависимости от банка.
    
    Args:
        bank (str): Код банка ('t-bank' или 'alpha').
    
    Returns:
        int: Сумма бонуса реферала в рублях.
    """
    return PAYMENT_RULES.get(bank, {}).get("referral_bonus", 0)