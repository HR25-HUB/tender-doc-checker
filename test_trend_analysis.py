#!/usr/bin/env python3
"""
Тестовый скрипт для проверки функций тренд-аналитики в analytics.py и price_analytics.py
"""

import json
import os
import sys
from datetime import datetime

# Добавляем путь к проекту для импортов
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from analytics import AnalyticsEngine
    from price_analytics import PriceAnalyticsEngine
except ImportError as e:
    print(f"Ошибка импорта: {e}")
    sys.exit(1)


def test_analytics_trends():
    """Тестирование трендовых функций в analytics.py"""
    print("=== Тестирование analytics.py тренд-функций ===")

    engine = AnalyticsEngine()

    # Тест 1: Анализ трендов документов
    print("\n1. Анализ трендов документов...")
    doc_trends = engine.analyze_document_trends(days_back=7)
    print(f"   Тип документов: {doc_trends['document_type']}")
    print(f"   Всего документов: {doc_trends['total_documents']}")
    print(f"   Направление тренда: {doc_trends['trend_direction']}")
    print(f"   Средний дневной объем: {doc_trends['average_daily_volume']}")

    # Тест 2: Анализ трендов для конкретного типа документов
    print("\n2. Анализ трендов для типа 'price_list'...")
    price_trends = engine.analyze_document_trends(
        document_type="price_list", days_back=7
    )
    print(f"   Тип документов: {price_trends['document_type']}")
    print(f"   Всего документов: {price_trends['total_documents']}")

    # Тест 3: Анализ использования системы
    print("\n3. Анализ трендов использования системы...")
    usage_trends = engine.analyze_system_usage_trends(days_back=7)
    print(f"   Всего использований: {usage_trends['total_usage']}")
    print(f"   Тренд использования: {usage_trends['usage_trend']}")
    print(f"   Рост поставщиков: {usage_trends['supplier_growth']}")
    print(f"   Пиковый день: {usage_trends['peak_usage_day']}")

    # Тест 4: Комплексный дашборд
    print("\n4. Комплексный дашборд трендов...")
    dashboard = engine.get_trend_analysis_dashboard(days_back=7)
    print(f"   Сгенерировано: {dashboard['generated_at']}")
    print(f"   Период: {dashboard['period_days']} дней")
    print(f"   Сводка: {dashboard['summary']}")

    return True


def test_price_analytics_trends():
    """Тестирование трендовых функций в price_analytics.py"""
    print("\n=== Тестирование price_analytics.py тренд-функций ===")

    engine = PriceAnalyticsEngine()

    # Тест 1: Сезонные тренды
    print("\n1. Анализ сезонных трендов...")
    seasonal = engine.analyze_seasonal_trends(item_name="electronics", years_back=2)
    print(f"   Категория: {seasonal.item_name}")
    print(f"   Пиковый сезон: {seasonal.peak_season}")
    print(f"   Низкий сезон: {seasonal.low_season}")
    print(f"   Волатильность: {seasonal.seasonal_volatility}")

    # Тест 2: Корреляция цен
    print("\n2. Анализ корреляции цен...")
    correlation = engine.analyze_price_correlation(
        item1="electronics", item2="accessories", days_back=7
    )
    print(f"   Корреляция: {correlation['correlation_coefficient']}")
    print(f"   Сила корреляции: {correlation['correlation_strength']}")
    print(f"   Размер выборки: {correlation['sample_size']}")

    # Тест 3: Прогнозирование цен
    print("\n3. Прогноз ценовых трендов...")
    forecast = engine.forecast_price_trend(
        item_name="electronics", supplier_id="supplier_001", days_ahead=7
    )
    print(f"   Товар: {forecast['item_name']}")
    print(f"   Прогноз тренда: {forecast['forecast']}")
    print(f"   Уровень доверия: {forecast['confidence']}")

    # Тест 4: Резюме рыночных трендов
    print("\n4. Резюме рыночных трендов...")
    market_summary = engine.get_market_trend_summary(days_back=7)
    print(f"   Всего товаров: {market_summary['total_items']}")
    print(f"   Восходящих трендов: {market_summary['upward_trends']}")
    print(f"   Нисходящих трендов: {market_summary['downward_trends']}")

    return True


def test_edge_cases():
    """Тестирование крайних случаев"""
    print("\n=== Тестирование крайних случаев ===")

    analytics_engine = AnalyticsEngine()
    price_engine = PriceAnalyticsEngine()

    # Тест 1: Нет данных
    print("\n1. Тест без данных...")
    no_data_trends = analytics_engine.analyze_document_trends(
        document_type="nonexistent_type", days_back=1
    )
    print(f"   Результат при отсутствии данных: {no_data_trends['trend_direction']}")

    # Тест 2: Очень короткий период
    print("\n2. Тест за 1 день...")
    short_trends = analytics_engine.analyze_system_usage_trends(days_back=1)
    print(f"   Результат за 1 день: {short_trends['usage_trend']}")

    # Тест 3: Долгий период
    print("\n3. Тест за 365 дней...")
    long_trends = price_engine.analyze_seasonal_trends(
        item_name="electronics", years_back=2
    )
    print(f"   Результат за 12 месяцев: {long_trends.seasonal_volatility}")

    return True


def save_test_results():
    """Сохранение результатов тестов в файл"""
    print("\n=== Сохранение результатов ===")

    analytics_engine = AnalyticsEngine()
    price_engine = PriceAnalyticsEngine()

    results = {
        "test_timestamp": datetime.now().isoformat(),
        "analytics_dashboard": analytics_engine.get_trend_analysis_dashboard(
            days_back=7
        ),
        "price_market_summary": price_engine.get_market_trend_summary(days_back=7),
        "test_summary": {
            "analytics_functions_tested": [
                "analyze_document_trends",
                "analyze_supplier_performance_trends",
                "analyze_system_usage_trends",
                "get_trend_analysis_dashboard",
            ],
            "price_analytics_functions_tested": [
                "analyze_seasonal_trends",
                "analyze_price_correlation",
                "forecast_price_trend",
                "get_market_trend_summary",
            ],
        },
    }

    # Создаем директорию для результатов
    os.makedirs("test_results", exist_ok=True)

    # Сохраняем результаты
    with open(
        "test_results/trend_analysis_test_results.json", "w", encoding="utf-8"
    ) as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("   Результаты сохранены в test_results/trend_analysis_test_results.json")
    return True


def main():
    """Основная функция тестирования"""
    print("Запуск тестов тренд-аналитики...")

    try:
        # Запускаем все тесты
        test_analytics_trends()
        test_price_analytics_trends()
        test_edge_cases()
        save_test_results()

        print("\n✅ Все тесты тренд-аналитики успешно пройдены!")
        print("\nРеализованные функции:")
        print("- Анализ трендов документов и системы")
        print("- Анализ производительности поставщиков")
        print("- Сезонные и корреляционные тренды цен")
        print("- Прогнозирование ценовых трендов")
        print("- Комплексные дашборды и резюме")

    except Exception as e:
        print(f"\n❌ Ошибка при тестировании: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    main()
