import json
from database.db_manager import decrypt_phone, get_all_referrals_data
from services.bonus_calculator import is_bonus_confirmed, calculate_your_bonus

def format_optional_date(date_val):
    if not date_val:
        return "—"
    if isinstance(date_val, str):
        try:
            year, month, day = date_val.split("-")
            return f"{day}.{month}.{year}"
        except:
            return str(date_val)
    return str(date_val)

def generate_referral_json(user_data: dict) -> str:
    try:
        phone = decrypt_phone(user_data["phone_enc"])
    except Exception:
        phone = "[ошибка расшифровки]"

    bank = user_data["bank"]
    your_bonus = 500 if bank == "t-bank" else 700
    referral_bonus = 1000 if bank == "t-bank" else 1500

    card_activated = bool(user_data.get("card_activated", False))
    purchase_made = bool(user_data.get("purchase_made", False))
    
    if bank == "t-bank":
        bonus_confirmed = card_activated and purchase_made
    else:  # alpha
        bonus_confirmed = card_activated

    report = {
        "personal_info": {
            "full_name": user_data["full_name"],
            "phone": phone,
            "bank": bank,
        },
        "application_status": {
            "card_activated": card_activated,
            "purchase_made": purchase_made
        },
        "financial_info": {
            "total_referral_bonus": referral_bonus,
            "referral_bonus_received": bonus_confirmed,  # или отдельное поле даты
            "total_your_bonus": your_bonus,
            "your_bonus_status": "confirmed" if bonus_confirmed else "pending"
        }
    }
    return json.dumps(report, ensure_ascii=False, indent=2)

async def generate_full_json_report() -> str:
    referrals = await get_all_referrals_data()
    result = []

    for ref in referrals:
        try:
            phone = decrypt_phone(ref["phone_enc"])
        except Exception:
            phone = "[ошибка расшифровки]"

        bank = ref["bank"]
        your_bonus = 500 if bank == "t-bank" else 700
        referral_bonus = 1000 if bank == "t-bank" else 1500

        card_activated = bool(ref.get("card_activated", False))
        purchase_made = bool(ref.get("purchase_made", False))

        if bank == "t-bank":
            bonus_confirmed = card_activated and purchase_made
        else:  # alpha
            bonus_confirmed = card_activated

        result.append({
            "personal_info": {
                "full_name": ref["full_name"],
                "phone": phone,
                "bank": bank,
            },
            "application_status": {
                "card_activated": card_activated,
                "purchase_made": purchase_made
            },
            "financial_info": {
                "total_referral_bonus": referral_bonus,
                "referral_bonus_received": bonus_confirmed,
                "total_your_bonus": your_bonus,
                "your_bonus_status": "confirmed" if bonus_confirmed else "pending"
            }
        })

    return json.dumps(result, ensure_ascii=False, indent=2)

async def generate_referral_text_report_with_conditions(user_data: dict) -> str:

    try:
        phone = decrypt_phone(user_data["phone_enc"])
    except Exception:
        phone = "[ошибка расшифровки]"

    from database.db_manager import get_user_banks
    banks = await get_user_banks(user_data["user_id"])
    if not banks:
        banks = [user_data.get("bank", "t-bank")]  # fallback для старых пользователей

    bonus_lines = []
    total_bonus = 0

    for bank in banks:
        bank_name = "Т-Банк" if bank == "t-bank" else "Альфа-Банк"
        card_activated = bool(user_data.get("card_activated", False))
        purchase_made = bool(user_data.get("purchase_made", False))
        confirmed = is_bonus_confirmed(bank, card_activated, purchase_made)
        bonus = calculate_your_bonus(bank)
        status = "✅ Подтверждён" if confirmed else "⏳ Ожидает"
        bonus_lines.append(f"• {bank_name}: {bonus} ₽ ({status})")
        if confirmed:
            total_bonus += bonus

    bank_display = ", ".join(["Т-Банк" if b == "t-bank" else "Альфа-Банк" for b in banks])

    card_activated = bool(user_data.get("card_activated", False))
    purchase_made = bool(user_data.get("purchase_made", False))
    your_bonus = total_bonus
    your_status = "✅ Подтверждён" if total_bonus > 0 else "⏳ Ожидает"

    if "t-bank" in banks and "alpha" in banks:
        conditions_text = (
            "💰 <b>Ваш бонус: 1000₽</b>\n"
            "Чтобы бонус зачислился:\n"
            "• Т-Банк: активация + покупка от 500₽\n"
            "• Альфа-Банк: активация + любая покупка\n\n"
            "✅ Бонусы приходят в течение 3–14 дней."
        )

    elif "t-bank" in banks:
        conditions_text = (
            "💰 <b>Ваш бонус: 500₽</b>\n\n"
            "Чтобы бонус зачислился:\n"
            "1️⃣ Активируйте карту\n"
            "2️⃣ Совершите покупку на сумму <b>от 500 рублей</b>\n\n"
            "✅ Бонус приходит в течение 5–10 дней."
        )
    else:
        conditions_text = (
            "💰 <b>Ваш бонус: 500₽</b>\n\n"
            "Чтобы бонус зачислился:\n"
            "1️⃣ Получите и активируйте карту\n"
            "2️⃣ Совершите покупку на <b>любую сумму</b>\n\n"
            "✅ Бонус приходит в течение 3–14 дней."
        )

    status_card = "✅ Активирована" if user_data.get("card_activated") else "❌ Не активирована"
    status_purchase = "✅ Совершена" if user_data.get("purchase_made") else "❌ Не совершена"

    return (
        f"📋 <b>Ваша заявка</b>\n\n"
        f"👤 <b>ФИО:</b> {user_data['full_name']}\n"
        f"📞 <b>Телефон:</b> <code>{phone}</code>\n"
        f"🏦 <b>Банк:</b> {bank_display}\n\n"
        f"🔓 <b>Активация карты:</b> {status_card}\n"
        f"💳 <b>Первая покупка:</b> {status_purchase}\n\n"
        f"{conditions_text}\n\n"
        f"💎 <b>Итоговый бонус</b>: {your_bonus} руб. ({your_status})"
    )