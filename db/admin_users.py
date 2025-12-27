from db.base import get_db_connection


async def get_admin_users_list(limit: int = 50) -> list[dict]:
    async with get_db_connection() as db:
        cur = await db.execute("""
            SELECT
                u.id            AS user_id,
                u.username,
                u.first_name,
                COUNT(a.id)     AS applications_count,
                MAX(a.created_at) AS last_activity
            FROM users u
            LEFT JOIN applications a
                ON a.user_id = u.id
            GROUP BY u.id
            ORDER BY last_activity DESC NULLS LAST
            LIMIT ?
        """, (limit,))

        rows = await cur.fetchall()
        return [dict(row) for row in rows]

async def get_admin_users_page(limit: int = 10, offset: int = 0) -> list[dict]:
    async with get_db_connection() as db:
        cur = await db.execute("""
            SELECT
                u.id AS user_id,
                u.username,
                u.first_name,
                COUNT(a.id) AS applications_count,
                MAX(a.created_at) AS last_activity
            FROM users u
            LEFT JOIN applications a ON a.user_id = u.id
            GROUP BY u.id
            ORDER BY last_activity DESC NULLS LAST
            LIMIT ? OFFSET ?
        """, (limit, offset))

        rows = await cur.fetchall()
        return [dict(row) for row in rows]