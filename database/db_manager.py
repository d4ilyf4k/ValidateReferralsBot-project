import aiosqlite
import os
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from config import settings
from cryptography.fernet import Fernet
from utils.validation import normalize_phone

_fernet = Fernet(settings.ENCRYPTION_KEY)

DATABASE_URL = settings.DATABASE_URL
if DATABASE_URL.startswith('sqlite:///'):
    DB_PATH = DATABASE_URL.replace('sqlite:///', '')
elif DATABASE_URL.startswith('sqlite:'):
    DB_PATH = DATABASE_URL.replace('sqlite:', '')
else:
    DB_PATH = DATABASE_URL

@asynccontextmanager
async def get_db_connection():
    connection = await aiosqlite.connect(DB_PATH)
    connection.row_factory = aiosqlite.Row
    try:
        yield connection
    finally:
        await connection.close()


async def ensure_db_directory():
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

async def initialize_database():
    await ensure_db_directory()
    
    print(f"🔄 Инициализация базы данных по пути: {DB_PATH}")
    
    async with get_db_connection() as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                full_name TEXT NOT NULL,
                phone_enc BLOB NOT NULL,
                bank TEXT NOT NULL,
                selected_product TEXT,
                selected_product_name TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("✅ Таблица users создана/проверена")
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS user_banks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                bank TEXT NOT NULL CHECK (bank IN ('t-bank', 'alpha')),
                selected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, bank)
            )
        ''')
        print("✅ Таблица user_banks создана/проверена")
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS referral_progress (
                user_id INTEGER PRIMARY KEY,
                application_submitted BOOLEAN DEFAULT 0,
                application_date TEXT,
                application_approved BOOLEAN DEFAULT 0,
                approval_date TEXT,
                card_received BOOLEAN DEFAULT 0,
                card_received_date TEXT,
                card_activated BOOLEAN DEFAULT 0,
                card_activated_date TEXT,
                purchase_made BOOLEAN DEFAULT 0,
                first_purchase_date TEXT,
                first_purchase_amount REAL,
                card_last4 TEXT,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
        print("✅ Таблица referral_progress создана/проверена")
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS financial_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE,
                total_referral_bonus INTEGER DEFAULT 0,
                total_your_bonus INTEGER DEFAULT 0,
                total_bonus_status TEXT DEFAULT 'pending',
                bonus_details TEXT,
                referral_bonus_amount INTEGER DEFAULT 0,
                your_bonus_amount INTEGER DEFAULT 0,
                your_bonus_status TEXT DEFAULT 'pending',
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
        print("✅ Таблица financial_data создана/проверена")
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS reminders_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                admin_id INTEGER NOT NULL,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
        print("✅ Таблица reminders_log создана/проверена")
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS referral_links (
                bank TEXT NOT NULL,
                product_key TEXT NOT NULL DEFAULT 'main',
                base_url TEXT NOT NULL,
                utm_source TEXT DEFAULT 'telegram',
                utm_medium TEXT DEFAULT 'referral',
                utm_campaign TEXT DEFAULT 'default',
                offer_id TEXT,
                gross_bonus INTEGER DEFAULT 0,
                net_bonus INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (bank, product_key)
            )
        ''')
        print("✅ Таблица referral_links создана/проверена")
        
        await db.commit()
    
    print("🎉 Инициализация базы данных завершена!")


def encrypt_phone(phone: str) -> bytes:
    """Encrypt phone number for secure storage."""
    return _fernet.encrypt(phone.encode())


def decrypt_phone(encrypted: Optional[bytes]) -> str:
    """Decrypt phone number from storage."""
    if encrypted is None:
        return "[нет телефона]"
    try:
        return _fernet.decrypt(encrypted).decode()
    except Exception:
        return "[ошибка расшифровки]"

async def create_user(user_id: int, full_name: str, phone: str, bank: str) -> bool:
    normalized_phone = normalize_phone(phone)
    phone_enc = encrypt_phone(normalized_phone)
    async with get_db_connection() as db:
        try:
            await db.execute(
                "INSERT INTO users (user_id, full_name, phone_enc, bank) VALUES (?, ?, ?, ?)",
                (user_id, full_name, phone_enc, bank)
            )
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
            print(f"❌ Error creating user: {e}")
            return False


async def user_exists(user_id: int) -> bool:
    async with get_db_connection() as db:
        cursor = await db.execute(
            "SELECT 1 FROM users WHERE user_id = ?",
            (user_id,)
        )
        return await cursor.fetchone() is not None


async def get_user_full_data(user_id: int) -> Optional[Dict[str, Any]]:
    async with get_db_connection() as db:
        cursor = await db.execute("""
            SELECT 
                u.*, 
                p.*, 
                f.*,
                (
                    SELECT GROUP_CONCAT(bank) 
                    FROM user_banks ub 
                    WHERE ub.user_id = u.user_id
                ) as all_banks
            FROM users u
            LEFT JOIN referral_progress p ON u.user_id = p.user_id
            LEFT JOIN financial_data f ON u.user_id = f.user_id
            WHERE u.user_id = ?
        """, (user_id,))
        
        row = await cursor.fetchone()
        if not row:
            return None
        
        user_data = dict(row)
        
        all_banks = user_data.get('all_banks', '')
        user_data['banks'] = all_banks.split(',') if all_banks else []
        
        return user_data


async def get_user_by_phone(phone: str) -> Optional[Dict[str, Any]]:
    normalized_input = normalize_phone(phone)
    async with get_db_connection() as db:
        cursor = await db.execute(
            "SELECT user_id, phone_enc FROM users"
        )
        
        async for row in cursor:
            try:
                stored_phone = decrypt_phone(row["phone_enc"])
                if stored_phone == normalized_input:
                    return await get_user_full_data(row["user_id"])
            except Exception:
                continue
        return None


async def update_user_field(user_id: int, field: str, value: Any) -> bool:
    async with get_db_connection() as db:
        try:
            if field == "phone":
                value = encrypt_phone(value)
            
            await db.execute(
                f"UPDATE users SET {field} = ? WHERE user_id = ?",
                (value, user_id)
            )
            await db.commit()
            return True
        except Exception as e:
            print(f"❌ Error updating user field: {e}")
            return False


async def update_progress_field(user_id: int, field: str, value: Any) -> bool:
    async with get_db_connection() as db:
        try:
            await db.execute(
                f"UPDATE referral_progress SET {field} = ? WHERE user_id = ?",
                (value, user_id)
            )
            await db.commit()
            return True
        except Exception as e:
            print(f"❌ Error updating progress field: {e}")
            return False

async def add_user_bank(user_id: int, bank: str, product_key: Optional[str] = None, product_name: Optional[str] = None) -> bool:
    async with get_db_connection() as db:
        try:
            await db.execute(
                "INSERT OR IGNORE INTO user_banks (user_id, bank) VALUES (?, ?)",
                (user_id, bank)
            )
            
            if product_key or product_name:
                await db.execute("""
                    UPDATE users 
                    SET selected_product = ?, selected_product_name = ?
                    WHERE user_id = ?
                """, (product_key, product_name, user_id))
            
            await db.commit()
            return True
        except Exception as e:
            print(f"❌ Error adding user bank: {e}")
            return False


async def get_user_banks(user_id: int) -> List[str]:
    async with get_db_connection() as db:
        cursor = await db.execute(
            "SELECT bank FROM user_banks WHERE user_id = ? ORDER BY selected_at",
            (user_id,)
        )
        rows = await cursor.fetchall()
        return [row['bank'] for row in rows] if rows else []

async def add_referral_link(bank: str, base_url: str, product_key: str = "main", utm_source: str = "telegram", utm_medium: str = "referral", utm_campaign: str = "default"
) -> bool:
    async with get_db_connection() as db:
        try:
            await db.execute("""
                INSERT OR REPLACE INTO referral_links 
                (bank, product_key, base_url, utm_source, utm_medium, utm_campaign, updated_at) 
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (bank, product_key, base_url, utm_source, utm_medium, utm_campaign))
            
            await db.commit()
            print(f"✅ Referral link added/updated: {bank}/{product_key}")
            return True
        except Exception as e:
            print(f"❌ Error adding referral link: {e}")
            return False


async def get_referral_link(bank: str, product_key: str = "main") -> Optional[str]:
    try:
        async with get_db_connection() as db:
            try:
                cursor = await db.execute("""
                    SELECT url, base_url, utm_source, utm_medium, utm_campaign
                    FROM referral_links 
                    WHERE bank = ? AND product_key = ? AND is_active = 1
                    LIMIT 1
                """, (bank, product_key))
                
                row = await cursor.fetchone()
                if row and row[0]:
                    return row[0]
            except Exception:
                pass
            
            cursor = await db.execute("""
                SELECT 
                    base_url,
                    COALESCE(utm_source, 'telegram') as utm_source,
                    COALESCE(utm_medium, 'referral') as utm_medium,
                    COALESCE(utm_campaign, 'default') as utm_campaign
                FROM referral_links 
                WHERE bank = ? AND product_key = ? AND is_active = 1
                LIMIT 1
            """, (bank, product_key))
            
            row = await cursor.fetchone()
            if not row:
                print(f"⚠️ Активная ссылка не найдена для {bank}/{product_key}")
                return None
            
            base_url = row[0] or ""
            if not base_url:
                print(f"⚠️ Пустой базовый URL для {bank}/{product_key}")
                return None
            
            query_params = {
                "utm_source": row[1],
                "utm_medium": row[2],
                "utm_campaign": row[3]
            }
            
            from urllib.parse import urlencode, urlparse, urlunparse, parse_qs
            
            parsed = urlparse(base_url)
            existing_params = parse_qs(parsed.query) if parsed.query else {}
            
            merged_params = {**existing_params, **query_params}
            for key in merged_params:
                if isinstance(merged_params[key], list):
                    merged_params[key] = merged_params[key][0]
            
            new_query = urlencode(merged_params, safe='/:')
            full_url = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                parsed.fragment
            ))
            
            return full_url
            
    except Exception as e:
        print(f"❌ Ошибка получения ссылки: {e}")
        import traceback
        traceback.print_exc()
        return None



async def update_referral_link(
    bank: str,
    product_key: str,
    base_url: str,
    utm_source: str,
    utm_medium: str,
    utm_campaign: str,
) -> bool:
    try:
        if not base_url.startswith(('http://', 'https://')):
            base_url = f"https://{base_url}"
        
        async with get_db_connection() as db:
            cursor = await db.execute("PRAGMA table_info(referral_links)")
            columns = [col[1] for col in await cursor.fetchall()]
            
            if 'url' in columns:
                from urllib.parse import urlencode
                query_params = {
                    "utm_source": utm_source,
                    "utm_medium": utm_medium,
                    "utm_campaign": utm_campaign
                }
                query_string = urlencode(query_params, safe='/:')
                full_url = f"{base_url}?{query_string}"
                
                await db.execute("""
                    INSERT OR REPLACE INTO referral_links 
                    (bank, product_key, base_url, url, utm_source, utm_medium, utm_campaign, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (bank, product_key, base_url, full_url, utm_source, utm_medium, utm_campaign))
            else:
                await db.execute("""
                    INSERT OR REPLACE INTO referral_links 
                    (bank, product_key, base_url, utm_source, utm_medium, utm_campaign, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (bank, product_key, base_url, utm_source, utm_medium, utm_campaign))
            
            await db.commit()
            print(f"✅ Ссылка обновлена: {bank}/{product_key}")
            return True
            
    except Exception as e:
        print(f"❌ Ошибка обновления ссылки: {e}")
        import traceback
        traceback.print_exc()
        return False



async def set_offer_bonus(bank: str, product_key: str, gross_bonus: int) -> bool:
    net_bonus = int(gross_bonus * 0.94)  # 6% commission
    
    async with get_db_connection() as db:
        try:
            await db.execute("""
                INSERT INTO referral_links (bank, product_key, gross_bonus, net_bonus)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(bank, product_key) 
                DO UPDATE SET 
                    gross_bonus = excluded.gross_bonus,
                    net_bonus = excluded.net_bonus,
                    updated_at = CURRENT_TIMESTAMP
            """, (bank, product_key, gross_bonus, net_bonus))
            
            await db.commit()
            return True
        except Exception as e:
            print(f"❌ Error setting offer bonus: {e}")
            return False

async def get_all_offer_net_bonuses() -> Dict[Tuple[str, str], int]:
    result = {}
    async with get_db_connection() as db:
        cursor = await db.execute(
            "SELECT bank, product_key, net_bonus FROM referral_links"
        )
        rows = await cursor.fetchall()
        
        for row in rows:
            key = (row["bank"], row["product_key"])
            result[key] = row["net_bonus"] or 0
    
    return result

async def get_user_financial_data(user_id: int) -> Optional[Dict[str, Any]]:
    async with get_db_connection() as db:
        cursor = await db.execute("""
            SELECT 
                id,
                user_id,
                COALESCE(total_referral_bonus, 0) as total_referral_bonus,
                COALESCE(total_your_bonus, 0) as total_your_bonus,
                COALESCE(total_bonus_status, 'pending') as total_bonus_status,
                bonus_details,
                COALESCE(referral_bonus_amount, 0) as referral_bonus_amount,
                COALESCE(your_bonus_amount, 0) as your_bonus_amount,
                COALESCE(your_bonus_status, 'pending') as your_bonus_status
            FROM financial_data 
            WHERE user_id = ?
        """, (user_id,))
        
        row = await cursor.fetchone()
        return dict(row) if row else None

async def update_financial_field(user_id: int, field: str, value: Any) -> bool:
    FIELD_CONFIG = {
        'total_referral_bonus': {
            'sql': "total_referral_bonus = ?",
            'type': int,
            'default': 0
        },
        'total_your_bonus': {
            'sql': "total_your_bonus = ?",
            'type': int,
            'default': 0
        },
        'your_bonus_status': {
            'sql': "total_bonus_status = ?",
            'type': str,
            'default': 'pending',
            'allowed_values': ['pending', 'confirmed']
        },
        'total_bonus_status': {
            'sql': "total_bonus_status = ?",
            'type': str,
            'default': 'pending',
            'allowed_values': ['pending', 'confirmed', 'processing', 'paid', 'cancelled']
        },
        'bonus_details': {
            'sql': "bonus_details = ?",
            'type': str,
            'default': None
        },
        'referral_bonus_amount': {
            'sql': "total_referral_bonus = ?",
            'type': int,
            'default': 0
        },
        'your_bonus_amount': {
            'sql': "total_your_bonus = ?",
            'type': int,
            'default': 0
        }
    }
    
    if field not in FIELD_CONFIG:
        allowed = ', '.join(sorted(FIELD_CONFIG.keys()))
        print(f"⚠️ Field '{field}' not allowed. Allowed: {allowed}")
        return False
    
    config = FIELD_CONFIG[field]
    
    if 'type' in config:
        expected_type = config['type']
        if isinstance(expected_type, tuple):
            if not any(isinstance(value, t) for t in expected_type):
                print(f"⚠️ Field '{field}' expects {expected_type}, got {type(value)}")
                return False
        elif not isinstance(value, expected_type):
            print(f"⚠️ Field '{field}' expects {expected_type}, got {type(value)}")
            return False
    
    if 'allowed_values' in config and value not in config['allowed_values']:
        print(f"⚠️ Field '{field}' value '{value}' not in allowed values: {config['allowed_values']}")
        return False
    
    async with get_db_connection() as db:
        try:
            await db.execute(
                f"UPDATE financial_data SET {config['sql']} WHERE user_id = ?",
                (value, user_id)
            )
            await db.commit()
            print(f"✅ Updated financial field: {field} = {value} for user_id={user_id}")
            return True
        except Exception as e:
            print(f"❌ Error updating financial field: {e}")
            return False


async def get_finance_summary() -> Dict[str, int]:
    async with get_db_connection() as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        total_referrals = (await cursor.fetchone())[0]
        
        cursor = await db.execute(
            "SELECT COALESCE(SUM(total_your_bonus), 0) FROM financial_data WHERE your_bonus_status = 'confirmed'"
        )
        confirmed_income = (await cursor.fetchone())[0]
        
        cursor = await db.execute(
            "SELECT COALESCE(SUM(total_your_bonus), 0) FROM financial_data WHERE your_bonus_status = 'pending'"
        )
        pending_income = (await cursor.fetchone())[0]
        
        cursor = await db.execute("""
            SELECT COALESCE(SUM(f.total_your_bonus), 0), COUNT(*)
            FROM financial_data f 
            JOIN users u ON f.user_id = u.user_id 
            WHERE u.bank = 't-bank'
        """)
        tbank_result = await cursor.fetchone()
        tbank_income, tbank_count = tbank_result[0], tbank_result[1]
        
        cursor = await db.execute("""
            SELECT COALESCE(SUM(f.total_your_bonus), 0), COUNT(*)
            FROM financial_data f 
            JOIN users u ON f.user_id = u.user_id 
            WHERE u.bank = 'alpha'
        """)
        alpha_result = await cursor.fetchone()
        alpha_income, alpha_count = alpha_result[0], alpha_result[1]
        
        cursor = await db.execute(
            "SELECT COUNT(*) FROM financial_data WHERE your_bonus_status = 'confirmed'"
        )
        confirmed_count = (await cursor.fetchone())[0]
        
        cursor = await db.execute(
            "SELECT COUNT(*) FROM financial_data WHERE your_bonus_status = 'pending'"
        )
        pending_count = (await cursor.fetchone())[0]
        
        cursor = await db.execute(
            "SELECT COALESCE(SUM(total_referral_bonus), 0) FROM financial_data WHERE total_bonus_status = 'confirmed'"
        )
        total_referral_paid = (await cursor.fetchone())[0]
        
        return {
            "total_referrals": total_referrals,
            "total_income": confirmed_income + pending_income,
            "confirmed_income": confirmed_income,
            "pending_income": pending_income,
            "total_referral_paid": total_referral_paid,
            "tbank_income": tbank_income,
            "tbank_count": tbank_count,
            "alpha_income": alpha_income,
            "alpha_count": alpha_count,
            "confirmed_count": confirmed_count,
            "pending_count": pending_count,
        }

async def get_all_referrals_data(include_financial: bool = True) -> List[Dict[str, Any]]:
    async with get_db_connection() as db:
        query = """
            SELECT 
                u.user_id,
                u.user_id as id,
                u.full_name,
                u.phone_enc,
                u.bank as primary_bank,
                u.selected_product,
                u.selected_product_name,
                u.created_at,
                (
                    SELECT GROUP_CONCAT(bank) 
                    FROM user_banks ub 
                    WHERE ub.user_id = u.user_id
                ) as all_banks,
                COALESCE(p.card_received, 0) as card_received,
                COALESCE(p.card_activated, 0) as card_activated,
                p.card_activated_date,
                COALESCE(p.purchase_made, 0) as purchase_made,
                p.first_purchase_date,
                p.card_received_date,
                p.application_date
        """
        
        if include_financial:
            query += """,
                COALESCE(f.total_referral_bonus, 0) as total_referral_bonus,
                COALESCE(f.total_your_bonus, 0) as total_your_bonus,
                COALESCE(f.total_bonus_status, 'pending') as total_bonus_status,
                f.bonus_details
            """
        
        query += """
            FROM users u
            LEFT JOIN referral_progress p ON u.user_id = p.user_id
        """
        
        if include_financial:
            query += "LEFT JOIN financial_data f ON u.user_id = f.user_id"
        
        query += " ORDER BY u.created_at DESC"
        
        cursor = await db.execute(query)
        rows = await cursor.fetchall()
        
        result = []
        for row in rows:
            item = dict(row)
            item['phone'] = decrypt_phone(item.get('phone_enc'))
            
            all_banks = item.get('all_banks', '')
            item['banks'] = all_banks.split(',') if all_banks else []
            
            result.append(item)
        
        return result


async def log_reminder_sent(user_id: int, admin_id: int) -> bool:
    async with get_db_connection() as db:
        try:
            await db.execute(
                "INSERT INTO reminders_log (user_id, admin_id) VALUES (?, ?)",
                (user_id, admin_id)
            )
            await db.commit()
            return True
        except Exception as e:
            print(f"❌ Error logging reminder: {e}")
            return False

async def get_users_for_auto_reminder() -> List[Dict[str, Any]]:
    seven_days_ago = (datetime.utcnow().date() - timedelta(days=7)).isoformat()
    
    async with get_db_connection() as db:
        query1 = """
            SELECT u.user_id, u.bank, 'activation' as reminder_type
            FROM users u
            JOIN referral_progress p ON u.user_id = p.user_id
            WHERE p.card_received = 1
              AND p.card_activated = 0
              AND p.card_received_date <= ?
        """
        
        query2 = """
            SELECT u.user_id, u.bank, 'purchase' as reminder_type
            FROM users u
            JOIN referral_progress p ON u.user_id = p.user_id
            WHERE u.bank = 't-bank'
              AND p.card_activated = 1
              AND p.purchase_made = 0
              AND p.card_activated_date <= ?
        """
        
        cursor1 = await db.execute(query1, (seven_days_ago,))
        cursor2 = await db.execute(query2, (seven_days_ago,))
        
        rows1 = await cursor1.fetchall()
        rows2 = await cursor2.fetchall()
        
        return [dict(row) for row in rows1 + rows2]

async def delete_user_all_data(user_id: int) -> bool:
    async with get_db_connection() as db:
        try:
            await db.execute("BEGIN TRANSACTION")
            
            await db.execute("DELETE FROM reminders_log WHERE user_id = ?", (user_id,))
            await db.execute("DELETE FROM referral_progress WHERE user_id = ?", (user_id,))
            await db.execute("DELETE FROM financial_data WHERE user_id = ?", (user_id,))
            await db.execute("DELETE FROM user_banks WHERE user_id = ?", (user_id,))
            cursor = await db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
            
            await db.commit()
            deleted = cursor.rowcount > 0
            
            if deleted:
                print(f"✅ User {user_id} deleted successfully")
            else:
                print(f"⚠️ User {user_id} not found")
            
            return deleted
            
        except Exception as e:
            await db.execute("ROLLBACK")
            print(f"❌ Error deleting user {user_id}: {e}")
            return False


async def delete_user_by_id(user_id: int) -> bool:
    """Alias for delete_user_all_data."""
    return await delete_user_all_data(user_id)


async def delete_user_by_phone(phone: str) -> bool:
    """Delete user by phone number."""
    user = await get_user_by_phone(phone)
    if user:
        return await delete_user_all_data(user['user_id'])
    return False

async def check_database_health() -> Dict[str, Any]:
    async with get_db_connection() as db:
        stats = {}
        
        tables = ['users', 'user_banks', 'referral_progress', 
                 'financial_data', 'referral_links', 'reminders_log']
        
        for table in tables:
            cursor = await db.execute(f"SELECT COUNT(*) FROM {table}")
            stats[f"{table}_count"] = (await cursor.fetchone())[0]
        
        cursor = await db.execute("PRAGMA page_size")
        page_size = (await cursor.fetchone())[0]
        
        cursor = await db.execute("PRAGMA page_count")
        page_count = (await cursor.fetchone())[0]
        
        stats['database_size_kb'] = (page_size * page_count) / 1024
        
        cursor = await db.execute(
            "SELECT bank, COUNT(*) as count FROM referral_links GROUP BY bank"
        )
        stats['referral_links_by_bank'] = dict(await cursor.fetchall())
        
        return stats