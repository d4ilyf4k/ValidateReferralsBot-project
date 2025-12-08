from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram.fsm.state import State, StatesGroup
from database.db_manager import get_referral_link, add_user_bank
from utils.keyboards import get_bank_kb, get_user_main_menu_kb, get_agreement_kb, get_detailed_conditions_kb
from services.bonus_calculator import recalculate_all_bonuses


router = Router()

class BankAgreement(StatesGroup):
    waiting_agreement = State()
    waiting_agreement_alpha = State()

@router.message(F.text == "🏦 Выбрать банк")
async def choose_bank(message: types.Message):
    await message.answer(
        "Выберите банк, чтобы получить персональную ссылку на оформление карты:",
        reply_markup=get_bank_kb()
    )

@router.message(F.text.in_(["🏦Т-Банк", "🏦Альфа-Банк"]))
async def send_bank_info_and_link(message: types.Message, state: FSMContext):
    bank_key = "t-bank" if message.text == "🏦Т-Банк" else "alpha"
    
    await state.update_data(bank_key=bank_key, user_id=message.from_user.id)
    
    if bank_key == "t-bank":
        desc = (
            "<b>🏦 Т-Банк | Карта Tinkoff Black</b>\n\n"
            
            "<b>📋 Условия для получения бонуса:</b>\n\n"
            "•✅ Быть <b>новым клиентом</b> Т-Банка (без других продуктов банка)\n"
            "•✅ Оформить именно <b>карту Tinkoff Black</b> (не Junior, не Drive)\n"
            "•✅ Совершить <b>любую покупку</b> картой в течение 30 дней после получения\n"
            "•✅ Активировать <b>промокод на 2 месяца бесплатного обслуживания</b>\n\n"
            
            "<b>💰 Что вы получаете:</b>\n\n"
            "•✅ <b>500 рублей</b> на счёт карты после первой покупки\n"
            "•✅ <b>60 дней бесплатного обслуживания</b> карты\n"
            "•✅ Все преимущества Tinkoff Black (кэшбэк до 30%, проценты на остаток)\n\n"
            
            "<i>⚠️ Внимательно ознакомьтесь с условиями выше.</i>\n\n"
            "<b>Вы согласны с условиями и готовы получить ссылку?</b>"
        )
        
        await state.set_state(BankAgreement.waiting_agreement)
        await message.answer(desc, parse_mode="HTML", reply_markup=get_agreement_kb())
        
    else:  # alpha
        desc = (
            "<b>🏦 Альфа-Банк | Дебетовая карта</b>\n\n"
                        
            "<b>📋 Условия для получения бонуса:</b>\n"
            "•✅ Оформить <b>дебетовую карту Альфа-Банка</b>\n"
            "•✅ <b>Получить и активировать карту</b> после оформления\n\n"
                        
            "<b>✨ Особые условия:</b>\n"
            "• <b>Совершить первую покупку</b> — онлайн или в магазине, на любую сумму\n\n"
            
            "<b>💰 Что ты получаешь:</b>\n"
            "•✅ Все преимущества карты Альфа-Банка (проценты, кешбэк, мили)\n"
            "•✅ <b>Дополнительный бонус в размере 500₽ за оформление карты!</b>\n\n"
            
            "<b>⏱️ Сроки:</b>\n"
            "Бонус зачисляется автоматически в течение <b>3–14 дней</b> после выполнения условий.\n\n"
            
            "<i>⚠️ Внимательно ознакомьтесь с условиями выше.</i>\n\n"
            "<b>Вы согласны с условиями и готовы получить ссылку?</b>"
        )
        
        await state.set_state(BankAgreement.waiting_agreement_alpha)
        await message.answer(desc, parse_mode="HTML", reply_markup=get_agreement_kb())

@router.callback_query(F.data == "agree_conditions", StateFilter(BankAgreement.waiting_agreement))
async def process_tbank_agreement(callback: types.CallbackQuery, state: FSMContext):

    data = await state.get_data()
    bank_key = data.get("bank_key", "t-bank")
    user_id = data.get("user_id", callback.from_user.id)
    
    await add_user_bank(user_id, bank_key)
    await recalculate_all_bonuses(user_id)
    link = await get_referral_link(bank_key)
    
    if link:
        success_message = (
            "<b>🎉 Отлично! Ваша персональная ссылка:</b>\n\n"
            f"<code>{link}</code>\n\n"
            "<b>🔹 Инструкция:</b>\n"
            "1. Перейдите по ссылке выше\n"
            "2. Оформите карту Tinkoff Black\n"
            "3. Введите промокод при оформлении\n"
            "4. Совершите покупку в течение 30 дней\n"
            "5. Получите 500₽ на счёт\n\n"
            
            "<i>⚠️ Ссылка персональная, не передавайте её другим.</i>\n\n"
            "<b>Удачи в оформлении! 🚀</b>"
        )
        
        await callback.message.edit_text(
            success_message,
            parse_mode="HTML",
            reply_markup=None
        )
        
        await callback.message.answer("Главное меню:", reply_markup=get_user_main_menu_kb())
        
    else:
        await callback.message.edit_text(
            "⚠️ Ссылка временно недоступна. Обратитесь к администратору.",
            parse_mode="HTML",
            reply_markup=None
        )
    
    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "agree_conditions", StateFilter(BankAgreement.waiting_agreement_alpha))
async def process_alpha_agreement(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    bank_key = data.get("bank_key", "alpha")
    user_id = data.get("user_id", callback.from_user.id)
    
    await add_user_bank(user_id, bank_key)
    await recalculate_all_bonuses(user_id)
    
    link = await get_referral_link(bank_key)
    
    if link:
        success_message = (
            "<b>🎉 Отлично! Ваша персональная ссылка для Альфа-Банка:</b>\n\n"
            f"<code>{link}</code>\n\n"
            
            "<b>🔹 Инструкция:</b>\n"
            "1. Перейдите по ссылке выше\n"
            "2. Оформите дебетовую карту\n"
            "3. Получите и активируйте карту\n"
            "4. Совершите первую покупку\n"
            "5. Получите 500₽ на счёт\n\n"
            
            "<i>⚠️ Ссылка персональная, не передавайте её другим.</i>\n\n"
            "<b>Удачи в оформлении! 🚀</b>"
        )
        
        await callback.message.edit_text(
            success_message,
            parse_mode="HTML",
            reply_markup=None
        )
        
        await callback.message.answer("Главное меню:", reply_markup=get_user_main_menu_kb())
        
    else:
        await callback.message.edit_text(
            "⚠️ Ссылка временно недоступна. Обратитесь к администратору.",
            parse_mode="HTML",
            reply_markup=None
        )
    
    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "disagree_conditions", StateFilter("*"))
async def process_disagreement(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "❌ Вы отказались от получения ссылки.\n\n"
        "Вы можете выбрать другой банк или вернуться в главное меню.",
        parse_mode="HTML",
        reply_markup=None
    )
    await callback.message.answer(
        "Выберите действие:",
        reply_markup=get_user_main_menu_kb()
    )
    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "show_details")
async def show_detailed_conditions(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    bank_key = data.get("bank_key", "t-bank")
    if bank_key == "t-bank":
        detailed_text = (
            "<b>📄 Подробные условия Т-Банк:</b>\n\n"
            
            "<b>Требования к клиенту:</b>\n"
            "• Не иметь других продуктов Т-Банка\n"
            "• Оформить именно Tinkoff Black (не Junior/Drive)\n"
            "• Совершить покупку в течение 30 дней после получения карты\n\n"
            
            "<b>Бонусы:</b>\n"
            "• 500 рублей на счёт после первой покупки\n"
            "• 2 месяца бесплатного обслуживания (по промокоду)\n\n"
            
            "<b>Сроки:</b>\n"
            "• Бонус начисляется до 10 рабочих дней\n"
            "• Карта доставляется бесплатно\n\n"
            
            "<b>📌 Официальные правила:</b>\n"
            "https://www.tinkoff.ru/about/promo/rules/500rub/\n\n"
            
            "<i>Вопросы: 8 800 555-77-78</i>"
        )
    else:
        detailed_text = (
            "<b>📄 Подробные условия Альфа-Банк:</b>\n\n"
            
            "<b>Требования к клиенту:</b>\n"
            "• Оформить дебетовую карту\n"
            "• Получить и активировать карту\n"
            "• Совершить первую покупку\n\n"
            
            "<b>Бонусы:</b>\n"
            "• 500 рублей на счёт после активации карты\n\n"
            
            "<b>Сроки:</b>\n"
            "• Бонус начисляется в течение 3-14 дней\n"
            "• Карта выпускается бесплатно\n\n"
            
            "<i>Дополнительные условия уточняйте на сайте банка.</i>"
        )
    
    await callback.message.edit_text(
        detailed_text,
        parse_mode="HTML",
        reply_markup=get_detailed_conditions_kb()
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_main")
async def back_to_main_conditions(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    bank_key = data.get("bank_key", "t-bank")
    
    if bank_key == "t-bank":
        desc = (
            "<b>🏦 Т-Банк | Карта Tinkoff Black</b>\n\n"
            
            "<b>📋 Условия для получения бонуса:</b>\n\n"
            "•✅ Быть <b>новым клиентом</b> Т-Банка (без других продуктов банка)\n"
            "•✅ Оформить именно <b>карту Tinkoff Black</b> (не Junior, не Drive)\n"
            "•✅ Совершить <b>любую покупку</b> картой в течение 30 дней после получения\n"
            "•✅ Активировать <b>промокод на 2 месяца бесплатного обслуживания</b>\n\n"
            
            "<b>💰 Что вы получаете:</b>\n\n"
            "•✅ <b>500 рублей</b> на счёт карты после первой покупки\n"
            "•✅ <b>60 дней бесплатного обслуживания</b> карты\n"
            "•✅ Все преимущества Tinkoff Black\n\n"
            
            "<i>⚠️ Внимательно ознакомьтесь с условиями выше.</i>\n\n"
            "<b>Вы согласны с условиями и готовы получить ссылку?</b>"
        )
    else:
        desc = (
            "<b>🏦 Альфа-Банк | Дебетовая карта</b>\n\n"
                        
            "<b>📋 Условия для получения бонуса:</b>\n"
            "•✅ Оформить <b>дебетовую карту Альфа-Банка</b>\n"
            "•✅ <b>Получить и активировать карту</b> после оформления\n\n"
                        
            "<b>✨ Особые условия:</b>\n"
            "• <b>Совершить первую покупку</b> — онлайн или в магазине, на любую сумму\n\n"
            
            "<b>💰 Что ты получаешь:</b>\n"
            "•✅ Все преимущества карты Альфа-Банка (проценты, кешбэк, мили)\n"
            "•✅ <b>Дополнительный бонус в размере 500₽ за оформление карты!</b>\n\n"
            
            "<b>⏱️ Сроки:</b>\n"
            "Бонус зачисляется автоматически в течение <b>3–14 дней</b> после выполнения условий.\n\n"
            
            "<i>⚠️ Внимательно ознакомьтесь с условиями выше.</i>\n\n"
            "<b>Вы согласны с условиями и готовы получить ссылку?</b>"
        )
    
    await callback.message.edit_text(
        desc,
        parse_mode="HTML",
        reply_markup=get_agreement_kb()
    )
    await callback.answer()