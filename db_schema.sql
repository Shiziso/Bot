-- Схема базы данных для телеграм-бота психотерапевта
-- Создание таблиц для хранения данных пользователей, советов, тестов, настроений и вопросов

-- Таблица пользователей
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_blocked BOOLEAN DEFAULT FALSE
);

-- Таблица истории советов дня
CREATE TABLE IF NOT EXISTS daily_tips_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    tip_text TEXT NOT NULL,
    date_sent TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Таблица для хранения результатов тестов
CREATE TABLE IF NOT EXISTS test_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    test_type TEXT NOT NULL, -- 'MDQ', 'GAD-7', 'PHQ-9', 'PCL-5'
    score INTEGER,
    answers TEXT, -- JSON строка с ответами на вопросы
    interpretation TEXT, -- Интерпретация результата
    date_taken TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Таблица для отслеживания настроения
CREATE TABLE IF NOT EXISTS mood_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    mood_emoji TEXT, -- Эмодзи, представляющее настроение
    mood_text TEXT, -- Текстовое описание настроения
    notes TEXT, -- Дополнительные заметки пользователя
    date_recorded TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Таблица для отслеживания привычек
CREATE TABLE IF NOT EXISTS habit_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    habit_name TEXT NOT NULL,
    date_recorded DATE,
    completed BOOLEAN DEFAULT FALSE,
    notes TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Таблица для анонимных вопросов
CREATE TABLE IF NOT EXISTS anonymous_questions (
    question_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    question_text TEXT NOT NULL,
    answer_text TEXT,
    status TEXT DEFAULT '❗️', -- '❗️' для неотвеченных, '✅' для отвеченных
    date_asked TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_answered TIMESTAMP,
    is_public BOOLEAN DEFAULT FALSE, -- Флаг для публикации в FAQ
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Таблица для пользовательских настроек
CREATE TABLE IF NOT EXISTS user_settings (
    user_id INTEGER PRIMARY KEY,
    daily_tip_time TEXT DEFAULT '09:00', -- Время для отправки ежедневного совета
    notifications_enabled BOOLEAN DEFAULT TRUE,
    language TEXT DEFAULT 'ru',
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Таблица для статистики использования бота
CREATE TABLE IF NOT EXISTS usage_statistics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    command TEXT,
    date_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Индексы для оптимизации запросов
CREATE INDEX IF NOT EXISTS idx_daily_tips_user_id ON daily_tips_history(user_id);
CREATE INDEX IF NOT EXISTS idx_test_results_user_id ON test_results(user_id);
CREATE INDEX IF NOT EXISTS idx_mood_tracking_user_id ON mood_tracking(user_id);
CREATE INDEX IF NOT EXISTS idx_habit_tracking_user_id ON habit_tracking(user_id);
CREATE INDEX IF NOT EXISTS idx_anonymous_questions_user_id ON anonymous_questions(user_id);
CREATE INDEX IF NOT EXISTS idx_anonymous_questions_status ON anonymous_questions(status);
CREATE INDEX IF NOT EXISTS idx_usage_statistics_user_id ON usage_statistics(user_id);
