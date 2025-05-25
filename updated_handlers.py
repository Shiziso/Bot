#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль с обновленными обработчиками для интеграции новых тестов
"""

import logging
import random
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, ConversationHandler

from database import Database
from config import ADMIN_USER_ID, MOOD_EMOJIS, BOT_INFO, NOTIFICATION_SETTINGS, RATE_LIMIT
from utils import rate_limit, format_datetime, get_user_mention, split_text, sanitize_input
from data.tests import TESTS, TEST_CATEGORIES
from data.new_tests import NEW_TESTS, NEW_TEST_CATEGORIES

# Настройка логирования
logger = logging.getLogger(__name__)

# Инициализация базы данных
db = Database()

# Объединяем все тесты и категории
ALL_TESTS = {**TESTS, **NEW_TESTS}
ALL_TEST_CATEGORIES = {**TEST_CATEGORIES, **NEW_TEST_CATEGORIES}

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
    
    # Создаем клавиатуру с кнопкой для блога
    keyboard = [
        [InlineKeyboardButton("📚 Блог доктора Лысенко", url="https://t.me/psihotips")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем приветственное сообщение
    await update.message.reply_text(
        f"👋 Здравствуйте, {user.first_name}!\n\n"
        f"Я {BOT_INFO['name']} - бот для психологической поддержки, созданный врачом-психотерапевтом Юрием Лысенко.\n\n"
        f"Что я могу предложить вам:\n"
        f"• Эффективные техники самопомощи при стрессе, тревоге и других состояниях\n"
        f"• Удобное отслеживание вашего эмоционального состояния\n"
        f"• Профессиональные психологические тесты с интерпретацией\n"
        f"• Возможность задать вопрос лично врачу-психотерапевту\n\n"
        f"Используйте команду /help, чтобы узнать больше о возможностях бота. Помните, что бот не заменяет консультацию специалиста.",
        reply_markup=reply_markup
    )
    
    logger.info(f"Пользователь {user.id} ({user.username}) начал использовать бота")
    
    return ConversationHandler.END

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает команду /help, показывает список доступных команд
    """
    # Создаем клавиатуру с кнопками для блога и записи на прием
    keyboard = [
        [InlineKeyboardButton("📚 Блог доктора Лысенко", url="https://t.me/psihotips")],
        [InlineKeyboardButton("🗓 Записаться на консультацию", url="https://t.me/psihotips/22")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🔍 *Доступные команды:*\n\n"
        "/start - Начать использование бота\n"
        "/help - Показать список команд\n"
        "/about - Информация о боте и враче\n"
        "/test - Пройти профессиональный психологический тест\n"
        "/mood - Отслеживание эмоционального состояния\n"
        "/techniques - Техники самопомощи от врача-психотерапевта\n"
        "/question - Задать вопрос лично врачу\n"
        "/cancel - Отменить текущее действие\n\n"
        "Если у вас возникли вопросы или вы чувствуете, что вам нужна профессиональная поддержка, не стесняйтесь обращаться к доктору Лысенко через команду /question или записаться на личную консультацию.",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает команду /about, показывает информацию о боте и враче
    """
    # Создаем клавиатуру с кнопками для блога и записи на прием
    keyboard = [
        [InlineKeyboardButton("📚 Блог доктора Лысенко", url="https://t.me/psihotips")],
        [InlineKeyboardButton("🗓 Записаться на консультацию", url="https://t.me/psihotips/22")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"ℹ️ *О боте и авторе*\n\n"
        f"*Название:* {BOT_INFO['name']}\n"
        f"*Версия:* {BOT_INFO['version']}\n"
        f"*Описание:* {BOT_INFO['description']}\n\n"
        f"*Автор:* {BOT_INFO['author']}\n"
        f"*Блог:* {BOT_INFO['website']}\n\n"
        f"Я — Юрий Александрович Лысенко, психотерапевт, врач-психиатр высшей категории с опытом работы более 10 лет. "
        f"Моя цель — помогать вам обрести внутреннюю гармонию и уверенность в завтрашнем дне.\n\n"
        f"Этот бот создан для оказания психологической поддержки и самопомощи, но он не заменяет профессиональную консультацию. "
        f"Если вы испытываете серьезные психологические трудности, рекомендую записаться на личный прием.",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обрабатывает команду /cancel, отменяет текущее действие
    """
    await update.message.reply_text(
        "❌ Действие отменено. Используйте команды /help, чтобы узнать о возможностях бота, или обратитесь к доктору Лысенко через команду /question."
    )
    
    # Очищаем данные пользователя
    context.user_data.clear()
    
    return ConversationHandler.END

# --- Обработчики для психологических тестов ---

@rate_limit("test", RATE_LIMIT["test"])
async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обрабатывает команду /test, показывает доступные категории тестов
    """
    # Создаем клавиатуру с категориями тестов
    keyboard = []
    for category_key, category_data in ALL_TEST_CATEGORIES.items():
        keyboard.append([InlineKeyboardButton(category_data["name"], callback_data=f"test_cat_{category_key}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📝 *Профессиональные психологические тесты*\n\n"
        "Эти тесты разработаны и отобраны доктором Лысенко для предварительной самодиагностики. "
        "Помните, что окончательный диагноз может поставить только врач при личной консультации.\n\n"
        "Выберите категорию теста, который хотите пройти:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    return CHOOSING_TEST

async def show_test_categories(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Показывает доступные тесты в выбранной категории
    """
    query = update.callback_query
    await query.answer()
    
    # Получаем ключ категории из callback_data
    category_key = query.data.replace("test_cat_", "")
    
    # Получаем информацию о категории
    category_data = ALL_TEST_CATEGORIES.get(category_key)
    
    if not category_data:
        await query.edit_message_text("❌ Выбранная категория недоступна.")
        return ConversationHandler.END
    
    # Создаем клавиатуру с тестами в этой категории
    keyboard = []
    for test_key in category_data["tests"]:
        test_data = ALL_TESTS.get(test_key)
        if test_data:
            keyboard.append([InlineKeyboardButton(test_data["name"], callback_data=f"test_{test_key}")])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад к категориям", callback_data="test_back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"📝 *{category_data['name']}*\n\n"
        f"{category_data['description']}\n\n"
        f"Выберите тест, который хотите пройти:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    return CHOOSING_TEST

async def select_test(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обрабатывает выбор теста пользователем
    """
    query = update.callback_query
    await query.answer()
    
    # Если пользователь нажал "Назад к категориям"
    if query.data == "test_back":
        return await test_command(update, context)
    
    # Получаем ключ теста из callback_data
    test_key = query.data.replace("test_", "")
    
    # Получаем информацию о тесте
    test_data = ALL_TESTS.get(test_key)
    
    if not test_data:
        await query.edit_message_text("❌ Выбранный тест недоступен.")
        return ConversationHandler.END
    
    # Сохраняем выбранный тест в данных пользователя
    context.user_data["selected_test"] = test_key
    context.user_data["current_question"] = 0
    context.user_data["answers"] = []
    
    # Для тестов с подшкалами инициализируем словарь для ответов по подшкалам
    if test_data.get("calculation_type") == "subscales":
        context.user_data["subscale_answers"] = {}
        for subscale in test_data.get("subscales", []):
            context.user_data["subscale_answers"][subscale] = []
    
    # Создаем клавиатуру для подтверждения
    keyboard = [
        [InlineKeyboardButton("✅ Начать тест", callback_data="test_start")],
        [InlineKeyboardButton("❌ Отмена", callback_data="test_cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Добавляем предупреждение для чувствительных тестов
    sensitive_warning = ""
    if test_data.get("sensitive", False):
        sensitive_warning = "\n⚠️ *Примечание:* Этот тест содержит вопросы деликатного характера. Ваши ответы конфиденциальны и используются только для расчета результата."
    
    await query.edit_message_text(
        f"📝 *{test_data['name']}*\n\n"
        f"{test_data['description']}\n\n"
        f"Количество вопросов: {len(test_data['questions'])}\n"
        f"Примерное время: {test_data['time']} минут{sensitive_warning}\n\n"
        f"Готовы начать тест?",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    return CONFIRMING_TEST

async def process_test_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обрабатывает ответ пользователя на вопрос теста
    """
    query = update.callback_query
    await query.answer()
    
    # Если пользователь отменил тест
    if query.data == "test_cancel":
        await query.edit_message_text("❌ Тест отменен.")
        return ConversationHandler.END
    
    # Если пользователь начинает тест
    if query.data == "test_start":
        # Показываем первый вопрос
        return await show_test_question(update, context)
    
    # Получаем номер ответа из callback_data
    answer_num = int(query.data.replace("answer_", ""))
    
    test_key = context.user_data.get("selected_test")
    current_question = context.user_data.get("current_question", 0)
    test_data = ALL_TESTS.get(test_key)
    
    # Сохраняем ответ
    if test_data.get("calculation_type") == "subscales":
        # Для тестов с подшкалами
        question_data = test_data["questions"][current_question]
        subscale = question_data.get("subscale")
        
        if subscale:
            # Если вопрос относится к подшкале, сохраняем ответ в соответствующую подшкалу
            context.user_data["subscale_answers"][subscale].append(answer_num)
        
        # В любом случае сохраняем ответ в общий список
        context.user_data["answers"].append(answer_num)
    else:
        # Для обычных тестов
        context.user_data["answers"].append(answer_num)
    
    # Увеличиваем номер текущего вопроса
    context.user_data["current_question"] += 1
    
    # Показываем следующий вопрос или результат
    return await show_test_question(update, context)

async def show_test_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Показывает текущий вопрос теста
    """
    query = update.callback_query
    
    test_key = context.user_data.get("selected_test")
    current_question = context.user_data.get("current_question", 0)
    
    # Получаем информацию о тесте
    test_data = ALL_TESTS.get(test_key)
    
    if not test_data:
        await query.edit_message_text("❌ Произошла ошибка при загрузке теста.")
        return ConversationHandler.END
    
    # Если все вопросы заданы, показываем результат
    if current_question >= len(test_data["questions"]):
        return await calculate_test_result(update, context)
    
    # Получаем текущий вопрос
    question_data = test_data["questions"][current_question]
    
    # Создаем клавиатуру с вариантами ответов
    keyboard = []
    for i, answer in enumerate(question_data["answers"]):
        keyboard.append([InlineKeyboardButton(answer, callback_data=f"answer_{i}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"📝 *{test_data['name']}*\n\n"
        f"Вопрос {current_question + 1} из {len(test_data['questions'])}:\n\n"
        f"{question_data['text']}",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    return TAKING_TEST

async def calculate_test_result(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Рассчитывает результат теста
    """
    test_key = context.user_data.get("selected_test")
    answers = context.user_data.get("answers", [])
    
    # Получаем информацию о тесте
    test_data = ALL_TESTS.get(test_key)
    
    if not test_data or not answers:
        await update.callback_query.edit_message_text("❌ Произошла ошибка при расчете результата.")
        return ConversationHandler.END
    
    # Рассчитываем результат в зависимости от типа теста
    if test_data.get("calculation_type") == "subscales":
        # Для тестов с подшкалами
        subscale_scores = {}
        subscale_answers = context.user_data.get("subscale_answers", {})
        
        for subscale in test_data.get("subscales", []):
            subscale_score = 0
            subscale_questions = [q for q in test_data["questions"] if q.get("subscale") == subscale]
            
            for i, answer_idx in enumerate(subscale_answers.get(subscale, [])):
                question = subscale_questions[i]
                score = question["scores"][answer_idx]
                
                # Учитываем реверсивные вопросы
                if question.get("reverse", False):
                    # Для реверсивных вопросов уже учтено в структуре scores
                    pass
                
                subscale_score += score
            
            subscale_scores[subscale] = subscale_score
        
        # Сохраняем результаты подшкал
        context.user_data["subscale_scores"] = subscale_scores
        
        # Определяем интерпретации для каждой подшкалы
        interpretations = {}
        for subscale, score in subscale_scores.items():
            subscale_interpretation = ""
            for result in test_data["interpretations"].get(subscale, []):
                if score >= result["min_score"] and score <= result["max_score"]:
                    subscale_interpretation = result["text"]
                    break
            interpretations[subscale] = subscale_interpretation
        
        # Сохраняем интерпретации
        context.user_data["interpretations"] = interpretations
        
        # Сохраняем результат в базе данных
        db.save_test_result(
            user_id=update.callback_query.from_user.id,
            test_type=test_data["name"],
            score=sum(subscale_scores.values()),  # Общий балл как сумма подшкал
            answers=answers,
            interpretation=str(interpretations)  # Преобразуем словарь в строку
        )
    else:
        # Для обычных тестов
        score = 0
        for i, answer_idx in enumerate(answers):
            question = test_data["questions"][i]
            
            # Учитываем реверсивные вопросы
            if question.get("reverse", False):
                # Для реверсивных вопросов уже учтено в структуре scores
                pass
            
            score += question["scores"][answer_idx]
        
        # Сохраняем общий балл
        context.user_data["score"] = score
        
        # Определяем интерпретацию результата
        interpretation = ""
        for result in test_data["interpretations"]:
            if score >= result["min_score"] and score <= result["max_score"]:
                interpretation = result["text"]
                break
        
        # Сохраняем интерпретацию
        context.user_data["interpretation"] = interpretation
        
        # Сохраняем результат в базе данных
        db.save_test_result(
            user_id=update.callback_query.from_user.id,
            test_type=test_data["name"],
            score=score,
            answers=answers,
            interpretation=interpretation
        )
    
    # Создаем клавиатуру для просмотра результата
    keyboard = [
        [InlineKeyboardButton("📊 Показать результат", callback_data=f"result_{test_key}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        "✅ Тест завершен!\n\n"
        "Нажмите кнопку ниже, чтобы увидеть результат.",
        reply_markup=reply_markup
    )
    
    return SHOWING_RESULT

async def show_test_result(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Показывает результат теста
    """
    query = update.callback_query
    await query.answer()
    
    test_key = context.user_data.get("selected_test")
    
    # Получаем информацию о тесте
    test_data = ALL_TESTS.get(test_key)
    
    if not test_data:
        await query.edit_message_text("❌ Произошла ошибка при отображении результата.")
        return ConversationHandler.END
    
    # Формируем сообщение с результатом в зависимости от типа теста
    if test_data.get("calculation_type") == "subscales":
        # Для тестов с подшкалами
        subscale_scores = context.user_data.get("subscale_scores", {})
        interpretations = context.user_data.get("interpretations", {})
        
        result_text = f"📊 *Результат теста: {test_data['name']}*\n\n"
        
        # Добавляем результаты по каждой подшкале
        for subscale in test_data.get("subscales", []):
            score = subscale_scores.get(subscale, 0)
            interpretation = interpretations.get(subscale, "")
            
            # Определяем название подшкалы
            subscale_name = subscale.replace("_", " ").capitalize()
            
            result_text += f"*{subscale_name}*: {score} баллов\n"
            result_text += f"{interpretation}\n\n"
    else:
        # Для обычных тестов
        score = context.user_data.get("score", 0)
        interpretation = context.user_data.get("interpretation", "")
        
        result_text = f"📊 *Результат теста: {test_data['name']}*\n\n"
        result_text += f"Ваш результат: *{score}* баллов\n\n"
        result_text += f"{interpretation}\n\n"
    
    # Добавляем дисклеймер
    result_text += "⚠️ *Важно:* Результаты этого теста предназначены только для предварительной самодиагностики и не заменяют консультацию специалиста. Если у вас есть опасения относительно вашего психологического состояния, рекомендуется обратиться к психологу или психотерапевту."
    
    # Создаем клавиатуру для возврата к тестам и кнопки для блога и записи на прием
    keyboard = [
        [InlineKeyboardButton("🔄 Пройти еще раз", callback_data=f"test_{test_key}")],
        [InlineKeyboardButton("📝 Другие тесты", callback_data="test_back")],
        [InlineKeyboardButton("📚 Блог доктора Лысенко", url="https://t.me/psihotips")],
        [InlineKeyboardButton("🗓 Записаться на консультацию", url="https://t.me/psihotips/22")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Разбиваем длинное сообщение, если необходимо
    if len(result_text) > 4000:
        parts = split_text(result_text, 4000)
        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                # Последняя часть с кнопками
                await query.edit_message_text(
                    part,
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
            else:
                # Промежуточные части
                await query.message.reply_text(
                    part,
                    parse_mode="Markdown"
                )
    else:
        await query.edit_message_text(
            result_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    
    return CHOOSING_TEST
