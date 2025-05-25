#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Обновленные обработчики команд для телеграм-бота с интеграцией статистики
"""

import logging
import traceback
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from config import ADMIN_USER_ID, MOOD_TRACKING_SETTINGS
from database import Database
from stats.stats_collector import StatsCollector
from utils import sanitize_input, format_datetime, format_mood_history, format_test_results, format_questions

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация базы данных
db = Database()

# Инициализация коллектора статистики
stats_collector = StatsCollector(db)

# Константы для состояний разговора
SELECTING_TEST, ANSWERING_TEST, SHOWING_RESULT = range(3)
SELECTING_MOOD, ENTERING_NOTES = range(2)
SHOWING_CATEGORIES, SHOWING_TECHNIQUE = range(2)
ENTERING_QUESTION = range(1)
ADMIN_REPLYING = range(1)

# --- Основные команды ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает команду /start
    """
    user = update.effective_user
    user_id = user.id
    username = user.username
    first_name = user.first_name
    last_name = user.last_name
    
    # Логируем использование команды
    stats_collector.log_command_usage(user_id, "/start")
    
    # Регистрируем пользователя в базе данных
    db.register_user(user_id, username, first_name, last_name)
    
    await update.message.reply_text(
        f"👋 Здравствуйте, {first_name}!\n\n"
        "Я бот-помощник психотерапевта, который поможет вам отслеживать своё настроение, "
        "пройти психологические тесты и получить рекомендации по самопомощи.\n\n"
        "Используйте /help, чтобы увидеть список доступных команд."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает команду /help
    """
    user_id = update.effective_user.id
    
    # Логируем использование команды
    stats_collector.log_command_usage(user_id, "/help")
    
    help_text = (
        "🔍 *Список доступных команд:*\n\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать список команд\n"
        "/about - Информация о боте\n"
        "/test - Пройти психологический тест\n"
        "/mood - Отслеживание настроения\n"
        "/techniques - Техники самопомощи\n"
        "/question - Задать анонимный вопрос психотерапевту\n"
        "/cancel - Отменить текущую операцию\n\n"
    )
    
    # Добавляем команды администратора, если пользователь - администратор
    if user_id == ADMIN_USER_ID:
        help_text += (
            "👑 *Команды администратора:*\n\n"
            "/questions - Просмотр и ответы на вопросы\n"
            "/stats - Общая статистика бота\n"
            "/active_users [дней] - Активные пользователи\n"
            "/commands_stats [дней] - Статистика использования команд\n\n"
        )
    
    help_text += "Для отмены любой операции используйте команду /cancel."
    
    await update.message.reply_text(
        help_text,
        parse_mode="Markdown"
    )

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает команду /about
    """
    user_id = update.effective_user.id
    
    # Логируем использование команды
    stats_collector.log_command_usage(user_id, "/about")
    
    from config import BOT_INFO
    
    about_text = (
        f"ℹ️ *{BOT_INFO['name']}*\n\n"
        f"Версия: {BOT_INFO['version']}\n"
        f"Описание: {BOT_INFO['description']}\n\n"
        f"Автор: {BOT_INFO['author']}\n"
        f"Сайт: {BOT_INFO['website']}\n\n"
        "Этот бот предназначен для психологической поддержки и самопомощи. "
        "Он поможет вам отслеживать настроение, пройти психологические тесты "
        "и получить рекомендации по самопомощи."
    )
    
    await update.message.reply_text(
        about_text,
        parse_mode="Markdown"
    )

# --- Обработчики для тестов ---
async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обрабатывает команду /test
    """
    user_id = update.effective_user.id
    
    # Логируем использование команды
    stats_collector.log_command_usage(user_id, "/test")
    
    # Получаем список доступных тестов
    tests = [
        {"id": "anxiety", "name": "Тест на тревожность (GAD-7)"},
        {"id": "depression", "name": "Тест на депрессию (PHQ-9)"},
        {"id": "stress", "name": "Тест на стресс (PSS-10)"},
        {"id": "ptsd", "name": "Тест на ПТСР (PCL-5)"}
    ]
    
    # Создаем клавиатуру для выбора теста
    keyboard = []
    for test in tests:
        keyboard.append([InlineKeyboardButton(test["name"], callback_data=f"test_{test['id']}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📝 *Психологические тесты*\n\n"
        "Выберите тест, который хотите пройти:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    return SELECTING_TEST

async def select_test(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обрабатывает выбор теста
    """
    query = update.callback_query
    await query.answer()
    
    # Получаем ID теста из callback_data
    test_id = query.data.replace("test_", "")
    
    # Сохраняем ID теста в данных пользователя
    context.user_data["selected_test"] = test_id
    context.user_data["current_question"] = 0
    context.user_data["answers"] = []
    
    # Получаем вопросы для выбранного теста
    from data.tests import TESTS
    
    if test_id not in TESTS:
        await query.edit_message_text(
            "❌ Выбранный тест не найден. Пожалуйста, попробуйте снова."
        )
        return ConversationHandler.END
    
    test_data = TESTS[test_id]
    questions = test_data["questions"]
    
    # Показываем первый вопрос
    question_index = context.user_data["current_question"]
    question = questions[question_index]
    
    # Создаем клавиатуру для ответов
    keyboard = []
    for i, option in enumerate(question["options"]):
        keyboard.append([InlineKeyboardButton(option, callback_data=f"answer_{i}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"📝 *{test_data['name']}*\n\n"
        f"Вопрос {question_index + 1} из {len(questions)}:\n"
        f"{question['text']}",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    return ANSWERING_TEST

async def process_test_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обрабатывает ответ на вопрос теста
    """
    query = update.callback_query
    await query.answer()
    
    # Получаем индекс ответа из callback_data
    answer_index = int(query.data.replace("answer_", ""))
    
    # Сохраняем ответ
    context.user_data["answers"].append(answer_index)
    
    # Получаем данные о текущем тесте
    test_id = context.user_data["selected_test"]
    from data.tests import TESTS
    test_data = TESTS[test_id]
    questions = test_data["questions"]
    
    # Увеличиваем индекс текущего вопроса
    context.user_data["current_question"] += 1
    question_index = context.user_data["current_question"]
    
    # Проверяем, есть ли еще вопросы
    if question_index < len(questions):
        # Показываем следующий вопрос
        question = questions[question_index]
        
        # Создаем клавиатуру для ответов
        keyboard = []
        for i, option in enumerate(question["options"]):
            keyboard.append([InlineKeyboardButton(option, callback_data=f"answer_{i}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"📝 *{test_data['name']}*\n\n"
            f"Вопрос {question_index + 1} из {len(questions)}:\n"
            f"{question['text']}",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
        return ANSWERING_TEST
    else:
        # Все вопросы отвечены, показываем результат
        # Вычисляем результат теста
        score = sum(context.user_data["answers"])
        
        # Определяем интерпретацию результата
        interpretation = ""
        for threshold in test_data["thresholds"]:
            if score >= threshold["min"] and score <= threshold["max"]:
                interpretation = threshold["interpretation"]
                break
        
        # Сохраняем результат в базе данных
        user_id = update.effective_user.id
        db.save_test_result(
            user_id,
            test_id,
            score,
            str(context.user_data["answers"]),
            interpretation
        )
        
        # Создаем клавиатуру для просмотра результата
        keyboard = [[InlineKeyboardButton("Подробнее о результате", callback_data=f"result_{test_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✅ *Тест завершен*\n\n"
            f"Ваш результат: {score} баллов\n\n"
            f"Интерпретация: {interpretation}\n\n"
            f"Нажмите кнопку ниже, чтобы узнать больше о вашем результате.",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
        return SHOWING_RESULT

async def show_test_result(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Показывает подробную информацию о результате теста
    """
    query = update.callback_query
    await query.answer()
    
    # Получаем ID теста из callback_data
    test_id = query.data.replace("result_", "")
    
    # Получаем данные о тесте
    from data.tests import TESTS
    test_data = TESTS[test_id]
    
    # Получаем результат теста
    score = sum(context.user_data["answers"])
    
    # Определяем интерпретацию результата
    interpretation = ""
    recommendations = ""
    for threshold in test_data["thresholds"]:
        if score >= threshold["min"] and score <= threshold["max"]:
            interpretation = threshold["interpretation"]
            recommendations = threshold.get("recommendations", "")
            break
    
    result_text = (
        f"📊 *Результаты теста: {test_data['name']}*\n\n"
        f"Ваш результат: {score} баллов\n\n"
        f"Интерпретация: {interpretation}\n\n"
    )
    
    if recommendations:
        result_text += f"Рекомендации:\n{recommendations}\n\n"
    
    result_text += (
        "⚠️ *Важно*: Результаты этого теста не являются диагнозом. "
        "Для получения профессиональной помощи обратитесь к квалифицированному специалисту."
    )
    
    await query.edit_message_text(
        result_text,
        parse_mode="Markdown"
    )
    
    return ConversationHandler.END

# --- Обработчики для отслеживания настроения ---
async def mood_tracking_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обрабатывает команду /mood
    """
    user_id = update.effective_user.id
    
    # Логируем использование команды
    stats_collector.log_command_usage(user_id, "/mood")
    
    # Создаем клавиатуру для выбора настроения
    keyboard = []
    row = []
    
    for i, (mood_id, emoji) in enumerate(MOOD_TRACKING_SETTINGS["mood_emojis"].items()):
        row.append(InlineKeyboardButton(emoji, callback_data=f"mood_{mood_id}"))
        
        # По 3 кнопки в ряду
        if (i + 1) % 3 == 0 or i == len(MOOD_TRACKING_SETTINGS["mood_emojis"]) - 1:
            keyboard.append(row)
            row = []
    
    # Добавляем кнопку для просмотра истории
    keyboard.append([InlineKeyboardButton("📊 История настроения", callback_data="history")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "😊 *Отслеживание настроения*\n\n"
        "Как вы себя чувствуете сегодня? Выберите эмодзи, соответствующий вашему настроению:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    return SELECTING_MOOD

async def select_mood(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обрабатывает выбор настроения
    """
    query = update.callback_query
    await query.answer()
    
    # Получаем ID настроения из callback_data
    mood_id = query.data.replace("mood_", "")
    
    # Сохраняем выбранное настроение в данных пользователя
    context.user_data["selected_mood"] = mood_id
    context.user_data["mood_emoji"] = MOOD_TRACKING_SETTINGS["mood_emojis"][mood_id]
    context.user_data["mood_text"] = MOOD_TRACKING_SETTINGS["mood_texts"][mood_id]
    
    # Создаем клавиатуру для пропуска заметок
    keyboard = [[InlineKeyboardButton("Пропустить", callback_data="skip")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"📝 Вы выбрали настроение: {context.user_data['mood_emoji']} {context.user_data['mood_text']}\n\n"
        f"Хотите добавить заметку о том, что повлияло на ваше настроение? "
        f"Напишите её или нажмите 'Пропустить'.",
        reply_markup=reply_markup
    )
    
    return ENTERING_NOTES

async def save_mood_with_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Сохраняет настроение с заметками
    """
    notes = sanitize_input(update.message.text)  # Очистка пользовательского ввода
    
    # Сохраняем заметки в данных пользователя
    context.user_data["mood_notes"] = notes
    
    # Сохраняем настроение в базе данных
    user_id = update.effective_user.id
    mood_emoji = context.user_data["mood_emoji"]
    mood_text = context.user_data["mood_text"]
    
    db.save_mood(user_id, mood_emoji, mood_text, notes)
    
    await update.message.reply_text(
        f"✅ Ваше настроение ({mood_emoji} {mood_text}) и заметки сохранены!\n\n"
        f"Продолжайте отслеживать своё настроение, чтобы лучше понимать свои эмоциональные паттерны."
    )
    
    return ConversationHandler.END

async def save_mood_without_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Сохраняет настроение без заметок
    """
    query = update.callback_query
    await query.answer()
    
    # Сохраняем настроение в базе данных
    user_id = update.effective_user.id
    mood_emoji = context.user_data["mood_emoji"]
    mood_text = context.user_data["mood_text"]
    
    db.save_mood(user_id, mood_emoji, mood_text, "")
    
    await query.edit_message_text(
        f"✅ Ваше настроение ({mood_emoji} {mood_text}) сохранено!\n\n"
        f"Продолжайте отслеживать своё настроение, чтобы лучше понимать свои эмоциональные паттерны."
    )
    
    return ConversationHandler.END

async def show_mood_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Показывает историю настроения
    """
    query = update.callback_query
    await query.answer()
    
    # Получаем историю настроения из базы данных
    user_id = update.effective_user.id
    mood_history = db.get_mood_history(user_id)
    
    # Форматируем историю настроения
    history_text = format_mood_history(mood_history)
    
    await query.edit_message_text(
        history_text,
        parse_mode="Markdown"
    )
    
    return ConversationHandler.END

# --- Обработчики для техник самопомощи ---
async def techniques_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обрабатывает команду /techniques
    """
    user_id = update.effective_user.id
    
    # Логируем использование команды
    stats_collector.log_command_usage(user_id, "/techniques")
    
    # Получаем категории техник
    from data.techniques import TECHNIQUE_CATEGORIES
    
    # Создаем клавиатуру для выбора категории
    keyboard = []
    for category_id, category in TECHNIQUE_CATEGORIES.items():
        keyboard.append([InlineKeyboardButton(category["name"], callback_data=f"cat_{category_id}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🧘 *Техники самопомощи*\n\n"
        "Выберите категорию техник, которая вас интересует:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    return SHOWING_CATEGORIES

async def show_techniques_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Показывает техники выбранной категории
    """
    query = update.callback_query
    await query.answer()
    
    # Получаем ID категории из callback_data
    category_id = query.data.replace("cat_", "")
    
    # Сохраняем ID категории в данных пользователя
    context.user_data["selected_category"] = category_id
    
    # Получаем данные о категории и техниках
    from data.techniques import TECHNIQUE_CATEGORIES, TECHNIQUES
    
    category = TECHNIQUE_CATEGORIES[category_id]
    techniques = [tech for tech in TECHNIQUES if tech["category_id"] == category_id]
    
    # Создаем клавиатуру для выбора техники
    keyboard = []
    for technique in techniques:
        keyboard.append([InlineKeyboardButton(technique["name"], callback_data=f"tech_{technique['id']}")])
    
    # Добавляем кнопку "Назад"
    keyboard.append([InlineKeyboardButton("« Назад к категориям", callback_data="tech_back")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"🧘 *{category['name']}*\n\n"
        f"{category['description']}\n\n"
        f"Выберите технику, чтобы узнать подробности:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    return SHOWING_TECHNIQUE

async def show_technique_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Показывает подробную информацию о технике
    """
    query = update.callback_query
    await query.answer()
    
    # Получаем ID техники из callback_data
    technique_id = int(query.data.replace("tech_", ""))
    
    # Получаем данные о технике
    from data.techniques import TECHNIQUES
    
    technique = next((t for t in TECHNIQUES if t["id"] == technique_id), None)
    
    if not technique:
        await query.edit_message_text(
            "❌ Техника не найдена. Пожалуйста, попробуйте снова."
        )
        return SHOWING_CATEGORIES
    
    # Создаем клавиатуру для возврата к категории
    keyboard = [[InlineKeyboardButton("« Назад к списку техник", callback_data=f"cat_{technique['category_id']}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Формируем текст с описанием техники
    technique_text = (
        f"🧘 *{technique['name']}*\n\n"
        f"{technique['description']}\n\n"
        f"*Как выполнять:*\n{technique['instructions']}\n\n"
    )
    
    if technique.get("benefits"):
        technique_text += f"*Польза:*\n{technique['benefits']}\n\n"
    
    if technique.get("tips"):
        technique_text += f"*Советы:*\n{technique['tips']}"
    
    await query.edit_message_text(
        technique_text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    return SHOWING_TECHNIQUE

async def back_to_categories(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Возвращает к списку категорий
    """
    query = update.callback_query
    await query.answer()
    
    # Получаем категории техник
    from data.techniques import TECHNIQUE_CATEGORIES
    
    # Создаем клавиатуру для выбора категории
    keyboard = []
    for category_id, category in TECHNIQUE_CATEGORIES.items():
        keyboard.append([InlineKeyboardButton(category["name"], callback_data=f"cat_{category_id}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🧘 *Техники самопомощи*\n\n"
        "Выберите категорию техник, которая вас интересует:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    return SHOWING_CATEGORIES

# --- Обработчики для анонимных вопросов ---
async def question_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обрабатывает команду /question
    """
    user_id = update.effective_user.id
    
    # Логируем использование команды
    stats_collector.log_command_usage(user_id, "/question")
    
    await update.message.reply_text(
        "❓ *Анонимный вопрос психотерапевту*\n\n"
        "Напишите ваш вопрос в следующем сообщении. "
        "Ваш вопрос будет передан психотерапевту, и вы получите ответ, как только он будет готов.\n\n"
        "Для отмены используйте команду /cancel.",
        parse_mode="Markdown"
    )
    
    return ENTERING_QUESTION

async def process_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обрабатывает вопрос пользователя
    """
    user_id = update.effective_user.id
    question_text = sanitize_input(update.message.text)  # Очистка пользовательского ввода
    
    # Проверяем длину вопроса
    from config import ANONYMOUS_QUESTIONS_SETTINGS
    
    if len(question_text) > ANONYMOUS_QUESTIONS_SETTINGS["max_question_length"]:
        await update.message.reply_text(
            f"❌ Ваш вопрос слишком длинный. Максимальная длина - "
            f"{ANONYMOUS_QUESTIONS_SETTINGS['max_question_length']} символов.\n\n"
            f"Пожалуйста, сократите вопрос и отправьте снова."
        )
        return ENTERING_QUESTION
    
    # Проверяем количество вопросов за день
    questions_today = db.get_user_questions_count_today(user_id)
    
    if questions_today >= ANONYMOUS_QUESTIONS_SETTINGS["max_questions_per_day"]:
        await update.message.reply_text(
            f"❌ Вы уже задали максимальное количество вопросов за сегодня "
            f"({ANONYMOUS_QUESTIONS_SETTINGS['max_questions_per_day']}).\n\n"
            f"Пожалуйста, попробуйте завтра."
        )
        return ConversationHandler.END
    
    # Сохраняем вопрос в базе данных
    question_id = db.save_question(user_id, question_text)
    
    if not question_id:
        await update.message.reply_text(
            "❌ Произошла ошибка при сохранении вопроса. Пожалуйста, попробуйте позже."
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        f"✅ Ваш вопрос #{question_id} успешно отправлен!\n\n"
        f"Вы получите уведомление, когда психотерапевт ответит на ваш вопрос."
    )
    
    # Отправляем уведомление администратору
    try:
        await context.bot.send_message(
            chat_id=ADMIN_USER_ID,
            text=f"❗️ *Новый анонимный вопрос*\n\n"
                 f"Номер вопроса: #{question_id}\n"
                 f"От пользователя: {user_id}\n"
                 f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                 f"Вопрос: {question_text}\n\n"
                 f"Используйте команду /questions для ответа.",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления администратору: {e}")
    
    return ConversationHandler.END

# --- Обработчики для ответов на вопросы (только для администратора) ---
async def show_questions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Показывает список неотвеченных вопросов
    """
    user_id = update.effective_user.id
    
    # Проверяем, является ли пользователь администратором
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text(
            "⛔ У вас нет доступа к этой команде."
        )
        return ConversationHandler.END
    
    # Логируем использование команды
    stats_collector.log_command_usage(user_id, "/questions")
    
    # Получаем список неотвеченных вопросов
    unanswered_questions = db.get_unanswered_questions()
    
    if not unanswered_questions:
        await update.message.reply_text(
            "✅ Нет неотвеченных вопросов."
        )
        return ConversationHandler.END
    
    # Создаем клавиатуру для выбора вопроса
    keyboard = []
    for question in unanswered_questions:
        keyboard.append([InlineKeyboardButton(
            f"#{question['question_id']} - {question['question_text'][:30]}...",
            callback_data=f"q_{question['question_id']}"
        )])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📝 *Список неотвеченных вопросов*\n\n"
        "Выберите вопрос, на который хотите ответить:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    return ADMIN_REPLYING

async def answer_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обрабатывает выбор вопроса администратором
    """
    query = update.callback_query
    await query.answer()
    
    # Получаем ID вопроса из callback_data
    question_id = int(query.data.replace("q_", ""))
    
    # Сохраняем ID вопроса в данных пользователя
    context.user_data["selected_question_id"] = question_id
    
    # Получаем информацию о вопросе
    question_data = db.get_question_by_id(question_id)
    
    if not question_data:
        await query.edit_message_text(
            "❌ Вопрос не найден или уже был отвечен."
        )
        return ConversationHandler.END
    
    await query.edit_message_text(
        f"📝 *Вопрос #{question_id}*\n\n"
        f"От пользователя: {question_data['user_id']}\n"
        f"Дата: {format_datetime(question_data['date_asked'])}\n\n"
        f"Вопрос: {question_data['question_text']}\n\n"
        f"Напишите ваш ответ или отправьте /cancel для отмены.",
        parse_mode="Markdown"
    )
    
    return ADMIN_REPLYING

async def save_question_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Сохраняет ответ на вопрос
    """
    question_id = context.user_data.get("selected_question_id")
    answer_text = sanitize_input(update.message.text)  # Очистка пользовательского ввода
    
    if not question_id:
        await update.message.reply_text(
            "❌ Произошла ошибка при сохранении ответа."
        )
        return ConversationHandler.END
    
    # Получаем информацию о вопросе
    question_data = db.get_question_by_id(question_id)
    
    if not question_data:
        await update.message.reply_text(
            "❌ Вопрос не найден или уже был отвечен."
        )
        return ConversationHandler.END
    
    # Сохраняем ответ в базе данных
    if not db.save_question_answer(question_id, answer_text):
        await update.message.reply_text(
            "❌ Произошла ошибка при сохранении ответа."
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        f"✅ Ответ на вопрос #{question_id} успешно сохранен!"
    )
    
    # Отправляем уведомление пользователю
    try:
        await context.bot.send_message(
            chat_id=question_data["user_id"],
            text=f"✅ *Получен ответ на ваш вопрос*\n\n"
                 f"Номер вопроса: #{question_id}\n"
                 f"Ваш вопрос: {question_data['question_text']}\n\n"
                 f"Ответ: {answer_text}",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления пользователю: {e}")
    
    return ConversationHandler.END

# --- Обработчик для отмены операций ---
async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обрабатывает команду /cancel
    """
    user_id = update.effective_user.id
    
    # Логируем использование команды
    stats_collector.log_command_usage(user_id, "/cancel")
    
    # Очищаем данные пользователя
    context.user_data.clear()
    
    await update.message.reply_text(
        "❌ Операция отменена."
    )
    
    return ConversationHandler.END

# --- Обработчик для неизвестных команд ---
async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает неизвестные команды
    """
    user_id = update.effective_user.id
    
    # Логируем использование неизвестной команды
    stats_collector.log_command_usage(user_id, update.message.text)
    
    await update.message.reply_text(
        "❓ Неизвестная команда. Используйте /help, чтобы увидеть список доступных команд."
    )

# --- Обработчик ошибок ---
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает ошибки, возникающие при работе бота
    """
    # Получаем информацию об ошибке
    error_traceback = traceback.format_exception(None, context.error, context.error.__traceback__)
    error_text = ''.join(error_traceback)
    
    # Логируем полную информацию об ошибке
    logger.error(f"Произошла ошибка: {context.error}\n{error_text}")
    
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
            f"Ошибка: {context.error}\n\n"
            f"Трассировка: ```{error_text[:1000]}```"  # Ограничиваем длину трассировки
        )
        
        await context.bot.send_message(
            chat_id=ADMIN_USER_ID,
            text=error_message,
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления администратору: {e}")
