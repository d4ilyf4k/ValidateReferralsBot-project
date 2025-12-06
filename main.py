import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import settings
from database.db_manager import init_db
from core.bot_instance import setup_bot
from aiogram.types import BotCommand

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
    dp = Dispatcher()
    await setup_bot(dp, bot)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())