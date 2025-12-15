from database.db_manager import (
    get_user_products,
    get_user_full_data,
    get_offer_bonus,
    get_db_connection
)
import json

NPD_RATE = 0.06

PAYMENT_RULES = {
    "t-bank": {
        "conditions": {
            "card_activated": True,
            "purchase_made": True
        }
    },
    "alpha": {
        "conditions": {
            "card_activated": True,
            "purchase_made": False
        }
    }
}


def is_bonus_confirmed(bank: str, card_activated: bool, purchase_made: bool) -> bool:
    rules = PAYMENT_RULES.get(bank)
    if not rules:
        return False

    cond = rules["conditions"]

    if cond.get("card_activated") and not card_activated:
        return False
    if cond.get("purchase_made") and not purchase_made:
        return False

    return True


async def recalculate_all_bonuses(user_id: int) -> None:
    user_products = await get_user_products(user_id)
    user_data = await get_user_full_data(user_id)

    if not user_products or not user_data:
        return

    card_activated = bool(user_data.get("card_activated"))
    purchase_made = bool(user_data.get("purchase_made"))

    total_referrer_bonus = 0
    all_confirmed = True
    bonus_details = {}

    for item in user_products:
        bank = item["bank"]
        product_key = item["product_key"]
        product_name = item["product_name"]

        gross_bonus = await get_offer_bonus(bank, product_key)
        if not gross_bonus:
            continue

        confirmed = is_bonus_confirmed(
            bank=bank,
            card_activated=card_activated,
            purchase_made=purchase_made
        )

        net_bonus = int(gross_bonus * (1 - NPD_RATE))

        bonus_details[product_key] = {
            "bank": bank,
            "product_name": product_name,
            "gross_bonus": gross_bonus,
            "net_bonus": net_bonus,
            "confirmed": confirmed
        }

        if confirmed:
            total_referrer_bonus += net_bonus
        else:
            all_confirmed = False

    async with get_db_connection() as db:
        await db.execute("""
            UPDATE financial_data
            SET
                total_referrer_bonus = ?,
                bonus_details = ?
            WHERE user_id = ?
        """, (
            total_referrer_bonus,
            "confirmed" if all_confirmed else "pending",
            json.dumps(bonus_details, ensure_ascii=False),
            user_id
        ))
        await db.commit()

    print(f"💰 Бонусы пересчитаны для user_id={user_id}")

