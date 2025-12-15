import json
from datetime import datetime
from database.db_manager import (
    get_all_referrals_data,
    get_weekly_traffic_aggregation,
    get_admin_finance_summary,
)

BANK_LABELS = {
    "t-bank": "Т-Банк",
    "alpha": "Альфа-Банк",
}


def normalize_bank(bank: str) -> str:
    return BANK_LABELS.get(bank, bank)

async def generate_full_json_report() -> str:
    data = await get_referrer_report_data()
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)

async def get_referrer_report_data() -> list[dict]:
    rows = await get_all_referrals_data()

    users_map: dict[int, dict] = {}

    for row in rows:
        user_id = row["user_id"]

        if user_id not in users_map:
            users_map[user_id] = {
                "user_id": user_id,
                "traffic_source": row.get("traffic_source", "unknown"),
                "products": []
            }

        users_map[user_id]["products"].append({
            "bank": row["bank"],
            "product_key": row["product_key"],
            "product_name": row["product_name"],
            "referrer_bonus": row["referrer_bonus"],
            "progress": row["progress"]
        })

    return list(users_map.values())



async def generate_admin_text_report() -> str:
    data = await get_referrer_report_data()
    totals = data["totals"]

    lines = [
        "📊 <b>Админ-отчёт</b>\n",
        f"👥 Пользователей: <b>{totals['users']}</b>",
        f"📦 Подтверждённых продуктов: <b>{totals['confirmed_products']}</b>",
        f"💰 Доход: <b>{totals['total_profit']:,} ₽</b>",
        "",
        "🏦 <b>По банкам:</b>",
    ]

    for row in data["by_bank"]:
        lines.append(
            f"• {normalize_bank(row['bank'])} — <b>{row['profit']:,} ₽</b>"
        )

    lines.append(
        "\n📅 Обновлено: " +
        data["generated_at"].strftime("%d.%m.%Y %H:%M")
    )

    return "\n".join(lines)


async def generate_admin_dashboard_text() -> str:
    finance = await get_admin_finance_summary()
    traffic = await get_weekly_traffic_aggregation()

    text = (
        "<b>📊 Админ-панель</b>\n\n"
        f"👥 Пользователей: {sum(row['users'] for row in traffic)}\n"
        f"📦 Подтверждено: {finance['total_count']}\n"
        f"💰 Доход: {finance['total_profit']} ₽\n\n"
        "<b>📈 Трафик (7 дней)</b>\n"
    )

    for row in traffic[:5]:
        src = row.get("traffic_source") or "organic"
        text += f"• {src}: {row['users']} пользователей\n"

    return text




