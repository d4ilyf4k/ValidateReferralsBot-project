from typing import Optional, Dict, Any
from .base import get_db_connection
import logging

logger = logging.getLogger(__name__)

ALLOWED_USER_FIELDS = {
    "traffic_source",
    "full_name"
}


async def create_user(user_id: int, full_name: str, source: Optional[str]) -> bool:
    """
    Создает пользователя без телефона
    """
    traffic_source = (source or "organic")[:32]

    async with get_db_connection() as db:
        try:
            await db.execute("""
                INSERT INTO users (
                    user_id, full_name, traffic_source
                ) VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    full_name = excluded.full_name,
                    traffic_source = excluded.traffic_source
            """, (user_id, full_name, traffic_source))

            # Создаём пустые записи для прогресса рефералов и финансов
            await db.execute(
                "INSERT OR IGNORE INTO referral_progress (user_id) VALUES (?)",
                (user_id,)
            )
            await db.commit()
            return True

        except Exception as e:
            logger.exception(f"❌ create_user error: {e}")
            return False


async def user_exists(user_id: int) -> bool:
    async with get_db_connection() as db:
        cur = await db.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
        return await cur.fetchone() is not None


async def update_user_field(user_id: int, field: str, value: Any) -> bool:
    if field not in ALLOWED_USER_FIELDS:
        return False

    async with get_db_connection() as db:
        await db.execute(
            f"UPDATE users SET {field} = ? WHERE user_id = ?",
            (value, user_id)
        )
        await db.commit()
        return True


async def delete_user_all_data(user_id: int) -> bool:
    async with get_db_connection() as db:
        try:
            await db.execute(
                "DELETE FROM users WHERE user_id = ?",
                (user_id,)
            )
            await db.commit()
            return True
        except Exception:
            logger.exception("delete_user_all_data failed")
            return False


async def anonymize_user(user_id: int) -> bool:
    async with get_db_connection() as db:
        try:
            await db.execute("""
                UPDATE users
                SET 
                    full_name = '[deleted]',
                    traffic_source = 'deleted'
                WHERE user_id = ?
            """, (user_id,))

            await db.commit()
            return True

        except Exception as e:
            logger.exception(f"❌ anonymize_user error: {e}")
            return False

async def get_user_full_data(user_id: int):
    async with get_db_connection() as db:
        cur = await db.execute("""
            SELECT
                user_id,
                full_name,
                traffic_source
            FROM users
            WHERE user_id = ?
        """, (user_id,))
        row = await cur.fetchone()
        return dict(row) if row else None
    
async def get_user(user_id: int) -> dict | None:
    """Возвращает данные пользователя по user_id, либо None, если пользователя нет."""
    async with get_db_connection() as db:
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None