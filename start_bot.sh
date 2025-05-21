#!/bin/bash
cd /root/telegram_bot
source venv/bin/activate

# Установка переменных окружения
export TOKEN="ваш_токен_от_botfather"
export ADMIN_USER_ID="ваш_id_пользователя"

python3 psihotips_bot_updated_v6.py
