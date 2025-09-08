import os
import sqlite3
import tempfile
from unittest.mock import patch

import pytest

from db import init_db


class TestDatabaseIndexes:
    """Тесты для проверки индексов базы данных."""

    @pytest.fixture
    def temp_db(self):
        """Создает временную базу данных для тестов."""
        # Создаем временный файл
        fd, temp_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        # Патчим DB_PATH для использования временной БД
        with patch("db.DB_PATH", temp_path):
            init_db()
            yield temp_path

        # Удаляем временный файл
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    def test_indexes_created_successfully(self, temp_db):
        """Тест проверяет, что все индексы созданы успешно."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # Получаем список всех индексов
        cursor.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type = 'index' AND name LIKE 'idx_%'
            ORDER BY name
        """
        )

        indexes = [row[0] for row in cursor.fetchall()]
        conn.close()

        # Ожидаемые индексы
        expected_indexes = [
            "idx_suppliers_inn",
            "idx_suppliers_status",
            "idx_suppliers_rating",
            "idx_suppliers_last_transaction",
            "idx_supplier_documents_supplier_id",
            "idx_supplier_documents_type",
            "idx_supplier_documents_status",
            "idx_supplier_documents_upload_date",
            "idx_supplier_documents_supplier_type",
            "idx_price_history_supplier_id",
            "idx_price_history_product_code",
            "idx_price_history_valid_from",
            "idx_price_history_valid_to",
            "idx_price_history_supplier_product",
            "idx_price_history_date_range",
            "idx_supplier_transactions_supplier_id",
            "idx_supplier_transactions_date",
            "idx_supplier_transactions_type",
            "idx_supplier_transactions_status",
            "idx_supplier_transactions_supplier_date",
            "idx_performance_metrics_supplier_id",
            "idx_performance_metrics_period_end",
            "idx_performance_metrics_supplier_period",
            "idx_report_history_checked_at",
            "idx_report_history_filename",
        ]

        # Проверяем, что все ожидаемые индексы созданы
        for expected_index in expected_indexes:
            assert expected_index in indexes, f"Индекс {expected_index} не найден"

        assert len(indexes) == len(
            expected_indexes
        ), f"Ожидалось {len(expected_indexes)} индексов, найдено {len(indexes)}"

    def test_index_structure_suppliers(self, temp_db):
        """Тест проверяет структуру индексов для таблицы suppliers."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # Проверяем индекс по ИНН
        cursor.execute(
            """
            SELECT sql FROM sqlite_master
            WHERE type = 'index' AND name = 'idx_suppliers_inn'
        """
        )

        result = cursor.fetchone()
        assert result is not None, "Индекс idx_suppliers_inn не найден"
        assert (
            "suppliers (inn)" in result[0]
        ), "Неверная структура индекса idx_suppliers_inn"

        conn.close()

    def test_index_structure_supplier_documents(self, temp_db):
        """Тест проверяет структуру составного индекса для документов."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # Проверяем составной индекс supplier_id + document_type
        cursor.execute(
            """
            SELECT sql FROM sqlite_master
            WHERE type = 'index' AND name = 'idx_supplier_documents_supplier_type'
        """
        )

        result = cursor.fetchone()
        assert (
            result is not None
        ), "Составной индекс idx_supplier_documents_supplier_type не найден"
        assert (
            "supplier_documents (supplier_id, document_type)" in result[0]
        ), "Неверная структура составного индекса"

        conn.close()

    def test_index_structure_price_history(self, temp_db):
        """Тест проверяет структуру индексов для истории цен."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # Проверяем составной индекс для диапазона дат
        cursor.execute(
            """
            SELECT sql FROM sqlite_master
            WHERE type = 'index' AND name = 'idx_price_history_date_range'
        """
        )

        result = cursor.fetchone()
        assert result is not None, "Индекс idx_price_history_date_range не найден"
        assert (
            "price_history (valid_from, valid_to)" in result[0]
        ), "Неверная структура индекса для диапазона дат"

        conn.close()

    def test_indexes_do_not_duplicate(self, temp_db):
        """Тест проверяет, что индексы не дублируются при повторном вызове init_db."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # Получаем количество индексов до повторной инициализации
        cursor.execute(
            """
            SELECT COUNT(*) FROM sqlite_master
            WHERE type = 'index' AND name LIKE 'idx_%'
        """
        )

        count_before = cursor.fetchone()[0]
        conn.close()

        # Повторно инициализируем БД
        with patch("db.DB_PATH", temp_db):
            init_db()

        # Проверяем количество индексов после повторной инициализации
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT COUNT(*) FROM sqlite_master
            WHERE type = 'index' AND name LIKE 'idx_%'
        """
        )

        count_after = cursor.fetchone()[0]
        conn.close()

        assert (
            count_before == count_after
        ), "Индексы дублируются при повторной инициализации"

    def test_foreign_key_indexes_exist(self, temp_db):
        """Тест проверяет, что созданы индексы для внешних ключей."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # Проверяем индексы для supplier_id во всех связанных таблицах
        foreign_key_indexes = [
            "idx_supplier_documents_supplier_id",
            "idx_price_history_supplier_id",
            "idx_supplier_transactions_supplier_id",
            "idx_performance_metrics_supplier_id",
        ]

        for index_name in foreign_key_indexes:
            cursor.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type = 'index' AND name = ?
            """,
                (index_name,),
            )

            result = cursor.fetchone()
            assert (
                result is not None
            ), f"Индекс для внешнего ключа {index_name} не найден"

        conn.close()
