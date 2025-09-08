"""Тесты для модуля интеграции с ERP системами."""

from datetime import datetime
from unittest.mock import patch

import pytest

from erp_integration import (
    ERPConnectionConfig,
    ERPConnectionError,
    ERPSystemType,
    InventoryInfo,
    MockERPConnector,
    PriceInfo,
    ProductInfo,
    check_inventory_levels_from_erp,
    create_erp_connector,
    get_current_prices_from_erp,
    get_product_info_from_erp,
)


class TestERPConnectionConfig:
    """Тесты для конфигурации подключения к ERP."""

    def test_erp_connection_config_creation(self):
        """Тест создания конфигурации подключения."""
        config = ERPConnectionConfig(
            system_type=ERPSystemType.ONEC,
            host="localhost",
            port=1433,
            database="test_db",
            username="test_user",
            password="test_pass",
        )

        assert config.system_type == ERPSystemType.ONEC
        assert config.host == "localhost"
        assert config.port == 1433
        assert config.database == "test_db"
        assert config.username == "test_user"
        assert config.password == "test_pass"
        assert config.timeout == 30  # default value
        assert config.ssl_enabled is False  # default value


class TestMockERPConnector:
    """Тесты для мок-коннектора ERP системы."""

    @pytest.fixture
    def mock_config(self):
        """Фикстура с мок-конфигурацией."""
        return ERPConnectionConfig(
            system_type=ERPSystemType.CUSTOM,
            host="mock",
            port=8080,
            database="mock_db",
            username="mock_user",
            password="mock_pass",
        )

    @pytest.fixture
    def mock_connector(self, mock_config):
        """Фикстура с мок-коннектором."""
        return MockERPConnector(mock_config)

    def test_erp_connection(self, mock_connector):
        """Тест подключения к ERP системе."""
        # Проверяем начальное состояние
        assert not mock_connector.is_connected

        # Подключаемся
        result = mock_connector.connect()
        assert result is True
        assert mock_connector.is_connected

        # Проверяем соединение
        assert mock_connector.test_connection() is True

        # Отключаемся
        mock_connector.disconnect()
        assert not mock_connector.is_connected

    def test_context_manager(self, mock_connector):
        """Тест использования коннектора как контекстного менеджера."""
        assert not mock_connector.is_connected

        with mock_connector as conn:
            assert conn.is_connected
            assert conn.test_connection() is True

        assert not mock_connector.is_connected

    def test_product_data_fetch(self, mock_connector):
        """Тест получения данных о товарах."""
        mock_connector.connect()

        # Тест получения существующего товара
        product = mock_connector.get_product_info("PROD001")
        assert product is not None
        assert product.product_code == "PROD001"
        assert product.name == "Тестовый товар 1"
        assert product.current_price == 100.0
        assert product.currency == "RUB"

        # Тест получения несуществующего товара
        product = mock_connector.get_product_info("NONEXISTENT")
        assert product is None

        mock_connector.disconnect()

    def test_product_data_fetch_without_connection(self, mock_connector):
        """Тест получения данных без подключения."""
        with pytest.raises(ERPConnectionError):
            mock_connector.get_product_info("PROD001")

    def test_current_prices_fetch(self, mock_connector):
        """Тест получения текущих цен."""
        mock_connector.connect()

        prices = mock_connector.get_current_prices(["PROD001", "PROD002"])
        assert len(prices) == 2

        price1 = next(p for p in prices if p.product_code == "PROD001")
        assert price1.price == 100.0
        assert price1.currency == "RUB"
        assert price1.price_type == "base"

        price2 = next(p for p in prices if p.product_code == "PROD002")
        assert price2.price == 250.5
        assert price2.currency == "RUB"

        mock_connector.disconnect()

    def test_current_prices_fetch_without_connection(self, mock_connector):
        """Тест получения цен без подключения."""
        with pytest.raises(ERPConnectionError):
            mock_connector.get_current_prices(["PROD001"])

    def test_inventory_check(self, mock_connector):
        """Тест проверки остатков на складе."""
        mock_connector.connect()

        inventory = mock_connector.check_inventory_levels(["PROD001", "PROD002"])
        assert len(inventory) == 2

        inv1 = next(inv for inv in inventory if inv.product_code == "PROD001")
        assert inv1.quantity_available == 100.0
        assert inv1.quantity_reserved == 10.0
        assert inv1.warehouse_code == "WH001"
        assert inv1.unit_of_measure == "шт"

        inv2 = next(inv for inv in inventory if inv.product_code == "PROD002")
        assert inv2.quantity_available == 75.5
        assert inv2.quantity_reserved == 5.0
        assert inv2.unit_of_measure == "кг"

        mock_connector.disconnect()

    def test_inventory_check_with_warehouse_filter(self, mock_connector):
        """Тест проверки остатков с фильтром по складу."""
        mock_connector.connect()

        inventory = mock_connector.check_inventory_levels(["PROD001"], "WH001")
        assert len(inventory) == 1
        assert inventory[0].warehouse_code == "WH001"

        # Тест с несуществующим складом
        inventory = mock_connector.check_inventory_levels(["PROD001"], "WH999")
        assert len(inventory) == 0

        mock_connector.disconnect()

    def test_inventory_check_without_connection(self, mock_connector):
        """Тест проверки остатков без подключения."""
        with pytest.raises(ERPConnectionError):
            mock_connector.check_inventory_levels(["PROD001"])


class TestERPConnectorFactory:
    """Тесты для фабрики ERP коннекторов."""

    def test_create_mock_connector(self):
        """Тест создания мок-коннектора."""
        config = ERPConnectionConfig(
            system_type=ERPSystemType.CUSTOM,
            host="mock",
            port=8080,
            database="test",
            username="user",
            password="pass",
        )

        connector = create_erp_connector(config)
        assert isinstance(connector, MockERPConnector)

    def test_create_unsupported_connector(self):
        """Тест создания неподдерживаемого коннектора."""
        config = ERPConnectionConfig(
            system_type=ERPSystemType.SAP,
            host="sap.example.com",
            port=3300,
            database="sap_db",
            username="sap_user",
            password="sap_pass",
        )

        with pytest.raises(ValueError, match="ERP система sap пока не поддерживается"):
            create_erp_connector(config)


class TestERPHelperFunctions:
    """Тесты для вспомогательных функций ERP."""

    @pytest.fixture
    def mock_config(self):
        """Фикстура с мок-конфигурацией."""
        return ERPConnectionConfig(
            system_type=ERPSystemType.CUSTOM,
            host="mock",
            port=8080,
            database="mock_db",
            username="mock_user",
            password="mock_pass",
        )

    def test_get_product_info_from_erp_success(self, mock_config):
        """Тест успешного получения информации о товаре."""
        product = get_product_info_from_erp("PROD001", mock_config)

        assert product is not None
        assert product.product_code == "PROD001"
        assert product.name == "Тестовый товар 1"
        assert product.current_price == 100.0

    def test_get_product_info_from_erp_not_found(self, mock_config):
        """Тест получения информации о несуществующем товаре."""
        product = get_product_info_from_erp("NONEXISTENT", mock_config)
        assert product is None

    @patch("erp_integration.logging.error")
    def test_get_product_info_from_erp_error(self, mock_log, mock_config):
        """Тест обработки ошибки при получении информации о товаре."""
        # Создаем конфигурацию с неподдерживаемой системой
        error_config = ERPConnectionConfig(
            system_type=ERPSystemType.SAP,
            host="error.example.com",
            port=3300,
            database="error_db",
            username="error_user",
            password="error_pass",
        )

        product = get_product_info_from_erp("PROD001", error_config)
        assert product is None
        mock_log.assert_called_once()

    def test_get_current_prices_from_erp_success(self, mock_config):
        """Тест успешного получения цен."""
        prices = get_current_prices_from_erp(["PROD001", "PROD002"], mock_config)

        assert len(prices) == 2
        assert all(isinstance(p, PriceInfo) for p in prices)
        assert any(p.product_code == "PROD001" and p.price == 100.0 for p in prices)
        assert any(p.product_code == "PROD002" and p.price == 250.5 for p in prices)

    def test_get_current_prices_from_erp_empty_list(self, mock_config):
        """Тест получения цен для пустого списка товаров."""
        prices = get_current_prices_from_erp([], mock_config)
        assert len(prices) == 0

    @patch("erp_integration.logging.error")
    def test_get_current_prices_from_erp_error(self, mock_log, mock_config):
        """Тест обработки ошибки при получении цен."""
        error_config = ERPConnectionConfig(
            system_type=ERPSystemType.SAP,
            host="error.example.com",
            port=3300,
            database="error_db",
            username="error_user",
            password="error_pass",
        )

        prices = get_current_prices_from_erp(["PROD001"], error_config)
        assert len(prices) == 0
        mock_log.assert_called_once()

    def test_check_inventory_levels_from_erp_success(self, mock_config):
        """Тест успешной проверки остатков."""
        inventory = check_inventory_levels_from_erp(["PROD001", "PROD002"], mock_config)

        assert len(inventory) == 2
        assert all(isinstance(inv, InventoryInfo) for inv in inventory)

        inv1 = next(inv for inv in inventory if inv.product_code == "PROD001")
        assert inv1.quantity_available == 100.0
        assert inv1.warehouse_code == "WH001"

    def test_check_inventory_levels_from_erp_with_warehouse(self, mock_config):
        """Тест проверки остатков с указанием склада."""
        inventory = check_inventory_levels_from_erp(["PROD001"], mock_config, "WH001")

        assert len(inventory) == 1
        assert inventory[0].warehouse_code == "WH001"

    @patch("erp_integration.logging.error")
    def test_check_inventory_levels_from_erp_error(self, mock_log, mock_config):
        """Тест обработки ошибки при проверке остатков."""
        error_config = ERPConnectionConfig(
            system_type=ERPSystemType.SAP,
            host="error.example.com",
            port=3300,
            database="error_db",
            username="error_user",
            password="error_pass",
        )

        inventory = check_inventory_levels_from_erp(["PROD001"], error_config)
        assert len(inventory) == 0
        mock_log.assert_called_once()


class TestDataClasses:
    """Тесты для классов данных."""

    def test_product_info_creation(self):
        """Тест создания объекта ProductInfo."""
        product = ProductInfo(
            product_code="TEST001",
            name="Тестовый товар",
            description="Описание",
            unit_of_measure="шт",
            current_price=150.0,
            currency="RUB",
            category="Тест",
        )

        assert product.product_code == "TEST001"
        assert product.name == "Тестовый товар"
        assert product.current_price == 150.0
        assert product.supplier_id is None  # default value

    def test_inventory_info_creation(self):
        """Тест создания объекта InventoryInfo."""
        now = datetime.now()
        inventory = InventoryInfo(
            product_code="TEST001",
            warehouse_code="WH001",
            quantity_available=50.0,
            quantity_reserved=5.0,
            quantity_ordered=20.0,
            unit_of_measure="шт",
            last_updated=now,
        )

        assert inventory.product_code == "TEST001"
        assert inventory.warehouse_code == "WH001"
        assert inventory.quantity_available == 50.0
        assert inventory.last_updated == now
        assert inventory.min_stock_level is None  # default value

    def test_price_info_creation(self):
        """Тест создания объекта PriceInfo."""
        now = datetime.now()
        price = PriceInfo(
            product_code="TEST001",
            price=200.0,
            currency="RUB",
            price_type="base",
            valid_from=now,
        )

        assert price.product_code == "TEST001"
        assert price.price == 200.0
        assert price.currency == "RUB"
        assert price.price_type == "base"
        assert price.valid_from == now
        assert price.valid_to is None  # default value
        assert price.supplier_id is None  # default value


class TestInventoryFunctions:
    """Тесты для функций работы с остатками (Task 2.1.3)."""

    def setup_method(self):
        """Настройка для каждого теста."""
        self.config = ERPConnectionConfig(
            system_type=ERPSystemType.CUSTOM,
            host="mock",
            port=8080,
            database="test_db",
            username="test_user",
            password="test_pass",
        )

    def test_check_inventory_levels_success(self):
        """Тест успешной проверки остатков."""
        from erp_integration import check_inventory_levels

        inventory = check_inventory_levels(["PROD001", "PROD002"], self.config)

        assert len(inventory) == 2
        assert inventory[0].product_code == "PROD001"
        assert inventory[0].quantity_available == 100.0
        assert inventory[1].product_code == "PROD002"
        assert inventory[1].quantity_available == 75.5

    def test_check_inventory_levels_with_warehouse(self):
        """Тест проверки остатков с указанием склада."""
        from erp_integration import check_inventory_levels

        inventory = check_inventory_levels(
            ["PROD001"], self.config, warehouse_code="WH001"
        )

        assert len(inventory) == 1
        assert inventory[0].warehouse_code == "WH001"

    def test_check_inventory_levels_not_found(self):
        """Тест проверки остатков для несуществующего товара."""
        from erp_integration import check_inventory_levels

        inventory = check_inventory_levels(["NONEXISTENT"], self.config)

        assert len(inventory) == 0

    def test_get_low_stock_products_success(self):
        """Тест получения товаров с низкими остатками."""
        from erp_integration import get_low_stock_products

        low_stock = get_low_stock_products(self.config, threshold_percentage=0.5)

        # Проверяем, что функция возвращает список
        assert isinstance(low_stock, list)
        # В мок-данных должны быть товары с низкими остатками
        for item in low_stock:
            assert hasattr(item, "product_code")
            assert hasattr(item, "quantity_available")
            assert hasattr(item, "min_stock_level")

    def test_get_low_stock_products_with_warehouse(self):
        """Тест получения товаров с низкими остатками для конкретного склада."""
        from erp_integration import get_low_stock_products

        low_stock = get_low_stock_products(self.config, warehouse_code="WH001")

        assert isinstance(low_stock, list)
        for item in low_stock:
            assert item.warehouse_code == "WH001"

    def test_get_warehouse_summary_success(self):
        """Тест получения сводки по складу."""
        from erp_integration import get_warehouse_summary

        summary = get_warehouse_summary(self.config)

        assert isinstance(summary, dict)
        assert "warehouse_code" in summary
        assert "total_products" in summary
        assert "total_quantity" in summary
        assert "total_reserved" in summary
        assert "total_ordered" in summary
        assert "low_stock_count" in summary
        assert "products_by_category" in summary
        assert "last_updated" in summary

        assert summary["warehouse_code"] == "ALL"
        assert summary["total_products"] >= 0
        assert summary["total_quantity"] >= 0.0

    def test_get_warehouse_summary_specific_warehouse(self):
        """Тест получения сводки для конкретного склада."""
        from erp_integration import get_warehouse_summary

        summary = get_warehouse_summary(self.config, warehouse_code="WH001")

        assert isinstance(summary, dict)
        assert summary["warehouse_code"] == "WH001"

    def test_check_product_availability_sufficient(self):
        """Тест проверки доступности товара - достаточное количество."""
        from erp_integration import check_product_availability

        availability = check_product_availability("PROD001", 50.0, self.config)

        assert isinstance(availability, dict)
        assert availability["product_code"] == "PROD001"
        assert availability["available"] is True
        assert availability["available_quantity"] >= 50.0
        assert availability["required_quantity"] == 50.0
        assert availability["shortage"] == 0.0
        assert "reason" in availability
        assert "warehouse_code" in availability
        assert "unit_of_measure" in availability
        assert "last_updated" in availability

    def test_check_product_availability_insufficient(self):
        """Тест проверки доступности товара - недостаточное количество."""
        from erp_integration import check_product_availability

        availability = check_product_availability("PROD001", 200.0, self.config)

        assert isinstance(availability, dict)
        assert availability["product_code"] == "PROD001"
        assert availability["available"] is False
        assert availability["available_quantity"] < 200.0
        assert availability["required_quantity"] == 200.0
        assert availability["shortage"] > 0.0
        assert "Недостаточно товара" in availability["reason"]

    def test_check_product_availability_not_found(self):
        """Тест проверки доступности несуществующего товара."""
        from erp_integration import check_product_availability

        availability = check_product_availability("NONEXISTENT", 10.0, self.config)

        assert isinstance(availability, dict)
        assert availability["product_code"] == "NONEXISTENT"
        assert availability["available"] is False
        assert availability["available_quantity"] == 0.0
        assert availability["required_quantity"] == 10.0
        assert availability["shortage"] == 10.0
        assert "не найден" in availability["reason"]

    def test_check_product_availability_with_warehouse(self):
        """Тест проверки доступности товара для конкретного склада."""
        from erp_integration import check_product_availability

        availability = check_product_availability(
            "PROD001", 10.0, self.config, warehouse_code="WH001"
        )

        assert isinstance(availability, dict)
        assert availability["product_code"] == "PROD001"
        if availability["available"]:
            assert "warehouse_code" in availability

    def test_inventory_functions_error_handling(self):
        """Тест обработки ошибок в функциях работы с остатками."""
        from erp_integration import (
            check_product_availability,
            get_low_stock_products,
            get_warehouse_summary,
        )

        # Создаем неправильную конфигурацию
        bad_config = ERPConnectionConfig(
            system_type=ERPSystemType.SAP,  # Неподдерживаемый тип
            host="invalid",
            port=0,
            database="",
            username="",
            password="",
        )

        # Все функции должны корректно обрабатывать ошибки
        low_stock = get_low_stock_products(bad_config)
        assert isinstance(low_stock, list)
        assert len(low_stock) == 0

        summary = get_warehouse_summary(bad_config)
        assert isinstance(summary, dict)
        assert len(summary) == 0

        availability = check_product_availability("PROD001", 10.0, bad_config)
        assert isinstance(availability, dict)
        assert availability["available"] is False
        # Может быть либо "Ошибка проверки", либо "Товар не найден на складе"
        assert (
            "Ошибка проверки" in availability["reason"]
            or "не найден" in availability["reason"]
        )


class TestAdditionalERPFunctions:
    """Тесты для дополнительных функций ERP интеграции."""

    def setup_method(self):
        """Настройка для каждого теста."""
        self.config = ERPConnectionConfig(
            system_type=ERPSystemType.CUSTOM,
            host="mock",
            port=8080,
            database="test_db",
            username="test_user",
            password="test_pass",
        )

    @pytest.fixture
    def erp_config(self):
        """Фикстура для конфигурации ERP."""
        return ERPConnectionConfig(
            system_type=ERPSystemType.CUSTOM,
            host="mock",
            port=8080,
            database="test",
            username="user",
            password="pass",
        )

    def test_get_product_info_success(self, erp_config):
        """Тест успешного получения информации о товаре."""
        from erp_integration import get_product_info

        product = get_product_info("PROD001", erp_config)

        assert product is not None
        assert product.product_code == "PROD001"
        assert product.name == "Тестовый товар 1"
        assert product.current_price == 100.0

    def test_get_product_info_not_found(self, erp_config):
        """Тест получения информации о несуществующем товаре."""
        from erp_integration import get_product_info

        product = get_product_info("NONEXISTENT", erp_config)

        assert product is None

    def test_get_current_prices_success(self, erp_config):
        """Тест успешного получения текущих цен."""
        from erp_integration import get_current_prices

        prices = get_current_prices(["PROD001", "PROD002"], erp_config)

        assert len(prices) == 2
        assert any(p.product_code == "PROD001" and p.price == 100.0 for p in prices)
        assert any(p.product_code == "PROD002" and p.price == 250.5 for p in prices)

    def test_get_current_prices_empty_list(self, erp_config):
        """Тест получения цен для пустого списка товаров."""
        from erp_integration import get_current_prices

        prices = get_current_prices([], erp_config)

        assert len(prices) == 0

    def test_get_products_by_category_success(self, erp_config):
        """Тест успешного получения товаров по категории."""
        from erp_integration import get_products_by_category

        products = get_products_by_category("Категория 1", erp_config)

        assert len(products) >= 1
        for product in products:
            assert product.category == "Категория 1"

    def test_get_products_by_category_with_limit(self, erp_config):
        """Тест получения товаров по категории с ограничением."""
        from erp_integration import get_products_by_category

        products = get_products_by_category("Категория 1", erp_config, limit=1)

        assert len(products) <= 1

    def test_get_products_by_category_not_found(self, erp_config):
        """Тест получения товаров несуществующей категории."""
        from erp_integration import get_products_by_category

        products = get_products_by_category("Несуществующая категория", erp_config)

        assert len(products) == 0

    def test_search_products_success(self, erp_config):
        """Тест успешного поиска товаров."""
        from erp_integration import search_products

        products = search_products("Тестовый", erp_config)

        assert len(products) >= 1
        for product in products:
            assert (
                "тестовый" in product.name.lower()
                or "тестовый" in product.description.lower()
            )

    def test_search_products_with_limit(self, erp_config):
        """Тест поиска товаров с ограничением результатов."""
        from erp_integration import search_products

        products = search_products("товар", erp_config, limit=1)

        assert len(products) <= 1

    def test_search_products_not_found(self, erp_config):
        """Тест поиска несуществующих товаров."""
        from erp_integration import search_products

        products = search_products("Несуществующий товар", erp_config)

        assert len(products) == 0

    def test_get_product_price_history_success(self, erp_config):
        """Тест успешного получения истории цен товара."""
        from erp_integration import get_product_price_history

        history = get_product_price_history("PROD001", erp_config, days_back=5)

        assert len(history) == 5
        for price_info in history:
            assert price_info.product_code == "PROD001"
            assert price_info.price > 0
            assert price_info.price_type == "historical"

    def test_get_product_price_history_not_found(self, erp_config):
        """Тест получения истории цен несуществующего товара."""
        from erp_integration import get_product_price_history

        history = get_product_price_history("NONEXISTENT", erp_config)

        assert len(history) == 0

    def test_get_product_price_history_default_days(self, erp_config):
        """Тест получения истории цен с параметрами по умолчанию."""
        from erp_integration import get_product_price_history

        history = get_product_price_history("PROD001", erp_config)

        # Для мок-коннектора ограничиваем до 10 дней
        assert len(history) == 10
        for price_info in history:
            assert price_info.product_code == "PROD001"
