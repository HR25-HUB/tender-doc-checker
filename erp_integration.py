"""Модуль интеграции с ERP системами.

Этот модуль предоставляет базовые классы и функции для интеграции
с различными ERP системами (1C, SAP и др.).
"""

import abc
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class ERPSystemType(Enum):
    """Типы поддерживаемых ERP систем."""

    ONEC = "1c"
    SAP = "sap"
    ORACLE = "oracle"
    CUSTOM = "custom"


@dataclass
class ERPConnectionConfig:
    """Конфигурация подключения к ERP системе."""

    system_type: ERPSystemType
    host: str
    port: int
    database: str
    username: str
    password: str
    timeout: int = 30
    ssl_enabled: bool = False
    additional_params: Optional[dict[str, Any]] = None


@dataclass
class ProductInfo:
    """Информация о товаре из ERP системы."""

    product_code: str
    name: str
    description: str
    unit_of_measure: str
    current_price: float
    currency: str
    category: str
    supplier_id: Optional[str] = None
    last_updated: Optional[datetime] = None
    specifications: Optional[dict[str, Any]] = None


@dataclass
class InventoryInfo:
    """Информация об остатках товара на складе."""

    product_code: str
    warehouse_code: str
    quantity_available: float
    quantity_reserved: float
    quantity_ordered: float
    unit_of_measure: str
    last_updated: datetime
    min_stock_level: Optional[float] = None
    max_stock_level: Optional[float] = None


@dataclass
class PriceInfo:
    """Информация о ценах товара."""

    product_code: str
    price: float
    currency: str
    price_type: str  # "base", "discount", "special", etc.
    valid_from: datetime
    valid_to: Optional[datetime] = None
    supplier_id: Optional[str] = None


class ERPConnectionError(Exception):
    """Ошибка подключения к ERP системе."""

    pass


class ERPDataError(Exception):
    """Ошибка получения данных из ERP системы."""

    pass


class BaseERPConnector(abc.ABC):
    """Базовый класс для подключения к ERP системам."""

    def __init__(self, config: ERPConnectionConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._connection = None
        self._is_connected = False

    @abc.abstractmethod
    def connect(self) -> bool:
        """Установить соединение с ERP системой.

        Returns:
            bool: True если соединение установлено успешно

        Raises:
            ERPConnectionError: При ошибке подключения
        """
        pass

    @abc.abstractmethod
    def disconnect(self) -> None:
        """Закрыть соединение с ERP системой."""
        pass

    @abc.abstractmethod
    def test_connection(self) -> bool:
        """Проверить соединение с ERP системой.

        Returns:
            bool: True если соединение активно
        """
        pass

    @abc.abstractmethod
    def get_product_info(self, product_code: str) -> Optional[ProductInfo]:
        """Получить информацию о товаре.

        Args:
            product_code: Код товара

        Returns:
            ProductInfo или None если товар не найден

        Raises:
            ERPDataError: При ошибке получения данных
        """
        pass

    @abc.abstractmethod
    def get_current_prices(self, product_codes: list[str]) -> list[PriceInfo]:
        """Получить текущие цены товаров.

        Args:
            product_codes: Список кодов товаров

        Returns:
            Список информации о ценах

        Raises:
            ERPDataError: При ошибке получения данных
        """
        pass

    @abc.abstractmethod
    def check_inventory_levels(
        self, product_codes: list[str], warehouse_code: Optional[str] = None
    ) -> list[InventoryInfo]:
        """Проверить остатки товаров на складе.

        Args:
            product_codes: Список кодов товаров
            warehouse_code: Код склада (если не указан, проверяются все склады)

        Returns:
            Список информации об остатках

        Raises:
            ERPDataError: При ошибке получения данных
        """
        pass

    @property
    def is_connected(self) -> bool:
        """Проверить статус соединения."""
        return self._is_connected

    def __enter__(self):
        """Контекстный менеджер для автоматического управления соединением."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Закрыть соединение при выходе из контекста."""
        self.disconnect()


class MockERPConnector(BaseERPConnector):
    """Мок-реализация ERP коннектора для тестирования."""

    def __init__(self, config: ERPConnectionConfig):
        super().__init__(config)
        self._mock_products = {
            "PROD001": ProductInfo(
                product_code="PROD001",
                name="Тестовый товар 1",
                description="Описание тестового товара 1",
                unit_of_measure="шт",
                current_price=100.0,
                currency="RUB",
                category="Категория 1",
                supplier_id="SUP001",
                last_updated=datetime.now(),
            ),
            "PROD002": ProductInfo(
                product_code="PROD002",
                name="Тестовый товар 2",
                description="Описание тестового товара 2",
                unit_of_measure="кг",
                current_price=250.5,
                currency="RUB",
                category="Категория 2",
                supplier_id="SUP002",
                last_updated=datetime.now(),
            ),
        }

        self._mock_inventory = {
            "PROD001": InventoryInfo(
                product_code="PROD001",
                warehouse_code="WH001",
                quantity_available=100.0,
                quantity_reserved=10.0,
                quantity_ordered=50.0,
                unit_of_measure="шт",
                last_updated=datetime.now(),
                min_stock_level=20.0,
                max_stock_level=500.0,
            ),
            "PROD002": InventoryInfo(
                product_code="PROD002",
                warehouse_code="WH001",
                quantity_available=75.5,
                quantity_reserved=5.0,
                quantity_ordered=25.0,
                unit_of_measure="кг",
                last_updated=datetime.now(),
                min_stock_level=10.0,
                max_stock_level=200.0,
            ),
        }

    def connect(self) -> bool:
        """Имитация подключения к ERP системе."""
        self.logger.info(
            f"Подключение к мок ERP системе {self.config.host}:{self.config.port}"
        )
        self._is_connected = True
        return True

    def disconnect(self) -> None:
        """Имитация отключения от ERP системы."""
        self.logger.info("Отключение от мок ERP системы")
        self._is_connected = False

    def test_connection(self) -> bool:
        """Проверка соединения с мок ERP системой."""
        return self._is_connected

    def get_product_info(self, product_code: str) -> Optional[ProductInfo]:
        """Получить информацию о товаре из мок данных."""
        if not self._is_connected:
            raise ERPConnectionError("Нет соединения с ERP системой")

        return self._mock_products.get(product_code)

    def get_current_prices(self, product_codes: list[str]) -> list[PriceInfo]:
        """Получить текущие цены товаров из мок данных."""
        if not self._is_connected:
            raise ERPConnectionError("Нет соединения с ERP системой")

        prices = []
        for code in product_codes:
            product = self._mock_products.get(code)
            if product:
                prices.append(
                    PriceInfo(
                        product_code=code,
                        price=product.current_price,
                        currency=product.currency,
                        price_type="base",
                        valid_from=datetime.now(),
                        supplier_id=product.supplier_id,
                    )
                )

        return prices

    def check_inventory_levels(
        self, product_codes: list[str], warehouse_code: Optional[str] = None
    ) -> list[InventoryInfo]:
        """Проверить остатки товаров из мок данных."""
        if not self._is_connected:
            raise ERPConnectionError("Нет соединения с ERP системой")

        inventory = []
        for code in product_codes:
            inv_info = self._mock_inventory.get(code)
            if inv_info and (
                warehouse_code is None or inv_info.warehouse_code == warehouse_code
            ):
                inventory.append(inv_info)

        return inventory


def create_erp_connector(config: ERPConnectionConfig) -> BaseERPConnector:
    """Фабричная функция для создания ERP коннектора.

    Args:
        config: Конфигурация подключения

    Returns:
        Экземпляр ERP коннектора

    Raises:
        ValueError: При неподдерживаемом типе ERP системы
    """
    if config.system_type == ERPSystemType.CUSTOM or config.host == "mock":
        return MockERPConnector(config)
    else:
        # В будущем здесь будут реальные коннекторы для 1C, SAP и др.
        raise ValueError(
            f"ERP система {config.system_type.value} пока не поддерживается"
        )


def get_product_info_from_erp(
    product_code: str, erp_config: ERPConnectionConfig
) -> Optional[ProductInfo]:
    """Удобная функция для получения информации о товаре из ERP.

    Args:
        product_code: Код товара
        erp_config: Конфигурация ERP системы

    Returns:
        Информация о товаре или None
    """
    try:
        with create_erp_connector(erp_config) as connector:
            return connector.get_product_info(product_code)
    except Exception as e:
        logging.error(f"Ошибка получения информации о товаре {product_code}: {e}")
        return None


def get_current_prices_from_erp(
    product_codes: list[str], erp_config: ERPConnectionConfig
) -> list[PriceInfo]:
    """Удобная функция для получения текущих цен из ERP.

    Args:
        product_codes: Список кодов товаров
        erp_config: Конфигурация ERP системы

    Returns:
        Список информации о ценах
    """
    try:
        with create_erp_connector(erp_config) as connector:
            return connector.get_current_prices(product_codes)
    except Exception as e:
        logging.error(f"Ошибка получения цен товаров {product_codes}: {e}")
        return []


def check_inventory_levels_from_erp(
    product_codes: list[str],
    erp_config: ERPConnectionConfig,
    warehouse_code: Optional[str] = None,
) -> list[InventoryInfo]:
    """Удобная функция для проверки остатков товаров в ERP.

    Args:
        product_codes: Список кодов товаров
        erp_config: Конфигурация ERP системы
        warehouse_code: Код склада (опционально)

    Returns:
        Список информации об остатках
    """
    try:
        with create_erp_connector(erp_config) as connector:
            return connector.check_inventory_levels(product_codes, warehouse_code)
    except Exception as e:
        logging.error(f"Ошибка проверки остатков товаров {product_codes}: {e}")
        return []


# === ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ TASK 2.1.2 ===


def get_product_info(
    product_code: str, erp_config: ERPConnectionConfig
) -> Optional[ProductInfo]:
    """Получить информацию о товаре из ERP системы.

    Основная функция для получения детальной информации о товаре,
    включая цену, описание, категорию и другие характеристики.

    Args:
        product_code: Код товара
        erp_config: Конфигурация ERP системы

    Returns:
        ProductInfo: Информация о товаре или None если не найден

    Example:
        >>> config = ERPConnectionConfig(
        ...     system_type=ERPSystemType.CUSTOM,
        ...     host="mock", port=8080, database="test",
        ...     username="user", password="pass"
        ... )
        >>> product = get_product_info("PROD001", config)
        >>> if product:
        ...     print(f"Товар: {product.name}, Цена: {product.current_price}")
    """
    return get_product_info_from_erp(product_code, erp_config)


def get_current_prices(
    product_codes: list[str], erp_config: ERPConnectionConfig
) -> list[PriceInfo]:
    """Получить текущие цены товаров из ERP системы.

    Функция для массового получения актуальных цен на товары.
    Полезна для сравнения цен и анализа коммерческих предложений.

    Args:
        product_codes: Список кодов товаров
        erp_config: Конфигурация ERP системы

    Returns:
        List[PriceInfo]: Список информации о ценах

    Example:
        >>> config = ERPConnectionConfig(
        ...     system_type=ERPSystemType.CUSTOM,
        ...     host="mock", port=8080, database="test",
        ...     username="user", password="pass"
        ... )
        >>> prices = get_current_prices(["PROD001", "PROD002"], config)
        >>> for price in prices:
        ...     print(f"Товар {price.product_code}: {price.price} {price.currency}")
    """
    return get_current_prices_from_erp(product_codes, erp_config)


def get_products_by_category(
    category: str, erp_config: ERPConnectionConfig, limit: Optional[int] = None
) -> list[ProductInfo]:
    """Получить список товаров по категории из ERP системы.

    Args:
        category: Название категории товаров
        erp_config: Конфигурация ERP системы
        limit: Максимальное количество товаров (опционально)

    Returns:
        List[ProductInfo]: Список товаров в категории
    """
    try:
        with create_erp_connector(erp_config) as connector:
            if isinstance(connector, MockERPConnector):
                # Для мок-коннектора фильтруем по категории
                all_products = [
                    p
                    for p in connector._mock_products.values()
                    if p.category == category
                ]
                if limit:
                    all_products = all_products[:limit]
                return all_products
            else:
                # Для реальных коннекторов будет реализовано позже
                raise NotImplementedError(
                    "Получение товаров по категории пока не реализовано"
                )
    except Exception as e:
        logging.error(f"Ошибка получения товаров категории {category}: {e}")
        return []


def search_products(
    search_query: str, erp_config: ERPConnectionConfig, limit: Optional[int] = None
) -> list[ProductInfo]:
    """Поиск товаров по названию или описанию в ERP системе.

    Args:
        search_query: Поисковый запрос
        erp_config: Конфигурация ERP системы
        limit: Максимальное количество результатов (опционально)

    Returns:
        List[ProductInfo]: Список найденных товаров
    """
    try:
        with create_erp_connector(erp_config) as connector:
            if isinstance(connector, MockERPConnector):
                # Для мок-коннектора ищем по названию и описанию
                search_lower = search_query.lower()
                found_products = []
                for product in connector._mock_products.values():
                    if (
                        search_lower in product.name.lower()
                        or search_lower in product.description.lower()
                    ):
                        found_products.append(product)

                if limit:
                    found_products = found_products[:limit]
                return found_products
            else:
                # Для реальных коннекторов будет реализовано позже
                raise NotImplementedError("Поиск товаров пока не реализован")
    except Exception as e:
        logging.error(f"Ошибка поиска товаров по запросу '{search_query}': {e}")
        return []


def get_product_price_history(
    product_code: str, erp_config: ERPConnectionConfig, days_back: int = 30
) -> list[PriceInfo]:
    """Получить историю цен товара из ERP системы.

    Args:
        product_code: Код товара
        erp_config: Конфигурация ERP системы
        days_back: Количество дней назад для получения истории

    Returns:
        List[PriceInfo]: История цен товара
    """
    try:
        with create_erp_connector(erp_config) as connector:
            if isinstance(connector, MockERPConnector):
                # Для мок-коннектора генерируем фиктивную историю
                product = connector._mock_products.get(product_code)
                if not product:
                    return []

                history = []
                base_price = product.current_price

                # Генерируем историю с небольшими колебаниями цены
                for i in range(min(days_back, 10)):  # Ограничиваем для мока
                    price_variation = 1.0 + (i * 0.02)  # Небольшие изменения
                    history_price = base_price * price_variation

                    price_info = PriceInfo(
                        product_code=product_code,
                        price=round(history_price, 2),
                        currency=product.currency,
                        price_type="historical",
                        valid_from=datetime.now().replace(
                            day=max(1, datetime.now().day - i)
                        ),
                        supplier_id=product.supplier_id,
                    )
                    history.append(price_info)

                return history
            else:
                # Для реальных коннекторов будет реализовано позже
                raise NotImplementedError("Получение истории цен пока не реализовано")
    except Exception as e:
        logging.error(f"Ошибка получения истории цен товара {product_code}: {e}")
        return []


# === ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ РАБОТЫ С ОСТАТКАМИ (TASK 2.1.3) ===


def check_inventory_levels(
    product_codes: list[str],
    erp_config: ERPConnectionConfig,
    warehouse_code: Optional[str] = None,
) -> list[InventoryInfo]:
    """Проверить остатки товаров на складе.

    Основная функция для проверки текущих остатков товаров.
    Возвращает детальную информацию о количестве, резервах и заказах.

    Args:
        product_codes: Список кодов товаров
        erp_config: Конфигурация ERP системы
        warehouse_code: Код склада (опционально)

    Returns:
        List[InventoryInfo]: Список информации об остатках

    Example:
        >>> config = ERPConnectionConfig(
        ...     system_type=ERPSystemType.CUSTOM,
        ...     host="mock", port=8080, database="test",
        ...     username="user", password="pass"
        ... )
        >>> inventory = check_inventory_levels(["PROD001", "PROD002"], config)
        >>> for item in inventory:
        ...     print(f"Товар {item.product_code}: доступно {item.quantity_available}")
    """
    return check_inventory_levels_from_erp(product_codes, erp_config, warehouse_code)


def get_low_stock_products(
    erp_config: ERPConnectionConfig,
    warehouse_code: Optional[str] = None,
    threshold_percentage: float = 0.2,
) -> list[InventoryInfo]:
    """Получить список товаров с низкими остатками.

    Args:
        erp_config: Конфигурация ERP системы
        warehouse_code: Код склада (опционально)
        threshold_percentage: Порог в процентах от минимального остатка

    Returns:
        List[InventoryInfo]: Список товаров с низкими остатками
    """
    try:
        with create_erp_connector(erp_config) as connector:
            if isinstance(connector, MockERPConnector):
                low_stock_items = []
                for inventory in connector._mock_inventory.values():
                    if warehouse_code and inventory.warehouse_code != warehouse_code:
                        continue

                    # Проверяем, если остаток ниже порогового значения
                    if (
                        inventory.min_stock_level
                        and inventory.quantity_available
                        <= inventory.min_stock_level * (1 + threshold_percentage)
                    ):
                        low_stock_items.append(inventory)

                return low_stock_items
            else:
                # Для реальных коннекторов будет реализовано позже
                raise NotImplementedError(
                    "Получение товаров с низкими остатками пока не реализовано"
                )
    except Exception as e:
        logging.error(f"Ошибка получения товаров с низкими остатками: {e}")
        return []


def get_warehouse_summary(
    erp_config: ERPConnectionConfig, warehouse_code: Optional[str] = None
) -> dict[str, Any]:
    """Получить сводку по складу.

    Args:
        erp_config: Конфигурация ERP системы
        warehouse_code: Код склада (опционально)

    Returns:
        Dict[str, Any]: Сводная информация по складу
    """
    try:
        with create_erp_connector(erp_config) as connector:
            if isinstance(connector, MockERPConnector):
                summary = {
                    "warehouse_code": warehouse_code or "ALL",
                    "total_products": 0,
                    "total_quantity": 0.0,
                    "total_reserved": 0.0,
                    "total_ordered": 0.0,
                    "low_stock_count": 0,
                    "products_by_category": {},
                    "last_updated": datetime.now().isoformat(),
                }

                for inventory in connector._mock_inventory.values():
                    if warehouse_code and inventory.warehouse_code != warehouse_code:
                        continue

                    summary["total_products"] += 1
                    summary["total_quantity"] += inventory.quantity_available
                    summary["total_reserved"] += inventory.quantity_reserved
                    summary["total_ordered"] += inventory.quantity_ordered

                    # Проверяем низкие остатки
                    if (
                        inventory.min_stock_level
                        and inventory.quantity_available <= inventory.min_stock_level
                    ):
                        summary["low_stock_count"] += 1

                    # Получаем категорию товара
                    product = connector._mock_products.get(inventory.product_code)
                    if product:
                        category = product.category
                        if category not in summary["products_by_category"]:
                            summary["products_by_category"][category] = 0
                        summary["products_by_category"][category] += 1

                return summary
            else:
                # Для реальных коннекторов будет реализовано позже
                raise NotImplementedError(
                    "Получение сводки по складу пока не реализовано"
                )
    except Exception as e:
        logging.error(f"Ошибка получения сводки по складу: {e}")
        return {}


def check_product_availability(
    product_code: str,
    required_quantity: float,
    erp_config: ERPConnectionConfig,
    warehouse_code: Optional[str] = None,
) -> dict[str, Any]:
    """Проверить доступность товара в требуемом количестве.

    Args:
        product_code: Код товара
        required_quantity: Требуемое количество
        erp_config: Конфигурация ERP системы
        warehouse_code: Код склада (опционально)

    Returns:
        Dict[str, Any]: Информация о доступности товара
    """
    try:
        inventory_list = check_inventory_levels(
            [product_code], erp_config, warehouse_code
        )

        if not inventory_list:
            return {
                "product_code": product_code,
                "available": False,
                "reason": "Товар не найден на складе",
                "available_quantity": 0.0,
                "required_quantity": required_quantity,
                "shortage": required_quantity,
            }

        inventory = inventory_list[0]
        available_qty = inventory.quantity_available

        return {
            "product_code": product_code,
            "available": available_qty >= required_quantity,
            "reason": "Достаточно товара"
            if available_qty >= required_quantity
            else "Недостаточно товара",
            "available_quantity": available_qty,
            "required_quantity": required_quantity,
            "shortage": max(0, required_quantity - available_qty),
            "warehouse_code": inventory.warehouse_code,
            "unit_of_measure": inventory.unit_of_measure,
            "last_updated": inventory.last_updated.isoformat(),
        }
    except Exception as e:
        logging.error(f"Ошибка проверки доступности товара {product_code}: {e}")
        return {
            "product_code": product_code,
            "available": False,
            "reason": f"Ошибка проверки: {str(e)}",
            "available_quantity": 0.0,
            "required_quantity": required_quantity,
            "shortage": required_quantity,
        }
