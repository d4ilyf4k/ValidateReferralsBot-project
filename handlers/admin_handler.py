import logging
import json
from datetime import datetime
from config import settings
from aiogram import Router, types, F
from aiogram.types import BufferedInputFile, CallbackQuery
from aiogram.filters import Command
from services.report_generator import generate_full_json_report
from database.db_manager import (
    get_user_by_phone, 
    log_reminder_sent, 
    update_referral_link, 
    delete_user_by_id,  
    delete_user_by_phone
)

router = Router()
logger = logging.getLogger(__name__)

def is_admin(user_id: int) -> bool:
    return user_id in settings.ADMIN_IDS


@router.callback_query(F.data == "admin_update_links")
async def handle_update_link_button(callback: CallbackQuery):
    if callback.from_user.id not in settings.ADMIN_IDS:
        await callback.answer("🚫 Доступ запрещён.", show_alert=True)
        return

    await callback.answer()
    await callback.message.answer(
        "📌 Отправьте команду в формате:\n"
        "<code>/update_link t-bank https://tbank.ru/ref/123 utm_source=telegram utm_medium=referral utm_campaign=winter2025</code>",
        parse_mode="HTML"
    )

@router.message(Command("update_link"))
async def cmd_update_link(message: types.Message):
    if not is_admin(message.from_user.id):
        return

    args = message.text.split()
    if len(args) < 3:
        await message.answer(
            "📌 Использование:\n"
            "<code>/update_link t-bank https://tbank.ru/ref/123</code>\n"
            "<code>/update_link alpha https://a.ru/ref utm_source=blog utm_medium=social</code>",
            parse_mode="HTML"
        )
        return

    bank = args[1]
    if bank not in ("t-bank", "alpha"):
        await message.answer("🏦 Поддерживаемые банки: <code>t-bank</code>, <code>alpha</code>", parse_mode="HTML")
        return

    base_url = args[2]
    if not base_url.startswith(("http://", "https://")):
        await message.answer("🔗 Ссылка должна начинаться с <code>http://</code> или <code>https://</code>", parse_mode="HTML")
        return

    utm = {"utm_source": "telegram", "utm_medium": "referral", "utm_campaign": "default"}
    for param in args[3:]:
        if "=" in param:
            key, value = param.split("=", 1)
            if key in utm:
                utm[key] = value

    await update_referral_link(bank, base_url, utm["utm_source"], utm["utm_medium"], utm["utm_campaign"])

    bank_name = "Т-Банка" if bank == "t-bank" else "Альфа-Банка"
    await message.answer(
        f"✅ Ссылка для {bank_name} обновлена:\n"
        f"• Источник: <code>{utm['utm_source']}</code>\n"
        f"• Медиум: <code>{utm['utm_medium']}</code>\n"
        f"• Кампания: <code>{utm['utm_campaign']}</code>",
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

        bonus_amount = 500 if user["bank"] == "t-bank" else 700
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
        await bot.send_message(user_id, message_text)
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
    await message.bot.send_message(
        user["user_id"],
        "👋 Пожалуйста, обновите статус вашей заявки — это поможет нам быстрее начислить бонус!"
    )
    await log_reminder_sent(user["user_id"], message.from_user.id)
    await message.answer("✅ Напоминание отправлено.")
    
@router.message(Command("delete_data"))
async def cmd_delete_data(message: types.Message):
    """
    Удаляет данные пользователя из БД.
    Использование:
        /delete_data                     → удалить самого админа
        /delete_data +79161234567        → удалить реферала по номеру
    """
    if not is_admin(message.from_user.id):
        return

    args = message.text.split(maxsplit=1)
    if len(args) == 1:
        # Удалить самого админа
        success = await delete_user_by_id(message.from_user.id)
        if success:
            await message.answer("✅ Ваши данные удалены.")
        else:
            await message.answer("Вы не найдены в базе данных.")
    else:
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