import json
from datetime import datetime, timedelta

from db.base import get_db_connection

# ==================================
# Weekly analytics (NEW ARCHITECTURE)
# Source of truth: applications
# ==================================


def get_last_week_period():
    """
    Returns last full calendar week (Mon–Sun).
    """
    today = datetime.utcnow().date()
    last_monday = today - timedelta(days=today.weekday() + 7)
    last_sunday = last_monday + timedelta(days=6)
    return last_monday, last_sunday


async def generate_weekly_snapshot() -> str:
    """
    Weekly JSON snapshot for admin / analytics.
    Uses applications as the only source of truth.
    """
    start_date, end_date = get_last_week_period()

    async with get_db_connection() as db:
        # --- summary ---
        summary_query = """
            SELECT
                COUNT(*) AS applications,
                SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) AS approved,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) AS pending,
                SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) AS rejected,
                COALESCE(SUM(CASE WHEN status = 'approved' THEN gross_bonus END), 0) AS gross_income
            FROM applications
            WHERE DATE(created_at) BETWEEN ? AND ?
        """

        cur = await db.execute(summary_query, (start_date, end_date))
        row = await cur.fetchone()

        summary = {
            "applications": row["applications"] or 0,
            "approved": row["approved"] or 0,
            "pending": row["pending"] or 0,
            "rejected": row["rejected"] or 0,
            "gross_income": row["gross_income"] or 0,
        }

        # --- by bank ---
        by_bank_query = """
            SELECT
                bank_key,
                COUNT(*) AS applications,
                SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) AS approved,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) AS pending,
                SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) AS rejected,
                COALESCE(SUM(CASE WHEN status = 'approved' THEN gross_bonus END), 0) AS gross_income
            FROM applications
            WHERE DATE(created_at) BETWEEN ? AND ?
            GROUP BY bank_key
            ORDER BY applications DESC
        """

        cur = await db.execute(by_bank_query, (start_date, end_date))
        rows = await cur.fetchall()

        by_bank = []
        for r in rows:
            by_bank.append({
                "bank": r["bank_key"],
                "applications": r["applications"] or 0,
                "approved": r["approved"] or 0,
                "pending": r["pending"] or 0,
                "rejected": r["rejected"] or 0,
                "gross_income": r["gross_income"] or 0,
            })

    result = {
        "period": f"{start_date:%d.%m.%Y} — {end_date:%d.%m.%Y}",
        "generated_at": datetime.utcnow().isoformat(),
        "summary": summary,
        "by_bank": by_bank
    }

    return json.dumps(result, ensure_ascii=False, indent=2)


# ==================================
# Helpers for dashboards / jobs
# ==================================


async def get_weekly_applications_stats(days: int = 7):
    """
    Rolling weekly stats (last N days).
    Useful for dashboards.
    """
    since = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")

    async with get_db_connection() as db:
        query = """
            SELECT
                bank_key,
                COUNT(*) AS applications,
                SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) AS approved,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) AS pending,
                SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) AS rejected,
                COALESCE(SUM(CASE WHEN status = 'approved' THEN gross_bonus END), 0) AS gross_income
            FROM applications
            WHERE DATE(created_at) >= ?
            GROUP BY bank_key
            ORDER BY applications DESC
        """

        cur = await db.execute(query, (since,))
        rows = await cur.fetchall()
        return [dict(r) for r in rows]
