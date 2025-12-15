from database.db_manager import get_user_products_for_finance
from aiogram.types import InlineKeyboardMarkup

BANK_TITLES = {
    "t-bank": "Т-Банк",
    "alpha": "Альфа-Банк"
}

BANK_LABELS = {
    "t-bank": "🏦 Т-Банк",
    "sber": "🏦 СберБанк",
    "vtb": "🏦 ВТБ",
    "alfa": "🏦 Альфа-Банк",
}

async def generate_user_finance_report(user_id: int) -> str:
    products = await get_user_products_for_finance(user_id)
    
    if not products:
        return (
            "💰 <b>Финансовый отчёт</b>\n\n"
            "У вас пока нет оформленных продуктов.\n\n"
            "Выберите банк и карту — после оформления "
            "информация появится здесь."
        )

    lines = [
        "💰 <b>Финансовый отчёт</b>\n",
        "<i>Информация носит справочный характер.</i>\n"
    ]

    for p in products:
        bank_label = BANK_LABELS.get(p["bank"], p["bank"])

    lines.append(
        f"{bank_label}\n"
        f"• Продукт: {p['product_name']}\n"
        f"• Статус: передано банку\n"
    )

    lines.append(
        "\nℹ️ <b>Важно:</b>\n"
        "Бот не начисляет бонусы.\n"
        "Бонусы и сроки зачисления определяются банком."
    )

    return "\n".join(lines)
