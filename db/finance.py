from typing import List, Dict
from .base import get_db_connection

# =========================
# ADMIN FINANCE — SUMMARY
# =========================

async def get_admin_finance_summary(days: int = 30) -> Dict:
    """
    Возвращает сводку по пользователям и количеству заявок.
    Доход и статусы не учитываются.
    """
    async with get_db_connection() as db:
        cur = await db.execute("SELECT COUNT(DISTINCT user_id) AS total_users FROM users")
        row = await cur.fetchone()
        return {
            "total_users": row["total_users"] if row else 0,
            "total_confirmed": 0,
            "total_bonus": 0,
        }

# =========================
# FINANCE DETAILS
# =========================

async def get_admin_finance_details() -> List[Dict]:
    """
    Детальный список заявок из таблицы applications
    без статусов и доходов.
    """
    async with get_db_connection() as db:
        async with db.execute("""
            SELECT id, user_id, bank_key, product_key, variant_key, created_at
            FROM applications
            ORDER BY created_at DESC
        """) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

# =========================
# TRAFFIC OVERVIEW
# =========================

async def get_admin_traffic_overview() -> List[Dict]:
    """
    Подсчёт пользователей и уникальных продуктов по источникам трафика.
    Учитывает variant_key.
    """
    async with get_db_connection() as db:
        async with db.execute("""
            SELECT traffic_source, COUNT(DISTINCT user_id) AS users
            FROM users
            GROUP BY traffic_source
        """) as cursor:
            users_data = await cursor.fetchall()

        async with db.execute("""
            SELECT a.user_id, a.product_key, a.variant_key, u.traffic_source
            FROM applications a
            LEFT JOIN users u ON a.user_id = u.user_id
        """) as cursor:
            apps_data = await cursor.fetchall()

    overview = {}
    for row in users_data:
        overview[row["traffic_source"]] = {"users": row["users"], "products_selected": 0}

    products_by_source = {}
    for app in apps_data:
        source = app["traffic_source"] or "unknown"
        key = (app["product_key"], app["variant_key"])
        products_by_source.setdefault(source, set()).add(key)

    for source, products in products_by_source.items():
        if source in overview:
            overview[source]["products_selected"] = len(products)
        else:
            overview[source] = {"users": 0, "products_selected": len(products)}

    return [{"traffic_source": k, **v} for k, v in overview.items()]

# =========================
# TRAFFIC PROJECTION
# =========================

async def get_admin_traffic_finance_projection() -> Dict:
    """
    Подсчёт общего количества пользователей.
    Доходы больше не учитываются.
    """
    async with get_db_connection() as db:
        cur = await db.execute("SELECT COUNT(DISTINCT user_id) AS total_users FROM users")
        row = await cur.fetchone()
        total_users = row["total_users"] if row else 0
        return {"total_users": total_users}

# =========================
# USER-SPECIFIC FINANCE
# =========================

async def get_user_applications(user_id: int) -> List[Dict]:
    """
    Список всех заявок пользователя.
    """
    async with get_db_connection() as db:
        async with db.execute("""
            SELECT id, bank_key, product_key, variant_key, created_at
            FROM applications
            WHERE user_id = ?
            ORDER BY created_at DESC
        """, (user_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_user_finance_summary(user_id: int) -> Dict:
    """
    Сводка по заявкам пользователя.
    Доходы и статусы не учитываются.
    """
    apps = await get_user_applications(user_id)
    return {
        "approved_sum": 0,
        "pending_sum": 0,
        "total_applications": len(apps)
    }


