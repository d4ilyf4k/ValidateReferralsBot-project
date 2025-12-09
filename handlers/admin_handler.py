import logging
import json
from datetime import datetime
from config import settings
from aiogram import Router, F, types
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from aiogram.filters import Command
from typing import List
from services.report_generator import generate_full_json_report
from database.db_manager import (
    get_user_by_phone,
    log_reminder_sent,
    update_referral_link,
    delete_user_by_phone,
)
from utils.reminders import send_reminder_to_user

router = Router()
logger = logging.getLogger(__name__)

def is_admin(user_id: int) -> bool:
    return user_id in settings.ADMIN_IDS


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
        "<code>/update_link t-bank black_aroma https://www.tbank.ru/finance/blog/aroma-black/ utm_source=bot</code>\n"
        "<code>/update_link t-bank drive https://www.tbank.ru/cards/debit-cards/drive/promo/form/short/partners/ utm_medium=ref</code>\n"
        "<code>/update_link alpha main https://alfabank.ru/ref?partner=123</code>\n\n"

        "<b>Поддерживаемые банки:</b> <code>t-bank</code>, <code>alpha</code>\n"
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
async def cmd_update_link(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("🚫 У вас нет прав на эту команду.")
        return

    args: List[str] = message.text.split()
    if len(args) < 4:
        await message.answer(
            "❌ Неверный формат.\n"
            "Используйте:\n"
            "<code>/update_link [банк] [продукт] [ссылка] [utm-параметры...]</code>\n\n"
            "<b>Пример:</b>\n"
            "<code>/update_link t-bank black_aroma https://www.tbank.ru/finance/blog/aroma-black/ utm_source=bot</code>",
            parse_mode="HTML"
        )
        return

    bank = args[1]
    product_key = args[2]
    base_url = args[3]

    if bank not in {"t-bank", "alpha"}:
        await message.answer("🏦 Поддерживаемые банки: <code>t-bank</code>, <code>alpha</code>", parse_mode="HTML")
        return

    if not base_url.startswith(("http://", "https://")):
        await message.answer("🔗 Ссылка должна начинаться с <code>http://</code> или <code>https://</code>", parse_mode="HTML")
        return

    utm = {"utm_source": "telegram", "utm_medium": "referral", "utm_campaign": "default"}
    for param in args[4:]:
        if "=" in param:
            key, value = param.split("=", 1)
            if key in utm:
                utm[key] = value

    await update_referral_link(bank, product_key, base_url, utm["utm_source"], utm["utm_medium"], utm["utm_campaign"])

    bank_name = "Т-Банка" if bank == "t-bank" else "Альфа-Банка"
    await message.answer(
        f"✅ Ссылка для {bank_name} обновлена!\n\n"
        f"<b>Продукт:</b> <code>{product_key}</code>\n"
        f"<b>Источник:</b> <code>{utm['utm_source']}</code>\n"
        f"<b>Медиум:</b> <code>{utm['utm_medium']}</code>\n"
        f"<b>Кампания:</b> <code>{utm['utm_campaign']}</code>\n\n"
        f"<b>Ссылка:</b>\n<code>{base_url}</code>",
        parse_mode="HTML"
    )

@router.message(Command("set_offer_bonus"))
async def cmd_set_offer_bonus(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("🚫 Команда доступна только администратору.")
        return

    args = message.text.split()
    if len(args) != 4:
        await message.answer(
            "❌ Неверный формат.\n"
            "Используйте:\n"
            "<code>/set_offer_bonus [банк] [продукт] [сумма]</code>\n\n"
            "<b>Примеры:</b>\n"
            "<code>/set_offer_bonus t-bank black_youth 3000</code>\n"
            "<code>/set_offer_bonus alpha debit 1500</code>",
            parse_mode="HTML"
        )
        return

    bank = args[1]
    product_key = args[2]
    try:
        gross_bonus = int(args[3])
        if gross_bonus <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Сумма должна быть положительным целым числом.")
        return

    from database.db_manager import set_offer_bonus
    await set_offer_bonus(bank, product_key, gross_bonus)

    net_bonus = int(gross_bonus * 0.94)

    bank_name = "Т-Банка" if bank == "t-bank" else "Альфа-Банка" if bank == "alpha" else bank
    await message.answer(
        f"✅ Вознаграждение за оффер обновлено!\n\n"
        f"<b>Банк:</b> {bank_name}\n"
        f"<b>Продукт:</b> <code>{product_key}</code>\n"
        f"<b>Брутто (до налогов):</b> {gross_bonus} ₽\n"
        f"<b>Нетто (после 6% НПД):</b> {net_bonus} ₽",
        parse_mode="HTML"
    )

@router.message(Command("report"))
async def cmd_report(message: types.Message):
    if not is_admin(message.from_user.id):
        logger.warning(f"Попытка доступа к /report от не-админа: {message.from_user.id}")
        await message.answer("🚫 Доступ только для администраторов.")
        return
    
    processing_msg = await message.answer("⏳ Генерируем отчёт...")
    
    try:
        json_data = await generate_full_json_report()
        
        if not json_data:
            await processing_msg.edit_text("📭 Нет данных для отчёта.")
            return
        
        try:
            report_dict = json.loads(json_data)
            user_count = len(report_dict.get('users', []))
        except:
            user_count = 0
        
        await message.answer_document(
            BufferedInputFile(
                json_data.encode("utf-8"),
                filename=f"report_{datetime.now().strftime('%Y%m%d')}.json"
            ),
            caption=f"📊 Отчёт по рефералам\n👥 Пользователей: {user_count}\n📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )
        
        await processing_msg.delete()
        
        logger.info(f"Админ {message.from_user.id} успешно получил отчёт ({user_count} пользователей)")
        
    except Exception as e:
        logger.error(f"Ошибка при генерации /report: {e}", exc_info=True)
        await processing_msg.edit_text(
            f"❌ Ошибка генерации отчёта:\n"
            f"```{str(e)[:150]}```\n\n"
            f"Проверьте:\n"
            f"1. Наличие функции generate_full_json_report\n"
            f"2. Доступ к базе данных\n"
            f"3. Корректность данных в таблицах",
            parse_mode="Markdown"
        )

@router.message(Command("find"))
async def cmd_find(message: types.Message):
    if not is_admin(message.from_user.id):
        logger.warning(f"Попытка доступа к /find от не-админа: {message.from_user.id}")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("🔍 Укажите номер телефона в формате:\n<code>/find +79161234567</code>", parse_mode="HTML")
        return

    phone = parts[1].strip()

    try:
        user = await get_user_by_phone(phone)
        if not user:
            await message.answer(f"❌ Реферал с номером <code>{phone}</code> не найден.", parse_mode="HTML")
            return

        bank_name = {"t-bank": "Т-Банк", "alpha": "Альфа-Банк"}.get(user["bank"], user["bank"])
        status_card = "✅ Активирована" if user.get("card_activated") else "❌ Не активирована"
        status_purchase = "✅ Совершена" if user.get("purchase_made") else "❌ Не совершена"

        if user["bank"] == "t-bank":
            fallback_bonus = 500
        elif user["bank"] == "alpha":
            fallback_bonus = 700
        else:
            fallback_bonus = 0

        bonus_amount = user.get("total_referral_bonus", 0) or fallback_bonus

        bonus_confirmed = (
            (user["bank"] == "t-bank" and user.get("card_activated") and user.get("purchase_made")) or
            (user["bank"] == "alpha" and user.get("card_activated"))
        )
        bonus_status = "✅ Подтверждён" if bonus_confirmed else "⏳ Ожидает"

        report = (
            f"👤 <b>Найден реферал</b>\n\n"
            f"ФИО: {user['full_name']}\n"
            f"Телефон: <code>{phone}</code>\n"
            f"Банк: {bank_name}\n\n"
            f"Статус:\n"
            f"• Активация карты: {status_card}\n"
            f"• Первая покупка: {status_purchase}\n\n"
            f"Бонус:\n"
            f"• Ваше вознаграждение: {bonus_amount} руб.\n"
            f"• Статус: {bonus_status}"
        )
        await message.answer(report, parse_mode="HTML")
        logger.info(f"Админ {message.from_user.id} нашёл реферала по номеру {phone}")

    except Exception as e:
        logger.error(f"Ошибка при поиске по номеру {phone}: {e}")
        await message.answer("❌ Произошла ошибка при поиске.")

async def send_reminder_to_user(bot, user_id: int, message_text: str):
    try:
        await bot.send_message(user_id, message_text, parse_mode="HTML")
    except Exception as e:
        print(f"Не удалось отправить напоминание пользователю {user_id}: {e}")
        raise

@router.message(Command("remind"))
async def cmd_remind(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Укажите номер: /remind +79161234567")
        return
    phone = args[1].strip()
    user = await get_user_by_phone(phone)
    if not user:
        await message.answer("Реферал не найден.")
        return

    bank_name = "Т-Банка" if user["bank"] == "t-bank" else "Альфа-Банка"
    message_text = (
        f"🔔 <b>Напоминание</b>\n\n"
        f"👋 Пожалуйста, обновите статус вашей заявки по карте {bank_name} — "
        f"это поможет нам быстрее начислить вам бонус!"
    )

    try:
        await send_reminder_to_user(message.bot, user["user_id"], message_text)
        await log_reminder_sent(user["user_id"], message.from_user.id)
        await message.answer("✅ Напоминание отправлено.")
    except Exception as e:
        await message.answer("❌ Не удалось отправить сообщение пользователю.")
        logger.error(f"Ошибка отправки напоминания: {e}")
    
@router.message(Command("delete_data"))
async def cmd_delete_data(message: types.Message):
    """
    Удаляет данные реферала по номеру телефона.
    Использование: /delete_data +79161234567
    """
    if not is_admin(message.from_user.id):
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "❌ Укажите номер телефона реферала:\n"
            "<code>/delete_data +79161234567</code>",
            parse_mode="HTML"
        )
        return

    phone = args[1].strip()
    success = await delete_user_by_phone(phone)
    if success:
        await message.answer(
            f"✅ Данные реферала с номером <code>{phone}</code> удалены.",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            f"❌ Реферал с номером <code>{phone}</code> не найден.",
            parse_mode="HTML"
        )