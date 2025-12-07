import aiosqlite
import os
from config import settings
from cryptography.fernet import Fernet
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from utils.validation import normalize_phone

_fernet = Fernet(settings.ENCRYPTION_KEY)

DB_PATH = settings.DATABASE_URL.replace("sqlite:///", "")

async def init_db():
    os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else ".", exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                full_name TEXT NOT NULL,
                phone_enc BLOB NOT NULL,
                bank TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_banks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                bank TEXT NOT NULL CHECK (bank IN ('t-bank', 'alpha')),
                selected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, bank)   
            )
        """)
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
        cursor = await db.execute("PRAGMA table_info(referral_progress)")
        columns = {row[1] for row in await cursor.fetchall()}
        if "card_last4" not in columns:
            await db.execute("ALTER TABLE referral_progress ADD COLUMN card_last4 TEXT")
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS financial_data (
                user_id INTEGER PRIMARY KEY,
                total_referral_bonus INTEGER DEFAULT 0,
                total_your_bonus INTEGER DEFAULT 0,
                total_bonus_status TEXT DEFAULT 'pending',
                bonus_details TEXT,
                referral_bonus_amount INTEGER DEFAULT 0,
                your_bonus_amount INTEGER DEFAULT 0,
                your_bonus_status TEXT DEFAULT 'pending'
            )
        ''')

        await db.execute('''
            CREATE TABLE IF NOT EXISTS reminders_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                admin_id INTEGER NOT NULL,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS referral_links (
                bank TEXT PRIMARY KEY,
                url TEXT NOT NULL
            )
        ''')

        cursor = await db.execute("PRAGMA table_info(referral_links)")
        referral_columns = {row[1] for row in await cursor.fetchall()}
        cursor = await db.execute("PRAGMA table_info(financial_data)")
        financial_columns = {row[1] for row in await cursor.fetchall()}
        if "bank" not in referral_columns:
            await db.execute("ALTER TABLE referral_links ADD COLUMN bank TEXT")
        if "utm_source" not in referral_columns:
            await db.execute("ALTER TABLE referral_links ADD COLUMN utm_source TEXT DEFAULT 'telegram'")
        if "utm_medium" not in referral_columns:
            await db.execute("ALTER TABLE referral_links ADD COLUMN utm_medium TEXT DEFAULT 'referral'")
        if "utm_campaign" not in referral_columns:
            await db.execute("ALTER TABLE referral_links ADD COLUMN utm_campaign TEXT DEFAULT 'default'")

        if "user_id" not in financial_columns:
            await db.execute("ALTER TABLE financial_data ADD COLUMN user_id INTEGER UNIQUE")
        if "total_referral_bonus" not in financial_columns:
            await db.execute("ALTER TABLE financial_data ADD COLUMN total_referral_bonus INTEGER DEFAULT 0")
        if "total_your_bonus" not in financial_columns:
            await db.execute("ALTER TABLE financial_data ADD COLUMN total_your_bonus INTEGER DEFAULT 0")
        if "total_bonus_status" not in financial_columns:
            await db.execute("ALTER TABLE financial_data ADD COLUMN total_bonus_status TEXT DEFAULT 'pending'")
        if "bonus_details" not in financial_columns:
            await db.execute("ALTER TABLE financial_data ADD COLUMN bonus_details TEXT")
        await db.commit()

def encrypt_phone(phone: str) -> bytes:
    return _fernet.encrypt(phone.encode())

def decrypt_phone(encrypted: bytes | None) -> str:
    if encrypted is None:
        return "[нет телефона]"
    try:
        return _fernet.decrypt(encrypted).decode()
    except Exception:
        return "[ошибка расшифровки]"

async def create_user(user_id: int, full_name: str, phone: str, bank: str):
    normalized_phone = normalize_phone(phone)
    phone_enc = encrypt_phone(normalized_phone)
    async with aiosqlite.connect(DB_PATH) as db:    
        await db.execute(
            "INSERT INTO users (user_id, full_name, phone_enc, bank) VALUES (?, ?, ?, ?)",
            (user_id, full_name, phone_enc, bank)
        )
        await db.execute("INSERT OR IGNORE INTO referral_progress (user_id) VALUES (?)", (user_id,))
        await db.execute("INSERT OR IGNORE INTO financial_data (user_id) VALUES (?)", (user_id,))
        await db.commit()

async def user_exists(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
        return await cursor.fetchone() is not None

async def add_user_bank(user_id: int, bank: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO user_banks (user_id, bank) VALUES (?, ?)",
            (user_id, bank)
        )
        await db.commit()

async def get_user_banks(user_id: int) -> list[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT bank FROM user_banks WHERE user_id = ? ORDER BY selected_at",
            (user_id,)
        )
        return [row[0] for row in await cursor.fetchall()]

async def get_user_full_data(user_id: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT u.*, p.*, f.*
            FROM users u
            JOIN referral_progress p ON u.user_id = p.user_id
            JOIN financial_data f ON u.user_id = f.user_id
            WHERE u.user_id = ?
        """, (user_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def get_user_by_phone(phone: str) -> Optional[Dict[str, Any]]:
    normalized_input = normalize_phone(phone)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT user_id, phone_enc FROM users")
        async for row in cursor:
            try:
                stored_phone = decrypt_phone(row["phone_enc"])
                if stored_phone == normalized_input:
                    return await get_user_full_data(row["user_id"])
            except Exception:
                continue
        return None

async def update_user_field(user_id: int, field: str, value):
    async with aiosqlite.connect(DB_PATH) as db:
        if field == "phone":
            value = encrypt_phone(value)
        await db.execute(f"UPDATE users SET {field} = ? WHERE user_id = ?", (value, user_id))
        await db.commit()

async def update_progress_field(user_id: int, field: str, value):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE referral_progress SET {field} = ? WHERE user_id = ?", (value, user_id))
        await db.commit()

async def get_user_financial_data(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT 
                id,
                user_id,
                COALESCE(amount, 0) as amount,
                COALESCE(total_referral_bonus, 0) as total_referral_bonus,
                COALESCE(total_your_bonus, 0) as total_your_bonus,
                COALESCE(total_bonus_status, 'pending') as total_bonus_status,
                bonus_details,
                created_at,
                updated_at
            FROM financial_data 
            WHERE user_id = ?
        """, (user_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def update_financial_field(user_id: int, field: str, value):
    field = field.strip()
    
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
        },
        'amount': {
            'sql': "amount = ?",
            'type': (int, float),
            'default': 0
        },
        'status': {
            'sql': "status = ?",
            'type': str,
            'default': 'active'
        },
        'bank': {
            'sql': "bank = ?",
            'type': str,
            'default': None
        },
        'payment_method': {
            'sql': "payment_method = ?",
            'type': str,
            'default': None
        },
        'transaction_id': {
            'sql': "transaction_id = ?",
            'type': str,
            'default': None
        },
        'updated_at': {
            'sql': "updated_at = datetime('now')",
            'type': None,
            'auto': True
        }
    }
    
    if field not in FIELD_CONFIG:
        allowed = ', '.join(sorted(FIELD_CONFIG.keys()))
        raise ValueError(f"Поле '{field}' не разрешено. Разрешены: {allowed}")
    
    config = FIELD_CONFIG[field]
    
    if config.get('type') and not config.get('auto', False):
        expected_type = config['type']
        if isinstance(expected_type, tuple):
            if not any(isinstance(value, t) for t in expected_type):
                expected_names = ' или '.join(t.__name__ for t in expected_type)
                raise TypeError(f"Поле '{field}' ожидает {expected_names}, получен {type(value).__name__}")
        elif not isinstance(value, expected_type):
            raise TypeError(f"Поле '{field}' ожидает {expected_type.__name__}, получен {type(value).__name__}")
    
    if 'allowed_values' in config and value not in config['allowed_values']:
        allowed = ', '.join(config['allowed_values'])
        raise ValueError(f"Поле '{field}' допускает значения: {allowed}")
    
    async with aiosqlite.connect(DB_PATH) as db:
        if config.get('auto', False):
            await db.execute(
                f"UPDATE financial_data SET {config['sql']} WHERE user_id = ?",
                (user_id,)
            )
        else:
            await db.execute(
                f"UPDATE financial_data SET {config['sql']} WHERE user_id = ?",
                (value, user_id)
            )
        await db.commit()
        print(f"✅ Обновлено: {field} = {value} для user_id={user_id}")
        return True

async def get_all_referrals_data(include_financial: bool = True):
    """Получаем данные всех рефералов с отладкой."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Сначала узнаем структуру таблицы users
        cursor = await db.execute("PRAGMA table_info(users)")
        columns = await cursor.fetchall()
        user_columns = [col[1] for col in columns]
        
        print(f"🔍 Колонки users: {user_columns}")
        
        # Определяем ключ для JOIN
        if 'id' in user_columns:
            join_key = 'u.id'
        elif 'user_id' in user_columns:
            join_key = 'u.user_id'
        elif 'telegram_id' in user_columns:
            join_key = 'u.telegram_id'
        else:
            # Если ничего не нашли, используем первую колонку
            join_key = f'u.{user_columns[0]}'
        
        print(f"🔍 Используем JOIN ключ: {join_key}")
        
        if include_financial:
            query = f"""
                SELECT 
                    u.*,
                    COALESCE(p.referrals_count, 0) as referrals_count,
                    COALESCE(p.successful_referrals, 0) as successful_referrals,
                    COALESCE(f.total_referral_bonus, 0) as total_referral_bonus,
                    COALESCE(f.total_your_bonus, 0) as total_your_bonus,
                    COALESCE(f.total_bonus_status, 'pending') as total_bonus_status,
                    f.bonus_details,
                    f.updated_at as last_financial_update
                FROM users u
                LEFT JOIN referral_progress p ON {join_key} = p.user_id
                LEFT JOIN financial_data f ON {join_key} = f.user_id
                ORDER BY u.created_at DESC
            """
        else:
            query = f"""
                SELECT 
                    u.*,
                    COALESCE(p.referrals_count, 0) as referrals_count,
                    COALESCE(p.successful_referrals, 0) as successful_referrals
                FROM users u
                LEFT JOIN referral_progress p ON {join_key} = p.user_id
                ORDER BY u.created_at DESC
            """
        
        print(f"🔍 Выполняем запрос:\n{query[:200]}...")
        
        cursor = await db.execute(query)
        rows = await cursor.fetchall()
        
        print(f"✅ Найдено записей: {len(rows)}")
        if rows:
            print(f"📊 Первая запись ключи: {list(dict(rows[0]).keys())}")
        
        return [dict(row) for row in rows]

async def get_finance_summary() -> Dict[str, int]:
    async with aiosqlite.connect(DB_PATH) as db:

        cursor = await db.execute("SELECT COUNT(*) FROM users")
        total = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COALESCE(SUM(total_your_bonus), 0) FROM financial_data WHERE your_bonus_status = 'confirmed'")
        confirmed_income = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COALESCE(SUM(total_your_bonus), 0) FROM financial_data WHERE your_bonus_status = 'pending'")
        pending_income = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COALESCE(SUM(f.total_your_bonus), 0) FROM financial_data f JOIN users u ON f.user_id = u.user_id WHERE u.bank = 't-bank'")
        tbank_income = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM users WHERE bank = 't-bank'")
        tbank_count = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COALESCE(SUM(f.total_your_bonus), 0) FROM financial_data f JOIN users u ON f.user_id = u.user_id WHERE u.bank = 'alpha'")
        alpha_income = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM users WHERE bank = 'alpha'")
        alpha_count = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM financial_data WHERE your_bonus_status = 'confirmed'")
        confirmed_count = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM financial_data WHERE your_bonus_status = 'pending'")
        pending_count = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COALESCE(SUM(total_referral_bonus), 0) FROM financial_data WHERE referral_bonus_date IS NOT NULL")
        total_referral_paid = (await cursor.fetchone())[0]

        return {
            "total_referrals": total,
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

async def add_referral_link(bank: str, url: str, utm_source="telegram", utm_medium="referral"):
    """Добавляет реферальную ссылку для банка."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO referral_links 
            (bank, url, utm_source, utm_medium, utm_campaign) 
            VALUES (?, ?, ?, ?, 'default')
        """, (bank, url, utm_source, utm_medium))
        await db.commit()

async def get_referral_link(bank: str) -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT 
                url, 
                COALESCE(utm_source, 'telegram') as utm_source,
                COALESCE(utm_medium, 'referral') as utm_medium,
                COALESCE(utm_campaign, 'default') as utm_campaign
            FROM referral_links 
            WHERE bank = ?
            """,
            (bank,)
        )
        row = await cursor.fetchone()
        if not row:
            return None

        # Строим UTM-ссылку
        parsed = urlparse(row["url"])
        query_params = parse_qs(parsed.query) if parsed.query else {}
        query_params = {k: v[0] if v else '' for k, v in query_params.items()}
        
        if "utm_source" not in query_params:
            query_params["utm_source"] = row["utm_source"]
        if "utm_medium" not in query_params:
            query_params["utm_medium"] = row["utm_medium"]
        if "utm_campaign" not in query_params:
            query_params["utm_campaign"] = row["utm_campaign"]
        new_query = urlencode(query_params, safe='/:')
        return urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment
        ))

async def update_referral_link(bank: str, base_url: str, utm_source: str, utm_medium: str, utm_campaign: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO referral_links
            (bank, url, utm_source, utm_medium, utm_campaign)
            VALUES (?, ?, ?, ?, ?)
        """, (bank, base_url, utm_source, utm_medium, utm_campaign))
        await db.commit()

async def get_users_for_auto_reminder() -> list[dict]:
    """
    Возвращает список пользователей, которым нужно отправить автоматическое напоминание.
    
    Условия:
    - Для всех: карта получена, но не активирована >7 дней.
    - Для Т-Банка: карта активирована, но покупка не совершена >7 дней.
    
    Returns:
        list[dict]: Список словарей с ключами 'user_id', 'bank'.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        seven_days_ago = (datetime.utcnow().date() - timedelta(days=7)).isoformat()

        # Условие 1: карта получена, но не активирована >7 дней
        query1 = """
            SELECT u.user_id, u.bank
            FROM users u
            JOIN referral_progress p ON u.user_id = p.user_id
            WHERE p.card_received = 1
              AND p.card_activated = 0
              AND p.card_received_date <= ?
        """

        # Условие 2: Т-Банк, карта активирована, но покупка не сделана >7 дней
        query2 = """
            SELECT u.user_id, u.bank
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

        # Объединяем и убираем дубли (маловероятно, но возможно)
        all_rows = {row["user_id"]: dict(row) for row in rows1 + rows2}
        return list(all_rows.values())  

async def log_reminder_sent(user_id: int, admin_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO reminders_log (user_id, admin_id) VALUES (?, ?)",
            (user_id, admin_id)
        )
        await db.commit()

async def get_users_needing_reminder() -> list:
    return []

async def delete_user_by_id(user_id: int) -> bool:
    """Удаляет пользователя и все связанные данные по user_id."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM referral_progress WHERE user_id = ?", (user_id,))
        await db.execute("DELETE FROM financial_data WHERE user_id = ?", (user_id,))
        await db.execute("DELETE FROM reminders_log WHERE user_id = ?", (user_id,))
        cursor = await db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        await db.commit()
        return cursor.rowcount > 0

async def delete_user_by_phone(phone: str) -> bool:
    """Удаляет пользователя по номеру телефона (с расшифровкой)."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT user_id, phone_enc FROM users")
        async for row in cursor:
            try:
                if decrypt_phone(row["phone_enc"]) == phone:
                    user_id = row["user_id"]
                    return await delete_user_by_id(user_id)
            except Exception:
                continue
        return False
    
async def delete_user_all_data(user_id: int) -> bool:
    """
    Полностью удаляет пользователя и все связанные данные из БД.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        # Удаляем из зависимых таблиц
        await db.execute("DELETE FROM referral_progress WHERE user_id = ?", (user_id))
        await db.execute("DELETE FROM financial_data WHERE user_id = ?", (user_id))
        await db.execute("DELETE FROM reminders_log WHERE user_id = ?", (user_id))
        # Удаляем из основной таблицы
        cursor = await db.execute("DELETE FROM users WHERE user_id = ?", (user_id))
        await db.commit()
        return cursor.rowcount > 0