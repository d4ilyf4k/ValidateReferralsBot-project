from aiogram import Bot
from database.db_manager import get_users_for_auto_reminder, log_reminder_sent

async def send_auto_reminders(context):
    bot: Bot = context.job.data["bot"]
    users = await get_users_for_auto_reminder()
    for user in users:
        try:
            await bot.send_message(
                user["user_id"],
                "🔔 Напоминание: не забудьте обновить статус активации карты!"
            )
        except Exception as e:
            print(f"Ошибка отправки напоминания {user['user_id']}: {e}")
            
async def send_reminders_job(bot: Bot):
    users = await get_users_for_auto_reminder()

    for user in users:
        user_id = user["user_id"]
        bank = user["bank"]
        bank_name = "Т-Банка" if bank == "t-bank" else "Альфа-Банка"

        message_text = (
            f"🔔 <b>Напоминание</b>\n\n"
            f"👋 Пожалуйста, обновите статус вашей заявки по карте {bank_name} — "
            f"это поможет нам быстрее начислить вам реферальный бонус!"
        )

        try:
            await bot.send_message(
                user["user_id"],
                "🔔 Напоминание: пожалуйста, обновите статус заявки!"
            )
            await log_reminder_sent(user_id, admin_id=0)
        except Exception as e:
            print(f"❌ Не удалось отправить напоминание пользователю {user_id}: {e}")
            continue