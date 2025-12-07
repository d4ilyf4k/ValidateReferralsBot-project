from aiogram import Router, F, types
from aiogram.filters import Command
from database.db_manager import get_user_full_data
from services.bonus_calculator import is_bonus_confirmed, get_referral_bonus

router = Router()

@router.message(F.text == "📊 Статус заявки")
async def user_status(message: types.Message):
    data = await get_user_full_data(message.from_user.id)
    if not data:
        await message.answer("Сначала завершите регистрацию с помощью /start.")
        return

    bank_name = "Т-Банк" if data["bank"] == "t-bank" else "Альфа-Банк"

    card_activated = bool(data.get("card_activated", False))
    purchase_made = bool(data.get("purchase_made", False))

    card_status = "✅ Активирована" if card_activated else "❌ Не активирована"
    purchase_status = "✅ Совершена" if purchase_made else "❌ Не совершена"

    referral_bonus = get_referral_bonus(data["bank"])
    
    bonus_confirmed = is_bonus_confirmed(
        bank=data["bank"],
        card_activated=card_activated,
        purchase_made=purchase_made
    )
    bonus_status = "✅ Подтверждён" if bonus_confirmed else "⏳ Ожидает"

    status_message = (
        "📋 <b>Статус вашей заявки</b>\n\n"
        f"🏦 <b>Банк:</b> {bank_name}\n"
        f"🔓 <b>Активация карты:</b> {card_status}\n"
        f"💳 <b>Первая покупка:</b> {purchase_status}\n\n"
        f"💰 <b>Ваш бонус:</b> {referral_bonus:,} руб.\n"
        f"📊 <b>Статус бонуса:</b> {bonus_status}\n\n"
        "💡 <i>Бонус подтверждается автоматически при выполнении условий.</i>"
    )
    
    await message.answer(status_message, parse_mode="HTML")