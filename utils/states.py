from aiogram.fsm.state import State, StatesGroup

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