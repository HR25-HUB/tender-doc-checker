#!/usr/bin/env python
"""Скрипт для запуска тестов ценовой аналитики."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Попробуем импортировать pytest
try:
    import pytest

    if __name__ == "__main__":
        print("Запуск тестов ценовой аналитики через pytest...")
        # Запускаем pytest для конкретного файла
        exit_code = pytest.main(["tests/test_price_analytics.py", "-v", "--tb=short"])
        sys.exit(exit_code)

except ImportError:
    print("pytest не найден, попробуем установить...")
    import subprocess

    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pytest"])
        import pytest

        if __name__ == "__main__":
            print("Запуск тестов ценовой аналитики через pytest...")
            exit_code = pytest.main(
                ["tests/test_price_analytics.py", "-v", "--tb=short"]
            )
            sys.exit(exit_code)
    except Exception as e:
        print(f"Не удалось установить pytest: {e}")
        print("Попробуем запустить тесты вручную...")

        # Ручной запуск тестов
        from price_analytics import PriceAnalyticsEngine

        def run_manual_tests():
            print("\n=== Ручное тестирование модуля price_analytics ===")

            try:
                # Тест 1: Создание экземпляра
                engine = PriceAnalyticsEngine()
                print("✓ PriceAnalyticsEngine создан успешно")

                # Тест 2: Проверка методов
                methods = [
                    "analyze_price_trends",
                    "analyze_market_for_item",
                    "generate_price_alerts",
                    "analyze_supplier_price_profile",
                    "compare_suppliers_for_item",
                    "get_price_analytics_summary",
                ]

                for method in methods:
                    if hasattr(engine, method):
                        print(f"✓ Метод {method} найден")
                    else:
                        print(f"✗ Метод {method} не найден")

                print("\n=== Тестирование завершено ===")
                return True

            except Exception as e:
                print(f"✗ Ошибка при тестировании: {e}")
                return False

        if __name__ == "__main__":
            success = run_manual_tests()
            sys.exit(0 if success else 1)
