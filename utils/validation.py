import re

def is_valid_full_name(name: str) -> bool:
    return bool(re.match(r"^[а-яА-ЯёЁ\s\-]{5,60}$", name.strip()))

def is_valid_date(date_str: str) -> bool:
    if not re.match(r"^\d{2}\.\d{2}\.\d{4}$", date_str):
        return False
    from datetime import datetime
    try:
        datetime.strptime(date_str, "%d.%m.%Y")
        return True
    except ValueError:
        return False
    
def normalize_phone(phone: str) -> str | None:
    digits = re.sub(r"\D", "", phone)

    if len(digits) == 11 and digits[0] in ("7", "8"):
        return "7" + digits[1:]
    if len(digits) == 10:
        return "7" + digits

    return None