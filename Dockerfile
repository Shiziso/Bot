FROM python:3.11-slim

# Установка необходимых пакетов
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Установка рабочей директории
WORKDIR /app

# Копирование файлов проекта
COPY . /app/

# Создание директории для логов
RUN mkdir -p /app/logs && chmod 777 /app/logs

# Создание директории для инициализации БД (если её нет)
RUN mkdir -p /app/db_init

# Установка зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Проверка наличия критичных файлов
RUN if [ ! -f "main.py" ] || [ ! -f "config.py" ]; then \
    echo "Критичные файлы отсутствуют!" && exit 1; \
    fi

# Добавление заглушки для MOOD_TRACKING_SETTINGS в config.py, если её нет
RUN grep -q "MOOD_TRACKING_SETTINGS" config.py || echo 'MOOD_TRACKING_SETTINGS = {"enabled": True, "frequency": "daily"}' >> config.py

# Скрипт ожидания PostgreSQL должен быть исполняемым
COPY wait-for-postgres.sh /app/
RUN chmod +x /app/wait-for-postgres.sh

# Запуск бота
CMD ["./wait-for-postgres.sh", "python", "main.py"]
