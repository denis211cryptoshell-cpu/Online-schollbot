"""
Inline клавиатуры для управления FAQ (админ-панель)
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_faq_management_inline_keyboard() -> InlineKeyboardMarkup:
    """Inline-клавиатура управления FAQ"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Добавить вопрос", callback_data="faq_add"),
                InlineKeyboardButton(text="📋 Список вопросов", callback_data="faq_list"),
            ],
            [
                InlineKeyboardButton(text="✏️ Редактировать", callback_data="faq_edit_select"),
                InlineKeyboardButton(text="🗑 Удалить", callback_data="faq_delete_select"),
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="faq_back_to_admin"),
            ]
        ]
    )
    return keyboard


def get_faq_list_keyboard(faqs: list, page: int = 1, page_size: int = 5) -> InlineKeyboardMarkup:
    """Список FAQ с пагинацией"""
    start = (page - 1) * page_size
    end = start + page_size
    page_faqs = faqs[start:end]
    has_next = end < len(faqs)
    has_prev = page > 1

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    for faq in page_faqs:
        status_icon = "✅" if faq['is_active'] else "❌"
        btn_text = f"{status_icon} #{faq['id']} | {faq['question_ru'][:30]}..."
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text=btn_text, callback_data=f"faq_view_{faq['id']}")
        ])

    nav_row = []
    if has_prev:
        nav_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"faq_list_page_{page - 1}"))
    if has_next:
        nav_row.append(InlineKeyboardButton(text="➡️", callback_data=f"faq_list_page_{page + 1}"))
    if nav_row:
        keyboard.inline_keyboard.append(nav_row)

    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="⬅️ Назад к управлению", callback_data="faq_back_to_menu"),
    ])

    return keyboard


def get_faq_view_keyboard(faq_id: int) -> InlineKeyboardMarkup:
    """Просмотр конкретного FAQ"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"faq_edit_{faq_id}"),
                InlineKeyboardButton(text="🗑 Удалить", callback_data=f"faq_delete_confirm_{faq_id}"),
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="faq_list"),
            ]
        ]
    )
    return keyboard


def get_faq_edit_keyboard(faq_id: int) -> InlineKeyboardMarkup:
    """Редактирование конкретного FAQ"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇷🇺 Вопрос RU", callback_data=f"faq_edit_field_{faq_id}_question_ru"),
                InlineKeyboardButton(text="🇷🇺 Ответ RU", callback_data=f"faq_edit_field_{faq_id}_answer_ru"),
            ],
            [
                InlineKeyboardButton(text="🇬🇧 Вопрос EN", callback_data=f"faq_edit_field_{faq_id}_question_en"),
                InlineKeyboardButton(text="🇬🇧 Ответ EN", callback_data=f"faq_edit_field_{faq_id}_answer_en"),
            ],
            [
                InlineKeyboardButton(text="🔑 Ключевые слова", callback_data=f"faq_edit_field_{faq_id}_keywords"),
                InlineKeyboardButton(text="🔄 Активность", callback_data=f"faq_edit_field_{faq_id}_toggle_active"),
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data=f"faq_view_{faq_id}"),
            ]
        ]
    )
    return keyboard


def get_faq_delete_confirm_keyboard(faq_id: int) -> InlineKeyboardMarkup:
    """Подтверждение удаления FAQ"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"faq_delete_yes_{faq_id}"),
                InlineKeyboardButton(text="❌ Отмена", callback_data=f"faq_delete_no_{faq_id}"),
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data=f"faq_view_{faq_id}"),
            ]
        ]
    )
    return keyboard


def get_faq_edit_select_keyboard(faqs: list) -> InlineKeyboardMarkup:
    """Список FAQ для редактирования — inline кнопки на каждый"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    for faq in faqs[:10]:
        status_icon = "✅" if faq['is_active'] else "❌"
        btn_text = f"{status_icon} ✏️ #{faq['id']} | {faq['question_ru'][:25]}..."
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text=btn_text, callback_data=f"faq_edit_{faq['id']}")
        ])

    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="⬅️ Назад к управлению", callback_data="faq_back_to_menu"),
    ])

    return keyboard


def get_faq_delete_select_keyboard(faqs: list) -> InlineKeyboardMarkup:
    """Список FAQ для удаления — inline кнопки на каждый"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    for faq in faqs[:10]:
        status_icon = "✅" if faq['is_active'] else "❌"
        btn_text = f"{status_icon} 🗑 #{faq['id']} | {faq['question_ru'][:25]}..."
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text=btn_text, callback_data=f"faq_delete_confirm_{faq['id']}")
        ])

    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="⬅️ Назад к управлению", callback_data="faq_back_to_menu"),
    ])

    return keyboard


def get_faq_fsm_back_keyboard() -> InlineKeyboardMarkup:
    """Кнопка Назад для FSM состояний добавления/редактирования FAQ"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⬅️ Отмена и назад", callback_data="faq_cancel_fsm"),
            ]
        ]
    )
    return keyboard


def get_faq_list_back_keyboard() -> InlineKeyboardMarkup:
    """Кнопка Назад для списка FAQ"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⬅️ Назад к управлению", callback_data="faq_back_to_menu"),
            ]
        ]
    )
    return keyboard
