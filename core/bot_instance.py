from aiogram import Dispatcher
from handlers import register_all_handlers

async def setup_bot(dp: Dispatcher, bot):
    register_all_handlers(dp)