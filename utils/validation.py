import re

def is_valid_full_name(name: str) -> bool:
    return bool(re.match(r"^[а-яА-ЯёЁ\s]{5,60}$", name.strip()))

def is_valid_date(date_str: str) -> bool:
    if not re.match(r"^\d{2}\.\d{2}\.\d{4}$", date_str):
        return False
    from datetime import datetime
    try:
        datetime.strptime(date_str, "%d.%m.%Y")
        return True
    except ValueError:
        return False
    
def normalize_phone(phone: str) -> str:
    digits = re.sub(r'\D', '', phone)
    if digits.startswith('8'):
        digits = '7' + digits[1:]
    elif digits.startswith('7'):
        pass
    elif len(digits) == 10:
        digits = '7' + digits
    else:
        return phone.strip()
    return f'+{digits}'