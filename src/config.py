"""Конфигурация приложения."""

import os
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Настройки приложения."""

    # Пути
    project_root: Path = Field(default_factory=lambda: Path(__file__).parent.parent)
    data_dir: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent / "data"
    )
    reports_dir: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent / "data" / "reports"
    )

    # База данных
    db_path: str = Field(default="data/history.db", description="Путь к SQLite базе")

    # Bitrix24
    bitrix_webhook_url: str | None = Field(None, description="URL webhook для Bitrix24")

    # Email
    smtp_server: str = Field(default="smtp.yandex.ru", description="SMTP сервер")
    smtp_port: int = Field(default=587, description="SMTP порт")
    smtp_user: str | None = Field(None, description="SMTP пользователь")
    smtp_password: str | None = Field(None, description="SMTP пароль")
    smtp_from: str | None = Field(None, description="Email отправителя")

    # OpenAI
    openai_api_key: str | None = Field(None, description="API ключ OpenAI")
    openai_model: str = Field(default="gpt-4", description="Модель OpenAI")

    # Логирование
    log_level: str = Field(default="INFO", description="Уровень логирования")
    log_file: str | None = Field(None, description="Файл для логов")

    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, description="Включить rate limiting")
    rate_limit_requests_per_second: int = Field(
        default=10, description="Запросов в секунду"
    )
    rate_limit_requests_per_minute: int = Field(
        default=100, description="Запросов в минуту"
    )
    rate_limit_requests_per_hour: int = Field(
        default=1000, description="Запросов в час"
    )
    rate_limit_storage_type: str = Field(
        default="memory", description="Тип хранилища: memory, redis"
    )
    rate_limit_bypass_roles: list[str] = Field(
        default_factory=lambda: ["administrator"],
        description="Роли, которые обходят rate limiting",
    )

    # Стандарты
    standards_file: str = Field(
        default="data/internal_standards.yaml", description="Файл со стандартами"
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Создаем необходимые директории
        self.data_dir.mkdir(exist_ok=True)
        self.reports_dir.mkdir(exist_ok=True)


# Путь к файлу конфигурации
CONFIG_PATH = "data/tolerances.yaml"

import os
from typing import Any, Optional

import yaml


class CategoryConfig:
    """Конфигурация категории товаров."""

    def __init__(
        self,
        name: str,
        tolerance: float,
        description: str,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        currency: str = "RUB",
        active: bool = True,
    ):
        self.name = name
        self.tolerance = tolerance
        self.description = description
        self.min_price = min_price
        self.max_price = max_price
        self.currency = currency
        self.active = active

    def to_dict(self) -> dict[str, Any]:
        """Преобразует конфигурацию в словарь."""
        return {
            "tolerance": self.tolerance,
            "description": self.description,
            "min_price": self.min_price,
            "max_price": self.max_price,
            "currency": self.currency,
            "active": self.active,
        }

    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> "CategoryConfig":
        """Создает конфигурацию из словаря."""
        return cls(
            name=name,
            tolerance=data.get("tolerance", 0.05),
            description=data.get("description", ""),
            min_price=data.get("min_price"),
            max_price=data.get("max_price"),
            currency=data.get("currency", "RUB"),
            active=data.get("active", True),
        )


class ToleranceConfig:
    """Конфигурация допусков для всех категорий."""

    def __init__(self):
        self.categories: dict[str, CategoryConfig] = {}
        self.default_tolerance = 0.07
        self.default_currency = "RUB"

    def add_category(self, category: CategoryConfig):
        """Добавляет категорию."""
        self.categories[category.name] = category

    def get_category(self, name: str) -> CategoryConfig:
        """Получает конфигурацию категории."""
        return self.categories.get(
            name,
            CategoryConfig(
                name=name,
                tolerance=self.default_tolerance,
                description="Категория по умолчанию",
            ),
        )

    def get_tolerance(self, category_name: str) -> float:
        """Получает допуск для категории."""
        category = self.get_category(category_name)
        return category.tolerance if category.active else self.default_tolerance

    def list_categories(self) -> list[str]:
        """Возвращает список активных категорий."""
        return [name for name, cat in self.categories.items() if cat.active]

    def to_dict(self) -> dict[str, Any]:
        """Преобразует конфигурацию в словарь."""
        return {
            "default_tolerance": self.default_tolerance,
            "default_currency": self.default_currency,
            "categories": {
                name: cat.to_dict() for name, cat in self.categories.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ToleranceConfig":
        """Создает конфигурацию из словаря."""
        config = cls()
        config.default_tolerance = data.get("default_tolerance", 0.07)
        config.default_currency = data.get("default_currency", "RUB")

        categories_data = data.get("categories", {})
        for name, cat_data in categories_data.items():
            config.add_category(CategoryConfig.from_dict(name, cat_data))

        return config


# Функции для работы с конфигурацией допусков
def load_config() -> ToleranceConfig:
    """Загружает конфигурацию допусков из файла или использует по умолчанию."""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, encoding="utf-8") as f:
                data = yaml.safe_load(f)
                return ToleranceConfig.from_dict(data)
        except Exception as e:
            print(f"Ошибка загрузки конфигурации из {CONFIG_PATH}: {e}")

    # Конфигурация по умолчанию
    config = ToleranceConfig()
    default_categories = {
        "electronics": {
            "tolerance": 0.05,
            "description": "Электроника и бытовая техника",
            "min_price": 1000,
            "max_price": 1000000,
            "currency": "RUB",
        },
        "clothing": {
            "tolerance": 0.10,
            "description": "Одежда, обувь и аксессуары",
            "min_price": 500,
            "max_price": 50000,
            "currency": "RUB",
        },
        "food": {
            "tolerance": 0.03,
            "description": "Продукты питания и напитки",
            "min_price": 10,
            "max_price": 10000,
            "currency": "RUB",
        },
        "construction": {
            "tolerance": 0.08,
            "description": "Строительные материалы и инструменты",
            "min_price": 100,
            "max_price": 1000000,
            "currency": "RUB",
        },
        "medicine": {
            "tolerance": 0.02,
            "description": "Медицинские препараты и оборудование",
            "min_price": 50,
            "max_price": 100000,
            "currency": "RUB",
        },
        "office": {
            "tolerance": 0.06,
            "description": "Офисные принадлежности и расходные материалы",
            "min_price": 50,
            "max_price": 50000,
            "currency": "RUB",
        },
        "default": {
            "tolerance": 0.07,
            "description": "Категория по умолчанию для неопознанных товаров",
            "min_price": 1,
            "max_price": 1000000,
            "currency": "RUB",
        },
    }

    for name, data in default_categories.items():
        config.add_category(CategoryConfig.from_dict(name, data))

    return config


def save_config(config: ToleranceConfig):
    """Сохраняет конфигурацию в файл."""
    try:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.dump(config.to_dict(), f, default_flow_style=False, allow_unicode=True)
    except Exception as e:
        print(f"Ошибка сохранения конфигурации в {CONFIG_PATH}: {e}")


def load_config_dict():
    """Загружает конфигурацию в виде словаря для обратной совместимости."""
    config = load_config()
    return config.to_dict()


def validate_tolerance_config(config=None):
    """Валидирует конфигурацию допусков."""
    if config is None:
        config = load_config()

    if isinstance(config, dict):
        # Обратная совместимость со старой структурой
        if "categories" not in config:
            raise KeyError("Отсутствует секция 'categories' в конфигурации")

        for category, config_data in config["categories"].items():
            if "tolerance" not in config_data:
                raise KeyError(f"Отсутствует поле 'tolerance' для категории {category}")

            tolerance = config_data["tolerance"]
            if not isinstance(tolerance, (int, float)):
                raise TypeError(
                    f"Значение tolerance для категории {category} должно быть числом"
                )

            if tolerance < 0:
                raise ValueError(
                    f"Значение tolerance для категории {category} не может быть отрицательным"
                )

            if tolerance >= 0.5:
                import warnings

                warnings.warn(
                    f"Значение tolerance для категории {category} выглядит слишком высоким: {tolerance}",
                    UserWarning,
                    stacklevel=2,
                )
    elif isinstance(config, ToleranceConfig):
        # Новая структура с объектами
        for name, category in config.categories.items():
            if not isinstance(category.tolerance, (int, float)):
                raise TypeError(
                    f"Значение tolerance для категории {name} должно быть числом"
                )

            if category.tolerance < 0:
                raise ValueError(
                    f"Значение tolerance для категории {name} не может быть отрицательным"
                )

            if category.tolerance >= 0.5:
                import warnings

                warnings.warn(
                    f"Значение tolerance для категории {name} выглядит слишком высоким: {category.tolerance}",
                    UserWarning,
                    stacklevel=2,
                )
    else:
        raise TypeError("Неверный тип конфигурации")


def add_custom_category(
    name: str,
    tolerance: float,
    description: str = "",
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    currency: str = "RUB",
    save: bool = True,
) -> bool:
    """Добавляет пользовательскую категорию."""
    try:
        config = load_config()
        category = CategoryConfig(
            name=name,
            tolerance=tolerance,
            description=description,
            min_price=min_price,
            max_price=max_price,
            currency=currency,
        )
        config.add_category(category)

        if save:
            save_config(config)

        return True
    except Exception as e:
        print(f"Ошибка добавления категории {name}: {e}")
        return False


def remove_category(name: str, save: bool = True) -> bool:
    """Удаляет категорию (деактивирует)."""
    try:
        config = load_config()
        if name in config.categories:
            config.categories[name].active = False
            if save:
                save_config(config)
            return True
        return False
    except Exception as e:
        print(f"Ошибка удаления категории {name}: {e}")
        return False


def get_category_info(category_name: str) -> dict[str, Any]:
    """Получает информацию о категории."""
    config = load_config()
    category = config.get_category(category_name)
    return category.to_dict()


def list_all_categories() -> dict[str, dict[str, Any]]:
    """Возвращает список всех категорий."""
    config = load_config()
    return {name: cat.to_dict() for name, cat in config.categories.items()}


def reset_to_default():
    """Сбрасывает конфигурацию к значениям по умолчанию."""
    try:
        if os.path.exists(CONFIG_PATH):
            os.remove(CONFIG_PATH)
        return True
    except Exception as e:
        print(f"Ошибка сброса конфигурации: {e}")
        return False


# Глобальный экземпляр настроек
settings = Settings()
