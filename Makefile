.PHONY: help install dev-install format lint test clean run-api run-ui

check: ## Комплексная проверка качества проекта
	@echo "🔍 Проверка качества проекта..."
	@uv run python scripts/check_project.py

help: ## Показать справку
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Установить зависимости
	uv sync

dev-install: ## Установить зависимости для разработки
	uv sync --extra dev
	uv run pre-commit install

format: ## Форматировать код
	uv run ruff format .
	uv run ruff check --fix .

lint: ## Проверить код линтером
	uv run ruff check .
	uv run mypy .

test: ## Запустить тесты
	uv run pytest tests/ -v --cov=. --cov-report=html

clean: ## Очистить временные файлы
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .coverage htmlcov/ .pytest_cache/

run-api: ## Запустить FastAPI сервер
	uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000

run-ui: ## Запустить Streamlit интерфейс
	uv run streamlit run streamlit_ui.py

setup: dev-install ## Полная настройка проекта
	@echo "✅ Проект настроен! Используйте 'make help' для просмотра команд"
