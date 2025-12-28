from aiogram import Dispatcher

from .start_handler import router as start_router
from .profile_handler import router as profile_router
from .finance_handler import router as finance_router
from .help_handler import router as help_router
from .bank_handler import router as bank_router
from .user_handlers import router as user_router

from .admin_users_handler import router as admin_users_router
from .admin_handler import router as admin_router
from .admin_finance_handler import router as admin_finance_router

from .admin_catalog_fsm import router as admin_catalog_fsm_router
from .admin_product_fsm import router as admin_product_fsm_router
from .admin_variant_handlers import router as admin_variant_router
from .admin_conditions_fsm import router as admin_conditions_router
from .admin_offer_fsm import router as admin_offer_fsm_router
from .admin_back import router as admin_back_router

from .callback_handlers import router as callback_router


def register_all_handlers(dp: Dispatcher):
    # -------------------- ADMIN FSM (PRIORITY FIRST) --------------------
    dp.include_router(admin_catalog_fsm_router)
    dp.include_router(admin_product_fsm_router)
    dp.include_router(admin_variant_router)
    dp.include_router(admin_conditions_router)
    dp.include_router(admin_offer_fsm_router)

    # -------------------- USER FLOW --------------------
    dp.include_router(start_router)
    dp.include_router(profile_router)
    dp.include_router(finance_router)
    dp.include_router(help_router)
    dp.include_router(bank_router)
    dp.include_router(user_router)

    # -------------------- ADMIN NON-FSM --------------------
    dp.include_router(admin_router)
    dp.include_router(admin_users_router)
    dp.include_router(admin_finance_router)

    # -------------------- CALLBACK FALLBACKS --------------------
    dp.include_router(callback_router)
    dp.include_router(admin_back_router)
