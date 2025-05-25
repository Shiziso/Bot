#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Главный модуль телеграм-бота
"""

import os
import sys
import signal
import logging
from typing import Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes
)

from config import BOT_TOKEN, ADMIN_USER_ID
from database import Database
from handlers import (
    start_command,
    help_command,
    about_command,
    cancel_command,
    test_command,
    show_test_categories,
    select_test,
    process_test_answer,
    show_test_result,
    mood_tracking_command,
    select_mood,
    save_mood_without_notes,
    save_mood_with_notes,
    show_mood_history,
    techniques_command,
    show_techniques_category,
    show_technique_details,
    back_to_techniques,
    back_to_categories,
    question_command,
    process_question,
    show_questions,
    answer_question,
    save_question_answer,
    unknown_command,
    error_handler
)
from utils import error_handler
from stats.admin_stats import AdminStats

# Константы для состояний разговора
SELECTING_TEST, ANSWERING_TEST, SHOWING_RESULT = range(3)
SELECTING_MOOD, ENTERING_NOTES = range(2)
SHOWING_CATEGORIES, SHOWING_TECHNIQUE = range(2)
ENTERING_QUESTION = range(1)
ANSWERING_QUESTION = range(1)
SELECTING_STATS_PERIOD = range(1)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация базы данных
db = Database()

def signal_handler(sig, frame):
    """
    Обработчик сигналов завершения
    """
    logger.info("Получен сигнал завершения, закрываю соединения...")
    # Закрываем соединения с базой данных
    if hasattr(db, 'disconnect'):
        db.disconnect()
    logger.info("Бот остановлен")
    sys.exit(0)

def main() -> None:
    """
    Основная функция для запуска бота
    """
    # Инициализация базы данных
    db.init_db()
    
    # Инициализация обработчика административных команд
    admin_stats = AdminStats(db)
    
    # Создание приложения
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрация обработчиков команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("about", about_command))
    
    # Обработчик для тестов
    test_conversation = ConversationHandler(
        entry_points=[CommandHandler("test", test_command)],
        states={
            SELECTING_TEST: [CallbackQueryHandler(select_test, pattern=r"^test_")],
            ANSWERING_TEST: [CallbackQueryHandler(process_test_answer, pattern=r"^answer_")],
            SHOWING_RESULT: [CallbackQueryHandler(show_test_result, pattern=r"^result_")]
        },
        fallbacks=[CommandHandler("cancel", cancel_command)],
        conversation_timeout=300  # Тайм-аут 5 минут
    )
    application.add_handler(test_conversation)
    
    # Обработчик для отслеживания настроения
    mood_conversation = ConversationHandler(
        entry_points=[CommandHandler("mood", mood_tracking_command)],
        states={
            SELECTING_MOOD: [
                CallbackQueryHandler(select_mood, pattern=r"^mood_"),
                CallbackQueryHandler(show_mood_history, pattern=r"^history$")
            ],
            ENTERING_NOTES: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_mood_with_notes),
                CallbackQueryHandler(save_mood_without_notes, pattern=r"^skip$")
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel_command)],
        conversation_timeout=300  # Тайм-аут 5 минут
    )
    application.add_handler(mood_conversation)
    
    # Обработчик для техник самопомощи
    techniques_conversation = ConversationHandler(
        entry_points=[CommandHandler("techniques", techniques_command)],
        states={
            SHOWING_CATEGORIES: [CallbackQueryHandler(show_techniques_category, pattern=r"^cat_")],
            SHOWING_TECHNIQUE: [
                CallbackQueryHandler(show_technique_details, pattern=r"^tech_\d+$"),
                CallbackQueryHandler(back_to_categories, pattern=r"^tech_back$")
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel_command)],
        conversation_timeout=300  # Тайм-аут 5 минут
    )
    application.add_handler(techniques_conversation)
    
    # Обработчик для анонимных вопросов
    question_conversation = ConversationHandler(
        entry_points=[CommandHandler("question", question_command)],
        states={
            ENTERING_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_question)]
        },
        fallbacks=[CommandHandler("cancel", cancel_command)],
        conversation_timeout=300  # Тайм-аут 5 минут
    )
    application.add_handler(question_conversation)
    
    # Обработчик для ответов на вопросы (только для администратора)
    answer_conversation = ConversationHandler(
        entry_points=[CommandHandler("questions", show_questions)],
        states={
            ANSWERING_QUESTION: [
                CallbackQueryHandler(answer_question, pattern=r"^q_\d+$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_question_answer)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel_command)],
        conversation_timeout=300  # Тайм-аут 5 минут
    )
    application.add_handler(answer_conversation)
    
    # Обработчик для статистики (только для администратора)
    stats_conversation = ConversationHandler(
        entry_points=[CommandHandler("stats", admin_stats.stats_command)],
        states={
            SELECTING_STATS_PERIOD: [CallbackQueryHandler(admin_stats.select_stats_period, pattern=r"^stats_period_")]
        },
        fallbacks=[CommandHandler("cancel", cancel_command)],
        conversation_timeout=300  # Тайм-аут 5 минут
    )
    application.add_handler(stats_conversation)
    
    # Обработчики для других административных команд
    application.add_handler(CommandHandler("active_users", admin_stats.active_users_command))
    application.add_handler(CommandHandler("commands_stats", admin_stats.commands_stats_command))
    
    # Обработчик для неизвестных команд
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Регистрируем обработчик сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Запуск бота
    logger.info("Бот запущен")
    application.run_polling()

if __name__ == "__main__":
    main()
