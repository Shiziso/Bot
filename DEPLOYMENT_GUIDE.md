# Руководство по развертыванию телеграм-бота на VDS сервере Ubuntu

Это подробное руководство поможет вам развернуть телеграм-бота на удаленном VDS сервере под управлением Ubuntu. Инструкция предназначена для новичков и содержит все необходимые шаги от подготовки сервера до настройки автоматического запуска и мониторинга.

## Содержание

1. [Подготовка VDS сервера](#1-подготовка-vds-сервера)
2. [Установка необходимого ПО](#2-установка-необходимого-по)
3. [Настройка PostgreSQL](#3-настройка-postgresql)
4. [Клонирование и настройка бота](#4-клонирование-и-настройка-бота)
5. [Настройка переменных окружения](#5-настройка-переменных-окружения)
6. [Создание и настройка базы данных](#6-создание-и-настройка-базы-данных)
7. [Настройка автозапуска с помощью systemd](#7-настройка-автозапуска-с-помощью-systemd)
8. [Настройка логирования](#8-настройка-логирования)
9. [Настройка резервного копирования](#9-настройка-резервного-копирования)
10. [Мониторинг и обслуживание](#10-мониторинг-и-обслуживание)
11. [Обновление бота](#11-обновление-бота)
12. [Решение проблем](#12-решение-проблем)

## 1. Подготовка VDS сервера

### 1.1. Подключение к серверу

Для подключения к серверу используйте SSH. В Windows можно использовать PuTTY, в macOS и Linux - встроенный терминал.

```bash
ssh username@your_server_ip
```

Замените `username` на имя вашего пользователя, а `your_server_ip` на IP-адрес вашего сервера.

### 1.2. Обновление системы

После подключения к серверу обновите систему:

```bash
sudo apt update
sudo apt upgrade -y
```

### 1.3. Настройка временной зоны

Установите правильную временную зону:

```bash
sudo timedatectl set-timezone Europe/Moscow  # Замените на вашу временную зону
```

### 1.4. Настройка файрвола

Настройте файрвол для защиты сервера:

```bash
sudo apt install -y ufw
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw enable
```

## 2. Установка необходимого ПО

### 2.1. Установка Python и pip

```bash
sudo apt install -y python3 python3-pip python3-venv
```

### 2.2. Установка Git

```bash
sudo apt install -y git
```

### 2.3. Установка дополнительных пакетов

```bash
sudo apt install -y build-essential libssl-dev libffi-dev python3-dev
```

## 3. Настройка PostgreSQL

### 3.1. Установка PostgreSQL

```bash
sudo apt install -y postgresql postgresql-contrib
```

### 3.2. Запуск и включение автозапуска PostgreSQL

```bash
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### 3.3. Создание пользователя и базы данных

```bash
sudo -u postgres psql -c "CREATE USER botuser WITH PASSWORD 'your_strong_password';"
sudo -u postgres psql -c "CREATE DATABASE telegram_bot OWNER botuser;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE telegram_bot TO botuser;"
```

Замените `'your_strong_password'` на надежный пароль.

### 3.4. Настройка доступа к PostgreSQL

Отредактируйте файл конфигурации PostgreSQL для разрешения подключений:

```bash
sudo nano /etc/postgresql/*/main/pg_hba.conf
```

Добавьте следующую строку перед существующими строками с `host`:

```
host    telegram_bot    botuser    127.0.0.1/32    md5
```

Затем отредактируйте файл `postgresql.conf`:

```bash
sudo nano /etc/postgresql/*/main/postgresql.conf
```

Найдите строку `#listen_addresses = 'localhost'` и измените её на:

```
listen_addresses = 'localhost'
```

Перезапустите PostgreSQL:

```bash
sudo systemctl restart postgresql
```

## 4. Клонирование и настройка бота

### 4.1. Создание пользователя для бота

Рекомендуется создать отдельного пользователя для запуска бота:

```bash
sudo adduser botuser
sudo usermod -aG sudo botuser
```

Следуйте инструкциям для создания пароля и дополнительной информации.

### 4.2. Переключение на нового пользователя

```bash
su - botuser
```

### 4.3. Создание директории для бота

```bash
mkdir -p ~/telegram_bot
cd ~/telegram_bot
```

### 4.4. Копирование файлов бота

Вы можете скопировать файлы бота на сервер с помощью SCP или SFTP. Например, с локального компьютера:

```bash
# Выполните эту команду на локальном компьютере, не на сервере
scp -r /path/to/your/bot/* botuser@your_server_ip:~/telegram_bot/
```

Или вы можете клонировать репозиторий, если бот хранится в Git:

```bash
git clone https://github.com/your_username/your_bot_repo.git ~/telegram_bot
```

### 4.5. Создание виртуального окружения

```bash
cd ~/telegram_bot
python3 -m venv venv
source venv/bin/activate
```

### 4.6. Установка зависимостей

```bash
pip install -r requirements.txt
```

## 5. Настройка переменных окружения

### 5.1. Создание файла .env

```bash
nano ~/telegram_bot/.env
```

### 5.2. Добавление переменных окружения

Добавьте следующие строки в файл `.env`:

```
BOT_TOKEN=your_bot_token_from_botfather
ADMIN_USER_ID=your_telegram_user_id

DB_TYPE=postgresql
DB_HOST=localhost
DB_PORT=5432
DB_NAME=telegram_bot
DB_USER=botuser
DB_PASSWORD=your_strong_password
```

Замените значения на ваши собственные:
- `your_bot_token_from_botfather` - токен, полученный от @BotFather в Telegram
- `your_telegram_user_id` - ваш ID пользователя в Telegram (можно узнать у @userinfobot)
- `your_strong_password` - пароль, который вы установили для пользователя базы данных

Сохраните файл, нажав Ctrl+O, затем Enter, и выйдите с помощью Ctrl+X.

### 5.3. Настройка прав доступа к файлу .env

```bash
chmod 600 ~/telegram_bot/.env
```

## 6. Создание и настройка базы данных

### 6.1. Инициализация базы данных

```bash
cd ~/telegram_bot
source venv/bin/activate
psql -h localhost -U botuser -d telegram_bot -f db_schema.sql
```

Введите пароль, который вы установили для пользователя `botuser`.

## 7. Настройка автозапуска с помощью systemd

### 7.1. Создание файла службы systemd

```bash
sudo nano /etc/systemd/system/telegram-bot.service
```

### 7.2. Добавление конфигурации службы

```
[Unit]
Description=Telegram Bot Service
After=network.target postgresql.service

[Service]
User=botuser
Group=botuser
WorkingDirectory=/home/botuser/telegram_bot
Environment="PATH=/home/botuser/telegram_bot/venv/bin"
ExecStart=/home/botuser/telegram_bot/venv/bin/python updated_main.py
Restart=always
RestartSec=5
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=telegram-bot

[Install]
WantedBy=multi-user.target
```

Сохраните файл, нажав Ctrl+O, затем Enter, и выйдите с помощью Ctrl+X.

### 7.3. Перезагрузка systemd и включение службы

```bash
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot.service
sudo systemctl start telegram-bot.service
```

### 7.4. Проверка статуса службы

```bash
sudo systemctl status telegram-bot.service
```

## 8. Настройка логирования

### 8.1. Создание директории для логов

```bash
sudo mkdir -p /var/log/telegram-bot
sudo chown botuser:botuser /var/log/telegram-bot
```

### 8.2. Настройка rsyslog для бота

```bash
sudo nano /etc/rsyslog.d/telegram-bot.conf
```

Добавьте следующие строки:

```
if $programname == 'telegram-bot' then /var/log/telegram-bot/bot.log
& stop
```

Сохраните файл и перезапустите rsyslog:

```bash
sudo systemctl restart rsyslog
```

### 8.3. Настройка ротации логов

```bash
sudo nano /etc/logrotate.d/telegram-bot
```

Добавьте следующие строки:

```
/var/log/telegram-bot/bot.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 640 botuser botuser
}
```

Сохраните файл.

## 9. Настройка резервного копирования

### 9.1. Создание директории для резервных копий

```bash
mkdir -p ~/backups
```

### 9.2. Создание скрипта резервного копирования

```bash
nano ~/backup_bot.sh
```

Добавьте следующий код:

```bash
#!/bin/bash

# Настройки
BACKUP_DIR="/home/botuser/backups"
DB_NAME="telegram_bot"
DB_USER="botuser"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BOT_DIR="/home/botuser/telegram_bot"

# Создание директории для текущей резервной копии
BACKUP_PATH="${BACKUP_DIR}/${TIMESTAMP}"
mkdir -p $BACKUP_PATH

# Резервное копирование базы данных
PGPASSWORD="your_strong_password" pg_dump -h localhost -U $DB_USER $DB_NAME > "${BACKUP_PATH}/database.sql"

# Резервное копирование файлов бота
tar -czf "${BACKUP_PATH}/bot_files.tar.gz" -C $BOT_DIR .

# Удаление старых резервных копий (оставляем последние 7)
cd $BACKUP_DIR
ls -t | tail -n +8 | xargs -r rm -rf

echo "Резервное копирование завершено: ${BACKUP_PATH}"
```

Замените `your_strong_password` на пароль пользователя базы данных.

Сделайте скрипт исполняемым:

```bash
chmod +x ~/backup_bot.sh
```

### 9.3. Настройка автоматического резервного копирования с помощью cron

```bash
crontab -e
```

Добавьте следующую строку для ежедневного резервного копирования в 3:00:

```
0 3 * * * /home/botuser/backup_bot.sh >> /home/botuser/backups/backup.log 2>&1
```

## 10. Мониторинг и обслуживание

### 10.1. Просмотр логов

```bash
# Просмотр логов бота
tail -f /var/log/telegram-bot/bot.log

# Просмотр логов systemd
sudo journalctl -u telegram-bot.service -f
```

### 10.2. Перезапуск бота

```bash
sudo systemctl restart telegram-bot.service
```

### 10.3. Проверка использования ресурсов

```bash
# Проверка использования CPU и памяти
top

# Проверка использования диска
df -h
```

## 11. Обновление бота

### 11.1. Остановка службы

```bash
sudo systemctl stop telegram-bot.service
```

### 11.2. Обновление файлов

Если вы используете Git:

```bash
cd ~/telegram_bot
git pull
```

Или скопируйте новые файлы через SCP/SFTP.

### 11.3. Обновление зависимостей

```bash
cd ~/telegram_bot
source venv/bin/activate
pip install -r requirements.txt
```

### 11.4. Обновление базы данных (если необходимо)

```bash
psql -h localhost -U botuser -d telegram_bot -f update_schema.sql
```

### 11.5. Перезапуск службы

```bash
sudo systemctl start telegram-bot.service
```

## 12. Решение проблем

### 12.1. Бот не запускается

Проверьте статус службы:

```bash
sudo systemctl status telegram-bot.service
```

Проверьте логи:

```bash
tail -f /var/log/telegram-bot/bot.log
sudo journalctl -u telegram-bot.service -n 50
```

### 12.2. Проблемы с базой данных

Проверьте подключение к базе данных:

```bash
psql -h localhost -U botuser -d telegram_bot -c "SELECT 1;"
```

### 12.3. Проблемы с правами доступа

Проверьте права доступа к файлам:

```bash
ls -la ~/telegram_bot/
```

Исправьте права доступа при необходимости:

```bash
chmod -R 750 ~/telegram_bot/
chmod 600 ~/telegram_bot/.env
```

## Команды администратора для статистики

После успешного развертывания бота, администратор может использовать следующие команды для получения статистики:

- `/stats` - Общая статистика бота с выбором периода
- `/active_users [дней]` - Список активных пользователей за указанный период
- `/commands_stats [дней]` - Статистика использования команд за указанный период

Эти команды доступны только пользователю, чей ID указан в переменной окружения `ADMIN_USER_ID`.

## Заключение

Поздравляем! Теперь ваш телеграм-бот успешно развернут на VDS сервере Ubuntu и настроен для стабильной работы. Регулярно проверяйте логи и обновляйте бота для обеспечения его безопасности и стабильности.

Если у вас возникнут вопросы или проблемы, обратитесь к документации или свяжитесь с разработчиком бота.
