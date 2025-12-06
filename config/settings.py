from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

_admin_ids_raw = os.getenv("ADMIN_IDS", "").strip()
if _admin_ids_raw:
    try:
        ADMIN_IDS = set(
            int(x.strip()) for x in _admin_ids_raw.split(",") if x.strip()
        )
    except ValueError as e:
        raise ValueError(f"Ошибка в ADMIN_IDS: {e}. Убедитесь, что там только числа, разделённые запятыми.")
else:
    ADMIN_IDS = set()

ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    raise ValueError("ENCRYPTION_KEY обязателен в .env")