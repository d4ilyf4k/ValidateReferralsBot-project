import aiosqlite
from fastapi import APIRouter, Depends
from pathlib import Path

router = APIRouter()

DB_PATH = Path("db/sqlite.db")  # поправь, если путь другой


@router.get("/summary")
async def get_summary():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # confirmed сумма
        async with db.execute("""
            SELECT COALESCE(SUM(bonus), 0)
            FROM applications
            WHERE status = 'confirmed'
        """) as cursor:
            total_confirmed = (await cursor.fetchone())[0]

        # pending count
        async with db.execute("""
            SELECT COUNT(*)
            FROM applications
            WHERE status = 'pending'
        """) as cursor:
            pending_count = (await cursor.fetchone())[0]

        # confirmed count
        async with db.execute("""
            SELECT COUNT(*)
            FROM applications
            WHERE status = 'confirmed'
        """) as cursor:
            confirmed_count = (await cursor.fetchone())[0]

        # users count
        async with db.execute("""
            SELECT COUNT(DISTINCT user_id)
            FROM applications
        """) as cursor:
            users_count = (await cursor.fetchone())[0]

    return {
        "total_confirmed": total_confirmed,
        "pending_count": pending_count,
        "confirmed_count": confirmed_count,
        "users_count": users_count,
    }
