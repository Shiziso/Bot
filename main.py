#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Главный файл телеграм-бота психолога
"""

import os
import logging
import asyncio
from datetime import datetime

from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler
from telegram.ext import ConversationHandler, filters, ContextTypes

from config import BOT_TOKEN, BOT_INFO, ADMIN_USER_ID
from database import Database
from handlers import (
    start_command, help_command, about_command, daily_tip_command,
    ask_question_command, save_question, cancel_question,
    admin_reply_command, save_admin_reply, cancel_admin_reply, list_questions_command,
    tests_command, test_callback, start_test, process_test_answer,
    techniques_command, show_techniques_category, show_technique_detail, back_to_techniques,
    mood_tracking_command, process_mood_choice, ask_for_mood_notes, save_mood_with_notes,
    save_mood_without_notes, cancel_mood_tracking, show_mood_history_command,
    settings_command, process_settings_choice, save_setting_value, cancel_settings,
    handle_text_message, error_handler
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация базы данных
db = Database()

async def setup_commands(application: Application) -> None:
    """
    Настраивает команды бота для отображения в меню
    """
    commands = [
        BotCommand("start", "Запустить бота и показать главное меню"),
        BotCommand("help", "Показать справку по командам"),
        BotCommand("tip", "Получить совет дня"),
        BotCommand("tests", "Пройти психологический тест"),
        BotCommand("techniques", "Техники самопомощи"),
        BotCommand("mood", "Отслеживание настроения"),
        BotCommand("ask", "Задать вопрос психологу"),
        BotCommand("settings", "Настройки уведомлений"),
        BotCommand("about", "Информация о боте")
    ]
    
    await application.bot.set_my_commands(commands)
    logger.info("Команды бота настроены")

async def send_startup_notification(application: Application) -> None:
    """
    Отправляет уведомление администратору о запуске бота
    """
    try:
        await application.bot.send_message(
            chat_id=ADMIN_USER_ID,
            text=f"🤖 Бот {BOT_INFO['name']} запущен!\n"
                 f"Версия: {BOT_INFO['version']}\n"
                 f"Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        logger.info(f"Уведомление о запуске отправлено администратору (ID: {ADMIN_USER_ID})")
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления администратору: {e}")

async def schedule_daily_tasks(application: Application) -> None:
    """
    Планирует ежедневные задачи бота
    """
    while True:
        # Получаем текущее время
        now = datetime.now()
        
        # Если сейчас 9:00, отправляем ежедневные советы пользователям
        if now.hour == 9 and now.minute == 0:
            await send_daily_tips(application)
        
        # Если сейчас полночь, создаем резервную копию базы данных
        if now.hour == 0 and now.minute == 0:
            db.backup_database()
        
        # Ждем 60 секунд перед следующей проверкой
        await asyncio.sleep(60)

async def send_daily_tips(application: Application) -> None:
    """
    Отправляет ежедневные советы пользователям, которые включили эту опцию
    """
    try:
        # Получаем список пользователей, которые включили ежедневные советы
        users = db.get_users_with_daily_tips()
        
        if not users:
            logger.info("Нет пользователей для отправки ежедневных советов")
            return
        
        # Импортируем список советов
        from data.tips import DAILY_TIPS
        import random
        
        # Для каждого пользователя выбираем совет и отправляем
        for user in users:
            try:
                # Получаем историю советов пользователя
                tips_history = db.get_user_tips_history(user["user_id"])
                recent_tips = [tip["tip_text"] for tip in tips_history]
                
                # Выбираем совет, который не был недавно показан пользователю
                available_tips = [tip for tip in DAILY_TIPS if tip not in recent_tips]
                
                # Если все советы уже были показаны, используем полный список
                if not available_tips:
                    available_tips = DAILY_TIPS
                
                # Выбираем случайный совет
                tip = random.choice(available_tips)
                
                # Сохраняем совет в историю
                db.save_daily_tip(user["user_id"], tip)
                
                # Отправляем совет пользователю
                await application.bot.send_message(
                    chat_id=user["user_id"],
                    text=f"🧠 *Совет дня:*\n\n{tip}\n\n"
                         f"Хорошего вам дня! Для получения дополнительных советов используйте команду /tip.",
                    parse_mode="Markdown"
                )
                
                logger.info(f"Ежедневный совет отправлен пользователю {user['user_id']}")
            
            except Exception as e:
                logger.error(f"Ошибка при отправке ежедневного совета пользователю {user['user_id']}: {e}")
        
        logger.info(f"Ежедневные советы отправлены {len(users)} пользователям")
    
    except Exception as e:
        logger.error(f"Ошибка при отправке ежедневных советов: {e}")

def main() -> None:
    """
    Основная функция для запуска бота
    """
    # Проверяем наличие токена
    if not BOT_TOKEN:
        logger.error("Токен бота не найден. Пожалуйста, укажите его в config.py")
        return
    
    # Инициализируем базу данных
    db.init_db()
    logger.info("База данных инициализирована")
    
    # Создаем экземпляр приложения
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрируем обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("about", about_command))
    application.add_handler(CommandHandler("tip", daily_tip_command))
    application.add_handler(CommandHandler("list_questions", list_questions_command))
    application.add_handler(CommandHandler("mood_history", show_mood_history_command))
    
    # Регистрируем обработчик для анонимных вопросов
    ask_question_handler = ConversationHandler(
        entry_points=[CommandHandler("ask", ask_question_command)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_question)]
        },
        fallbacks=[CommandHandler("cancel", cancel_question)]
    )
    application.add_handler(ask_question_handler)
    
    # Регистрируем обработчик для ответов администратора
    admin_reply_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^/reply_\d+$"), admin_reply_command)],
        states={
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_admin_reply)]
        },
        fallbacks=[CommandHandler("cancel", cancel_admin_reply)]
    )
    application.add_handler(admin_reply_handler)
    
    # Регистрируем обработчик для психологических тестов
    tests_handler = ConversationHandler(
        entry_points=[CommandHandler("tests", tests_command)],
        states={
            1: [CallbackQueryHandler(test_callback, pattern=r"^test_")],
            2: [CallbackQueryHandler(start_test, pattern=r"^confirm_")],
            3: [CallbackQueryHandler(process_test_answer, pattern=r"^answer_")],
            4: [CallbackQueryHandler(test_callback, pattern=r"^test_")]
        },
        fallbacks=[CommandHandler("cancel", lambda update, context: ConversationHandler.END)]
    )
    application.add_handler(tests_handler)
    
    # Регистрируем обработчик для техник самопомощи
    techniques_handler = ConversationHandler(
        entry_points=[CommandHandler("techniques", techniques_command)],
        states={
            1: [CallbackQueryHandler(show_techniques_category, pattern=r"^cat_")],
            2: [
                CallbackQueryHandler(show_technique_detail, pattern=r"^tech_"),
                CallbackQueryHandler(back_to_techniques, pattern=r"^detail_")
            ]
        },
        fallbacks=[CommandHandler("cancel", lambda update, context: ConversationHandler.END)]
    )
    application.add_handler(techniques_handler)
    
    # Регистрируем обработчик для отслеживания настроения
    mood_handler = ConversationHandler(
        entry_points=[CommandHandler("mood", mood_tracking_command)],
        states={
            1: [CallbackQueryHandler(process_mood_choice, pattern=r"^mood_")],
            2: [
                CallbackQueryHandler(ask_for_mood_notes, pattern=r"^notes_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_mood_with_notes)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel_mood_tracking)]
    )
    application.add_handler(mood_handler)
    
    # Регистрируем обработчик для настроек
    settings_handler = ConversationHandler(
        entry_points=[CommandHandler("settings", settings_command)],
        states={
            1: [
                CallbackQueryHandler(process_settings_choice, pattern=r"^settings_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_setting_value)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel_settings)]
    )
    application.add_handler(settings_handler)
    
    # Регистрируем обработчик для текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    
    # Запускаем задачи при старте бота
    application.post_init = setup_commands
    application.post_shutdown = lambda app: logger.info("Бот остановлен")
    
    # Запускаем бота
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    
    # Запускаем асинхронные задачи
    loop = asyncio.get_event_loop()
    loop.create_task(send_startup_notification(application))
    loop.create_task(schedule_daily_tasks(application))

if __name__ == "__main__":
    main()
