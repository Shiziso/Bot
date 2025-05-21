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
            self.execute('''
                CREATE TABLE IF NOT EXISTS command_logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    command TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
            
            # Создаем таблицу ежедневных советов
            self.execute('''
                CREATE TABLE IF NOT EXISTS daily_tips (
                    tip_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    tip_text TEXT,
                    date_sent TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
            
            # Создаем таблицу анонимных вопросов
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
            
            # Создаем таблицу результатов тестов
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
            
            # Создаем таблицу отслеживания настроения
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
            existing_user = self.query("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            
            if existing_user:
                # Обновляем информацию о пользователе
                self.execute(
                    "UPDATE users SET username = ?, first_name = ?, last_name = ? WHERE user_id = ?",
                    (username, first_name, last_name, user_id)
                )
                logger.info(f"Обновлена информация о пользователе {user_id}")
            else:
                # Регистрируем нового пользователя
                self.execute(
                    "INSERT INTO users (user_id, username, first_name, last_name) VALUES (?, ?, ?, ?)",
                    (user_id, username, first_name, last_name)
                )
                
                # Создаем настройки по умолчанию
                self.execute(
                    "INSERT INTO user_settings (user_id) VALUES (?)",
                    (user_id,)
                )
                
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
            
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            self.execute(
                "UPDATE users SET last_activity = ? WHERE user_id = ?",
                (current_time, user_id)
            )
            
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
            
            self.execute(
                "INSERT INTO command_logs (user_id, command) VALUES (?, ?)",
                (user_id, command)
            )
            
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
            
            self.execute(
                "INSERT INTO daily_tips (user_id, tip_text) VALUES (?, ?)",
                (user_id, tip_text)
            )
            
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
            
            tips = self.query(
                "SELECT tip_id, tip_text, date_sent FROM daily_tips WHERE user_id = ? ORDER BY date_sent DESC LIMIT ?",
                (user_id, limit)
            )
            
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
                self.execute(
                    "INSERT INTO anonymous_questions (user_id, question_text) VALUES (?, ?)",
                    (user_id, question_text)
                )
                
                # Получаем ID последней вставленной записи
                question_id = self.query("SELECT last_insert_rowid() as id")[0]["id"]
            
            elif self.db_type == "postgresql":
                result = self.query(
                    "INSERT INTO anonymous_questions (user_id, question_text) VALUES (%s, %s) RETURNING question_id",
                    (user_id, question_text)
                )
                question_id = result[0]["question_id"]
            
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
            
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            from config import NOTIFICATION_SETTINGS
            
            self.execute(
                "UPDATE anonymous_questions SET answer_text = ?, status = ?, date_answered = ? WHERE question_id = ?",
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
            Словарь с информацией о вопросе или None в случае ошибки
        """
        try:
            self.connect()
            
            questions = self.query(
                "SELECT * FROM anonymous_questions WHERE question_id = ?",
                (question_id,)
            )
            
            if questions:
                return questions[0]
            else:
                return None
        
        except Exception as e:
            logger.error(f"Ошибка при получении информации о вопросе: {e}")
            return None
        
        finally:
            self.disconnect()
    
    def get_user_questions(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Получает список вопросов пользователя
        
        Args:
            user_id: ID пользователя в Telegram
            
        Returns:
            Список словарей с информацией о вопросах
        """
        try:
            self.connect()
            
            questions = self.query(
                "SELECT * FROM anonymous_questions WHERE user_id = ? ORDER BY date_asked DESC",
                (user_id,)
            )
            
            return questions
        
        except Exception as e:
            logger.error(f"Ошибка при получении вопросов пользователя: {e}")
            return []
        
        finally:
            self.disconnect()
    
    def get_unanswered_questions(self) -> List[Dict[str, Any]]:
        """
        Получает список неотвеченных вопросов
        
        Returns:
            Список словарей с информацией о вопросах
        """
        try:
            self.connect()
            
            from config import NOTIFICATION_SETTINGS
            
            questions = self.query(
                "SELECT * FROM anonymous_questions WHERE status = ? ORDER BY date_asked ASC",
                (NOTIFICATION_SETTINGS["new_question_emoji"],)
            )
            
            return questions
        
        except Exception as e:
            logger.error(f"Ошибка при получении неотвеченных вопросов: {e}")
            return []
        
        finally:
            self.disconnect()
    
    def save_test_result(self, user_id: int, test_type: str, score: int, answers: Dict[int, str], interpretation: str) -> bool:
        """
        Сохраняет результат психологического теста
        
        Args:
            user_id: ID пользователя в Telegram
            test_type: Тип теста
            score: Общий балл
            answers: Словарь с ответами на вопросы
            interpretation: Интерпретация результата
            
        Returns:
            True, если операция выполнена успешно
        """
        try:
            self.connect()
            
            # Преобразуем словарь с ответами в JSON
            answers_json = json.dumps(answers)
            
            self.execute(
                "INSERT INTO test_results (user_id, test_type, score, answers, interpretation) VALUES (?, ?, ?, ?, ?)",
                (user_id, test_type, score, answers_json, interpretation)
            )
            
            logger.info(f"Сохранен результат теста {test_type} для пользователя {user_id}")
            
            return True
        
        except Exception as e:
            logger.error(f"Ошибка при сохранении результата теста: {e}")
            return False
        
        finally:
            self.disconnect()
    
    def get_user_test_history(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Получает историю тестов пользователя
        
        Args:
            user_id: ID пользователя в Telegram
            
        Returns:
            Список словарей с информацией о тестах
        """
        try:
            self.connect()
            
            tests = self.query(
                "SELECT * FROM test_results WHERE user_id = ? ORDER BY date_taken DESC",
                (user_id,)
            )
            
            # Преобразуем JSON с ответами обратно в словарь
            for test in tests:
                test["answers"] = json.loads(test["answers"])
            
            return tests
        
        except Exception as e:
            logger.error(f"Ошибка при получении истории тестов: {e}")
            return []
        
        finally:
            self.disconnect()
    
    def save_mood(self, user_id: int, mood_emoji: str, mood_text: str, notes: str = None) -> bool:
        """
        Сохраняет запись о настроении пользователя
        
        Args:
            user_id: ID пользователя в Telegram
            mood_emoji: Эмодзи настроения
            mood_text: Текстовое описание настроения
            notes: Заметки пользователя (опционально)
            
        Returns:
            True, если операция выполнена успешно
        """
        try:
            self.connect()
            
            self.execute(
                "INSERT INTO mood_tracking (user_id, mood_emoji, mood_text, notes) VALUES (?, ?, ?, ?)",
                (user_id, mood_emoji, mood_text, notes)
            )
            
            logger.info(f"Сохранена запись о настроении для пользователя {user_id}")
            
            return True
        
        except Exception as e:
            logger.error(f"Ошибка при сохранении записи о настроении: {e}")
            return False
        
        finally:
            self.disconnect()
    
    def get_user_mood_history(self, user_id: int, limit: int = 30) -> List[Dict[str, Any]]:
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
            
            moods = self.query(
                "SELECT * FROM mood_tracking WHERE user_id = ? ORDER BY date_recorded DESC LIMIT ?",
                (user_id, limit)
            )
            
            return moods
        
        except Exception as e:
            logger.error(f"Ошибка при получении истории настроения: {e}")
            return []
        
        finally:
            self.disconnect()
    
    def get_user_settings(self, user_id: int) -> Dict[str, Any]:
        """
        Получает настройки пользователя
        
        Args:
            user_id: ID пользователя в Telegram
            
        Returns:
            Словарь с настройками пользователя
        """
        try:
            self.connect()
            
            settings = self.query(
                "SELECT * FROM user_settings WHERE user_id = ?",
                (user_id,)
            )
            
            if settings:
                return settings[0]
            else:
                # Если настройки не найдены, создаем их с значениями по умолчанию
                self.execute(
                    "INSERT INTO user_settings (user_id) VALUES (?)",
                    (user_id,)
                )
                
                return {
                    "user_id": user_id,
                    "notifications_enabled": True,
                    "daily_tip_time": "09:00"
                }
        
        except Exception as e:
            logger.error(f"Ошибка при получении настроек пользователя: {e}")
            return {
                "user_id": user_id,
                "notifications_enabled": True,
                "daily_tip_time": "09:00"
            }
        
        finally:
            self.disconnect()
    
    def update_user_settings(self, user_id: int, settings: Dict[str, Any]) -> bool:
        """
        Обновляет настройки пользователя
        
        Args:
            user_id: ID пользователя в Telegram
            settings: Словарь с настройками для обновления
            
        Returns:
            True, если операция выполнена успешно
        """
        try:
            self.connect()
            
            # Формируем SQL-запрос для обновления только указанных настроек
            set_clauses = []
            params = []
            
            for key, value in settings.items():
                set_clauses.append(f"{key} = ?")
                params.append(value)
            
            # Добавляем user_id в конец параметров
            params.append(user_id)
            
            query = f"UPDATE user_settings SET {', '.join(set_clauses)} WHERE user_id = ?"
            
            self.execute(query, tuple(params))
            
            logger.info(f"Обновлены настройки пользователя {user_id}")
            
            return True
        
        except Exception as e:
            logger.error(f"Ошибка при обновлении настроек пользователя: {e}")
            return False
        
        finally:
            self.disconnect()
    
    def get_users_with_daily_tips(self) -> List[Dict[str, Any]]:
        """
        Получает список пользователей, которые включили ежедневные советы
        
        Returns:
            Список словарей с информацией о пользователях
        """
        try:
            self.connect()
            
            current_time = datetime.now().strftime("%H:%M")
            
            users = self.query(
                """
                SELECT u.user_id, u.username, u.first_name, u.last_name
                FROM users u
                JOIN user_settings s ON u.user_id = s.user_id
                WHERE s.notifications_enabled = ? AND s.daily_tip_time = ?
                """,
                (True, current_time)
            )
            
            return users
        
        except Exception as e:
            logger.error(f"Ошибка при получении пользователей для ежедневных советов: {e}")
            return []
        
        finally:
            self.disconnect()
    
    def backup_database(self) -> bool:
        """
        Создает резервную копию базы данных
        
        Returns:
            True, если операция выполнена успешно
        """
        try:
            if self.db_type == "sqlite":
                import shutil
                
                # Создаем директорию для резервных копий, если она не существует
                backup_dir = "backups"
                os.makedirs(backup_dir, exist_ok=True)
                
                # Формируем имя файла резервной копии
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = os.path.join(backup_dir, f"backup_{timestamp}.db")
                
                # Копируем файл базы данных
                shutil.copy2(DATABASE["sqlite_path"], backup_file)
                
                logger.info(f"Создана резервная копия базы данных: {backup_file}")
                
                # Удаляем старые резервные копии (оставляем последние 5)
                backup_files = sorted([os.path.join(backup_dir, f) for f in os.listdir(backup_dir)])
                if len(backup_files) > 5:
                    for old_file in backup_files[:-5]:
                        os.remove(old_file)
                        logger.info(f"Удалена старая резервная копия: {old_file}")
            
            elif self.db_type == "postgresql":
                # Для PostgreSQL можно использовать pg_dump
                # Этот код требует наличия утилиты pg_dump и соответствующих прав
                import subprocess
                
                # Создаем директорию для резервных копий, если она не существует
                backup_dir = "backups"
                os.makedirs(backup_dir, exist_ok=True)
                
                # Формируем имя файла резервной копии
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = os.path.join(backup_dir, f"backup_{timestamp}.sql")
                
                # Формируем команду для pg_dump
                pg_config = DATABASE["postgresql"]
                cmd = [
                    "pg_dump",
                    f"--host={pg_config['host']}",
                    f"--port={pg_config['port']}",
                    f"--username={pg_config['user']}",
                    f"--dbname={pg_config['database']}",
                    f"--file={backup_file}"
                ]
                
                # Устанавливаем переменную окружения для пароля
                env = os.environ.copy()
                env["PGPASSWORD"] = pg_config["password"]
                
                # Выполняем команду
                subprocess.run(cmd, env=env, check=True)
                
                logger.info(f"Создана резервная копия базы данных: {backup_file}")
                
                # Удаляем старые резервные копии (оставляем последние 5)
                backup_files = sorted([os.path.join(backup_dir, f) for f in os.listdir(backup_dir)])
                if len(backup_files) > 5:
                    for old_file in backup_files[:-5]:
                        os.remove(old_file)
                        logger.info(f"Удалена старая резервная копия: {old_file}")
            
            return True
        
        except Exception as e:
            logger.error(f"Ошибка при создании резервной копии базы данных: {e}")
            return False
