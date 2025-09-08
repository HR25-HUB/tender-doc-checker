"""
Пример использования новой системы конфигурации категорий и допусков.

Этот файл демонстрирует основные функции работы с категориями:
- загрузку конфигурации
- получение информации о категориях
- добавление новых категорий
- управление допусками
"""

import os
import sys

# Добавляем путь к src для импорта
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.config import (
    add_custom_category,
    get_category_info,
    list_all_categories,
    load_config,
    remove_category,
    validate_tolerance_config,
)


def main():
    """Главная функция примера."""
    print("=== Пример использования конфигурации категорий и допусков ===\n")

    # 1. Загрузка текущей конфигурации
    print("1. Загрузка конфигурации...")
    config = load_config()
    print(f"Загружено категорий: {len(config.categories)}")

    # 2. Просмотр всех категорий
    print("\n2. Список всех категорий:")
    categories = list_all_categories()
    for name, data in categories.items():
        status = "✓" if data.get("active", True) else "✗"
        print(
            f"  {status} {name}: {data['description']} (tolerance: {data['tolerance']})"
        )

    # 3. Получение информации о конкретной категории
    print("\n3. Информация о категории 'electronics':")
    electronics_info = get_category_info("electronics")
    for key, value in electronics_info.items():
        print(f"  {key}: {value}")

    # 4. Добавление новой пользовательской категории
    print("\n4. Добавление новой категории...")
    success = add_custom_category(
        name="custom_tech",
        tolerance=0.04,
        description="Пользовательская техника и оборудование",
        min_price=5000,
        max_price=500000,
        currency="RUB",
    )
    print(f"Категория добавлена: {'✓' if success else '✗'}")

    # 5. Проверка новой категории
    print("\n5. Проверка новой категории:")
    new_category = get_category_info("custom_tech")
    print(f"  custom_tech: {new_category}")

    # 6. Получение допуска для категории
    print("\n6. Получение допусков:")
    print(f"  Допуск для electronics: {config.get_tolerance('electronics')}")
    print(f"  Допуск для несуществующей категории: {config.get_tolerance('unknown')}")

    # 7. Валидация конфигурации
    print("\n7. Валидация конфигурации...")
    try:
        validate_tolerance_config(config)
        print("  ✓ Конфигурация валидна")
    except Exception as e:
        print(f"  ✗ Ошибка валидации: {e}")

    # 8. Список активных категорий
    print("\n8. Активные категории:")
    active_categories = config.list_categories()
    for cat in active_categories:
        print(f"  - {cat}")

    # 9. Удаление категории (деактивация)
    print("\n9. Деактивация категории...")
    remove_success = remove_category("custom_tech")
    print(f"Категория деактивирована: {'✓' if remove_success else '✗'}")

    # 10. Проверка после деактивации
    print("\n10. Проверка после деактивации:")
    updated_config = load_config()
    custom_tech = updated_config.get_category("custom_tech")
    print(f"  custom_tech активна: {custom_tech.active}")
    print(f"  custom_tech допуск: {updated_config.get_tolerance('custom_tech')}")


if __name__ == "__main__":
    main()
