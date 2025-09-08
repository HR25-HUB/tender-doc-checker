#!/usr/bin/env python3
"""
Тестовый скрипт для проверки функциональности категорий допусков в price_checker.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import load_config
from src.price_checker import check_price_tolerance, get_active_categories


def test_categories():
    """Простой тест категорий."""
    print("=== Тест категорий допусков ===\n")

    # Проверяем загрузку конфигурации
    try:
        config = load_config()
        print(f"Конфигурация загружена: {len(config.categories)} категорий")

        # Показываем активные категории
        active_cats = get_active_categories()
        print(f"Активных категорий: {len(active_cats)}")

        for cat in active_cats:
            print(f"  - {cat['name']}: {cat['tolerance']}% допуск")

    except Exception as e:
        print(f"Ошибка загрузки конфигурации: {e}")
        return

    print()

    # Тестируем проверку цен
    test_cases = [
        ("electronics", 1000, 1050),
        ("electronics", 1000, 1100),
        ("clothing", 1000, 1100),
        ("food", 1000, 1020),
    ]

    print("Тестирование проверки цен:")
    for category, expected, actual in test_cases:
        try:
            result = check_price_tolerance(category, expected, actual)
            status = "✓" if result["within_tolerance"] else "✗"
            print(
                f"  {status} {category}: {expected} → {actual} "
                f"({result['deviation']:.1%}, допуск: {result['tolerance_used']:.1%})"
            )
        except Exception as e:
            print(f"  Ошибка при проверке {category}: {e}")

    print("\n=== Тест завершен ===")


if __name__ == "__main__":
    test_categories()
