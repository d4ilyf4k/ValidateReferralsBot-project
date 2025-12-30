# ================================
# LEGACY / DEPRECATED
# ================================
# Использовалось в старой логике OfferFSM
# и истории заявок пользователя.
#
# В текущей архитектуре:
# - заявки не сохраняются
# - статус и бонусы не отслеживаются
# - пользователь получает только ссылку
#
# Оставлено временно:
# - для возможного возврата логики
# - для аналитики в будущем
#
# НЕ ИСПОЛЬЗОВАТЬ В ТЕКУЩЕМ UI
# ================================


from .base import get_db_connection

async def get_user_applications_page(user_id: int, limit: int = 5, offset: int = 0) -> list[dict]:
    async with get_db_connection() as db:
        cur = await db.execute("""
            SELECT
                bank_key,
                product_key,
                status,
                gross_bonus,
                created_at
            FROM applications
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (user_id, limit, offset))

        rows = await cur.fetchall()
        return [dict(row) for row in rows]