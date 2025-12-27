import logging
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from utils.keyboards import add_back_button
from db.base import get_db_connection
from aiogram.filters import StateFilter

router = Router()
logging.basicConfig(level=logging.INFO)

# ==========================
# STATES
# ==========================
class AdminCatalogFSM(StatesGroup):
    menu = State()          # главное меню каталога
    banks = State()         # список банков
    add_bank_key = State()
    add_bank_title = State()
    add_bank_name = State()  # полное название банка
    edit_bank_title = State()
    products = State()      # продукты банка
    add_product_key = State()
    add_product_title = State()
    products_offers_menu = State()


# ==========================
# MAIN MENU
# ==========================
@router.callback_query(F.data == "admin:catalog")
async def admin_catalog_entry(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(AdminCatalogFSM.menu)
    await callback.message.edit_text(
        "📦 Управление каталогом\nВыберите раздел:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏦 Банки", callback_data="admin:catalog:banks")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:back")]
        ])
    )
    await callback.answer()


# ==========================
# BANKS LIST
# ==========================
async def get_admin_bank_kb():
    async with get_db_connection() as db:
        async with db.execute("SELECT bank_key, bank_title, is_active FROM banks") as cursor:
            banks = await cursor.fetchall()

    kb = InlineKeyboardBuilder()
    for bank in banks:
        status = "🟢" if bank["is_active"] else "🔴"
        kb.button(
            text=f"{status} {bank['bank_title']}",
            callback_data=f"admin_bank:open:{bank['bank_key']}"
        )

    kb.button(text="➕ Добавить банк", callback_data="admin_bank:add")
    add_back_button(kb, back_data="admin:catalog")
    kb.adjust(1)
    return kb.as_markup()


@router.callback_query(F.data == "admin:catalog:banks")
async def admin_catalog_banks(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminCatalogFSM.banks)
    await callback.message.edit_text("🏦 Управление банками", reply_markup=await get_admin_bank_kb())
    await callback.answer()


# ==========================
# ADD BANK FSM
# ==========================
@router.callback_query(F.data == "admin_bank:add")
async def admin_add_bank_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminCatalogFSM.add_bank_key)
    await callback.message.edit_text(
        "➕ Добавление нового банка\n\nВведите уникальный ключ банка (например, tb_bank):"
    )
    await callback.answer()


@router.message(AdminCatalogFSM.add_bank_key)
async def admin_add_bank_key(message: types.Message, state: FSMContext):
    bank_key = message.text.strip().lower().replace(" ", "_")
    if len(bank_key) < 2:
        await message.answer("⚠️ Ключ слишком короткий. Попробуйте ещё раз:")
        return

    async with get_db_connection() as db:
        async with db.execute("SELECT 1 FROM banks WHERE bank_key = ?", (bank_key,)) as cursor:
            exists = await cursor.fetchone()

    if exists:
        await message.answer("⚠️ Такой ключ уже существует. Введите другой:")
        return

    await state.update_data(bank_key=bank_key)
    await state.set_state(AdminCatalogFSM.add_bank_title)
    await message.answer("Введите короткое название банка (для меню/кнопок):")


@router.message(AdminCatalogFSM.add_bank_title)
async def admin_add_bank_title(message: types.Message, state: FSMContext):
    bank_title = message.text.strip()
    if len(bank_title) < 2:
        await message.answer("⚠️ Название слишком короткое. Попробуйте ещё раз:")
        return

    await state.update_data(bank_title=bank_title)
    await state.set_state(AdminCatalogFSM.add_bank_name)
    await message.answer("Введите полное название банка (для отображения пользователям):")


@router.message(AdminCatalogFSM.add_bank_name)
async def admin_add_bank_name(message: types.Message, state: FSMContext):
    bank_name = message.text.strip()
    if len(bank_name) < 2:
        await message.answer("⚠️ Слишком короткое название. Попробуйте ещё раз:")
        return

    data = await state.get_data()
    bank_key = data["bank_key"]
    bank_title = data["bank_title"]

    async with get_db_connection() as db:
        await db.execute(
            "INSERT INTO banks (bank_key, bank_name, bank_title, is_active) VALUES (?, ?, ?, 1)",
            (bank_key, bank_name, bank_title)
        )
        await db.commit()

    await state.set_state(AdminCatalogFSM.banks)
    markup = await get_admin_bank_kb()
    await message.answer(
        f"✅ Банк <b>{bank_name}</b> добавлен с ключом <code>{bank_key}</code>",
        parse_mode="HTML",
        reply_markup=markup
    )


# ==========================
# SINGLE BANK & PRODUCTS
# ==========================
@router.callback_query(F.data.startswith("admin_bank:open:"))
async def admin_single_bank(callback: types.CallbackQuery, state: FSMContext):
    bank_key = callback.data.split(":", 2)[2]

    async with get_db_connection() as db:
        db.row_factory = lambda cursor, row: {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

        async with db.execute("SELECT * FROM banks WHERE bank_key = ?", (bank_key,)) as cursor:
            bank = await cursor.fetchone()

        if not bank:
            await callback.answer("⚠️ Банк не найден", show_alert=True)
            return

        await state.update_data(bank_key=bank_key)
        await state.set_state(AdminCatalogFSM.products)

        async with db.execute(
            "SELECT product_key, product_name, is_active FROM products WHERE bank_key = ?", (bank_key,)
        ) as cursor:
            products = await cursor.fetchall()

    kb = InlineKeyboardBuilder()
    for p in products:
        status = "🟢" if p["is_active"] else "🔴"
        kb.button(
            text=f"{status} {p['product_name']}",
            callback_data=f"admin_product:open:{p['product_key']}:{bank_key}"
        )

    kb.button(text="➕ Добавить продукт", callback_data=f"admin_product:add:{bank_key}")
    add_back_button(kb, back_data="admin:catalog:banks")
    await callback.message.edit_text(
        f"📄 Продукты банка: {bank['bank_name']}",
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


# ==========================
# EDIT BANK FSM
# ==========================
@router.callback_query(F.data.startswith("admin_bank:edit:"))
async def admin_edit_bank_start(callback: types.CallbackQuery, state: FSMContext):
    bank_key = callback.data.split(":", 2)[2]
    async with get_db_connection() as db:
        async with db.execute("SELECT bank_title FROM banks WHERE bank_key = ?", (bank_key,)) as cursor:
            bank = await cursor.fetchone()
    if not bank:
        await callback.answer("⚠️ Банк не найден", show_alert=True)
        return
    await state.update_data(bank_key=bank_key)
    await state.set_state(AdminCatalogFSM.edit_bank_title)
    await callback.message.edit_text(
        f"✏️ Редактирование банка <b>{bank['bank_title']}</b>\n\nВведите новое название:",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminCatalogFSM.edit_bank_title)
async def admin_edit_bank_title(message: types.Message, state: FSMContext):
    new_title = message.text.strip()
    if len(new_title) < 2:
        await message.answer("⚠️ Слишком короткое название. Попробуйте ещё раз:")
        return
    data = await state.get_data()
    bank_key = data["bank_key"]
    async with get_db_connection() as db:
        await db.execute("UPDATE banks SET bank_title = ? WHERE bank_key = ?", (new_title, bank_key))
        await db.commit()
    await state.set_state(AdminCatalogFSM.banks)
    await message.answer(
        f"✅ Название банка обновлено: <b>{new_title}</b>",
        parse_mode="HTML",
        reply_markup=await get_admin_bank_kb()
    )


# ==========================
# TOGGLE BANK ACTIVE
# ==========================
@router.callback_query(F.data.startswith("admin_bank:toggle:"))
async def admin_toggle_bank(callback: types.CallbackQuery):
    bank_key = callback.data.split(":", 2)[2]
    async with get_db_connection() as db:
        async with db.execute("SELECT is_active, bank_title FROM banks WHERE bank_key = ?", (bank_key,)) as cursor:
            bank = await cursor.fetchone()
    if not bank:
        await callback.answer("⚠️ Банк не найден", show_alert=True)
        return
    new_status = 0 if bank["is_active"] else 1
    async with get_db_connection() as db:
        await db.execute("UPDATE banks SET is_active = ? WHERE bank_key = ?", (new_status, bank_key))
        await db.commit()
    await callback.answer(
        f"Статус банка <b>{bank['bank_title']}</b> изменён на: {'Активен' if new_status else 'Неактивен'}",
        show_alert=True
    )
    await callback.message.edit_text(
        "🏦 Управление банками",
        reply_markup=await get_admin_bank_kb()
    )


# ==========================
# PRODUCTS FSM
# ==========================
async def get_admin_product_kb(bank_key):
    async with get_db_connection() as db:
        async with db.execute(
            "SELECT product_key, product_name, is_active FROM products WHERE bank_key = ?", (bank_key,)
        ) as cursor:
            products = await cursor.fetchall()

    kb = InlineKeyboardBuilder()
    for p in products:
        status = "🟢" if p["is_active"] else "🔴"
        kb.button(
            text=f"{status} {p['product_name']}",
            callback_data=f"admin_product:open:{p['product_key']}"
        )

    kb.button(text="➕ Добавить продукт", callback_data=f"admin_product:add:{bank_key}")
    add_back_button(kb, back_data=f"admin_bank:open:{bank_key}")
    kb.adjust(1)
    return kb.as_markup()


@router.callback_query(F.data.startswith("admin_product:add:"))
async def admin_add_product_start(callback: types.CallbackQuery, state: FSMContext):
    bank_key = callback.data.split(":", 2)[2]
    await state.update_data(bank_key=bank_key)
    await state.set_state(AdminCatalogFSM.add_product_key)
    await callback.message.edit_text(
        f"➕ Добавление продукта для банка <b>{bank_key}</b>\n\nВведите уникальный ключ продукта:",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminCatalogFSM.add_product_key)
async def admin_add_product_key(message: types.Message, state: FSMContext):
    product_key = message.text.strip().lower().replace(" ", "_")
    data = await state.get_data()
    bank_key = data["bank_key"]
    async with get_db_connection() as db:
        async with db.execute(
            "SELECT 1 FROM products WHERE product_key = ? AND bank_key = ?", (product_key, bank_key)
        ) as cursor:
            exists = await cursor.fetchone()
    if exists:
        await message.answer("⚠️ Такой ключ продукта уже существует. Введите другой:")
        return
    await state.update_data(product_key=product_key)
    await state.set_state(AdminCatalogFSM.add_product_title)
    await message.answer("Введите название продукта (отображаемое пользователям):")


@router.message(AdminCatalogFSM.add_product_title)
async def admin_add_product_title(message: types.Message, state: FSMContext):
    product_name = message.text.strip()
    data = await state.get_data()
    bank_key = data.get("bank_key")
    product_key = data.get("product_key")

    if not bank_key:
        await message.answer("⚠️ Ошибка: не выбран банк", show_alert=True)
        return

    async with get_db_connection() as db:
        await db.execute(
            "INSERT INTO products (bank_key, product_key, product_name, is_active) VALUES (?, ?, ?, 1)",
            (bank_key, product_key, product_name)
        )
        await db.commit()
    await state.set_state(AdminCatalogFSM.products)
    await message.answer(
        f"✅ Продукт <b>{product_name}</b> добавлен в банк <b>{bank_key}</b>",
        parse_mode="HTML",
        reply_markup=await get_admin_product_kb(bank_key)
    )


# ==========================
# PRODUCT SELECT MENU
# ==========================
@router.callback_query(F.data.startswith("admin_product:select:"))
async def admin_product_select(callback: types.CallbackQuery, state: FSMContext):
    product_key = callback.data.split(":", 2)[2]

    data = await state.get_data()
    bank_key = data.get("bank_key")
    if not bank_key:
        await callback.answer("⚠️ Ошибка: банк не выбран", show_alert=True)
        return

    await state.update_data(product_key=product_key)
    await state.set_state(AdminCatalogFSM.products_offers_menu)

    kb = InlineKeyboardBuilder()
    kb.button(
        text="🛍 Управление продуктами",
        callback_data=f"admin_product:open:{product_key}:{bank_key}"
    )
    kb.button(
        text="🎯 Управление офферами",
        callback_data=f"admin_product:variants:{product_key}:{bank_key}"
    )
    add_back_button(kb, back_data=f"admin_bank:open:{bank_key}")
    kb.adjust(1)

    await callback.message.edit_text(
        "Выберите действие для продукта:",
        reply_markup=kb.as_markup()
    )
    await callback.answer()
