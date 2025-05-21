#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import random
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, ConversationHandler

from database import Database
from config import ADMIN_USER_ID, MOOD_EMOJIS, BOT_INFO, NOTIFICATION_SETTINGS, RATE_LIMIT
from utils import rate_limit, format_datetime, get_user_mention, split_text

# Настройка логирования
logger = logging.getLogger(__name__)

# Инициализация базы данных
db = Database()

# --- Состояния для разговоров ---
# Основное меню
MAIN_MENU = 0

# Анонимные вопросы
ASKING_QUESTION = 1
ADMIN_REPLYING = 2

# Тесты
CHOOSING_TEST = 1
CONFIRMING_TEST = 2
TAKING_TEST = 3
SHOWING_RESULT = 4

# Техники самопомощи
CHOOSING_TECHNIQUE = 1
SHOWING_TECHNIQUE = 2

# Отслеживание настроения
CHOOSING_MOOD = 1
ADDING_NOTES = 2

# Настройки
CHANGING_SETTINGS = 1

# --- Обработчики команд ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обрабатывает команду /start, регистрирует пользователя и показывает приветственное сообщение
    """
    user = update.effective_user
    
    # Регистрируем пользователя в базе данных
    db.register_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    # Логируем использование команды
    db.log_command_usage(user.id, "start")
    
    # Обновляем время последней активности
    db.update_user_activity(user.id)
    
    # Создаем клавиатуру для главного меню
    keyboard = [
        [KeyboardButton("🧠 Совет дня"), KeyboardButton("📊 Пройти тест")],
        [KeyboardButton("🛠 Техники самопомощи"), KeyboardButton("😊 Отслеживание настроения")],
        [KeyboardButton("❓ Задать вопрос врачу"), KeyboardButton("⚙️ Настройки")]
    ]
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    # Приветственное сообщение с элементами маркетинга и эмпатии
    welcome_message = (
        f"👋 Здравствуйте, {user.first_name}!\n\n"
        f"Я бот-помощник врача-психотерапевта, созданный для поддержки вашего ментального здоровья.\n\n"
        f"🧠 Что я могу для вас сделать:\n"
        f"• Предложить ежедневный совет для улучшения самочувствия\n"
        f"• Провести психологические тесты с интерпретацией результатов\n"
        f"• Показать техники самопомощи при тревоге, стрессе и других состояниях\n"
        f"• Помочь отслеживать ваше настроение\n"
        f"• Передать ваш вопрос врачу (анонимно)\n\n"
        f"💬 Присоединяйтесь к нашему каналу {BOT_INFO['channel']} для получения полезных материалов о ментальном здоровье.\n\n"
        f"🤝 Помните: забота о психическом здоровье — это проявление силы, а не слабости. Я здесь, чтобы поддержать вас на этом пути."
    )
    
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)
    return MAIN_MENU

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает команду /help, показывает справочную информацию
    """
    user = update.effective_user
    
    # Логируем использование команды
    db.log_command_usage(user.id, "help")
    
    # Обновляем время последней активности
    db.update_user_activity(user.id)
    
    help_message = (
        "🔍 *Справка по командам бота*\n\n"
        "/start - Запустить бота и показать главное меню\n"
        "/help - Показать эту справку\n"
        "/tip - Получить совет дня\n"
        "/tests - Пройти психологический тест\n"
        "/techniques - Техники самопомощи\n"
        "/mood - Отслеживание настроения\n"
        "/ask - Задать вопрос врачу\n"
        "/settings - Настройки уведомлений\n"
        "/about - Информация о боте\n\n"
        "Вы также можете использовать кнопки меню для доступа к функциям бота."
    )
    
    await update.message.reply_text(help_message, parse_mode="Markdown")

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает команду /about, показывает информацию о боте
    """
    user = update.effective_user
    
    # Логируем использование команды
    db.log_command_usage(user.id, "about")
    
    # Обновляем время последней активности
    db.update_user_activity(user.id)
    
    about_message = (
        f"ℹ️ *О боте {BOT_INFO['name']}*\n\n"
        f"Версия: {BOT_INFO['version']}\n\n"
        f"{BOT_INFO['description']}\n\n"
        f"Этот бот создан для поддержки вашего ментального здоровья и предоставления доступа к профессиональной помощи.\n\n"
        f"🔗 *Полезные ссылки:*\n"
        f"• Канал: {BOT_INFO['channel']}\n"
        f"• Сайт: {BOT_INFO['website']}\n\n"
        f"Если у вас есть вопросы или предложения, используйте функцию «Задать вопрос врачу»."
    )
    
    await update.message.reply_text(about_message, parse_mode="Markdown")

@rate_limit("daily_tip", RATE_LIMIT["daily_tip"])
async def daily_tip_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает команду /tip, показывает совет дня с учетом истории
    """
    user = update.effective_user
    
    # Логируем использование команды
    db.log_command_usage(user.id, "tip")
    
    # Обновляем время последней активности
    db.update_user_activity(user.id)
    
    # Получаем историю советов пользователя
    tips_history = db.get_user_tips_history(user.id)
    recent_tips = [tip["tip_text"] for tip in tips_history]
    
    # Импортируем список советов из конфигурации
    from data.tips import DAILY_TIPS
    
    # Выбираем совет, который не был недавно показан пользователю
    available_tips = [tip for tip in DAILY_TIPS if tip not in recent_tips]
    
    # Если все советы уже были показаны, используем полный список
    if not available_tips:
        available_tips = DAILY_TIPS
    
    # Выбираем случайный совет
    tip = random.choice(available_tips)
    
    # Сохраняем совет в историю
    db.save_daily_tip(user.id, tip)
    
    # Отправляем совет пользователю
    tip_message = (
        f"🧠 *Совет дня:*\n\n"
        f"{tip}\n\n"
        f"Надеюсь, этот совет будет полезен для вас сегодня! Возвращайтесь завтра за новым советом."
    )
    
    # Добавляем кнопку для перехода на канал
    keyboard = [
        [InlineKeyboardButton("📚 Больше полезных материалов", url=BOT_INFO["website"])]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(tip_message, parse_mode="Markdown", reply_markup=reply_markup)

# --- Обработчики для анонимных вопросов ---

async def ask_question_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обрабатывает команду /ask, начинает диалог для отправки анонимного вопроса
    """
    user = update.effective_user
    
    # Логируем использование команды
    db.log_command_usage(user.id, "ask")
    
    # Обновляем время последней активности
    db.update_user_activity(user.id)
    
    # Проверяем, есть ли у пользователя неотвеченные вопросы
    user_questions = db.get_user_questions(user.id)
    unanswered_questions = [q for q in user_questions if q["status"] == NOTIFICATION_SETTINGS["new_question_emoji"]]
    
    if unanswered_questions:
        # Если есть неотвеченные вопросы, предлагаем подождать
        await update.message.reply_text(
            "У вас уже есть неотвеченные вопросы. Пожалуйста, дождитесь ответа на них, прежде чем задавать новые вопросы."
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        "📝 Пожалуйста, напишите ваш вопрос врачу. Он будет передан анонимно.\n\n"
        "Для отмены отправьте /cancel."
    )
    
    return ASKING_QUESTION

@rate_limit("anonymous_question", RATE_LIMIT["anonymous_question"])
async def save_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Сохраняет анонимный вопрос пользователя и уведомляет администратора
    """
    user = update.effective_user
    question_text = update.message.text
    
    # Сохраняем вопрос в базе данных
    question_id = db.save_anonymous_question(user.id, question_text)
    
    if question_id:
        # Отправляем подтверждение пользователю
        await update.message.reply_text(
            "✅ Ваш вопрос успешно отправлен врачу. Вы получите уведомление, когда на него ответят."
        )
        
        # Уведомляем администратора о новом вопросе
        admin_notification = (
            f"{NOTIFICATION_SETTINGS['new_question_emoji']} *Новый анонимный вопрос*\n\n"
            f"*Вопрос:* {question_text}\n\n"
            f"Для ответа используйте команду /reply_{question_id}"
        )
        
        try:
            await context.bot.send_message(
                chat_id=ADMIN_USER_ID,
                text=admin_notification,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления администратору: {e}")
    else:
        # В случае ошибки
        await update.message.reply_text(
            "❌ Произошла ошибка при сохранении вашего вопроса. Пожалуйста, попробуйте позже."
        )
    
    return ConversationHandler.END

async def cancel_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Отменяет процесс отправки анонимного вопроса
    """
    await update.message.reply_text(
        "❌ Отправка вопроса отменена."
    )
    
    return ConversationHandler.END

async def admin_reply_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обрабатывает команду администратора для ответа на вопрос
    """
    user = update.effective_user
    
    # Проверяем, является ли пользователь администратором
    if user.id != ADMIN_USER_ID:
        await update.message.reply_text("У вас нет доступа к этой команде.")
        return ConversationHandler.END
    
    # Извлекаем ID вопроса из команды (формат: /reply_123)
    command_parts = update.message.text.split('_')
    if len(command_parts) != 2:
        await update.message.reply_text("Неверный формат команды. Используйте /reply_ID")
        return ConversationHandler.END
    
    try:
        question_id = int(command_parts[1])
    except ValueError:
        await update.message.reply_text("Неверный ID вопроса.")
        return ConversationHandler.END
    
    # Получаем информацию о вопросе
    question = db.get_question_by_id(question_id)
    
    if not question:
        await update.message.reply_text("Вопрос не найден.")
        return ConversationHandler.END
    
    # Сохраняем ID вопроса в контексте
    context.user_data["question_id"] = question_id
    
    # Показываем вопрос и запрашиваем ответ
    await update.message.reply_text(
        f"*Вопрос:* {question['question_text']}\n\n"
        f"Пожалуйста, напишите ваш ответ. Для отмены отправьте /cancel.",
        parse_mode="Markdown"
    )
    
    return ADMIN_REPLYING

async def save_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Сохраняет ответ администратора и отправляет его пользователю
    """
    answer_text = update.message.text
    question_id = context.user_data.get("question_id")
    
    if not question_id:
        await update.message.reply_text("Ошибка: ID вопроса не найден.")
        return ConversationHandler.END
    
    # Получаем информацию о вопросе
    question = db.get_question_by_id(question_id)
    
    if not question:
        await update.message.reply_text("Вопрос не найден.")
        return ConversationHandler.END
    
    # Сохраняем ответ в базе данных
    success = db.save_question_answer(question_id, answer_text)
    
    if success:
        # Отправляем подтверждение администратору
        await update.message.reply_text(
            f"✅ Ваш ответ успешно сохранен и отправлен пользователю."
        )
        
        # Отправляем ответ пользователю
        user_notification = (
            f"{NOTIFICATION_SETTINGS['answered_question_emoji']} *Получен ответ на ваш вопрос*\n\n"
            f"*Ваш вопрос:* {question['question_text']}\n\n"
            f"*Ответ врача:* {answer_text}\n\n"
            f"Если у вас есть дополнительные вопросы, вы можете задать их с помощью команды /ask."
        )
        
        try:
            await context.bot.send_message(
                chat_id=question["user_id"],
                text=user_notification,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка при отправке ответа пользователю: {e}")
            await update.message.reply_text(
                "⚠️ Ответ сохранен, но возникла ошибка при отправке уведомления пользователю."
            )
    else:
        # В случае ошибки
        await update.message.reply_text(
            "❌ Произошла ошибка при сохранении ответа. Пожалуйста, попробуйте позже."
        )
    
    return ConversationHandler.END

async def cancel_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Отменяет процесс ответа на вопрос
    """
    await update.message.reply_text(
        "❌ Ответ на вопрос отменен."
    )
    
    # Очищаем данные контекста
    if "question_id" in context.user_data:
        del context.user_data["question_id"]
    
    return ConversationHandler.END

async def list_questions_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Показывает список вопросов для администратора
    """
    user = update.effective_user
    
    # Проверяем, является ли пользователь администратором
    if user.id != ADMIN_USER_ID:
        await update.message.reply_text("У вас нет доступа к этой команде.")
        return
    
    # Получаем параметр фильтрации (если есть)
    filter_param = None
    if context.args and len(context.args) > 0:
        filter_param = context.args[0]
    
    # Получаем вопросы из базы данных
    if filter_param == "new":
        questions = db.get_unanswered_questions()
        status_text = "неотвеченных"
    elif filter_param == "answered":
        # Здесь нужно реализовать получение отвеченных вопросов
        questions = []  # Заглушка
        status_text = "отвеченных"
    else:
        # По умолчанию показываем все вопросы
        questions = []  # Заглушка
        status_text = "всех"
    
    if not questions:
        await update.message.reply_text(f"Список {status_text} вопросов пуст.")
        return
    
    # Формируем сообщение со списком вопросов
    message = f"📋 Список {status_text} вопросов:\n\n"
    
    for i, question in enumerate(questions, 1):
        # Ограничиваем длину вопроса для отображения
        short_question = question["question_text"][:50] + "..." if len(question["question_text"]) > 50 else question["question_text"]
        
        message += (
            f"{i}. {question['status']} ID: {question['question_id']}\n"
            f"   {short_question}\n"
            f"   Дата: {format_datetime(question['date_asked'])}\n"
            f"   Команда для ответа: /reply_{question['question_id']}\n\n"
        )
    
    # Разбиваем сообщение на части, если оно слишком длинное
    for part in split_text(message):
        await update.message.reply_text(part)

# --- Обработчики для психологических тестов ---

async def tests_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обрабатывает команду /tests, показывает список доступных тестов
    """
    user = update.effective_user
    
    # Логируем использование команды
    db.log_command_usage(user.id, "tests")
    
    # Обновляем время последней активности
    db.update_user_activity(user.id)
    
    # Создаем клавиатуру с доступными тестами
    keyboard = [
        [InlineKeyboardButton("MDQ - Тест на биполярное расстройство", callback_data="test_mdq")],
        [InlineKeyboardButton("GAD-7 - Тест на тревожное расстройство", callback_data="test_gad7")],
        [InlineKeyboardButton("PHQ-9 - Тест на депрессию", callback_data="test_phq9")],
        [InlineKeyboardButton("PCL-5 - Тест на ПТСР", callback_data="test_pcl5")],
        [InlineKeyboardButton("❌ Отмена", callback_data="test_cancel")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📊 *Доступные психологические тесты*\n\n"
        "Выберите тест, который хотите пройти:\n\n"
        "⚠️ *Важно:* Результаты тестов не являются диагнозом и не заменяют консультацию специалиста.",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    
    return CHOOSING_TEST

async def test_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обрабатывает выбор теста пользователем
    """
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    test_type = query.data.split('_')[1]
    
    # Если пользователь отменил выбор теста
    if test_type == "cancel":
        await query.edit_message_text("❌ Выбор теста отменен.")
        return ConversationHandler.END
    
    # Сохраняем выбранный тест в контексте
    context.user_data["test_type"] = test_type
    
    # Получаем информацию о тесте
    from data.tests import TESTS_INFO
    test_info = TESTS_INFO.get(test_type, {})
    
    if not test_info:
        await query.edit_message_text("❌ Выбранный тест недоступен.")
        return ConversationHandler.END
    
    # Показываем информацию о тесте и запрашиваем подтверждение
    keyboard = [
        [InlineKeyboardButton("✅ Начать тест", callback_data="confirm_yes")],
        [InlineKeyboardButton("❌ Отмена", callback_data="confirm_no")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"📊 *{test_info['name']}*\n\n"
        f"{test_info['description']}\n\n"
        f"⏱ Примерное время прохождения: {test_info['time']} минут\n"
        f"❓ Количество вопросов: {len(test_info['questions'])}\n\n"
        f"Готовы начать тест?",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    
    return CONFIRMING_TEST

@rate_limit("test", RATE_LIMIT["test"])
async def start_test(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Начинает прохождение выбранного теста
    """
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    
    # Проверяем подтверждение пользователя
    if query.data == "confirm_no":
        await query.edit_message_text("❌ Прохождение теста отменено.")
        return ConversationHandler.END
    
    # Получаем тип теста из контекста
    test_type = context.user_data.get("test_type")
    
    if not test_type:
        await query.edit_message_text("❌ Произошла ошибка. Пожалуйста, попробуйте снова.")
        return ConversationHandler.END
    
    # Получаем информацию о тесте
    from data.tests import TESTS_INFO
    test_info = TESTS_INFO.get(test_type, {})
    
    if not test_info:
        await query.edit_message_text("❌ Выбранный тест недоступен.")
        return ConversationHandler.END
    
    # Инициализируем данные для теста
    context.user_data["test_answers"] = {}
    context.user_data["current_question"] = 0
    
    # Показываем первый вопрос
    await show_test_question(query, context)
    
    return TAKING_TEST

async def show_test_question(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Показывает текущий вопрос теста
    """
    # Получаем тип теста и номер текущего вопроса
    test_type = context.user_data.get("test_type")
    current_question = context.user_data.get("current_question", 0)
    
    # Получаем информацию о тесте
    from data.tests import TESTS_INFO
    test_info = TESTS_INFO.get(test_type, {})
    
    if not test_info or current_question >= len(test_info["questions"]):
        await query.edit_message_text("❌ Произошла ошибка при загрузке вопроса.")
        return
    
    # Получаем текущий вопрос
    question = test_info["questions"][current_question]
    
    # Создаем клавиатуру с вариантами ответов
    keyboard = []
    for option_value, option_text in question["options"].items():
        keyboard.append([InlineKeyboardButton(option_text, callback_data=f"answer_{option_value}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Показываем вопрос и прогресс
    progress = f"{current_question + 1}/{len(test_info['questions'])}"
    
    await query.edit_message_text(
        f"📊 *{test_info['name']}* (Вопрос {progress})\n\n"
        f"{question['text']}",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def process_test_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обрабатывает ответ пользователя на вопрос теста
    """
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    
    # Получаем значение ответа
    answer_value = query.data.split('_')[1]
    
    # Получаем тип теста и номер текущего вопроса
    test_type = context.user_data.get("test_type")
    current_question = context.user_data.get("current_question", 0)
    
    # Получаем информацию о тесте
    from data.tests import TESTS_INFO
    test_info = TESTS_INFO.get(test_type, {})
    
    if not test_info:
        await query.edit_message_text("❌ Произошла ошибка при обработке ответа.")
        return ConversationHandler.END
    
    # Сохраняем ответ
    context.user_data["test_answers"][current_question] = answer_value
    
    # Переходим к следующему вопросу или завершаем тест
    if current_question + 1 < len(test_info["questions"]):
        context.user_data["current_question"] = current_question + 1
        await show_test_question(query, context)
        return TAKING_TEST
    else:
        # Вычисляем результат теста
        await calculate_test_result(query, context)
        return SHOWING_RESULT

async def calculate_test_result(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Вычисляет и показывает результат теста
    """
    user = query.from_user
    
    # Получаем тип теста и ответы
    test_type = context.user_data.get("test_type")
    answers = context.user_data.get("test_answers", {})
    
    # Получаем информацию о тесте
    from data.tests import TESTS_INFO
    test_info = TESTS_INFO.get(test_type, {})
    
    if not test_info:
        await query.edit_message_text("❌ Произошла ошибка при расчете результата.")
        return
    
    # Вычисляем общий балл
    score = 0
    for question_idx, answer_value in answers.items():
        try:
            score += int(answer_value)
        except ValueError:
            pass
    
    # Определяем интерпретацию результата
    interpretation = ""
    for threshold, text in test_info["interpretations"]:
        if score >= threshold:
            interpretation = text
            break
    
    # Сохраняем результат в базе данных
    db.save_test_result(
        user_id=user.id,
        test_type=test_type,
        score=score,
        answers=answers,
        interpretation=interpretation
    )
    
    # Показываем результат
    result_message = (
        f"📊 *Результаты теста {test_info['name']}*\n\n"
        f"Ваш балл: *{score}*\n\n"
        f"*Интерпретация:*\n{interpretation}\n\n"
        f"⚠️ *Важно:* Результаты тестов не являются диагнозом и не заменяют консультацию специалиста."
    )
    
    # Добавляем кнопку для записи на консультацию
    keyboard = [
        [InlineKeyboardButton("🧠 Записаться на консультацию", url=BOT_INFO["website"])]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        result_message,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

# --- Обработчики для техник самопомощи ---

async def techniques_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обрабатывает команду /techniques, показывает категории техник самопомощи
    """
    user = update.effective_user
    
    # Логируем использование команды
    db.log_command_usage(user.id, "techniques")
    
    # Обновляем время последней активности
    db.update_user_activity(user.id)
    
    # Получаем категории техник
    from data.techniques import SELF_HELP_TECHNIQUES
    
    # Создаем клавиатуру с категориями
    keyboard = []
    for category_key, category_data in SELF_HELP_TECHNIQUES.items():
        keyboard.append([InlineKeyboardButton(category_key, callback_data=f"cat_{category_key}")])
    
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cat_cancel")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🛠 *Техники самопомощи*\n\n"
        "Выберите категорию техник, которая вас интересует:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    
    return CHOOSING_TECHNIQUE

async def show_techniques_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Показывает список техник в выбранной категории
    """
    query = update.callback_query
    await query.answer()
    
    category_key = query.data.split('_')[1]
    
    # Если пользователь отменил выбор
    if category_key == "cancel":
        await query.edit_message_text("❌ Выбор техники отменен.")
        return ConversationHandler.END
    
    # Получаем информацию о категории
    from data.techniques import SELF_HELP_TECHNIQUES
    category_data = SELF_HELP_TECHNIQUES.get(category_key)
    
    if not category_data:
        await query.edit_message_text("❌ Выбранная категория недоступна.")
        return ConversationHandler.END
    
    # Сохраняем выбранную категорию в контексте
    context.user_data["selected_category"] = category_key
    
    # Создаем клавиатуру с техниками
    keyboard = []
    for i, technique in enumerate(category_data["techniques"]):
        keyboard.append([InlineKeyboardButton(technique["name"], callback_data=f"tech_{i}")])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад к категориям", callback_data="tech_back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"🛠 *{category_key}*\n\n"
        f"{category_data['description']}\n\n"
        f"Выберите технику для подробного описания:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    
    return SHOWING_TECHNIQUE

async def show_technique_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Показывает подробное описание выбранной техники
    """
    query = update.callback_query
    await query.answer()
    
    # Если пользователь вернулся к категориям
    if query.data == "tech_back":
        return await techniques_command(update, context)
    
    technique_idx = int(query.data.split('_')[1])
    category_key = context.user_data.get("selected_category")
    
    # Получаем информацию о технике
    from data.techniques import SELF_HELP_TECHNIQUES
    category_data = SELF_HELP_TECHNIQUES.get(category_key)
    
    if not category_data or technique_idx >= len(category_data["techniques"]):
        await query.edit_message_text("❌ Выбранная техника недоступна.")
        return ConversationHandler.END
    
    technique = category_data["techniques"][technique_idx]
    
    # Создаем клавиатуру для навигации
    keyboard = [
        [InlineKeyboardButton("⬅️ Назад к списку техник", callback_data="detail_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"🛠 *{technique['name']}*\n\n"
        f"{technique['description']}",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    
    return SHOWING_TECHNIQUE

async def back_to_techniques(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Возвращает к списку техник в категории
    """
    query = update.callback_query
    await query.answer()
    
    category_key = context.user_data.get("selected_category")
    
    # Создаем новый объект Update для передачи в функцию show_techniques_category
    new_query = query
    new_query.data = f"cat_{category_key}"
    
    return await show_techniques_category(update, context)

# --- Обработчики для отслеживания настроения ---

async def mood_tracking_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обрабатывает команду /mood, начинает диалог для отслеживания настроения
    """
    user = update.effective_user
    
    # Логируем использование команды
    db.log_command_usage(user.id, "mood")
    
    # Обновляем время последней активности
    db.update_user_activity(user.id)
    
    # Создаем клавиатуру с вариантами настроения
    keyboard = []
    for mood_key, mood_text in MOOD_EMOJIS.items():
        keyboard.append([InlineKeyboardButton(mood_text, callback_data=f"mood_{mood_key}")])
    
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="mood_cancel")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "😊 *Отслеживание настроения*\n\n"
        "Как вы себя чувствуете сегодня?",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    
    return CHOOSING_MOOD

async def process_mood_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обрабатывает выбор настроения пользователем
    """
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    mood_key = query.data.split('_')[1]
    
    # Если пользователь отменил выбор
    if mood_key == "cancel":
        await query.edit_message_text("❌ Отслеживание настроения отменено.")
        return ConversationHandler.END
    
    # Сохраняем выбранное настроение в контексте
    context.user_data["selected_mood"] = mood_key
    context.user_data["mood_emoji"] = MOOD_EMOJIS[mood_key].split()[0]
    context.user_data["mood_text"] = MOOD_EMOJIS[mood_key].split()[1]
    
    # Спрашиваем, хочет ли пользователь добавить заметку
    keyboard = [
        [InlineKeyboardButton("✅ Да, добавить заметку", callback_data="notes_yes")],
        [InlineKeyboardButton("❌ Нет, сохранить без заметки", callback_data="notes_no")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"Вы выбрали настроение: {MOOD_EMOJIS[mood_key]}\n\n"
        f"Хотите добавить заметку о том, что повлияло на ваше настроение?",
        reply_markup=reply_markup
    )
    
    return ADDING_NOTES

async def ask_for_mood_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Запрашивает заметки о настроении
    """
    query = update.callback_query
    await query.answer()
    
    choice = query.data.split('_')[1]
    
    # Если пользователь не хочет добавлять заметку
    if choice == "no":
        return await save_mood_without_notes(update, context)
    
    await query.edit_message_text(
        "📝 Пожалуйста, напишите заметку о том, что повлияло на ваше настроение.\n\n"
        "Для отмены отправьте /cancel."
    )
    
    return ADDING_NOTES

async def save_mood_with_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Сохраняет настроение с заметками
    """
    user = update.effective_user
    notes = update.message.text
    
    mood_emoji = context.user_data.get("mood_emoji")
    mood_text = context.user_data.get("mood_text")
    
    if not mood_emoji or not mood_text:
        await update.message.reply_text(
            "❌ Произошла ошибка при сохранении настроения. Пожалуйста, попробуйте снова."
        )
        return ConversationHandler.END
    
    # Сохраняем настроение в базе данных
    success = db.save_mood(
        user_id=user.id,
        mood_emoji=mood_emoji,
        mood_text=mood_text,
        notes=notes
    )
    
    if success:
        await update.message.reply_text(
            f"✅ Ваше настроение {mood_emoji} {mood_text} успешно сохранено с заметкой.\n\n"
            f"Спасибо за отслеживание вашего настроения! Это помогает лучше понимать ваше эмоциональное состояние."
        )
    else:
        await update.message.reply_text(
            "❌ Произошла ошибка при сохранении настроения. Пожалуйста, попробуйте позже."
        )
    
    return ConversationHandler.END

async def save_mood_without_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Сохраняет настроение без заметок
    """
    query = update.callback_query
    user = query.from_user
    
    mood_emoji = context.user_data.get("mood_emoji")
    mood_text = context.user_data.get("mood_text")
    
    if not mood_emoji or not mood_text:
        await query.edit_message_text(
            "❌ Произошла ошибка при сохранении настроения. Пожалуйста, попробуйте снова."
        )
        return ConversationHandler.END
    
    # Сохраняем настроение в базе данных
    success = db.save_mood(
        user_id=user.id,
        mood_emoji=mood_emoji,
        mood_text=mood_text
    )
    
    if success:
        await query.edit_message_text(
            f"✅ Ваше настроение {mood_emoji} {mood_text} успешно сохранено.\n\n"
            f"Спасибо за отслеживание вашего настроения! Это помогает лучше понимать ваше эмоциональное состояние."
        )
    else:
        await query.edit_message_text(
            "❌ Произошла ошибка при сохранении настроения. Пожалуйста, попробуйте позже."
        )
    
    return ConversationHandler.END

async def cancel_mood_tracking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Отменяет процесс отслеживания настроения
    """
    await update.message.reply_text(
        "❌ Отслеживание настроения отменено."
    )
    
    return ConversationHandler.END

async def show_mood_history_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Показывает историю настроения пользователя
    """
    user = update.effective_user
    
    # Логируем использование команды
    db.log_command_usage(user.id, "mood_history")
    
    # Обновляем время последней активности
    db.update_user_activity(user.id)
    
    # Получаем историю настроения
    mood_history = db.get_user_mood_history(user.id)
    
    if not mood_history:
        await update.message.reply_text(
            "У вас пока нет записей о настроении. Используйте команду /mood, чтобы начать отслеживание."
        )
        return
    
    # Формируем сообщение с историей настроения
    message = "📊 *История вашего настроения*\n\n"
    
    for mood in mood_history[:10]:  # Показываем последние 10 записей
        date_str = format_datetime(mood["date_recorded"])
        notes = f"\n   _Заметка: {mood['notes']}_" if mood["notes"] else ""
        
        message += f"{mood['mood_emoji']} {mood['mood_text']} - {date_str}{notes}\n\n"
    
    # Добавляем информацию о количестве записей
    if len(mood_history) > 10:
        message += f"_Показаны последние 10 из {len(mood_history)} записей._"
    
    await update.message.reply_text(message, parse_mode="Markdown")

# --- Обработчики для настроек ---

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обрабатывает команду /settings, показывает настройки пользователя
    """
    user = update.effective_user
    
    # Логируем использование команды
    db.log_command_usage(user.id, "settings")
    
    # Обновляем время последней активности
    db.update_user_activity(user.id)
    
    # Получаем текущие настройки пользователя
    settings = db.get_user_settings(user.id)
    
    # Создаем клавиатуру с настройками
    keyboard = [
        [InlineKeyboardButton(
            f"🔔 Уведомления: {'Включены' if settings['notifications_enabled'] else 'Выключены'}", 
            callback_data="settings_notifications"
        )],
        [InlineKeyboardButton(
            f"⏰ Время совета дня: {settings['daily_tip_time']}", 
            callback_data="settings_time"
        )],
        [InlineKeyboardButton("❌ Закрыть", callback_data="settings_close")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "⚙️ *Настройки*\n\n"
        "Здесь вы можете настроить параметры бота под свои предпочтения.\n"
        "Выберите настройку, которую хотите изменить:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    
    return CHANGING_SETTINGS

async def process_settings_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обрабатывает выбор настройки пользователем
    """
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    setting_key = query.data.split('_')[1]
    
    # Если пользователь закрыл настройки
    if setting_key == "close":
        await query.edit_message_text("✅ Настройки сохранены.")
        return ConversationHandler.END
    
    # Получаем текущие настройки пользователя
    settings = db.get_user_settings(user.id)
    
    # Обрабатываем выбор настройки
    if setting_key == "notifications":
        # Инвертируем значение настройки уведомлений
        new_value = not settings["notifications_enabled"]
        
        # Обновляем настройку в базе данных
        db.update_user_settings(user.id, {"notifications_enabled": new_value})
        
        # Обновляем сообщение с настройками
        return await settings_command(update, context)
    
    elif setting_key == "time":
        # Запрашиваем новое время для совета дня
        await query.edit_message_text(
            "⏰ Пожалуйста, укажите время для получения ежедневного совета в формате ЧЧ:ММ (например, 09:00).\n\n"
            "Для отмены отправьте /cancel."
        )
        
        # Сохраняем текущее состояние для обработки ответа
        context.user_data["changing_setting"] = "daily_tip_time"
        
        return CHANGING_SETTINGS
    
    # По умолчанию возвращаемся к настройкам
    return await settings_command(update, context)

async def save_setting_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Сохраняет новое значение настройки
    """
    user = update.effective_user
    value = update.message.text
    
    setting_key = context.user_data.get("changing_setting")
    
    if not setting_key:
        await update.message.reply_text(
            "❌ Произошла ошибка при сохранении настройки. Пожалуйста, попробуйте снова."
        )
        return ConversationHandler.END
    
    # Проверяем и сохраняем значение настройки
    if setting_key == "daily_tip_time":
        # Проверяем формат времени
        import re
        if not re.match(r'^([01]\d|2[0-3]):([0-5]\d)$', value):
            await update.message.reply_text(
                "❌ Неверный формат времени. Пожалуйста, используйте формат ЧЧ:ММ (например, 09:00)."
            )
            return CHANGING_SETTINGS
        
        # Обновляем настройку в базе данных
        db.update_user_settings(user.id, {setting_key: value})
        
        await update.message.reply_text(
            f"✅ Время для получения ежедневного совета установлено на {value}."
        )
    
    # Очищаем данные контекста
    if "changing_setting" in context.user_data:
        del context.user_data["changing_setting"]
    
    return ConversationHandler.END

async def cancel_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Отменяет процесс изменения настроек
    """
    await update.message.reply_text(
        "❌ Изменение настроек отменено."
    )
    
    # Очищаем данные контекста
    if "changing_setting" in context.user_data:
        del context.user_data["changing_setting"]
    
    return ConversationHandler.END

# --- Обработчик текстовых сообщений ---

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает текстовые сообщения, не соответствующие командам
    """
    user = update.effective_user
    text = update.message.text
    
    # Обновляем время последней активности
    db.update_user_activity(user.id)
    
    # Обрабатываем сообщения в зависимости от текста
    if text == "🧠 Совет дня":
        await daily_tip_command(update, context)
    elif text == "📊 Пройти тест":
        await tests_command(update, context)
    elif text == "🛠 Техники самопомощи":
        await techniques_command(update, context)
    elif text == "😊 Отслеживание настроения":
        await mood_tracking_command(update, context)
    elif text == "❓ Задать вопрос психологу":
        await ask_question_command(update, context)
    elif text == "⚙️ Настройки":
        await settings_command(update, context)
    else:
        # Если сообщение не соответствует ни одной кнопке
        await update.message.reply_text(
            "Я не понимаю эту команду. Пожалуйста, используйте кнопки меню или команды бота."
        )

# --- Обработчик ошибок ---

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает ошибки, возникающие при работе бота
    """
    logger.error(f"Произошла ошибка: {context.error}")
    
    # Отправляем сообщение пользователю
    if update and update.effective_chat:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже."
        )
    
    # Отправляем уведомление администратору
    try:
        error_message = (
            f"⚠️ *Ошибка в боте*\n\n"
            f"Пользователь: {update.effective_user.id if update and update.effective_user else 'Неизвестно'}\n"
            f"Сообщение: {update.message.text if update and update.message else 'Неизвестно'}\n\n"
            f"Ошибка: {context.error}"
        )
        
        await context.bot.send_message(
            chat_id=ADMIN_USER_ID,
            text=error_message,
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления администратору: {e}")
