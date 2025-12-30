from datetime import datetime
from collections import defaultdict
from db.base import get_db_connection

# ==============================
# Referrer / Admin reports
# Source of truth: applications
# ==============================

async def generate_admin_dashboard_text() -> str:
    """
    Простая текстовая сводка для админа.
    Сейчас выводит только количество пользователей с заявками.
    """
    async with get_db_connection() as db:
        async with db.execute("SELECT COUNT(DISTINCT user_id) FROM applications") as cursor:
            row = await cursor.fetchone()
            users_count = row[0] if row else 0

    text = (
        "📊 <b>Дашборд админа</b>\n\n"
        f"👥 Пользователей с заявками: {users_count}\n\n"
        "Выберите действие ниже:"
    )

    return text


async def get_all_applications():
    """
    Получение всех заявок с актуальными полями.
    Подготовка к будущему экспорту PDF или JSON.
    """
    async with get_db_connection() as db:
        async with db.execute("""
            SELECT
                id,
                user_id,
                bank_key,
                product_key,
                variant_key,
                created_at
            FROM applications
            ORDER BY created_at ASC
        """) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def build_referrer_report():
    """
    Основной отчёт для админа.
    Можно использовать как для JSON, так и для будущего PDF.
    """
    applications = await get_all_applications()
    now = datetime.utcnow().isoformat()

    totals = {
        "applications": len(applications),
        "users": len(set(app["user_id"] for app in applications)),
    }

    by_bank = defaultdict(lambda: {
        "applications": 0,
        "users": set(),
    })

    apps_list = []

    for app in applications:
        totals["applications"] += 1
        by_bank[app["bank_key"]]["applications"] += 1
        by_bank[app["bank_key"]]["users"].add(app["user_id"])

        apps_list.append({
            "application_id": app["id"],
            "user_id": app["user_id"],
            "bank": app["bank_key"],
            "product_key": app["product_key"],
            "variant_key": app.get("variant_key"),
            "created_at": app["created_at"]
        })

    # Преобразуем множества пользователей в число
    by_bank_json = []
    for bank, data in by_bank.items():
        by_bank_json.append({
            "bank": bank,
            "applications": data["applications"],
            "users": len(data["users"])
        })

    return {
        "generated_at": now,
        "totals": totals,
        "by_bank": by_bank_json,
        "applications": apps_list
    }


async def build_weekly_traffic_report(weeks: int = 1):
    async with get_db_connection() as db:
        cursor = await db.execute("""
            SELECT
                strftime('%Y-%W', a.created_at) AS week,
                COALESCE(u.traffic_source, 'unknown') AS traffic_source,
                COUNT(DISTINCT a.user_id) AS users,
                COUNT(a.id) AS applications
            FROM applications a
            LEFT JOIN users u ON u.user_id = a.user_id
            WHERE a.created_at >= date('now', ?)
            GROUP BY week, traffic_source
            ORDER BY week DESC
        """, (f"-{weeks * 7} days",))

        rows = await cursor.fetchall()

    report = defaultdict(list)
    for r in rows:
        report[r["week"]].append({
            "traffic_source": r["traffic_source"],
            "users": r["users"],
            "applications": r["applications"]
        })

    return dict(report)


def render_weekly_report_text(data: dict) -> str:
    lines = ["📆 <b>Еженедельный отчёт</b>\n"]

    for week, rows in data.items():
        lines.append(f"🗓 <b>Неделя {week}</b>")
        for r in rows:
            lines.append(
                f"• {r['traffic_source']}\n"
                f"  👥 Пользователи: {r['users']}\n"
                f"  📦 Заявки: {r['applications']}"
            )
        lines.append("")

    return "\n".join(lines)


# ==============================
# Optional helpers
# ==============================

async def export_referrer_report_to_json():
    """Алиас для экспорта отчёта в JSON"""
    return await build_referrer_report()

# TODO: В будущем можно добавить функцию export_referrer_report_to_pdf()
# которая будет брать результат build_referrer_report() и конвертировать его в PDF
