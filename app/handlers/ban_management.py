"""
Управление банами через админ-панель (FSM + inline кнопки)
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy import select
from app.core.logger import log
from app.core.settings import settings
from app.database.adapter import db_adapter
from app.database.models import Lead
from app.database.models_ban import BannedUser
from app.services.ban_service import ban_service
from app.keyboards.admin_ban_kb import (
    get_admin_main_inline_keyboard,
    get_ban_management_keyboard,
    get_ban_confirm_keyboard,
    get_unban_confirm_keyboard,
    get_ban_list_keyboard,
    get_ban_back_keyboard,
    get_admin_main_inline_keyboard,
)

router = Router()


# ========== FSM для блокировки ==========

class BanUser(StatesGroup):
    """Состояния для блокировки пользователя"""
    waiting_for_telegram_id = State()
    waiting_for_reason = State()


# ========== FSM для разблокировки ==========

class UnbanUser(StatesGroup):
    """Состояния для разблокировки пользователя"""
    waiting_for_telegram_id = State()


# ========== FSM для проверки статуса ==========

class CheckBan(StatesGroup):
    """Состояния для проверки статуса блокировки"""
    waiting_for_telegram_id = State()


# ========== ГЛАВНОЕ МЕНЮ УПРАВЛЕНИЯ БАНАМИ ==========

@router.callback_query(F.data == "ban_management")
async def ban_management(callback: CallbackQuery):
    """Главное меню управления банами"""
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("⛔ Нет прав", show_alert=True)
        return

    log.info(f"Ban management menu opened by admin {callback.from_user.id}")
    try:
        await callback.message.edit_text(
            "🚫 <b>Управление блокировками</b>\n\n"
            "Выберите действие:",
            parse_mode="HTML",
            reply_markup=get_ban_management_keyboard()
        )
    except Exception:
        await callback.message.answer(
            "🚫 <b>Управление блокировками</b>\n\n"
            "Выберите действие:",
            parse_mode="HTML",
            reply_markup=get_ban_management_keyboard()
        )
    await callback.answer()


@router.callback_query(F.data == "ban_back_to_admin")
async def ban_back_to_admin(callback: CallbackQuery, state: FSMContext):
    """Назад в главное меню админа (inline версия)"""
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("⛔ Нет прав", show_alert=True)
        return

    await state.clear()
    log.info(f"Back to admin menu from ban management, admin {callback.from_user.id}")

    # РЕДАКТИРУЕМ сообщение обратно в inline админ-меню
    try:
        await callback.message.edit_text(
            "🛠 Админ-панель бота\n\nВыберите действие:",
            reply_markup=get_admin_main_inline_keyboard()
        )
    except TelegramBadRequest as e:
        log.error(f"Error editing message to admin menu: {e}")
        # Fallback: если не удалось редактировать, удаляем и шлем новое
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(
            "🛠 Админ-панель бота\n\nВыберите действие:",
            reply_markup=get_admin_main_inline_keyboard()
        )
    
    await callback.answer("Вернулись в главное меню", show_alert=False)


@router.callback_query(F.data == "ban_back_to_menu")
async def ban_back_to_menu(callback: CallbackQuery, state: FSMContext):
    """Назад к меню управления банами (РЕДАКТИРОВАНИЕ сообщения)"""
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("⛔ Нет прав", show_alert=True)
        return

    await state.clear()
    log.info(f"Back to ban management menu, admin {callback.from_user.id}")

    # РЕДАКТИРУЕМ сообщение обратно в меню управления банами
    try:
        await callback.message.edit_text(
            "🚫 <b>Управление блокировками</b>\n\n"
            "Выберите действие:",
            parse_mode="HTML",
            reply_markup=get_ban_management_keyboard()
        )
    except TelegramBadRequest as e:
        log.error(f"Error editing message to ban menu: {e}")
        # Fallback: если не удалось редактировать, удаляем и шлем новое
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(
            "🚫 <b>Управление блокировками</b>\n\n"
            "Выберите действие:",
            parse_mode="HTML",
            reply_markup=get_ban_management_keyboard()
        )
    
    await callback.answer("Вернулись в меню управления банами", show_alert=False)


# ========== БЛОКИРОВКА ПОЛЬЗОВАТЕЛЯ (FSM) ==========

@router.callback_query(F.data == "ban_user_start")
async def ban_user_start(callback: CallbackQuery, state: FSMContext):
    """Начало процесса блокировки"""
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("⛔ Нет прав", show_alert=True)
        return

    log.info(f"Admin {callback.from_user.id} started ban user process")
    await state.set_state(BanUser.waiting_for_telegram_id)
    try:
        await callback.message.edit_text(
            "➕ <b>Блокировка пользователя</b>\n\n"
            "Введите Telegram ID пользователя:\n\n"
            "💡 <i>ID можно посмотреть в профиле пользователя или из заявки</i>",
            parse_mode="HTML",
            reply_markup=get_ban_back_keyboard()
        )
    except TelegramBadRequest:
        await callback.message.answer(
            "➕ <b>Блокировка пользователя</b>\n\n"
            "Введите Telegram ID пользователя:\n\n"
            "💡 <i>ID можно посмотреть в профиле пользователя или из заявки</i>",
            parse_mode="HTML",
            reply_markup=get_ban_back_keyboard()
        )
    await callback.answer()


@router.message(BanUser.waiting_for_telegram_id)
async def ban_process_telegram_id(message: Message, state: FSMContext):
    """Обработка введенного Telegram ID"""
    if message.from_user.id not in settings.admin_ids:
        return

    # Проверяем команду отмены
    if message.text.lower() in ['/cancel', 'отмена', 'отменить']:
        await state.clear()
        await message.answer(
            "❌ Блокировка отменена.",
            reply_markup=get_ban_back_keyboard()
        )
        log.info(f"Ban process cancelled by admin {message.from_user.id}")
        return

    try:
        telegram_id = int(message.text)
    except ValueError:
        await message.answer(
            "⚠️ Telegram ID должен быть числом.\n\n"
            "Пожалуйста, введите корректный ID или /cancel для отмены:"
        )
        return

    await state.set_data({'telegram_id': telegram_id})

    # Проверяем, существует ли пользователь
    async for db_session in db_adapter.get_session():
        try:
            result = await db_session.execute(
                select(Lead).where(Lead.telegram_id == telegram_id).limit(1)
            )
            lead = result.scalar_one_or_none()

            if lead:
                user_info = (
                    f"👤 <b>{lead.full_name}</b>\n"
                    f"📝 Username: @{lead.username or 'N/A'}\n"
                    f"🆔 Telegram ID: <code>{telegram_id}</code>"
                )
            else:
                user_info = (
                    f"⚠️ Пользователь с ID <code>{telegram_id}</code> не найден в базе\n\n"
                    "<i>Блокировка всё равно будет применена</i>"
                )

            await state.set_data({'telegram_id': telegram_id, 'user_info': user_info})
            await state.set_state(BanUser.waiting_for_reason)

            await message.answer(
                f"{user_info}\n\n"
                "Введите причину блокировки:",
                parse_mode="HTML"
            )

            log.info(f"Admin {message.from_user.id} entered telegram_id={telegram_id} for ban")

        except Exception as e:
            log.error(f"Error checking user {telegram_id}: {e}")
            await message.answer("⚠️ Ошибка при проверке пользователя. Попробуйте снова.")
        break


@router.message(BanUser.waiting_for_reason)
async def ban_process_reason(message: Message, state: FSMContext):
    """Обработка введенной причины"""
    if message.from_user.id not in settings.admin_ids:
        return

    reason = message.text
    data = await state.get_data()
    telegram_id = data.get('telegram_id')

    # Сохраняем причину
    await state.set_data({'telegram_id': telegram_id, 'reason': reason})

    # Показываем подтверждение
    await message.answer(
        "🚫 <b>Подтверждение блокировки</b>\n\n"
        f"🆔 Telegram ID: <code>{telegram_id}</code>\n"
        f"⚠️ Причина: {reason}\n\n"
        "Заблокировать пользователя?",
        parse_mode="HTML",
        reply_markup=get_ban_confirm_keyboard(telegram_id)
    )

    log.info(f"Admin {message.from_user.id} entered reason for banning user {telegram_id}")


@router.callback_query(F.data.startswith("ban_confirm_"))
async def ban_confirm(callback: CallbackQuery, state: FSMContext):
    """Подтверждение блокировки"""
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("⛔ Нет прав", show_alert=True)
        return

    try:
        telegram_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
        await callback.answer("⚠️ Ошибка", show_alert=True)
        return

    data = await state.get_data()
    reason = data.get('reason', 'Не указана')

    log.info(f"Admin {callback.from_user.id} confirmed ban for user {telegram_id}")

    async for db_session in db_adapter.get_session():
        try:
            # Проверяем, существует ли пользователь
            result = await db_session.execute(
                select(Lead).where(Lead.telegram_id == telegram_id).limit(1)
            )
            lead = result.scalar_one_or_none()

            username = lead.username if lead else "unknown"
            full_name = lead.full_name if lead else "unknown"

            # Блокируем
            banned_user = await ban_service.ban_user(
                db_session=db_session,
                telegram_id=telegram_id,
                username=username,
                full_name=full_name,
                reason=reason,
                banned_by=f"admin_{callback.from_user.id}"
            )

            # Показываем подтверждение с меню банов
            await callback.message.edit_text(
                "🚫 <b>Пользователь заблокирован</b>\n\n"
                f"🆔 Telegram ID: <code>{telegram_id}</code>\n"
                f"👤 Имя: {full_name}\n"
                f"📝 Username: @{username}\n"
                f"⚠️ Причина: {reason}\n\n"
                "✅ Блокировка применена успешно!",
                parse_mode="HTML",
                reply_markup=get_ban_management_keyboard()
            )

            log.info(f"User {telegram_id} banned via UI by admin {callback.from_user.id}")

        except Exception as e:
            log.error(f"Error banning user {telegram_id}: {e}")
            try:
                await callback.message.edit_text(
                    f"⚠️ Ошибка при блокировке пользователя {telegram_id}\n\n"
                    f"Ошибка: {str(e)}",
                    reply_markup=get_ban_management_keyboard()
                )
            except TelegramBadRequest:
                await callback.message.answer(
                    f"⚠️ Ошибка при блокировке пользователя {telegram_id}",
                    reply_markup=get_ban_management_keyboard()
                )
        break

    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "ban_cancel")
async def ban_cancel(callback: CallbackQuery, state: FSMContext):
    """Отмена блокировки (возврат в меню банов)"""
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("⛔ Нет прав", show_alert=True)
        return

    await state.clear()
    log.info(f"Ban cancelled by admin {callback.from_user.id}")
    
    # РЕДАКТИРУЕМ сообщение обратно в меню банов
    try:
        await callback.message.edit_text(
            "❌ Блокировка отменена.\n\n"
            "🚫 <b>Управление блокировками</b>\n\n"
            "Выберите действие:",
            parse_mode="HTML",
            reply_markup=get_ban_management_keyboard()
        )
    except TelegramBadRequest as e:
        log.error(f"Error editing message on ban cancel: {e}")
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(
            "❌ Блокировка отменена.\n\n"
            "🚫 <b>Управление блокировками</b>\n\n"
            "Выберите действие:",
            parse_mode="HTML",
            reply_markup=get_ban_management_keyboard()
        )
    
    await callback.answer("❌ Блокировка отменена", show_alert=False)


# ========== РАЗБЛОКИРОВКА ПОЛЬЗОВАТЕЛЯ (FSM) ==========

@router.callback_query(F.data == "unban_user_start")
async def unban_user_start(callback: CallbackQuery, state: FSMContext):
    """Начало процесса разблокировки"""
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("⛔ Нет прав", show_alert=True)
        return

    log.info(f"Admin {callback.from_user.id} started unban user process")
    await state.set_state(UnbanUser.waiting_for_telegram_id)
    try:
        await callback.message.edit_text(
            "✅ <b>Разблокировка пользователя</b>\n\n"
            "Введите Telegram ID пользователя:",
            parse_mode="HTML",
            reply_markup=get_ban_back_keyboard()
        )
    except TelegramBadRequest:
        await callback.message.answer(
            "✅ <b>Разблокировка пользователя</b>\n\n"
            "Введите Telegram ID пользователя:",
            parse_mode="HTML",
            reply_markup=get_ban_back_keyboard()
        )
    await callback.answer()


@router.message(UnbanUser.waiting_for_telegram_id)
async def unban_process_telegram_id(message: Message, state: FSMContext):
    """Обработка введенного Telegram ID для разблокировки"""
    if message.from_user.id not in settings.admin_ids:
        return

    # Проверяем команду отмены
    if message.text.lower() in ['/cancel', 'отмена', 'отменить']:
        await state.clear()
        await message.answer(
            "❌ Разблокировка отменена.",
            reply_markup=get_ban_back_keyboard()
        )
        log.info(f"Unban process cancelled by admin {message.from_user.id}")
        return

    try:
        telegram_id = int(message.text)
    except ValueError:
        await message.answer(
            "⚠️ Telegram ID должен быть числом.\n\n"
            "Пожалуйста, введите корректный ID или /cancel для отмены:"
        )
        return

    await state.set_data({'telegram_id': telegram_id})

    # Проверяем, заблокирован ли пользователь
    async for db_session in db_adapter.get_session():
        try:
            banned_user = await ban_service.is_banned(db_session, telegram_id)

            if banned_user:
                user_info = (
                    f"🚫 <b>Пользователь заблокирован</b>\n\n"
                    f"🆔 Telegram ID: <code>{telegram_id}</code>\n"
                    f"👤 Имя: {banned_user.full_name}\n"
                    f"📝 Username: @{banned_user.username or 'N/A'}\n"
                    f"⚠️ Причина: {banned_user.reason}\n"
                    f"👮 Заблокировал: {banned_user.banned_by}\n"
                    f"📅 Дата: {banned_user.created_at.strftime('%d.%m.%Y %H:%M')}"
                )
            else:
                user_info = (
                    f"✅ Пользователь с ID <code>{telegram_id}</code> не заблокирован"
                )

            await state.set_data({'telegram_id': telegram_id, 'user_info': user_info})

            if banned_user:
                await message.answer(
                    f"{user_info}\n\n"
                    "Разблокировать пользователя?",
                    parse_mode="HTML",
                    reply_markup=get_unban_confirm_keyboard(telegram_id)
                )
            else:
                await message.answer(
                    f"{user_info}",
                    parse_mode="HTML",
                    reply_markup=get_ban_back_keyboard()
                )

            log.info(f"Admin {message.from_user.id} checking unban for user {telegram_id}")

        except Exception as e:
            log.error(f"Error checking ban status for {telegram_id}: {e}")
            await message.answer("⚠️ Ошибка при проверке статуса. Попробуйте снова.")
        break


@router.callback_query(F.data.startswith("unban_confirm_"))
async def unban_confirm(callback: CallbackQuery, state: FSMContext):
    """Подтверждение разблокировки"""
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("⛔ Нет прав", show_alert=True)
        return

    try:
        telegram_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
        await callback.answer("⚠️ Ошибка", show_alert=True)
        return

    log.info(f"Admin {callback.from_user.id} confirmed unban for user {telegram_id}")

    async for db_session in db_adapter.get_session():
        try:
            success = await ban_service.unban_user(
                db_session=db_session,
                telegram_id=telegram_id,
                unbanned_by=f"admin_{callback.from_user.id}"
            )

            if success:
                await callback.message.edit_text(
                    f"✅ Пользователь <code>{telegram_id}</code> разблокирован",
                    parse_mode="HTML",
                    reply_markup=get_ban_management_keyboard()
                )
                log.info(f"User {telegram_id} unbanned via UI by admin {callback.from_user.id}")
            else:
                await callback.message.edit_text(
                    f"⚠️ Пользователь <code>{telegram_id}</code> не был заблокирован",
                    parse_mode="HTML",
                    reply_markup=get_ban_management_keyboard()
                )
                log.warning(f"Attempt to unban non-banned user {telegram_id}")

        except Exception as e:
            log.error(f"Error unbanning user {telegram_id}: {e}")
            try:
                await callback.message.edit_text(
                    f"⚠️ Ошибка при разблокировке пользователя {telegram_id}\n\n"
                    f"Ошибка: {str(e)}",
                    reply_markup=get_ban_management_keyboard()
                )
            except TelegramBadRequest:
                await callback.message.answer(
                    f"⚠️ Ошибка при разблокировке пользователя {telegram_id}",
                    reply_markup=get_ban_management_keyboard()
                )
        break

    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "unban_cancel")
async def unban_cancel(callback: CallbackQuery, state: FSMContext):
    """Отмена разблокировки (возврат в меню банов)"""
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("⛔ Нет прав", show_alert=True)
        return

    await state.clear()
    log.info(f"Unban cancelled by admin {callback.from_user.id}")
    
    # РЕДАКТИРУЕМ сообщение обратно в меню банов
    try:
        await callback.message.edit_text(
            "❌ Разблокировка отменена.\n\n"
            "🚫 <b>Управление блокировками</b>\n\n"
            "Выберите действие:",
            parse_mode="HTML",
            reply_markup=get_ban_management_keyboard()
        )
    except TelegramBadRequest as e:
        log.error(f"Error editing message on unban cancel: {e}")
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(
            "❌ Разблокировка отменена.\n\n"
            "🚫 <b>Управление блокировками</b>\n\n"
            "Выберите действие:",
            parse_mode="HTML",
            reply_markup=get_ban_management_keyboard()
        )
    
    await callback.answer("❌ Разблокировка отменена", show_alert=False)


# ========== СПИСОК БЛОКИРОВОК ==========

@router.callback_query(F.data == "list_bans")
async def list_bans(callback: CallbackQuery):
    """Список заблокированных пользователей"""
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("⛔ Нет прав", show_alert=True)
        return

    log.info(f"Admin {callback.from_user.id} requested banned users list")

    async for db_session in db_adapter.get_session():
        try:
            banned_users = await ban_service.get_banned_users(db_session, limit=20)

            if not banned_users:
                try:
                    await callback.message.edit_text(
                        "✅ Список блокировок пуст"
                    )
                except TelegramBadRequest:
                    await callback.message.answer(
                        "✅ Список блокировок пуст"
                    )
                await callback.answer()
                return

            text = "🚫 <b>Заблокированные пользователи</b>\n\n"

            for user in banned_users:
                text += (
                    f"🆔 <code>{user.telegram_id}</code> - {user.full_name}\n"
                    f"   📝 @{user.username or 'N/A'}\n"
                    f"   ⚠️ Причина: {user.reason}\n"
                    f"   👮 Заблокировал: {user.banned_by}\n"
                    f"   📅 {user.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
                )

            try:
                await callback.message.edit_text(
                    text,
                    parse_mode="HTML",
                    reply_markup=get_ban_list_keyboard()
                )
            except TelegramBadRequest:
                # Если текст слишком длинный, отправляем как документ
                await callback.message.answer(
                    "📋 Список блокировок (слишком много данных для сообщения)",
                    reply_markup=get_ban_list_keyboard()
                )

            log.info(f"Shown {len(banned_users)} banned users to admin {callback.from_user.id}")

        except Exception as e:
            log.error(f"Error listing banned users: {e}")
            await callback.answer("⚠️ Ошибка при загрузке списка блокировок", show_alert=True)

        break

    await callback.answer()


# ========== ПРОВЕРКА СТАТУСА БЛОКИРОВКИ (FSM) ==========

@router.callback_query(F.data == "check_ban_start")
async def check_ban_start(callback: CallbackQuery, state: FSMContext):
    """Начало проверки статуса блокировки"""
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("⛔ Нет прав", show_alert=True)
        return

    log.info(f"Admin {callback.from_user.id} started check ban status process")
    await state.set_state(CheckBan.waiting_for_telegram_id)
    try:
        await callback.message.edit_text(
            "🔍 <b>Проверка статуса блокировки</b>\n\n"
            "Введите Telegram ID пользователя:",
            parse_mode="HTML",
            reply_markup=get_ban_back_keyboard()
        )
    except TelegramBadRequest:
        await callback.message.answer(
            "🔍 <b>Проверка статуса блокировки</b>\n\n"
            "Введите Telegram ID пользователя:",
            parse_mode="HTML",
            reply_markup=get_ban_back_keyboard()
        )
    await callback.answer()


@router.message(CheckBan.waiting_for_telegram_id)
async def check_ban_process_telegram_id(message: Message, state: FSMContext):
    """Обработка введенного Telegram ID для проверки статуса"""
    if message.from_user.id not in settings.admin_ids:
        return

    # Проверяем команду отмены
    if message.text.lower() in ['/cancel', 'отмена', 'отменить']:
        await state.clear()
        await message.answer(
            "❌ Проверка отменена.",
            reply_markup=get_ban_back_keyboard()
        )
        log.info(f"Check ban process cancelled by admin {message.from_user.id}")
        return

    try:
        telegram_id = int(message.text)
    except ValueError:
        await message.answer(
            "⚠️ Telegram ID должен быть числом.\n\n"
            "Пожалуйста, введите корректный ID или /cancel для отмены:"
        )
        return

    log.info(f"Admin {message.from_user.id} checking ban status for user {telegram_id}")

    async for db_session in db_adapter.get_session():
        try:
            banned_user = await ban_service.is_banned(db_session, telegram_id)

            if banned_user:
                text = (
                    f"🚫 <b>Пользователь заблокирован</b>\n\n"
                    f"🆔 Telegram ID: <code>{telegram_id}</code>\n"
                    f"👤 Имя: {banned_user.full_name}\n"
                    f"📝 Username: @{banned_user.username or 'N/A'}\n"
                    f"⚠️ Причина: {banned_user.reason}\n"
                    f"👮 Заблокировал: {banned_user.banned_by}\n"
                    f"📅 Дата: {banned_user.created_at.strftime('%d.%m.%Y %H:%M')}"
                )
            else:
                text = f"✅ Пользователь <code>{telegram_id}</code> не заблокирован"

            await message.answer(
                text,
                parse_mode="HTML",
                reply_markup=get_ban_back_keyboard()
            )

            log.info(f"Ban status checked for user {telegram_id} by admin {message.from_user.id}")

        except Exception as e:
            log.error(f"Error checking ban status for {telegram_id}: {e}")
            await message.answer("⚠️ Ошибка при проверке статуса.")

        break

    await state.clear()


@router.callback_query(F.data == "ban_close")
async def ban_close(callback: CallbackQuery, state: FSMContext):
    """Закрыть список блокировок (возврат в меню банов)"""
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("⛔ Нет прав", show_alert=True)
        return

    log.info(f"Admin {callback.from_user.id} closed ban info, returning to ban menu")
    
    # РЕДАКТИРУЕМ сообщение обратно в меню банов
    try:
        await callback.message.edit_text(
            "🚫 <b>Управление блокировками</b>\n\n"
            "Выберите действие:",
            parse_mode="HTML",
            reply_markup=get_ban_management_keyboard()
        )
    except TelegramBadRequest as e:
        log.error(f"Error editing message on ban close: {e}")
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(
            "🚫 <b>Управление блокировками</b>\n\n"
            "Выберите действие:",
            parse_mode="HTML",
            reply_markup=get_ban_management_keyboard()
        )
    
    await callback.answer()


# ========== CALLBACK HANDLERS ДЛЯ INLINE ADMIN MENU ==========

@router.callback_query(F.data == "stats_day")
async def callback_stats_day(callback: CallbackQuery):
    """Статистика за день (inline кнопка)"""
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("⛔ Нет прав", show_alert=True)
        return

    log.info(f"Admin {callback.from_user.id} clicked: stats_day (inline)")
    await callback.answer("Загружаю статистику за день...", show_alert=False)

    async for db_session in db_adapter.get_session():
        try:
            from app.services.lead_service import lead_service
            stats = await lead_service.get_statistics(db_session, days=1)

            text = (
                f"📊 Статистика за день ({stats['start_date']})\n\n"
                f"📝 Всего заявок: {stats['total_leads']}\n"
            )

            for status, count in stats['status_breakdown'].items():
                emoji = {"new": "🆕", "accepted": "✅", "callback": "📞", "rejected": "❌"}.get(status, "📋")
                text += f"{emoji} {status}: {count}\n"

            await callback.message.edit_text(text, reply_markup=get_admin_main_inline_keyboard())

        except Exception as e:
            log.error(f"Error getting daily stats: {e}")
            await callback.answer("⚠️ Ошибка при получении статистики", show_alert=True)
        break


@router.callback_query(F.data == "stats_week")
async def callback_stats_week(callback: CallbackQuery):
    """Статистика за неделю (inline кнопка)"""
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("⛔ Нет прав", show_alert=True)
        return

    log.info(f"Admin {callback.from_user.id} clicked: stats_week (inline)")
    await callback.answer("Загружаю статистику за неделю...", show_alert=False)

    async for db_session in db_adapter.get_session():
        try:
            from app.services.lead_service import lead_service
            stats = await lead_service.get_statistics(db_session, days=7)

            text = (
                f"📈 Статистика за неделю ({stats['start_date']} - {stats['end_date']})\n\n"
                f"📝 Всего заявок: {stats['total_leads']}\n"
            )

            for status, count in stats['status_breakdown'].items():
                emoji = {"new": "🆕", "accepted": "✅", "callback": "📞", "rejected": "❌"}.get(status, "📋")
                text += f"{emoji} {status}: {count}\n"

            await callback.message.edit_text(text, reply_markup=get_admin_main_inline_keyboard())

        except Exception as e:
            log.error(f"Error getting weekly stats: {e}")
            await callback.answer("⚠️ Ошибка при получении статистики", show_alert=True)
        break


@router.callback_query(F.data == "stats_month")
async def callback_stats_month(callback: CallbackQuery):
    """Статистика за месяц (inline кнопка)"""
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("⛔ Нет прав", show_alert=True)
        return

    log.info(f"Admin {callback.from_user.id} clicked: stats_month (inline)")
    await callback.answer("Загружаю статистику за месяц...", show_alert=False)

    async for db_session in db_adapter.get_session():
        try:
            from app.services.lead_service import lead_service
            stats = await lead_service.get_statistics(db_session, days=30)

            text = (
                f"📅 Статистика за месяц ({stats['start_date']} - {stats['end_date']})\n\n"
                f"📝 Всего заявок: {stats['total_leads']}\n"
            )

            for status, count in stats['status_breakdown'].items():
                emoji = {"new": "🆕", "accepted": "✅", "callback": "📞", "rejected": "❌"}.get(status, "📋")
                text += f"{emoji} {status}: {count}\n"

            await callback.message.edit_text(text, reply_markup=get_admin_main_inline_keyboard())

        except Exception as e:
            log.error(f"Error getting monthly stats: {e}")
            await callback.answer("⚠️ Ошибка при получении статистики", show_alert=True)
        break


@router.callback_query(F.data == "top_questions")
async def callback_top_questions(callback: CallbackQuery):
    """Топ частых вопросов (inline кнопка)"""
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("⛔ Нет прав", show_alert=True)
        return

    log.info(f"Admin {callback.from_user.id} clicked: top_questions (inline)")
    await callback.answer("Загружаю топ вопросов...", show_alert=False)

    async for db_session in db_adapter.get_session():
        try:
            from app.services.lead_service import lead_service
            stats = await lead_service.get_statistics(db_session, days=30)

            text = "🔥 Топ-10 частых вопросов за месяц:\n\n"

            for i, faq in enumerate(stats['top_faqs'], 1):
                text += f"{i}. {faq['question']} ({faq['count']} раз)\n"

            await callback.message.edit_text(text, reply_markup=get_admin_main_inline_keyboard())

        except Exception as e:
            log.error(f"Error getting top questions: {e}")
            await callback.answer("⚠️ Ошибка при получении топа вопросов", show_alert=True)
        break


@router.callback_query(F.data == "time_saved")
async def callback_time_saved(callback: CallbackQuery):
    """Экономия времени (inline кнопка)"""
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("⛔ Нет прав", show_alert=True)
        return

    log.info(f"Admin {callback.from_user.id} clicked: time_saved (inline)")
    await callback.answer("Считаю экономию времени...", show_alert=False)

    async for db_session in db_adapter.get_session():
        try:
            from app.services.lead_service import lead_service
            stats = await lead_service.get_statistics(db_session, days=7)
            faq_answers = sum(faq['count'] for faq in stats['top_faqs'])
            time_saved_minutes = faq_answers * 3
            time_saved_hours = time_saved_minutes / 60

            text = (
                f"⏱ Экономия времени за неделю:\n\n"
                f"💬 FAQ ответов: {faq_answers}\n"
                f"⏰ Сэкономлено времени: {time_saved_hours:.1f} часов\n\n"
                f"Средняя экономия: ~{time_saved_hours/7:.1f} часов в день"
            )

            await callback.message.edit_text(text, reply_markup=get_admin_main_inline_keyboard())

        except Exception as e:
            log.error(f"Error calculating time saved: {e}")
            await callback.answer("⚠️ Ошибка при расчете экономии времени", show_alert=True)
        break


@router.callback_query(F.data == "faq_management")
async def callback_faq_management_from_admin(callback: CallbackQuery):
    """Управление FAQ из админ-меню (inline кнопка)"""
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("⛔ Нет прав", show_alert=True)
        return

    log.info(f"Admin {callback.from_user.id} clicked: faq_management (inline from admin)")
    await callback.answer()

    try:
        await callback.message.edit_text(
            "📝 <b>Управление базой знаний</b>\n\n"
            "Выберите действие:",
            parse_mode="HTML"
        )
    except TelegramBadRequest as e:
        log.error(f"Error editing message in faq_management: {e}")
        await callback.message.answer(
            "📝 <b>Управление базой знаний</b>\n\n"
            "Выберите действие:",
            parse_mode="HTML"
        )


@router.callback_query(F.data == "export_sheets")
async def callback_export_sheets(callback: CallbackQuery):
    """Экспорт в Google Sheets (inline кнопка)"""
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("⛔ Нет прав", show_alert=True)
        return

    log.info(f"Admin {callback.from_user.id} clicked: export_sheets (inline)")
    await callback.answer("Запускаю экспорт...", show_alert=False)

    try:
        from app.services.google_sheets_service import google_sheets_service
        from app.database.models import Lead

        initialized = await google_sheets_service.initialize()

        if not initialized:
            await callback.message.edit_text(
                "⚠️ Google Sheets не настроен.\n\n"
                "Проверьте настройки в .env файле.",
                reply_markup=get_admin_main_inline_keyboard()
            )
            return

        async for db_session in db_adapter.get_session():
            result = await db_session.execute(select(Lead))
            leads = result.scalars().all()

            exported = 0
            for lead in leads:
                success = await google_sheets_service.add_lead(
                    lead_id=lead.id,
                    telegram_id=lead.telegram_id,
                    username=lead.username or "",
                    full_name=lead.full_name or "",
                    contact=lead.contact or "",
                    message_text=lead.message_text or "",
                    status=lead.status.value if lead.status else "new",
                    language=lead.language or "ru"
                )
                if success:
                    exported += 1

            await callback.message.edit_text(
                f"✅ Экспорт завершен!\n\n"
                f"📝 Экспортировано заявок: {exported}",
                reply_markup=get_admin_main_inline_keyboard()
            )
            log.info(f"Manual export via inline button: {exported} leads")
            break

    except Exception as e:
        log.error(f"Error during export: {e}")
        await callback.answer("⚠️ Ошибка при экспорте", show_alert=True)


@router.callback_query(F.data == "crm_settings")
async def callback_crm_settings(callback: CallbackQuery):
    """CRM настройки (inline кнопка)"""
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("⛔ Нет прав", show_alert=True)
        return

    log.info(f"Admin {callback.from_user.id} clicked: crm_settings (inline)")

    backend = "Google Sheets" if settings.GOOGLE_SHEETS_ENABLED else "Локальная БД"

    text = (
        f"🔧 <b>Текущий CRM бэкенд:</b> {backend}\n\n"
        f"📋 <b>Доступные бэкенды:</b>\n"
        f"• database - Локальная БД (SQLite/PostgreSQL)\n"
        f"• google_sheets - Google Sheets\n\n"
        f"⚙️ <b>Текущие настройки:</b>\n"
        f"• GOOGLE_SHEETS_ENABLED: {settings.GOOGLE_SHEETS_ENABLED}\n"
        f"• GOOGLE_SHEETS_ID: {settings.GOOGLE_SHEETS_ID or 'Не указан'}\n"
        f"• DATABASE_TYPE: {settings.DATABASE_TYPE}\n\n"
        f"Для переключения измените в .env:\n"
        f"<code>GOOGLE_SHEETS_ENABLED=true/false</code>"
    )

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_main_inline_keyboard())
    await callback.answer()


@router.callback_query(F.data == "refresh_cache")
async def callback_refresh_cache(callback: CallbackQuery):
    """Обновить кэш (inline кнопка)"""
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("⛔ Нет прав", show_alert=True)
        return

    log.info(f"Admin {callback.from_user.id} clicked: refresh_cache (inline)")
    await callback.answer("Обновляю кэш...", show_alert=False)

    try:
        from app.services.faq_service import faq_service
        await faq_service.clear_cache()
        await callback.message.edit_text(
            "✅ Кэш FAQ успешно обновлен",
            reply_markup=get_admin_main_inline_keyboard()
        )
        log.info("FAQ cache refreshed via inline button")
    except Exception as e:
        log.error(f"Error refreshing cache: {e}")
        await callback.answer("⚠️ Ошибка при обновлении кэша", show_alert=True) 
