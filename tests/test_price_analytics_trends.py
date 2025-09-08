"""Тесты для анализа трендов цен."""

from datetime import datetime, timedelta

from price_analytics import PriceTrendAnalyzer
from src.models import PriceRecord


class TestPriceAnalyticsTrends:
    """Тесты для выявления трендов цен."""

    def test_detect_price_increase_trend(self):
        """Тест выявления тренда роста цен."""
        # Создаем исторические данные с ростом цены
        records = [
            PriceRecord(
                sku="PROD001",
                price=100.0,
                currency="RUB",
                supplier="Supplier1",
                category="electronics",
                timestamp=datetime.now() - timedelta(days=30),
            ),
            PriceRecord(
                sku="PROD001",
                price=110.0,
                currency="RUB",
                supplier="Supplier1",
                category="electronics",
                timestamp=datetime.now() - timedelta(days=20),
            ),
            PriceRecord(
                sku="PROD001",
                price=125.0,
                currency="RUB",
                supplier="Supplier1",
                category="electronics",
                timestamp=datetime.now() - timedelta(days=10),
            ),
            PriceRecord(
                sku="PROD001",
                price=140.0,
                currency="RUB",
                supplier="Supplier1",
                category="electronics",
                timestamp=datetime.now(),
            ),
        ]

        analyzer = PriceTrendAnalyzer()
        trend = analyzer.analyze_trend(records)

        assert trend.trend_direction == "increasing"
        assert trend.price_change_percent > 0
        assert abs(trend.price_change_percent - 40.0) < 0.1  # (140-100)/100 * 100 = 40%

    def test_detect_price_decrease_trend(self):
        """Тест выявления тренда падения цен."""
        records = [
            PriceRecord(
                sku="PROD002",
                price=200.0,
                currency="RUB",
                supplier="Supplier2",
                category="clothing",
                timestamp=datetime.now() - timedelta(days=30),
            ),
            PriceRecord(
                sku="PROD002",
                price=180.0,
                currency="RUB",
                supplier="Supplier2",
                category="clothing",
                timestamp=datetime.now() - timedelta(days=20),
            ),
            PriceRecord(
                sku="PROD002",
                price=160.0,
                currency="RUB",
                supplier="Supplier2",
                category="clothing",
                timestamp=datetime.now() - timedelta(days=10),
            ),
            PriceRecord(
                sku="PROD002",
                price=150.0,
                currency="RUB",
                supplier="Supplier2",
                category="clothing",
                timestamp=datetime.now(),
            ),
        ]

        analyzer = PriceTrendAnalyzer()
        trend = analyzer.analyze_trend(records)

        assert trend.trend_direction == "decreasing"
        assert trend.price_change_percent < 0
        assert (
            abs(trend.price_change_percent - (-25.0)) < 0.1
        )  # (150-200)/200 * 100 = -25%

    def test_detect_stable_price_trend(self):
        """Тест выявления стабильного тренда цен."""
        records = [
            PriceRecord(
                sku="PROD003",
                price=50.0,
                currency="RUB",
                supplier="Supplier3",
                category="food",
                timestamp=datetime.now() - timedelta(days=30),
            ),
            PriceRecord(
                sku="PROD003",
                price=50.5,
                currency="RUB",
                supplier="Supplier3",
                category="food",
                timestamp=datetime.now() - timedelta(days=20),
            ),
            PriceRecord(
                sku="PROD003",
                price=49.8,
                currency="RUB",
                supplier="Supplier3",
                category="food",
                timestamp=datetime.now() - timedelta(days=10),
            ),
            PriceRecord(
                sku="PROD003",
                price=50.2,
                currency="RUB",
                supplier="Supplier3",
                category="food",
                timestamp=datetime.now(),
            ),
        ]

        analyzer = PriceTrendAnalyzer()
        trend = analyzer.analyze_trend(records)

        assert trend.trend_direction == "stable"
        assert abs(trend.price_change_percent) < 2.0  # Менее 2% изменения

    def test_calculate_average_price_increase_per_month(self):
        """Тест расчета среднего роста цен в месяц."""
        records = [
            PriceRecord(
                sku="PROD004",
                price=100.0,
                currency="RUB",
                supplier="Supplier4",
                category="construction",
                timestamp=datetime.now() - timedelta(days=90),
            ),
            PriceRecord(
                sku="PROD004",
                price=120.0,
                currency="RUB",
                supplier="Supplier4",
                category="construction",
                timestamp=datetime.now() - timedelta(days=60),
            ),
            PriceRecord(
                sku="PROD004",
                price=150.0,
                currency="RUB",
                supplier="Supplier4",
                category="construction",
                timestamp=datetime.now() - timedelta(days=30),
            ),
            PriceRecord(
                sku="PROD004",
                price=180.0,
                currency="RUB",
                supplier="Supplier4",
                category="construction",
                timestamp=datetime.now(),
            ),
        ]

        analyzer = PriceTrendAnalyzer()
        trend = analyzer.analyze_trend(records)

        # Ожидаемый рост: 80% за 3 месяца = ~26.67% в месяц
        expected_monthly_increase = 80.0 / 3
        assert abs(trend.monthly_change_rate - expected_monthly_increase) < 0.5

    def test_insufficient_data_for_trend_analysis(self):
        """Тест обработки недостаточных данных для анализа тренда."""
        records = [
            PriceRecord(
                sku="PROD005",
                price=100.0,
                currency="RUB",
                supplier="Supplier5",
                category="electronics",
                timestamp=datetime.now(),
            )
        ]

        analyzer = PriceTrendAnalyzer()
        trend = analyzer.analyze_trend(records)

        assert trend.trend_direction == "insufficient_data"
        assert trend.confidence_level == 0.0

    def test_trend_analysis_with_different_suppliers(self):
        """Тест анализа тренда для разных поставщиков одного товара."""
        records = [
            PriceRecord(
                sku="PROD006",
                price=100.0,
                currency="RUB",
                supplier="SupplierA",
                category="precision_parts",
                timestamp=datetime.now() - timedelta(days=30),
            ),
            PriceRecord(
                sku="PROD006",
                price=105.0,
                currency="RUB",
                supplier="SupplierB",
                category="precision_parts",
                timestamp=datetime.now() - timedelta(days=25),
            ),
            PriceRecord(
                sku="PROD006",
                price=110.0,
                currency="RUB",
                supplier="SupplierA",
                category="precision_parts",
                timestamp=datetime.now() - timedelta(days=15),
            ),
            PriceRecord(
                sku="PROD006",
                price=115.0,
                currency="RUB",
                supplier="SupplierB",
                category="precision_parts",
                timestamp=datetime.now() - timedelta(days=5),
            ),
        ]

        analyzer = PriceTrendAnalyzer()

        # Анализ по SupplierA
        supplier_a_records = [r for r in records if r.supplier == "SupplierA"]
        trend_a = analyzer.analyze_trend(supplier_a_records)
        assert trend_a.trend_direction == "increasing"

        # Анализ по SupplierB
        supplier_b_records = [r for r in records if r.supplier == "SupplierB"]
        trend_b = analyzer.analyze_trend(supplier_b_records)
        assert trend_b.trend_direction == "increasing"

    def test_volatile_price_trend(self):
        """Тест выявления волатильного тренда цен."""
        records = [
            PriceRecord(
                sku="PROD007",
                price=100.0,
                currency="RUB",
                supplier="Supplier7",
                category="electronics",
                timestamp=datetime.now() - timedelta(days=30),
            ),
            PriceRecord(
                sku="PROD007",
                price=150.0,
                currency="RUB",
                supplier="Supplier7",
                category="electronics",
                timestamp=datetime.now() - timedelta(days=20),
            ),
            PriceRecord(
                sku="PROD007",
                price=80.0,
                currency="RUB",
                supplier="Supplier7",
                category="electronics",
                timestamp=datetime.now() - timedelta(days=10),
            ),
            PriceRecord(
                sku="PROD007",
                price=200.0,
                currency="RUB",
                supplier="Supplier7",
                category="electronics",
                timestamp=datetime.now(),
            ),
        ]

        analyzer = PriceTrendAnalyzer()
        trend = analyzer.analyze_trend(records)

        assert trend.trend_direction == "volatile"
        assert trend.volatility_index > 30.0  # Высокая волатильность

    def test_trend_analysis_with_different_currencies(self):
        """Тест анализа тренда для цен в разных валютах."""
        records = [
            PriceRecord(
                sku="PROD008",
                price=1.0,
                currency="USD",
                supplier="Supplier8",
                category="electronics",
                timestamp=datetime.now() - timedelta(days=30),
            ),
            PriceRecord(
                sku="PROD008",
                price=1.1,
                currency="USD",
                supplier="Supplier8",
                category="electronics",
                timestamp=datetime.now() - timedelta(days=20),
            ),
            PriceRecord(
                sku="PROD008",
                price=1.2,
                currency="USD",
                supplier="Supplier8",
                category="electronics",
                timestamp=datetime.now() - timedelta(days=10),
            ),
            PriceRecord(
                sku="PROD008",
                price=1.3,
                currency="USD",
                supplier="Supplier8",
                category="electronics",
                timestamp=datetime.now(),
            ),
        ]

        analyzer = PriceTrendAnalyzer()
        trend = analyzer.analyze_trend(records)

        assert trend.trend_direction == "increasing"
        assert abs(trend.price_change_percent - 30.0) < 0.1  # (1.3-1.0)/1.0 * 100 = 30%
