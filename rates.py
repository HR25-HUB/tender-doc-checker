"""
Модуль для работы с курсами валют.

Предоставляет интерфейс для получения курсов валют с поддержкой
инъекции зависимостей для тестирования.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Protocol

logger = logging.getLogger(__name__)


class ExchangeRateProvider(Protocol):
    """Протокол для провайдеров курсов валют."""

    def get_rate(
        self, from_currency: str, to_currency: str, date: Optional[datetime] = None
    ) -> float:
        """Получить курс обмена между валютами."""
        ...

    def get_rates(
        self, base_currency: str, date: Optional[datetime] = None
    ) -> dict[str, float]:
        """Получить все курсы относительно базовой валюты."""
        ...


class BaseExchangeRateProvider(ABC):
    """Базовый абстрактный класс для провайдеров курсов валют."""

    @abstractmethod
    def get_rate(
        self, from_currency: str, to_currency: str, date: Optional[datetime] = None
    ) -> float:
        """Получить курс обмена между валютами."""
        pass

    @abstractmethod
    def get_rates(
        self, base_currency: str, date: Optional[datetime] = None
    ) -> dict[str, float]:
        """Получить все курсы относительно базовой валюты."""
        pass


class MockExchangeRateProvider(BaseExchangeRateProvider):
    """Мок-провайдер для тестирования."""

    def __init__(self, rates: Optional[dict[str, dict[str, float]]] = None):
        """
        Инициализировать мок-провайдер.

        Args:
            rates: Словарь курсов валют {base: {target: rate}}
        """
        self.rates = rates or {
            "USD": {"EUR": 0.85, "RUB": 90.0, "CNY": 7.2},
            "EUR": {"USD": 1.18, "RUB": 106.0, "CNY": 8.5},
            "RUB": {"USD": 0.011, "EUR": 0.0094, "CNY": 0.08},
            "CNY": {"USD": 0.139, "EUR": 0.118, "RUB": 12.5},
        }

    def get_rate(
        self, from_currency: str, to_currency: str, date: Optional[datetime] = None
    ) -> float:
        """Получить курс обмена между валютами из мок-данных."""
        if from_currency == to_currency:
            return 1.0

        if from_currency in self.rates and to_currency in self.rates[from_currency]:
            return self.rates[from_currency][to_currency]
        elif to_currency in self.rates and from_currency in self.rates[to_currency]:
            return 1.0 / self.rates[to_currency][from_currency]
        else:
            logger.warning(f"Курс {from_currency}/{to_currency} не найден в мок-данных")
            return 1.0

    def get_rates(
        self, base_currency: str, date: Optional[datetime] = None
    ) -> dict[str, float]:
        """Получить все курсы относительно базовой валюты из мок-данных."""
        if base_currency in self.rates:
            return self.rates[base_currency].copy()
        else:
            logger.warning(f"Базовая валюта {base_currency} не найдена в мок-данных")
            return {}


class ExchangeRateService:
    """Сервис для работы с курсами валют."""

    def __init__(self, provider: Optional[ExchangeRateProvider] = None):
        """
        Инициализировать сервис курсов валют.

        Args:
            provider: Провайдер курсов валют (можно заменить для тестирования)
        """
        self.provider = provider or MockExchangeRateProvider()

    def convert_amount(
        self,
        amount: float,
        from_currency: str,
        to_currency: str,
        date: Optional[datetime] = None,
    ) -> float:
        """
        Конвертировать сумму между валютами.

        Args:
            amount: Сумма для конвертации
            from_currency: Исходная валюта
            to_currency: Целевая валюта
            date: Дата курса (опционально)

        Returns:
            Сконвертированная сумма
        """
        if from_currency == to_currency:
            return amount

        rate = self.provider.get_rate(from_currency, to_currency, date)
        return amount * rate

    def get_exchange_rate(
        self, from_currency: str, to_currency: str, date: Optional[datetime] = None
    ) -> float:
        """
        Получить курс обмена между валютами.

        Args:
            from_currency: Исходная валюта
            to_currency: Целевая валюта
            date: Дата курса (опционально)

        Returns:
            Курс обмена
        """
        return self.provider.get_rate(from_currency, to_currency, date)

    def get_all_rates(
        self, base_currency: str = "USD", date: Optional[datetime] = None
    ) -> dict[str, float]:
        """
        Получить все курсы относительно базовой валюты.

        Args:
            base_currency: Базовая валюта
            date: Дата курса (опционально)

        Returns:
            Словарь курсов {валюта: курс}
        """
        return self.provider.get_rates(base_currency, date)


# Глобальный экземпляр сервиса
_exchange_rate_service = None


def get_exchange_rate_service(
    provider: Optional[ExchangeRateProvider] = None
) -> ExchangeRateService:
    """
    Получить экземпляр сервиса курсов валют.

    Args:
        provider: Провайдер курсов валют (для тестирования)

    Returns:
        Экземпляр ExchangeRateService
    """
    global _exchange_rate_service

    if provider is not None:
        return ExchangeRateService(provider)

    if _exchange_rate_service is None:
        _exchange_rate_service = ExchangeRateService()

    return _exchange_rate_service


def reset_exchange_rate_service():
    """Сбросить глобальный экземпляр сервиса (для тестирования)."""
    global _exchange_rate_service
    _exchange_rate_service = None
