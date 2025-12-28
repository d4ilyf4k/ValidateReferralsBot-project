from .base import get_db_connection

async def get_conditions(type_: str, related_key: str):
    async with get_db_connection() as db:
        cursor = await db.execute(
            "SELECT id, text, type, related_key, active FROM conditions WHERE type = ? AND related_key = ? AND active = 1",
            (type_, related_key)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


# -------------------- Добавление нового условия --------------------
async def save_condition(text: str, type_: str, related_key: str, active: int = 1):
    async with get_db_connection() as db:
        await db.execute(
            "INSERT INTO conditions (text, type, related_key, active) VALUES (?, ?, ?, ?)",
            (text, type_, related_key, active)
        )
        await db.commit()


# -------------------- Обновление условия --------------------
async def update_condition(cond_id: int, new_text: str):
    async with get_db_connection() as db:
        await db.execute(
            "UPDATE conditions SET text = ? WHERE id = ?",
            (new_text, cond_id)
        )
        await db.commit()


# -------------------- Удаление условия --------------------
async def delete_condition(cond_id: int):
    async with get_db_connection() as db:
        await db.execute(
            "DELETE FROM conditions WHERE id = ?",
            (cond_id,)
        )
        await db.commit()
        

