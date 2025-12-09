from aiogram import Bot

async def send_reminder_to_user(bot: Bot, user_id: int, message_text: str):
    try:
        await bot.send_message(user_id, message_text, parse_mode="HTML")
    except Exception as e:
        print(f"❌ Не удалось отправить напоминание пользователю {user_id}: {e}")