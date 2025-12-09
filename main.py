import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import asyncio
import logging
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import Bot, Dispatcher
from config import settings
from database.db_manager import init_db
from core.bot_instance import setup_bot
from aiogram.types import BotCommand
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from jobs.reminder_job import send_reminders_job
from jobs.weekly_report_job import send_weekly_report

async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Начать работу"),
        BotCommand(command="status", description="Статус заявки"),
        BotCommand(command="help", description="Помощь")
    ]
    await bot.set_my_commands(commands)

async def main():
    await init_db()
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=settings.BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    await setup_bot(dp, bot)
    await dp.start_polling(bot)
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(
        send_reminders_job,
        "cron",
        day_of_week="mon",  # mon, tue, ..., sun
        hour=10,
        args=[bot]
    )
    scheduler.add_job(
        send_weekly_report,
        "cron",
        day_of_week="mon",
        hour=10,
        minute=5,
        args=[bot]
    )

    scheduler.start()

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())