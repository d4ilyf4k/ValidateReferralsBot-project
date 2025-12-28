import logging
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder
from urllib.parse import urlparse, urlencode, urlunparse, parse_qs

from utils.traffic_sources import DEFAULT_SOURCE
from utils.keyboards import get_user_bank_kb, get_user_main_menu_kb
from db.banks import get_active_banks
from db.products import get_products_by_bank
from db.variants import get_variants
from db.referrals import get_referral_link, shorten_link
from db.conditions import get_conditions

router = Router()
logger = logging.getLogger(__name__)

# -------------------- FSM --------------------
class UserCatalogFSM(StatesGroup):
    choosing_bank = State()
    choosing_product = State()
    choosing_variant = State()
    viewing_conditions = State()


# -------------------- helpers --------------------
def build_kb(items: list[dict], callback_prefix: str, back: str | None = None) -> types.InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for item in items:
        key = item.get('product_key') or item.get('variant_key')
        if not key:
            continue
        kb.button(
            text=item.get("product_name") or item.get("title") or str(key),
            callback_data=f"{callback_prefix}:{key}"
        )
    if back:
        kb.button(text="⬅ Назад", callback_data=back)
    kb.adjust(1)
    return kb.as_markup()


async def build_final_referral_url(
    base_url: str,
    bank_key: str,
    product_key: str,
    variant_key: str | None,
    traffic_source: str
) -> str:

    base_url = await get_referral_link(bank_key, product_key, variant_key, shorten=False)
    if not base_url:
        return None

    utm_source = "ReferralFlowBot"
    utm_medium = traffic_source
    utm_campaign = variant_key or product_key

    parsed = urlparse(base_url)
    existing = parse_qs(parsed.query)

    merged = {
        **existing,
        "utm_source": utm_source,
        "utm_medium": utm_medium,
        "utm_campaign": utm_campaign,
    }

    merged = {
        k: v[0] if isinstance(v, list) else v
        for k, v in merged.items()
    }

    final_url = urlunparse(
        parsed._replace(query=urlencode(merged))
    )

    short_url = await shorten_link(final_url)
    return short_url


# -------------------- start: choose_bank --------------------
@router.message(F.text == "🏦 Выбрать банк")
async def choose_bank(message: types.Message, state: FSMContext):
    await state.clear()
    await state.set_state(UserCatalogFSM.choosing_bank)

    kb = await get_user_bank_kb()
    await message.answer("🏦 Выберите банк:", reply_markup=kb)


# -------------------- choose_product --------------------
@router.message(UserCatalogFSM.choosing_bank, F.text.startswith("🏦"))
async def bank_selected(message: types.Message, state: FSMContext):
    bank_title = message.text.replace("🏦", "").strip()
    banks = await get_active_banks()
    bank = next((b for b in banks if b["bank_title"] == bank_title), None)

    if not bank:
        await message.answer("⚠️ Банк не найден")
        return

    await state.update_data(bank_key=bank["bank_key"])
    await state.set_state(UserCatalogFSM.choosing_product)

    products = await get_products_by_bank(bank["bank_key"])
    if not products:
        await message.answer("⚠️ Продукты временно недоступны")
        return

    kb = build_kb(products, "user_product")
    await message.answer("💳 <b>Выберите продукт:</b>", reply_markup=kb, parse_mode="HTML")


# -------------------- choose_variant --------------------
@router.callback_query(UserCatalogFSM.choosing_product, F.data.startswith("user_product:"))
async def choose_product(callback: types.CallbackQuery, state: FSMContext):
    product_key = callback.data.split(":", 1)[1]
    data = await state.get_data()
    bank_key = data.get("bank_key")
    if not bank_key:
        raise RuntimeError("FSM missing bank_key before choose_product")

    products = await get_products_by_bank(bank_key)
    product = next((p for p in products if str(p["product_key"]) == product_key), None)
    if not product:
        await callback.answer("⚠️ Продукт не найден", show_alert=True)
        return

    product_name = product.get("product_name") or product.get("title") or product_key
    await state.update_data(product_key=product_key)

    variants = await get_variants(bank_key, product_key)
    kb = InlineKeyboardBuilder()

    # Кнопка просмотра условий продукта вместо прямого оформления
    kb.button(
        text=f"📋 Показать условия {product_name}",
        callback_data=f"view_product_conditions:{product_key}"
    )

    if variants:
        for v in variants:
            kb.button(
                text=f"📌 Вариант: {v['title']}",
                callback_data=f"user_variant:{v['variant_key']}"
            )

    kb.button(text="⬅ Назад", callback_data="choose_bank")
    kb.adjust(1)
    await state.set_state(UserCatalogFSM.choosing_variant)

    await callback.message.edit_text(
        f"🛍 <b>Продукт:</b> {product_name}\nВыберите действие:",
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


# -------------------- show_conditions --------------------
@router.callback_query(UserCatalogFSM.choosing_variant, F.data.startswith("user_variant:"))
async def show_conditions(callback: types.CallbackQuery, state: FSMContext):
    variant_key = callback.data.split(":", 1)[1]
    data = await state.get_data()
    product_key = data.get("product_key")
    bank_key = data.get("bank_key")

    if not product_key or not bank_key:
        await callback.answer("❌ Ошибка: продукт или банк не выбран.", show_alert=True)
        return

    # Условия варианта
    variant_conditions = await get_conditions("variant", variant_key)
    variant_text = "\n".join(f"{i+1}️⃣ {c['text']}" for i, c in enumerate(variant_conditions)) \
                   if variant_conditions else "Условия для варианта отсутствуют."

    # Условия продукта
    product_conditions = await get_conditions("product", product_key)
    product_text = "\n".join(f"{i+1}️⃣ {c['text']}" for i, c in enumerate(product_conditions)) \
                   if product_conditions else "Условия для продукта отсутствуют."

    # Формируем текст с визуальным разделением
    full_text = (
        f"📌 <b>Общие условия продукта:</b>\n{product_text}\n\n"
        f"📌 <b>Условия варианта:</b>\n{variant_text}"

    )

    kb = InlineKeyboardBuilder()
    kb.button(text="❌ Отказаться", callback_data="cancel_offer")
    kb.button(text="✅ Оформить", callback_data=f"apply_offer:{product_key}|{variant_key}")
    kb.button(text="⬅ Назад", callback_data=f"user_product:{product_key}")
    kb.adjust(1)

    await callback.message.edit_text(
        full_text,
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )
    await state.update_data(variant_key=variant_key)
    await state.set_state(UserCatalogFSM.viewing_conditions)
    await callback.answer()


# -------------------- view_product_conditions --------------------
@router.callback_query(UserCatalogFSM.choosing_variant, F.data.startswith("view_product_conditions:"))
async def view_product_conditions(callback: types.CallbackQuery, state: FSMContext):
    product_key = callback.data.split(":", 1)[1]
    product_conditions = await get_conditions("product", product_key)
    product_text = "\n".join(f"{i+1}️⃣ {c['text']}" for i, c in enumerate(product_conditions)) \
                   if product_conditions else "Условия отсутствуют."

    data = await state.get_data()
    variant_key = data.get("variant_key")

    kb = InlineKeyboardBuilder()
    kb.button(text="❌ Отказаться", callback_data="cancel_offer")
    if variant_key:
        kb.button(text="✅ Оформить", callback_data=f"apply_offer:{product_key}|{variant_key}")
    else:
        kb.button(text="✅ Оформить", callback_data=f"apply_offer:{product_key}|0")
                
    kb.button(text="⬅ Назад", callback_data=f"user_variant:{variant_key}" if variant_key else f"user_product:{product_key}")
    kb.adjust(1)

    await callback.message.edit_text(
        f"📋 <b>Общие условия продукта:</b>\n\n{product_text}",
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


# -------------------- apply_offer --------------------
@router.callback_query(F.data.startswith("apply_offer:"))
async def apply_offer(callback: types.CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        bank_key = data.get("bank_key")
        traffic_source = data.get("traffic_source", DEFAULT_SOURCE)

        payload = callback.data.split(":", 1)[1]
        product_key, variant_key = payload.split("|") if "|" in payload else (payload, None)
        if variant_key == "0":
            variant_key = None

        final_url = await build_final_referral_url(
            base_url=None,
            bank_key=bank_key,
            product_key=str(product_key),
            variant_key=str(variant_key) if variant_key else None,
            traffic_source=traffic_source
        )

        if not final_url:
            raise ValueError("Ссылка не найдена")

        await callback.message.answer(
            f"🔗 Ваша уникальная ссылка:\n{final_url}",
            disable_web_page_preview=True,
            reply_markup=get_user_main_menu_kb()
        )
        await state.clear()
        await callback.answer()

    except Exception:
        logging.exception("apply_offer failed")
        await callback.message.answer(
            "❌ Ссылка временно недоступна.\n"
            "Пожалуйста, выберите продукт заново.",
            reply_markup=get_user_main_menu_kb()
        )
        await callback.answer()


# -------------------- cancel_offer --------------------
@router.callback_query(F.data == "cancel_offer")
async def cancel_offer(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("❌ Действие отменено", reply_markup=get_user_main_menu_kb())
    await callback.answer()
