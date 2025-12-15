import json
from datetime import datetime, timedelta
from database.db_manager import get_db_connection

def get_last_week_period():
    today = datetime.now().date()
    last_monday = today - timedelta(days=today.weekday() + 7)
    last_sunday = last_monday + timedelta(days=6)

    return last_monday, last_sunday


async def generate_weekly_snapshot() -> str:
    start_date, end_date = get_last_week_period()

    async with get_db_connection() as db:
        # --- summary ---
        summary_query = """
        SELECT
            COUNT(DISTINCT u.user_id) AS new_users,
            COUNT(up.id) AS products,
            COALESCE(SUM(o.gross_bonus), 0) AS gross_income
        FROM users u
        LEFT JOIN user_products up
            ON up.user_id = u.user_id
           AND DATE(up.created_at) BETWEEN ? AND ?
        LEFT JOIN offers o
            ON up.bank = o.bank
           AND up.product_key = o.product_key
        WHERE DATE(u.created_at) BETWEEN ? AND ?
        """

        cursor = await db.execute(
            summary_query,
            (start_date, end_date, start_date, end_date)
        )
        row = await cursor.fetchone()

        summary = {
            "new_users": row["new_users"] or 0,
            "products": row["products"] or 0,
            "gross_income": row["gross_income"] or 0,
        }

        # --- by traffic source ---
        source_query = """
        SELECT
            u.traffic_source,
            COUNT(DISTINCT u.user_id) AS users,
            COUNT(up.id) AS products,
            COALESCE(SUM(o.gross_bonus), 0) AS gross_income
        FROM users u
        LEFT JOIN user_products up
            ON up.user_id = u.user_id
           AND DATE(up.created_at) BETWEEN ? AND ?
        LEFT JOIN offers o
            ON up.bank = o.bank
           AND up.product_key = o.product_key
        WHERE DATE(u.created_at) BETWEEN ? AND ?
        GROUP BY u.traffic_source
        """

        cursor = await db.execute(
            source_query,
            (start_date, end_date, start_date, end_date)
        )
        rows = await cursor.fetchall()

        by_source = {}
        for row in rows:
            source = row["traffic_source"] or "unknown"
            by_source[source] = {
                "users": row["users"] or 0,
                "products": row["products"] or 0,
                "gross_income": row["gross_income"] or 0
            }

    result = {
        "period": f"{start_date:%d.%m.%Y} — {end_date:%d.%m.%Y}",
        "generated_at": datetime.utcnow().isoformat(),
        "summary": summary,
        "by_traffic_source": by_source
    }

    return json.dumps(result, ensure_ascii=False, indent=2)


async def get_weekly_traffic_stats(days: int = 7):
    since = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")

    async with get_db_connection() as db:
        cursor = await db.execute("""
            SELECT 
                u.traffic_source,
                COUNT(DISTINCT u.user_id) AS users,
                COUNT(up.id) AS products
            FROM users u
            LEFT JOIN user_products up ON up.user_id = u.user_id
            WHERE date(u.created_at) >= ?
            GROUP BY u.traffic_source
            ORDER BY users DESC
        """, (since,))

        rows = await cursor.fetchall()
        return [dict(r) for r in rows]



async def get_weekly_finance_stats(days: int = 7):
    since = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")

    async with get_db_connection() as db:
        cursor = await db.execute("""
            SELECT
                COUNT(up.id) AS products,
                COALESCE(SUM(o.gross_bonus), 0) AS gross_income
            FROM user_products up
            JOIN offers o
              ON up.bank = o.bank
             AND up.product_key = o.product_key
            WHERE date(up.created_at) >= ?
        """, (since,))

        row = await cursor.fetchone()
        return dict(row) if row else {
            "products": 0,
            "gross_income": 0
        }