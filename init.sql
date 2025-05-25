
-- Инициализация базы данных
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS user_sessions (
    session_id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id),
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    session_data JSONB
);

CREATE TABLE IF NOT EXISTS user_stats (
    stat_id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id),
    stat_date DATE DEFAULT CURRENT_DATE,
    commands_used INTEGER DEFAULT 0,
    messages_sent INTEGER DEFAULT 0,
    tests_completed INTEGER DEFAULT 0,
    techniques_viewed INTEGER DEFAULT 0
);
