import logging
from config import settings
from aiogram import Router, F, types
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from database.db_manager import (
    update_referral_link,
    delete_user_all_data,
    upsert_offer,
)
from utils.keyboards import get_start_kb, get_admin_panel_kb


router = Router()
logger = logging.getLogger(__name__)


NPD_RATE = 0.06

SUPPORTED_BANKS = {
    "t-bank": "Т-Банк",
    "alpha": "Альфа-Банк"
}


def is_admin(user_id: int) -> bool:
    return user_id in settings.ADMIN_IDS

@router.callback_query(F.data == "admin_panel")
async def admin_panel(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🛠 <b>Админ-меню</b>",
        reply_markup=get_admin_panel_kb(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "admin_update_links")
async def handle_update_link_button(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("🚫 Доступ запрещён.", show_alert=True)
        return

    await callback.answer()
    await callback.message.answer(
    "📌 Отправьте команду в формате:\n"
    "<code>/update_link [банк] [продукт] [ссылка] [utm-параметры...]</code>\n\n"

    "<b>Примеры:</b>\n"
    "<code>/update_link t-bank black_aroma https://www.tbank.ru/finance/blog/aroma-black/ "
    "utm_source=ValidateReferrals_Bot utm_medium=telegram utm_campaign=black_aroma</code>\n\n"

    "<code>/update_link t-bank black_drive https://www.tbank.ru/cards/debit-cards/drive/promo/form/short/partners/ "
    "utm_source=ValidateReferrals_Bot utm_medium=telegram utm_campaign=black_drive</code>\n\n"

    "<code>/update_link alpha main https://alfabank.ru/ref?partner=123 "
    "utm_source=ValidateReferrals_Bot utm_medium=telegram utm_campaign=alpha_main</code>\n\n"

    "При добавлении или обновлении реферальной ссылки\n"
    "используйте стандартные UTM-метки без вложенных параметров.\n\n"

    "<b>Рекомендуемый формат:</b>\n\n"
    "utm_source   — источник трафика\n"
    "  Пример: <code>ValidateReferrals_Bot</code>\n\n"

    "utm_medium   — тип канала\n"
    "  Пример: <code>telegram</code>\n\n"

    "utm_campaign — кампания или оффер\n"
    "  Пример: <code>black_golden_ticket_dec25</code>\n\n"

    "<b>Пример корректной ссылки:</b>\n"
    "<code>https://example.com/offer?"
    "utm_source=ValidateReferrals_Bot"
    "&utm_medium=telegram"
    "&utm_campaign=black_golden_ticket_dec25</code>\n\n"

    "❗ <b>Не используйте значения вида:</b>\n"
    "<code>utm_source=utm_source=...</code>\n"
    "<code>utm_medium=utm_medium=...</code>\n\n"

    "<b>Поддерживаемые банки:</b> <code>t-bank</code>, <code>alpha</code>\n\n"
    "<b>Продукты для t-bank:</b>\n"
    "• <code>black_classic</code> — обычная Black\n"
    "• <code>black_aroma</code> — аромакарта\n"
    "• <code>black_youth</code> — молодёжная\n"
    "• <code>black_retro</code> — ретро\n"
    "• <code>black_drive</code> — карта для авто\n"
    "• <code>black_premium</code> — премиальная карта\n"
    "• <code>main</code> — fallback (для alpha или общих ссылок)",
    parse_mode="HTML"
)



@router.message(Command("update_link"))
async def cmd_update_link(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("🚫 Доступ запрещён.")
        return

    try:
        parts = message.text.split()
        if len(parts) < 7:
            await message.answer("Формат: /update_link банк продукт url utm_source utm_medium utm_campaign")
            return
        
        bank = parts[1]          # t-bank или alpha
        product_key = parts[2]   # black_classic, alpha_debit и т.д.
        base_url = parts[3]      # URL
        utm_source = parts[4]    # telegram
        utm_medium = parts[5]    # referral  
        utm_campaign = parts[6]  # default
        
        success = await update_referral_link(
            bank=bank,
            product_key=product_key,
            base_url=base_url,
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
        )
        
        if success:
            await message.answer(f"✅ Ссылка для {bank}/{product_key} обновлена!")
        else:
            await message.answer("❌ Ошибка при обновлении ссылки")
            
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}")

@router.message(Command("set_offer_bonus"))
async def cmd_set_offer_bonus(message: Message):
    if message.from_user.id not in settings.ADMIN_IDS:
        await message.answer("🚫 Команда доступна только администратору.")
        return

    args = message.text.split()
    if len(args) != 4:
        await message.answer(
            "❌ Неверный формат.\n\n"
            "<code>/set_offer_bonus [банк] [продукт] [сумма]</code>\n\n"
            "<b>Примеры:</b>\n"
            "<code>/set_offer_bonus t-bank black_youth 3000</code>\n"
            "<code>/set_offer_bonus alpha debit 1500</code>",
            parse_mode="HTML"
        )
        return

    bank = args[1].lower()
    product_key = args[2].lower()

    if bank not in SUPPORTED_BANKS:
        await message.answer(
            f"❌ Неизвестный банк.\n"
            f"Доступны: {', '.join(SUPPORTED_BANKS.keys())}"
        )
        return

    try:
        gross_bonus = int(args[3])
        if gross_bonus <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Сумма должна быть положительным целым числом.")
        return

    # Пока product_name = product_key (позже можно сделать словарь)
    product_name = product_key.replace("_", " ").title()

    await upsert_offer(
        bank=bank,
        product_key=product_key,
        product_name=product_name,
        gross_bonus=gross_bonus
    )

    net_bonus = int(gross_bonus * (1 - NPD_RATE))

    await message.answer(
        "✅ <b>Оффер обновлён</b>\n\n"
        f"🏦 <b>Банк:</b> {SUPPORTED_BANKS[bank]}\n"
        f"📦 <b>Продукт:</b> <code>{product_key}</code>\n"
        f"💰 <b>Брутто:</b> {gross_bonus:,} ₽\n"
        f"🧾 <b>НПД 6%:</b> {gross_bonus - net_bonus:,} ₽\n"
        f"✅ <b>Нетто:</b> {net_bonus:,} ₽",
        parse_mode="HTML"
    )


    
@router.message(Command("delete_data"))
async def cmd_delete_data(message: types.Message, state: FSMContext):
    """
    DEV-ONLY.
    Используется администратором для тестирования онбординга.
    В проде подлежит удалению или ограничению.
    """
    if not is_admin(message.from_user.id):
        await message.answer("🚫 Доступ запрещён.")
        return
    
    user_id = message.from_user.id

    success = await delete_user_all_data(user_id)
    if success:
        await message.answer(
            "✅ Ваши данные удалены. Вы можете начать регистрацию заново.",
            reply_markup=get_start_kb()
        )
        await state.clear()
    else:
        await message.answer(
            "Вы не найдены в базе данных. Нажмите «Начать регистрацию», чтобы создать профиль.",
            reply_markup=get_start_kb()
        )