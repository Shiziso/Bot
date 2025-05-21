#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import os
import json
import asyncio
from datetime import datetime

# Путь к базе данных
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bot_statistics.db')

# Инициализация базы данных
async def initialize_database():
    """Создает базу данных и необходимые таблицы, если они не существуют."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        first_seen TIMESTAMP,
        last_seen TIMESTAMP,
        message_count INTEGER DEFAULT 0
    )
    ''')
    
    # Таблица использования команд
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS command_usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        command TEXT,
        count INTEGER DEFAULT 0
    )
    ''')
    
    # Таблица взаимодействий с функциями
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS feature_interactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        feature TEXT,
        action TEXT,
        timestamp TIMESTAMP,
        metadata TEXT,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    ''')
    
    conn.commit()
    conn.close()

# Обработка сообщений пользователя
async def process_message(user_id, username, first_name, is_command=False):
    """Обновляет статистику пользователя при получении сообщения."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Проверяем, существует ли пользователь
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    
    if user:
        # Обновляем существующего пользователя
        cursor.execute(
            "UPDATE users SET username = ?, first_name = ?, last_seen = ?, message_count = message_count + 1 WHERE user_id = ?",
            (username, first_name, now, user_id)
        )
    else:
        # Добавляем нового пользователя
        cursor.execute(
            "INSERT INTO users (user_id, username, first_name, first_seen, last_seen, message_count) VALUES (?, ?, ?, ?, ?, 1)",
            (user_id, username, first_name, now, now)
        )
    
    conn.commit()
    conn.close()

# Увеличение счетчика использования команды
async def increment_command_usage(command):
    """Увеличивает счетчик использования определенной команды."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Проверяем, существует ли запись для этой команды
    cursor.execute("SELECT * FROM command_usage WHERE command = ?", (command,))
    cmd = cursor.fetchone()
    
    if cmd:
        # Увеличиваем счетчик
        cursor.execute(
            "UPDATE command_usage SET count = count + 1 WHERE command = ?",
            (command,)
        )
    else:
        # Добавляем новую запись
        cursor.execute(
            "INSERT INTO command_usage (command, count) VALUES (?, 1)",
            (command,)
        )
    
    conn.commit()
    conn.close()

# Запись взаимодействия с функцией
async def record_feature_interaction(user_id, feature, action, metadata=None):
    """Записывает взаимодействие пользователя с определенной функцией."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    metadata_json = json.dumps(metadata) if metadata else None
    
    cursor.execute(
        "INSERT INTO feature_interactions (user_id, feature, action, timestamp, metadata) VALUES (?, ?, ?, ?, ?)",
        (user_id, feature, action, now, metadata_json)
    )
    
    conn.commit()
    conn.close()

# Получение расширенной статистики
async def get_advanced_stats():
    """Возвращает расширенную статистику использования бота."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    stats = {}
    
    # Общая статистика пользователей
    cursor.execute("SELECT COUNT(*) FROM users")
    stats["total_users"] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE last_seen >= datetime('now', '-1 day')")
    stats["active_users_24h"] = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE last_seen >= datetime('now', '-7 day')")
    stats["active_users_7d"] = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(message_count) FROM users")
    stats["total_messages"] = cursor.fetchone()[0] or 0
    
    # Статистика команд
    cursor.execute("SELECT command, count FROM command_usage ORDER BY count DESC")
    stats["command_usage"] = {row[0]: row[1] for row in cursor.fetchall()}
    
    # Статистика функций
    cursor.execute("""
    SELECT feature, COUNT(*) as count 
    FROM feature_interactions 
    GROUP BY feature 
    ORDER BY count DESC
    """)
    stats["feature_usage"] = {row[0]: row[1] for row in cursor.fetchall()}
    
    # Статистика действий
    cursor.execute("""
    SELECT feature, action, COUNT(*) as count 
    FROM feature_interactions 
    GROUP BY feature, action 
    ORDER BY count DESC
    """)
    
    stats["action_usage"] = {}
    for row in cursor.fetchall():
        feature, action, count = row
        if feature not in stats["action_usage"]:
            stats["action_usage"][feature] = {}
        stats["action_usage"][feature][action] = count
    
    # Статистика по времени
    cursor.execute("""
    SELECT strftime('%Y-%m-%d', timestamp) as day, COUNT(*) as count 
    FROM feature_interactions 
    GROUP BY day 
    ORDER BY day DESC 
    LIMIT 7
    """)
    stats["daily_interactions"] = {row[0]: row[1] for row in cursor.fetchall()}
    
    conn.close()
    return stats

# Форматирование статистики в HTML
def format_stats_html(stats):
    """Форматирует статистику в HTML для отображения."""
    html = "<b>📊 Расширенная статистика бота</b>\n\n"
    
    # Общая статистика
    html += "<b>👥 Пользователи:</b>\n"
    html += f"• Всего пользователей: {stats['total_users']}\n"
    html += f"• Активных за 24 часа: {stats['active_users_24h']}\n"
    html += f"• Активных за 7 дней: {stats['active_users_7d']}\n"
    html += f"• Всего сообщений: {stats['total_messages']}\n\n"
    
    # Статистика команд
    html += "<b>🔍 Использование команд:</b>\n"
    for cmd, count in stats['command_usage'].items():
        html += f"• /{cmd}: {count}\n"
    html += "\n"
    
    # Статистика функций
    html += "<b>🛠 Использование функций:</b>\n"
    for feature, count in stats['feature_usage'].items():
        html += f"• {feature}: {count}\n"
    html += "\n"
    
    # Статистика действий
    html += "<b>🔄 Детализация по действиям:</b>\n"
    for feature, actions in stats['action_usage'].items():
        html += f"<b>{feature}:</b>\n"
        for action, count in actions.items():
            html += f"  • {action}: {count}\n"
    html += "\n"
    
    # Статистика по дням
    html += "<b>📅 Активность по дням:</b>\n"
    for day, count in stats['daily_interactions'].items():
        html += f"• {day}: {count} взаимодействий\n"
    
    return html
