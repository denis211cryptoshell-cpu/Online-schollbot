"""
Обработчик команд бана/разбана пользователей
"""
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy import select
from app.core.logger import log
from app.core.settings import settings
from app.database.adapter import db_adapter
from app.database.models import Lead
from app.database.models_ban import BannedUser
from app.services.ban_service import ban_service
from app.services.notification_service import manager_notification_service

router = Router()


@router.message(Command("ban"))
async def cmd_ban(message: Message):
    """
    Заблокировать пользователя
    
    Использование: /ban [Telegram ID] [причина]
    """
    if message.from_user.id not in settings.admin_ids:
        await message.answer("⛔ У вас нет прав администратора.")
        return
    
    parts = message.text.split(maxsplit=2)
    
    if len(parts) < 2:
        await message.answer(
            "🚫 <b>Блокировка пользователя</b>\n\n"
            "Использование: <code>/ban [Telegram ID] [причина]</code>\n\n"
            "Примеры:\n"
            "• <code>/ban 123456789 Спам</code>\n"
            "• <code>/ban 123456789 Оскорбления</code>",
            parse_mode="HTML"
        )
        return
    
    try:
        telegram_id = int(parts[1])
    except ValueError:
        await message.answer("⚠️ Telegram ID должен быть числом")
        return
    
    reason = parts[2] if len(parts) > 2 else "Не указана"
    
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
                banned_by=f"admin_{message.from_user.id}"
            )
            
            await message.answer(
                f"🚫 <b>Пользователь заблокирован</b>\n\n"
                f"🆔 Telegram ID: <code>{telegram_id}</code>\n"
                f"👤 Имя: {full_name}\n"
                f"📝 Username: @{username}\n"
                f"⚠️ Причина: {reason}"
            )
            
            log.info(f"User {telegram_id} banned via command")
            
        except Exception as e:
            log.error(f"Error banning user {telegram_id}: {e}")
            await message.answer("⚠️ Ошибка при блокировке пользователя")
        
        break


@router.message(Command("unban"))
async def cmd_unban(message: Message):
    """
    Разблокировать пользователя
    
    Использование: /unban [Telegram ID]
    """
    if message.from_user.id not in settings.admin_ids:
        await message.answer("⛔ У вас нет прав администратора.")
        return
    
    parts = message.text.split()
    
    if len(parts) < 2:
        await message.answer(
            "✅ <b>Разблокировка пользователя</b>\n\n"
            "Использование: <code>/unban [Telegram ID]</code>\n\n"
            "Пример: <code>/unban 123456789</code>",
            parse_mode="HTML"
        )
        return
    
    try:
        telegram_id = int(parts[1])
    except ValueError:
        await message.answer("⚠️ Telegram ID должен быть числом")
        return
    
    async for db_session in db_adapter.get_session():
        try:
            success = await ban_service.unban_user(
                db_session=db_session,
                telegram_id=telegram_id,
                unbanned_by=f"admin_{message.from_user.id}"
            )
            
            if success:
                await message.answer(f"✅ Пользователь <code>{telegram_id}</code> разблокирован")
                log.info(f"User {telegram_id} unbanned via command")
            else:
                await message.answer(f"⚠️ Пользователь <code>{telegram_id}</code> не был заблокирован")
            
        except Exception as e:
            log.error(f"Error unbanning user {telegram_id}: {e}")
            await message.answer("⚠️ Ошибка при разблокировке пользователя")
        
        break


@router.message(Command("list_bans"))
async def cmd_list_bans(message: Message):
    """Список заблокированных пользователей"""
    if message.from_user.id not in settings.admin_ids:
        await message.answer("⛔ У вас нет прав администратора.")
        return
    
    async for db_session in db_adapter.get_session():
        try:
            banned_users = await ban_service.get_banned_users(db_session, limit=20)
            
            if not banned_users:
                await message.answer("✅ Список блокировок пуст")
                return
            
            text = "🚫 <b>Заблокированные пользователи</b>\n\n"
            
            for user in banned_users:
                text += (
                    f"🆔 <code>{user.telegram_id}</code> - {user.full_name}\n"
                    f"   📝 @{user.username or 'N/A'}\n"
                    f"   ⚠️ Причина: {user.reason}\n"
                    f"   📅 {user.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
                )
            
            await message.answer(text, parse_mode="HTML")
            
        except Exception as e:
            log.error(f"Error listing banned users: {e}")
            await message.answer("⚠️ Ошибка при загрузке списка блокировок")
        
        break


@router.message(Command("check_ban"))
async def cmd_check_ban(message: Message):
    """Проверить статус блокировки пользователя"""
    if message.from_user.id not in settings.admin_ids:
        await message.answer("⛔ У вас нет прав администратора.")
        return
    
    parts = message.text.split()
    
    if len(parts) < 2:
        await message.answer(
            "🔍 <b>Проверка блокировки</b>\n\n"
            "Использование: <code>/check_ban [Telegram ID]</code>\n\n"
            "Пример: <code>/check_ban 123456789</code>",
            parse_mode="HTML"
        )
        return
    
    try:
        telegram_id = int(parts[1])
    except ValueError:
        await message.answer("⚠️ Telegram ID должен быть числом")
        return
    
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
            
            await message.answer(text, parse_mode="HTML")
            
        except Exception as e:
            log.error(f"Error checking ban status for {telegram_id}: {e}")
            await message.answer("⚠️ Ошибка при проверке статуса")
        
        break
