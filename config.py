#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Конфигурационный файл телеграм-бота
"""

# Токен бота, полученный от @BotFather
BOT_TOKEN = "8093256646:AAH5Zybvzhzkk-ZBTFRzrVq1X2wn_4yO8ps"

# ID администратора бота
ADMIN_USER_ID = 1398676375

# Настройки базы данных
DATABASE = {
    "type": "postgresql",  # тип базы данных: sqlite или postgresql
    "sqlite_path": "bot_database.db",  # путь к файлу SQLite (используется только при type = "sqlite")
    "postgresql": {
        "host": "postgres",  # имя хоста (postgres - имя сервиса в docker-compose)
        "port": 5432,  # порт PostgreSQL
        "database": "botdb",  # имя базы данных
        "user": "botuser",  # имя пользователя
        "password": "Ihavepipilo963"  # пароль
    }
}

# Настройки уведомлений
NOTIFICATION_SETTINGS = {
    "daily_tip_emoji": "💡",
    "answered_question_emoji": "✅",
    "unanswered_question_emoji": "❓"
}

# Настройки тестов
TEST_SETTINGS = {
    "questions_per_page": 1,  # количество вопросов на странице
    "default_test_time": 300  # время на прохождение теста в секундах
}
