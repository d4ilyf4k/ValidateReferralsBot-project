from typing import Optional, List
from .base import get_db_connection


# =========================
# OFFERS
# =========================

async def create_or_update_offer(
    bank_key: str,
    parent_type: str,
    parent_key: str,
    offer_title: str,
    offer_conditions: str,
    gross_bonus: int,
    is_active: int
) -> int:
    async with get_db_connection() as db:
        query = """
        INSERT INTO offers (
            bank_key,
            parent_type,
            parent_key,
            offer_title,
            offer_conditions,
            gross_bonus,
            is_active
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(bank_key, parent_type, parent_key, offer_title)
        DO UPDATE SET
            offer_conditions = excluded.offer_conditions,
            gross_bonus = excluded.gross_bonus,
            is_active = excluded.is_active,
            updated_at = CURRENT_TIMESTAMP
        """
        await db.execute(
            query,
            (
                bank_key,
                parent_type,
                parent_key,
                offer_title,
                offer_conditions,
                gross_bonus,
                is_active
            )
        )
        await db.commit()


async def update_offer(
    offer_id: int,
    offer_title: Optional[str] = None,
    offer_conditions: Optional[str] = None,
    gross_bonus: Optional[int] = None,
):
    fields = []
    values = []

    if offer_title is not None:
        fields.append("offer_title = ?")
        values.append(offer_title)

    if offer_conditions is not None:
        fields.append("offer_conditions = ?")
        values.append(offer_conditions)

    if gross_bonus is not None:
        fields.append("gross_bonus = ?")
        values.append(gross_bonus)

    if not fields:
        return

    values.append(offer_id)

    async with get_db_connection() as db:
        await db.execute(
            f"""
            UPDATE offers
            SET {", ".join(fields)},
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            tuple(values)
        )
        await db.commit()


async def get_offer_by_id(offer_id: int) -> Optional[dict]:
    async with get_db_connection() as db:
        async with db.execute(
            "SELECT * FROM offers WHERE id = ?",
            (offer_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_active_offers(
    parent_type: str,
    parent_key: str,
    include_inactive: bool = False
) -> List[dict]:
    async with get_db_connection() as db:
        query = """
            SELECT *
            FROM offers
            WHERE parent_type = ?
              AND parent_key = ?
        """
        params = [parent_type, parent_key]

        if not include_inactive:
            query += " AND is_active = 1"

        query += " ORDER BY created_at DESC"

        async with db.execute(query, tuple(params)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_all_offers(include_inactive: bool = True) -> List[dict]:
    async with get_db_connection() as db:
        if include_inactive:
            query = "SELECT * FROM offers ORDER BY created_at DESC"
            cur = await db.execute(query)
        else:
            query = "SELECT * FROM offers WHERE is_active = 1 ORDER BY created_at DESC"
            cur = await db.execute(query)

        rows = await cur.fetchall()
        return [dict(row) for row in rows]


async def delete_offer(offer_id: int):
    async with get_db_connection() as db:
        await db.execute("DELETE FROM offers WHERE id = ?", (offer_id,))
        await db.commit()


# =========================
# APPLICATIONS (заявки)
# =========================

async def create_application(user_id: int, offer_id: int, bank_key: str, product_key: str, gross_bonus: int):
    async with get_db_connection() as db:
        query = """
            INSERT INTO applications (
                user_id,
                offer_id,
                bank_key,
                product_key,
                gross_bonus
            )
            VALUES (?, ?, ?, ?, ?)
        """
        await db.execute(query, (user_id, offer_id, bank_key, product_key, gross_bonus))
        await db.commit()


async def update_application_status(application_id: int, status: str):
    async with get_db_connection() as db:
        query = """
            UPDATE applications
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """
        await db.execute(query, (status, application_id))
        await db.commit()


async def get_application_by_id(application_id: int) -> Optional[dict]:
    async with get_db_connection() as db:
        cur = await db.execute(
            "SELECT * FROM applications WHERE id = ?",
            (application_id,)
        )
        row = await cur.fetchone()
        return dict(row) if row else None


async def get_pending_applications():
    async with get_db_connection() as db:
        async with db.execute( """
            SELECT
                a.*,
                o.offer_title
            FROM applications a
            JOIN offers o ON o.id = a.offer_id
            WHERE a.status = 'pending'
            ORDER BY a.created_at ASC
        """) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_user_last_pending_application(user_id: int):
    async with get_db_connection() as db:
        async with db.execute("""
            SELECT *
            FROM applications
            WHERE user_id = ?
              AND status = 'pending'
            ORDER BY id DESC
            LIMIT 1
        """) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None
