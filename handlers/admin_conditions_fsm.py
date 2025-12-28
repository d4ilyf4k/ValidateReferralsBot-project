from aiogram import Router, types, F
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db.products import get_all_products
from db.variants import get_all_variants
from db.conditions import (
    get_conditions,
    save_condition,
    update_condition,
    delete_condition,
)

router = Router()


# ================= FSM =================

class AdminConditionsFSM(StatesGroup):
    ChoosingTarget = State()
    ViewingConditions = State()
    AddingCondition = State()
    EditingCondition = State()
    ConfirmingDelete = State()


# -------------------- Главное меню условий --------------------
@router.callback_query(F.data == "admin_conditions")
async def admin_conditions_menu(callback: types.CallbackQuery, state: FSMContext):
    kb = InlineKeyboardBuilder()
    products = await get_all_products()
    for product in products:
        kb.button(text=f"Продукт: {product['product_name']}", callback_data=f"cond_product_{product['product_key']}")
    # варианты
    variants = []
    for product in products:
        bank_key = product["bank_key"]
        product_key = product["product_key"]
        variants_for_product = await get_all_variants(bank_key, product_key)
        variants.extend(variants_for_product)
    for variant in variants:
        kb.button(text=f"Вариант: {variant['title']}", callback_data=f"cond_variant_{variant['variant_key']}")

    kb.button(text="◀️ Назад", callback_data="admin_panel")
        
    kb.adjust(1)
    await callback.message.edit_text(
        "Выберите продукт или вариант для управления условиями:",
        reply_markup=kb.as_markup()
    )
    await state.set_state(AdminConditionsFSM.ChoosingTarget)
    await callback.answer()


# -------------------- Функция для генерации меню условий --------------------
async def generate_conditions_menu(type_: str, target_id: str):
    conditions = await get_conditions(type_, target_id)
    kb = InlineKeyboardBuilder()
    # Кнопки с существующими условиями
    for c in conditions:
        kb.button(text=f"{c['text'][:30]}...", callback_data=f"view_cond_{c['id']}")
    kb.button(text="➕ Добавить новое", callback_data="add_condition")
    kb.button(text="◀️ Назад", callback_data="admin_conditions")
    kb.adjust(1)
    return kb


# -------------------- Выбор продукта или варианта --------------------
@router.callback_query(F.data.startswith(("cond_product_", "cond_variant_")))
async def choose_target(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    type_ = parts[1]  # product или variant
    target_id = parts[2]
    await state.update_data(target_type=type_, target_id=target_id)

    kb = await generate_conditions_menu(type_, target_id)
    await callback.message.edit_text(
        "Выберите действие с условиями:",
        reply_markup=kb.as_markup()
    )
    await state.set_state(AdminConditionsFSM.ViewingConditions)
    await callback.answer()

# -------------------- Обработка кнопок действий с условием --------------------
@router.callback_query(F.data.startswith(("view_cond_", "add_condition", "edit_condition", "delete_condition")))
async def condition_actions(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()

    # Добавление нового условия
    if callback.data == "add_condition":
        await state.set_state(AdminConditionsFSM.AddingCondition)
        await callback.message.edit_text("Введите текст нового условия (можно вводить несколько условий подряд):")
        await callback.answer()
        return

    # Просмотр конкретного условия
    if callback.data.startswith("view_cond_"):
        cond_id = callback.data.split("_")[-1]
        await state.update_data(edit_cond_id=cond_id)   

        kb = InlineKeyboardBuilder()
        kb.button(text="✏️ Редактировать", callback_data="edit_condition")
        kb.button(text="🗑 Удалить", callback_data="delete_condition")
        kb.button(text="◀️ Назад", callback_data=f"{data['target_type']}_{data['target_id']}")
        kb.adjust(1)

        await callback.message.edit_text("Выберите действие с условием:", reply_markup=kb.as_markup())
        await state.set_state(AdminConditionsFSM.ViewingConditions)
        await callback.answer()
        return

    # Редактирование условия
    if callback.data == "edit_condition":
        await state.set_state(AdminConditionsFSM.EditingCondition)
        await callback.message.edit_text("Введите новый текст для условия:")
        await callback.answer()
        return

    # Удаление условия
    if callback.data == "delete_condition":
        await state.set_state(AdminConditionsFSM.ConfirmingDelete)
        await callback.message.edit_text("Введите 'да' для удаления условия:")
        await callback.answer()
        return

# -------------------- Добавление нового условия --------------------
@router.message(AdminConditionsFSM.AddingCondition)
async def add_condition_finish(message: types.Message, state: FSMContext):
    data = await state.get_data()
    type_ = data["target_type"]
    target_id = data["target_id"]

    # Разбиваем текст на строки, чтобы каждое условие сохранялось отдельно
    lines = [line.strip() for line in message.text.split("\n") if line.strip()]
    for line in lines:
        await save_condition(line, type_, target_id)

    # После добавления оставляем состояние AddingCondition для ввода следующего
    kb = await generate_conditions_menu(type_, target_id)
    await message.answer("Условие добавлено ✅", reply_markup=kb.as_markup())
    await message.answer("Введите следующий пункт условия или нажмите ◀️ Назад, чтобы выйти:")
    await state.set_state(AdminConditionsFSM.AddingCondition)


# -------------------- Редактирование условия --------------------
@router.message(AdminConditionsFSM.EditingCondition)
async def edit_condition_finish(message: types.Message, state: FSMContext):
    data = await state.get_data()
    cond_id = data["edit_cond_id"]
    await update_condition(cond_id, message.text)

    kb = await generate_conditions_menu(data["target_type"], data["target_id"])
    await message.answer("Условие обновлено ✅", reply_markup=kb.as_markup())
    await state.set_state(AdminConditionsFSM.ViewingConditions)


# -------------------- Удаление условия --------------------
@router.message(AdminConditionsFSM.ConfirmingDelete)
async def delete_condition_finish(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if message.text.lower() != "да":
        kb = await generate_conditions_menu(data["target_type"], data["target_id"])
        await message.answer("Удаление отменено ❌", reply_markup=kb.as_markup())
        await state.set_state(AdminConditionsFSM.ViewingConditions)
        return

    await delete_condition(data["edit_cond_id"])
    kb = await generate_conditions_menu(data["target_type"], data["target_id"])
    await message.answer("Условие удалено ✅", reply_markup=kb.as_markup())
    await state.set_state(AdminConditionsFSM.ViewingConditions)