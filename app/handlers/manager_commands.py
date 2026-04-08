"""
Обработчик команд менеджера (/leads, /lead_info, /search)
"""
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy import select, desc, func
from app.core.logger import log
from app.core.settings import settings
from app.database.adapter import db_adapter
from app.database.models import Lead, LeadStatus, LeadStatusHistory
from app.keyboards.inline_kb import get_pagination_keyboard

router = Router()


@router.message(Command("leads"))
async def cmd_leads(message: Message):
    """Показать список заявок"""
    # Проверяем, что команда из чата менеджера
    if str(message.chat.id) != str(settings.MANAGER_CHAT_ID):
        return
    
    await show_leads_list(message, page=1)


async def show_leads_list(message: Message, page: int = 1):
    """Показать список заявок с пагинацией"""
    per_page = 10
    offset = (page - 1) * per_page
    
    async for db_session in db_adapter.get_session():
        try:
            # Получаем общее количество заявок
            count_result = await db_session.execute(
                select(func.count(Lead.id))
            )
            total_leads = count_result.scalar() or 0
            
            # Получаем заявки
            result = await db_session.execute(
                select(Lead)
                .order_by(desc(Lead.created_at))
                .offset(offset)
                .limit(per_page)
            )
            leads = result.scalars().all()
            
            if not leads:
                await message.answer("📋 Список заявок пуст")
                return
            
            # Формируем текст
            text = f"📋 <b>Заявки (страница {page})</b>\n\n"
            text += f"Всего заявок: {total_leads}\n\n"
            
            for lead in leads:
                status_emoji = {
                    LeadStatus.NEW: "🆕",
                    LeadStatus.ACCEPTED: "✅",
                    LeadStatus.CALLBACK: "📞",
                    LeadStatus.REJECTED: "❌"
                }.get(lead.status, "📋")
                
                text += (
                    f"{status_emoji} <b>#{lead.id}</b> - {lead.full_name or 'Без имени'}\n"
                    f"   📞 {lead.contact or 'Нет контакта'}\n"
                    f"   📅 {lead.created_at.strftime('%d.%m %H:%M')}\n\n"
                )
            
            # Клавиатура пагинации
            has_next = total_leads > (page * per_page)
            keyboard = get_pagination_keyboard(page, has_next)
            
            await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
            
        except Exception as e:
            log.error(f"Error showing leads list: {e}")
            await message.answer("⚠️ Ошибка при загрузке списка заявок")
        
        break


@router.message(Command("lead_info"))
async def cmd_lead_info(message: Message):
    """Показать информацию о заявке по ID"""
    if str(message.chat.id) != str(settings.MANAGER_CHAT_ID):
        return
    
    # Проверяем, есть ли аргумент (ID заявки)
    text = message.text.strip()
    
    if len(text.split()) < 2:
        await message.answer(
            "📝 Использование: <code>/lead_info [ID]</code>\n\n"
            "Пример: <code>/lead_info 123</code>",
            parse_mode="HTML"
        )
        return
    
    try:
        lead_id = int(text.split()[1])
    except ValueError:
        await message.answer("⚠️ ID должен быть числом")
        return
    
    async for db_session in db_adapter.get_session():
        try:
            result = await db_session.execute(
                select(Lead).where(Lead.id == lead_id)
            )
            lead = result.scalar_one_or_none()
            
            if not lead:
                await message.answer(f"⚠️ Заявка #{lead_id} не найдена")
                return
            
            # Формируем текст
            status_emoji = {
                LeadStatus.NEW: "🆕",
                LeadStatus.ACCEPTED: "✅",
                LeadStatus.CALLBACK: "📞",
                LeadStatus.REJECTED: "❌"
            }.get(lead.status, "📋")
            
            text = (
                f"{status_emoji} <b>Заявка #{lead.id}</b>\n\n"
                f"👤 <b>Имя:</b> {lead.full_name or 'Не указано'}\n"
                f"🆔 <b>Telegram:</b> @{lead.username or 'N/A'} (ID: <code>{lead.telegram_id}</code>)\n"
                f"📞 <b>Контакт:</b> <code>{lead.contact or 'Не указано'}</code>\n"
                f"🌐 <b>Язык:</b> {'🇷🇺 Русский' if lead.language == 'ru' else '🇬🇧 English'}\n\n"
                f"💬 <b>Сообщение:</b>\n"
                f"<i>{lead.message_text[:500] if lead.message_text else 'Не указано'}</i>\n\n"
                f"📅 <b>Создана:</b> {lead.created_at.strftime('%d.%m.%Y %H:%M')}\n"
                f"🔄 <b>Обновлена:</b> {lead.updated_at.strftime('%d.%m.%Y %H:%M')}\n"
            )
            
            await message.answer(text, parse_mode="HTML")
            
        except Exception as e:
            log.error(f"Error showing lead info for #{lead_id}: {e}")
            await message.answer("⚠️ Ошибка при загрузке информации о заявке")
        
        break


@router.message(Command("search"))
async def cmd_search(message: Message):
    """Поиск заявки по Telegram ID, username или контакту"""
    if str(message.chat.id) != str(settings.MANAGER_CHAT_ID):
        return
    
    # Проверяем, есть ли аргумент
    text = message.text.strip()
    
    if len(text.split()) < 2:
        await message.answer(
            "🔍 Использование: <code>/search [запрос]</code>\n\n"
            "Примеры:\n"
            "• <code>/search 7901094710</code> (по Telegram ID)\n"
            "• <code>/search @username</code> (по username)\n"
            "• <code>/search +79991234567</code> (по телефону)\n"
            "• <code>/search Иван</code> (по имени)",
            parse_mode="HTML"
        )
        return
    
    query = text.split(maxsplit=1)[1].strip()
    
    async for db_session in db_adapter.get_session():
        try:
            # Ищем по разным полям
            from sqlalchemy import or_
            
            result = await db_session.execute(
                select(Lead)
                .where(
                    or_(
                        Lead.telegram_id == int(query) if query.isdigit() else None,
                        Lead.username == query.lstrip('@'),
                        Lead.contact == query,
                        Lead.full_name.ilike(f"%{query}%")
                    )
                )
                .order_by(desc(Lead.created_at))
                .limit(10)
            )
            leads = result.scalars().all()
            
            if not leads:
                await message.answer(f"🔍 По запросу '<code>{query}</code>' ничего не найдено")
                return
            
            # Формируем текст
            text = f"🔍 <b>Результаты поиска</b> ({len(leads)}):\n\n"
            
            for lead in leads:
                status_emoji = {
                    LeadStatus.NEW: "🆕",
                    LeadStatus.ACCEPTED: "✅",
                    LeadStatus.CALLBACK: "📞",
                    LeadStatus.REJECTED: "❌"
                }.get(lead.status, "📋")
                
                text += (
                    f"{status_emoji} <b>#{lead.id}</b> - {lead.full_name or 'Без имени'}\n"
                    f"   🆔 Telegram: <code>{lead.telegram_id}</code>\n"
                    f"   📞 {lead.contact or 'Нет контакта'}\n"
                    f"   📅 {lead.created_at.strftime('%d.%m %H:%M')}\n\n"
                )
            
            await message.answer(text, parse_mode="HTML")
            
        except Exception as e:
            log.error(f"Error searching leads: {e}")
            await message.answer("⚠️ Ошибка при поиске")
        
        break


@router.message(Command("new_leads"))
async def cmd_new_leads(message: Message):
    """Показать только новые заявки"""
    if str(message.chat.id) != str(settings.MANAGER_CHAT_ID):
        return
    
    async for db_session in db_adapter.get_session():
        try:
            result = await db_session.execute(
                select(Lead)
                .where(Lead.status == LeadStatus.NEW)
                .order_by(desc(Lead.created_at))
                .limit(10)
            )
            leads = result.scalars().all()
            
            if not leads:
                await message.answer("✅ Новых заявок нет!")
                return
            
            text = f"🆕 <b>Новые заявки</b> ({len(leads)}):\n\n"
            
            for lead in leads:
                text += (
                    f"📋 <b>#{lead.id}</b> - {lead.full_name or 'Без имени'}\n"
                    f"   📞 {lead.contact or 'Нет контакта'}\n"
                    f"   💬 {lead.message_text[:100] if lead.message_text else 'Нет сообщения'}\n"
                    f"   📅 {lead.created_at.strftime('%d.%m %H:%M')}\n\n"
                )
            
            await message.answer(text, parse_mode="HTML")
            
        except Exception as e:
            log.error(f"Error showing new leads: {e}")
            await message.answer("⚠️ Ошибка при загрузке")
        
        break


@router.message(Command("callback_leads"))
async def cmd_callback_leads(message: Message):
    """Показать заявки требующие перезвона"""
    if str(message.chat.id) != str(settings.MANAGER_CHAT_ID):
        return
    
    async for db_session in db_adapter.get_session():
        try:
            result = await db_session.execute(
                select(Lead)
                .where(Lead.status == LeadStatus.CALLBACK)
                .order_by(desc(Lead.created_at))
                .limit(10)
            )
            leads = result.scalars().all()
            
            if not leads:
                await message.answer("✅ Заявок требующих перезвона нет!")
                return
            
            text = f"📞 <b>Требуют перезвона</b> ({len(leads)}):\n\n"
            
            for lead in leads:
                text += (
                    f"📋 <b>#{lead.id}</b> - {lead.full_name or 'Без имени'}\n"
                    f"   📞 {lead.contact or 'Нет контакта'}\n"
                    f"   🆔 Telegram: <code>{lead.telegram_id}</code>\n"
                    f"   📅 {lead.created_at.strftime('%d.%m %H:%M')}\n\n"
                )
            
            await message.answer(text, parse_mode="HTML")
            
        except Exception as e:
            log.error(f"Error showing callback leads: {e}")
            await message.answer("⚠️ Ошибка при загрузке")
        
        break
