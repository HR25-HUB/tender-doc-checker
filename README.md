# Tender Document Checker 📄🔍

AI-ассистент по проверке тендерной документации на соответствие внутренним стандартам компании.

## 🚀 Быстрый старт

### Требования
- Python 3.11+
- [UV](https://docs.astral.sh/uv/) для управления зависимостями

### Установка

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd tender_doc_checker
```

2. Установите UV (если не установлен):
```bash
# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

3. Настройте проект:
```bash
make setup
```

4. Скопируйте и настройте переменные окружения:
```bash
cp .env.example .env
# Отредактируйте .env файл с вашими настройками
```

### Использование

#### Запуск веб-интерфейса (Streamlit)
```bash
make run-ui
```

#### Запуск API сервера (FastAPI)
```bash
make run-api
```

#### Разработка

```bash
# Установка зависимостей для разработки
make dev-install

# Форматирование кода
make format

# Проверка линтером
make lint

# Запуск тестов
make test

# Просмотр всех команд
make help
```

## 📁 Структура проекта

```
tender_doc_checker/
├── src/                    # Исходный код
│   ├── models.py          # Pydantic модели
│   ├── config.py          # Конфигурация
│   └── logger.py          # Настройка логирования
├── data/                  # Данные
│   ├── internal_standards.yaml
│   └── reports/
├── tests/                 # Тесты
├── prompts/              # Промпты для LLM
├── pyproject.toml        # Конфигурация проекта
├── Makefile             # Команды для разработки
└── README.md
```

## 🛠️ Технологии

- **UV** - управление зависимостями и виртуальными окружениями
- **Ruff** - линтер и форматтер кода
- **FastAPI** - веб API
- **Streamlit** - пользовательский интерфейс
- **Pydantic** - валидация данных
- **Loguru** - логирование
- **MyPy** - статическая типизация

## 📋 Функциональность

- ✅ Извлечение текста из PDF и DOCX документов
- ✅ Анализ документов с помощью LLM (GPT-4)
- ✅ Сравнение с внутренними стандартами компании
- ✅ Генерация PDF отчетов
- ✅ Интеграция с Bitrix24
- ✅ Email уведомления
- ✅ История проверок в SQLite
- ✅ Веб-интерфейс и API

## 🔧 Конфигурация

Основные настройки в файле `.env`:

```env
# Bitrix24
BITRIX_WEBHOOK_URL=https://your-domain.bitrix24.ru/rest/user_id/webhook_key

# Email
SMTP_SERVER=smtp.yandex.ru
SMTP_USER=your_email@yandex.ru
SMTP_PASSWORD=your_app_password
SMTP_FROM=your_email@yandex.ru

# OpenAI
OPENAI_API_KEY=your_openai_api_key
```

## 🧪 Тестирование

```bash
# Запуск всех тестов
make test

# Запуск с покрытием
uv run pytest --cov=. --cov-report=html
```

## 📈 Roadmap

- [ ] Docker контейнеризация
- [ ] Интеграция с облачными хранилищами
- [ ] Поддержка CSV таблиц
- [ ] Ролевая система проверок
- [ ] ML модель для анализа прецедентов

## 🤝 Участие в разработке

1. Форкните репозиторий
2. Создайте ветку для новой функции
3. Внесите изменения
4. Запустите тесты и линтеры
5. Создайте Pull Request

## 📄 Лицензия

MIT License
