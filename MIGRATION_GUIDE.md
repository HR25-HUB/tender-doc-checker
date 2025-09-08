# 🔄 Руководство по миграции на UV и Ruff

Это руководство поможет вам перейти от старой системы управления зависимостями к современному стеку с UV и Ruff.

## 📋 Что изменилось

### ✅ Добавлено
- **UV** - современный менеджер пакетов и виртуальных окружений
- **Ruff** - быстрый линтер и форматтер кода
- **Pydantic** - валидация данных и настроек
- **Loguru** - структурированное логирование
- **MyPy** - статическая типизация
- **Pre-commit hooks** - автоматические проверки кода
- **Современная структура проекта** с src layout

### 🗑️ Заменено
- `requirements.txt` → `pyproject.toml` с точными версиями
- Ручное управление зависимостями → автоматическое с UV
- Отсутствие линтера → Ruff для проверки качества кода
- Простые типы → Pydantic модели с валидацией

## 🚀 Пошаговая миграция

### Шаг 1: Установка UV

#### Windows (PowerShell)
```powershell
irm https://astral.sh/uv/install.ps1 | iex
```

#### macOS/Linux
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Шаг 2: Автоматическая настройка проекта

#### Windows
```powershell
.\scripts\setup.ps1
```

#### macOS/Linux
```bash
python scripts/setup.py
```

#### Или через Makefile
```bash
make setup
```

### Шаг 3: Настройка переменных окружения

1. Скопируйте `.env.example` в `.env`:
```bash
cp .env.example .env
```

2. Отредактируйте `.env` файл с вашими настройками:
```env
# Bitrix24
BITRIX_WEBHOOK_URL=https://your-domain.bitrix24.ru/rest/user_id/webhook_key

# Email
SMTP_USER=your_email@yandex.ru
SMTP_PASSWORD=your_app_password

# OpenAI
OPENAI_API_KEY=your_openai_api_key
```

### Шаг 4: Проверка миграции

```bash
# Проверка зависимостей
uv sync --extra dev

# Проверка линтера
make lint

# Запуск тестов
make test

# Запуск приложения
make run-api
```

## 🛠️ Новые команды разработки

### Управление зависимостями
```bash
# Установка зависимостей
uv sync

# Установка зависимостей для разработки
uv sync --extra dev

# Добавление новой зависимости
uv add package_name

# Добавление зависимости для разработки
uv add --dev package_name

# Обновление зависимостей
uv lock --upgrade
```

### Качество кода
```bash
# Форматирование кода
make format
# или
uv run ruff format .

# Проверка линтером
make lint
# или
uv run ruff check .

# Автоисправление проблем
uv run ruff check --fix .

# Проверка типов
uv run mypy .
```

### Тестирование
```bash
# Запуск всех тестов
make test

# Запуск с покрытием
uv run pytest --cov=. --cov-report=html

# Запуск конкретного теста
uv run pytest tests/test_checker.py::test_check_document_basic
```

### Запуск приложения
```bash
# API сервер
make run-api
# или
uv run uvicorn main:app --reload

# Streamlit UI
make run-ui
# или
uv run streamlit run streamlit_ui.py
```

## 📁 Новая структура проекта

```
tender_doc_checker/
├── src/                    # Новая папка с исходным кодом
│   ├── __init__.py
│   ├── models.py          # Pydantic модели
│   ├── config.py          # Централизованная конфигурация
│   └── logger.py          # Настройка логирования
├── scripts/               # Скрипты для настройки
│   ├── setup.py
│   └── setup.ps1
├── tests/                 # Улучшенные тесты
│   ├── test_models.py     # Тесты моделей
│   ├── test_api.py        # Тесты API
│   └── test_checker.py    # Существующие тесты
├── pyproject.toml         # Современная конфигурация проекта
├── .pre-commit-config.yaml # Pre-commit hooks
├── Makefile              # Команды для разработки
├── .env.example          # Пример переменных окружения
├── .gitignore            # Обновленный gitignore
└── README.md             # Обновленная документация
```

## 🔧 Конфигурация инструментов

### Ruff (pyproject.toml)
```toml
[tool.ruff]
target-version = "py311"
line-length = 88
select = ["E", "W", "F", "I", "B", "C4", "UP"]
```

### MyPy (pyproject.toml)
```toml
[tool.mypy]
python_version = "3.11"
check_untyped_defs = true
disallow_untyped_defs = true
```

### Pytest (pyproject.toml)
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra -q --strict-markers"
```

## 🚨 Возможные проблемы и решения

### Проблема: UV не найден после установки
**Решение**: Перезапустите терминал или обновите PATH:
```bash
# Windows
$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "User")

# macOS/Linux
source ~/.bashrc  # или ~/.zshrc
```

### Проблема: Ошибки импортов после миграции
**Решение**: Убедитесь, что используете UV для запуска:
```bash
# Вместо
python main.py

# Используйте
uv run python main.py
```

### Проблема: Pre-commit hooks не работают
**Решение**: Переустановите hooks:
```bash
uv run pre-commit uninstall
uv run pre-commit install
```

### Проблема: Ошибки типизации MyPy
**Решение**: Добавьте type hints или используйте `# type: ignore`:
```python
# Было
def process_file(filename):
    return result

# Стало
def process_file(filename: str) -> dict[str, Any]:
    return result
```

## 📈 Преимущества новой системы

1. **Скорость**: UV в 10-100 раз быстрее pip
2. **Надежность**: Детерминированные зависимости с lock-файлом
3. **Качество кода**: Автоматическое форматирование и проверки
4. **Типизация**: Статическая проверка типов с MyPy
5. **Автоматизация**: Pre-commit hooks и CI/CD
6. **Современность**: Соответствие лучшим практикам Python

## 🆘 Получение помощи

Если возникли проблемы:

1. Проверьте логи: `uv run python -c "from src.logger import logger; logger.info('test')"`
2. Запустите диагностику: `make lint && make test`
3. Посмотрите документацию: `make help`
4. Создайте issue в репозитории проекта
