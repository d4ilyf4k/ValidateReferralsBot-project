from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder
from db.offers import (
    create_or_update_offer,
    update_offer,
    delete_offer,
    get_active_offers,
    get_offer_by_id
)

from utils.keyboards import (
    get_admin_offers_list_kb,
    get_admin_offer_card_kb,
    confirm_keyboard,
    add_back_button
)

router = Router()


# =========================
# FSM
# =========================
class OfferFSM(StatesGroup):
    view_offers = State()
    view_offer = State()

    add_title = State()
    add_conditions = State()
    add_bonus = State()
    confirm_add = State()

    edit_title = State()
    edit_conditions = State()
    edit_bonus = State()
    confirm_edit = State()

    confirm_delete = State()


# =========================
# HELPERS
# =========================
async def show_offer_list(target, state: FSMContext):
    data = await state.get_data()

    parent_type = data.get("parent_type")
    parent_key = data.get("parent_key")

    if not parent_type or not parent_key:
        if isinstance(target, types.CallbackQuery):
            await target.answer("⚠️ Контекст оффера утерян", show_alert=True)
        return

    offers = await get_active_offers(parent_type, parent_key)
    markup = get_admin_offers_list_kb(offers)

    await state.set_state(OfferFSM.view_offers)

    title = (
        "🎯 Офферы продукта:"
        if parent_type == "product"
        else "🎯 Офферы варианта:"
    )

    if isinstance(target, types.CallbackQuery):
        await target.message.edit_text(title, reply_markup=markup)
        await target.answer()
    else:
        await target.answer(title, reply_markup=markup)


# =========================
# ENTRY
# =========================
@router.callback_query(F.data.startswith("admin_offer:open:"))
async def admin_offer_entry(callback: types.CallbackQuery, state: FSMContext):
    _, _, parent_type, parent_key = callback.data.split(":")

    await state.update_data(
        parent_type=parent_type,
        parent_key=parent_key,
        variant_key=parent_key if parent_type == "variant" else None,
    )

    await show_offer_list(callback, state)


# =========================
# VIEW OFFER
# =========================
@router.callback_query(F.data.startswith("admin_offer:view:"))
async def admin_offer_view(callback: types.CallbackQuery, state: FSMContext):
    offer_id = int(callback.data.split(":")[2])
    offer = await get_offer_by_id(offer_id)

    if not offer:
        await callback.answer("⚠️ Оффер не найден", show_alert=True)
        return

    await state.update_data(
        offer_id=offer_id,
        offer=offer,
    )
    await state.set_state(OfferFSM.view_offer)

    await callback.message.edit_text(
        f"<b>{offer['offer_title']}</b>\n\n"
        f"<b>Условия:</b>\n{offer['offer_conditions']}\n\n"
        f"<b>Бонус:</b> {offer['gross_bonus']}",
        reply_markup=get_admin_offer_card_kb(
            offer_id,
            offer["is_active"]
        ),
        parse_mode="HTML"
    )
    await callback.answer()


# =========================
# ADD OFFER
# =========================
@router.callback_query(F.data == "admin_offer:add")
async def add_offer_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(OfferFSM.add_title)

    kb = InlineKeyboardBuilder()
    add_back_button(kb)

    await callback.message.edit_text(
        "Введите название оффера:",
        reply_markup=kb.as_markup()
    )
    await callback.answer()


@router.message(OfferFSM.add_title)
async def add_offer_title(message: types.Message, state: FSMContext):
    await state.update_data(offer_title=message.text.strip())
    await state.set_state(OfferFSM.add_conditions)
    await message.answer("Введите условия оффера:")


@router.message(OfferFSM.add_conditions)
async def add_offer_conditions(message: types.Message, state: FSMContext):
    await state.update_data(offer_conditions=message.text.strip())
    await state.set_state(OfferFSM.add_bonus)
    await message.answer("Введите бонус (число):")


@router.message(OfferFSM.add_bonus)
async def add_offer_bonus(message: types.Message, state: FSMContext):
    try:
        bonus = int(message.text.strip())
    except ValueError:
        await message.answer("⚠️ Бонус должен быть числом")
        return

    await state.update_data(gross_bonus=bonus)

    data = await state.get_data()
    kb = InlineKeyboardBuilder()
    confirm_keyboard(kb)
    add_back_button(kb)

    await state.set_state(OfferFSM.confirm_add)
    await message.answer(
        f"Создать оффер?\n\n"
        f"Название: {data['offer_title']}\n"
        f"Условия: {data['offer_conditions']}\n"
        f"Бонус: {data['gross_bonus']}",
        reply_markup=kb.as_markup()
    )


@router.callback_query(F.data == "confirm_yes", OfferFSM.confirm_add)
async def confirm_add_offer(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()

    await create_or_update_offer(
        bank_key=data["bank_key"],
        parent_type=data["parent_type"],
        parent_key=data["parent_key"],
        offer_title=data["offer_title"],
        offer_conditions=data["offer_conditions"],
        gross_bonus=data["gross_bonus"],
        is_active=1
    )

    await callback.answer("✅ Оффер создан")
    await show_offer_list(callback, state)


@router.callback_query(F.data == "confirm_no", OfferFSM.confirm_add)
async def cancel_add_offer(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer("❌ Создание отменено")
    await show_offer_list(callback, state)


# =========================
# EDIT OFFER
# =========================
@router.callback_query(F.data.startswith("admin_offer:edit:"))
async def edit_offer_start(callback: types.CallbackQuery, state: FSMContext):
    offer_id = int(callback.data.split(":")[2])
    offer = await get_offer_by_id(offer_id)

    if not offer:
        await callback.answer("⚠️ Оффер не найден", show_alert=True)
        return

    await state.update_data(
        offer_id=offer_id,
        offer_title=offer["offer_title"],
        offer_conditions=offer["offer_conditions"],
        gross_bonus=offer["gross_bonus"]
    )
    await state.set_state(OfferFSM.edit_title)

    kb = InlineKeyboardBuilder()
    add_back_button(kb)
    await callback.message.edit_text(
        f"Новое название или /skip\nТекущее: {offer['offer_title']}",
        reply_markup=kb.as_markup()
    )
    await callback.answer()


@router.message(OfferFSM.edit_title)
async def edit_offer_title(message: types.Message, state: FSMContext):
    if message.text != "/skip":
        await state.update_data(offer_title=message.text.strip())
    await state.set_state(OfferFSM.edit_conditions)
    await message.answer("Новые условия или /skip:")


@router.message(OfferFSM.edit_conditions)
async def edit_offer_conditions(message: types.Message, state: FSMContext):
    if message.text != "/skip":
        await state.update_data(offer_conditions=message.text.strip())
    await state.set_state(OfferFSM.edit_bonus)
    await message.answer("Новый бонус или /skip:")


@router.message(OfferFSM.edit_bonus)
async def edit_offer_bonus(message: types.Message, state: FSMContext):
    if message.text != "/skip":
        try:
            await state.update_data(gross_bonus=int(message.text.strip()))
        except ValueError:
            await message.answer("⚠️ Бонус должен быть числом")
            return

    kb = InlineKeyboardBuilder()
    confirm_keyboard(kb)
    add_back_button(kb)
    await state.set_state(OfferFSM.confirm_edit)
    await message.answer("Сохранить изменения?", reply_markup=kb.as_markup())


@router.callback_query(F.data == "confirm_yes", OfferFSM.confirm_edit)
async def confirm_edit_offer(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()

    await update_offer(
        data["offer_id"],
        offer_title=data["offer_title"],
        offer_conditions=data["offer_conditions"],
        gross_bonus=data["gross_bonus"]
    )

    await callback.answer("✅ Оффер обновлён")
    await show_offer_list(callback, state)


@router.callback_query(F.data == "confirm_no", OfferFSM.confirm_edit)
async def cancel_edit_offer(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer("❌ Изменения отменены")
    await show_offer_list(callback, state)


# =========================
# DELETE OFFER
# =========================
@router.callback_query(F.data.startswith("admin_offer:delete:"))
async def delete_offer_confirm(callback: types.CallbackQuery, state: FSMContext):
    offer_id = int(callback.data.split(":")[2])
    await state.update_data(offer_id=offer_id)
    await state.set_state(OfferFSM.confirm_delete)

    kb = InlineKeyboardBuilder()
    confirm_keyboard(kb)
    add_back_button(kb)

    await callback.message.edit_text(
        "❗ Удалить оффер навсегда?",
        reply_markup=kb.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data == "confirm_yes", OfferFSM.confirm_delete)
async def delete_offer_final(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await delete_offer(data["offer_id"])
    await callback.answer("🗑 Оффер удалён")
    await show_offer_list(callback, state)


