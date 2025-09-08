# План расширения проекта (TDD чек-лист)

Правила выполнения:
- Сначала пишем тесты, затем реализуем код и только потом рефакторим.
- Задачи делим на маленькие и атомарные шаги (максимум 1 подтема за задачу).
- Отмечаем чекбокс по мере выполнения, не перескакивая этапы.

## 1) Аудит и история проверок (расширение)

Тесты
- [x] tests/test_audit_history.py::TestAuditHistoryWrite::test_save_history_with_metadata — запись истории с метаданными (user_id, standard_version, source)
- [x] tests/test_audit_history.py::TestAuditHistoryFilters::test_get_audit_history_filters_pagination — фильтры по дате/типу/пользователю и пагинация
- [x] tests/test_audit_history.py::TestAuditHistoryExport::test_export_history_txt_json — экспорт истории в txt/json в data/reports/
Код
- [x] db.py::init_db + таблица report_history — добавить поля: user_id, standard_version, source; индексы: created_at, doc_type, user_id
- [x] report_generator.py::export_audit_history(format, filters) — экспорт с учетом фильтров
- [x] main.py::get_audit_history_endpoint — эндпоинт GET /audit/history с фильтрами (start_date, end_date, doc_type, user_id) и пагинацией (limit, offset)

## 2) Проверка цен: допуски по категориям и валюты
Тесты
- [x] tests/test_price_checker_tolerances.py: допуски по категориям SKU (категория → tolerance)
- [x] tests/test_price_currency.py: конвертация валют (мок источника курсов), расчет отклонений после конверсии
- [x] tests/test_price_analytics_trends.py: выявление трендов цен (рост/падение) на истории
Код
- [x] src/config.py: конфигурация категорий и допусков (реализована расширенная система с YAML конфигурацией, классами CategoryConfig и ToleranceConfig)
- [x] price_checker.py: поддержка категорий допусков - обновлен для использования новой системы конфигурации с CategoryConfig и ToleranceConfig, добавлены методы работы с категориями
- [x] analytics.py/price_analytics.py: функции тренд-аналитики
  - **analytics.py**: добавлены методы `analyze_document_trends()`, `analyze_supplier_performance_trends()`, `analyze_system_usage_trends()`, `get_trend_analysis_dashboard()`, и `_generate_trend_summary()` для комплексного анализа трендов документов, поставщиков и использования системы
  - **price_analytics.py**: добавлены методы `analyze_seasonal_trends()`, `analyze_price_correlation()`, `forecast_price_trend()`, и `get_market_trend_summary()` для анализа ценовых трендов и прогнозирования
- [x] новый модуль rates.py: интерфейс курсов (инъекция зависимостей для моков)

## 3) Сравнение предложений поставщиков (многокритериально)
Тесты
- [x] tests/test_supplier_scoring.py: взвешенная оценка (цена, срок поставки, рейтинг)
- [x] tests/test_supplier_scoring.py: сортировка и топ-N рекомендаций
- [x] tests/test_supplier_scoring.py: сохранение принятого решения в БД
Код
- [x] recommendations.py: функции score_suppliers(), select_top_suppliers()
- [x] src/models.py: модель SupplierScore, веса критериев
- [x] main.py: эндпоинт POST /suppliers/compare (вход: цены/сроки/рейтинги, выход: топ-N)

## 4) Управление поставщиками и документами
Тесты
- [x] tests/test_supplier_documents.py: статусы документов (на проверке/одобрен/отклонен), валидации переходов
- [x] tests/test_supplier_documents.py: напоминания поставщику (моки email/Bitrix)
- [x] tests/test_supplier_uniqueness.py: уникальность ИНН и номера договора
Код
- [x] db.py: статусы документов, уникальные ограничения, индексы
- [x] bitrix_notifier.py/emailer.py: шлюзы уведомлений с безопасными мок-точками
- [x] main.py: эндпоинты смены статуса и отправки напоминаний

## 5) Извлечение и тегирование данных из документов
Тесты
- [x] tests/test_extractor_mapping.py: соответствие полей extractor ↔ internal_standards.yaml
- [x] tests/test_extractor_multifile.py: разбор многостраничных PDF/DOCX (моки PyMuPDF/python-docx)
- [x] tests/test_extractor_errors.py: устойчивость к ошибкам и fallback-механизм
Код
- [x] extractor.py: улучшение стратегий парсинга и обработка ошибок
- [x] chunker.py: семантическая нарезка с лимитом по токенам
- [x] src/logger.py: детальное логирование исключений парсинга

## 6) API и аутентификация/авторизация
Тесты
- [x] tests/test_auth_roles.py: роли и доступ к маршрутам (roles.py)
- [x] tests/test_rate_limit.py: ограничение частоты запросов (in-memory мок)
- [x] tests/test_api_schemas.py: проверка схем Pydantic ответов
Код
- [x] roles.py/main.py: применение ролей к защищенным эндпоинтам
- [x] main.py: middleware для rate limiting (настройка в src/config.py)
- [x] main.py/src/models.py: явные схемы запросов/ответов (все эндпоинты используют Pydantic схемы, добавлен tests/test_api_schemas.py)

## 7) UI (Streamlit)
Тесты
- [x] tests/test_ui_smoke.py: smoke-тест импортов и вызова ключевых функций c мок-данными
- [x] tests/test_ui_tables.py: формирование таблиц/фильтров на основе моков
Код
- [x] streamlit_ui.py: вынести бизнес-логику в чистые функции (минимум кода в UI-слое)
- [x] streamlit_ui.py: индикаторы прогресса, фильтры, загрузка файлов с валидацией

## 8) CI/CD и качество
Тесты
- [x] tests/test_run_tests.py: проверка скрипта run_tests.py (возврат корректного кода выхода)
- [x] pytest.ini (pyproject): warnings-as-errors для ключевых категорий (с исключениями)
Код
- [x] .github/workflows/ci.yml: порог покрытия 60% → 70% по этапам, матрица Python 3.11/3.12
- [x] pre-commit: ruff + mypy обязательны перед коммитом

## 9) Данные и сценарии
Задачи
- [x] tests/resources/: добавить примеры КП, спецификаций, прайсов (маленькие, обезличенные)
- [x] TESTING_PLAN.md: дописать сценарии с привязкой к реальным кейсам оптовой компании (крупные спецификации, партии, скидки)
- В тестах для БД использовать временные файлы и patch DB_PATH (как в существующих тестах).
- Для внешних сервисов (Bitrix, SMTP, OpenAI) всегда использовать моки/фикстуры.
