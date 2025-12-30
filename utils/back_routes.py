from handlers.admin_catalog_fsm import AdminCatalogFSM, admin_catalog_entry, get_admin_product_kb, get_admin_bank_kb
from handlers.admin_variant_handlers import AdminVariantFSM
from utils.keyboards import variant_view_keyboard
from db.variants import get_all_variants, get_variant

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
async def variant_list_keyboard_placeholder(data):
    return None

BACK_ROUTES.update({
    AdminVariantFSM.view_variants: {
        "state": AdminCatalogFSM.products,
        "text": "📝 Продукты банка <b>{bank_key}</b>",
        "keyboard": lambda data: get_admin_product_kb(data["bank_key"]),
        "parse_mode": "HTML",
    },
    AdminVariantFSM.add_title: {
        "state": AdminVariantFSM.view_variants,
        "text": "📄 Варианты продукта <b>{product_key}</b>",
        "keyboard": variant_list_keyboard_placeholder,
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
        "keyboard": variant_list_keyboard_placeholder,
        "parse_mode": "HTML",
    },
})