"""
Утилиты для обработки данных
"""
import re


def format_phone_number(phone: str) -> str:
    """
    Форматирует номер телефона в простой формат с пробелами.
    
    Из: 79991234567, +79991234567, 89991234567, 7 999 123 45 67
    В: 7 999 123 45 67 или 8 999 123 45 67
    
    Если номер не похож на телефон — возвращает как есть, 
    но УБИРАЕТ + и = в начале (для Google Sheets).
    """
    if not phone:
        return phone

    # Очищаем от всего кроме цифр
    digits = re.sub(r'[^\d]', '', phone)

    # Если начинается с 8 и длина 11 — российский
    if digits.startswith('8') and len(digits) == 11:
        return f"8 {digits[1:4]} {digits[4:7]} {digits[7:9]} {digits[9:11]}"

    # Если начинается с 7 и длина 11 — российский
    if digits.startswith('7') and len(digits) == 11:
        return f"7 {digits[1:4]} {digits[4:7]} {digits[7:9]} {digits[9:11]}"

    # Для остальных — убираем + и = в начале (чтобы Sheets не ругался)
    result = phone.strip()
    if result and result[0] in ('=', '+', '-'):
        result = result[1:]
    
    return result if result else phone
