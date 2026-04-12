"""
Скрипт для удаления всех заявок из БД
"""
import asyncio
import sqlite3
from app.core.settings import settings


async def clear_leads():
    """Удалить все заявки и историю статусов"""
    db_path = settings.SQLITE_PATH

    print(f"🗑 Подключение к БД: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Считаем записи до удаления
    cursor.execute("SELECT COUNT(*) FROM leads")
    leads_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM lead_status_history")
    history_count = cursor.fetchone()[0]

    print(f"📋 Найдено заявок: {leads_count}")
    print(f"📋 Записей истории статусов: {history_count}")

    if leads_count == 0 and history_count == 0:
        print("✅ База данных уже пуста")
        conn.close()
        return

    # Удаляем
    cursor.execute("DELETE FROM lead_status_history")
    cursor.execute("DELETE FROM leads")

    # Сбрасываем autoincrement (если таблица существует)
    try:
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='leads'")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='lead_status_history'")
    except Exception:
        pass  # sqlite_sequence может не существовать

    conn.commit()
    conn.close()

    print(f"✅ Удалено заявок: {leads_count}")
    print(f"✅ Удалено записей истории: {history_count}")
    print("✅ База данных очищена!")


if __name__ == "__main__":
    asyncio.run(clear_leads())
