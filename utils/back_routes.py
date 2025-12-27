from handlers.admin_catalog_fsm import AdminCatalogFSM, admin_catalog_entry, get_admin_product_kb, get_admin_bank_kb
from handlers.admin_variant_handlers import AdminVariantFSM
from handlers.admin_offer_fsm import OfferFSM
from utils.keyboards import variants_keyboard, get_admin_offers_list_kb, variant_view_keyboard
from db.variants import get_all_variants, get_variant
from db.offers import get_offer_by_id

BACK_ROUTES = {}


async def variant_view_keyboard_from_state(data):
    bank_key = data.get("bank_key")
    product_key = data.get("product_key")
    variant_key = data.get("variant_key")

    if not bank_key or not product_key or not variant_key:
        return None

    variant = await get_variant(bank_key, product_key, variant_key)
    if not variant:
        return None

    data.setdefault("title", variant.get("title"))
    return variant_view_keyboard(variant)


# -------------------- Catalog FSM --------------------
BACK_ROUTES.update({
    AdminCatalogFSM.banks: {
        "state": AdminCatalogFSM.menu,
        "text": "📦 Управление каталогом",
        "keyboard": lambda _: admin_catalog_entry(),
    },
    AdminCatalogFSM.edit_bank_title: {
        "state": AdminCatalogFSM.banks,
        "text": "🏦 Управление банками",
        "keyboard": lambda _: get_admin_bank_kb(),
    },
    AdminCatalogFSM.add_bank_key: {
        "state": AdminCatalogFSM.banks,
        "text": "🏦 Управление банками",
        "keyboard": lambda _: get_admin_bank_kb(),
    },
    AdminCatalogFSM.add_bank_title: {
        "state": AdminCatalogFSM.banks,
        "text": "🏦 Управление банками",
        "keyboard": lambda _: get_admin_bank_kb(),
    },
    AdminCatalogFSM.products: {
        "state": AdminCatalogFSM.banks,
        "text": "🏦 Управление банками",
        "keyboard": lambda _: get_admin_bank_kb(),
    },
    AdminCatalogFSM.add_product_key: {
        "state": AdminCatalogFSM.products,
        "text": "📝 Продукты банка <b>{bank_key}</b>",
        "keyboard": lambda data: get_admin_product_kb(data["bank_key"]),
        "parse_mode": "HTML",
    },
    AdminCatalogFSM.add_product_title: {
        "state": AdminCatalogFSM.products,
        "text": "📝 Продукты банка <b>{bank_key}</b>",
        "keyboard": lambda data: get_admin_product_kb(data["bank_key"]),
        "parse_mode": "HTML",
    },
})

# -------------------- Variant FSM --------------------
async def variant_list_keyboard(data):
    variants = await get_all_variants(data["bank_key"], data["product_key"])
    return variants_keyboard(variants)

BACK_ROUTES.update({
    AdminVariantFSM.view_variants: {
        "state": AdminCatalogFSM.products,
        "text": "📝 Продукты банка <b>{bank_key}</b>",
        "keyboard": lambda data: get_admin_product_kb(data["bank_key"]),
        "parse_mode": "HTML",
    },
    AdminVariantFSM.view_variant: {
        "state": None,
        "text": None,
        "keyboard": lambda data: {"redirect": f"admin_product:open:{data['product_key']}"},
    },
    AdminVariantFSM.add_title: {
        "state": AdminVariantFSM.view_variants,
        "text": "📄 Варианты продукта <b>{product_key}</b>",
        "keyboard": variant_list_keyboard,
        "parse_mode": "HTML",
    },
    AdminVariantFSM.edit_title: {
        "state": AdminVariantFSM.view_variant,
        "text": "📄 Вариант: <b>{title}</b>",
        "keyboard": variant_view_keyboard_from_state,
        "parse_mode": "HTML",
    },
    AdminVariantFSM.edit_description: {
        "state": AdminVariantFSM.view_variant,
        "text": "📄 Вариант: <b>{title}</b>",
        "keyboard": variant_view_keyboard_from_state,
        "parse_mode": "HTML",
    },
    AdminVariantFSM.confirm_edit: {
        "state": AdminVariantFSM.view_variant,
        "text": "📄 Вариант: <b>{title}</b>",
        "keyboard": variant_view_keyboard_from_state,
        "parse_mode": "HTML",
    },
    AdminVariantFSM.confirm_add: {
        "state": AdminVariantFSM.view_variants,
        "text": "📄 Варианты продукта <b>{product_key}</b>",
        "keyboard": variant_list_keyboard,
        "parse_mode": "HTML",
    },
})

# -------------------- Offer FSM --------------------
async def offer_list_keyboard(data):
    variant_key = data.get("variant_key")
    offer = await get_offer_by_id(variant_key)
    offers = [offer] if offer else []
    return get_admin_offers_list_kb(offers)

BACK_ROUTES.update({
    OfferFSM.view_offers: {
        "state": None,
        "text": None,
        "keyboard": lambda data: {"redirect": f"admin_product:open:{data['product_key']}"},
    },
    OfferFSM.view_offer: {
        "state": None,
        "text": None,
        "keyboard": lambda data: {"redirect": f"admin_product:open:{data['product_key']}"},
    },
    OfferFSM.add_title: {
        "state": None,
        "text": None,
        "keyboard": lambda data: {"redirect": f"admin_product:open:{data['product_key']}"},
    },
    OfferFSM.add_conditions: {
        "state": None,
        "text": None,
        "keyboard": lambda data: {"redirect": f"admin_product:open:{data['product_key']}"},
    },
    OfferFSM.add_bonus: {
        "state": None,
        "text": None,
        "keyboard": lambda data: {"redirect": f"admin_product:open:{data['product_key']}"},
    },
    OfferFSM.confirm_add: {
        "state": None,
        "text": None,
        "keyboard": lambda data: {"redirect": f"admin_product:open:{data['product_key']}"},
    },
    OfferFSM.edit_title: {
        "state": None,
        "text": None,
        "keyboard": lambda data: {"redirect": f"admin_product:open:{data['product_key']}"},
    },
    OfferFSM.edit_conditions: {
        "state": None,
        "text": None,
        "keyboard": lambda data: {"redirect": f"admin_product:open:{data['product_key']}"},
    },
    OfferFSM.edit_bonus: {
        "state": None,
        "text": None,
        "keyboard": lambda data: {"redirect": f"admin_product:open:{data['product_key']}"},
    },
    OfferFSM.confirm_edit: {
        "state": None,
        "text": None,
        "keyboard": lambda data: {"redirect": f"admin_product:open:{data['product_key']}"},
    },
    OfferFSM.confirm_delete: {
        "state": None,
        "text": None,
        "keyboard": lambda data: {"redirect": f"admin_product:open:{data['product_key']}"},
    },
})
