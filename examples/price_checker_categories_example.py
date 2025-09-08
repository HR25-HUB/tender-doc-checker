#!/usr/bin/env python3
"""
Пример использования системы проверки цен с категориями допусков.

Этот пример демонстрирует:
1. Использование категорий из новой системы конфигурации
2. Проверку цен с учетом категорий товаров
3. Получение информации о доступных категориях
4. Сравнение результатов с категориями и без них
"""

import json
from decimal import Decimal

from src.config import add_custom_category, save_config
from src.price_checker import PriceChecker, check_price_tolerance, get_active_categories


def main():
    """Основная функция примера."""
    print("=== Пример использования системы проверки цен с категориями ===\n")

    # 1. Получение списка активных категорий
    print("1. Активные категории:")
    active_categories = get_active_categories()
    for cat in active_categories:
        print(
            f"   - {cat['name']}: {cat['description']} (допуск: {cat['tolerance']}%, диапазон: {cat['price_range']})"
        )

    print()

    # 2. Примеры проверки цен по категориям
    test_cases = [
        {
            "category": "electronics",
            "expected": 1000.0,
            "actual": 1050.0,
            "description": "Электроника - в пределах допуска",
        },
        {
            "category": "electronics",
            "expected": 1000.0,
            "actual": 1100.0,
            "description": "Электроника - превышение допуска",
        },
        {
            "category": "clothing",
            "expected": 500.0,
            "actual": 550.0,
            "description": "Одежда - в пределах допуска",
        },
        {
            "category": "food",
            "expected": 100.0,
            "actual": 104.0,
            "description": "Продукты - в пределах допуска",
        },
        {
            "category": "construction",
            "expected": 2000.0,
            "actual": 2200.0,
            "description": "Строительные материалы - превышение",
        },
    ]

    print("2. Проверка цен по категориям:")
    for case in test_cases:
        result = check_price_tolerance(
            case["category"], case["expected"], case["actual"]
        )
        status = "✓" if result["within_tolerance"] else "✗"
        print(f"   {status} {case['description']}")
        print(f"      Ожидаемая: {case['expected']}, Фактическая: {case['actual']}")
        print(
            f"      Отклонение: {result['deviation']:.1%}, Допуск: {result['tolerance_used']:.1%}"
        )
        print(f"      Категория: {result['category_description']}")
        print()

    # 3. Использование PriceChecker с категориями
    print("3. Использование PriceChecker с категориями:")

    # Создаем проверщик с базовыми ценами
    base_prices = {
        "laptop_001": Decimal("50000"),
        "phone_001": Decimal("25000"),
        "shirt_001": Decimal("1500"),
        "bread_001": Decimal("50"),
        "cement_001": Decimal("300"),
    }

    checker = PriceChecker(base_prices=base_prices)

    # Проверяем цены с указанием категорий
    test_prices = {
        "laptop_001": 52000,  # Электроника - в пределах 5%
        "phone_001": 29000,  # Электроника - превышение 5%
        "shirt_001": 1600,  # Одежда - в пределах 10%
        "bread_001": 52,  # Продукты - в пределах 3%
        "cement_001": 330,  # Строительные материалы - в пределах 8%
    }

    # Категории для товаров
    categories = {
        "laptop_001": "electronics",
        "phone_001": "electronics",
        "shirt_001": "clothing",
        "bread_001": "food",
        "cement_001": "construction",
    }

    # Проверка с категориями
    results_with_categories = checker.check_multiple_prices(
        test_prices, categories=categories
    )

    print("   Результаты с учетом категорий:")
    for result in results_with_categories:
        status = "✓" if result.match == "да" else "✗"
        print(f"   {status} {result.product_code}: {result.comments}")

    print()

    # Проверка без категорий (используется общий допуск 10%)
    results_without_categories = checker.check_multiple_prices(
        test_prices, tolerance_percent=Decimal("10")
    )

    print("   Результаты без категорий (допуск 10%):")
    for result in results_without_categories:
        status = "✓" if result.match == "да" else "✗"
        print(f"   {status} {result.product_code}: {result.comments}")

    print()

    # 4. Добавление новой категории и проверка
    print("4. Добавление новой категории и проверка:")

    # Добавляем новую категорию
    new_category = {
        "name": "furniture",
        "description": "Мебель и предметы интерьера",
        "tolerance": 12,
        "min_price": 1000,
        "max_price": 100000,
        "currency": "RUB",
        "active": True,
    }

    try:
        add_custom_category(**new_category)
        save_config()
        print("   ✓ Новая категория 'furniture' добавлена с допуском 12%")

        # Проверяем с новой категорией
        furniture_result = check_price_tolerance("furniture", 5000, 5600)
        print(
            f"   Проверка мебели: 5000 → 5600 (отклонение {furniture_result['deviation']:.1%})"
        )
        print(
            f"   Результат: {'В пределах допуска' if furniture_result['within_tolerance'] else 'Превышение допуска'}"
        )

    except Exception as e:
        print(f"   Ошибка при добавлении категории: {e}")

    print()

    # 5. Сохранение результатов в JSON
    print("5. Сохранение результатов в JSON:")

    results_summary = {
        "active_categories": active_categories,
        "test_results": [
            {
                "category": case["category"],
                "expected": case["expected"],
                "actual": case["actual"],
                "within_tolerance": result["within_tolerance"],
                "deviation": result["deviation"],
                "tolerance_used": result["tolerance_used"],
            }
            for case, result in zip(
                test_cases,
                [
                    check_price_tolerance(
                        case["category"], case["expected"], case["actual"]
                    )
                    for case in test_cases
                ],
            )
        ],
    }

    with open("price_check_results.json", "w", encoding="utf-8") as f:
        json.dump(results_summary, f, ensure_ascii=False, indent=2)

    print("   Результаты сохранены в price_check_results.json")

    print("\n=== Пример завершен ===")


if __name__ == "__main__":
    main()
