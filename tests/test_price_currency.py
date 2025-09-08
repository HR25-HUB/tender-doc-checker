"""
Tests for currency conversion functionality in price checking.

This module tests:
1. Currency conversion using mocked exchange rate sources
2. Deviation calculation after currency conversion
3. Mocking external exchange rate APIs
"""

from decimal import Decimal
from unittest.mock import Mock, patch

import pytest

from price_checker import PriceChecker
from src.models import PriceRecord


class TestCurrencyConversion:
    """Test currency conversion and deviation calculation after conversion."""

    def test_convert_price_usd_to_rub(self):
        """Test conversion from USD to RUB using mocked exchange rates."""
        # Arrange
        price_checker = PriceChecker()
        price_record = PriceRecord(
            sku="ITEM-001",
            price=Decimal("100.00"),
            currency="USD",
            supplier="Supplier A",
        )

        # Mock exchange rate: 1 USD = 90 RUB
        mock_rate = Decimal("90.00")

        with patch.object(
            price_checker.rate_provider, "get_rate", return_value=mock_rate
        ):
            # Act
            converted_price = price_checker.convert_currency(
                price_record, target_currency="RUB"
            )

            # Assert
            assert converted_price == Decimal("9000.00")

    def test_convert_price_eur_to_rub(self):
        """Test conversion from EUR to RUB using mocked exchange rates."""
        # Arrange
        price_checker = PriceChecker()
        price_record = PriceRecord(
            sku="ITEM-002",
            price=Decimal("50.00"),
            currency="EUR",
            supplier="Supplier B",
        )

        # Mock exchange rate: 1 EUR = 95 RUB
        mock_rate = Decimal("95.00")

        with patch.object(
            price_checker.rate_provider, "get_rate", return_value=mock_rate
        ):
            # Act
            converted_price = price_checker.convert_currency(
                price_record, target_currency="RUB"
            )

            # Assert
            assert converted_price == Decimal("4750.00")

    def test_calculate_deviation_after_conversion(self):
        """Test deviation calculation after currency conversion."""
        # Arrange
        price_checker = PriceChecker()

        # Two prices in different currencies
        price1 = PriceRecord(
            sku="ITEM-003",
            price=Decimal("100.00"),
            currency="USD",
            supplier="Supplier A",
        )
        price2 = PriceRecord(
            sku="ITEM-003",
            price=Decimal("9500.00"),
            currency="RUB",
            supplier="Supplier B",
        )

        # Mock exchange rate: 1 USD = 95 RUB
        mock_rate = Decimal("95.00")

        with patch.object(
            price_checker.rate_provider, "get_rate", return_value=mock_rate
        ):
            # Act
            deviation = price_checker.calculate_deviation_after_conversion(
                price1, price2
            )

            # Assert
            # price1 in RUB = 100 * 95 = 9500
            # price2 in RUB = 9500
            # deviation = 0%
            assert deviation == Decimal("0.00")

    def test_calculate_deviation_with_different_prices(self):
        """Test deviation calculation with different prices after conversion."""
        # Arrange
        price_checker = PriceChecker()

        price1 = PriceRecord(
            sku="ITEM-004",
            price=Decimal("100.00"),
            currency="USD",
            supplier="Supplier A",
        )
        price2 = PriceRecord(
            sku="ITEM-004",
            price=Decimal("8550.00"),
            currency="RUB",
            supplier="Supplier B",
        )

        # Mock exchange rate: 1 USD = 95 RUB
        mock_rate = Decimal("95.00")

        with patch.object(
            price_checker.rate_provider, "get_rate", return_value=mock_rate
        ):
            # Act
            deviation = price_checker.calculate_deviation_after_conversion(
                price1, price2
            )

            # Assert
            # price1 in RUB = 100 * 95 = 9500
            # price2 in RUB = 8550
            # deviation = (9500 - 8550) / 9500 * 100 = 10%
            assert deviation == Decimal("10.00")

    def test_same_currency_no_conversion_needed(self):
        """Test that no conversion is performed when currencies match."""
        # Arrange
        price_checker = PriceChecker()
        price_record = PriceRecord(
            sku="ITEM-005",
            price=Decimal("5000.00"),
            currency="RUB",
            supplier="Supplier C",
        )

        # Mock should not be called
        with patch.object(price_checker.rate_provider, "get_rate") as mock_get_rate:
            # Act
            converted_price = price_checker.convert_currency(
                price_record, target_currency="RUB"
            )

            # Assert
            assert converted_price == Decimal("5000.00")
            mock_get_rate.assert_not_called()

    def test_exchange_rate_not_found(self):
        """Test handling when exchange rate is not available."""
        # Arrange
        price_checker = PriceChecker()
        price_record = PriceRecord(
            sku="ITEM-006",
            price=Decimal("100.00"),
            currency="USD",
            supplier="Supplier A",
        )

        # Mock rate provider to raise exception
        with patch.object(
            price_checker.rate_provider,
            "get_rate",
            side_effect=ValueError("Rate not found"),
        ):
            # Act & Assert
            with pytest.raises(ValueError, match="Rate not found"):
                price_checker.convert_currency(price_record, target_currency="RUB")

    def test_mock_exchange_rate_provider(self):
        """Test that we can inject a mock exchange rate provider."""
        # Arrange
        mock_provider = Mock()
        mock_provider.get_rate.return_value = Decimal("88.50")

        price_checker = PriceChecker(rate_provider=mock_provider)
        price_record = PriceRecord(
            sku="ITEM-007",
            price=Decimal("200.00"),
            currency="USD",
            supplier="Supplier D",
        )

        # Act
        converted_price = price_checker.convert_currency(
            price_record, target_currency="RUB"
        )

        # Assert
        assert converted_price == Decimal("17700.00")
        mock_provider.get_rate.assert_called_once_with("USD", "RUB")

    def test_batch_currency_conversion(self):
        """Test batch conversion of multiple price records."""
        # Arrange
        price_checker = PriceChecker()

        price_records = [
            PriceRecord(
                sku="ITEM-008", price=Decimal("100.00"), currency="USD", supplier="A"
            ),
            PriceRecord(
                sku="ITEM-009", price=Decimal("200.00"), currency="EUR", supplier="B"
            ),
            PriceRecord(
                sku="ITEM-010", price=Decimal("5000.00"), currency="RUB", supplier="C"
            ),
        ]

        mock_rates = {
            ("USD", "RUB"): Decimal("95.00"),
            ("EUR", "RUB"): Decimal("105.00"),
        }

        def mock_get_rate(source_currency, target_currency):
            if source_currency == target_currency:
                return Decimal("1.00")
            return mock_rates[(source_currency, target_currency)]

        with patch.object(
            price_checker.rate_provider, "get_rate", side_effect=mock_get_rate
        ):
            # Act
            converted_prices = price_checker.convert_batch_to_currency(
                price_records, target_currency="RUB"
            )

            # Assert
            assert converted_prices[0] == Decimal("9500.00")  # 100 * 95
            assert converted_prices[1] == Decimal("21000.00")  # 200 * 105
            assert converted_prices[2] == Decimal("5000.00")  # Already RUB
