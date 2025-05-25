#!/bin/bash

# Остановка контейнеров, если они уже запущены
docker-compose down

# Сборка и запуск контейнеров
docker-compose up -d

# Вывод логов
echo "Бот запущен! Проверка логов..."
sleep 5
docker-compose logs telegram_bot
