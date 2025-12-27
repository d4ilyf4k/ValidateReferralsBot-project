import logging
import pyshorteners
import asyncio

from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from utils.keyboards import get_admin_panel_kb
from utils.traffic_sources import TRAFFIC_SOURCES, DEFAULT_SOURCE
from db.banks import get_active_banks
from db.products import get_products_by_bank
from db.variants import get_variants_by_product
from db.referrals import update_referral_link

logger = logging.getLogger(__name__)
router = Router()

# --------------------
# Админские проверки
# --------------------
def is_admin(user_id: int) -> bool:
    from config import settings
    return user_id in settings.ADMIN_IDS

# --------------------
# FSM состояния
# --------------------
class UpdateLinkFSM:
    select_bank = "update_link_select_bank"
    select_product = "update_link_select_product"
    select_variant = "update_link_select_variant"
    input_link = "update_link_input"


# =========================
# Админ-панель
# =========================
@router.callback_query(F.data == "admin_panel")
async def admin_panel(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("🚫 Доступ запрещён.", show_alert=True)

    await callback.message.edit_text(
        "🛠 <b>Админ-меню</b>",
        reply_markup=get_admin_panel_kb(),
        parse_mode="HTML"
    )
    await callback.answer()

# -----------------------------
# Шаг 1: выбрать банк
# -----------------------------
@router.callback_query(F.data == "admin_update_links")
async def handle_update_link_button(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("🚫 Доступ запрещён.", show_alert=True)
        return

    banks = await get_active_banks()
    if not banks:
        await callback.answer("❌ Нет активных банков", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    for b in banks:
        builder.button(
            text=b["bank_title"],
            callback_data=f"{UpdateLinkFSM.select_bank}:{b['bank_key']}"
        )
    builder.adjust(2)
    kb = builder.as_markup()

    await callback.message.answer(
        "📌 Выберите банк для обновления реферальной ссылки:",
        reply_markup=kb
    )
    await callback.answer()

# -----------------------------
# Шаг 2: выбрать продукт
# -----------------------------
@router.callback_query(F.data.startswith(UpdateLinkFSM.select_bank + ":"))
async def select_bank(callback: types.CallbackQuery, state: FSMContext):
    bank_key = callback.data.split(":")[1]
    await state.update_data(bank_key=bank_key)

    products = await get_products_by_bank(bank_key)
    if not products:
        await callback.message.answer("⚠️ У банка нет продуктов")
        await state.clear()
        return

    builder = InlineKeyboardBuilder()
    for p in products:
        builder.button(
            text=p.get("product_name") or p.get("title") or str(p.get("product_key")),
            callback_data=f"{UpdateLinkFSM.select_product}:{p.get('product_key')}"
        )
    builder.adjust(2)
    kb = builder.as_markup()

    await state.set_state(UpdateLinkFSM.select_product)
    await callback.message.answer(
        "📌 Выберите продукт:",
        reply_markup=kb
    )
    await callback.answer()

# -----------------------------
# Шаг 3: выбрать вариант
# -----------------------------
@router.callback_query(F.data.startswith(UpdateLinkFSM.select_product + ":"))
async def select_product(callback: types.CallbackQuery, state: FSMContext):
    product_key = callback.data.split(":")[1]
    await state.update_data(product_key=product_key)

    data = await state.get_data()
    bank_key = data["bank_key"]
    variants = await get_variants_by_product(bank_key, product_key)

    if not variants:
        # Нет вариантов — сразу идем к вводу ссылки
        await state.set_state(UpdateLinkFSM.input_link)
        await callback.message.answer(
            "📌 Введите ссылку от банка (без UTM, они будут сгенерированы автоматически):\n"
            "Пример:\n<code>https://example.com/offer</code>",
            parse_mode="HTML"
        )
        await callback.answer()
        return

    builder = InlineKeyboardBuilder()
    for v in variants:
        builder.button(
            text=v["title"],
            callback_data=f"{UpdateLinkFSM.select_variant}:{v['variant_key']}"
        )
    builder.adjust(2)
    kb = builder.as_markup()

    await state.set_state(UpdateLinkFSM.select_variant)
    await callback.message.answer(
        "📌 Выберите вариант (или 'Без варианта'):",
        reply_markup=kb
    )
    await callback.answer()

# -----------------------------
# Шаг 4: вариант выбран → ввод ссылки
# -----------------------------
@router.callback_query(F.data.startswith(UpdateLinkFSM.select_variant + ":"))
async def select_variant(callback: types.CallbackQuery, state: FSMContext):
    variant_key = callback.data.split(":")[1]
    if variant_key == "none":
        variant_key = None
    await state.update_data(variant_key=variant_key)
    await state.set_state(UpdateLinkFSM.input_link)

    await callback.message.answer(
        "📌 Введите ссылку от банка (без UTM, они будут сгенерированы автоматически):\n"
        "Пример:\n<code>https://example.com/offer</code>",
        parse_mode="HTML"
    )
    await callback.answer()

# -----------------------------
# Шаг 5: сохранение ссылки
# -----------------------------
@router.message(F.text)
async def update_link_input(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    data = await state.get_data()
    bank_key = data.get("bank_key")
    product_key = data.get("product_key")
    variant_key = data.get("variant_key")

    if not bank_key or not product_key:
        await message.answer("❌ Ошибка состояния. Попробуйте начать заново.")
        await state.clear()
        return

    base_url = message.text.strip()

    if not base_url.startswith(("http://", "https://")):
        await message.answer("❌ URL должен начинаться с http:// или https://")
        return

    success = await update_referral_link(
        bank_key=bank_key,
        product_key=product_key,
        variant_key=variant_key,
        base_url=base_url,
        utm_source=None,
        utm_medium=None,
        utm_campaign=None
    )

    if success:
        await message.answer(
            f"✅ Ссылка успешно сохранена!\n\n"
            f"Банк: {bank_key}\n"
            f"Продукт: {product_key}\n"
            f"Вариант: {variant_key or '—'}\n\n"
            f"🔗 Оригинальная ссылка:\n{base_url}"
        )
    else:
        await message.answer("❌ Ошибка при сохранении ссылки")

    await state.clear()

