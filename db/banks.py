from db.base import get_db_connection


async def get_active_banks():
    async with get_db_connection() as db:
        async with db.execute(
            """
            SELECT bank_key, bank_title, bank_name
            FROM banks
            WHERE is_active = 1
            """
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_bank_by_name(bank_name: str):
    async with get_db_connection() as db:
        async with db.execute(
            """
            SELECT bank_key, bank_title, bank_name
            FROM banks
            WHERE LOWER(bank_name) = LOWER(?)
              AND is_active = 1
            """,
            (bank_name,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def create_bank(bank_key: str, bank_name: str, bank_title: str, is_active: int = 1):
    async with get_db_connection() as db:
        query = """
            INSERT INTO banks (bank_key, bank_name, bank_title, is_active)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(bank_key) DO UPDATE SET
                bank_name = excluded.bank_name,
                bank_title = excluded.bank_title,
                is_active = excluded.is_active
        """
        await db.execute(query, (bank_key, bank_name, bank_title, is_active))
        await db.commit()


async def toggle_bank(bank_key: str, is_active: int):
    async with get_db_connection() as db:
        query = """
            UPDATE banks
            SET is_active = ?
            WHERE bank_key = ?
        """
        await db.execute(query, (is_active, bank_key))
        await db.commit()
