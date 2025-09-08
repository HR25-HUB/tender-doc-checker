"""Модуль для проверки цен в коммерческих предложениях."""

import json
import logging
from decimal import Decimal, InvalidOperation
from typing import Any, Optional, Union

from src.config import get_category_info, list_all_categories, load_config
from src.models import CheckResult, PriceRecord


class PriceComparison:
    """Класс для сравнения цен."""

    def __init__(
        self,
        product_code: str,
        current_price: float,
        proposed_price: float,
        price_difference: float,
        price_difference_percent: float,
        recommendation: str,
    ):
        self.product_code = product_code
        self.current_price = current_price
        self.proposed_price = proposed_price
        self.price_difference = price_difference
        self.price_difference_percent = price_difference_percent
        self.recommendation = recommendation


logger = logging.getLogger(__name__)


class MockExchangeRateProvider:
    """Мок провайдер курсов валют для тестирования."""

    def __init__(self):
        self.rates = {
            ("USD", "RUB"): Decimal("95.00"),
            ("EUR", "RUB"): Decimal("105.00"),
            ("USD", "EUR"): Decimal("1.10"),
            ("EUR", "USD"): Decimal("0.91"),
        }

    def get_rate(self, source_currency: str, target_currency: str) -> Decimal:
        """
        Получает курс обмена валют.

        Args:
            source_currency: Исходная валюта
            target_currency: Целевая валюта

        Returns:
            Курс обмена

        Raises:
            ValueError: Если курс не найден
        """
        if source_currency == target_currency:
            return Decimal("1.00")

        rate = self.rates.get((source_currency, target_currency))
        if rate is None:
            raise ValueError(
                f"Курс обмена {source_currency} -> {target_currency} не найден"
            )

        return rate


def get_category_tolerance(category: str) -> Decimal:
    """Получает допустимое отклонение для категории товара."""
    try:
        config = load_config()
        category_info = get_category_info(category)
        if category_info and category_info.active:
            return Decimal(str(category_info.tolerance))
        else:
            # Используем категорию по умолчанию
            default_info = get_category_info("default")
            if default_info and default_info.active:
                return Decimal(str(default_info.tolerance))
            else:
                return Decimal("7")  # Значение по умолчанию
    except Exception:
        return Decimal("7")  # Значение по умолчанию в случае ошибки


def check_price_tolerance(
    category: str, expected_price: float, actual_price: float
) -> dict:
    """
    Проверяет цену на соответствие допустимому отклонению по категории.

    Args:
        category: Категория товара
        expected_price: Ожидаемая цена
        actual_price: Фактическая цена

    Returns:
        Словарь с результатами проверки
    """
    tolerance = get_category_tolerance(category)

    if expected_price == 0:
        deviation = 0.0
    else:
        deviation = abs((actual_price - expected_price) / expected_price)

    tolerance_decimal = float(tolerance) / 100

    # Получаем информацию о категории из новой системы конфигурации
    try:
        category_info = get_category_info(category)
        if category_info and category_info.active:
            category_used = category_info.name
            category_description = category_info.description
            price_range = f"{category_info.min_price}-{category_info.max_price} {category_info.currency}"
        else:
            # Используем категорию по умолчанию
            default_info = get_category_info("default")
            if default_info and default_info.active:
                category_used = default_info.name
                category_description = default_info.description
                price_range = f"{default_info.min_price}-{default_info.max_price} {default_info.currency}"
            else:
                category_used = "default"
                category_description = "Категория по умолчанию"
                price_range = "0-1000000 RUB"
    except Exception:
        category_used = "default"
        category_description = "Категория по умолчанию"
        price_range = "0-1000000 RUB"

    return {
        "within_tolerance": deviation <= tolerance_decimal,
        "deviation": deviation,
        "tolerance_used": tolerance_decimal,
        "category_used": category_used.lower(),
        "category_description": category_description,
        "price_range": price_range,
    }


def check_prices_batch(items: list[dict]) -> list[dict]:
    """
    Проверяет несколько цен одновременно.

    Args:
        items: Список словарей с параметрами проверки

    Returns:
        Список результатов проверки
    """
    results = []
    for item in items:
        result = check_price_tolerance(
            category=item["category"],
            expected_price=item["expected"],
            actual_price=item["actual"],
        )
        results.append(result)
    return results


def get_active_categories() -> list[dict[str, Any]]:
    """
    Получает список всех активных категорий с их параметрами.

    Returns:
        Список словарей с информацией об активных категориях
    """
    try:
        categories = list_all_categories()
        active_categories = []

        for category in categories:
            if category.active:
                active_categories.append(
                    {
                        "name": category.name,
                        "description": category.description,
                        "tolerance": category.tolerance,
                        "min_price": category.min_price,
                        "max_price": category.max_price,
                        "currency": category.currency,
                        "price_range": f"{category.min_price}-{category.max_price} {category.currency}",
                    }
                )

        return active_categories
    except Exception as e:
        logger.error(f"Ошибка при получении активных категорий: {e}")
        return []


class PriceChecker:
    """Класс для проверки цен в коммерческих предложениях."""

    def __init__(
        self, base_prices: Optional[dict[str, Decimal]] = None, rate_provider=None
    ):
        """
        Инициализация проверщика цен.

        Args:
            base_prices: Словарь базовых цен {product_code: price}
            rate_provider: Провайдер курсов валют (по умолчанию MockExchangeRateProvider)
        """
        self.base_prices = base_prices or {}
        self.rate_provider = rate_provider or MockExchangeRateProvider()

    def load_base_prices(self, prices_data: Union[str, dict[str, Any]]) -> None:
        """
        Загружает базовые цены из JSON строки или словаря.

        Args:
            prices_data: JSON строка или словарь с ценами
        """
        try:
            if isinstance(prices_data, str):
                data = json.loads(prices_data)
            else:
                data = prices_data

            self.base_prices = {}
            for product_code, price in data.items():
                try:
                    self.base_prices[product_code] = Decimal(str(price))
                except (InvalidOperation, ValueError) as e:
                    logger.warning(
                        f"Некорректная цена для товара {product_code}: {price}. Ошибка: {e}"
                    )

        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON с ценами: {e}")
            raise ValueError(f"Некорректный формат данных цен: {e}")

    def convert_currency(
        self, price_record: PriceRecord, target_currency: str
    ) -> Decimal:
        """
        Конвертирует цену в указанную валюту.

        Args:
            price_record: Запись с ценой и валютой
            target_currency: Целевая валюта

        Returns:
            Конвертированная цена
        """
        if price_record.currency == target_currency:
            return Decimal(str(price_record.price))

        rate = self.rate_provider.get_rate(price_record.currency, target_currency)
        converted_price = Decimal(str(price_record.price)) * rate
        return converted_price.quantize(Decimal("0.01"))

    def calculate_deviation_after_conversion(
        self, price1: PriceRecord, price2: PriceRecord
    ) -> Decimal:
        """
        Рассчитывает отклонение между двумя ценами после конвертации в одну валюту.

        Args:
            price1: Первая цена
            price2: Вторая цена

        Returns:
            Отклонение в процентах
        """
        # Конвертируем обе цены в RUB для сравнения
        price1_rub = self.convert_currency(price1, "RUB")
        price2_rub = self.convert_currency(price2, "RUB")

        if price1_rub == 0:
            return Decimal("0")

        deviation = abs((price1_rub - price2_rub) / price1_rub) * 100
        return deviation.quantize(Decimal("0.01"))

    def convert_batch_to_currency(
        self, price_records: list[PriceRecord], target_currency: str
    ) -> list[Decimal]:
        """
        Конвертирует список цен в указанную валюту.

        Args:
            price_records: Список записей с ценами
            target_currency: Целевая валюта

        Returns:
            Список конвертированных цен
        """
        return [
            self.convert_currency(record, target_currency) for record in price_records
        ]

    def calculate_price_deviation(
        self, expected_price: Decimal, actual_price: Decimal
    ) -> Decimal:
        """
        Рассчитывает отклонение цены в процентах.

        Args:
            expected_price: Ожидаемая цена
            actual_price: Фактическая цена

        Returns:
            Отклонение в процентах (положительное - превышение, отрицательное - снижение)
        """
        if expected_price == 0:
            return Decimal("0")

        deviation = ((actual_price - expected_price) / expected_price) * 100
        return deviation.quantize(Decimal("0.01"))

    def check_price(
        self,
        product_code: str,
        actual_price: Union[str, int, float, Decimal],
        tolerance_percent: Decimal = Decimal("10"),
        category: Optional[str] = None,
    ) -> CheckResult:
        """
        Проверяет цену товара относительно базовой цены.

        Args:
            product_code: Код товара
            actual_price: Фактическая цена
            tolerance_percent: Допустимое отклонение в процентах
            category: Категория товара (если не указана, используется tolerance_percent)

        Returns:
            Результат проверки цены
        """
        try:
            actual_price_decimal = Decimal(str(actual_price))
        except (InvalidOperation, ValueError):
            return CheckResult(
                section=f"Проверка цены товара {product_code}",
                match="нет",
                comments=f"Некорректная цена для товара {product_code}: {actual_price}",
                check_type="ценовой",
                product_code=product_code,
                actual_price=float(str(actual_price))
                if str(actual_price).replace(".", "").isdigit()
                else None,
            )

        if product_code not in self.base_prices:
            return CheckResult(
                section=f"Проверка цены товара {product_code}",
                match="нет",
                comments=f"Базовая цена для товара {product_code} не найдена",
                check_type="ценовой",
                product_code=product_code,
                actual_price=float(actual_price_decimal),
            )

        expected_price = self.base_prices[product_code]
        deviation = self.calculate_price_deviation(expected_price, actual_price_decimal)

        # Определяем допустимое отклонение
        if category:
            category_tolerance = get_category_tolerance(category)
            used_tolerance = category_tolerance
            tolerance_source = f"категория {category}"
        else:
            used_tolerance = tolerance_percent
            tolerance_source = "общее"

        is_within_tolerance = abs(deviation) <= used_tolerance

        if is_within_tolerance:
            comments = f"Цена товара {product_code} в пределах допустимого отклонения {used_tolerance}% ({tolerance_source}) - ({deviation:.1f}%)"
            match = "да"
            price_check = "соответствует"
        else:
            if deviation > 0:
                comments = f"Цена товара {product_code} превышает базовую на {deviation:.1f}% (допуск {used_tolerance}% {tolerance_source})"
                price_check = "завышена"
            else:
                comments = f"Цена товара {product_code} ниже базовой на {abs(deviation):.1f}% (допуск {used_tolerance}% {tolerance_source})"
                price_check = "занижена"
            match = "нет"

        return CheckResult(
            section=f"Проверка цены товара {product_code}",
            match=match,
            comments=comments,
            check_type="ценовой",
            product_code=product_code,
            expected_price=float(expected_price),
            actual_price=float(actual_price_decimal),
            price_deviation_percent=float(deviation),
            price_check=price_check,
        )

    def check_multiple_prices(
        self,
        prices: dict[str, Union[str, int, float, Decimal]],
        tolerance_percent: Decimal = Decimal("10"),
        categories: Optional[dict[str, str]] = None,
    ) -> list[CheckResult]:
        """
        Проверяет несколько цен одновременно.

        Args:
            prices: Словарь {product_code: price}
            tolerance_percent: Допустимое отклонение в процентах
            categories: Словарь {product_code: category} для указания категорий товаров

        Returns:
            Список результатов проверки
        """
        results = []
        categories = categories or {}

        for product_code, price in prices.items():
            category = categories.get(product_code)
            result = self.check_price(product_code, price, tolerance_percent, category)
            results.append(result)

        return results

    def compare_supplier_prices(
        self,
        supplier_prices: dict[str, dict[str, Union[str, int, float, Decimal]]],
        tolerance_percent: Decimal = Decimal("10"),
    ) -> dict[str, list[CheckResult]]:
        """
        Сравнивает цены от разных поставщиков.

        Args:
            supplier_prices: Словарь {supplier_name: {product_code: price}}
            tolerance_percent: Допустимое отклонение в процентах

        Returns:
            Словарь результатов по поставщикам
        """
        results = {}
        for supplier_name, prices in supplier_prices.items():
            supplier_results = []
            for product_code, price in prices.items():
                result = self.check_price(product_code, price, tolerance_percent)
                result.supplier_name = supplier_name
                supplier_results.append(result)
            results[supplier_name] = supplier_results

        return results

    def create_price_comparison(
        self,
        product_code: str,
        current_price: Union[str, int, float, Decimal],
        proposed_price: Union[str, int, float, Decimal],
    ) -> PriceComparison:
        """
        Создает сравнение текущей и предложенной цены.

        Args:
            product_code: Код товара
            current_price: Текущая цена
            proposed_price: Предложенная цена

        Returns:
            Объект сравнения цен
        """
        try:
            # Конвертируем цены в Decimal
            current_decimal = Decimal(str(current_price))
            proposed_decimal = Decimal(str(proposed_price))

            # Рассчитываем разницу
            price_difference = float(proposed_decimal - current_decimal)

            # Рассчитываем разницу в процентах
            if current_decimal != 0:
                price_difference_percent = float(
                    ((proposed_decimal - current_decimal) / current_decimal) * 100
                )
            else:
                price_difference_percent = 0.0

            # Определяем рекомендацию
            if price_difference_percent <= -5:  # Экономия больше 5%
                recommendation = "принять"
            elif price_difference_percent > 15:  # Удорожание больше 15%
                recommendation = "отклонить"
            elif abs(price_difference_percent) <= 5:  # Изменение в пределах 5%
                recommendation = "принять"
            else:
                recommendation = "требует согласования"

            return PriceComparison(
                product_code=product_code,
                current_price=float(current_decimal),
                proposed_price=float(proposed_decimal),
                price_difference=price_difference,
                price_difference_percent=price_difference_percent,
                recommendation=recommendation,
            )

        except (InvalidOperation, ValueError) as e:
            logger.error(
                f"Ошибка при создании сравнения цен для товара {product_code}: {e}"
            )
            raise ValueError(f"Некорректные цены для сравнения: {e}")


def load_base_prices_from_file(file_path: str) -> dict[str, Decimal]:
    """
    Загружает базовые цены из JSON файла.

    Args:
        file_path: Путь к файлу с ценами

    Returns:
        Словарь базовых цен
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        base_prices = {}
        for product_code, price in data.items():
            try:
                base_prices[product_code] = Decimal(str(price))
            except (InvalidOperation, ValueError) as e:
                logger.warning(
                    f"Некорректная цена для товара {product_code}: {price}. Ошибка: {e}"
                )

        return base_prices

    except FileNotFoundError:
        logger.error(f"Файл с ценами не найден: {file_path}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка парсинга JSON файла {file_path}: {e}")
        return {}


def calculate_total_savings(
    base_prices: dict[str, Decimal],
    supplier_prices: dict[str, Decimal],
    quantities: dict[str, int],
) -> dict[str, Any]:
    """
    Рассчитывает общую экономию при выборе поставщика.

    Args:
        base_prices: Базовые цены {product_code: price}
        supplier_prices: Цены поставщика {product_code: price}
        quantities: Количества товаров {product_code: quantity}

    Returns:
        Словарь с информацией об экономии
    """
    total_base_cost = Decimal("0")
    total_supplier_cost = Decimal("0")
    savings_by_product = {}

    for product_code in base_prices.keys():
        if product_code in supplier_prices and product_code in quantities:
            base_price = base_prices[product_code]
            supplier_price = supplier_prices[product_code]
            quantity = quantities[product_code]

            base_cost = base_price * quantity
            supplier_cost = supplier_price * quantity
            savings = base_cost - supplier_cost

            total_base_cost += base_cost
            total_supplier_cost += supplier_cost

            savings_by_product[product_code] = {
                "base_cost": float(base_cost),
                "supplier_cost": float(supplier_cost),
                "savings": float(savings),
                "savings_percent": float((savings / base_cost) * 100)
                if base_cost > 0
                else 0,
            }

    total_savings = total_base_cost - total_supplier_cost
    total_savings_percent = (
        float((total_savings / total_base_cost) * 100) if total_base_cost > 0 else 0
    )

    return {
        "total_base_cost": float(total_base_cost),
        "total_supplier_cost": float(total_supplier_cost),
        "total_savings": float(total_savings),
        "total_savings_percent": total_savings_percent,
        "savings_by_product": savings_by_product,
    }
