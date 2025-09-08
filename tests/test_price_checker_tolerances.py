"""
Tests for price checker tolerances by SKU categories.

This module tests the tolerance configuration and price checking logic
for different SKU categories as specified in the project requirements.
"""

import json
import os
import tempfile
from unittest.mock import patch

import pytest


class TestPriceCheckerTolerances:
    """Test suite for price checker tolerance functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.mock_config = {
            "categories": {
                "electronics": {"tolerance": 0.05, "description": "Электроника"},
                "clothing": {"tolerance": 0.10, "description": "Одежда"},
                "food": {"tolerance": 0.03, "description": "Продукты питания"},
                "construction": {
                    "tolerance": 0.08,
                    "description": "Строительные материалы",
                },
                "default": {"tolerance": 0.07, "description": "По умолчанию"},
            }
        }

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_category_tolerance_mapping(self):
        """Test that category tolerances are correctly mapped."""
        # Test that we can load category tolerances from config
        with patch("src.config.load_config") as mock_load:
            mock_load.return_value = self.mock_config

            from src.config import load_config

            config = load_config()

            assert "electronics" in config["categories"]
            assert config["categories"]["electronics"]["tolerance"] == 0.05
            assert config["categories"]["clothing"]["tolerance"] == 0.10

    def test_price_within_tolerance(self):
        """Test price checking within tolerance for specific category."""
        with patch("src.config.load_config") as mock_load:
            mock_load.return_value = self.mock_config

            from price_checker import check_price_tolerance

            # Test electronics category (5% tolerance)
            result = check_price_tolerance(
                category="electronics", expected_price=1000.0, actual_price=1020.0
            )
            assert result["within_tolerance"] is True
            assert result["deviation"] == 0.02  # 2% deviation
            assert result["tolerance_used"] == 0.05

    def test_price_exceeds_tolerance(self):
        """Test price checking when price exceeds tolerance."""
        with patch("src.config.load_config") as mock_load:
            mock_load.return_value = self.mock_config

            from price_checker import check_price_tolerance

            # Test food category (3% tolerance)
            result = check_price_tolerance(
                category="food", expected_price=100.0, actual_price=105.0
            )
            assert result["within_tolerance"] is False
            assert result["deviation"] == 0.05  # 5% deviation
            assert result["tolerance_used"] == 0.03

    def test_unknown_category_uses_default(self):
        """Test that unknown categories use default tolerance."""
        with patch("src.config.load_config") as mock_load:
            mock_load.return_value = self.mock_config

            from price_checker import check_price_tolerance

            result = check_price_tolerance(
                category="unknown_category", expected_price=1000.0, actual_price=1065.0
            )
            assert result["within_tolerance"] is True  # 6.5% vs 7% default
            assert result["tolerance_used"] == 0.07
            assert result["category_used"] == "default"

    def test_zero_tolerance_edge_case(self):
        """Test edge case with zero tolerance."""
        zero_tolerance_config = {
            "categories": {
                "precision_parts": {"tolerance": 0.0, "description": "Точные детали"},
                "default": {"tolerance": 0.05, "description": "По умолчанию"},
            }
        }

        with patch("src.config.load_config") as mock_load:
            mock_load.return_value = zero_tolerance_config

            from price_checker import check_price_tolerance

            result = check_price_tolerance(
                category="precision_parts", expected_price=100.0, actual_price=100.01
            )
            assert result["within_tolerance"] is False  # Any deviation > 0
            assert result["tolerance_used"] == 0.0

    def test_negative_tolerance_handling(self):
        """Test handling of negative tolerance values."""
        negative_tolerance_config = {
            "categories": {
                "electronics": {"tolerance": -0.05, "description": "Электроника"},
                "default": {"tolerance": 0.07, "description": "По умолчанию"},
            }
        }

        with patch("src.config.load_config") as mock_load:
            mock_load.return_value = negative_tolerance_config

            from price_checker import check_price_tolerance

            result = check_price_tolerance(
                category="electronics", expected_price=100.0, actual_price=95.0
            )
            # Should handle negative tolerance as absolute value
            assert result["within_tolerance"] is True

    def test_config_file_loading(self):
        """Test loading tolerance configuration from file."""
        config_path = os.path.join(self.temp_dir, "tolerances.yaml")

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(self.mock_config, f)

        with patch("src.config.CONFIG_PATH", config_path):
            from src.config import load_config

            config = load_config()

            assert "categories" in config
            assert len(config["categories"]) == 5

    def test_category_description_preservation(self):
        """Test that category descriptions are preserved in results."""
        with patch("src.config.load_config") as mock_load:
            mock_load.return_value = self.mock_config

            from price_checker import check_price_tolerance

            result = check_price_tolerance(
                category="construction", expected_price=1000.0, actual_price=1080.0
            )
            assert result["category_description"] == "Строительные материалы"
            assert result["tolerance_used"] == 0.08

    def test_multiple_categories_batch_check(self):
        """Test batch checking of prices across multiple categories."""
        with patch("src.config.load_config") as mock_load:
            mock_load.return_value = self.mock_config

            from price_checker import check_prices_batch

            items = [
                {"category": "electronics", "expected": 1000.0, "actual": 1020.0},
                {"category": "clothing", "expected": 500.0, "actual": 540.0},
                {"category": "food", "expected": 50.0, "actual": 48.5},
            ]

            results = check_prices_batch(items)

            assert len(results) == 3
            assert results[0]["within_tolerance"] is True  # 2% vs 5%
            assert results[1]["within_tolerance"] is True  # 8% vs 10%
            assert results[2]["within_tolerance"] is True  # 3% vs 3%

    def test_empty_category_config(self):
        """Test behavior with empty category configuration."""
        empty_config = {"categories": {}}

        with patch("src.config.load_config") as mock_load:
            mock_load.return_value = empty_config

            from price_checker import check_price_tolerance

            result = check_price_tolerance(
                category="electronics", expected_price=100.0, actual_price=105.0
            )
            # Should use default or handle gracefully
            assert "tolerance_used" in result

    def test_tolerance_precision(self):
        """Test precision handling for tolerance calculations."""
        with patch("src.config.load_config") as mock_load:
            mock_load.return_value = self.mock_config

            from price_checker import check_price_tolerance

            result = check_price_tolerance(
                category="electronics", expected_price=1000.123, actual_price=1050.123
            )

            assert abs(result["deviation"] - 0.05) < 0.001
            assert isinstance(result["deviation"], float)


class TestToleranceConfigValidation:
    """Test suite for tolerance configuration validation."""

    def test_valid_tolerance_range(self):
        """Test validation of tolerance ranges."""
        with patch("src.config.load_config") as mock_load:
            mock_load.return_value = {
                "categories": {"test": {"tolerance": 0.5, "description": "Test"}}
            }

            from src.config import validate_tolerance_config

            # Should warn about high tolerance (>1.0)
            with pytest.warns(UserWarning):
                validate_tolerance_config()

    def test_missing_tolerance_field(self):
        """Test handling of missing tolerance field."""
        with patch("src.config.load_config") as mock_load:
            mock_load.return_value = {
                "categories": {"incomplete": {"description": "Missing tolerance"}}
            }

            from src.config import validate_tolerance_config

            with pytest.raises(KeyError):
                validate_tolerance_config()

    def test_tolerance_type_validation(self):
        """Test type validation for tolerance values."""
        with patch("src.config.load_config") as mock_load:
            mock_load.return_value = {
                "categories": {
                    "invalid": {"tolerance": "not_a_number", "description": "Invalid"}
                }
            }

            from src.config import validate_tolerance_config

            with pytest.raises(TypeError):
                validate_tolerance_config()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
