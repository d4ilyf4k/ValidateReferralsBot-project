import aiosqlite
import os
from contextlib import asynccontextmanager
from config import settings

DATABASE_URL = settings.DATABASE_URL
if DATABASE_URL.startswith("sqlite:///"):
    DB_PATH = DATABASE_URL.replace("sqlite:///", "")
elif DATABASE_URL.startswith("sqlite:"):
    DB_PATH = DATABASE_URL.replace("sqlite:", "")
else:
    DB_PATH = DATABASE_URL

@asynccontextmanager
async def get_db_connection():
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA busy_timeout=5000;")
    await db.execute("PRAGMA foreign_keys=ON;")
    try:
        yield db
    finally:
        await db.close()

def ensure_db_directory():
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
        
async def table_exists(db, table_name: str) -> bool:
    cur = await db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    return await cur.fetchone() is not None

async def column_exists(db, table_name: str, column_name: str) -> bool:
    cur = await db.execute(f"PRAGMA table_info({table_name})")
    columns = [row["name"] for row in await cur.fetchall()]
    return column_name in columns

async def db_health_check():
    required_tables = {
        "users",
        "referral_progress",
        "financial_data",
        "referral_links",
        "products",
        "offers",
        "applications",
        "banks",
        "variants",
    }

    async with get_db_connection() as db:
        cur = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row["name"] for row in await cur.fetchall()}

    missing = required_tables - tables
    if missing:
        raise RuntimeError(f"❌ Missing DB tables: {missing}")

    print("✅ DB health check passed")