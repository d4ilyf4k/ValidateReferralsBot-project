from database.db_manager import get_user_banks, update_financial_field
import json

PAYMENT_RULES = {
    "t-bank": {
        "referrer_bonus": 3000,
        "referral_bonus": 500,
        "conditions": {
            "card_activated": True,
            "purchase_made": True
        }
    },
    "alpha": {
        "referrer_bonus": 2000,
        "referral_bonus": 500,
        "conditions": {
            "card_activated": True,
            "purchase_made": False
        }
    }
}


def calculate_your_bonus(bank: str) -> int:
    return PAYMENT_RULES.get(bank, {}).get("referrer_bonus", 0)

def is_bonus_confirmed(bank: str, card_activated: bool, purchase_made: bool) -> bool:
    if bank == "t-bank":
        return card_activated and purchase_made
    elif bank == "alpha":
        return card_activated
    return False

async def recalculate_all_bonuses(user_id: int):
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

        # ПРАВИЛЬНО получаем бонусы
        referral_bonus = get_referral_bonus(bank)      # бонус реферала = 500
        your_bonus = calculate_your_bonus(bank)        # ваш бонус = 3000/2000
        confirmed = is_bonus_confirmed(bank, card_activated, purchase_made)

        bonus_details[bank] = {
            "referral_bonus": referral_bonus,  # 500
            "your_bonus": your_bonus,          # 3000/2000
            "confirmed": confirmed
        }

        total_referral_bonus += referral_bonus  # суммируем бонусы реферала
        total_your_bonus += your_bonus          # суммируем ваши бонусы
        
        if not confirmed:
            all_confirmed = False

    await update_financial_field(user_id, "total_referral_bonus", total_referral_bonus)
    await update_financial_field(user_id, "total_your_bonus", total_your_bonus)
    await update_financial_field(user_id, "total_bonus_status", "confirmed" if all_confirmed else "pending")
    await update_financial_field(user_id, "bonus_details", json.dumps(bonus_details))
    
    print(f"💰 Пересчитаны бонусы для user_id={user_id}:")
    print(f"   Банки: {banks}")
    print(f"   total_referral_bonus (бонус реферала) = {total_referral_bonus}")
    print(f"   total_your_bonus (ваш бонус) = {total_your_bonus}")
    print(f"   Статус: {'confirmed' if all_confirmed else 'pending'}")

def get_referral_bonus(bank: str) -> int:
    return PAYMENT_RULES.get(bank, {}).get("referral_bonus", 0)