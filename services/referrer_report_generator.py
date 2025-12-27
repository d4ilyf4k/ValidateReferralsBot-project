from datetime import datetime
from collections import defaultdict

from db.base import get_db_connection

# ==============================
# Referrer / Admin JSON reports
# Source of truth: applications
# ==============================

async def generate_admin_dashboard_text() -> str:
    async with get_db_connection() as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            row = await cursor.fetchone()
            users_count = row[0] if row else 0

        async with db.execute("SELECT COUNT(*) FROM referrals") as cursor:
            row = await cursor.fetchone()
            referrals_count = row[0] if row else 0

        async with db.execute("SELECT COUNT(*) FROM referrals WHERE status = 'pending'") as cursor:
            row = await cursor.fetchone()
            pending_count = row[0] if row else 0

        async with db.execute("SELECT COUNT(*) FROM referrals WHERE status = 'approved'") as cursor:
            row = await cursor.fetchone()
            approved_count = row[0] if row else 0

    return (
        "📊 <b>Дашборд админа</b>\n\n"
        f"👥 Пользователей: {users_count}\n"
        f"🔗 Рефералов: {referrals_count}\n"
        f"⏳ В ожидании: {pending_count}\n"
        f"✅ Подтверждено: {approved_count}"
    )


async def get_all_applications():
    async with get_db_connection() as db:
        async with db.execute("""
            SELECT
                a.id,
                a.user_id,
                a.bank_key,
                a.product_key,
                a.status,
                a.gross_bonus,
                a.created_at
            FROM applications a
            ORDER BY a.created_at ASC
        """) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def build_referrer_json_report():
    """
    Main referrer/admin JSON report.
    Used for analytics, exports, dashboards.
    """
    applications = await get_all_applications()

    now = datetime.utcnow().isoformat()

    totals = {
        "applications": 0,
        "approved": 0,
        "pending": 0,
        "rejected": 0,
        "total_profit": 0
    }

    by_bank = defaultdict(lambda: {
        "applications": 0,
        "approved": 0,
        "pending": 0,
        "rejected": 0,
        "profit": 0
    })

    apps_json = []

    for app in applications:
        totals["applications"] += 1
        by_bank[app["bank_key"]]["applications"] += 1

        status = app["status"]
        totals[status] += 1
        by_bank[app["bank_key"]][status] += 1

        if status == "approved":
            totals["total_profit"] += app["gross_bonus"]
            by_bank[app["bank_key"]]["profit"] += app["gross_bonus"]

        apps_json.append({
            "application_id": app["id"],
            "user_id": app["user_id"],
            "bank": app["bank_key"],
            "product_key": app["product_key"],
            "status": status,
            "gross_bonus": app["gross_bonus"],
            "created_at": app["created_at"]
        })

    by_bank_json = []
    for bank, data in by_bank.items():
        by_bank_json.append({
            "bank": bank,
            **data
        })

    return {
        "generated_at": now,
        "totals": totals,
        "by_bank": by_bank_json,
        "applications": apps_json
    }


# ==============================
# Optional helpers
# ==============================


async def export_referrer_report_to_json():
    """Alias helper for clarity / future extension."""
    return await build_referrer_json_report()
