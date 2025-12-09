from aiogram import Router, F, types
from config import settings
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, BufferedInputFile
from aiogram.filters import StateFilter
from handlers.onboarding_handler import Onboarding
from handlers.profile_handler import ProfileEdit
from handlers.admin_handler import send_reminder_to_user
from utils.keyboards import (
    get_phone_kb,
    get_bank_kb,
    get_yes_no_kb,
    get_user_main_menu_kb,
    get_admin_main_menu_kb,
    get_admin_panel_kb, 
    get_agreement_kb,
    get_detailed_back_kb,
)
from utils.validation import is_valid_date
from database.db_manager import (
        update_progress_field, 
        get_user_by_phone, 
        log_reminder_sent, 
        get_user_full_data,
        get_all_referrals_data,
        decrypt_phone
)
from services.report_generator import (
    generate_referral_text_report_with_conditions, 
    )
from services.bonus_calculator import recalculate_all_bonuses
from handlers.finance_handler import show_finance_report
from handlers.bank_handler import BankAgreement, _get_detailed_conditions_text, _get_conditions_text


router = Router()

@router.callback_query(F.data == "menu_finance")
async def admin_finance(callback: types.CallbackQuery):
    if callback.from_user.id not in settings.ADMIN_IDS:
        await callback.answer("🚫 Доступ запрещён.", show_alert=True)
        return
    await callback.answer()
    await show_finance_report(callback.message)

@router.callback_query(F.data == "menu_status")
async def admin_status(callback: types.CallbackQuery):
    await callback.answer()
    user_data = await get_user_full_data(callback.from_user.id)
    if not user_data:
        await callback.message.answer("Ошибка: профиль не найден.")
        return
    def fmt_date(d): return d if d else "—"
    status_text = (
        "📋 <b>Статус вашей заявки</b>\n\n"
        f"• 🔓 Карта активирована: {'✅' if user_data['card_activated'] else '❌'}\n"
        f"• 💳 Покупка: {'✅' if user_data['purchase_made'] else '❌'}"
    )
    await callback.message.answer(status_text, parse_mode="HTML")


@router.callback_query(F.data == "menu_profile")
async def admin_profile(callback: types.CallbackQuery):
    await callback.answer()
    from .profile_handler import edit_profile
    fake_message = types.Message(
        message_id=callback.message.message_id,
        date=callback.message.date,
        chat=callback.message.chat,
        from_user=callback.from_user,
        text="✏️ Редактировать профиль"
    )
    await edit_profile(fake_message)
    
@router.callback_query(F.data == "menu_admin")
async def admin_panel(callback: types.CallbackQuery):
    if callback.from_user.id not in settings.ADMIN_IDS:
        await callback.answer("🚫 Доступ запрещён.", show_alert=True)
        return
    await callback.answer()
    await callback.message.answer(
        "🛠 <b>Админ-панель</b>\nВыберите действие:",
        reply_markup=get_admin_panel_kb(),
        parse_mode="HTML"
    )
    
@router.callback_query(F.data == "cancel_edit")
async def cancel_edit(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer("Отменено ✅", show_alert=False)
    await callback.message.answer(
        "Действие отменено. Вы в главном меню:",
        reply_markup=get_user_main_menu_kb()
    )


@router.callback_query(Onboarding.full_name, F.data == "back_to_start")
async def back_to_start_from_name(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("Регистрация отменена. Нажмите /start для начала.")

@router.callback_query(Onboarding.phone, F.data == "back_to_name")
async def back_to_name(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите ваше ФИО:")
    await state.set_state(Onboarding.full_name)

@router.callback_query(Onboarding.bank, F.data == "back_to_phone")
async def back_to_phone(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Отправьте номер телефона:", reply_markup=get_phone_kb())
    await state.set_state(Onboarding.phone)

@router.callback_query(F.data == "back_to_bank")
async def back_to_bank(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Выберите банк:", reply_markup=get_bank_kb())
    await state.set_state(Onboarding.bank)

@router.callback_query(ProfileEdit.application_submitted, F.data.startswith("yesno_"))
async def handle_app_submitted_choice(callback: CallbackQuery, state: FSMContext):
    value = callback.data == "yesno_app_submitted_yes"
    await update_progress_field(callback.from_user.id, "application_submitted", value)
    if value:
        await callback.message.answer("Укажите дату подачи заявки (ДД.ММ.ГГГГ):")
        await state.set_state(ProfileEdit.application_date)
    else:
        await _finalize_profile_edit(callback, state)

@router.message(ProfileEdit.application_date)
async def process_app_date(message: types.Message, state: FSMContext):
    if not is_valid_date(message.text):
        await message.answer("Неверный формат даты. Используйте ДД.ММ.ГГГГ.")
        return
    await update_progress_field(message.from_user.id, "application_date", message.text)
    await _finalize_profile_edit(message, state)

@router.callback_query(ProfileEdit.card_activated, F.data.startswith("yesno_"))
async def handle_card_activated_choice(callback: CallbackQuery, state: FSMContext):
    value = callback.data == "yesno_card_act_yes"
    await update_progress_field(callback.from_user.id, "card_activated", value)
    if value:
        await callback.message.answer("Укажите дату активации карты (ДД.ММ.ГГГГ):")
        await state.set_state(ProfileEdit.card_activated_date)
    else:
        await _finalize_profile_edit(callback, state)

@router.message(ProfileEdit.card_activated_date)
async def process_card_activated_date(message: types.Message, state: FSMContext):
    if is_valid_date(message.text):
        await update_progress_field(message.from_user.id, "card_activated_date", message.text)
        await _finalize_profile_edit(message, state)
    else:
        await message.answer("Неверная дата. Формат: ДД.ММ.ГГГГ")


async def _finalize_profile_edit(obj, state: FSMContext):
    await recalculate_all_bonuses(obj.from_user.id)
    msg = "✅ Данные обновлены! Бонусы пересчитаны."
    if isinstance(obj, types.Message):
        await obj.answer(msg, reply_markup=get_user_main_menu_kb())
    else:
        await obj.message.answer(msg, reply_markup=get_user_main_menu_kb())
    await state.clear()


@router.callback_query(F.data.startswith("edit_"))
async def handle_edit_field(callback: CallbackQuery, state: FSMContext):
    field = callback.data.replace("edit_", "")
    if field == "full_name":
        await callback.message.answer("Введите новое ФИО:")
        await state.set_state(ProfileEdit.full_name)
    elif field == "phone":
        await callback.message.answer("Отправьте новый номер:", reply_markup=get_phone_kb())
        await state.set_state(ProfileEdit.phone)
    elif field == "bank":
        await callback.message.answer("Выберите банк:", reply_markup=get_bank_kb())
        await state.set_state(ProfileEdit.bank)
    elif field == "application_submitted":
        await callback.message.answer("Заявка подана?", reply_markup=get_yes_no_kb("app_submitted"))
        await state.set_state(ProfileEdit.application_submitted)
    elif field == "card_activated":
        await callback.message.answer("Карта активирована?", reply_markup=get_yes_no_kb("card_act"))
        await state.set_state(ProfileEdit.card_activated)
    else:
        await callback.answer("Функция временно недоступна.", show_alert=True)
    await callback.answer()


@router.callback_query(F.data.startswith("black_"), StateFilter(BankAgreement.choosing_black_subtype))
async def process_black_type_selection(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "black_drive":
        product_key = "drive"
        product_name = "дебетовую карту Drive"
        black_type_name = "Карта Drive"
    
    elif callback.data == "black_premium":
        product_key = "tbank_premium"
        product_name = "премиальную карту Tinkoff Black Premium"
        black_type_name = "Премиум-карта"
        
    else:
        product_key = "tbank_black"
        type_map = {
            "black_classic": "Классическая карта (пластик)",
            "black_aroma": "Аромакарта (металл)",
            "black_youth": "Молодёжная карта",
            "black_retro": "Карта в ретро-дизайне",
        }
        black_type_name = type_map.get(callback.data, "Классическая карта (пластик)")
        product_name = "Tinkoff Black"

    await state.update_data(
        black_type=callback.data,
        black_type_name=black_type_name,
        product_key=product_key,
        product_name=product_name
    )

    await show_product_conditions(callback, state, product_key, product_name)
    await callback.answer()


async def show_product_conditions(
    callback: types.CallbackQuery, 
    state: FSMContext, 
    product_key: str, 
    product_name: str
):
    data = await state.get_data()
    black_type_name = data.get("black_type_name", "")

    conditions_text = _get_detailed_conditions_text(product_key, product_name, black_type_name)

    await state.update_data(final_product_selection={
        "product_key": product_key,
        "product_name": product_name,
        "black_type": black_type_name if product_key == "tbank_black" else None
    })

    await state.set_state(BankAgreement.waiting_agreement)

    await callback.message.edit_text(
        conditions_text,
        parse_mode="HTML",
        reply_markup=get_agreement_kb()
    )
    
@router.callback_query(F.data == "admin_report")
async def admin_report(callback: types.CallbackQuery):
    if callback.from_user.id not in settings.ADMIN_IDS:
        await callback.answer("🚫 Доступ запрещён.", show_alert=True)
        return
    
    await callback.answer("📊 Генерируем отчёт...", show_alert=False)
    
    try:
        raw_data = await get_all_referrals_data(include_financial=True)
        
        if not raw_data:
            await callback.message.answer("📭 Нет данных для отчёта.")
            return
        
        import json
        from datetime import datetime
        
        processed_users = []
        for user in raw_data:
            user_dict = dict(user)
            
            phone_enc = user_dict.get('phone_enc')
            if phone_enc:
                user_dict['phone'] = decrypt_phone(phone_enc)
            else:
                user_dict['phone'] = None
            
            if 'phone_enc' in user_dict:
                del user_dict['phone_enc']
            
            processed_users.append(user_dict)
        
        json_result = {
            "generated_at": datetime.now().isoformat(),
            "total_users": len(processed_users),
            "users": processed_users
        }
        
        json_str = json.dumps(json_result, ensure_ascii=False, indent=2, default=str)
        
        await callback.message.answer_document(
            BufferedInputFile(
                json_str.encode("utf-8"),
                filename=f"referral_report_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
            ),
            caption=f"📄 Отчёт по рефералам\n📊 Пользователей: {len(processed_users)}\n🕒 Сгенерирован: {datetime.now().strftime('%H:%M')}"
        )
        
    except Exception as e:
        print(f"❌ Ошибка генерации отчёта: {e}")
        import traceback
        traceback.print_exc()
        
        await callback.message.answer(
            f"❌ Ошибка генерации отчёта:\n"
            f"`{str(e)[:100]}`\n\n"
            f"Проверьте логи или настройки БД.",
            parse_mode="Markdown"
        )
    
    await callback.answer()

@router.callback_query(F.data == "admin_finance_total")
async def admin_finance_total(callback: CallbackQuery):
    await callback.answer()
    from handlers.admin_handler import cmd_finance_total
    await cmd_finance_total(callback.message)

class AdminStates(StatesGroup):
    find_phone = State()
    finance_referral_phone = State()
    remind_phone = State()

@router.callback_query(F.data == "admin_finance_referral")
async def admin_finance_referral_start(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in settings.ADMIN_IDS:
        await callback.answer("🚫 Доступ запрещён.", show_alert=True)
        return
    await callback.answer()
    await callback.message.answer("📱 Введите номер телефона реферала:")
    await state.set_state(AdminStates.finance_referral_phone)

@router.message(AdminStates.finance_referral_phone)
async def process_finance_referral_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip()
    user = await get_user_by_phone(phone)
    if not user:
        await message.answer("❌ Реферал не найден.")
    else:
        report = generate_referral_text_report_with_conditions(user)
        await message.answer(report, parse_mode="HTML")
    await state.clear()

@router.callback_query(F.data == "admin_remind")
async def admin_remind_start(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in settings.ADMIN_IDS:
        await callback.answer("🚫 Доступ запрещён.", show_alert=True)
        return
    await callback.answer()
    await callback.message.answer("📱 Введите номер телефона реферала (например, +79161234567):")
    await state.set_state(AdminStates.remind_phone)
    
@router.message(AdminStates.remind_phone)
async def process_remind_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip()
    user = await get_user_by_phone(phone)
    
    if not user:
        await message.answer("❌ Реферал с таким номером не найден.")
        await state.clear()
        return

    await send_reminder_to_user(
        bot=message.bot,
        user_id=user["user_id"],
        message_text="👋 Пожалуйста, обновите статус вашей заявки — это поможет нам быстрее начислить бонус!"
    )
    
    await log_reminder_sent(user["user_id"], message.from_user.id)
    
    await message.answer(f"✅ Напоминание отправлено рефералу {user['full_name']}.")
    await state.clear()


@router.callback_query(F.data == "admin_find_phone")
async def start_admin_find_phone(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in settings.ADMIN_IDS:
        await callback.answer("🚫 Доступ запрещён.", show_alert=True)
        return

    await callback.answer()
    await callback.message.answer("📱 Введите номер телефона реферала (например, +79161234567):")
    await state.set_state(AdminStates.find_phone)
    
@router.message(AdminStates.find_phone)
async def process_find_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip()
    user = await get_user_by_phone(phone)

    if not user:
        await message.answer("❌ Реферал с таким номером не найден.")
    else:
        report = generate_referral_text_report_with_conditions(user)
        await message.answer(report, parse_mode="HTML")

    await state.clear()
    
@router.callback_query(F.data == "admin_update_links")
async def admin_update_links(callback: types.CallbackQuery):
    if callback.from_user.id not in settings.ADMIN_IDS:
        await callback.answer("🚫 Доступ запрещён.", show_alert=True)
        return
    await callback.answer()
    await callback.message.answer(
        "📌 Отправьте команду в формате:\n"
        "<code>/update_link [банк] [продукт] [ссылка] [utm-параметры...]</code>\n\n"
        "<b>Пример:</b>\n"
        "<code>/update_link t-bank black_aroma https://tbank.ru/aroma utm_source=bot utm_medium=ref</code>\n\n"
        "<b>Поддерживаемые банки:</b> <code>t-bank</code>, <code>alpha</code>\n"
        "<b>Продукты для t-bank:</b>\n"
        "• <code>black_classic</code> — обычная Black\n"
        "• <code>black_aroma</code> — аромакарта\n"
        "• <code>black_youth</code> — молодёжная\n"
        "• <code>black_retro</code> — ретро\n"
        "• <code>black_premium</code> — premium\n"
        "• <code>drive</code> — карта для авто\n"
        "• <code>main</code> — fallback (не рекомендуется)",
        parse_mode="HTML"
    )

@router.callback_query(F.data == "admin_back")
async def admin_back(callback: types.CallbackQuery):
    if callback.from_user.id not in settings.ADMIN_IDS:
        await callback.answer("🚫 Доступ запрещён.", show_alert=True)
        return

    await callback.answer()
    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(
        "🛠 <b>Админ-меню</b>",
        reply_markup=get_admin_main_menu_kb(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "show_details", StateFilter(BankAgreement.waiting_agreement))
async def show_details(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    product_key = data.get("product_key")
    product_name = data.get("product_name", "продукт")

    if not product_key:
        await callback.answer("❌ Не удалось определить продукт.", show_alert=True)
        return

    detailed_text = _get_detailed_conditions_text(product_key, product_name)
    await callback.message.edit_text(detailed_text, parse_mode="HTML", reply_markup=get_detailed_back_kb())
    await callback.answer()
    
@router.callback_query(F.data == "back_to_summary", StateFilter(BankAgreement.waiting_agreement))
async def back_to_summary(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    product_key = data.get("product_key")
    product_name = data.get("product_name")

    if not product_key:
        await callback.answer("❌ Ошибка: продукт не выбран.", show_alert=True)
        return

    summary_text = _get_conditions_text(product_key, product_name)
    await callback.message.edit_text(summary_text, parse_mode="HTML", reply_markup=get_agreement_kb())
    await callback.answer()