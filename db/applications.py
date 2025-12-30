from typing import Optional, List
from .base import get_db_connection

# =========================
# APPLICATIONS (future-ready)
# =========================

async def create_application(
    user_id: int,
    bank_key: str,
    product_key: str,
    variant_key: str | None = None,
    traffic_source: str | None = None,
):
    async with get_db_connection() as db:
        query = """
            INSERT INTO applications (
                user_id,
                bank_key,
                product_key,
                variant_key,
                traffic_source,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """
        await db.execute(query, (user_id, bank_key, product_key, variant_key, traffic_source))
        await db.commit()


async def get_application_by_id(application_id: int) -> Optional[dict]:
    async with get_db_connection() as db:
        cur = await db.execute(
            "SELECT * FROM applications WHERE id = ?",
            (application_id,)
        )
        row = await cur.fetchone()
        return dict(row) if row else None


async def get_applications_by_user(user_id: int) -> List[dict]:
    async with get_db_connection() as db:
        cur = await db.execute(
            "SELECT * FROM applications WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def get_applications_by_bank(bank_key: str) -> List[dict]:
    async with get_db_connection() as db:
        cur = await db.execute(
            "SELECT * FROM applications WHERE bank_key = ? ORDER BY created_at DESC",
            (bank_key,)
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def get_recent_applications(days: int = 7) -> List[dict]:
    async with get_db_connection() as db:
        cur = await db.execute(
            """
            SELECT *
            FROM applications
            WHERE created_at >= datetime('now', ? || ' days')
            ORDER BY created_at DESC
            """,
            (-days,)
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def get_all_applications() -> List[dict]:
    async with get_db_connection() as db:
        cur = await db.execute(
            "SELECT * FROM applications ORDER BY created_at DESC"
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]
