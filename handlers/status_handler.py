from aiogram import Router, F, types
from aiogram.filters import Command
from database.db_manager import get_user_full_data, get_user_banks
from services.bonus_calculator import is_bonus_confirmed, get_referral_bonus

router = Router()

@router.message(F.text == "📊 Статус заявки")
async def user_status(message: types.Message):
    user_id = message.from_user.id
    user_banks = await get_user_banks(user_id)
    if not user_banks:
        await message.answer("Сначала завершите регистрацию с помощью /start.")
        return
    
    status_messages = []
    
    for bank in user_banks:
        data = await get_user_full_data(user_id)
        if not data:
            continue
        bank_name = "Т-Банк" if bank == "t-bank" else "Альфа-Банк"
        card_activated = bool(data.get("card_activated", False))
        purchase_made = bool(data.get("purchase_made", False))
        card_status = "✅ Активирована" if card_activated else "❌ Не активирована"
        purchase_status = "✅ Совершена" if purchase_made else "❌ Не совершена"
        referral_bonus = get_referral_bonus(bank)
        bonus_confirmed = is_bonus_confirmed(
            bank=bank,
            card_activated=card_activated,
            purchase_made=purchase_made
        )
        bonus_status = "✅ Подтверждён" if bonus_confirmed else "⏳ Ожидает"
        status_messages.append(
            f"🏦 <b>{bank_name}</b>\n"
            f"🔓 <b>Активация карты:</b> {card_status}\n"
            f"💳 <b>Первая покупка:</b> {purchase_status}\n"
            f"💰 <b>Ваш бонус:</b> {referral_bonus:,} руб.\n"
            f"📊 <b>Статус бонуса:</b> {bonus_status}\n"
        )
    if status_messages:
        full_message = (
            "📋 <b>Статус ваших заявок</b>\n\n" +
            "\n\n".join(status_messages) +
            "\n\n💡 <i>Бонус подтверждается автоматически при выполнении условий.</i>"
        )
        await message.answer(full_message, parse_mode="HTML")
    else:
        await message.answer("Не удалось получить данные по вашим банкам.")