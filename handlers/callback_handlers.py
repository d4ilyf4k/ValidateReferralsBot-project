from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from config import settings
from database.db_manager import (
    confirm_user_bonus,
    reject_user_bonus,
    get_admin_finance_details,
    get_admin_finance_summary,
    get_admin_traffic_overview,
    get_admin_traffic_finance_projection,
    get_or_create_user_product,
    get_referral_link,
)
from services.referrer_report_generator import generate_admin_dashboard_text
from utils.keyboards import (
    get_user_main_menu_kb,
    get_admin_panel_kb,
    get_admin_dashboard_kb,
    get_admin_finance_kb,
    get_admin_traffic_filter_kb,
    get_agreement_kb,
    get_bank_kb,
)
from handlers.bank_handler import (
    _get_conditions_text,
    _get_detailed_conditions_text,
)

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in settings.ADMIN_IDS


# ==========================
# ADMIN PANEL
# ==========================

@router.callback_query(F.data == "menu_admin")
async def open_admin_panel(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("🚫 Доступ запрещён.", show_alert=True)

    await callback.message.edit_text(
        "🛠 <b>Админ-панель</b>\nВыберите действие:",
        reply_markup=get_admin_panel_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("bonus:"))
async def handle_bonus_action(call: types.CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return

    _, action, user_id, bank, product_key = call.data.split(":")

    user_id = int(user_id)

    if action == "confirm":
        success = await confirm_user_bonus(user_id, bank, product_key)
        text = "✅ Бонус подтверждён" if success else "⚠️ Уже обработан"

    elif action == "reject":
        success = await reject_user_bonus(user_id, bank, product_key)
        text = "❌ Бонус отклонён" if success else "⚠️ Уже обработан"

    else:
        await call.answer("Неизвестное действие", show_alert=True)
        return

    # UX: обновляем сообщение
    await call.message.edit_text(
        call.message.text + f"\n\n<b>{text}</b>",
        parse_mode="HTML"
    )
    await call.answer()


@router.callback_query(F.data == "admin:finance")
async def admin_finance_root(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("⛔️ Нет доступа", show_alert=True)

    data = await get_admin_finance_summary()

    if data["total_count"] == 0:
        text = "💰 <b>Финансы</b>\n\nПока нет подтверждённых заявок."
    else:
        text = (
            "💰 <b>Финансы</b>\n\n"
            f"📦 Подтверждённых заявок: <b>{data['total_count']}</b>\n"
            f"💵 Общий доход: <b>{data['total_profit']:,} ₽</b>"
        )

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_admin_finance_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "admin:finance:summary")
async def admin_finance_summary_cb(callback: types.CallbackQuery):
    await callback.answer()

    data = await get_admin_finance_summary()

    text = (
        "📊 <b>Финансовая сводка</b>\n\n"
        f"💳 Подтверждённых заявок: <b>{data['total_count']}</b>\n"
        f"💰 Общая прибыль: <b>{data['total_profit']} ₽</b>\n\n"
        "Выберите действие ниже:"
    )

    await callback.message.edit_text(
        text,
        reply_markup=get_admin_finance_kb(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "admin:finance:details")
async def admin_finance_details_cb(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    rows = await get_admin_finance_details()
    if not rows:
        return await callback.message.edit_text("📭 Пока нет данных по продуктам")

    text = (
        "📄 <b>Детальный финансовый отчёт</b>\n"
        "<i>Суммы указаны согласно условиям офферов. "
        "Фактическая выплата зависит от банка.</i>\n\n"
    )

    for r in rows[:20]:
        text += (
            f"👤 {r['user_id']} | {r['traffic_source']}\n"
            f"🏦 {r['bank']}\n"
            f"📦 {r['product_name']}\n"
            f"💰 {r['referrer_bonus']:,} ₽\n"
            f"🕒 {r['created_at']}\n\n"
        )

    await callback.message.edit_text(text, parse_mode="HTML")
    await callback.answer()

    
@router.callback_query(F.data == "admin_dashboard")
async def admin_dashboard(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("⛔️ Нет доступа", show_alert=True)

    text = await generate_admin_dashboard_text()

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_admin_dashboard_kb()
    )
    await callback.answer()
    



    
@router.callback_query(F.data == "admin:traffic")
async def admin_traffic_root(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return await cb.answer("⛔️ Нет доступа", show_alert=True)

    overview = await get_admin_traffic_overview()
    projection = await get_admin_traffic_finance_projection()

    total_users = sum(r["users"] for r in overview)
    total_products = sum(r["products_selected"] for r in overview)
    total_net = sum(r["net_bonus"] for r in projection)

    text = (
        "📊 <b>Трафик (сводка)</b>\n\n"
        f"👥 Пользователей: <b>{total_users}</b>\n"
        f"📦 Продуктов: <b>{total_products}</b>\n"
        f"💰 Прогноз дохода: <b>{total_net} ₽</b>"
    )

    await cb.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_admin_traffic_filter_kb()
    )
    await cb.answer()


@router.callback_query(F.data == "admin:traffic:all")
async def admin_traffic_all(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return await cb.answer("⛔️ Нет доступа", show_alert=True)

    overview = await get_admin_traffic_overview()
    projection = await get_admin_traffic_finance_projection()

    text = "<b>📊 Трафик: все источники</b>\n\n"

    for ov in overview:
        pr = next(
            (p for p in projection if p["traffic_source"] == ov["traffic_source"]),
            None
        )

        text += (
            f"• <b>{ov['traffic_source']}</b>\n"
            f"  👥 Пользователей: {ov['users']}\n"
            f"  📦 Продуктов: {ov['products_selected']}\n"
            f"  💰 Нетто: {pr['net_bonus'] if pr else 0} ₽\n\n"
        )

    await cb.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_admin_traffic_filter_kb()
    )
    await cb.answer()


@router.callback_query(
    F.data.startswith("admin:traffic:")
    & ~F.data.in_(["admin:traffic", "admin:traffic:all"])
)
async def admin_traffic_by_source(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return await cb.answer("⛔️ Нет доступа", show_alert=True)

    source = cb.data.split(":")[-1]

    overview = await get_admin_traffic_overview()
    projection = await get_admin_traffic_finance_projection()

    ov = next((r for r in overview if r["traffic_source"] == source), None)
    pr = next((r for r in projection if r["traffic_source"] == source), None)

    text = (
        f"📊 <b>Трафик: {source}</b>\n\n"
        f"👥 Пользователей: <b>{ov['users'] if ov else 0}</b>\n"
        f"📦 Продуктов: <b>{ov['products_selected'] if ov else 0}</b>\n"
        f"💰 Доход (нетто): <b>{pr['net_bonus'] if pr else 0} ₽</b>"
    )

    await cb.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_admin_traffic_filter_kb()
    )
    await cb.answer()


@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("🚫 Доступ запрещён.", show_alert=True)
        return

    await callback.message.edit_text(
        "🛠 <b>Админ-меню</b>",
        reply_markup=get_admin_panel_kb(),
        parse_mode="HTML"
    )
    await callback.answer()
    

# ==========================
# BANK AGREEMENT FLOW
# ==========================

@router.callback_query(F.data == "agree_conditions")
async def agree_conditions(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    if not all(k in data for k in ("bank_key", "product_key", "product_name")):
        await callback.answer("⚠️ Сессия устарела, начните заново", show_alert=True)
        await state.clear()
        return

    user_id = callback.from_user.id

    await get_or_create_user_product(
        user_id,
        data["bank_key"],
        data["product_key"],
        data["product_name"]
    )

    link = await get_referral_link(data["bank_key"], data["product_key"])

    if not link:
        await callback.message.edit_text("⚠️ Ссылка временно недоступна")
        await state.clear()
        return

    await callback.message.edit_text(
        f"<b>🎉 Ваша персональная ссылка на {data['product_name']}:</b>\n\n"
        f"{link}",
        parse_mode="HTML"
    )

    await callback.message.answer(
        "Главное меню:",
        reply_markup=get_user_main_menu_kb()
    )

    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "show_details")
async def show_details(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    product_key = data.get("product_key")
    product_name = data.get("product_name", "продукт")

    if not product_key:
        await callback.answer("❌ Продукт не найден.", show_alert=True)
        return

    text = _get_detailed_conditions_text(product_key, product_name)
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_agreement_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "disagree_conditions")
async def agree_fallback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    await callback.message.edit_text(
        "❌ Без согласия с условиями участие невозможно.\n\n"
        "Если передумаете — нажмите /start"
    )



@router.callback_query(F.data == "back_to_summary")
async def back_to_summary(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    product_key = data.get("product_key")
    product_name = data.get("product_name")

    if not product_key:
        await callback.answer("❌ Продукт не выбран.", show_alert=True)
        return

    text = _get_conditions_text(product_key, product_name)
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_agreement_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_banks")
async def back_to_banks(callback: CallbackQuery, state: FSMContext):
    await state.clear()

    await callback.message.answer(
        "🏦 Выберите банк:",
        reply_markup=get_bank_kb()
    )

    await callback.answer()


# ==========================
# COMMON
# ==========================

@router.callback_query(F.data == "cancel_edit")
async def cancel_edit(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer("Отменено")
    await callback.message.answer(
        "Вы в главном меню:",
        reply_markup=get_user_main_menu_kb()
    )
