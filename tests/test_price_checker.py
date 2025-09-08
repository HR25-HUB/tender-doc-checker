"""Тесты для модуля price_checker."""

import json
import tempfile
from decimal import Decimal
from pathlib import Path

import pytest

from price_checker import (
    PriceChecker,
    PriceComparison,
    calculate_total_savings,
    load_base_prices_from_file,
)
from src.models import CheckResult


class TestPriceChecker:
    """Тесты для класса PriceChecker."""

    def setup_method(self):
        """Настройка для каждого теста."""
        self.base_prices = {
            "CABLE_001": Decimal("100.00"),
            "CABLE_002": Decimal("250.50"),
            "SWITCH_001": Decimal("1500.00"),
            "ROUTER_001": Decimal("3000.00"),
        }
        self.checker = PriceChecker(self.base_prices)

    def test_price_checker_initialization(self):
        """Тест инициализации PriceChecker."""
        # Инициализация без базовых цен
        checker = PriceChecker()
        assert checker.base_prices == {}

        # Инициализация с базовыми ценами
        checker = PriceChecker(self.base_prices)
        assert checker.base_prices == self.base_prices

    def test_load_base_prices_from_dict(self):
        """Тест загрузки базовых цен из словаря."""
        prices_dict = {"ITEM_001": 100.50, "ITEM_002": "200.75", "ITEM_003": 300}

        checker = PriceChecker()
        checker.load_base_prices(prices_dict)

        assert checker.base_prices["ITEM_001"] == Decimal("100.50")
        assert checker.base_prices["ITEM_002"] == Decimal("200.75")
        assert checker.base_prices["ITEM_003"] == Decimal("300")

    def test_load_base_prices_from_json_string(self):
        """Тест загрузки базовых цен из JSON строки."""
        prices_json = '{"ITEM_001": 100.50, "ITEM_002": 200.75}'

        checker = PriceChecker()
        checker.load_base_prices(prices_json)

        assert checker.base_prices["ITEM_001"] == Decimal("100.50")
        assert checker.base_prices["ITEM_002"] == Decimal("200.75")

    def test_load_base_prices_invalid_json(self):
        """Тест загрузки некорректного JSON."""
        invalid_json = '{"ITEM_001": 100.50, "ITEM_002":}'

        checker = PriceChecker()
        with pytest.raises(ValueError, match="Некорректный формат данных цен"):
            checker.load_base_prices(invalid_json)

    def test_calculate_price_deviation(self):
        """Тест расчета отклонения цены."""
        # Превышение на 20%
        deviation = self.checker.calculate_price_deviation(
            Decimal("100"), Decimal("120")
        )
        assert deviation == Decimal("20.00")

        # Снижение на 15%
        deviation = self.checker.calculate_price_deviation(
            Decimal("100"), Decimal("85")
        )
        assert deviation == Decimal("-15.00")

        # Без отклонения
        deviation = self.checker.calculate_price_deviation(
            Decimal("100"), Decimal("100")
        )
        assert deviation == Decimal("0.00")

        # Базовая цена равна нулю
        deviation = self.checker.calculate_price_deviation(Decimal("0"), Decimal("100"))
        assert deviation == Decimal("0.00")

    def test_check_price_within_tolerance(self):
        """Тест проверки цены в пределах допустимого отклонения."""
        result = self.checker.check_price("CABLE_001", "105.00", Decimal("10"))

        assert isinstance(result, CheckResult)
        assert result.match == "да"
        assert result.check_type == "ценовой"
        assert result.product_code == "CABLE_001"
        assert result.expected_price == 100.0
        assert result.actual_price == 105.0
        assert result.price_deviation_percent == 5.0
        assert result.price_check == "соответствует"
        assert "в пределах допустимого" in result.comments

    def test_check_price_exceeds_tolerance(self):
        """Тест проверки цены, превышающей допуск."""
        result = self.checker.check_price("CABLE_001", "125.00", Decimal("10"))

        assert result.match == "нет"
        assert result.price_deviation_percent == 25.0
        assert "превышает базовую на 25.0%" in result.comments
        assert result.price_check == "завышена"

    def test_check_price_below_tolerance(self):
        """Тест проверки цены ниже допуска."""
        result = self.checker.check_price("CABLE_001", "75.00", Decimal("10"))

        assert result.match == "нет"
        assert result.price_deviation_percent == -25.0
        assert "ниже базовой на 25.0%" in result.comments
        assert result.price_check == "занижена"

    def test_check_price_invalid_price(self):
        """Тест проверки некорректной цены."""
        result = self.checker.check_price("CABLE_001", "invalid_price")

        assert result.match == "нет"
        assert "Некорректная цена" in result.comments
        assert result.actual_price is None

    def test_check_price_unknown_product(self):
        """Тест проверки цены неизвестного товара."""
        result = self.checker.check_price("UNKNOWN_001", "100.00")

        assert result.match == "нет"
        assert "Базовая цена для товара UNKNOWN_001 не найдена" in result.comments

    def test_check_multiple_prices(self):
        """Тест проверки нескольких цен."""
        prices = {
            "CABLE_001": "105.00",  # В пределах допуска
            "CABLE_002": "300.00",  # Превышает допуск
            "SWITCH_001": "1400.00",  # В пределах допуска
        }

        results = self.checker.check_multiple_prices(prices, Decimal("10"))

        assert len(results) == 3
        assert results[0].match == "да"  # CABLE_001
        assert results[1].match == "нет"  # CABLE_002
        assert results[2].match == "да"  # SWITCH_001

    def test_compare_supplier_prices(self):
        """Тест сравнения цен от разных поставщиков."""
        supplier_prices = {
            "Supplier_A": {"CABLE_001": "95.00", "CABLE_002": "240.00"},
            "Supplier_B": {"CABLE_001": "110.00", "CABLE_002": "260.00"},
        }

        results = self.checker.compare_supplier_prices(supplier_prices, Decimal("10"))

        assert "Supplier_A" in results
        assert "Supplier_B" in results
        assert len(results["Supplier_A"]) == 2
        assert len(results["Supplier_B"]) == 2

        # Проверяем, что имена поставщиков установлены
        assert results["Supplier_A"][0].supplier_name == "Supplier_A"
        assert results["Supplier_B"][0].supplier_name == "Supplier_B"

    def test_create_price_comparison(self):
        """Тест создания сравнения цен."""
        comparison = self.checker.create_price_comparison(
            "CABLE_001", "100.00", "95.00"
        )

        assert isinstance(comparison, PriceComparison)
        assert comparison.product_code == "CABLE_001"
        assert comparison.current_price == 100.0
        assert comparison.proposed_price == 95.0
        assert comparison.price_difference == -5.0
        assert comparison.price_difference_percent == -5.0
        assert comparison.recommendation == "принять"

    def test_create_price_comparison_invalid_prices(self):
        """Тест создания сравнения с некорректными ценами."""
        with pytest.raises(ValueError, match="Некорректные цены для сравнения"):
            self.checker.create_price_comparison("CABLE_001", "invalid", "100.00")


class TestPriceComparisonFunctions:
    """Тесты для вспомогательных функций."""

    def test_load_base_prices_from_file(self):
        """Тест загрузки базовых цен из файла."""
        prices_data = {"ITEM_001": 100.50, "ITEM_002": 200.75, "ITEM_003": 300}

        # Создаем временный файл
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(prices_data, f)
            temp_file_path = f.name

        try:
            loaded_prices = load_base_prices_from_file(temp_file_path)

            assert loaded_prices["ITEM_001"] == Decimal("100.50")
            assert loaded_prices["ITEM_002"] == Decimal("200.75")
            assert loaded_prices["ITEM_003"] == Decimal("300")
        finally:
            Path(temp_file_path).unlink()

    def test_load_base_prices_from_nonexistent_file(self):
        """Тест загрузки из несуществующего файла."""
        loaded_prices = load_base_prices_from_file("nonexistent_file.json")
        assert loaded_prices == {}

    def test_calculate_total_savings(self):
        """Тест расчета общей экономии."""
        base_prices = {"ITEM_001": Decimal("100.00"), "ITEM_002": Decimal("200.00")}

        supplier_prices = {"ITEM_001": Decimal("95.00"), "ITEM_002": Decimal("210.00")}

        quantities = {"ITEM_001": 10, "ITEM_002": 5}

        savings = calculate_total_savings(base_prices, supplier_prices, quantities)

        # ITEM_001: (100 - 95) * 10 = 50 экономии
        # ITEM_002: (200 - 210) * 5 = -50 переплаты
        # Итого: 0 экономии

        assert savings["total_base_cost"] == 2000.0  # 100*10 + 200*5
        assert savings["total_supplier_cost"] == 2000.0  # 95*10 + 210*5
        assert savings["total_savings"] == 0.0
        assert savings["total_savings_percent"] == 0.0

        assert savings["savings_by_product"]["ITEM_001"]["savings"] == 50.0
        assert savings["savings_by_product"]["ITEM_002"]["savings"] == -50.0


class TestPriceCheckerIntegration:
    """Интеграционные тесты для PriceChecker."""

    def test_full_price_check_workflow(self):
        """Тест полного workflow проверки цен."""
        # Настройка
        base_prices = {"CABLE_001": Decimal("100.00"), "SWITCH_001": Decimal("1500.00")}
        checker = PriceChecker(base_prices)

        # Проверка цен от поставщика
        supplier_prices = {
            "CABLE_001": "105.00",  # +5% - в пределах допуска
            "SWITCH_001": "1650.00",  # +10% - на границе допуска
        }

        results = checker.check_multiple_prices(supplier_prices, Decimal("10"))

        # Проверяем результаты
        assert len(results) == 2
        assert all(result.match == "да" for result in results)

        # Создаем сравнение цен
        comparison = checker.create_price_comparison("CABLE_001", "105.00", "98.00")

        assert comparison.current_price == 105.0
        assert comparison.proposed_price == 98.0
        assert comparison.recommendation == "принять"

    def test_price_comparison_workflow(self):
        """Тест workflow сравнения цен от разных поставщиков."""
        checker = PriceChecker()

        # Загружаем базовые цены
        base_prices_data = {"CABLE_001": 100.00, "CABLE_002": 250.50}
        checker.load_base_prices(base_prices_data)

        # Сравниваем цены от трех поставщиков
        supplier_prices = {
            "Supplier_A": {"CABLE_001": "95.00", "CABLE_002": "240.00"},
            "Supplier_B": {"CABLE_001": "110.00", "CABLE_002": "260.00"},
            "Supplier_C": {"CABLE_001": "102.00", "CABLE_002": "245.00"},
        }

        results = checker.compare_supplier_prices(supplier_prices, Decimal("15"))

        # Все поставщики должны пройти проверку с допуском 15%
        for supplier_name, supplier_results in results.items():
            assert all(result.match == "да" for result in supplier_results)
            assert all(
                result.supplier_name == supplier_name for result in supplier_results
            )

        # Создаем сравнение цен (базовая vs лучшая цена от поставщика)
        cable_001_comparison = checker.create_price_comparison(
            "CABLE_001", "100.00", "95.00"
        )

        assert cable_001_comparison.current_price == 100.0
        assert cable_001_comparison.proposed_price == 95.0
        assert cable_001_comparison.recommendation == "принять"
