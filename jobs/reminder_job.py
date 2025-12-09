from aiogram import Bot
from database.db_manager import get_users_for_auto_reminder, log_reminder_sent
from utils.reminders import send_reminder_to_user

async def send_reminders_job(bot: Bot):
    users = await get_users_for_auto_reminder()

    for user in users:
        user_id = user["user_id"]
        bank = user["bank"]
        reminder_type = user["reminder_type"]

        if reminder_type == "activation":
            if bank == "alpha":
                message_text = (
                    "🔔 <b>Напоминание от бота</b>\n\n"
                    "👋 Здравствуйте! Вы получили дебетовую карту Альфа-Банка, но, возможно, ещё не активировали её.\n\n"
                    "✅ Чтобы получить бонус в размере 500–700 ₽, активируйте карту в приложении или по звонку в банк."
                )
            else:  # t-bank и другие
                bank_name = "Т-Банка" if bank == "t-bank" else bank
                message_text = (
                    f"🔔 <b>Напоминание от бота</b>\n\n"
                    f"👋 Здравствуйте! Вы получили карту {bank_name}, но, возможно, ещё не активировали её.\n\n"
                    f"✅ Чтобы получить бонус, активируйте карту в течение 7 дней."
                )
        elif reminder_type == "purchase" and bank == "t-bank":
            message_text = (
                "🔔 <b>Напоминание от бота</b>\n\n"
                "👋 Здравствуйте! Вы активировали карту Т-Банка, но ещё не совершили первую покупку.\n\n"
                "✅ Чтобы получить бонус, совершите покупку от 500 ₽ в течение 7 дней."
            )
        else:
            continue

        try:
            await send_reminder_to_user(bot, user_id, message_text)
            await log_reminder_sent(user_id, admin_id=0)  # 0 = системное напоминание
        except Exception as e:
            print(f"❌ Ошибка при отправке напоминания {user_id}: {e}")