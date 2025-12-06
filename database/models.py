from dataclasses import dataclass
from typing import Optional

@dataclass
class Referral:
    user_id: int
    full_name: str
    phone_enc: bytes
    bank: str
    # Добавьте остальные поля при расширении