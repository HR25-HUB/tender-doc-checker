"""Модуль для проверки наличия товаров в складском учете."""

import json
import logging
from datetime import datetime
from typing import Any, Optional, Union

from src.models import CheckResult, ProductSpecification

logger = logging.getLogger(__name__)


class InventoryChecker:
    """Класс для проверки наличия товаров в складском учете."""

    def __init__(self, inventory_data: Optional[dict[str, dict[str, Any]]] = None):
        """
        Инициализация проверщика наличия товаров.

        Args:
            inventory_data: Словарь данных о наличии товаров
                {product_code: {
                    "quantity": int,
                    "status": str,
                    "location": str,
                    "reserved": int,
                    "last_updated": str
                }}
        """
        self.inventory_data = inventory_data or {}
        self.api_client = None  # Заглушка для API клиента

    def load_inventory_data(self, inventory_data: Union[str, dict[str, Any]]) -> None:
        """
        Загружает данные о наличии товаров из JSON строки или словаря.

        Args:
            inventory_data: JSON строка или словарь с данными о наличии
        """
        try:
            if isinstance(inventory_data, str):
                data = json.loads(inventory_data)
            else:
                data = inventory_data

            self.inventory_data = {}
            for product_code, info in data.items():
                if not isinstance(info, dict):
                    logger.warning(
                        f"Некорректные данные для товара {product_code}: {info}"
                    )
                    continue

                # Валидация обязательных полей
                required_fields = ["quantity", "status"]
                if not all(field in info for field in required_fields):
                    logger.warning(
                        f"Отсутствуют обязательные поля для товара {product_code}"
                    )
                    continue

                self.inventory_data[product_code] = {
                    "quantity": int(info.get("quantity", 0)),
                    "status": str(info.get("status", "неизвестно")),
                    "location": str(info.get("location", "")),
                    "reserved": int(info.get("reserved", 0)),
                    "last_updated": info.get(
                        "last_updated", datetime.now().isoformat()
                    ),
                }

        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON с данными о наличии: {e}")
            raise ValueError(f"Некорректный формат данных о наличии: {e}")
        except (ValueError, TypeError) as e:
            logger.error(f"Ошибка обработки данных о наличии: {e}")
            raise ValueError(f"Некорректные данные о наличии: {e}")

    def get_available_quantity(self, product_code: str) -> int:
        """
        Получает доступное количество товара (общее количество - зарезервированное).

        Args:
            product_code: Код товара

        Returns:
            Доступное количество товара
        """
        if product_code not in self.inventory_data:
            return 0

        inventory_info = self.inventory_data[product_code]
        total_quantity = inventory_info.get("quantity", 0)
        reserved_quantity = inventory_info.get("reserved", 0)

        return max(0, total_quantity - reserved_quantity)

    def check_availability(
        self, product_code: str, required_quantity: int = 1
    ) -> CheckResult:
        """
        Проверяет наличие товара на складе.

        Args:
            product_code: Код товара
            required_quantity: Требуемое количество

        Returns:
            Результат проверки наличия
        """
        if required_quantity <= 0:
            return CheckResult(
                section=f"Проверка наличия товара {product_code}",
                match="нет",
                comments=f"Некорректное требуемое количество: {required_quantity}",
                check_type="складской",
                product_code=product_code,
                expected_quantity=0,
                actual_quantity=0,
                availability_check="не проверялась",
                quantity_check="не проверялось",
            )

        if product_code not in self.inventory_data:
            return CheckResult(
                section=f"Проверка наличия товара {product_code}",
                match="нет",
                comments=f"Товар {product_code} не найден в складском учете",
                check_type="складской",
                product_code=product_code,
                expected_quantity=required_quantity,
                availability_check="нет в наличии",
            )

        inventory_info = self.inventory_data[product_code]
        available_quantity = self.get_available_quantity(product_code)
        status = inventory_info.get("status", "неизвестно")
        location = inventory_info.get("location", "")

        # Определяем статус наличия
        if status.lower() in ["нет в наличии", "отсутствует", "снят с производства"]:
            availability_status = "нет в наличии"
            match = "нет"
            comments = f"Товар {product_code} отсутствует на складе (статус: {status})"
        elif status.lower() in ["под заказ", "ожидается поставка", "в производстве"]:
            availability_status = "под заказ"
            match = "частично"
            comments = f"Товар {product_code} доступен под заказ (статус: {status})"
        elif available_quantity >= required_quantity:
            availability_status = "в наличии"
            match = "да"
            location_info = f" (склад: {location})" if location else ""
            comments = f"Товар {product_code} в наличии: {available_quantity} шт.{location_info}"
        else:
            availability_status = "нет в наличии"
            match = "нет"
            comments = f"Недостаточное количество товара {product_code}: доступно {available_quantity} шт., требуется {required_quantity} шт."

        # Определяем статус количества
        if available_quantity >= required_quantity:
            quantity_check = "достаточно"
        elif available_quantity > 0:
            quantity_check = "недостаточно"
        else:
            quantity_check = "недостаточно"

        return CheckResult(
            section=f"Проверка наличия товара {product_code}",
            match=match,
            comments=comments,
            check_type="складской",
            product_code=product_code,
            expected_quantity=required_quantity,
            actual_quantity=available_quantity,
            availability_check=availability_status,
            quantity_check=quantity_check,
        )

    def check_multiple_availability(
        self, products: dict[str, int]
    ) -> list[CheckResult]:
        """
        Проверяет наличие нескольких товаров одновременно.

        Args:
            products: Словарь {product_code: required_quantity}

        Returns:
            Список результатов проверки
        """
        results = []
        for product_code, quantity in products.items():
            result = self.check_availability(product_code, quantity)
            results.append(result)

        return results

    def check_product_specifications(
        self, specifications: list[ProductSpecification]
    ) -> list[CheckResult]:
        """
        Проверяет наличие товаров из списка спецификаций.

        Args:
            specifications: Список товарных спецификаций

        Returns:
            Список результатов проверки
        """
        results = []
        for spec in specifications:
            result = self.check_availability(spec.product_code, spec.quantity)
            # Добавляем информацию из спецификации
            result.supplier_name = getattr(spec, "supplier_name", None)
            results.append(result)

        return results

    def get_low_stock_items(self, threshold: int = 10) -> list[dict[str, Any]]:
        """
        Получает список товаров с низким остатком.

        Args:
            threshold: Пороговое значение для определения низкого остатка

        Returns:
            Список товаров с низким остатком
        """
        low_stock_items = []

        for product_code, inventory_info in self.inventory_data.items():
            # Исключаем товары со статусом "под заказ" и "нет в наличии"
            status = inventory_info.get("status", "")
            if status in ["под заказ", "нет в наличии"]:
                continue

            available_quantity = self.get_available_quantity(product_code)

            if available_quantity <= threshold and inventory_info.get(
                "status", ""
            ).lower() not in ["нет в наличии", "снят с производства"]:
                low_stock_items.append(
                    {
                        "product_code": product_code,
                        "available_quantity": available_quantity,
                        "total_quantity": inventory_info.get("quantity", 0),
                        "reserved": inventory_info.get("reserved", 0),
                        "status": inventory_info.get("status", ""),
                        "location": inventory_info.get("location", ""),
                        "last_updated": inventory_info.get("last_updated", ""),
                    }
                )

        return sorted(low_stock_items, key=lambda x: x["available_quantity"])

    def simulate_api_request(self, product_code: str) -> dict[str, Any]:
        """
        Симулирует запрос к API складского учета.
        Это заглушка для реальной интеграции с API.

        Args:
            product_code: Код товара

        Returns:
            Данные о товаре из API
        """
        # Заглушка - в реальной системе здесь будет HTTP запрос к API
        if product_code in self.inventory_data:
            return self.inventory_data[product_code]

        # Симуляция ответа API для неизвестного товара
        return {
            "quantity": 0,
            "status": "не найден",
            "location": "",
            "reserved": 0,
            "last_updated": datetime.now().isoformat(),
            "error": f"Товар {product_code} не найден в системе",
        }

    def refresh_inventory_data(self, product_codes: Optional[list[str]] = None) -> None:
        """
        Обновляет данные о наличии товаров через API.
        Это заглушка для реальной интеграции с API.

        Args:
            product_codes: Список кодов товаров для обновления.
                          Если None, обновляются все товары.
        """
        codes_to_update = product_codes or list(self.inventory_data.keys())

        for product_code in codes_to_update:
            try:
                # В реальной системе здесь будет вызов API
                api_data = self.simulate_api_request(product_code)

                if "error" not in api_data:
                    self.inventory_data[product_code] = api_data
                    logger.info(f"Обновлены данные для товара {product_code}")
                else:
                    logger.warning(
                        f"Не удалось обновить данные для товара {product_code}: {api_data.get('error')}"
                    )

            except Exception as e:
                logger.error(
                    f"Ошибка при обновлении данных для товара {product_code}: {e}"
                )


def load_inventory_from_file(file_path: str) -> dict[str, dict[str, Any]]:
    """
    Загружает данные о наличии товаров из файла.

    Args:
        file_path: Путь к файлу с данными

    Returns:
        Словарь с данными о наличии товаров
    """
    try:
        with open(file_path, encoding="utf-8") as file:
            data = json.load(file)
        return data
    except FileNotFoundError:
        logger.error(f"Файл {file_path} не найден")
        raise FileNotFoundError(f"Файл с данными о наличии не найден: {file_path}")
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка парсинга JSON файла {file_path}: {e}")
        raise ValueError(f"Некорректный формат JSON файла: {e}")


def calculate_total_required_quantity(products: dict[str, int]) -> int:
    """
    Рассчитывает общее требуемое количество товаров.

    Args:
        products: Словарь {product_code: required_quantity}

    Returns:
        Общее количество товаров
    """
    return sum(products.values())


def get_availability_summary(results: list[CheckResult]) -> dict[str, int]:
    """
    Создает сводку по результатам проверки наличия.

    Args:
        results: Список результатов проверки

    Returns:
        Словарь со статистикой
    """
    summary = {
        "total_products": len(results),
        "available": 0,
        "partially_available": 0,
        "not_available": 0,
        "not_checked": 0,
    }

    for result in results:
        if result.match == "да":
            summary["available"] += 1
        elif result.match == "частично":
            summary["partially_available"] += 1
        elif result.match == "нет":
            summary["not_available"] += 1
        else:
            summary["not_checked"] += 1

    return summary
