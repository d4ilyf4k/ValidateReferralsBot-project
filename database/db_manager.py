import aiosqlite
import os
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, List, Tuple
from cryptography.fernet import Fernet
from urllib.parse import urlencode, urlparse, urlunparse, parse_qs
from config import settings
from utils.validation import normalize_phone
import hashlib


def make_phone_hash(phone: str) -> str:
    return hashlib.sha256(phone.encode()).hexdigest()

_fernet = Fernet(settings.ENCRYPTION_KEY)

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
    try:
        yield db
    finally:
        await db.close()


async def ensure_db_directory():
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)


async def initialize_database():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA busy_timeout=5000;")
        await db.execute("PRAGMA foreign_keys=ON;")

        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT NOT NULL,
            phone_enc BLOB,
            phone_hash TEXT UNIQUE,
            traffic_source TEXT DEFAULT 'organic',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS user_products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            bank TEXT NOT NULL,
            product_key TEXT NOT NULL,
            product_name TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            conditions_met_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS referral_progress (
            user_id INTEGER PRIMARY KEY,
            card_received INTEGER DEFAULT 0,
            card_activated INTEGER DEFAULT 0,
            card_received_date DATETIME,
            card_activated_date DATETIME,
            purchase_made INTEGER DEFAULT 0,
            first_purchase_date DATETIME,
            first_purchase_amount REAL,
            FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS financial_data (
            user_id INTEGER PRIMARY KEY,
            total_referral_bonus INTEGER DEFAULT 0,
            total_tax INTEGER DEFAULT 0,
            total_referrer_bonus INTEGER DEFAULT 0,
            bonus_details TEXT,
            updated_at DATETIME,
            FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS referral_links (
            bank TEXT NOT NULL,
            product_key TEXT NOT NULL,
            base_url TEXT NOT NULL,
            utm_source TEXT,
            utm_medium TEXT,
            utm_campaign TEXT,
            is_active INTEGER DEFAULT 1,
            updated_at DATETIME,
            PRIMARY KEY (bank, product_key)
        )
        """)


        await db.execute("""
        CREATE TABLE IF NOT EXISTS offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bank TEXT NOT NULL,
            product_key TEXT NOT NULL,
            product_name TEXT NOT NULL,
            gross_bonus INTEGER NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (bank, product_key)
        )
        """)
        
        
        await db.execute("""
            
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            user_product_id INTEGER NOT NULL,
            bank TEXT NOT NULL,
            product_key TEXT NOT NULL,
            product_name TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            confirmed_at TIMESTAMP,
            bonus_amount INTEGER
        )
        """)

        await db.execute("CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_users_phone_hash ON users(phone_hash)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_user_products_user_id ON user_products(user_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_user_products_status ON user_products(status)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_user_products_offer ON user_products(bank, product_key)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_applications_user_id ON applications(user_id)")

        await db.commit()



def encrypt_phone(phone: str) -> bytes:
    return _fernet.encrypt(phone.encode())


def decrypt_phone(phone_enc: Optional[bytes]) -> str:
    if not phone_enc:
        return "[no phone]"
    try:
        return _fernet.decrypt(phone_enc).decode()
    except Exception:
        return "[decrypt error]"


async def create_user(user_id: int, full_name: str, phone: str, source: Optional[str]) -> bool:

    normalized_phone = normalize_phone(phone)
    phone_enc = encrypt_phone(normalized_phone)
    phone_hash = make_phone_hash(normalized_phone)
    traffic_source = (source or "organic")[:32]

    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute("""
                INSERT INTO users (
                    user_id, full_name, phone_enc, phone_hash, traffic_source
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    full_name = excluded.full_name,
                    traffic_source = excluded.traffic_source
            """, (
                user_id,
                full_name,
                phone_enc,
                phone_hash,
                traffic_source
            ))

            await db.execute(
                "INSERT OR IGNORE INTO referral_progress (user_id) VALUES (?)",
                (user_id,)
            )
            await db.execute(
                "INSERT OR IGNORE INTO financial_data (user_id) VALUES (?)",
                (user_id,)
            )

            await db.commit()
            return True

        except Exception as e:
            print(f"❌ create_user error: {e}")
            return False


async def user_exists(user_id: int) -> bool:
    async with get_db_connection() as db:
        cur = await db.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
        return await cur.fetchone() is not None


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


ALLOWED_USER_FIELDS = {
    "traffic_source",
    "full_name"
}


ALLOWED_PROGRESS_FIELDS = {
    "card_received",
    "card_activated",
    "purchase_made",
    "first_purchase_amount",
}



async def get_user_by_phone(phone: str) -> Optional[Dict[str, Any]]:
    normalized = normalize_phone(phone)
    phone_hash = make_phone_hash(normalized)

    async with get_db_connection() as db:
        cursor = await db.execute("""
            SELECT
                u.user_id,
                u.full_name,
                u.traffic_source,
                u.created_at,
                p.card_activated,
                p.purchase_made
            FROM users u
            LEFT JOIN referral_progress p ON p.user_id = u.user_id
            WHERE u.phone_hash = ?
            LIMIT 1
        """, (phone_hash,))

        row = await cursor.fetchone()
        if not row:
            return None

        user = dict(row)
        user["phone"] = normalized
        return user


async def update_user_phone(user_id: int, phone: str) -> bool:
    normalized = normalize_phone(phone)
    phone_enc = encrypt_phone(normalized)
    phone_hash = make_phone_hash(normalized)

    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute("""
                UPDATE users
                SET phone_enc = ?, phone_hash = ?
                WHERE user_id = ?
            """, (phone_enc, phone_hash, user_id))

            await db.commit()
            return True

        except Exception as e:
            print(f"❌ update_user_phone error: {e}")
            return False


async def add_user_product(user_id: int, bank: str, product_key: str, product_name: str) -> int:
    if user_id in settings.ADMIN_IDS:
        print(f"[TEST MODE] add_user_bank ignored for admin {user_id}")
        return
    print("ADD USER PRODUCT:", user_id, bank, product_key)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO user_products (
                user_id,
                bank,
                product_key,
                product_name,
                status
            )
            VALUES (?, ?, ?, ?, 'pending')
        """, (user_id, bank, product_key, product_name))

        await db.commit()

        cur = await db.execute("SELECT last_insert_rowid()")
        row = await cur.fetchone()
        return row[0]
    



async def get_user_products(user_id: int) -> list[dict]:
    async with get_db_connection() as db:
        cur = await db.execute("""
            SELECT
                up.id,
                up.bank,
                up.product_key,
                up.product_name,
                up.status,
                up.created_at,
                COALESCE(o.gross_bonus, 0) AS gross_bonus
            FROM user_products up
            LEFT JOIN offers o
                ON up.bank = o.bank
                AND up.product_key = o.product_key
            WHERE up.user_id = ?
            ORDER BY up.created_at ASC
        """, (user_id,))
        rows = await cur.fetchall()
        return [dict(row) for row in rows]


async def get_or_create_user_product(user_id: int, bank: str, product_key: str, product_name: str) -> int | None:

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        cur = await db.execute("""
            SELECT id FROM user_products
            WHERE user_id = ? AND bank = ? AND product_key = ?
        """, (user_id, bank, product_key))
        row = await cur.fetchone()

        if row:
            return row["id"]

        cur = await db.execute("""
            INSERT INTO user_products (
                user_id, bank, product_key, product_name, status
            )
            VALUES (?, ?, ?, ?, 'pending')
        """, (user_id, bank, product_key, product_name))

        await db.commit()
        return cur.lastrowid



async def get_user_products_for_finance(user_id: int) -> list[dict]:
    async with get_db_connection() as db:
        cur = await db.execute("""
            SELECT
                up.bank,
                up.product_key,
                up.product_name,
                up.status,
                COALESCE(o.gross_bonus, 0) AS gross_bonus
            FROM user_products up
            LEFT JOIN offers o
              ON up.bank = o.bank
             AND up.product_key = o.product_key
            WHERE up.user_id = ?
            ORDER BY up.created_at ASC
        """, (user_id,))
        rows = await cur.fetchall()
        return [dict(row) for row in rows]



async def update_application_status(app_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE applications SET status = ? WHERE id = ?",
            (status, app_id)
        )
        await db.commit()


async def get_user_last_application(user_id: int) -> dict | None:
    async with get_db_connection() as db:
        cur = await db.execute(
            """
            SELECT *
            FROM applications
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (user_id,)
        )
        row = await cur.fetchone()
        return dict(row) if row else None


async def get_pending_applications() -> list[dict]:
    query = """
    SELECT
        id,
        user_id,
        bank,
        product_name,
        status,
        created_at
    FROM applications
    WHERE status = 'pending'
    ORDER BY created_at ASC
    """

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(query)
        rows = await cursor.fetchall()

    return [dict(row) for row in rows]


async def get_application_by_id(app_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        query = """
    SELECT id, user_id, bank, product_key, product_name, status, bonus_amount
    FROM applications
    WHERE id = ?
    """
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(query, (app_id,))
        row = await cursor.fetchone()

    return dict(row) if row else None

async def approve_application(app_id: int, bonus_amount: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE applications
            SET status = 'confirmed',
                bonus_amount = ?,
                confirmed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (bonus_amount, app_id))

        await db.execute("""
            UPDATE user_products
            SET status = 'confirmed'
            WHERE id = (
                SELECT user_product_id
                FROM applications
                WHERE id = ?
            )
        """, (app_id,))

        await db.commit()


async def reject_application(app_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        query = """
    UPDATE applications
    SET status = 'rejected'
    WHERE id = ? AND status = 'pending'
    """
        await db.execute(query, (app_id,))
        await db.commit()


async def get_offer_bonus(bank: str, product_key: str) -> int | None:
    async with get_db_connection() as db:
        cursor = await db.execute("""
            SELECT gross_bonus
            FROM offers
            WHERE bank = ? AND product_key = ?
        """, (bank, product_key))
        row = await cursor.fetchone()
        return row["gross_bonus"] if row else None


async def get_offer_by_product(bank: str, product_key: str) -> dict | None:
    async with get_db_connection() as db:
        cursor = await db.execute(
            """
            SELECT
                bank,
                product_key,
                product_name,
                gross_bonus
            FROM offers
            WHERE bank = ?
              AND product_key = ?
              AND is_active = 1
            """,
            (bank, product_key)
        )
        row = await cursor.fetchone()

    return dict(row) if row else None


async def upsert_offer(bank: str, product_key: str, product_name: str, gross_bonus: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO offers (bank, product_key, product_name, gross_bonus)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(bank, product_key)
            DO UPDATE SET
                gross_bonus = excluded.gross_bonus,
                product_name = excluded.product_name,
                updated_at = CURRENT_TIMESTAMP
            """,
            (bank, product_key, product_name, gross_bonus)
        )
        await db.commit()


async def confirm_user_bonus(user_id: int, bank: str, product_key: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
            UPDATE user_products
            SET
                status = 'confirmed',
                conditions_met_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
              AND bank = ?
              AND product_key = ?
              AND status = 'pending'
        """, (user_id, bank, product_key))
        await db.commit()
        return cur.rowcount > 0


async def reject_user_bonus(user_id: int, bank: str, product_key: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
            UPDATE user_products
            SET
                status = 'rejected'
            WHERE user_id = ?
              AND bank = ?
              AND product_key = ?
              AND status = 'pending'
        """, (user_id, bank, product_key))
        await db.commit()
        return cur.rowcount > 0

async def get_pending_application_by_user(user_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
        SELECT id, user_id, bank, product_key, product_name, status, bonus_amount
        FROM applications
        WHERE user_id = ?
          AND status IN ('pending', 'waiting_confirmation')
        ORDER BY id DESC
        LIMIT 1
        """
        cursor = await db.execute(query, (user_id,))
        row = await cursor.fetchone()

    return dict(row) if row else None


async def get_user_last_pending_application(user_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        query = """
        SELECT
            id,
            user_id,
            bank,
            product_key,
            product_name,
            status,
            created_at
        FROM applications
        WHERE user_id = ?
          AND status = 'pending'
        ORDER BY created_at DESC
        LIMIT 1
        """

        cursor = await db.execute(query, (user_id,))
        row = await cursor.fetchone()

    return dict(row) if row else None


async def get_pending_bonuses() -> list[dict]:
    async with get_db_connection() as db:
        cur = await db.execute("""
            SELECT
                up.user_id,
                up.bank,
                up.product_key,
                up.product_name,
                up.created_at
            FROM user_products up
            JOIN offers o
              ON up.bank = o.bank
             AND up.product_key = o.product_key
            WHERE up.status = 'pending'
            ORDER BY up.created_at ASC
        """)
        rows = await cur.fetchall()
        return [dict(row) for row in rows]


async def get_user_full_data(user_id: int) -> Optional[dict]:
    async with get_db_connection() as db:
        cur = await db.execute("""
            SELECT
                u.user_id,
                u.full_name,
                u.phone_enc,
                u.traffic_source,
                u.created_at,

                COUNT(up.id)                                   AS total_products,
                SUM(CASE WHEN up.status = 'pending' THEN 1 ELSE 0 END)    AS pending_count,
                SUM(CASE WHEN up.status = 'confirmed' THEN 1 ELSE 0 END)  AS confirmed_count,
                SUM(CASE WHEN up.status = 'rejected' THEN 1 ELSE 0 END)   AS rejected_count

            FROM users u
            LEFT JOIN user_products up ON up.user_id = u.user_id
            WHERE u.user_id = ?
            GROUP BY u.user_id
        """, (user_id,))

        row = await cur.fetchone()
        if not row:
            return None

        data = dict(row)
        data["phone"] = decrypt_phone(data.pop("phone_enc", None))
        return data



async def update_user_field(user_id: int, field: str, value: Any) -> bool:
    if field not in ALLOWED_USER_FIELDS:
        return False

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"UPDATE users SET {field} = ? WHERE user_id = ?",
            (value, user_id)
        )
        await db.commit()
        return True


async def update_progress_field(user_id: int, field: str, value: Any) -> bool:
    if field not in ALLOWED_PROGRESS_FIELDS:
        return False

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            f"""
            UPDATE referral_progress
            SET {field} = ?
            WHERE user_id = ?
            """,
            (value, user_id)
        )

        await db.commit()
        return cur.rowcount > 0


async def get_referral_link(bank: str, product_key: str = "main") -> Optional[str]:
    async with get_db_connection() as db:
        cur = await db.execute("""
            SELECT base_url, utm_source, utm_medium, utm_campaign
            FROM referral_links
            WHERE bank = ? AND product_key = ? AND is_active = 1
            LIMIT 1
        """, (bank, product_key))

        row = await cur.fetchone()
        if not row:
            return None

        base_url = row["base_url"]
        params = {
            "utm_source": row["utm_source"],
            "utm_medium": row["utm_medium"],
            "utm_campaign": row["utm_campaign"]
        }

        parsed = urlparse(base_url)
        existing = parse_qs(parsed.query)
        merged = {**existing, **params}
        merged = {k: v[0] if isinstance(v, list) else v for k, v in merged.items()}

        query = urlencode(merged)
        return urlunparse(parsed._replace(query=query))


async def update_referral_link(bank: str, product_key: str, base_url: str, utm_source: str = "telegram", utm_medium: str = "referral", utm_campaign: str = "default") -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute("""
                INSERT INTO referral_links
                (bank, product_key, base_url, utm_source, utm_medium, utm_campaign, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(bank, product_key) DO UPDATE SET
                    base_url = excluded.base_url,
                    utm_source = excluded.utm_source,
                    utm_medium = excluded.utm_medium,
                    utm_campaign = excluded.utm_campaign,
                    updated_at = CURRENT_TIMESTAMP
            """, (bank, product_key, base_url, utm_source, utm_medium, utm_campaign))

            await db.commit()
            return True
        except Exception as e:
            print(f"❌ update_referral_link error: {e}")
            return False


async def get_admin_traffic_overview() -> list[dict]:
    async with get_db_connection() as db:
        cursor = await db.execute("""
            SELECT
                u.traffic_source,
                COUNT(DISTINCT u.user_id) AS users,
                COUNT(up.id) AS products_selected
            FROM users u
            LEFT JOIN user_products up ON up.user_id = u.user_id
            GROUP BY u.traffic_source
            ORDER BY users DESC
        """)
        rows = await cursor.fetchall()

    return [
        {
            "traffic_source": row["traffic_source"] or "unknown",
            "users": row["users"],
            "products_selected": row["products_selected"]
        }
        for row in rows
    ]


async def get_admin_traffic_finance_projection(npd_rate: float = 0.06) -> list[dict]:
    async with get_db_connection() as db:
        cursor = await db.execute("""
            SELECT
                u.traffic_source,
                COUNT(up.id) AS products,
                SUM(o.gross_bonus) AS gross_bonus
            FROM user_products up
            JOIN users u ON u.user_id = up.user_id
            JOIN offers o
              ON o.bank = up.bank
             AND o.product_key = up.product_key
            GROUP BY u.traffic_source
            ORDER BY gross_bonus DESC
        """)
        rows = await cursor.fetchall()

    result = []
    for row in rows:
        gross = row["gross_bonus"] or 0
        net = int(gross * (1 - npd_rate))

        result.append({
            "traffic_source": row["traffic_source"] or "unknown",
            "products": row["products"],
            "gross_bonus": gross,
            "net_bonus": net
        })

    return result



async def get_admin_finance_summary() -> dict:
    async with get_db_connection() as db:

        cur = await db.execute("""
            SELECT
                COUNT(*) AS total_count,
                COALESCE(SUM(o.gross_bonus), 0) AS total_profit
            FROM user_products up
            JOIN offers o
              ON up.bank = o.bank
             AND up.product_key = o.product_key
            WHERE up.status = 'confirmed'
        """)
        summary = await cur.fetchone()

        cur = await db.execute("""
            SELECT
                up.bank,
                COUNT(*) AS cnt,
                COALESCE(SUM(o.gross_bonus), 0) AS profit
            FROM user_products up
            JOIN offers o
              ON up.bank = o.bank
             AND up.product_key = o.product_key
            WHERE up.status = 'confirmed'
            GROUP BY up.bank
            ORDER BY profit DESC
        """)
        banks = await cur.fetchall()

        cur = await db.execute("""
            SELECT
                up.product_name,
                COUNT(*) AS cnt,
                COALESCE(SUM(o.gross_bonus), 0) AS profit
            FROM user_products up
            JOIN offers o
              ON up.bank = o.bank
             AND up.product_key = o.product_key
            WHERE up.status = 'confirmed'
            GROUP BY up.product_key
            ORDER BY cnt DESC
            LIMIT 5
        """)
        products = await cur.fetchall()

        return {
            "total_count": summary["total_count"],
            "total_profit": summary["total_profit"],
            "banks": [dict(b) for b in banks],
            "products": [dict(p) for p in products],
        }


async def get_admin_finance_details():
    async with get_db_connection() as db:
        cursor = await db.execute("""
            SELECT
                up.user_id,
                up.bank,
                up.product_name,
                o.gross_bonus AS bonus,
                u.traffic_source,
                up.created_at
            FROM user_products up
            JOIN offers o
              ON o.bank = up.bank
             AND o.product_key = up.product_key
            JOIN users u
              ON u.user_id = up.user_id
            ORDER BY up.created_at DESC
        """)
        rows = await cursor.fetchall()
        return rows



async def get_all_referrals_data() -> list[dict]:
    async with get_db_connection() as db:
        cursor = await db.execute("""
            SELECT
                u.user_id,
                u.full_name,
                u.phone_enc,
                u.traffic_source,
                u.created_at,

                p.card_received,
                p.card_activated,
                p.purchase_made,

                up.bank,
                up.product_key,
                up.product_name,

                o.gross_bonus
            FROM users u
            LEFT JOIN referral_progress p ON p.user_id = u.user_id
            LEFT JOIN user_products up ON up.user_id = u.user_id
            LEFT JOIN offers o
              ON o.bank = up.bank
             AND o.product_key = up.product_key
            ORDER BY u.created_at DESC
        """)

        rows = await cursor.fetchall()

    result = []

    for row in rows:
        item = dict(row)

        item["phone"] = decrypt_phone(item.pop("phone_enc"))
        item["referrer_bonus"] = item.pop("gross_bonus") or 0
        item["progress"] = {
            "card_received": bool(item.get("card_received")),
            "card_activated": bool(item.get("card_activated")),
            "purchase_made": bool(item.get("purchase_made")),
        }
        result.append(item)

    return result



    
async def get_traffic_sources_stats(days: int = 1) -> list[dict]:
    async with get_db_connection() as db:
        cursor = await db.execute("""
            SELECT
                u.traffic_source,
                COUNT(*) AS users,
                SUM(CASE WHEN p.card_activated = 1 THEN 1 ELSE 0 END) AS activated,
                SUM(CASE WHEN p.purchase_made = 1 THEN 1 ELSE 0 END) AS purchases
            FROM users u
            LEFT JOIN referral_progress p ON p.user_id = u.user_id
            WHERE u.created_at >= date('now', ?)
            GROUP BY u.traffic_source
            ORDER BY users DESC
        """, (f"-{days} days",))

        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def get_weekly_traffic_aggregation() -> list[dict]:
    """
    Статистика по источникам трафика за последние 7 дней.
    """
    async with get_db_connection() as db:
        cursor = await db.execute("""
            SELECT
                u.traffic_source,
                COUNT(DISTINCT u.user_id) AS users,
                SUM(CASE WHEN p.card_activated = 1 THEN 1 ELSE 0 END) AS activated,
                SUM(CASE WHEN p.purchase_made = 1 THEN 1 ELSE 0 END) AS purchases
            FROM users u
            LEFT JOIN referral_progress p ON p.user_id = u.user_id
            WHERE u.created_at >= date('now', '-7 days')
            GROUP BY u.traffic_source
            ORDER BY users DESC
        """)

        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def delete_user_by_phone(phone: str) -> bool:
    normalized = normalize_phone(phone)
    phone_hash = make_phone_hash(normalized)

    async with get_db_connection() as db:
        cursor = await db.execute(
            "SELECT user_id FROM users WHERE phone_hash = ?",
            (phone_hash,)
        )
        row = await cursor.fetchone()
        if not row:
            return False

        return await delete_user_all_data(row["user_id"])



async def delete_user_all_data(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "DELETE FROM users WHERE user_id = ?",
                (user_id,)
            )
            await db.commit()
            return True
        except Exception as e:
            print(f"❌ delete_user_all_data error: {e}")
            return False

async def anonymize_user(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute("""
                UPDATE users
                SET 
                    full_name = '[deleted]',
                    phone_enc = NULL,
                    phone_hash = NULL,
                    traffic_source = 'deleted'
                WHERE user_id = ?
            """, (user_id,))

            await db.execute("""
                UPDATE financial_data
                SET bonus_details = NULL
                WHERE user_id = ?
            """, (user_id,))

            await db.commit()
            return True

        except Exception as e:
            print(f"❌ anonymize_user error: {e}")
            return False
        
        
async def db_health_check():
    required_tables = {
        "users",
        "user_products",
        "applications",
        "offers",
        "referral_links"
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