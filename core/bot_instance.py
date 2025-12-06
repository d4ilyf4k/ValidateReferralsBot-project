from aiogram import Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from handlers import register_all_handlers
from jobs.reminder_job import send_reminders_job
    
async def setup_bot(dp: Dispatcher, bot):
    register_all_handlers(dp)

    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        send_reminders_job,
        "interval",
        minutes=10,
        kwargs={"bot": bot}
    )
    scheduler.start()