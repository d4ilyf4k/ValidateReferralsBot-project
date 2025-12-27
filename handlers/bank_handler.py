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
from db.offers import get_offer_by_id
from db.referrals import get_referral_link, shorten_link

router = Router()
logger = logging.getLogger(__name__)

# -------------------- FSM --------------------
class UserCatalogFSM(StatesGroup):
    choosing_bank = State()
    choosing_product = State()
    choosing_variant = State()
    viewing_conditions = State()


# -------------------- helpers --------------------
def append_utm(url: str, query: dict) -> str:
    if isinstance(url, bytes):
        url = url.decode("utf-8")
    parsed = urlparse(url)
    query_str = {k: str(v) for k, v in query.items() if v is not None}
    return urlunparse(parsed._replace(query=urlencode(query_str)))


def build_kb(items: list[dict], callback_prefix: str, back: str | None = None) -> types.InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for item in items:
        key = item.get('product_key')
        if not key:
            continue
        kb.button(
            text=item.get("title", str(key)),
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

    kb.button(
        text=f"✅ Оформить {product_name}",
        callback_data=f"user_offer_apply:{product_key}|0"
    )

    if variants:
        kb.button(
            text="📌 Показать текущие акции",
            callback_data=f"user_product_variants:{product_key}"
        )

    kb.adjust(1)
    await state.set_state(UserCatalogFSM.viewing_conditions)

    await callback.message.edit_text(
        f"🛍 <b>Продукт:</b> {product_name}\nВыберите действие:",
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


# -------------------- show_product_variants --------------------
@router.callback_query(UserCatalogFSM.viewing_conditions, F.data.startswith("user_product_variants:"))
async def show_product_variants(callback: types.CallbackQuery, state: FSMContext):
    product_key = callback.data.split(":", 1)[1]
    data = await state.get_data()
    bank_key = data.get("bank_key")

    variants = await get_variants(bank_key, product_key)
    if not variants:
        await callback.answer("⚠️ Акций нет", show_alert=True)
        return

    kb = InlineKeyboardBuilder()
    for v in variants:
        variant_name = v.get("title") or f"Акция {v.get('variant_key')}"
        kb.button(
            text=variant_name,
            callback_data=f"user_variant:{v.get('variant_key')}"
        )
    kb.adjust(1)

    await state.set_state(UserCatalogFSM.choosing_variant)

    await callback.message.edit_text(
        f"🧩 <b>Текущие акции продукта:</b>",
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


# -------------------- show_standard_conditions --------------------
async def show_standard_conditions(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    product_key = data.get("product_key")

    if not product_key:
        await callback.message.answer(
            "❌ Ошибка: не выбран продукт. Вернитесь в меню.",
            reply_markup=get_user_main_menu_kb()
        )
        await callback.answer()
        return

    kb = InlineKeyboardBuilder()
    kb.button(text="❌ Отказаться", callback_data="offer_cancel")
    kb.button(text="✅ Оформить", callback_data=f"offer_apply:{product_key}|0")
    kb.adjust(1)

    await callback.message.edit_text(
        "📋 <b>Стандартные условия оформления</b>\n\n"
        "После подтверждения вы получите ссылку для оформления.",
        parse_mode="HTML",
        reply_markup=kb.as_markup()
    )
    await callback.answer()


# -------------------- show_conditions --------------------
@router.callback_query(UserCatalogFSM.choosing_variant, F.data.startswith("user_variant:"))
async def show_conditions(callback: types.CallbackQuery, state: FSMContext):
    variant_key = callback.data.split(":", 1)[1]
    offer = await get_offer_by_id(variant_key)

    if not offer:
        await show_standard_conditions(callback, state)
        return

    await state.update_data(
        product_key=str(offer["product_key"]),
        variant_key=str(variant_key)
    )
    await state.set_state(UserCatalogFSM.viewing_conditions)

    kb = InlineKeyboardBuilder()
    kb.button(text="❌ Отказаться", callback_data="offer_cancel")
    kb.button(text="✅ Оформить", callback_data=f"offer_apply:{offer['product_key']}|{variant_key}")
    kb.adjust(1)

    await callback.message.edit_text(
        f"📋 <b>Условия:</b>\n\n{offer['offer_conditions']}",
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


# -------------------- apply_offer --------------------
@router.callback_query(F.data.startswith("offer_apply:"))
async def apply_offer(call: types.CallbackQuery, state: FSMContext):
    try:
        payload = call.data.split(":", 1)[1]
        if not payload:
            raise ValueError("Пустой payload offer_apply")

        product_key, variant_key = payload.split("|") if "|" in payload else (payload, None)

        if variant_key == "0":
            variant_key = None

        data = await state.get_data()
        bank_key = data.get("bank_key")
        traffic_source = data.get("traffic_source", DEFAULT_SOURCE)

        if not bank_key:
            raise ValueError("bank_key отсутствует в FSM")

        base_url = await get_referral_link(
            bank_key=bank_key,
            product_key=str(product_key),
            variant_key=str(variant_key) if variant_key else None,
            shorten=False
        )

        if not base_url:
            raise ValueError(
                f"Ссылка не найдена (bank={bank_key}, product={product_key}, variant={variant_key})"
            )

        final_url = await build_final_referral_url(
            base_url=base_url,
            bank_key=bank_key,
            product_key=str(product_key),
            variant_key=str(variant_key) if variant_key else None,
            traffic_source=traffic_source
        )

        await call.message.answer(
            f"🔗 Ваша ссылка:\n{final_url}",
            disable_web_page_preview=True,
            reply_markup=get_user_main_menu_kb()
        )
        await state.clear()        
        await call.answer()

    except Exception:
        logging.exception("apply_offer failed")

        await call.message.answer(
            "❌ Ссылка временно недоступна.\n"
            "Пожалуйста, выберите продукт заново.",
            reply_markup=get_user_main_menu_kb()
        )
        await call.answer()



# -------------------- cancel_offer --------------------
@router.callback_query(F.data == "offer_cancel")
async def cancel_offer(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("❌ Действие отменено", reply_markup=get_user_main_menu_kb())
    await callback.answer()
