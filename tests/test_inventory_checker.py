"""Тесты для модуля inventory_checker."""

import json
import tempfile
from pathlib import Path

import pytest

from inventory_checker import (
    InventoryChecker,
    calculate_total_required_quantity,
    get_availability_summary,
    load_inventory_from_file,
)
from src.models import CheckResult, ProductSpecification


class TestInventoryChecker:
    """Тесты для класса InventoryChecker."""

    def setup_method(self):
        """Настройка для каждого теста."""
        self.inventory_data = {
            "CABLE_001": {
                "quantity": 100,
                "status": "в наличии",
                "location": "Склад А",
                "reserved": 10,
                "last_updated": "2024-01-15T10:00:00",
            },
            "CABLE_002": {
                "quantity": 50,
                "status": "в наличии",
                "location": "Склад Б",
                "reserved": 5,
                "last_updated": "2024-01-15T10:00:00",
            },
            "SWITCH_001": {
                "quantity": 0,
                "status": "под заказ",
                "location": "",
                "reserved": 0,
                "last_updated": "2024-01-15T10:00:00",
            },
            "ROUTER_001": {
                "quantity": 0,
                "status": "нет в наличии",
                "location": "",
                "reserved": 0,
                "last_updated": "2024-01-15T10:00:00",
            },
            "SERVER_001": {
                "quantity": 5,
                "status": "в наличии",
                "location": "Склад В",
                "reserved": 3,
                "last_updated": "2024-01-15T10:00:00",
            },
        }
        self.checker = InventoryChecker(self.inventory_data)

    def test_inventory_checker_initialization(self):
        """Тест инициализации InventoryChecker."""
        # Инициализация без данных о наличии
        checker = InventoryChecker()
        assert checker.inventory_data == {}

        # Инициализация с данными о наличии
        checker = InventoryChecker(self.inventory_data)
        assert checker.inventory_data == self.inventory_data

    def test_load_inventory_data_from_dict(self):
        """Тест загрузки данных о наличии из словаря."""
        inventory_dict = {
            "ITEM_001": {
                "quantity": 100,
                "status": "в наличии",
                "location": "Склад А",
                "reserved": 10,
            },
            "ITEM_002": {"quantity": 50, "status": "под заказ"},
        }

        checker = InventoryChecker()
        checker.load_inventory_data(inventory_dict)

        assert checker.inventory_data["ITEM_001"]["quantity"] == 100
        assert checker.inventory_data["ITEM_001"]["status"] == "в наличии"
        assert checker.inventory_data["ITEM_001"]["location"] == "Склад А"
        assert checker.inventory_data["ITEM_001"]["reserved"] == 10

        assert checker.inventory_data["ITEM_002"]["quantity"] == 50
        assert checker.inventory_data["ITEM_002"]["status"] == "под заказ"
        assert checker.inventory_data["ITEM_002"]["location"] == ""
        assert checker.inventory_data["ITEM_002"]["reserved"] == 0

    def test_load_inventory_data_from_json_string(self):
        """Тест загрузки данных о наличии из JSON строки."""
        inventory_json = """
        {
            "ITEM_001": {
                "quantity": 100,
                "status": "в наличии",
                "location": "Склад А",
                "reserved": 10
            }
        }
        """

        checker = InventoryChecker()
        checker.load_inventory_data(inventory_json)

        assert checker.inventory_data["ITEM_001"]["quantity"] == 100
        assert checker.inventory_data["ITEM_001"]["status"] == "в наличии"

    def test_load_inventory_data_invalid_json(self):
        """Тест загрузки некорректного JSON."""
        invalid_json = '{"ITEM_001": {"quantity": 100, "status":}}'

        checker = InventoryChecker()
        with pytest.raises(ValueError, match="Некорректный формат данных о наличии"):
            checker.load_inventory_data(invalid_json)

    def test_load_inventory_data_missing_required_fields(self):
        """Тест загрузки данных с отсутствующими обязательными полями."""
        inventory_dict = {
            "ITEM_001": {
                "location": "Склад А"  # Отсутствуют quantity и status
            }
        }

        checker = InventoryChecker()
        checker.load_inventory_data(inventory_dict)

        # Товар с неполными данными должен быть пропущен
        assert "ITEM_001" not in checker.inventory_data

    def test_get_available_quantity(self):
        """Тест получения доступного количества товара."""
        # Товар с резервом
        available = self.checker.get_available_quantity("CABLE_001")
        assert available == 90  # 100 - 10

        # Товар без резерва
        available = self.checker.get_available_quantity("SWITCH_001")
        assert available == 0  # 0 - 0

        # Неизвестный товар
        available = self.checker.get_available_quantity("UNKNOWN_001")
        assert available == 0

    def test_check_availability_sufficient_stock(self):
        """Тест проверки наличия при достаточном количестве."""
        result = self.checker.check_availability("CABLE_001", 50)

        assert isinstance(result, CheckResult)
        assert result.match == "да"
        assert result.check_type == "складской"
        assert result.product_code == "CABLE_001"
        assert result.expected_quantity == 50
        assert result.actual_quantity == 90
        assert result.availability_check == "в наличии"
        assert result.quantity_check == "достаточно"
        assert "в наличии: 90 шт." in result.comments
        assert "Склад А" in result.comments

    def test_check_availability_insufficient_stock(self):
        """Тест проверки наличия при недостаточном количестве."""
        result = self.checker.check_availability("SERVER_001", 5)

        assert result.match == "нет"
        assert result.expected_quantity == 5
        assert result.actual_quantity == 2  # 5 - 3
        assert result.availability_check == "нет в наличии"
        assert result.quantity_check == "недостаточно"
        assert "Недостаточное количество" in result.comments
        assert "доступно 2 шт., требуется 5 шт." in result.comments

    def test_check_availability_out_of_stock(self):
        """Тест проверки наличия отсутствующего товара."""
        result = self.checker.check_availability("ROUTER_001", 1)

        assert result.match == "нет"
        assert result.availability_check == "нет в наличии"
        assert result.quantity_check == "недостаточно"
        assert "отсутствует на складе" in result.comments

    def test_check_availability_on_order(self):
        """Тест проверки товара под заказ."""
        result = self.checker.check_availability("SWITCH_001", 1)

        assert result.match == "частично"
        assert result.availability_check == "под заказ"
        assert "доступен под заказ" in result.comments

    def test_check_availability_unknown_product(self):
        """Тест проверки неизвестного товара."""
        result = self.checker.check_availability("UNKNOWN_001", 1)

        assert result.match == "нет"
        assert result.availability_check == "нет в наличии"
        assert "не найден в складском учете" in result.comments

    def test_check_availability_invalid_quantity(self):
        """Тест проверки с некорректным количеством."""
        result = self.checker.check_availability("CABLE_001", 0)

        assert result.match == "нет"
        assert result.availability_check == "не проверялась"
        assert "Некорректное требуемое количество" in result.comments

        result = self.checker.check_availability("CABLE_001", -5)

        assert result.match == "нет"
        assert result.availability_check == "не проверялась"
        assert "Некорректное требуемое количество" in result.comments

    def test_check_multiple_availability(self):
        """Тест проверки наличия нескольких товаров."""
        products = {
            "CABLE_001": 50,  # Достаточно
            "CABLE_002": 100,  # Недостаточно
            "SWITCH_001": 1,  # Под заказ
            "UNKNOWN_001": 1,  # Неизвестный товар
        }

        results = self.checker.check_multiple_availability(products)

        assert len(results) == 4
        assert results[0].match == "да"  # CABLE_001
        assert results[1].match == "нет"  # CABLE_002
        assert results[2].match == "частично"  # SWITCH_001
        assert results[3].match == "нет"  # UNKNOWN_001

    def test_check_product_specifications(self):
        """Тест проверки товарных спецификаций."""
        specifications = [
            ProductSpecification(
                product_code="CABLE_001",
                product_name="Кабель сетевой",
                quantity=30,
                unit="шт",
                unit_price=100.0,
                total_amount=3000.0,
                availability_status="в наличии",
            ),
            ProductSpecification(
                product_code="SERVER_001",
                product_name="Сервер",
                quantity=5,
                unit="шт",
                unit_price=50000.0,
                total_amount=250000.0,
                availability_status="в наличии",
            ),
        ]

        results = self.checker.check_product_specifications(specifications)

        assert len(results) == 2
        assert results[0].match == "да"  # CABLE_001 - достаточно
        assert results[1].match == "нет"  # SERVER_001 - недостаточно

    def test_get_low_stock_items(self):
        """Тест получения товаров с низким остатком."""
        # Тест с порогом 10
        low_stock = self.checker.get_low_stock_items(threshold=10)

        # Ожидаем только SERVER_001 (доступно 2 шт.)
        # SWITCH_001 и ROUTER_001 исключены из-за статуса "под заказ" и "нет в наличии"
        # CABLE_001 и CABLE_002 имеют больше 10 шт.
        assert len(low_stock) == 1
        assert low_stock[0]["product_code"] == "SERVER_001"
        assert low_stock[0]["available_quantity"] == 2

        # Тест с порогом 50
        low_stock = self.checker.get_low_stock_items(threshold=50)

        # Ожидаем SERVER_001 (2 шт.) и CABLE_002 (45 шт.)
        # SWITCH_001 и ROUTER_001 по-прежнему исключены
        assert len(low_stock) == 2
        assert low_stock[0]["product_code"] == "SERVER_001"  # Меньше всего
        assert low_stock[1]["product_code"] == "CABLE_002"

    def test_simulate_api_request(self):
        """Тест симуляции API запроса."""
        # Существующий товар
        api_data = self.checker.simulate_api_request("CABLE_001")
        assert api_data == self.inventory_data["CABLE_001"]

        # Несуществующий товар
        api_data = self.checker.simulate_api_request("UNKNOWN_001")
        assert api_data["quantity"] == 0
        assert api_data["status"] == "не найден"
        assert "error" in api_data

    def test_refresh_inventory_data(self):
        """Тест обновления данных о наличии."""
        # Обновление конкретных товаров
        self.checker.refresh_inventory_data(["CABLE_001", "UNKNOWN_001"])

        # Данные должны остаться без изменений для существующих товаров
        assert "CABLE_001" in self.checker.inventory_data

        # Обновление всех товаров
        original_count = len(self.checker.inventory_data)
        self.checker.refresh_inventory_data()

        # Количество товаров должно остаться тем же
        assert len(self.checker.inventory_data) == original_count


class TestInventoryHelperFunctions:
    """Тесты для вспомогательных функций."""

    def test_load_inventory_from_file(self):
        """Тест загрузки данных о наличии из файла."""
        inventory_data = {
            "ITEM_001": {
                "quantity": 100,
                "status": "в наличии",
                "location": "Склад А",
                "reserved": 10,
            }
        }

        # Создаем временный файл
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as temp_file:
            json.dump(inventory_data, temp_file, ensure_ascii=False)
            temp_file_path = temp_file.name

        try:
            # Загружаем данные из файла
            loaded_data = load_inventory_from_file(temp_file_path)
            assert loaded_data == inventory_data
        finally:
            # Удаляем временный файл
            Path(temp_file_path).unlink()

    def test_load_inventory_from_nonexistent_file(self):
        """Тест загрузки из несуществующего файла."""
        with pytest.raises(
            FileNotFoundError, match="Файл с данными о наличии не найден"
        ):
            load_inventory_from_file("nonexistent_file.json")

    def test_calculate_total_required_quantity(self):
        """Тест расчета общего требуемого количества."""
        products = {"ITEM_001": 10, "ITEM_002": 25, "ITEM_003": 5}

        total = calculate_total_required_quantity(products)
        assert total == 40

        # Пустой словарь
        total = calculate_total_required_quantity({})
        assert total == 0

    def test_get_availability_summary(self):
        """Тест создания сводки по результатам проверки."""
        results = [
            CheckResult(
                section="Test 1",
                match="да",
                check_type="складской",
                availability_check="в наличии",
            ),
            CheckResult(
                section="Test 2",
                match="нет",
                check_type="складской",
                availability_check="нет в наличии",
            ),
            CheckResult(
                section="Test 3",
                match="частично",
                check_type="складской",
                availability_check="под заказ",
            ),
            CheckResult(
                section="Test 4",
                match="да",
                check_type="складской",
                availability_check="в наличии",
            ),
        ]

        summary = get_availability_summary(results)

        assert summary["total_products"] == 4
        assert summary["available"] == 2
        assert summary["partially_available"] == 1
        assert summary["not_available"] == 1
        assert summary["not_checked"] == 0


class TestInventoryCheckerIntegration:
    """Интеграционные тесты для InventoryChecker."""

    def setup_method(self):
        """Настройка для интеграционных тестов."""
        self.inventory_data = {
            "CABLE_001": {
                "quantity": 100,
                "status": "в наличии",
                "location": "Склад А",
                "reserved": 10,
                "last_updated": "2024-01-15T10:00:00",
            },
            "SWITCH_001": {
                "quantity": 0,
                "status": "под заказ",
                "location": "",
                "reserved": 0,
                "last_updated": "2024-01-15T10:00:00",
            },
        }
        self.checker = InventoryChecker(self.inventory_data)

    def test_full_availability_check_workflow(self):
        """Тест полного workflow проверки наличия."""
        # Проверяем наличие товара
        result = self.checker.check_availability("CABLE_001", 50)

        assert result.match == "да"
        assert result.availability_check == "в наличии"
        assert result.quantity_check == "достаточно"

        # Получаем сводку по низким остаткам
        low_stock = self.checker.get_low_stock_items(threshold=100)
        # Ожидаем только CABLE_001, так как SWITCH_001 исключен из-за статуса "под заказ"
        assert len(low_stock) == 1
        assert low_stock[0]["product_code"] == "CABLE_001"

    def test_availability_check_workflow(self):
        """Тест workflow проверки наличия нескольких товаров."""
        products = {"CABLE_001": 30, "SWITCH_001": 1}

        # Проверяем наличие
        results = self.checker.check_multiple_availability(products)

        assert len(results) == 2
        assert results[0].match == "да"  # CABLE_001
        assert results[1].match == "частично"  # SWITCH_001

        # Создаем сводку
        summary = get_availability_summary(results)
        assert summary["available"] == 1
        assert summary["partially_available"] == 1
        assert summary["not_available"] == 0
