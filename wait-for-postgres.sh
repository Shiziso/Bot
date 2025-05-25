
#!/bin/bash
set -e

# Цвета для вывода сообщений
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Функция для вывода сообщений с временной меткой
log() {
  local level=$1
  local message=$2
  local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
  
  case $level in
    "INFO")
      echo -e "${GREEN}[INFO]${NC} $timestamp - $message"
      ;;
    "WARN")
      echo -e "${YELLOW}[WARN]${NC} $timestamp - $message"
      ;;
    "ERROR")
      echo -e "${RED}[ERROR]${NC} $timestamp - $message"
      ;;
    *)
      echo "$timestamp - $message"
      ;;
  esac
}

# Получение переменных окружения для подключения к PostgreSQL с проверкой наличия
DB_HOST=${DB_HOST:-postgres}
DB_PORT=${DB_PORT:-5432}
DB_USER=${DB_USER:-botuser}
DB_PASSWORD=${DB_PASSWORD:-Ihavepipilo963}
DB_NAME=${DB_NAME:-telegram_bot}

# Проверка наличия критичных переменных окружения
if [ -z "$DB_PASSWORD" ]; then
  log "ERROR" "DB_PASSWORD не задан. Пожалуйста, укажите пароль для базы данных."
  exit 1
fi

# Проверка наличия psql
if ! command -v psql &> /dev/null; then
  log "ERROR" "Команда psql не найдена. Установите postgresql-client."
  exit 1
fi

log "INFO" "Ожидание доступности PostgreSQL на $DB_HOST:$DB_PORT..."

# Счетчик попыток
attempt=1
max_attempts=30
retry_interval=2

# Ожидание доступности PostgreSQL с передачей пароля через переменную окружения
until PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c '\q' > /dev/null 2>&1; do
  if [ $attempt -ge $max_attempts ]; then
    log "ERROR" "PostgreSQL недоступен после $max_attempts попыток. Проверьте настройки подключения и состояние сервера."
    exit 1
  fi
  
  log "WARN" "PostgreSQL недоступен (попытка $attempt/$max_attempts) - ожидание $retry_interval сек."
  sleep $retry_interval
  attempt=$((attempt+1))
done

log "INFO" "PostgreSQL доступен! Проверка структуры базы данных..."

# Проверка наличия основных таблиц (опционально)
tables_count=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';" | tr -d ' ')

if [ "$tables_count" -eq "0" ]; then
  log "WARN" "База данных пуста. Возможно, требуется инициализация схемы."
  
  # Проверка наличия файла схемы
  if [ -f "/app/db_schema.sql" ]; then
    log "INFO" "Найден файл схемы db_schema.sql. Выполняем инициализацию..."
    PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f /app/db_schema.sql
    log "INFO" "Инициализация схемы базы данных завершена."
  else
    log "WARN" "Файл схемы db_schema.sql не найден. Инициализация базы данных может потребоваться позже."
  fi
fi

log "INFO" "Проверка конфигурации Python..."

# Проверка наличия критичных файлов Python
for file in "/app/main.py" "/app/config.py" "/app/handlers.py"; do
  if [ ! -f "$file" ]; then
    log "ERROR" "Критичный файл $file не найден!"
    exit 1
  fi
done

# Проверка наличия директории для логов
if [ ! -d "/app/logs" ]; then
  log "INFO" "Создание директории для логов..."
  mkdir -p /app/logs
fi

log "INFO" "Все проверки пройдены. Запуск приложения..."

# Запуск команды, переданной в аргументах
exec "$@"
