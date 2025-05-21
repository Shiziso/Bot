#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль конфигурации для телеграм-бота психолога
"""

# Токен бота (заменить на реальный токен)
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

# ID администратора (заменить на реальный ID)
ADMIN_USER_ID = 123456789

# Информация о боте
BOT_INFO = {
    "name": "PsihoTips Bot",
    "version": "2.0.0",
    "description": "Бот-помощник врача-психотерапевта для поддержки ментального здоровья",
    "channel": "@psihotips_channel",
    "website": "https://psihotips.ru"
}

# Эмодзи для настроения
MOOD_EMOJIS = {
    "great": "😄 Отлично",
    "good": "🙂 Хорошо",
    "neutral": "😐 Нормально",
    "bad": "😔 Плохо",
    "awful": "😢 Ужасно",
    "anxious": "😰 Тревожно",
    "angry": "😠 Злость",
    "tired": "😴 Усталость"
}

# Настройки уведомлений
NOTIFICATION_SETTINGS = {
    "new_question_emoji": "❓",
    "answered_question_emoji": "✅",
    "viewed_question_emoji": "👁️"
}

# Ограничения на использование функций (защита от злоупотреблений)
RATE_LIMIT = {
    "daily_tip": 3600,  # 1 час между запросами совета дня
    "anonymous_question": 86400,  # 24 часа между анонимными вопросами
    "test": 3600  # 1 час между прохождениями тестов
}

# Настройки базы данных
DATABASE = {
    "type": "sqlite",  # sqlite или postgresql
    "sqlite_path": "bot_database.db",
    "postgresql": {
        "host": "localhost",
        "port": 5432,
        "database": "psihotips_bot",
        "user": "postgres",
        "password": "password"
    }
}
