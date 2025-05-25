#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для тестирования новых тестов и их интеграции
"""

import sys
import os
import json
from pprint import pprint

# Добавляем путь к директории бота
sys.path.append('/home/ubuntu/bot_analysis')

# Импортируем модули для тестирования
try:
    from data.new_tests import NEW_TESTS, NEW_TEST_CATEGORIES
    print("✅ Успешно импортированы новые тесты и категории")
except Exception as e:
    print(f"❌ Ошибка при импорте новых тестов: {e}")
    sys.exit(1)

def test_test_structure():
    """
    Проверяет структуру новых тестов
    """
    print("\n=== Тестирование структуры новых тестов ===")
    
    # Проверяем наличие всех категорий
    expected_categories = ["mood", "stress", "self", "specific"]
    for category in expected_categories:
        if category in NEW_TEST_CATEGORIES:
            print(f"✅ Категория '{category}' найдена")
        else:
            print(f"❌ Категория '{category}' не найдена")
    
    # Проверяем наличие всех тестов
    expected_tests = [
        "hads", "who5", "pss", "burnout", "panic", 
        "rosenberg", "procrastination", "coping", "sleep", "audit"
    ]
    for test in expected_tests:
        if test in NEW_TESTS:
            print(f"✅ Тест '{test}' найден")
        else:
            print(f"❌ Тест '{test}' не найден")
    
    # Проверяем структуру каждого теста
    for test_key, test_data in NEW_TESTS.items():
        print(f"\nПроверка структуры теста '{test_key}':")
        
        # Проверяем обязательные поля
        required_fields = ["name", "description", "time", "questions", "calculation_type"]
        for field in required_fields:
            if field in test_data:
                print(f"  ✅ Поле '{field}' присутствует")
            else:
                print(f"  ❌ Поле '{field}' отсутствует")
        
        # Проверяем структуру вопросов
        if "questions" in test_data and isinstance(test_data["questions"], list):
            print(f"  ✅ Найдено {len(test_data['questions'])} вопросов")
            
            # Проверяем первый вопрос
            if test_data["questions"]:
                question = test_data["questions"][0]
                question_fields = ["text", "answers", "scores"]
                for field in question_fields:
                    if field in question:
                        print(f"  ✅ Поле вопроса '{field}' присутствует")
                    else:
                        print(f"  ❌ Поле вопроса '{field}' отсутствует")
        else:
            print("  ❌ Поле 'questions' отсутствует или не является списком")
        
        # Проверяем интерпретации
        if "interpretations" in test_data:
            if isinstance(test_data["interpretations"], dict):
                print(f"  ✅ Найдены интерпретации для подшкал: {', '.join(test_data['interpretations'].keys())}")
            elif isinstance(test_data["interpretations"], list):
                print(f"  ✅ Найдено {len(test_data['interpretations'])} интерпретаций")
            else:
                print("  ❌ Поле 'interpretations' имеет неверный формат")
        else:
            print("  ❌ Поле 'interpretations' отсутствует")

def test_calculation_logic():
    """
    Тестирует логику расчета результатов тестов
    """
    print("\n=== Тестирование логики расчета результатов ===")
    
    # Тестируем обычный тест (sum)
    test_key = "who5"
    if test_key in NEW_TESTS:
        test_data = NEW_TESTS[test_key]
        print(f"\nТестирование расчета для теста '{test_key}' (тип: {test_data.get('calculation_type', 'sum')})")
        
        # Симулируем ответы пользователя (все максимальные баллы)
        answers = [0] * len(test_data["questions"])  # Индексы ответов с максимальными баллами
        
        # Рассчитываем ожидаемый результат
        expected_score = 0
        for i, answer_idx in enumerate(answers):
            expected_score += test_data["questions"][i]["scores"][answer_idx]
        
        print(f"  ✅ Ожидаемый результат при всех максимальных ответах: {expected_score}")
        
        # Определяем ожидаемую интерпретацию
        expected_interpretation = None
        for interp in test_data["interpretations"]:
            if expected_score >= interp["min_score"] and expected_score <= interp["max_score"]:
                expected_interpretation = interp
                break
        
        if expected_interpretation:
            print(f"  ✅ Ожидаемая интерпретация: {expected_interpretation['text'][:50]}...")
        else:
            print("  ❌ Не удалось определить интерпретацию для рассчитанного результата")
    
    # Тестируем тест с подшкалами (subscales)
    test_key = "hads"
    if test_key in NEW_TESTS:
        test_data = NEW_TESTS[test_key]
        print(f"\nТестирование расчета для теста '{test_key}' (тип: {test_data.get('calculation_type', 'sum')})")
        
        if test_data.get("calculation_type") == "subscales" and "subscales" in test_data:
            # Группируем вопросы по подшкалам
            subscale_questions = {}
            for subscale in test_data["subscales"]:
                subscale_questions[subscale] = [q for q in test_data["questions"] if q.get("subscale") == subscale]
            
            # Выводим информацию о подшкалах
            for subscale, questions in subscale_questions.items():
                print(f"  ✅ Подшкала '{subscale}': {len(questions)} вопросов")
            
            # Симулируем ответы пользователя (все максимальные баллы)
            subscale_scores = {}
            for subscale, questions in subscale_questions.items():
                subscale_score = 0
                for question in questions:
                    # Находим индекс ответа с максимальным баллом
                    max_score_idx = question["scores"].index(max(question["scores"]))
                    subscale_score += question["scores"][max_score_idx]
                
                subscale_scores[subscale] = subscale_score
                print(f"  ✅ Ожидаемый результат для подшкалы '{subscale}': {subscale_score}")
                
                # Определяем ожидаемую интерпретацию для подшкалы
                expected_interpretation = None
                for interp in test_data["interpretations"].get(subscale, []):
                    if subscale_score >= interp["min_score"] and subscale_score <= interp["max_score"]:
                        expected_interpretation = interp
                        break
                
                if expected_interpretation:
                    print(f"  ✅ Ожидаемая интерпретация для подшкалы '{subscale}': {expected_interpretation['text'][:50]}...")
                else:
                    print(f"  ❌ Не удалось определить интерпретацию для подшкалы '{subscale}'")
        else:
            print("  ❌ Тест не имеет подшкал или неверно настроен")

def test_integration():
    """
    Тестирует интеграцию новых тестов с существующим кодом
    """
    print("\n=== Тестирование интеграции с существующим кодом ===")
    
    # Проверяем наличие обновленных файлов
    required_files = [
        "/home/ubuntu/bot_analysis/data/new_tests.py",
        "/home/ubuntu/bot_analysis/updated_handlers.py",
        "/home/ubuntu/bot_analysis/updated_main.py"
    ]
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ Файл '{file_path}' существует")
        else:
            print(f"❌ Файл '{file_path}' не найден")
    
    # Проверяем импорт обновленных обработчиков
    try:
        sys.path.append('/home/ubuntu/bot_analysis')
        from updated_handlers import (
            test_command, show_test_categories, select_test,
            process_test_answer, show_test_question, calculate_test_result, show_test_result
        )
        print("✅ Успешно импортированы обновленные обработчики")
    except Exception as e:
        print(f"❌ Ошибка при импорте обновленных обработчиков: {e}")

def main():
    """
    Основная функция для запуска тестов
    """
    print("🔍 Начинаем тестирование новых тестов и их интеграции")
    
    # Тестируем структуру тестов
    test_test_structure()
    
    # Тестируем логику расчета
    test_calculation_logic()
    
    # Тестируем интеграцию
    test_integration()
    
    print("\n✅ Тестирование завершено")

if __name__ == "__main__":
    main()
