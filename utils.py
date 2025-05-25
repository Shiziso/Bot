#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль с вспомогательными функциями для телеграм-бота
"""

import re
import time
import logging
import traceback
from datetime import datetime
from functools import wraps
from typing import Callable, Dict, Any, List, Optional

from telegram import Update
from telegram.ext import ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def rate_limit(key: str, limit_seconds: int) -> Callable:
    """
    Декоратор для ограничения частоты использования функций
    
    Args:
        key: Ключ для хранения времени последнего использования
        limit_seconds: Минимальный интервал между вызовами в секундах
        
    Returns:
        Декорированная функция
    """
    def decorator(func: Callable) -> Callable:
        # Словарь для хранения времени последнего использования для каждого пользователя
        last_used = {}
        
        @wraps(func)
        async def wrapper(update, context, *args, **kwargs):
            user_id = update.effective_user.id
            
            # Формируем уникальный ключ для пользователя и функции
            user_key = f"{user_id}_{key}"
            
            # Получаем текущее время
            current_time = time.time()
            
            # Очистка старых записей (старше 24 часов)
            keys_to_remove = []
            for k, v in last_used.items():
                if current_time - v > 86400:  # 24 часа в секундах
                    keys_to_remove.append(k)
            
            for k in keys_to_remove:
                del last_used[k]
            
            # Проверяем, прошло ли достаточно времени с последнего использования
            if user_key in last_used and current_time - last_used[user_key] < limit_seconds:
                # Вычисляем оставшееся время ожидания
                remaining_time = int(limit_seconds - (current_time - last_used[user_key]))
                
                # Форматируем время ожидания
                if remaining_time < 60:
                    time_str = f"{remaining_time} секунд"
                elif remaining_time < 3600:
                    time_str = f"{remaining_time // 60} минут"
                else:
                    time_str = f"{remaining_time // 3600} часов"
                
                # Отправляем сообщение о необходимости подождать
                await update.message.reply_text(
                    f"⏳ Пожалуйста, подождите {time_str} перед повторным использованием этой функции."
                )
                return
            
            # Обновляем время последнего использования
            last_used[user_key] = current_time
            
            # Вызываем оригинальную функцию
            return await func(update, context, *args, **kwargs)
        
        return wrapper
    
    return decorator

def format_datetime(dt: datetime) -> str:
    """
    Форматирует дату и время в удобочитаемый формат
    
    Args:
        dt: Объект datetime
        
    Returns:
        Отформатированная строка даты и времени
    """
    if not dt:
        return ""
    
    return dt.strftime("%d.%m.%Y %H:%M")

def split_text(text: str, max_length: int = 4096) -> List[str]:
    """
    Разбивает длинный текст на части для отправки в Telegram
    
    Args:
        text: Исходный текст
        max_length: Максимальная длина части
        
    Returns:
        Список частей текста
    """
    if len(text) <= max_length:
        return [text]
    
    parts = []
    for i in range(0, len(text), max_length):
        parts.append(text[i:i + max_length])
    
    return parts

def sanitize_input(text: str) -> str:
    """
    Очищает пользовательский ввод от потенциально опасных символов
    
    Args:
        text: Исходный текст
        
    Returns:
        Очищенный текст
    """
    if not text:
        return ""
    
    # Удаляем HTML-теги
    text = re.sub(r'<[^>]*>', '', text)
    
    # Экранируем специальные символы Markdown
    markdown_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in markdown_chars:
        text = text.replace(char, '\\' + char)
    
    return text

def format_mood_history(mood_history: List[Dict[str, Any]]) -> str:
    """
    Форматирует историю настроения для отображения пользователю
    
    Args:
        mood_history: Список словарей с информацией о настроении
        
    Returns:
        Отформатированный текст
    """
    if not mood_history:
        return "У вас пока нет записей о настроении."
    
    result = "📊 *История вашего настроения:*\n\n"
    
    for i, mood in enumerate(mood_history):
        date = mood["date_recorded"].strftime("%d.%m.%Y %H:%M")
        result += f"{i+1}. {date} - {mood['mood_emoji']} {mood['mood_text']}\n"
        
        if mood["notes"]:
            result += f"   _Заметка: {mood['notes']}_\n"
        
        result += "\n"
    
    return result

def format_test_results(test_results: List[Dict[str, Any]]) -> str:
    """
    Форматирует результаты тестов для отображения пользователю
    
    Args:
        test_results: Список словарей с информацией о результатах тестов
        
    Returns:
        Отформатированный текст
    """
    if not test_results:
        return "У вас пока нет пройденных тестов."
    
    result = "📝 *История ваших тестов:*\n\n"
    
    for i, test in enumerate(test_results):
        date = test["date_taken"].strftime("%d.%m.%Y %H:%M")
        result += f"{i+1}. {date} - {test['test_type']}\n"
        result += f"   Результат: {test['score']} баллов\n"
        result += f"   Интерпретация: {test['interpretation']}\n\n"
    
    return result

def format_questions(questions: List[Dict[str, Any]]) -> str:
    """
    Форматирует список вопросов для отображения пользователю
    
    Args:
        questions: Список словарей с информацией о вопросах
        
    Returns:
        Отформатированный текст
    """
    if not questions:
        return "У вас пока нет заданных вопросов."
    
    result = "❓ *Ваши вопросы:*\n\n"
    
    for i, question in enumerate(questions):
        date = question["date_asked"].strftime("%d.%m.%Y %H:%M")
        status = question["status"] if question["status"] else "⏳"
        
        result += f"{i+1}. {date} - {status}\n"
        result += f"   Вопрос: {question['question_text']}\n"
        
        if question["answer_text"]:
            result += f"   Ответ: {question['answer_text']}\n"
        
        result += "\n"
    
    return result

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
        from config import ADMIN_USER_ID
        
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

def get_user_mention(user) -> str:
    """
    Создает упоминание пользователя
    
    Args:
        user: Объект пользователя Telegram
        
    Returns:
        Строка с упоминанием пользователя
    """
    if user.username:
        return f"@{user.username}"
    else:
        return f"[{user.first_name}](tg://user?id={user.id})"
