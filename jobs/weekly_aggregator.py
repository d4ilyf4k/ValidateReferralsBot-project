import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo  # Python 3.9+
from db.base import get_db_connection

TOP_PRODUCTS = 8  # максимум отображаемых продуктов в PDF
MSK = ZoneInfo("Europe/Moscow")

def get_last_week_period():
    """Возвращает последний полный календарный неделю (Mon–Sun)."""
    today = datetime.now(MSK).date()
    last_monday = today - timedelta(days=today.weekday() + 7)
    last_sunday = last_monday + timedelta(days=6)
    return last_monday, last_sunday

async def generate_weekly_snapshot() -> str:
    """Генерирует snapshot для weekly PDF (immutable contract) с местным временем МСК."""
    start_date, end_date = get_last_week_period()

    async with get_db_connection() as db:
        # ===== SUMMARY =====
        cur = await db.execute("""
            SELECT
                COUNT(*) AS applications,
                COUNT(DISTINCT user_id) AS users
            FROM applications
            WHERE DATE(created_at) BETWEEN ? AND ?
        """, (start_date, end_date))
        row = await cur.fetchone()
        total_apps = row["applications"] or 0
        total_users = row["users"] or 0

        summary = {
            "applications": total_apps,
            "users": total_users
        }

        # ===== PRODUCTS =====
        cur = await db.execute("""
            SELECT
                product_key,
                variant_key,
                COUNT(*) AS applications
            FROM applications
            WHERE DATE(created_at) BETWEEN ? AND ?
            GROUP BY product_key, variant_key
            ORDER BY applications DESC
        """, (start_date, end_date))
        products_raw = [dict(r) for r in await cur.fetchall()]

        # Post-processing: Top N + Others + label + percent
        top_products = products_raw[:TOP_PRODUCTS]
        others_apps = sum(r["applications"] for r in products_raw[TOP_PRODUCTS:])

        products = []
        for r in top_products:
            label = r["product_key"]
            if r.get("variant_key"):
                label = f"{label} / {r['variant_key']}"
            percent = round(r["applications"] / total_apps * 100, 1) if total_apps else 0
            products.append({
                "product_key": r["product_key"],
                "variant_key": r.get("variant_key"),
                "label": label,
                "applications": r["applications"],
                "percent": percent
            })

        if others_apps > 0:
            products.append({
                "product_key": "others",
                "variant_key": None,
                "label": "Others",
                "applications": others_apps,
                "percent": round(others_apps / total_apps * 100, 1)
            })

        # ===== TRAFFIC =====
        cur = await db.execute("""
            SELECT
                COALESCE(u.traffic_source, 'unknown') AS traffic_source,
                COUNT(DISTINCT a.user_id) AS users,
                COUNT(*) AS applications
            FROM applications a
            LEFT JOIN users u ON u.user_id = a.user_id
            WHERE DATE(a.created_at) BETWEEN ? AND ?
            GROUP BY traffic_source
            ORDER BY users DESC
        """, (start_date, end_date))
        traffic = [dict(r) for r in await cur.fetchall()]

        # ===== BANKS =====
        cur = await db.execute("""
            SELECT
                bank_key,
                COUNT(*) AS applications,
                COUNT(DISTINCT user_id) AS users,
                COUNT(DISTINCT product_key || ':' || COALESCE(variant_key, '')) AS products
            FROM applications
            WHERE DATE(created_at) BETWEEN ? AND ?
            GROUP BY bank_key
            ORDER BY applications DESC
        """, (start_date, end_date))
        banks = [dict(r) for r in await cur.fetchall()]

    # ===== Snapshot with MSK time +03:00 =====
    now_msk = datetime.now(MSK)
    snapshot = {
        "meta": {
            "period_start": f"{start_date:%Y-%m-%d}",
            "period_end": f"{end_date:%Y-%m-%d}",
            "generated_at": now_msk.isoformat(timespec="seconds"),  # будет с +03:00
            "week_id": f"{start_date.isocalendar()[0]}-W{start_date.isocalendar()[1]}"
        },
        "summary": summary,
        "products": products,
        "traffic": traffic,
        "banks": banks
    }

    return json.dumps(snapshot, ensure_ascii=False, indent=2)
