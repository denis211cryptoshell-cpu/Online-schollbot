"""
Inline клавиатуры для управления банами
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_ban_management_keyboard() -> InlineKeyboardMarkup:
    """Главное inline меню управления банами"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Заблокировать", callback_data="ban_user_start"),
                InlineKeyboardButton(text="✅ Разблокировать", callback_data="unban_user_start"),
            ],
            [
                InlineKeyboardButton(text="📋 Список блокировок", callback_data="list_bans"),
                InlineKeyboardButton(text="🔍 Проверить статус", callback_data="check_ban_start"),
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data="ban_back_to_admin"),
            ]
        ]
    )
    return keyboard


def get_ban_confirm_keyboard(telegram_id: int) -> InlineKeyboardMarkup:
    """Подтверждение блокировки пользователя"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🚫 Заблокировать", callback_data=f"ban_confirm_{telegram_id}"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="ban_cancel"),
            ]
        ]
    )
    return keyboard


def get_unban_confirm_keyboard(telegram_id: int) -> InlineKeyboardMarkup:
    """Подтверждение разблокировки пользователя"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Разблокировать", callback_data=f"unban_confirm_{telegram_id}"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="unban_cancel"),
            ]
        ]
    )
    return keyboard


def get_ban_list_keyboard(has_more: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура для списка блокировок"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Обновить", callback_data="list_bans"),
                InlineKeyboardButton(text="🗑 Закрыть", callback_data="ban_close"),
            ]
        ]
    )
    return keyboard


def get_ban_back_keyboard() -> InlineKeyboardMarkup:
    """Кнопка назад к управлению банами"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⬅️ К управлению банами", callback_data="ban_back_to_menu"),
            ]
        ]
    )
    return keyboard


def get_admin_main_inline_keyboard() -> InlineKeyboardMarkup:
    """Inline версия главного меню админа (для edit_message_text)"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Статистика за день", callback_data="stats_day"),
                InlineKeyboardButton(text="📈 Статистика за неделю", callback_data="stats_week"),
            ],
            [
                InlineKeyboardButton(text="📅 Статистика за месяц", callback_data="stats_month"),
                InlineKeyboardButton(text="🔥 Топ вопросов", callback_data="top_questions"),
            ],
            [
                InlineKeyboardButton(text="⏱ Экономия времени", callback_data="time_saved"),
                InlineKeyboardButton(text="📝 Управление FAQ", callback_data="faq_management"),
            ],
            [
                InlineKeyboardButton(text="📤 Экспорт в Google Sheets", callback_data="export_sheets"),
                InlineKeyboardButton(text="🔧 CRM настройки", callback_data="crm_settings"),
            ],
            [
                InlineKeyboardButton(text="🔄 Обновить кэш", callback_data="refresh_cache"),
                InlineKeyboardButton(text="🚫 Управление банами", callback_data="ban_management"),
            ]
        ]
    )
    return keyboard
