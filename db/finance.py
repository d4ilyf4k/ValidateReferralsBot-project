from typing import List, Dict
from .base import get_db_connection


# =========================
# ADMIN FINANCE — SUMMARY
# =========================

async def get_admin_finance_summary(days: int = 30) -> Dict:
    async with get_db_connection() as db:
        cur = await db.execute(
            """
            SELECT
                COUNT(DISTINCT up.user_id)                         AS total_users,
                COUNT(up.id)                                       AS total_confirmed,
                COALESCE(SUM(o.gross_bonus), 0)                    AS total_bonus
            FROM user_products up
            JOIN offers o ON o.id = up.offer_id
            WHERE up.status = 'approved'
              AND up.offer_id IS NOT NULL
              AND up.confirmed_at >= date('now', ?)
            """,
            (f"-{days} days",)
        )
        row = await cur.fetchone()

        return {
            "total_users": row["total_users"],
            "total_confirmed": row["total_confirmed"],
            "total_bonus": row["total_bonus"],
        }


# =========================
# FINANCE DETAILS
# =========================

async def get_admin_finance_details(days: int = 30) -> List[Dict]:
    async with get_db_connection() as db:
        cur = await db.execute(
            """
            SELECT
                up.id                      AS record_id,
                up.user_id,
                up.bank_key,
                up.product_key,
                p.product_name,
                o.offer_title,
                o.gross_bonus,
                up.confirmed_at
            FROM user_products up
            JOIN offers o   ON o.id = up.offer_id
            JOIN products p ON p.bank_key = up.bank_key AND p.product_key = up.product_key
            WHERE up.status = 'approved'
              AND up.offer_id IS NOT NULL
              AND up.confirmed_at >= date('now', ?)
            ORDER BY up.confirmed_at DESC
            """,
            (f"-{days} days",)
        )
        rows = await cur.fetchall()
        return [dict(row) for row in rows]


# =========================
# FINANCE BY PRODUCT
# =========================

async def get_admin_finance_by_product(days: int = 30) -> List[Dict]:
    async with get_db_connection() as db:
        cur = await db.execute(
            """
            SELECT
                up.bank_key,
                up.product_key,
                p.product_name,
                COUNT(up.id)                    AS confirmed_count,
                COALESCE(SUM(o.gross_bonus), 0) AS total_bonus
            FROM user_products up
            JOIN offers o   ON o.id = up.offer_id
            JOIN products p ON p.bank_key = up.bank_key AND p.product_key = up.product_key
            WHERE up.status = 'approved'
              AND up.offer_id IS NOT NULL
              AND up.confirmed_at >= date('now', ?)
            GROUP BY up.bank_key, up.product_key
            ORDER BY total_bonus DESC
            """,
            (f"-{days} days",)
        )
        rows = await cur.fetchall()
        return [dict(row) for row in rows]


# =========================
# TRAFFIC OVERVIEW
# =========================

async def get_admin_traffic_overview(days: int = 30) -> List[Dict]:
    async with get_db_connection() as db:
        cur = await db.execute(
            """
            SELECT
                COALESCE(rp.traffic_source, 'unknown') AS traffic_source,
                COUNT(DISTINCT u.user_id)              AS total_users,
                COUNT(up.id)                            AS confirmed_count,
                COALESCE(SUM(o.gross_bonus), 0)         AS total_bonus
            FROM users u
            LEFT JOIN referral_progress rp ON rp.user_id = u.user_id
            LEFT JOIN user_products up
                   ON up.user_id = u.user_id
                  AND up.status = 'approved'
                  AND up.offer_id IS NOT NULL
                  AND up.confirmed_at >= date('now', ?)
            LEFT JOIN offers o ON o.id = up.offer_id
            GROUP BY traffic_source
            ORDER BY total_bonus DESC
            """,
            (f"-{days} days",)
        )
        rows = await cur.fetchall()
        return [dict(row) for row in rows]


# =========================
# TRAFFIC PROJECTION
# =========================

async def get_admin_traffic_finance_projection(days: int = 30) -> Dict:
    async with get_db_connection() as db:
        cur = await db.execute(
            """
            SELECT
                COUNT(DISTINCT u.user_id)      AS total_users,
                COUNT(up.id)                    AS confirmed_count,
                COALESCE(SUM(o.gross_bonus), 0) AS total_bonus
            FROM users u
            LEFT JOIN user_products up
                   ON up.user_id = u.user_id
                  AND up.status = 'approved'
                  AND up.offer_id IS NOT NULL
                  AND up.confirmed_at >= date('now', ?)
            LEFT JOIN offers o ON o.id = up.offer_id
            """,
            (f"-{days} days",)
        )
        row = await cur.fetchone()

        total_users = row["total_users"] or 0
        total_bonus = row["total_bonus"] or 0

        avg_per_user = (
            round(total_bonus / total_users, 2)
            if total_users > 0 else 0
        )

        return {
            "total_users": total_users,
            "total_bonus": total_bonus,
            "avg_bonus_per_user": avg_per_user,
        }


# =========================
# WEEKLY AGGREGATION
# =========================

async def get_weekly_traffic_aggregation(weeks: int = 8) -> List[Dict]:
    async with get_db_connection() as db:
        cur = await db.execute(
            """
            SELECT
                strftime('%Y-%W', up.confirmed_at) AS week,
                COUNT(up.id)                       AS confirmed_count,
                COALESCE(SUM(o.gross_bonus), 0)    AS total_bonus
            FROM user_products up
            JOIN offers o ON o.id = up.offer_id
            WHERE up.status = 'approved'
              AND up.offer_id IS NOT NULL
              AND up.confirmed_at >= date('now', ?)
            GROUP BY week
            ORDER BY week ASC
            """,
            (f"-{weeks * 7} days",)
        )
        rows = await cur.fetchall()
        return [dict(row) for row in rows]
    
async def get_user_finance_summary(user_id: int):
    async with get_db_connection() as db:
        async with db.execute( """
            SELECT
                COALESCE(SUM(CASE WHEN status = 'approved' THEN gross_bonus END), 0) AS approved_sum,
                COALESCE(SUM(CASE WHEN status = 'pending' THEN gross_bonus END), 0) AS pending_sum
            FROM applications
            WHERE user_id = ?
        """) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_user_applications(user_id: int):
    async with get_db_connection() as db:
        async with db.execute("""
            SELECT
                id,
                bank_key,
                product_key,
                gross_bonus,
                status,
                created_at
            FROM applications
            WHERE user_id = ?
            ORDER BY created_at DESC
        """) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]