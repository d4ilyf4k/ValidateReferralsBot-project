from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from utils.keyboards import add_back_button
from db.products import get_products_by_bank, toggle_product_active
from db.variants import get_all_variants

router = Router()


# =========================
# Получение продукта по ключу
# =========================
async def get_product_by_key(bank_key: str, product_key: str):
    products = await get_products_by_bank(bank_key)
    return next((p for p in products if p["product_key"] == product_key), None)

@router.callback_query(F.data.startswith("admin_product:open:"))
async def admin_product_open(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    if len(parts) < 3:
        await callback.answer("⚠️ Ошибка: некорректные данные", show_alert=True)
        return

    product_key = parts[2]

    data = await state.get_data()
    bank_key = data.get("bank_key")
    if not bank_key:
        await callback.answer("⚠️ Контекст банка не найден", show_alert=True)
        return

    await state.update_data(
        bank_key=bank_key,
        product_key=product_key,
        parent_type="product",
        parent_key=product_key
    )

    products = await get_products_by_bank(bank_key)
    product = next((p for p in products if p["product_key"] == product_key), None)
    if not product:
        await callback.answer("⚠️ Продукт не найден", show_alert=True)
        return

    variants = await get_all_variants(bank_key, product_key)

    kb = InlineKeyboardBuilder()

    # Статус продукта
    status = "🟢 Включен" if product.get("is_active", False) else "🔴 Выключен"
    kb.button(text=f"{status} 🔄", callback_data=f"admin_product:toggle:{product_key}")

    # Добавить оффер продукта
    kb.button(
        text="➕ Добавить оффер продукта",
        callback_data=f"admin_offer:open:product:{product_key}"
    )

    # Список вариантов
    for v in variants:
        v_status = "🟢" if v.get("is_active", False) else "🔴"
        kb.button(
            text=f"{v_status} {v.get('title', 'Без названия')}",
            callback_data=f"admin_variant:view:{v.get('variant_key', '')}"
        )

    # Добавить вариант
    kb.button(
        text="➕ Добавить вариант",
        callback_data=f"admin_variant:add:{product_key}"
    )

    # Кнопка назад к банку
    add_back_button(kb, back_data=f"admin_bank:open:{bank_key}")
    kb.adjust(1)

    await callback.message.edit_text(
        f"📄 Продукт: <b>{product.get('title', product_key)}</b>\n🏦 Банк: <b>{bank_key}</b>",
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_product:toggle:"))
async def admin_toggle_product(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    if len(parts) < 3:
        await callback.answer("⚠️ Некорректные данные", show_alert=True)
        return

    product_key = ":".join(parts[2:])

    bank_key = parts[1]
    if not bank_key:
        await callback.answer("⚠️ Не удалось определить банк", show_alert=True)
        return

    await toggle_product_active(product_key)

    products = await get_products_by_bank(bank_key)
    kb = InlineKeyboardBuilder()
    for p in products:
        status_text = "✅ Активен" if p.get("is_active") else "❌ Неактивен"
        kb.button(
            text=f"{p.get('title', p['product_key'])} — {status_text}",
            callback_data=f"admin_product:toggle:{p['product_key']}"
        )
    kb.button(text="◀️ Назад", callback_data=f"admin_bank:open:{bank_key}")
    kb.adjust(1)

    await callback.message.edit_text(
        "🛠 Управление продуктами:",
        reply_markup=kb.as_markup()
    )
    await callback.answer("Статус продукта изменён")