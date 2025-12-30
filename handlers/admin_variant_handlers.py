from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db.variants import (
    get_all_variants,
    get_variant,
    add_variant,
    toggle_variant,
    generate_variant_key,
    update_variant
)
from utils.keyboards import add_back_button, confirm_keyboard

router = Router()

class AdminVariantFSM(StatesGroup):
    view_variants = State()
    view_variant = State()
    add_title = State()
    add_description = State()
    confirm_add = State()
    edit_title = State()
    edit_description = State()
    confirm_edit = State()


# =========================
# Helper: показать список вариантов
# =========================
async def show_variant_list(target, state: FSMContext):
    """
    Показывает список вариантов продукта с названием, описанием, статусом и кнопками.
    """
    data = await state.get_data()
    bank_key = data.get("bank_key")
    product_key = data.get("product_key")

    if not bank_key or not product_key:
        await target.answer("⚠️ Сначала выберите банк и продукт", show_alert=True)
        return

    variants = await get_all_variants(bank_key, product_key)
    await state.set_state(AdminVariantFSM.view_variants)

    kb = InlineKeyboardBuilder()
    for v in variants:
        status = "🟢" if v["is_active"] else "🔴"
        text = f"{status} {v['title']} — {v['description'] or '—'}"
        kb.button(
            text=text,
            callback_data=f"admin_variant:view:{v['variant_key']}"
        )

    kb.button(
        text="➕ Добавить вариант",
        callback_data=f"admin_variant:add:{product_key}"
    )

    add_back_button(kb, back_data=f"admin_product:open:{product_key}:{bank_key}")
    kb.adjust(1)

    if isinstance(target, types.CallbackQuery):
        await target.message.edit_text(
            f"📄 Варианты продукта <b>{product_key}</b>:\n\nНазвание — Описание",
            reply_markup=kb.as_markup(),
            parse_mode="HTML"
        )
        await target.answer()
    else:
        await target.answer(
            f"📄 Варианты продукта <b>{product_key}</b>:\n\nНазвание — Описание",
            reply_markup=kb.as_markup(),
            parse_mode="HTML"
        )


# =========================
# Entry point: открыть список вариантов
# =========================
@router.callback_query(F.data.startswith("admin_variant:open:"))
async def admin_variant_open(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    if len(parts) < 3:
        await callback.answer("⚠️ Некорректные данные", show_alert=True)
        return

    product_key = parts[2]
    data = await state.get_data()
    bank_key = data.get("bank_key", "unknown_bank")

    await state.update_data(
        bank_key=bank_key,
        product_key=product_key,
        parent_type="product",
        parent_key=product_key
    )

    await show_variant_list(callback, state)


# =========================
# Просмотр варианта
# =========================
@router.callback_query(F.data.startswith("admin_variant:view:"))
async def admin_variant_view(callback: types.CallbackQuery, state: FSMContext):
    variant_key = callback.data.split(":")[2]
    data = await state.get_data()
    bank_key = data.get("bank_key")
    product_key = data.get("product_key")

    if not bank_key or not product_key:
        await callback.answer("⚠️ Ошибка: не выбран банк или продукт", show_alert=True)
        return

    variant = await get_variant(bank_key, product_key, variant_key)
    if not variant:
        await callback.answer("⚠️ Вариант недоступен", show_alert=True)
        return

    await state.update_data(
        variant_key=variant_key,
        title=variant["title"],
        description=variant["description"]
    )
    await state.set_state(AdminVariantFSM.view_variant)

    kb = InlineKeyboardBuilder()
    # Кнопки для редактирования, удаления, включения/выключения
    kb.button(text="✏️ Редактировать вариант", callback_data=f"admin_variant:edit:{variant_key}")
    kb.button(
        text="🟢 Вкл/🔴 Выкл",
        callback_data=f"admin_variant:toggle:{variant_key}:{int(not variant['is_active'])}"
    )
    add_back_button(kb, back_data=f"admin_variant:open:{product_key}")

    await callback.message.edit_text(
        f"Вариант: <b>{variant['title']}</b>\n\nОписание:\n{variant['description'] or '—'}",
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


# =========================
# Добавление варианта
# =========================
@router.callback_query(F.data.startswith("admin_variant:add"))
async def admin_variant_add(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminVariantFSM.add_title)
    kb = InlineKeyboardBuilder()
    add_back_button(kb)
    await callback.message.edit_text(
        "Введите название нового варианта:",
        reply_markup=kb.as_markup()
    )
    await callback.answer()


@router.message(AdminVariantFSM.add_title)
async def admin_variant_add_title(message: types.Message, state: FSMContext):
    title = message.text.strip()
    if not title:
        await message.answer("⚠️ Название не может быть пустым")
        return
    await state.update_data(title=title)
    await state.set_state(AdminVariantFSM.add_description)
    await message.answer("Введите описание варианта (или отправьте /skip):")


@router.message(AdminVariantFSM.add_description)
async def admin_variant_add_description(message: types.Message, state: FSMContext):
    description = None if message.text.strip() == "/skip" else message.text.strip()
    await state.update_data(description=description)

    data = await state.get_data()
    title = data.get("title")

    kb = InlineKeyboardBuilder()
    confirm_keyboard(kb)
    add_back_button(kb)

    await state.set_state(AdminVariantFSM.confirm_add)
    await message.answer(
        f"Создать вариант?\n\nНазвание: {title}\nОписание: {description or '—'}",
        reply_markup=kb.as_markup()
    )


@router.callback_query(F.data == "confirm_yes", AdminVariantFSM.confirm_add)
async def admin_variant_confirm_add(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    bank_key = data.get("bank_key")
    product_key = data.get("product_key")
    title = data.get("title")
    description = data.get("description")

    if not all([bank_key, product_key, title]):
        await callback.answer("⚠️ Ошибка: не заполнены данные", show_alert=True)
        return

    variant_key = await generate_variant_key(bank_key, product_key, title)

    await add_variant(
        bank_key=bank_key,
        product_key=product_key,
        variant_key=variant_key,
        title=title,
        description=description
    )

    await callback.answer("✅ Вариант создан")
    await show_variant_list(callback, state)


@router.callback_query(F.data == "confirm_no", AdminVariantFSM.confirm_add)
async def admin_variant_cancel_add(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer("❌ Создание варианта отменено")
    await show_variant_list(callback, state)


# =========================
# Редактирование варианта
# =========================
@router.callback_query(F.data.startswith("admin_variant:edit:"), AdminVariantFSM.view_variant)
async def admin_variant_edit_start(callback: types.CallbackQuery, state: FSMContext):
    variant_key = callback.data.split(":")[2]
    data = await state.get_data()
    bank_key = data.get("bank_key")
    product_key = data.get("product_key")

    if not bank_key or not product_key:
        await callback.answer("⚠️ Ошибка: не выбран банк или продукт", show_alert=True)
        return

    variant = await get_variant(bank_key, product_key, variant_key)
    if not variant:
        await callback.answer("⚠️ Вариант недоступен", show_alert=True)
        return

    await state.update_data(
        variant_key=variant_key,
        title=variant["title"],
        description=variant["description"]
    )
    await state.set_state(AdminVariantFSM.edit_title)

    kb = InlineKeyboardBuilder()
    add_back_button(kb)
    await callback.message.edit_text(
        f"✏️ Редактирование варианта:\nТекущее название: {variant['title']}\n\n"
        "Отправьте новое название или /skip, чтобы оставить без изменений",
        reply_markup=kb.as_markup()
    )
    await callback.answer()


@router.message(AdminVariantFSM.edit_title)
async def admin_variant_edit_title(message: types.Message, state: FSMContext):
    new_title = message.text.strip()
    if new_title != "/skip" and new_title:
        await state.update_data(title=new_title)
    await state.set_state(AdminVariantFSM.edit_description)
    await message.answer("Введите новое описание или /skip, чтобы оставить без изменений:")


@router.message(AdminVariantFSM.edit_description)
async def admin_variant_edit_description(message: types.Message, state: FSMContext):
    new_description = None if message.text.strip() == "/skip" else message.text.strip()
    await state.update_data(description=new_description)

    data = await state.get_data()
    title = data.get("title")
    description = data.get("description")

    kb = InlineKeyboardBuilder()
    confirm_keyboard(kb)
    add_back_button(kb)

    await state.set_state(AdminVariantFSM.confirm_edit)
    await message.answer(
        f"Сохранить изменения?\n\nНазвание: {title}\nОписание: {description or '—'}",
        reply_markup=kb.as_markup()
    )


@router.callback_query(F.data == "confirm_yes", AdminVariantFSM.confirm_edit)
async def admin_variant_confirm_edit(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await update_variant(
        bank_key=data["bank_key"],
        product_key=data["product_key"],
        variant_key=data["variant_key"],
        title=data["title"],
        description=data["description"]
    )
    await callback.answer("✅ Вариант обновлён")
    await show_variant_list(callback, state)


@router.callback_query(F.data == "confirm_no", AdminVariantFSM.confirm_edit)
async def admin_variant_cancel_edit(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer("❌ Изменения отменены")
    await show_variant_list(callback, state)


# =========================
# Включение/выключение варианта
# =========================
@router.callback_query(F.data.startswith("admin_variant:toggle:"))
async def admin_variant_toggle(callback: types.CallbackQuery, state: FSMContext):
    _, _, variant_key, is_active = callback.data.split(":")
    data = await state.get_data()

    await toggle_variant(
        bank_key=data["bank_key"],
        product_key=data["product_key"],
        variant_key=variant_key,
        is_active=int(is_active)
    )

    await callback.answer("✅ Статус варианта обновлён")
    await show_variant_list(callback, state)


# =========================
# Кнопка "Назад" к списку вариантов
# =========================
@router.callback_query(F.data == "admin_variant:list")
async def admin_variant_back_to_list(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data.get("bank_key") or not data.get("product_key"):
        await callback.answer("⚠️ Контекст продукта утерян", show_alert=True)
        return

    await show_variant_list(callback, state)
