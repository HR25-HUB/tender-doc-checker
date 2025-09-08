"""Скелеты тестов для аудита и истории проверок (Раздел 1 чек-листа).

Задача: подготовить минимальные тестовые заготовки, не ломающие текущий прогон тестов,
чтобы далее реализовать функциональность по TDD.
"""

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    pass

from fastapi.testclient import TestClient

from auth import get_current_user, require_role

# Подключаем приложение и зависимости аутентификации
from main import app

# Унифицированная настройка аутентификации как в tests/test_api.py
_test_user = {
    "username": "test_user",
    "user_id": "test_user_id",
    "role": "manager",
    "is_active": True,
}


def _mock_get_current_user():
    return _test_user


def _mock_require_role(roles):
    def _wrapper():
        return _test_user

    return _wrapper


# Переопределяем зависимости (для будущих вызовов эндпоинтов аудита)
app.dependency_overrides[get_current_user] = _mock_get_current_user
app.dependency_overrides[
    require_role(["manager", "supervisor", "administrator"])
] = _mock_require_role(["manager", "supervisor", "administrator"])  # noqa: E501
app.dependency_overrides[
    require_role(["administrator", "supervisor"])
] = _mock_require_role(["administrator", "supervisor"])  # noqa: E501
app.dependency_overrides[require_role(["administrator"])] = _mock_require_role(
    ["administrator"]
)  # noqa: E501

client = TestClient(app)


class TestAuditHistoryWrite:
    """Тесты записи истории проверок с метаданными."""

    @pytest.mark.skip(
        reason="Будет реализовано в рамках Раздела 1: запись истории с метаданными"
    )
    def test_save_history_with_metadata(self):
        """
        Должно сохранять запись истории с метаданными:
        - user_id
        - standard_version
        - source (например, 'api' или 'ui')

        План:
        1) Патчить путь БД/создать временную БД (monkeypatch DB_PATH или мок sqlite соединения).
        2) Вызвать функцию сохранения исторического отчета (db.save_report или аналог после расширения схемы).
        3) Проверить, что запись содержит нужные метаданные и корректные значения полей и дат.
        """
        # TODO: Реализация через TDD после добавления полей и индексов в db.py
        pass


class TestAuditHistoryFilters:
    """Тесты фильтрации истории (дата, тип документа) и пагинации."""

    def test_get_audit_history_filters_pagination(self, tmp_path, monkeypatch):
        """
        Должно корректно фильтровать и постранично выдавать историю:
        - по датам (start_date, end_date)
        - по типу документа (doc_type)
        - по пользователю (user_id) — опционально
        - пагинация limit/offset
        """
        import sqlite3
        from datetime import datetime, timedelta

        # Создаем временную БД для тестов
        test_db_path = tmp_path / "test_audit.db"
        monkeypatch.setattr("db.DB_PATH", str(test_db_path))

        # Импортируем после патча пути
        from db import init_db

        # Инициализируем БД и создаем тестовые данные
        init_db()

        conn = sqlite3.connect(str(test_db_path))
        cursor = conn.cursor()

        # Добавляем тестовые записи в report_history
        base_date = datetime.now()
        test_records = [
            (
                "user1",
                "spec_2024",
                "tender_specification",
                "1.0",
                "api",
                base_date.isoformat(),
            ),
            (
                "user1",
                "price_2024",
                "price_list",
                "1.0",
                "api",
                (base_date - timedelta(days=1)).isoformat(),
            ),
            (
                "user2",
                "contract_2024",
                "contract",
                "1.1",
                "ui",
                (base_date - timedelta(days=2)).isoformat(),
            ),
            (
                "user1",
                "spec_2023",
                "tender_specification",
                "1.0",
                "api",
                (base_date - timedelta(days=3)).isoformat(),
            ),
            (
                "user2",
                "price_2023",
                "price_list",
                "1.0",
                "ui",
                (base_date - timedelta(days=4)).isoformat(),
            ),
            (
                "user3",
                "contract_2023",
                "contract",
                "1.0",
                "api",
                (base_date - timedelta(days=5)).isoformat(),
            ),
        ]

        for user_id, doc_name, doc_type, version, source, created_at in test_records:
            cursor.execute(
                """
                INSERT INTO report_history (user_id, doc_name, doc_type, standard_version, source, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (user_id, doc_name, doc_type, version, source, created_at),
            )

        conn.commit()
        conn.close()

        # Тест 1: Получение всех записей без фильтров
        response = client.get("/audit/history")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 6
        assert data["total"] == 6

        # Тест 2: Фильтрация по типу документа
        response = client.get("/audit/history?doc_type=tender_specification")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert all(item["doc_type"] == "tender_specification" for item in data["items"])

        # Тест 3: Фильтрация по пользователю
        response = client.get("/audit/history?user_id=user1")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3
        assert all(item["user_id"] == "user1" for item in data["items"])

        # Тест 4: Фильтрация по дате (start_date)
        start_date = (base_date - timedelta(days=2)).isoformat()
        response = client.get(f"/audit/history?start_date={start_date}")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3  # Записи за последние 2 дня

        # Тест 5: Фильтрация по дате (end_date)
        end_date = (base_date - timedelta(days=3)).isoformat()
        response = client.get(f"/audit/history?end_date={end_date}")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 4  # Записи до 3 дней назад включительно

        # Тест 6: Комбинированная фильтрация
        response = client.get("/audit/history?doc_type=price_list&user_id=user1")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["doc_type"] == "price_list"
        assert data["items"][0]["user_id"] == "user1"

        # Тест 7: Пагинация (limit)
        response = client.get("/audit/history?limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 6

        # Тест 8: Пагинация (offset)
        response = client.get("/audit/history?limit=2&offset=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 6

        # Тест 9: Сортировка по дате (новые первые)
        response = client.get("/audit/history")
        assert response.status_code == 200
        data = response.json()
        dates = [datetime.fromisoformat(item["created_at"]) for item in data["items"]]
        assert dates == sorted(dates, reverse=True)


class TestAuditHistoryExport:
    """Тесты экспорта истории в файлы (txt/json) в data/reports/."""

    def test_export_history_txt_json(self, tmp_path):
        """
        Должно экспортировать историю в файлы:
        - export_audit_history('txt') => файл .txt
        - export_audit_history('json') => файл .json
        - директория назначения: data/reports/ (переопределить через monkeypatch для теста)

        План:
        1) Подготовить тестовые данные в БД.
        2) Вызвать функции экспорта для обоих форматов, с фильтрами.
        3) Проверить наличие файлов и непустое содержимое.
        """
        # Переопределяем директорию для отчетов на временную
        import json
        from pathlib import Path

        from src.config import settings

        # Сохраняем оригинальный путь
        original_reports_dir = settings.reports_dir

        try:
            # Устанавливаем временную директорию для тестов
            settings.reports_dir = tmp_path

            # Импортируем функцию экспорта
            from report_generator import export_audit_history

            # Экспортируем в JSON формат
            json_path = export_audit_history("json")

            # Проверяем, что файл создан
            assert Path(json_path).exists()
            assert json_path.endswith(".json")

            # Читаем содержимое JSON файла
            with open(json_path, encoding="utf-8") as f:
                json_content = json.load(f)

            # Проверяем структуру JSON
            assert "exported_at" in json_content
            assert "total" in json_content
            assert "items" in json_content

            # Экспортируем в TXT формат
            txt_path = export_audit_history("txt")

            # Проверяем, что файл создан
            assert Path(txt_path).exists()
            assert txt_path.endswith(".txt")

            # Читаем содержимое TXT файла
            with open(txt_path, encoding="utf-8") as f:
                txt_content = f.read()

            # Проверяем, что файл не пустой
            assert len(txt_content) > 0
            assert "Exported at:" in txt_content
            assert "Total items:" in txt_content

        finally:
            # Восстанавливаем оригинальный путь
            settings.reports_dir = original_reports_dir
