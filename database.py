#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль для работы с базой данных телеграм-бота
"""

import os
import json
import sqlite3
import logging
import psycopg2
from datetime import datetime
from typing import List, Dict, Any, Optional, Union

from config import DATABASE

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class Database:
    """
    Класс для работы с базой данных
    Поддерживает SQLite и PostgreSQL
    """
    
    def __init__(self):
        """
        Инициализация класса базы данных
        """
        self.db_type = DATABASE["type"]
        self.connection = None
        self.cursor = None
    
    def connect(self) -> None:
        """
        Устанавливает соединение с базой данных
        """
        try:
            if self.db_type == "sqlite":
                self.connection = sqlite3.connect(DATABASE["sqlite_path"])
                self.connection.row_factory = sqlite3.Row
            elif self.db_type == "postgresql":
                self.connection = psycopg2.connect(
                    host=DATABASE["postgresql"]["host"],
                    port=DATABASE["postgresql"]["port"],
                    database=DATABASE["postgresql"]["database"],
                    user=DATABASE["postgresql"]["user"],
                    password=DATABASE["postgresql"]["password"]
                )
            else:
                raise ValueError(f"Неподдерживаемый тип базы данных: {self.db_type}")
            
            self.cursor = self.connection.cursor()
            logger.info(f"Соединение с базой данных {self.db_type} установлено")
        
        except Exception as e:
            logger.error(f"Ошибка при подключении к базе данных: {e}")
            raise
    
    def disconnect(self) -> None:
        """
        Закрывает соединение с базой данных
        """
        if self.connection:
            if self.cursor:
                self.cursor.close()
            self.connection.close()
            logger.info("Соединение с базой данных закрыто")
    
    def execute(self, query: str, params: tuple = ()) -> None:
        """
        Выполняет SQL-запрос без возврата результатов
        
        Args:
            query: SQL-запрос
            params: Параметры запроса
        """
        try:
            if not self.connection:
                self.connect()
            
            self.cursor.execute(query, params)
            self.connection.commit()
        
        except Exception as e:
            logger.error(f"Ошибка при выполнении запроса: {e}")
            logger.error(f"Запрос: {query}")
            logger.error(f"Параметры: {params}")
            if self.connection:
                self.connection.rollback()
            raise
    
    def query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """
        Выполняет SQL-запрос и возвращает результаты
        
        Args:
            query: SQL-запрос
            params: Параметры запроса
            
        Returns:
            Список словарей с результатами запроса
        """
        try:
            if not self.connection:
                self.connect()
            
            self.cursor.execute(query, params)
            
            if self.db_type == "sqlite":
                # SQLite.Row уже возвращает словарь-подобный объект
                return [dict(row) for row in self.cursor.fetchall()]
            elif self.db_type == "postgresql":
                # Для PostgreSQL нужно преобразовать результаты в словари
                columns = [desc[0] for desc in self.cursor.description]
                return [dict(zip(columns, row)) for row in self.cursor.fetchall()]
        
        except Exception as e:
            logger.error(f"Ошибка при выполнении запроса: {e}")
            logger.error(f"Запрос: {query}")
            logger.error(f"Параметры: {params}")
            if self.connection:
                self.connection.rollback()
            raise
    
    def init_db(self) -> None:
        """
        Инициализирует базу данных, создавая необходимые таблицы
        """
        try:
            self.connect()
            
            # Создаем таблицу пользователей
            self.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Создаем таблицу настроек пользователей
            self.execute('''
                CREATE TABLE IF NOT EXISTS user_settings (
                    user_id INTEGER PRIMARY KEY,
                    notifications_enabled BOOLEAN DEFAULT TRUE,
                    daily_tip_time TEXT DEFAULT '09:00',
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
            
            # Создаем таблицу логов команд
            if self.db_type == "sqlite":
                self.execute('''
                    CREATE TABLE IF NOT EXISTS command_logs (
                        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        command TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                    )
                ''')
            elif self.db_type == "postgresql":
                self.execute('''
                    CREATE TABLE IF NOT EXISTS command_logs (
                        log_id SERIAL PRIMARY KEY,
                        user_id INTEGER,
                        command TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                    )
                ''')
            
            # Создаем таблицу ежедневных советов
            if self.db_type == "sqlite":
                self.execute('''
                    CREATE TABLE IF NOT EXISTS daily_tips (
                        tip_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        tip_text TEXT,
                        date_sent TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                    )
                ''')
            elif self.db_type == "postgresql":
                self.execute('''
                    CREATE TABLE IF NOT EXISTS daily_tips (
                        tip_id SERIAL PRIMARY KEY,
                        user_id INTEGER,
                        tip_text TEXT,
                        date_sent TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                    )
                ''')
            
            # Создаем таблицу анонимных вопросов
            if self.db_type == "sqlite":
                self.execute('''
                    CREATE TABLE IF NOT EXISTS anonymous_questions (
                        question_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        question_text TEXT,
                        answer_text TEXT,
                        status TEXT DEFAULT '❓',
                        date_asked TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        date_answered TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                    )
                ''')
            elif self.db_type == "postgresql":
                self.execute('''
                    CREATE TABLE IF NOT EXISTS anonymous_questions (
                        question_id SERIAL PRIMARY KEY,
                        user_id INTEGER,
                        question_text TEXT,
                        answer_text TEXT,
                        status TEXT DEFAULT '❓',
                        date_asked TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        date_answered TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                    )
                ''')
            
            # Создаем таблицу результатов тестов
            if self.db_type == "sqlite":
                self.execute('''
                    CREATE TABLE IF NOT EXISTS test_results (
                        result_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        test_type TEXT,
                        score INTEGER,
                        answers TEXT,
                        interpretation TEXT,
                        date_taken TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                    )
                ''')
            elif self.db_type == "postgresql":
                self.execute('''
                    CREATE TABLE IF NOT EXISTS test_results (
                        result_id SERIAL PRIMARY KEY,
                        user_id INTEGER,
                        test_type TEXT,
                        score INTEGER,
                        answers TEXT,
                        interpretation TEXT,
                        date_taken TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                    )
                ''')
            
            # Создаем таблицу отслеживания настроения
            if self.db_type == "sqlite":
                self.execute('''
                    CREATE TABLE IF NOT EXISTS mood_tracking (
                        mood_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        mood_emoji TEXT,
                        mood_text TEXT,
                        notes TEXT,
                        date_recorded TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                    )
                ''')
            elif self.db_type == "postgresql":
                self.execute('''
                    CREATE TABLE IF NOT EXISTS mood_tracking (
                        mood_id SERIAL PRIMARY KEY,
                        user_id INTEGER,
                        mood_emoji TEXT,
                        mood_text TEXT,
                        notes TEXT,
                        date_recorded TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                    )
                ''')
            
            # Создаем таблицу статистики использования
            if self.db_type == "sqlite":
                self.execute('''
                    CREATE TABLE IF NOT EXISTS usage_statistics (
                        stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        feature TEXT,
                        usage_count INTEGER DEFAULT 1,
                        last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                    )
                ''')
            elif self.db_type == "postgresql":
                self.execute('''
                    CREATE TABLE IF NOT EXISTS usage_statistics (
                        stat_id SERIAL PRIMARY KEY,
                        user_id INTEGER,
                        feature TEXT,
                        usage_count INTEGER DEFAULT 1,
                        last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                    )
                ''')
            
            logger.info("База данных инициализирована")
        
        except Exception as e:
            logger.error(f"Ошибка при инициализации базы данных: {e}")
            raise
        
        finally:
            self.disconnect()
    
    def register_user(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None) -> bool:
        """
        Регистрирует нового пользователя или обновляет информацию о существующем
        
        Args:
            user_id: ID пользователя в Telegram
            username: Имя пользователя в Telegram
            first_name: Имя пользователя
            last_name: Фамилия пользователя
            
        Returns:
            True, если операция выполнена успешно
        """
        try:
            self.connect()
            
            # Проверяем, существует ли пользователь
            if self.db_type == "postgresql":
                select_user_query = "SELECT user_id FROM users WHERE user_id = %s"
            else: # sqlite
                select_user_query = "SELECT user_id FROM users WHERE user_id = ?"
            
            existing_user = self.query(select_user_query, (user_id,))
            
            if existing_user:
                # Обновляем информацию о пользователе
                if self.db_type == "postgresql":
                    update_user_query = "UPDATE users SET username = %s, first_name = %s, last_name = %s WHERE user_id = %s"
                else: # sqlite
                    update_user_query = "UPDATE users SET username = ?, first_name = ?, last_name = ? WHERE user_id = ?"
                
                self.execute(update_user_query, (username, first_name, last_name, user_id))
                logger.info(f"Обновлена информация о пользователе {user_id}")
            else:
                # Регистрируем нового пользователя
                if self.db_type == "postgresql":
                    insert_user_query = "INSERT INTO users (user_id, username, first_name, last_name) VALUES (%s, %s, %s, %s)"
                else: # sqlite
                    insert_user_query = "INSERT INTO users (user_id, username, first_name, last_name) VALUES (?, ?, ?, ?)"
                
                self.execute(insert_user_query, (user_id, username, first_name, last_name))
                
                # Создаем настройки по умолчанию
                if self.db_type == "postgresql":
                    insert_settings_query = "INSERT INTO user_settings (user_id) VALUES (%s)"
                else: # sqlite
                    insert_settings_query = "INSERT INTO user_settings (user_id) VALUES (?)"
                
                self.execute(insert_settings_query, (user_id,))
                
                logger.info(f"Зарегистрирован новый пользователь {user_id}")
            
            return True
        
        except Exception as e:
            logger.error(f"Ошибка при регистрации пользователя: {e}")
            return False
        
        finally:
            self.disconnect()
    
    def update_user_activity(self, user_id: int) -> bool:
        """
        Обновляет время последней активности пользователя
        
        Args:
            user_id: ID пользователя в Telegram
            
        Returns:
            True, если операция выполнена успешно
        """
        try:
            self.connect()
            
            current_time = datetime.now()
            
            if self.db_type == "postgresql":
                update_activity_query = "UPDATE users SET last_activity = %s WHERE user_id = %s"
            else: # sqlite
                update_activity_query = "UPDATE users SET last_activity = ? WHERE user_id = ?"
            
            self.execute(update_activity_query, (current_time, user_id))
            
            return True
        
        except Exception as e:
            logger.error(f"Ошибка при обновлении активности пользователя: {e}")
            return False
        
        finally:
            self.disconnect()
    
    def log_command_usage(self, user_id: int, command: str) -> bool:
        """
        Логирует использование команды пользователем
        
        Args:
            user_id: ID пользователя в Telegram
            command: Название команды
            
        Returns:
            True, если операция выполнена успешно
        """
        try:
            self.connect()
            
            if self.db_type == "postgresql":
                insert_command_log_query = "INSERT INTO command_logs (user_id, command) VALUES (%s, %s)"
            else: # sqlite
                insert_command_log_query = "INSERT INTO command_logs (user_id, command) VALUES (?, ?)"
            
            self.execute(insert_command_log_query, (user_id, command))
            
            return True
        
        except Exception as e:
            logger.error(f"Ошибка при логировании команды: {e}")
            return False
        
        finally:
            self.disconnect()
    
    def save_daily_tip(self, user_id: int, tip_text: str) -> bool:
        """
        Сохраняет отправленный пользователю совет дня
        
        Args:
            user_id: ID пользователя в Telegram
            tip_text: Текст совета
            
        Returns:
            True, если операция выполнена успешно
        """
        try:
            self.connect()
            
            if self.db_type == "postgresql":
                insert_daily_tip_query = "INSERT INTO daily_tips (user_id, tip_text) VALUES (%s, %s)"
            else: # sqlite
                insert_daily_tip_query = "INSERT INTO daily_tips (user_id, tip_text) VALUES (?, ?)"
            
            self.execute(insert_daily_tip_query, (user_id, tip_text))
            
            return True
        
        except Exception as e:
            logger.error(f"Ошибка при сохранении совета дня: {e}")
            return False
        
        finally:
            self.disconnect()
    
    def get_user_tips_history(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Получает историю советов дня для пользователя
        
        Args:
            user_id: ID пользователя в Telegram
            limit: Максимальное количество записей
            
        Returns:
            Список словарей с информацией о советах
        """
        try:
            self.connect()
            
            if self.db_type == "postgresql":
                select_tips_history_query = "SELECT tip_id, tip_text, date_sent FROM daily_tips WHERE user_id = %s ORDER BY date_sent DESC LIMIT %s"
            else: # sqlite
                select_tips_history_query = "SELECT tip_id, tip_text, date_sent FROM daily_tips WHERE user_id = ? ORDER BY date_sent DESC LIMIT ?"
            
            tips = self.query(select_tips_history_query, (user_id, limit))
            
            return tips
        
        except Exception as e:
            logger.error(f"Ошибка при получении истории советов: {e}")
            return []
        
        finally:
            self.disconnect()
    
    def save_anonymous_question(self, user_id: int, question_text: str) -> Optional[int]:
        """
        Сохраняет анонимный вопрос пользователя
        
        Args:
            user_id: ID пользователя в Telegram
            question_text: Текст вопроса
            
        Returns:
            ID вопроса или None в случае ошибки
        """
        try:
            self.connect()
            
            if self.db_type == "sqlite":
                insert_query = "INSERT INTO anonymous_questions (user_id, question_text) VALUES (?, ?)"
                self.execute(insert_query, (user_id, question_text))
                # Получаем ID последней вставленной записи
                # For SQLite, last_insert_rowid() is specific and doesn't need %s or ?
                question_id_query = "SELECT last_insert_rowid() as id"
                question_id = self.query(question_id_query)[0]["id"]
            
            elif self.db_type == "postgresql":
                insert_query = "INSERT INTO anonymous_questions (user_id, question_text) VALUES (%s, %s) RETURNING question_id"
                result = self.query(insert_query, (user_id, question_text))
                question_id = result[0]["question_id"]
            else:
                # Should not happen if db_type is validated in __init__
                logger.error(f"Unsupported database type: {self.db_type} in save_anonymous_question")
                return None
            
            logger.info(f"Сохранен анонимный вопрос от пользователя {user_id}, ID вопроса: {question_id}")
            
            return question_id
        
        except Exception as e:
            logger.error(f"Ошибка при сохранении анонимного вопроса: {e}")
            return None
        
        finally:
            self.disconnect()
    
    def save_question_answer(self, question_id: int, answer_text: str) -> bool:
        """
        Сохраняет ответ на анонимный вопрос
        
        Args:
            question_id: ID вопроса
            answer_text: Текст ответа
            
        Returns:
            True, если операция выполнена успешно
        """
        try:
            self.connect()
            
            current_time = datetime.now()
            
            from config import NOTIFICATION_SETTINGS
            
            if self.db_type == "postgresql":
                update_query = "UPDATE anonymous_questions SET answer_text = %s, status = %s, date_answered = %s WHERE question_id = %s"
            else: # sqlite
                update_query = "UPDATE anonymous_questions SET answer_text = ?, status = ?, date_answered = ? WHERE question_id = ?"
            
            self.execute(
                update_query,
                (answer_text, NOTIFICATION_SETTINGS["answered_question_emoji"], current_time, question_id)
            )
            
            logger.info(f"Сохранен ответ на вопрос {question_id}")
            
            return True
        
        except Exception as e:
            logger.error(f"Ошибка при сохранении ответа на вопрос: {e}")
            return False
        
        finally:
            self.disconnect()
    
    def get_question_by_id(self, question_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает информацию о вопросе по его ID
        
        Args:
            question_id: ID вопроса
            
        Returns:
            Словарь с информацией о вопросе или None, если вопрос не найден
        """
        try:
            self.connect()
            
            if self.db_type == "postgresql":
                select_query = """
                    SELECT q.*, u.username, u.first_name, u.last_name
                    FROM anonymous_questions q
                    JOIN users u ON q.user_id = u.user_id
                    WHERE q.question_id = %s
                """
            else: # sqlite
                select_query = """
                    SELECT q.*, u.username, u.first_name, u.last_name
                    FROM anonymous_questions q
                    JOIN users u ON q.user_id = u.user_id
                    WHERE q.question_id = ?
                """
            
            questions = self.query(select_query, (question_id,))
            
            if questions:
                return questions[0]
            else:
                return None
        
        except Exception as e:
            logger.error(f"Ошибка при получении вопроса: {e}")
            return None
        
        finally:
            self.disconnect()
    
    def get_user_questions(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Получает список вопросов пользователя
        
        Args:
            user_id: ID пользователя в Telegram
            limit: Максимальное количество записей
            
        Returns:
            Список словарей с информацией о вопросах
        """
        try:
            self.connect()
            
            if self.db_type == "postgresql":
                select_query = """
                    SELECT question_id, question_text, answer_text, status, date_asked, date_answered
                    FROM anonymous_questions
                    WHERE user_id = %s
                    ORDER BY date_asked DESC
                    LIMIT %s
                """
            else: # sqlite
                select_query = """
                    SELECT question_id, question_text, answer_text, status, date_asked, date_answered
                    FROM anonymous_questions
                    WHERE user_id = ?
                    ORDER BY date_asked DESC
                    LIMIT ?
                """
            
            questions = self.query(select_query, (user_id, limit))
            
            return questions
        
        except Exception as e:
            logger.error(f"Ошибка при получении вопросов пользователя: {e}")
            return []
        
        finally:
            self.disconnect()
    
    def get_unanswered_questions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Получает список неотвеченных вопросов
        
        Args:
            limit: Максимальное количество записей
            
        Returns:
            Список словарей с информацией о вопросах
        """
        try:
            self.connect()
            
            if self.db_type == "postgresql":
                select_query = """
                    SELECT q.*, u.username, u.first_name, u.last_name
                    FROM anonymous_questions q
                    JOIN users u ON q.user_id = u.user_id
                    WHERE q.answer_text IS NULL
                    ORDER BY q.date_asked ASC
                    LIMIT %s
                """
            else: # sqlite
                select_query = """
                    SELECT q.*, u.username, u.first_name, u.last_name
                    FROM anonymous_questions q
                    JOIN users u ON q.user_id = u.user_id
                    WHERE q.answer_text IS NULL
                    ORDER BY q.date_asked ASC
                    LIMIT ?
                """
            
            questions = self.query(select_query, (limit,))
            
            return questions
        
        except Exception as e:
            logger.error(f"Ошибка при получении неотвеченных вопросов: {e}")
            return []
        
        finally:
            self.disconnect()
    
    def save_test_result(self, user_id: int, test_type: str, score: int, answers: Dict[str, Any], interpretation: str) -> Optional[int]:
        """
        Сохраняет результат теста
        
        Args:
            user_id: ID пользователя в Telegram
            test_type: Тип теста
            score: Результат теста
            answers: Ответы на вопросы теста
            interpretation: Интерпретация результата
            
        Returns:
            ID результата или None в случае ошибки
        """
        try:
            self.connect()
            
            # Преобразуем словарь ответов в JSON
            answers_json = json.dumps(answers)
            
            if self.db_type == "sqlite":
                insert_query = "INSERT INTO test_results (user_id, test_type, score, answers, interpretation) VALUES (?, ?, ?, ?, ?)"
                self.execute(insert_query, (user_id, test_type, score, answers_json, interpretation))
                # Получаем ID последней вставленной записи
                id_query = "SELECT last_insert_rowid() as id"
                result_id = self.query(id_query)[0]["id"]
            
            elif self.db_type == "postgresql":
                insert_query = "INSERT INTO test_results (user_id, test_type, score, answers, interpretation) VALUES (%s, %s, %s, %s, %s) RETURNING result_id"
                result = self.query(insert_query, (user_id, test_type, score, answers_json, interpretation))
                result_id = result[0]["result_id"]
            else:
                # Should not happen if db_type is validated in __init__
                logger.error(f"Unsupported database type: {self.db_type} in save_test_result")
                return None
            
            logger.info(f"Сохранен результат теста {test_type} для пользователя {user_id}, ID результата: {result_id}")
            
            return result_id
        
        except Exception as e:
            logger.error(f"Ошибка при сохранении результата теста: {e}")
            return None
        
        finally:
            self.disconnect()
    
    def get_user_test_results(self, user_id: int, test_type: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Получает результаты тестов пользователя
        
        Args:
            user_id: ID пользователя в Telegram
            test_type: Тип теста (если None, то все типы)
            limit: Максимальное количество записей
            
        Returns:
            Список словарей с информацией о результатах тестов
        """
        try:
            self.connect()
            
            if test_type:
                query_str = """
                    SELECT result_id, test_type, score, interpretation, date_taken
                    FROM test_results
                    WHERE user_id = %s AND test_type = %s
                    ORDER BY date_taken DESC
                    LIMIT %s
                """
                else:
                    query_str = """
                    SELECT result_id, test_type, score, interpretation, date_taken
                    FROM test_results
                    WHERE user_id = ? AND test_type = ?
                    ORDER BY date_taken DESC
                    LIMIT ?
                """
                results = self.query(query_str, (user_id, test_type, limit))
            else:
                if self.db_type == "postgresql":
                    query_str = """
                    SELECT result_id, test_type, score, interpretation, date_taken
                    FROM test_results
                    WHERE user_id = %s
                    ORDER BY date_taken DESC
                    LIMIT %s
                    """
                else:
                    query_str = """
                    SELECT result_id, test_type, score, interpretation, date_taken
                    FROM test_results
                    WHERE user_id = ?
                    ORDER BY date_taken DESC
                    LIMIT ?
                    """
                results = self.query(query_str, (user_id, limit))
            
            return results
        
        except Exception as e:
            logger.error(f"Ошибка при получении результатов тестов: {e}")
            return []
        
        finally:
            self.disconnect()
    
    def save_mood(self, user_id: int, mood_emoji: str, mood_text: str, notes: str = None) -> Optional[int]:
        """
        Сохраняет запись о настроении пользователя
        
        Args:
            user_id: ID пользователя в Telegram
            mood_emoji: Эмодзи настроения
            mood_text: Текстовое описание настроения
            notes: Дополнительные заметки
            
        Returns:
            ID записи или None в случае ошибки
        """
        try:
            self.connect()
            
            if self.db_type == "sqlite":
                insert_query = "INSERT INTO mood_tracking (user_id, mood_emoji, mood_text, notes) VALUES (?, ?, ?, ?)"
                self.execute(insert_query, (user_id, mood_emoji, mood_text, notes))
                # Получаем ID последней вставленной записи
                id_query = "SELECT last_insert_rowid() as id"
                mood_id = self.query(id_query)[0]["id"]
            
            elif self.db_type == "postgresql":
                insert_query = "INSERT INTO mood_tracking (user_id, mood_emoji, mood_text, notes) VALUES (%s, %s, %s, %s) RETURNING mood_id"
                result = self.query(insert_query, (user_id, mood_emoji, mood_text, notes))
                mood_id = result[0]["mood_id"]
            else:
                # Should not happen if db_type is validated in __init__
                logger.error(f"Unsupported database type: {self.db_type} in save_mood")
                return None
            
            logger.info(f"Сохранена запись о настроении пользователя {user_id}, ID записи: {mood_id}")
            
            return mood_id
        
        except Exception as e:
            logger.error(f"Ошибка при сохранении настроения: {e}")
            return None
        
        finally:
            self.disconnect()
    
    def get_user_mood_history(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Получает историю настроения пользователя
        
        Args:
            user_id: ID пользователя в Telegram
            limit: Максимальное количество записей
            
        Returns:
            Список словарей с информацией о настроении
        """
        try:
            self.connect()
            
            if self.db_type == "postgresql":
                select_query = """
                    SELECT mood_id, mood_emoji, mood_text, notes, date_recorded
                    FROM mood_tracking
                    WHERE user_id = %s
                    ORDER BY date_recorded DESC
                    LIMIT %s
                """
            else: # sqlite
                select_query = """
                    SELECT mood_id, mood_emoji, mood_text, notes, date_recorded
                    FROM mood_tracking
                    WHERE user_id = ?
                    ORDER BY date_recorded DESC
                    LIMIT ?
                """
            
            moods = self.query(select_query, (user_id, limit))
            
            return moods
        
        except Exception as e:
            logger.error(f"Ошибка при получении истории настроения: {e}")
            return []
        
        finally:
            self.disconnect()
    
    def get_user_settings(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает настройки пользователя
        
        Args:
            user_id: ID пользователя в Telegram
            
        Returns:
            Словарь с настройками или None, если пользователь не найден
        """
        try:
            self.connect()
            
            if self.db_type == "postgresql":
                select_settings_query = "SELECT * FROM user_settings WHERE user_id = %s"
            else: # sqlite
                select_settings_query = "SELECT * FROM user_settings WHERE user_id = ?"
            
            settings = self.query(select_settings_query, (user_id,))
            
            if settings:
                return settings[0]
            else:
                return None
        
        except Exception as e:
            logger.error(f"Ошибка при получении настроек пользователя: {e}")
            return None
        
        finally:
            self.disconnect()
    
    def update_user_settings(self, user_id: int, notifications_enabled: bool = None, daily_tip_time: str = None) -> bool:
        """
        Обновляет настройки пользователя
        
        Args:
            user_id: ID пользователя в Telegram
            notifications_enabled: Включены ли уведомления
            daily_tip_time: Время отправки ежедневного совета
            
        Returns:
            True, если операция выполнена успешно
        """
        try:
            self.connect()
            
            # Получаем текущие настройки
            if self.db_type == "postgresql":
                settings_query_str = "SELECT * FROM user_settings WHERE user_id = %s"
            else:
                settings_query_str = "SELECT * FROM user_settings WHERE user_id = ?"
            
            settings = self.query(settings_query_str, (user_id,))
            
            if not settings:
                # Создаем настройки по умолчанию
                if self.db_type == "postgresql":
                    insert_query_str = "INSERT INTO user_settings (user_id) VALUES (%s)"
                else:
                    insert_query_str = "INSERT INTO user_settings (user_id) VALUES (?)"
                self.execute(insert_query_str, (user_id,))
            
            # Обновляем настройки
            updates = []
            params = []
            
            placeholder = "%s" if self.db_type == "postgresql" else "?"
            
            if notifications_enabled is not None:
                updates.append(f"notifications_enabled = {placeholder}")
                params.append(notifications_enabled)
            
            if daily_tip_time is not None:
                updates.append(f"daily_tip_time = {placeholder}")
                params.append(daily_tip_time)
            
            if updates:
                update_query_str = f"UPDATE user_settings SET {', '.join(updates)} WHERE user_id = {placeholder}"
                params.append(user_id)
                self.execute(update_query_str, tuple(params))
            
            logger.info(f"Обновлены настройки пользователя {user_id}")
            
            return True
        
        except Exception as e:
            logger.error(f"Ошибка при обновлении настроек пользователя: {e}")
            return False
        
        finally:
            self.disconnect()
    
    def get_active_users(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Получает список активных пользователей за указанный период
        
        Args:
            days: Количество дней
            
        Returns:
            Список словарей с информацией о пользователях
        """
        try:
            self.connect()
            
            if self.db_type == "sqlite":
                query_str = """
                    SELECT u.user_id, u.username, u.first_name, u.last_name, u.last_activity,
                           COUNT(c.log_id) as command_count
                    FROM users u
                    LEFT JOIN command_logs c ON u.user_id = c.user_id
                    WHERE u.last_activity >= datetime('now', ?)
                    GROUP BY u.user_id
                    ORDER BY command_count DESC
                """
                days_param = f"-{days} days"
                users = self.query(query_str, (days_param,))
            elif self.db_type == "postgresql":
                query_str = """
                    SELECT u.user_id, u.username, u.first_name, u.last_name, u.last_activity,
                           COUNT(c.log_id) as command_count
                    FROM users u
                    LEFT JOIN command_logs c ON u.user_id = c.user_id
                    WHERE u.last_activity >= NOW() - INTERVAL %s
                    GROUP BY u.user_id
                    ORDER BY command_count DESC
                """
                days_param = f"{days} days"
                users = self.query(query_str, (days_param,))
            else:
                users = [] # Should not happen given db_type check at init
            
            return users
        
        except Exception as e:
            logger.error(f"Ошибка при получении активных пользователей: {e}")
            return []
        
        finally:
            self.disconnect()
    
    def get_commands_stats(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Получает статистику использования команд за указанный период
        
        Args:
            days: Количество дней
            
        Returns:
            Список словарей со статистикой команд
        """
        try:
            self.connect()
            
            if self.db_type == "sqlite":
                query_str = """
                    SELECT command, COUNT(*) as count, COUNT(DISTINCT user_id) as unique_users
                    FROM command_logs
                    WHERE timestamp >= datetime('now', ?)
                    GROUP BY command
                    ORDER BY count DESC
                """
                days_param = f"-{days} days"
                stats = self.query(query_str, (days_param,))
            elif self.db_type == "postgresql":
                query_str = """
                    SELECT command, COUNT(*) as count, COUNT(DISTINCT user_id) as unique_users
                    FROM command_logs
                    WHERE timestamp >= NOW() - INTERVAL %s
                    GROUP BY command
                    ORDER BY count DESC
                """
                days_param = f"{days} days"
                stats = self.query(query_str, (days_param,))
            else:
                stats = [] # Should not happen
            
            return stats
        
        except Exception as e:
            logger.error(f"Ошибка при получении статистики команд: {e}")
            return []
        
        finally:
            self.disconnect()
    
    def get_daily_stats(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Получает ежедневную статистику использования бота
        
        Args:
            days: Количество дней
            
        Returns:
            Список словарей с ежедневной статистикой
        """
        try:
            self.connect()
            
            if self.db_type == "sqlite":
                query_str = """
                    SELECT date(timestamp) as date, COUNT(*) as command_count, COUNT(DISTINCT user_id) as user_count
                    FROM command_logs
                    WHERE timestamp >= datetime('now', ?)
                    GROUP BY date(timestamp)
                    ORDER BY date
                """
                days_param = f"-{days} days"
                stats = self.query(query_str, (days_param,))
            elif self.db_type == "postgresql":
                query_str = """
                    SELECT DATE(timestamp) as date, COUNT(*) as command_count, COUNT(DISTINCT user_id) as user_count
                    FROM command_logs
                    WHERE timestamp >= NOW() - INTERVAL %s
                    GROUP BY DATE(timestamp)
                    ORDER BY date
                """
                days_param = f"{days} days"
                stats = self.query(query_str, (days_param,))
            else:
                stats = [] # Should not happen
            
            return stats
        
        except Exception as e:
            logger.error(f"Ошибка при получении ежедневной статистики: {e}")
            return []
        
        finally:
            self.disconnect()
    
    def get_feature_usage_stats(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Получает статистику использования различных функций бота
        
        Args:
            days: Количество дней
            
        Returns:
            Список словарей со статистикой функций
        """
        try:
            self.connect()
            
            # Статистика по тестам
            if self.db_type == "sqlite":
                tests_query = """
                    SELECT test_type as feature, COUNT(*) as count, COUNT(DISTINCT user_id) as unique_users
                    FROM test_results
                    WHERE date_taken >= datetime('now', ?)
                    GROUP BY test_type
                """
                days_param = f"-{days} days"
                tests_stats = self.query(tests_query, (days_param,))
            elif self.db_type == "postgresql":
                tests_query = """
                    SELECT test_type as feature, COUNT(*) as count, COUNT(DISTINCT user_id) as unique_users
                    FROM test_results
                    WHERE date_taken >= NOW() - INTERVAL %s
                    GROUP BY test_type
                """
                days_param = f"{days} days"
                tests_stats = self.query(tests_query, (days_param,))
            else:
                tests_stats = [] # Should not happen
            
            # Статистика по настроению
            if self.db_type == "sqlite":
                mood_query = """
                    SELECT 'mood_tracking' as feature, COUNT(*) as count, COUNT(DISTINCT user_id) as unique_users
                    FROM mood_tracking
                    WHERE date_recorded >= datetime('now', ?)
                """
                mood_stats = self.query(mood_query, (days_param,))
            elif self.db_type == "postgresql":
                mood_query = """
                    SELECT 'mood_tracking' as feature, COUNT(*) as count, COUNT(DISTINCT user_id) as unique_users
                    FROM mood_tracking
                    WHERE date_recorded >= NOW() - INTERVAL %s
                """
                mood_stats = self.query(mood_query, (days_param,))
            else:
                mood_stats = [] # Should not happen
            
            # Статистика по вопросам
            if self.db_type == "sqlite":
                questions_query = """
                    SELECT 'questions' as feature, COUNT(*) as count, COUNT(DISTINCT user_id) as unique_users
                    FROM anonymous_questions
                    WHERE date_asked >= datetime('now', ?)
                """
                questions_stats = self.query(questions_query, (days_param,))
            elif self.db_type == "postgresql":
                questions_query = """
                    SELECT 'questions' as feature, COUNT(*) as count, COUNT(DISTINCT user_id) as unique_users
                    FROM anonymous_questions
                    WHERE date_asked >= NOW() - INTERVAL %s
                """
                questions_stats = self.query(questions_query, (days_param,))
            else:
                questions_stats = [] # Should not happen
            
            # Объединяем статистику
            stats = tests_stats + mood_stats + questions_stats
            
            # Сортируем по количеству использований
            stats.sort(key=lambda x: x["count"], reverse=True)
            
            return stats
        
        except Exception as e:
            logger.error(f"Ошибка при получении статистики функций: {e}")
            return []
        
        finally:
            self.disconnect()
    
    def get_retention_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        Получает статистику удержания пользователей
        
        Args:
            days: Количество дней для анализа
            
        Returns:
            Словарь со статистикой удержания
        """
        try:
            self.connect()
            
            # Общее количество пользователей
            if self.db_type == "sqlite":
                total_query = "SELECT COUNT(*) as count FROM users"
                total_users = self.query(total_query)[0]["count"]
            elif self.db_type == "postgresql":
                total_query = "SELECT COUNT(*) as count FROM users"
                total_users = self.query(total_query)[0]["count"]
            else:
                total_users = 0 # Should not happen
            
            # Активные пользователи за последний день
            if self.db_type == "sqlite":
                day_query = """
                    SELECT COUNT(DISTINCT user_id) as count
                    FROM users
                    WHERE last_activity >= datetime('now', '-1 day')
                """
                day_active = self.query(day_query)[0]["count"]
            elif self.db_type == "postgresql":
                day_query = """
                    SELECT COUNT(DISTINCT user_id) as count
                    FROM users
                    WHERE last_activity >= NOW() - INTERVAL '1 day'
                """
                day_active = self.query(day_query)[0]["count"]
            else:
                day_active = 0 # Should not happen
            
            # Активные пользователи за последнюю неделю
            if self.db_type == "sqlite":
                week_query = """
                    SELECT COUNT(DISTINCT user_id) as count
                    FROM users
                    WHERE last_activity >= datetime('now', '-7 day')
                """
                week_active = self.query(week_query)[0]["count"]
            elif self.db_type == "postgresql":
                week_query = """
                    SELECT COUNT(DISTINCT user_id) as count
                    FROM users
                    WHERE last_activity >= NOW() - INTERVAL '7 days'
                """
                week_active = self.query(week_query)[0]["count"]
            else:
                week_active = 0 # Should not happen
            
            # Активные пользователи за последний месяц
            if self.db_type == "sqlite":
                month_query = """
                    SELECT COUNT(DISTINCT user_id) as count
                    FROM users
                    WHERE last_activity >= datetime('now', ?)
                """
                month_active = self.query(month_query, (f"-{days} days",))[0]["count"]
            elif self.db_type == "postgresql":
                month_query = """
                    SELECT COUNT(DISTINCT user_id) as count
                    FROM users
                    WHERE last_activity >= NOW() - INTERVAL %s
                """
                month_active = self.query(month_query, (f"{days} days",))[0]["count"]
            else:
                month_active = 0 # Should not happen
            
            # Расчет показателей удержания
            day_retention = round(day_active / total_users * 100, 2) if total_users > 0 else 0
            week_retention = round(week_active / total_users * 100, 2) if total_users > 0 else 0
            month_retention = round(month_active / total_users * 100, 2) if total_users > 0 else 0
            
            return {
                "total_users": total_users,
                "day_active": day_active,
                "week_active": week_active,
                "month_active": month_active,
                "day_retention": day_retention,
                "week_retention": week_retention,
                "month_retention": month_retention
            }
        
        except Exception as e:
            logger.error(f"Ошибка при получении статистики удержания: {e}")
            return {
                "total_users": 0,
                "day_active": 0,
                "week_active": 0,
                "month_active": 0,
                "day_retention": 0,
                "week_retention": 0,
                "month_retention": 0
            }
        
        finally:
            self.disconnect()
