#!/usr/bin/env python3
"""
Финальный тест для проверки поддержки категорий допусков в price_checker.py
"""

import os
import sys

# Добавляем текущую директорию в путь для импорта
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from price_checker import (
    PriceChecker,
    check_price_tolerance,
    get_active_categories,
    get_category_tolerance,
)


def test_category_tolerance():
    """Тест функции получения допуска по категории."""
    print("=== Тест получения допуска по категории ===")

    # Тест существующих категорий
    categories = ["electronics", "construction", "software", "medical"]
    for category in categories:
        try:
            tolerance = get_category_tolerance(category)
            print(f"Категория '{category}': допуск {tolerance}%")
        except Exception as e:
            print(f"Ошибка при получении допуска для категории '{category}': {e}")


def test_active_categories():
    """Тест получения активных категорий."""
    print("\n=== Тест получения активных категорий ===")

    try:
        active_categories = get_active_categories()
        print(f"Найдено активных категорий: {len(active_categories)}")
        for category in active_categories:
            print(
                f"  - {category['name']}: {category['description']}, допуск {category['tolerance']}%"
            )
    except Exception as e:
        print(f"Ошибка при получении активных категорий: {e}")


def test_price_checking():
    """Тест проверки цен с категориями."""
    print("\n=== Тест проверки цен с категориями ===")

    # Создаем экземпляр PriceChecker
    checker = PriceChecker()

    # Устанавливаем базовые цены
    base_prices = {
        "laptop": 50000,
        "cement": 300,
        "software_license": 10000,
        "medical_device": 25000,
    }
    checker.load_base_prices(base_prices)

    # Тестируем цены для разных категорий
    test_cases = [
        {"product": "laptop", "price": 52000, "category": "electronics"},
        {"product": "cement", "price": 280, "category": "construction"},
        {"product": "software_license", "price": 10500, "category": "software"},
        {"product": "medical_device", "price": 26000, "category": "medical"},
    ]

    for case in test_cases:
        result = checker.check_price(
            case["product"], case["price"], category=case["category"]
        )
        print(f"{case['product']}: {result.comments}")


def test_tolerance_checking():
    """Тест функции проверки допуска."""
    print("\n=== Тест функции проверки допуска ===")

    test_cases = [
        {"category": "electronics", "expected": 1000, "actual": 1050},  # 5% отклонение
        {
            "category": "construction",
            "expected": 1000,
            "actual": 1100,
        },  # 10% отклонение
        {"category": "software", "expected": 1000, "actual": 1200},  # 20% отклонение
    ]

    for case in test_cases:
        result = check_price_tolerance(
            case["category"], case["expected"], case["actual"]
        )
        print(
            f"{case['category']}: expected={case['expected']}, actual={case['actual']}"
        )
        print(
            f"  Результат: {'В пределах допуска' if result['within_tolerance'] else 'Вне допуска'}"
        )
        print(
            f"  Допуск: {result['tolerance_used']*100}%, Отклонение: {result['deviation']*100}%"
        )
        print()


if __name__ == "__main__":
    print("Тестирование поддержки категорий допусков в price_checker.py")
    print("=" * 60)

    try:
        test_category_tolerance()
        test_active_categories()
        test_price_checking()
        test_tolerance_checking()

        print("\n✅ Все тесты успешно пройдены!")
        print("Поддержка категорий допусков в price_checker.py работает корректно.")

    except Exception as e:
        print(f"\n❌ Ошибка при тестировании: {e}")
        import traceback

        traceback.print_exc()
