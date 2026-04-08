FROM python:3.11-slim

# Рабочая директория
WORKDIR /app

# Переменные окружения
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода
COPY . .

# Создание директорий для данных
RUN mkdir -p /app/logs /app/data

# Команда запуска
CMD ["python", "main.py"]
