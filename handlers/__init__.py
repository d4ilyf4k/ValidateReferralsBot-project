from aiogram import Dispatcher

from .start_handler import router as start_router
from .onboarding_handler import router as onboarding_router
from .profile_handler import router as profile_router
from .finance_handler import router as finance_router
from .status_handler import router as status_router
from .help_handler import router as help_router
from .bank_handler import router as bank_router
from .user_handlers import router as user_router
from .admin_handler import router as admin_router
from .callback_handlers import router as callback_router

def register_all_handlers(dp: Dispatcher):
    dp.include_router(start_router)
    dp.include_router(onboarding_router)
    dp.include_router(profile_router)
    dp.include_router(finance_router)
    dp.include_router(status_router)
    dp.include_router(help_router)
    dp.include_router(bank_router)
    dp.include_router(user_router)
    dp.include_router(admin_router)
    dp.include_router(callback_router)