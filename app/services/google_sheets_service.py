"""
Сервис для работы с Google Sheets
"""
from typing import List, Dict, Optional
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from app.core.settings import settings
from app.core.logger import log


class GoogleSheetsService:
    """Сервис для записи заявок в Google Sheets"""

    # Заголовки таблицы
    HEADERS = [
        "ID заявки",
        "Дата",
        "Время",
        "Telegram ID",
        "Username",
        "Имя",
        "Контакт",
        "Сообщение",
        "Статус",
        "Язык"
    ]

    def __init__(self):
        self.client: Optional[gspread.Client] = None
        self.sheet: Optional[gspread.Worksheet] = None
        self._initialized = False

    async def initialize(self) -> bool:
        """Инициализация подключения к Google Sheets"""
        if not settings.GOOGLE_SHEETS_ENABLED:
            log.info("Google Sheets is disabled")
            return False

        if self._initialized:
            return True

        try:
            scopes = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]

            creds = Credentials.from_service_account_file(
                settings.GOOGLE_CREDENTIALS_FILE,
                scopes=scopes
            )

            self.client = gspread.authorize(creds)
            self.sheet = self.client.open_by_key(settings.GOOGLE_SHEETS_ID).sheet1

            existing_headers = self.sheet.row_values(1)
            if not existing_headers or existing_headers[0] != self.HEADERS[0]:
                self.sheet.update('A1:J1', [self.HEADERS])
                log.info("Google Sheets headers created")

            self._initialized = True
            log.info("Google Sheets initialized successfully")
            return True

        except Exception as e:
            log.error(f"Google Sheets initialization error: {e}")
            return False

    async def add_lead(
        self,
        lead_id: int,
        telegram_id: int,
        username: str,
        full_name: str,
        contact: str,
        message_text: str,
        status: str,
        language: str
    ) -> bool:
        """Добавление заявки в Google Sheets"""
        if not self._initialized:
            if not await self.initialize():
                return False

        try:
            now = datetime.now()
            date_str = now.strftime('%d.%m.%Y')
            time_str = now.strftime('%H:%M:%S')

            row = [
                lead_id,
                date_str,
                time_str,
                telegram_id,
                f"@{username}" if username else "N/A",
                full_name or "Не указано",
                contact or "Не указано",
                message_text[:500] if message_text else "Не указано",
                status,
                language
            ]

            self.sheet.append_row(row)
            log.info(f"Lead #{lead_id} added to Google Sheets")
            return True

        except Exception as e:
            log.error(f"Error adding lead to Google Sheets: {e}")
            return False

    async def update_lead_contact(self, lead_id: int, new_contact: str) -> bool:
        """Обновление контакта заявки в Google Sheets"""
        if not self._initialized:
            return False

        try:
            cell = self.sheet.find(str(lead_id))
            if not cell:
                log.warning(f"Lead #{lead_id} not found in Google Sheets")
                return False

            self.sheet.update_cell(cell.row, 7, new_contact)
            log.info(f"Lead #{lead_id} contact updated in Google Sheets: {new_contact}")
            return True

        except Exception as e:
            log.error(f"Error updating lead contact in Google Sheets: {e}")
            return False

    async def update_lead_status(self, lead_id: int, new_status: str) -> bool:
        """Обновление статуса заявки в Google Sheets"""
        if not self._initialized:
            return False

        try:
            cell = self.sheet.find(str(lead_id))
            if not cell:
                log.warning(f"Lead #{lead_id} not found in Google Sheets")
                return False

            self.sheet.update_cell(cell.row, 9, new_status)
            log.info(f"Lead #{lead_id} status updated in Google Sheets: {new_status}")
            return True

        except Exception as e:
            log.error(f"Error updating lead status in Google Sheets: {e}")
            return False

    async def get_all_leads(self) -> List[Dict]:
        """Получение всех заявок из Google Sheets"""
        if not self._initialized:
            return []

        try:
            all_rows = self.sheet.get_all_records()
            log.info(f"Retrieved {len(all_rows)} leads from Google Sheets")
            return all_rows

        except Exception as e:
            log.error(f"Error getting leads from Google Sheets: {e}")
            return []

    async def get_statistics(self) -> Dict:
        """Получение статистики из Google Sheets"""
        if not self._initialized:
            return {}

        try:
            all_rows = self.sheet.get_all_records()

            stats = {
                'total': len(all_rows),
                'new': 0,
                'accepted': 0,
                'callback': 0,
                'rejected': 0
            }

            for row in all_rows:
                status = row.get('Статус', '').lower()
                if status == 'new':
                    stats['new'] += 1
                elif status == 'accepted':
                    stats['accepted'] += 1
                elif status == 'callback':
                    stats['callback'] += 1
                elif status == 'rejected':
                    stats['rejected'] += 1

            return stats

        except Exception as e:
            log.error(f"Error getting statistics from Google Sheets: {e}")
            return {}


# Глобальный экземпляр
google_sheets_service = GoogleSheetsService()
