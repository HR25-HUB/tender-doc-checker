# Руководство по конфигурации категорий и допусков

## Обзор

Система конфигурации категорий и допусков позволяет гибко настраивать правила проверки цен для различных категорий товаров.

## Основные компоненты

### Классы

- **CategoryConfig** - конфигурация отдельной категории
- **ToleranceConfig** - основная конфигурация всех категорий

### Основные функции

- `load_config()` - загрузка конфигурации
- `save_config(config)` - сохранение конфигурации
- `add_custom_category()` - добавление новой категории
- `remove_category()` - удаление категории (деактивация)
- `get_category_info()` - получение информации о категории
- `list_all_categories()` - список всех категорий

## Структура конфигурационного файла

Файл конфигурации: `data/tolerances.yaml`

```yaml
default_tolerance: 0.07
default_currency: "RUB"

categories:
  electronics:
    tolerance: 0.05
    description: "Электроника и бытовая техника"
    min_price: 1000
    max_price: 1000000
    currency: "RUB"
    active: true
```

## Параметры категории

- **tolerance** (float): допуск в долях (0.05 = 5%)
- **description** (str): описание категории
- **min_price** (float, optional): минимальная цена
- **max_price** (float, optional): максимальная цена
- **currency** (str): валюта (по умолчанию "RUB")
- **active** (bool): активна ли категория

## Примеры использования

### Получение допуска для категории
```python
from src.config import load_config

config = load_config()
tolerance = config.get_tolerance('electronics')
print(f"Допуск для электроники: {tolerance * 100}%")
```

### Добавление новой категории
```python
from src.config import add_custom_category

add_custom_category(
    name="furniture",
    tolerance=0.08,
    description="Мебель и предметы интерьера",
    min_price=1000,
    max_price=500000
)
```

### Получение списка всех категорий
```python
from src.config import list_all_categories

categories = list_all_categories()
for name, info in categories.items():
    print(f"{name}: {info['description']}")
```

## Встроенные категории

- **electronics** - Электроника (5%)
- **clothing** - Одежда (10%)
- **food** - Продукты питания (3%)
- **construction** - Строительные материалы (8%)
- **medicine** - Медицинские препараты (2%)
- **office** - Офисные принадлежности (6%)
- **default** - По умолчанию (7%)

## Резервное копирование и восстановление

Для сброса настроек к значениям по умолчанию:
```python
from src.config import reset_to_default

reset_to_default()
```

## Валидация конфигурации

```python
from src.config import validate_tolerance_config

try:
    validate_tolerance_config()
    print("Конфигурация валидна")
except Exception as e:
    print(f"Ошибка валидации: {e}")
```
