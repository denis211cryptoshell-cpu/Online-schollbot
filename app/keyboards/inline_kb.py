"""
Inline клавиатуры для менеджера
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_lead_status_keyboard(lead_id: int) -> InlineKeyboardMarkup:
    """
    Inline клавиатура для управления статусом заявки
    
    Args:
        lead_id: ID заявки (включается в callback_data)
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Принято", callback_data=f"status_{lead_id}_accepted"),
                InlineKeyboardButton(text="📞 Перезвонить", callback_data=f"status_{lead_id}_callback"),
            ],
            [
                InlineKeyboardButton(text="❌ Отказ", callback_data=f"status_{lead_id}_rejected"),
            ],
            [
                InlineKeyboardButton(text="👤 Профиль пользователя", callback_data=f"profile_{lead_id}"),
                InlineKeyboardButton(text="💬 Ответить", callback_data=f"reply_{lead_id}"),
            ]
        ]
    )
    return keyboard


def get_lead_actions_keyboard(lead_id: int) -> InlineKeyboardMarkup:
    """
    Inline клавиатура с дополнительными действиями для заявки
    
    Args:
        lead_id: ID заявки
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📝 Добавить заметку", callback_data=f"note_{lead_id}"),
            ],
            [
                InlineKeyboardButton(text="🔗 Открыть в CRM", callback_data=f"crm_{lead_id}"),
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data=f"back_{lead_id}"),
            ]
        ]
    )
    return keyboard


def get_pagination_keyboard(page: int, has_next: bool) -> InlineKeyboardMarkup:
    """
    Inline клавиатура для пагинации списка заявок
    
    Args:
        page: Текущая страница
        has_next: Есть ли следующая страница
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[]
    )
    
    row = []
    
    if page > 1:
        row.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"leads_page_{page-1}"))
    
    if has_next:
        row.append(InlineKeyboardButton(text="Вперед ➡️", callback_data=f"leads_page_{page+1}"))
    
    if row:
        keyboard.inline_keyboard.append(row)
    
    return keyboard


def get_yes_no_keyboard(action: str, lead_id: int = 0) -> InlineKeyboardMarkup:
    """
    Inline клавиатура Да/Нет для подтверждений
    
    Args:
        action: Действие (для callback_data)
        lead_id: ID заявки
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data=f"confirm_{action}_{lead_id}"),
                InlineKeyboardButton(text="❌ Нет", callback_data=f"cancel_{action}_{lead_id}"),
            ]
        ]
    )
    return keyboard
