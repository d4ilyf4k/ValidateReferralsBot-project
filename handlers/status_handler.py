from aiogram import Router, F, types

from database.db_manager import get_user_full_data, get_user_products
from services.bonus_calculator import is_bonus_confirmed

router = Router()


@router.message(F.text == "📊 Статус заявки")
async def user_status(message: types.Message):
    user_id = message.from_user.id

    user_data = await get_user_full_data(user_id)
    if not user_data:
        await message.answer("Сначала завершите регистрацию с помощью /start.")
        return

    user_products = await get_user_products(user_id)
    if not user_products:
        await message.answer("У вас пока нет оформленных продуктов.")
        return

    # ⚠️ Пока статусы глобальные (на будущее — перенос в продукты)
    card_activated = bool(user_data.get("card_activated"))
    purchase_made = bool(user_data.get("purchase_made"))

    status_blocks = []

    for product in user_products:
        bank = product["bank"]
        product_name = product["product_name"]
        bonus_amount = product.get("referral_bonus")

        bank_name = {
            "t-bank": "Т-Банк",
            "alpha": "Альфа-Банк"
        }.get(bank, bank)

        confirmed = is_bonus_confirmed(
            bank=bank,
            card_activated=card_activated,
            purchase_made=purchase_made
        )

        status_blocks.append(
            f"🏦 <b>{bank_name}</b>\n"
            f"📦 <b>Продукт:</b> {product_name}\n"
            f"🔓 <b>Активация карты:</b> {'✅ Да' if card_activated else '❌ Нет'}\n"
            f"💳 <b>Первая покупка:</b> {'✅ Да' if purchase_made else '❌ Нет'}\n"
            f"💰 <b>Бонус от банка:</b> {bonus_amount or '—'} ₽\n"
            f"📊 <b>Статус бонуса:</b> {'✅ Подтверждён' if confirmed else '⏳ Ожидает'}"
        )

    full_text = (
        "📋 <b>Статус ваших заявок</b>\n\n"
        + "\n\n".join(status_blocks)
        + "\n\n💡 <i>Бонус подтверждается после выполнения условий банка.</i>"
    )

    await message.answer(full_text, parse_mode="HTML")
