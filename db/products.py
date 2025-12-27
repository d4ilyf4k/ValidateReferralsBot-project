from .base import get_db_connection


async def create_product(bank_key: str, product_name: str, product_key: str, is_active: int):
    async with get_db_connection() as db:
        query = """
            INSERT INTO products (bank_key, product_name, product_key, is_active)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(bank_key, product_key) DO UPDATE SET
                product_name = excluded.product_name,
                is_active = excluded.is_active
        """
        await db.execute(query, (bank_key, product_name, product_key, is_active))
        await db.commit()

async def add_product(bank_key, product_key, product_name, description):
    async with get_db_connection() as db:
        await db.execute("""
            INSERT INTO products (bank_key, product_key, product_name, description)
            VALUES (?, ?, ?, ?)
            """, (bank_key, product_key, product_name, description))
        await db.commit()

async def add_user_product(user_id: int, bank_key: str, product_key: str, offer_id: int | None = None, gross_bonus: int = 0):
    async with get_db_connection() as db:
        await db.execute("""
            INSERT INTO applications (
                user_id,
                bank_key,
                product_key,
                offer_id,
                gross_bonus,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, 'pending', CURRENT_TIMESTAMP)
        """, (user_id, bank_key, product_key, offer_id, gross_bonus))

        await db.commit()
    
async def get_user_products(user_id: int) -> list[dict]:
    async with get_db_connection() as db:
        cur = await db.execute("""
            SELECT
                bank_key AS bank_key,
                product_key,
                created_at
            FROM applications
            WHERE user_id = ?
            ORDER BY created_at ASC
        """, (user_id,))

        rows = await cur.fetchall()
        return [dict(row) for row in rows]

async def get_products_by_bank(bank_key: str) -> list[dict]:
    async with get_db_connection() as db:
        async with db.execute(
            """
            SELECT product_key, product_name AS title, is_active
            FROM products
            WHERE bank_key = ?
            """,
            (bank_key,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def toggle_product_active(product_key: str) -> bool:
    async with get_db_connection() as db:
        # Переключаем статус в БД
        await db.execute("""
            UPDATE products
            SET is_active = CASE
                WHEN is_active = 1 THEN 0
                ELSE 1
            END
            WHERE product_key = ?
        """, (product_key,))
        await db.commit()

        cursor = await db.execute("SELECT is_active FROM products WHERE product_key = ?", (product_key,))
        row = await cursor.fetchone()
        if row is None:
            raise ValueError(f"Продукт с key={product_key} не найден")

        return bool(row[0])

async def get_all_products():
    async with get_db_connection() as db:
        cursor = await db.execute("""
            SELECT id, bank_key, product_key, product_name, is_active
            FROM products
            ORDER BY bank_key, product_name
        """)
        rows = await cursor.fetchall()
        await cursor.close()
        return [dict(row) for row in rows]
