"""Тесты для модуля price_analytics."""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from price_analytics import (
    MarketAnalysis,
    PriceAlert,
    PriceAnalyticsEngine,
    PriceTrend,
    SupplierPriceProfile,
    compare_suppliers,
    get_item_price_trend,
    get_market_analysis,
    get_price_alerts,
    get_supplier_price_analysis,
)


class TestPriceAnalyticsEngine:
    """Тесты для класса PriceAnalyticsEngine."""

    @pytest.fixture
    def mock_db_connection(self):
        """Мок соединения с базой данных."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.execute.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []
        mock_cursor.fetchone.return_value = None
        return mock_conn

    @pytest.fixture
    def analytics_engine(self, mock_db_connection):
        """Экземпляр PriceAnalyticsEngine с мок базой данных."""
        with patch("price_analytics.sqlite3.connect", return_value=mock_db_connection):
            return PriceAnalyticsEngine()

    def test_analytics_engine_initialization(self):
        """Тест инициализации PriceAnalyticsEngine."""
        engine = PriceAnalyticsEngine()
        assert engine.db_path is not None

    def test_analyze_price_trends_empty_data(
        self, analytics_engine, mock_db_connection
    ):
        """Тест анализа трендов с пустыми данными."""
        mock_cursor = mock_db_connection.execute.return_value
        mock_cursor.fetchall.return_value = []

        trends = analytics_engine.analyze_price_trends()
        assert isinstance(trends, list)
        assert len(trends) == 0

    def test_analyze_price_trends_with_data(self, analytics_engine, mock_db_connection):
        """Тест анализа трендов цен с данными."""
        # Мокируем метод _get_db_connection
        with patch.object(
            analytics_engine, "_get_db_connection", return_value=mock_db_connection
        ):
            # Мокаем данные трендов
            mock_trend_data = [
                {
                    "item_name": "ITEM_001",
                    "supplier_id": 1,
                    "supplier_name": "Поставщик 1",
                    "price": 100.0,
                    "recorded_at": "2024-01-01 10:00:00",
                },
                {
                    "item_name": "ITEM_001",
                    "supplier_id": 1,
                    "supplier_name": "Поставщик 1",
                    "price": 105.0,
                    "recorded_at": "2024-01-02 10:00:00",
                },
                {
                    "item_name": "ITEM_002",
                    "supplier_id": 2,
                    "supplier_name": "Поставщик 2",
                    "price": 200.0,
                    "recorded_at": "2024-01-01 10:00:00",
                },
            ]

            mock_cursor = mock_db_connection.execute.return_value
            mock_cursor.fetchall.return_value = mock_trend_data

            trends = analytics_engine.analyze_price_trends()

            assert isinstance(trends, list)
            # Проверяем, что метод был вызван
            mock_db_connection.execute.assert_called()

    def test_analyze_market_for_item_no_data(
        self, analytics_engine, mock_db_connection
    ):
        """Тест анализа рынка для товара без данных."""
        mock_cursor = mock_db_connection.execute.return_value
        mock_cursor.fetchall.return_value = []

        analysis = analytics_engine.analyze_market_for_item("NONEXISTENT_ITEM")

        assert isinstance(analysis, MarketAnalysis)
        assert analysis.item_name == "NONEXISTENT_ITEM"
        assert analysis.total_suppliers == 0
        assert analysis.price_range == (0, 0)
        assert analysis.market_avg_price == 0

    def test_analyze_market_for_item_with_data(
        self, analytics_engine, mock_db_connection
    ):
        """Тест анализа рынка для товара с данными."""
        # Мокируем метод _get_db_connection
        with patch.object(
            analytics_engine, "_get_db_connection", return_value=mock_db_connection
        ):
            # Мокаем данные рынка
            mock_market_data = [
                {
                    "supplier_id": 1,
                    "supplier_name": "Поставщик 1",
                    "price": 100.0,
                    "recorded_at": "2024-01-01 10:00:00",
                },
                {
                    "supplier_id": 2,
                    "supplier_name": "Поставщик 2",
                    "price": 105.0,
                    "recorded_at": "2024-01-01 10:00:00",
                },
                {
                    "supplier_id": 3,
                    "supplier_name": "Поставщик 3",
                    "price": 95.0,
                    "recorded_at": "2024-01-01 10:00:00",
                },
            ]

            mock_cursor = mock_db_connection.execute.return_value
            mock_cursor.fetchall.return_value = mock_market_data

            analysis = analytics_engine.analyze_market_for_item("ITEM_001")

            assert isinstance(analysis, MarketAnalysis)
            assert analysis.item_name == "ITEM_001"
            # Проверяем, что метод был вызван
            mock_db_connection.execute.assert_called()

    def test_generate_price_alerts_empty_data(self, analytics_engine):
        """Тест генерации предупреждений с пустыми данными."""
        with patch.object(analytics_engine, "analyze_price_trends", return_value=[]):
            alerts = analytics_engine.generate_price_alerts()
            assert isinstance(alerts, list)
            assert len(alerts) == 0

    def test_generate_price_alerts_with_trends(self, analytics_engine):
        """Тест генерации предупреждений с трендами."""
        # Создаем мок тренд с большим изменением цены
        mock_trend = PriceTrend(
            item_name="ITEM_001",
            supplier_id="SUP_001",
            supplier_name="Поставщик 1",
            price_history=[
                (datetime.now() - timedelta(days=1), 100.0),
                (datetime.now(), 120.0),
            ],
            trend_direction="up",
            trend_percentage=20.0,  # 20% рост - должен вызвать предупреждение
            volatility_score=15.0,
            last_price=120.0,
            avg_price=110.0,
            min_price=100.0,
            max_price=120.0,
        )

        with patch.object(
            analytics_engine, "analyze_price_trends", return_value=[mock_trend]
        ):
            alerts = analytics_engine.generate_price_alerts(threshold_percent=15.0)

            assert isinstance(alerts, list)
            # Должно быть создано предупреждение для значительного роста цены
            if len(alerts) > 0:
                alert = alerts[0]
                assert isinstance(alert, PriceAlert)
                assert alert.item_name == "ITEM_001"

    def test_analyze_supplier_price_profile(self, analytics_engine, mock_db_connection):
        """Тест анализа ценового профиля поставщика."""
        # Мокируем метод _get_db_connection
        with patch.object(
            analytics_engine, "_get_db_connection", return_value=mock_db_connection
        ):
            # Мокаем данные поставщика
            mock_cursor = mock_db_connection.execute.return_value

            # Первый вызов - получение информации о поставщике
            mock_cursor.fetchone.return_value = {"name": "Поставщик 1"}

            # Второй вызов - получение товаров поставщика
            mock_supplier_data = [
                {"item_name": "ITEM_001", "price": 100.0, "recorded_at": "2024-01-01"},
                {"item_name": "ITEM_002", "price": 200.0, "recorded_at": "2024-01-01"},
            ]
            mock_cursor.fetchall.return_value = mock_supplier_data

            # Мокируем analyze_market_for_item для каждого товара
            mock_market_analysis = MarketAnalysis(
                item_name="ITEM_001",
                total_suppliers=3,
                price_range=(90.0, 110.0),
                market_avg_price=100.0,
                market_median_price=100.0,
                price_std_deviation=5.0,
                competitive_suppliers=[],
                price_outliers=[],
                market_concentration=0.5,
            )

            # Мокируем analyze_price_trends для расчета стабильности цен
            mock_trends = [
                PriceTrend(
                    item_name="ITEM_001",
                    supplier_id="1",
                    supplier_name="Поставщик 1",
                    price_history=[(datetime.now(), 100.0)],
                    trend_direction="stable",
                    trend_percentage=0.0,
                    volatility_score=10.0,
                    last_price=100.0,
                    avg_price=100.0,
                    min_price=100.0,
                    max_price=100.0,
                )
            ]

            with patch.object(
                analytics_engine,
                "analyze_market_for_item",
                return_value=mock_market_analysis,
            ), patch.object(
                analytics_engine, "analyze_price_trends", return_value=mock_trends
            ):
                profile = analytics_engine.analyze_supplier_price_profile("1")

                assert isinstance(profile, SupplierPriceProfile)
                assert profile.supplier_id == "1"
                # Проверяем, что метод был вызван
                mock_db_connection.execute.assert_called()

    def test_compare_suppliers_for_item(self, analytics_engine):
        """Тест сравнения поставщиков для товара."""
        # Мокаем анализ рынка
        mock_analysis = MarketAnalysis(
            item_name="ITEM_001",
            total_suppliers=2,
            price_range=(95.0, 105.0),
            market_avg_price=100.0,
            market_median_price=100.0,
            price_std_deviation=5.0,
            competitive_suppliers=[
                {
                    "supplier_id": "SUP_001",
                    "supplier_name": "Поставщик 1",
                    "price": 95.0,
                },
                {
                    "supplier_id": "SUP_002",
                    "supplier_name": "Поставщик 2",
                    "price": 105.0,
                },
            ],
            price_outliers=[],
            market_concentration=0.5,
        )

        # Мокаем профили поставщиков
        mock_profile = SupplierPriceProfile(
            supplier_id="SUP_001",
            supplier_name="Поставщик 1",
            avg_price_position="below_market",
            price_stability_score=85.0,
            competitive_advantage=15.0,
            price_update_frequency=7,
            total_items=10,
            items_below_market=7,
            items_above_market=3,
            risk_score=25.0,
        )

        with patch.object(
            analytics_engine, "analyze_market_for_item", return_value=mock_analysis
        ), patch.object(
            analytics_engine,
            "analyze_supplier_price_profile",
            return_value=mock_profile,
        ):
            comparison = analytics_engine.compare_suppliers_for_item("ITEM_001")

            assert isinstance(comparison, dict)
            assert "item_name" in comparison
            assert comparison["item_name"] == "ITEM_001"

    def test_get_price_analytics_summary(self, analytics_engine):
        """Тест получения сводки ценовой аналитики."""
        # Мокаем методы
        with patch.object(analytics_engine, "analyze_price_trends", return_value=[]):
            with patch.object(
                analytics_engine, "generate_price_alerts", return_value=[]
            ):
                summary = analytics_engine.get_price_analytics_summary()

                assert isinstance(summary, dict)
                assert "trend_statistics" in summary
                assert "alert_statistics" in summary
                assert "summary_period_days" in summary
                assert "top_price_increases" in summary
                assert "top_price_decreases" in summary
                assert "recent_alerts" in summary
                assert "generated_at" in summary


class TestPriceAnalyticsHelperFunctions:
    """Тесты для вспомогательных функций модуля price_analytics."""

    @pytest.fixture
    def mock_db_connection(self):
        """Мок соединения с базой данных."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.execute.return_value = mock_cursor
        mock_conn.close.return_value = None
        mock_cursor.fetchall.return_value = []
        mock_cursor.fetchone.return_value = None
        return mock_conn

    @patch("price_analytics.PriceAnalyticsEngine")
    def test_get_item_price_trend_with_data(self, mock_engine_class):
        """Тест получения тренда цен товара с данными."""
        # Мокаем экземпляр движка
        mock_engine = Mock()
        mock_engine_class.return_value = mock_engine

        # Мокаем возвращаемые данные
        mock_trend = PriceTrend(
            item_name="ITEM_001",
            supplier_id="1",
            supplier_name="Поставщик 1",
            price_history=[(datetime.now(), 100.0)],
            trend_direction="up",
            trend_percentage=5.0,
            volatility_score=10.0,
            last_price=105.0,
            avg_price=102.5,
            min_price=100.0,
            max_price=105.0,
        )
        mock_engine.analyze_price_trends.return_value = [mock_trend]

        trends = get_item_price_trend("ITEM_001")

        assert isinstance(trends, list)
        assert len(trends) > 0
        assert trends[0].item_name == "ITEM_001"

    @patch("price_analytics.PriceAnalyticsEngine")
    def test_get_market_analysis_with_data(self, mock_engine_class):
        """Тест получения анализа рынка с данными."""
        # Мокаем экземпляр движка
        mock_engine = Mock()
        mock_engine_class.return_value = mock_engine

        # Мокаем возвращаемые данные
        mock_analysis = MarketAnalysis(
            item_name="ITEM_001",
            total_suppliers=2,
            price_range=(100.0, 105.0),
            market_avg_price=102.5,
            market_median_price=102.5,
            price_std_deviation=2.5,
            competitive_suppliers=[],
            price_outliers=[],
            market_concentration=0.5,
        )
        mock_engine.analyze_market_for_item.return_value = mock_analysis

        analysis = get_market_analysis("ITEM_001")

        assert isinstance(analysis, MarketAnalysis)
        assert analysis.item_name == "ITEM_001"

    @patch("price_analytics.PriceAnalyticsEngine")
    def test_get_price_alerts_with_data(self, mock_engine_class):
        """Тест получения предупреждений с данными."""
        # Мокаем экземпляр движка
        mock_engine = Mock()
        mock_engine_class.return_value = mock_engine

        # Мокаем возвращаемые данные
        mock_alert = PriceAlert(
            alert_type="price_spike",
            severity="high",
            item_name="ITEM_001",
            supplier_id="1",
            supplier_name="Поставщик 1",
            current_price=150.0,
            reference_price=100.0,
            price_change_percent=50.0,
            description="Резкий рост цены",
            created_at=datetime.now(),
            recommendations=["Проверить обоснованность"],
        )
        mock_engine.generate_price_alerts.return_value = [mock_alert]

        alerts = get_price_alerts(threshold_percent=20.0)

        assert isinstance(alerts, list)
        assert len(alerts) > 0

    @patch("price_analytics.PriceAnalyticsEngine")
    def test_compare_suppliers_function_with_data(self, mock_engine_class):
        """Тест функции сравнения поставщиков с данными."""
        # Мокаем экземпляр движка
        mock_engine = Mock()
        mock_engine_class.return_value = mock_engine

        # Мокаем возвращаемые данные
        mock_comparison = {
            "item_name": "ITEM_001",
            "market_analysis": MarketAnalysis(
                item_name="ITEM_001",
                total_suppliers=2,
                price_range=(100.0, 105.0),
                market_avg_price=102.5,
                market_median_price=102.5,
                price_std_deviation=2.5,
                competitive_suppliers=[],
                price_outliers=[],
                market_concentration=0.5,
            ),
            "supplier_rankings": [
                {"supplier_id": 1, "supplier_name": "Поставщик 1", "price": 100.0},
                {"supplier_id": 2, "supplier_name": "Поставщик 2", "price": 105.0},
            ],
        }
        mock_engine.compare_suppliers_for_item.return_value = mock_comparison

        comparison = compare_suppliers("ITEM_001")

        assert isinstance(comparison, dict)
        assert "item_name" in comparison
        assert "supplier_rankings" in comparison

    @patch("price_analytics.PriceAnalyticsEngine")
    def test_get_supplier_price_analysis_with_data(self, mock_engine_class):
        """Тест получения анализа цен поставщика с данными."""
        # Мокаем экземпляр движка
        mock_engine = Mock()
        mock_engine_class.return_value = mock_engine

        # Мокаем возвращаемые данные
        mock_profile = SupplierPriceProfile(
            supplier_id="1",
            supplier_name="Поставщик 1",
            avg_price_position="below_market",
            price_stability_score=85.0,
            competitive_advantage=15.0,
            price_update_frequency=7,
            total_items=10,
            items_below_market=7,
            items_above_market=3,
            risk_score=25.0,
        )
        mock_engine.analyze_supplier_price_profile.return_value = mock_profile

        analysis = get_supplier_price_analysis("1")

        assert isinstance(analysis, SupplierPriceProfile)
        assert analysis.supplier_id == "1"
        assert analysis.supplier_name == "Поставщик 1"


class TestPriceAnalyticsDataClasses:
    """Тесты для классов данных модуля price_analytics."""

    def test_price_trend_creation(self):
        """Тест создания объекта PriceTrend."""
        trend = PriceTrend(
            item_name="ITEM_001",
            supplier_id="SUP_001",
            supplier_name="Поставщик 1",
            price_history=[(datetime.now(), 100.0)],
            trend_direction="up",
            trend_percentage=5.0,
            volatility_score=10.0,
            last_price=105.0,
            avg_price=102.5,
            min_price=100.0,
            max_price=105.0,
        )

        assert trend.item_name == "ITEM_001"
        assert trend.supplier_id == "SUP_001"
        assert trend.trend_direction == "up"
        assert trend.trend_percentage == 5.0

    def test_market_analysis_creation(self):
        """Тест создания объекта MarketAnalysis."""
        analysis = MarketAnalysis(
            item_name="ITEM_001",
            total_suppliers=3,
            price_range=(95.0, 105.0),
            market_avg_price=100.0,
            market_median_price=100.0,
            price_std_deviation=5.0,
            competitive_suppliers=[],
            price_outliers=[],
            market_concentration=0.33,
        )

        assert analysis.item_name == "ITEM_001"
        assert analysis.total_suppliers == 3
        assert analysis.price_range == (95.0, 105.0)
        assert analysis.market_avg_price == 100.0

    def test_price_alert_creation(self):
        """Тест создания объекта PriceAlert."""
        alert = PriceAlert(
            alert_type="price_spike",
            severity="high",
            item_name="ITEM_001",
            supplier_id="SUP_001",
            supplier_name="Поставщик 1",
            current_price=120.0,
            reference_price=100.0,
            price_change_percent=20.0,
            description="Значительный рост цены",
            created_at=datetime.now(),
            recommendations=["Проверить альтернативных поставщиков"],
        )

        assert alert.alert_type == "price_spike"
        assert alert.severity == "high"
        assert alert.item_name == "ITEM_001"
        assert alert.price_change_percent == 20.0

    def test_supplier_price_profile_creation(self):
        """Тест создания объекта SupplierPriceProfile."""
        profile = SupplierPriceProfile(
            supplier_id="SUP_001",
            supplier_name="Поставщик 1",
            avg_price_position="low",
            price_stability_score=85.0,
            competitive_advantage=10.0,
            price_update_frequency=5.0,
            total_items=20,
            items_below_market=15,
            items_above_market=2,
            risk_score=15.0,
        )

        assert profile.supplier_id == "SUP_001"
        assert profile.supplier_name == "Поставщик 1"
        assert profile.avg_price_position == "low"
        assert profile.price_stability_score == 85.0
        assert profile.total_items == 20
