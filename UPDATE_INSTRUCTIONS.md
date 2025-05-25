# Инструкция по обновлению телеграм-бота на сервере

Данная инструкция предназначена для обновления телеграм-бота, запущенного в Docker-контейнере на VDS сервере Ubuntu. Обновление устраняет проблемы совместимости с PostgreSQL и восстанавливает полную функциональность бота.

## 1. Подготовка к обновлению

### 1.1. Создание резервной копии

Перед обновлением рекомендуется создать резервную копию текущей версии бота и базы данных:

```bash
# Подключитесь к серверу по SSH
ssh пользователь@адрес_сервера

# Создайте резервную копию директории с ботом
cd ~/telegram_bot_docker
cp -r updated_bot updated_bot_backup

# Создайте резервную копию базы данных PostgreSQL
docker exec postgres pg_dump -U postgres -d имя_базы_данных > backup_$(date +%Y%m%d).sql
```

## 2. Обновление файлов бота

### 2.1. Загрузка обновленных файлов на сервер

```bash
# Создайте временную директорию для обновления
mkdir -p ~/telegram_bot_update

# Загрузите архив с обновленной версией бота на сервер
# (Выполните эту команду на локальном компьютере)
scp /путь/к/telegram_bot_fix.zip пользователь@адрес_сервера:~/telegram_bot_update/
```

### 2.2. Распаковка и установка обновленных файлов

```bash
# Перейдите в директорию с обновлением
cd ~/telegram_bot_update

# Распакуйте архив
unzip telegram_bot_fix.zip

# Остановите контейнеры
cd ~/telegram_bot_docker
docker-compose down

# Замените файлы бота обновленными версиями
cp -r ~/telegram_bot_update/telegram_bot_fix/* ~/telegram_bot_docker/updated_bot/

# Убедитесь, что файлы имеют правильные права доступа
chmod -R 755 ~/telegram_bot_docker/updated_bot/
```

## 3. Обновление схемы базы данных

### 3.1. Создание скрипта миграции

Создайте файл с SQL-скриптом для обновления схемы базы данных:

```bash
cat > ~/telegram_bot_docker/db_migration.sql << 'EOF'
-- Обновление таблицы command_logs
ALTER TABLE command_logs ALTER COLUMN log_id DROP DEFAULT;
DROP SEQUENCE IF EXISTS command_logs_log_id_seq;
CREATE SEQUENCE command_logs_log_id_seq OWNED BY command_logs.log_id;
ALTER TABLE command_logs ALTER COLUMN log_id SET DEFAULT nextval('command_logs_log_id_seq');
SELECT setval('command_logs_log_id_seq', COALESCE((SELECT MAX(log_id) FROM command_logs), 1), false);

-- Обновление таблицы daily_tips
ALTER TABLE daily_tips ALTER COLUMN tip_id DROP DEFAULT;
DROP SEQUENCE IF EXISTS daily_tips_tip_id_seq;
CREATE SEQUENCE daily_tips_tip_id_seq OWNED BY daily_tips.tip_id;
ALTER TABLE daily_tips ALTER COLUMN tip_id SET DEFAULT nextval('daily_tips_tip_id_seq');
SELECT setval('daily_tips_tip_id_seq', COALESCE((SELECT MAX(tip_id) FROM daily_tips), 1), false);

-- Обновление таблицы anonymous_questions
ALTER TABLE anonymous_questions ALTER COLUMN question_id DROP DEFAULT;
DROP SEQUENCE IF EXISTS anonymous_questions_question_id_seq;
CREATE SEQUENCE anonymous_questions_question_id_seq OWNED BY anonymous_questions.question_id;
ALTER TABLE anonymous_questions ALTER COLUMN question_id SET DEFAULT nextval('anonymous_questions_question_id_seq');
SELECT setval('anonymous_questions_question_id_seq', COALESCE((SELECT MAX(question_id) FROM anonymous_questions), 1), false);

-- Обновление таблицы test_results
ALTER TABLE test_results ALTER COLUMN result_id DROP DEFAULT;
DROP SEQUENCE IF EXISTS test_results_result_id_seq;
CREATE SEQUENCE test_results_result_id_seq OWNED BY test_results.result_id;
ALTER TABLE test_results ALTER COLUMN result_id SET DEFAULT nextval('test_results_result_id_seq');
SELECT setval('test_results_result_id_seq', COALESCE((SELECT MAX(result_id) FROM test_results), 1), false);

-- Обновление таблицы mood_tracking
ALTER TABLE mood_tracking ALTER COLUMN mood_id DROP DEFAULT;
DROP SEQUENCE IF EXISTS mood_tracking_mood_id_seq;
CREATE SEQUENCE mood_tracking_mood_id_seq OWNED BY mood_tracking.mood_id;
ALTER TABLE mood_tracking ALTER COLUMN mood_id SET DEFAULT nextval('mood_tracking_mood_id_seq');
SELECT setval('mood_tracking_mood_id_seq', COALESCE((SELECT MAX(mood_id) FROM mood_tracking), 1), false);

-- Создание таблицы usage_statistics, если она не существует
CREATE TABLE IF NOT EXISTS usage_statistics (
    stat_id SERIAL PRIMARY KEY,
    user_id INTEGER,
    feature TEXT,
    usage_count INTEGER DEFAULT 1,
    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
EOF
```

### 3.2. Применение миграции к базе данных

```bash
# Запустите только контейнер с PostgreSQL
docker-compose up -d postgres

# Подождите несколько секунд, чтобы PostgreSQL полностью запустился
sleep 10

# Примените миграцию
docker exec -i postgres psql -U postgres -d имя_базы_данных < ~/telegram_bot_docker/db_migration.sql
```

## 4. Обновление Docker-конфигурации

### 4.1. Создание скрипта ожидания для PostgreSQL

Создайте скрипт, который будет ожидать полной инициализации PostgreSQL перед запуском бота:

```bash
cat > ~/telegram_bot_docker/wait-for-postgres.sh << 'EOF'
#!/bin/bash
# wait-for-postgres.sh

set -e

host="$1"
shift
cmd="$@"

until PGPASSWORD=$DB_PASSWORD psql -h "postgres" -U "$DB_USER" -d "$DB_NAME" -c '\q'; do
  >&2 echo "Postgres is unavailable - sleeping"
  sleep 1
done

>&2 echo "Postgres is up - executing command"
exec $cmd
EOF

# Сделайте скрипт исполняемым
chmod +x ~/telegram_bot_docker/wait-for-postgres.sh
```

### 4.2. Обновление Dockerfile

Обновите Dockerfile, чтобы использовать скрипт ожидания:

```bash
cat > ~/telegram_bot_docker/Dockerfile << 'EOF'
FROM python:3.9-slim

WORKDIR /app

COPY updated_bot/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY updated_bot/ .
COPY wait-for-postgres.sh .

RUN chmod +x /app/wait-for-postgres.sh

CMD ["/app/wait-for-postgres.sh", "postgres:5432", "--", "python", "updated_main.py"]
EOF
```

## 5. Перезапуск и проверка

### 5.1. Пересборка и запуск контейнеров

```bash
# Пересоберите образ бота
docker-compose build

# Запустите все контейнеры
docker-compose up -d

# Проверьте логи на наличие ошибок
docker-compose logs -f
```

### 5.2. Проверка функциональности

После успешного запуска проверьте основные функции бота:

1. Отправьте команду `/start` боту
2. Проверьте работу кнопок и меню
3. Попробуйте пройти тест
4. Проверьте функцию отслеживания настроения
5. Проверьте техники самопомощи
6. Проверьте функцию вопросов
7. Если вы администратор, проверьте команды статистики:
   - `/stats` - общая статистика
   - `/active_users` - активные пользователи
   - `/commands_stats` - статистика использования команд

## 6. Устранение возможных проблем

### 6.1. Проблемы с подключением к базе данных

Если бот не может подключиться к базе данных:

```bash
# Проверьте, запущен ли контейнер с PostgreSQL
docker ps | grep postgres

# Проверьте логи PostgreSQL
docker-compose logs postgres

# Проверьте переменные окружения в docker-compose.yml
cat ~/telegram_bot_docker/docker-compose.yml
```

### 6.2. Проблемы с синтаксисом SQL

Если возникают ошибки синтаксиса SQL:

```bash
# Проверьте логи бота
docker-compose logs telegram_bot

# Если видите ошибки, связанные с AUTOINCREMENT, выполните дополнительную миграцию
cat > ~/telegram_bot_docker/fix_autoincrement.sql << 'EOF'
-- Найти все таблицы с AUTOINCREMENT и исправить их
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN SELECT table_name, column_name
             FROM information_schema.columns
             WHERE table_schema = 'public'
             AND column_default LIKE '%AUTOINCREMENT%'
    LOOP
        EXECUTE format('ALTER TABLE %I ALTER COLUMN %I DROP DEFAULT', r.table_name, r.column_name);
        EXECUTE format('DROP SEQUENCE IF EXISTS %I_%I_seq', r.table_name, r.column_name);
        EXECUTE format('CREATE SEQUENCE %I_%I_seq OWNED BY %I.%I', r.table_name, r.column_name, r.table_name, r.column_name);
        EXECUTE format('ALTER TABLE %I ALTER COLUMN %I SET DEFAULT nextval(''%I_%I_seq'')', r.table_name, r.column_name, r.table_name, r.column_name);
        EXECUTE format('SELECT setval(''%I_%I_seq'', COALESCE((SELECT MAX(%I) FROM %I), 1), false)', r.table_name, r.column_name, r.column_name, r.table_name);
    END LOOP;
END $$;
EOF

docker exec -i postgres psql -U postgres -d имя_базы_данных < ~/telegram_bot_docker/fix_autoincrement.sql

# Перезапустите бота
docker-compose restart telegram_bot
```

## 7. Дополнительные рекомендации

### 7.1. Регулярное резервное копирование

Настройте регулярное резервное копирование базы данных:

```bash
# Создайте скрипт для резервного копирования
cat > ~/telegram_bot_docker/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR=~/telegram_bot_backups
mkdir -p $BACKUP_DIR
FILENAME=backup_$(date +%Y%m%d_%H%M%S).sql
docker exec postgres pg_dump -U postgres -d имя_базы_данных > $BACKUP_DIR/$FILENAME
# Удаляем бэкапы старше 30 дней
find $BACKUP_DIR -name "backup_*.sql" -type f -mtime +30 -delete
EOF

chmod +x ~/telegram_bot_docker/backup.sh

# Добавьте задание в crontab для ежедневного резервного копирования
(crontab -l 2>/dev/null; echo "0 3 * * * ~/telegram_bot_docker/backup.sh") | crontab -
```

### 7.2. Мониторинг работы бота

Для мониторинга работы бота можно использовать простой скрипт:

```bash
cat > ~/telegram_bot_docker/monitor.sh << 'EOF'
#!/bin/bash
if ! docker ps | grep -q telegram_bot; then
  echo "Бот не запущен! Перезапускаю..."
  cd ~/telegram_bot_docker && docker-compose up -d
  # Отправка уведомления (опционально)
  # curl -s -X POST https://api.telegram.org/bot$BOT_TOKEN/sendMessage -d chat_id=$ADMIN_ID -d text="Бот был перезапущен автоматически"
fi
EOF

chmod +x ~/telegram_bot_docker/monitor.sh

# Добавьте задание в crontab для проверки каждые 5 минут
(crontab -l 2>/dev/null; echo "*/5 * * * * ~/telegram_bot_docker/monitor.sh") | crontab -
```

## 8. Заключение

После выполнения всех шагов ваш бот должен работать стабильно с PostgreSQL. Если у вас возникнут вопросы или проблемы, обратитесь к разработчику для получения дополнительной помощи.

Не забывайте регулярно обновлять систему и контейнеры для обеспечения безопасности и стабильности работы:

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Обновление образов Docker
docker-compose pull
docker-compose build --no-cache
docker-compose up -d
```
