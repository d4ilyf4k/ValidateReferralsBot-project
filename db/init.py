from .base import get_db_connection


async def initialize_database():
    async with get_db_connection() as db:
        await db.execute("PRAGMA busy_timeout=5000;")
        await db.execute("PRAGMA foreign_keys=ON;")

        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT NOT NULL,
            traffic_source TEXT DEFAULT 'organic',
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
        CREATE TABLE IF NOT EXISTS conditions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            type TEXT NOT NULL,
            related_key INTEGER NOT NULL,
            active TEXT DEFAULT 0
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS referral_links (
            bank_key TEXT NOT NULL,
            product_key TEXT NOT NULL,
            variant_key TEXT NULL,
            base_url TEXT NOT NULL,
            utm_source TEXT,
            utm_medium TEXT,
            utm_campaign TEXT,
            is_active INTEGER DEFAULT 1,
            updated_at DATETIME,
            PRIMARY KEY (bank_key, product_key, variant_key)
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bank_key TEXT NOT NULL,
            product_key TEXT NOT NULL,
            product_name TEXT NOT NULL,
            description TEXT,
            is_active INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (bank_key, product_key)
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS variants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bank_key TEXT NOT NULL,
            product_key TEXT NOT NULL,
            variant_key TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            is_active INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (bank_key, product_key, variant_key)
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bank_key TEXT NOT NULL,
            parent_type TEXT NOT NULL CHECK (parent_type IN ('product', 'variant')),
            parent_key  TEXT NOT NULL,
            offer_title TEXT NOT NULL,
            offer_conditions TEXT NOT NULL,
            gross_bonus INTEGER NOT NULL,
            referral_link TEXT,
            is_active INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (bank_key, parent_type, parent_key, offer_title)
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            offer_id INTEGER NOT NULL,
            bank_key TEXT NOT NULL,
            product_key TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            gross_bonus INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (offer_id) REFERENCES offers(id)
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS banks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bank_key TEXT NOT NULL UNIQUE,
            bank_name TEXT NOT NULL,
            bank_title TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1
        )
        """)

        await db.execute("CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_applications_user_id ON applications(user_id)")

        await db.commit()