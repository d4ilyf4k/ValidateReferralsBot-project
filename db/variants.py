
import re
import unicodedata
from .base import get_db_connection

async def add_variant(bank_key: str, product_key: str, variant_key: str, title: str, description: str | None = None, is_active: int = 1) -> None:
    async with get_db_connection() as db:
        query = """
            INSERT INTO variants (
                bank_key,
                product_key,
                variant_key,
                title,
                description,
                is_active
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """
        await db.execute(query, (bank_key, product_key, variant_key, title, description, is_active))
        await db.commit()
        
async def get_variant(bank_key: str, product_key: str, variant_key: str) -> dict | None:
    async with get_db_connection() as db:
        async with db.execute("""
            SELECT
                id,
                variant_key,
                title,
                description,
                is_active
            FROM variants
            WHERE bank_key = ?
              AND product_key = ?
              AND variant_key = ?
            LIMIT 1
        """,
            (bank_key, product_key, variant_key)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def get_variants(bank_key: str, product_key: str):
    async with get_db_connection() as db:
        query = """
            SELECT variant_key, title
            FROM variants
            WHERE bank_key = ? AND product_key = ?
            ORDER BY id
        """
        async with db.execute(query, (bank_key, product_key)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_all_variants(bank_key: str, product_key: str) -> list[dict]:
    async with get_db_connection() as db:
        async with db.execute("""
            SELECT
                id,
                variant_key,
                title,
                description,
                is_active
            FROM variants
            WHERE bank_key = ? AND product_key = ?
            ORDER BY id ASC
        """, (bank_key, product_key)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def toggle_variant(bank_key: str, product_key: str, variant_key: str, is_active: int) -> None:
    async with get_db_connection() as db:
        query = """
            UPDATE variants
            SET is_active = ?
            WHERE bank_key = ?
              AND product_key = ?
              AND variant_key = ?
        """
        await db.execute(query, (is_active, bank_key, product_key, variant_key))
        await db.commit()

async def update_variant(bank_key: str, product_key: str, variant_key: str, title: str, description: str):
    async with get_db_connection() as db:
        query = """
            UPDATE variants
            SET title = :title,
                description = :description
            WHERE bank_key = :bank_key
            AND product_key = :product_key
            AND variant_key = :variant_key
        """
        await db.execute(query, {
            "title": title,
            "description": description,
            "bank_key": bank_key,
            "product_key": product_key,
            "variant_key": variant_key
        })
        await db.commit()

async def get_variants_by_product(bank_key: str, product_key: str) -> list[dict]:
    async with get_db_connection() as db:
        async with db.execute(
            """
            SELECT variant_key, title, description, is_active
            FROM variants
            WHERE bank_key = ? AND product_key = ?
            """,
            (bank_key, product_key)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def update_variant_description(bank_key: str, product_key: str, variant_key: str, description: str | None) -> None:
    async with get_db_connection() as db:
        query = """
            UPDATE variants
            SET description = ?
            WHERE bank_key = ?
              AND product_key = ?
              AND variant_key = ?
        """
        await db.execute(query, (description, bank_key, product_key, variant_key))
        await db.commit()

def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[\s_-]+", "_", text).strip("_")
    return text

async def generate_variant_key(bank_key: str, product_key: str, title: str) -> str:
    base_key = slugify(title)

    async with get_db_connection() as db:
        async with db.execute("""
            SELECT variant_key
            FROM variants
            WHERE bank_key = ?
              AND product_key = ?
              AND variant_key LIKE ?
        """, (bank_key, product_key, f"{base_key}%")) as cursor:
            rows = await cursor.fetchall()

    existing = {row["variant_key"] for row in rows}

    # если ключ свободен — берём его
    if base_key not in existing:
        return base_key

    # иначе добавляем постфикс
    i = 2
    while f"{base_key}_{i}" in existing:
        i += 1

    return f"{base_key}_{i}"
