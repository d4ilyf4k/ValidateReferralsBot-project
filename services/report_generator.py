import json
from datetime import datetime
from database.db_manager import decrypt_phone, get_all_referrals_data, get_all_offer_net_bonuses
from services.bonus_calculator import is_bonus_confirmed, calculate_your_bonus

def generate_referral_json(user_data: dict) -> str:
    try:
        phone = decrypt_phone(user_data["phone_enc"])
    except Exception:
        phone = "[ошибка расшифровки]"

    bank = user_data["bank"]
    your_bonus = 500 if bank == "t-bank" else 500
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
            "referral_bonus_received": bonus_confirmed,
            "total_your_bonus": your_bonus,
            "your_bonus_status": "confirmed" if bonus_confirmed else "pending"
        }
    }
    return json.dumps(report, ensure_ascii=False, indent=2)

def format_optional_date(date_val):
    if not date_val:
        return "—"
    
    try:
        if isinstance(date_val, str) and len(date_val) == 10 and date_val.count('-') == 2:
            year, month, day = date_val.split('-')
            return f"{day}.{month}.{year}"
        
        elif isinstance(date_val, str) and len(date_val) == 10 and date_val.count('.') == 2:
            return date_val
        
        elif hasattr(date_val, "strftime"):
            return date_val.strftime("%d.%m.%Y")
        
        elif isinstance(date_val, str):
            return date_val
        
        else:
            return str(date_val)
            
    except Exception:
        return str(date_val)

async def generate_full_json_report() -> str:
    try:
        raw_data = await get_all_referrals_data(include_financial=True)
        if not raw_data:
            return json.dumps({
                "generated_at": datetime.now().isoformat(),
                "total_users": 0,
                "summary": {
                    "total_potential_earnings_gross": 0,
                    "total_potential_earnings_net": 0,
                    "total_confirmed_earnings_net": 0,
                    "total_referrals": 0
                },
                "users": []
            }, ensure_ascii=False, indent=2)

        offer_net_bonuses = await get_all_offer_net_bonuses()

        processed_users = []
        total_gross = 0
        total_net = 0
        total_confirmed_net = 0

        for row in raw_data:
            user = dict(row)
            
            phone_enc = user.get('phone_enc')
            if phone_enc:
                try:
                    user['phone'] = decrypt_phone(phone_enc)
                except Exception as e:
                    print(f"⚠️ Ошибка расшифровки телефона для user_id={user.get('user_id')}: {e}")
                    user['phone'] = "[ошибка расшифровки]"
            else:
                user['phone'] = "[нет телефона]"
            
            user.pop('phone_enc', None)

            banks = user.get('banks', [])
            if isinstance(banks, str):
                banks = banks.split(',') if banks else []
            user['banks'] = banks

            product_key = user.get('selected_product')
            potential_net = 0
            
            for bank in banks:
                key = (bank, product_key)
                net_bonus = offer_net_bonuses.get(key, 0)
                potential_net += net_bonus

            user['potential_earnings_net'] = potential_net
            total_net += potential_net

            gross_est = int(potential_net / 0.94) if potential_net else 0
            user['potential_earnings_gross'] = gross_est
            total_gross += gross_est

            confirmed_bonus = user.get('total_your_bonus', 0)
            if confirmed_bonus > 0:
                user['confirmed_earnings_net'] = confirmed_bonus
                total_confirmed_net += confirmed_bonus
            else:
                user['confirmed_earnings_net'] = 0

            user['bonus_status'] = "confirmed" if confirmed_bonus > 0 else "pending"

            date_fields = [
                'created_at', 
                'application_date', 
                'approval_date', 
                'card_received_date',
                'card_activated_date',
                'first_purchase_date',
                'sent_at'
            ]
            
            for date_field in date_fields:
                if date_field in user and user[date_field]:
                    date_value = str(user[date_field]).strip()
                    if date_value and date_value != 'None' and date_value != 'null':
                        user[date_field] = format_optional_date(date_value)
                    else:
                        user[date_field] = "—"
                elif date_field in user:
                    user[date_field] = "—"

            for key in ['selected_product', 'selected_product_name', 'bank', 'primary_bank']:
                user.pop(key, None)

            processed_users.append(user)

        result = {
            "generated_at": datetime.now().isoformat(),
            "total_users": len(processed_users),
            "summary": {
                "total_potential_earnings_gross": total_gross,
                "total_potential_earnings_net": total_net,
                "total_confirmed_earnings_net": total_confirmed_net,
                "total_referrals": len(processed_users)
            },
            "users": processed_users
        }

        return json.dumps(result, ensure_ascii=False, indent=2, default=str)

    except Exception as e:
        print(f"❌ Ошибка в generate_full_json_report: {e}")
        import traceback
        traceback.print_exc()
        raise

async def generate_referral_text_report_with_conditions(user_data: dict) -> str:

    try:
        phone = decrypt_phone(user_data["phone_enc"])
    except Exception:
        phone = "[ошибка расшифровки]"

    from database.db_manager import get_user_banks
    banks = await get_user_banks(user_data["user_id"])
    if not banks:
        banks = [user_data.get("bank", "t-bank")]

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