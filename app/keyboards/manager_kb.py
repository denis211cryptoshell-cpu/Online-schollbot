"""
Клавиатуры для менеджера и админа (Reply кнопки только для админ-панели)
"""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_admin_main_keyboard() -> ReplyKeyboardMarkup:
    """Главная клавиатура админа"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📊 Статистика за день"),
                KeyboardButton(text="📈 Статистика за неделю"),
            ],
            [
                KeyboardButton(text="📅 Статистика за месяц"),
                KeyboardButton(text="🔥 Топ вопросов"),
            ],
            [
                KeyboardButton(text="⏱ Экономия времени"),
                KeyboardButton(text="📝 Управление FAQ"),
            ],
            [
                KeyboardButton(text="📤 Экспорт в Google Sheets"),
                KeyboardButton(text="🔧 CRM настройки"),
            ],
            [
                KeyboardButton(text="🔄 Обновить кэш"),
                KeyboardButton(text="🚫 Управление банами"),
            ]
        ],
        resize_keyboard=True
    )
    return keyboard


def get_faq_management_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура управления FAQ"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="➕ Добавить вопрос"),
                KeyboardButton(text="📋 Список вопросов"),
            ],
            [
                KeyboardButton(text="✏️ Редактировать"),
                KeyboardButton(text="🗑 Удалить вопрос"),
            ],
            [
                KeyboardButton(text="⬅️ Назад"),
            ]
        ],
        resize_keyboard=True
    )
    return keyboard
