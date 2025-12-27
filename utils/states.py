from aiogram.fsm.state import State, StatesGroup
# =========================
# FSM STATES
# =========================
class Onboarding(StatesGroup):
    full_name = State()
    phone = State()
    bank = State()

class ProfileEdit(StatesGroup):
    full_name = State()
    phone = State()
    bank = State()
    card_activated = State()
    card_activated_date = State()
    purchase_made = State()
    application_submitted = State()
    application_date = State()
    choose_bank_for_activation = State()
    choose_bank_for_purchase = State()
class BankAgreement(StatesGroup):
    choosing_bank = State()
    choosing_tbank_product = State()
    choosing_black_subtype = State()
    waiting_agreement = State()

class AdminStates(StatesGroup):
    finance_referral_phone = State()
    waiting_bonus_amount = State()
    
class AddOfferFSM(StatesGroup):
    product_key = State()
    title = State()
    conditions = State()
    gross_bonus = State()
    confirm = State()
    
class AddProductFSM(StatesGroup):
    bank = State()
    product_key = State()
    product_name = State()
    description = State()

class AdminAddVariant(StatesGroup):
    bank = State()
    product_name = State()
    product_key = State()
    
class AdminAddOffer(StatesGroup):
    product_key = State()
    title = State()
    conditions = State()
    details = State()
