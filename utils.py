#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль с вспомогательными функциями для телеграм-бота
"""

import re
import time
import logging
from functools import wraps
from datetime import datetime
from typing import Callable, List, Any, Dict

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
    Форматирует дату и время в удобочитаемый вид
    
    Args:
        dt: Объект datetime
        
    Returns:
        Отформатированная строка с датой и временем
    """
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except ValueError:
            try:
                dt = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return dt
    
    now = datetime.now()
    
    # Если дата сегодняшняя, показываем только время
    if dt.date() == now.date():
        return f"сегодня в {dt.strftime('%H:%M')}"
    
    # Если дата вчерашняя, показываем "вчера"
    yesterday = now.date().replace(day=now.day - 1)
    if dt.date() == yesterday:
        return f"вчера в {dt.strftime('%H:%M')}"
    
    # Если дата в текущем году, не показываем год
    if dt.year == now.year:
        return dt.strftime("%d %b в %H:%M")
    
    # В остальных случаях показываем полную дату
    return dt.strftime("%d.%m.%Y в %H:%M")

def get_user_mention(user) -> str:
    """
    Создает упоминание пользователя для сообщений
    
    Args:
        user: Объект пользователя Telegram
        
    Returns:
        Строка с упоминанием пользователя
    """
    if user.username:
        return f"@{user.username}"
    else:
        return f"{user.first_name}"

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
    
    # Разбиваем текст по абзацам
    paragraphs = text.split('\n\n')
    current_part = ""
    
    for paragraph in paragraphs:
        # Если абзац слишком длинный, разбиваем его на предложения
        if len(paragraph) > max_length:
            sentences = re.split(r'(?<=[.!?])\s+', paragraph)
            for sentence in sentences:
                if len(current_part) + len(sentence) + 2 <= max_length:
                    if current_part:
                        current_part += "\n\n" if current_part.endswith('.') else " "
                    current_part += sentence
                else:
                    parts.append(current_part)
                    current_part = sentence
        else:
            # Если текущая часть + абзац не превышают лимит
            if len(current_part) + len(paragraph) + 2 <= max_length:
                if current_part:
                    current_part += "\n\n"
                current_part += paragraph
            else:
                parts.append(current_part)
                current_part = paragraph
    
    # Добавляем последнюю часть
    if current_part:
        parts.append(current_part)
    
    return parts

def validate_time_format(time_str: str) -> bool:
    """
    Проверяет, соответствует ли строка формату времени ЧЧ:ММ
    
    Args:
        time_str: Строка с временем
        
    Returns:
        True, если формат верный, иначе False
    """
    pattern = r'^([01]\d|2[0-3]):([0-5]\d)$'
    return bool(re.match(pattern, time_str))

def sanitize_input(text: str) -> str:
    """
    Очищает пользовательский ввод от потенциально опасных символов
    
    Args:
        text: Исходный текст
        
    Returns:
        Очищенный текст
    """
    # Удаляем HTML-теги
    text = re.sub(r'<[^>]+>', '', text)
    
    # Экранируем специальные символы Markdown
    markdown_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in markdown_chars:
        text = text.replace(char, '\\' + char)
    
    return text

def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Обрезает текст до указанной длины, добавляя суффикс
    
    Args:
        text: Исходный текст
        max_length: Максимальная длина результата
        suffix: Суффикс для обрезанного текста
        
    Returns:
        Обрезанный текст
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix

def extract_command_args(text: str) -> List[str]:
    """
    Извлекает аргументы из текста команды
    
    Args:
        text: Текст команды
        
    Returns:
        Список аргументов
    """
    # Удаляем имя команды
    command_end = text.find(' ')
    if command_end == -1:
        return []
    
    args_text = text[command_end + 1:]
    
    # Разбиваем на аргументы, учитывая кавычки
    args = []
    current_arg = ""
    in_quotes = False
    quote_char = None
    
    for char in args_text:
        if char in ['"', "'"]:
            if not in_quotes:
                in_quotes = True
                quote_char = char
            elif char == quote_char:
                in_quotes = False
                quote_char = None
            else:
                current_arg += char
        elif char.isspace() and not in_quotes:
            if current_arg:
                args.append(current_arg)
                current_arg = ""
        else:
            current_arg += char
    
    if current_arg:
        args.append(current_arg)
    
    return args

def format_number(number: int) -> str:
    """
    Форматирует число для удобочитаемого отображения
    
    Args:
        number: Число для форматирования
        
    Returns:
        Отформатированная строка
    """
    if number < 1000:
        return str(number)
    elif number < 1000000:
        return f"{number / 1000:.1f}K".replace('.0K', 'K')
    else:
        return f"{number / 1000000:.1f}M".replace('.0M', 'M')

def calculate_age(birth_date: datetime) -> int:
    """
    Вычисляет возраст на основе даты рождения
    
    Args:
        birth_date: Дата рождения
        
    Returns:
        Возраст в годах
    """
    today = datetime.now()
    age = today.year - birth_date.year
    
    # Проверяем, был ли уже день рождения в этом году
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        age -= 1
    
    return age

def parse_duration(duration_str: str) -> int:
    """
    Преобразует строку с продолжительностью в секунды
    
    Args:
        duration_str: Строка с продолжительностью (например, "1h 30m")
        
    Returns:
        Продолжительность в секундах
    """
    total_seconds = 0
    
    # Ищем часы
    hours_match = re.search(r'(\d+)h', duration_str)
    if hours_match:
        total_seconds += int(hours_match.group(1)) * 3600
    
    # Ищем минуты
    minutes_match = re.search(r'(\d+)m', duration_str)
    if minutes_match:
        total_seconds += int(minutes_match.group(1)) * 60
    
    # Ищем секунды
    seconds_match = re.search(r'(\d+)s', duration_str)
    if seconds_match:
        total_seconds += int(seconds_match.group(1))
    
    return total_seconds

def format_duration(seconds: int) -> str:
    """
    Форматирует продолжительность в секундах в удобочитаемый вид
    
    Args:
        seconds: Продолжительность в секундах
        
    Returns:
        Отформатированная строка
    """
    if seconds < 60:
        return f"{seconds} сек."
    
    minutes = seconds // 60
    seconds %= 60
    
    if minutes < 60:
        if seconds == 0:
            return f"{minutes} мин."
        return f"{minutes} мин. {seconds} сек."
    
    hours = minutes // 60
    minutes %= 60
    
    if hours < 24:
        if minutes == 0:
            return f"{hours} ч."
        return f"{hours} ч. {minutes} мин."
    
    days = hours // 24
    hours %= 24
    
    if hours == 0:
        return f"{days} дн."
    return f"{days} дн. {hours} ч."
