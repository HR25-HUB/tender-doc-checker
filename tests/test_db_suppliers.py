import os
import sqlite3
import tempfile
from unittest.mock import mock_open, patch

import pytest

from db import (
    create_supplier,
    get_supplier_documents,
    get_supplier_history,
    init_db,
    save_supplier_document,
)
from src.models import SupplierHistory


class TestSupplierFunctions:
    """Тесты для функций работы с поставщиками (Task 2.2.2)"""

    @pytest.fixture(autouse=True)
    def setup_test_db(self):
        """Настройка тестовой базы данных перед каждым тестом"""
        # Создаем временную базу данных для тестов
        self.test_db_fd, self.test_db_path = tempfile.mkstemp(suffix=".db")

        # Патчим DB_PATH для использования тестовой БД
        with patch("db.DB_PATH", self.test_db_path):
            init_db()

        yield

        # Очищаем после теста
        os.close(self.test_db_fd)
        os.unlink(self.test_db_path)

    def test_create_supplier_success(self):
        """Тест успешного создания поставщика"""
        with patch("db.DB_PATH", self.test_db_path):
            supplier_id = create_supplier(
                name="ООО Тестовый поставщик",
                inn="1234567890",
                kpp="123456789",
                contact_person="Иванов И.И.",
                phone="+7 (495) 123-45-67",
                email="test@supplier.ru",
                address="г. Москва, ул. Тестовая, д. 1",
            )

        assert supplier_id is not None
        assert isinstance(supplier_id, int)
        assert supplier_id > 0

    def test_create_supplier_minimal_data(self):
        """Тест создания поставщика с минимальными данными"""
        with patch("db.DB_PATH", self.test_db_path):
            supplier_id = create_supplier(name="Минимальный поставщик")

        assert supplier_id is not None
        assert isinstance(supplier_id, int)
        assert supplier_id > 0

    def test_save_supplier_document_success(self):
        """Тест успешного сохранения документа поставщика"""
        with patch("db.DB_PATH", self.test_db_path):
            # Сначала создаем поставщика
            supplier_id = create_supplier(name="Тестовый поставщик")

            # Сохраняем документ
            document_id = save_supplier_document(
                supplier_id=supplier_id,
                document_type="коммерческое_предложение",
                document_name="КП №123",
                document_date="2024-01-15",
                content_summary="Коммерческое предложение на поставку оборудования",
            )

        assert document_id is not None
        assert isinstance(document_id, int)
        assert document_id > 0

    @patch("os.path.exists")
    @patch("os.path.getsize")
    @patch("builtins.open", new_callable=mock_open, read_data=b"test file content")
    def test_save_supplier_document_with_file(
        self, mock_file, mock_getsize, mock_exists
    ):
        """Тест сохранения документа с файлом"""
        mock_exists.return_value = True
        mock_getsize.return_value = 1024

        with patch("db.DB_PATH", self.test_db_path):
            supplier_id = create_supplier(name="Тестовый поставщик")

            document_id = save_supplier_document(
                supplier_id=supplier_id,
                document_type="договор",
                document_name="Договор поставки",
                file_path="/path/to/contract.pdf",
                document_date="2024-01-15",
            )

        assert document_id is not None
        assert isinstance(document_id, int)
        mock_exists.assert_called_once_with("/path/to/contract.pdf")
        mock_getsize.assert_called_once_with("/path/to/contract.pdf")

    def test_get_supplier_documents_success(self):
        """Тест получения списка документов поставщика"""
        with patch("db.DB_PATH", self.test_db_path):
            supplier_id = create_supplier(name="Тестовый поставщик")

            # Добавляем несколько документов
            doc1_id = save_supplier_document(
                supplier_id=supplier_id,
                document_type="коммерческое_предложение",
                document_name="КП №1",
            )
            doc2_id = save_supplier_document(
                supplier_id=supplier_id,
                document_type="договор",
                document_name="Договор №1",
            )

            # Получаем все документы
            documents = get_supplier_documents(supplier_id)

        assert len(documents) == 2
        assert all(isinstance(doc, dict) for doc in documents)
        assert any(doc["document_name"] == "КП №1" for doc in documents)
        assert any(doc["document_name"] == "Договор №1" for doc in documents)

    def test_get_supplier_documents_filtered(self):
        """Тест получения документов с фильтрацией по типу"""
        with patch("db.DB_PATH", self.test_db_path):
            supplier_id = create_supplier(name="Тестовый поставщик")

            # Добавляем документы разных типов
            save_supplier_document(
                supplier_id=supplier_id,
                document_type="коммерческое_предложение",
                document_name="КП №1",
            )
            save_supplier_document(
                supplier_id=supplier_id,
                document_type="договор",
                document_name="Договор №1",
            )

            # Получаем только коммерческие предложения
            documents = get_supplier_documents(supplier_id, "коммерческое_предложение")

        assert len(documents) == 1
        assert documents[0]["document_type"] == "коммерческое_предложение"
        assert documents[0]["document_name"] == "КП №1"

    def test_get_supplier_documents_empty(self):
        """Тест получения документов для поставщика без документов"""
        with patch("db.DB_PATH", self.test_db_path):
            supplier_id = create_supplier(name="Поставщик без документов")
            documents = get_supplier_documents(supplier_id)

        assert documents == []

    def test_get_supplier_history_from_db(self):
        """Тест получения истории поставщика из базы данных"""
        with patch("db.DB_PATH", self.test_db_path):
            # Создаем поставщика
            supplier_id = create_supplier(
                name="ООО Реальный поставщик",
                inn="9876543210",
                contact_person="Петров П.П.",
            )

            # Получаем историю
            history = get_supplier_history(supplier_id)

        assert isinstance(history, SupplierHistory)
        assert history.supplier_id == supplier_id
        assert history.supplier_info.name == "ООО Реальный поставщик"
        assert history.supplier_info.inn == "9876543210"
        assert history.supplier_info.contact_person == "Петров П.П."
        assert history.cooperation_status == "на проверке"
        assert history.transactions == []  # Нет транзакций
        assert history.total_transactions == 0

    def test_get_supplier_history_demo_data(self):
        """Тест получения демонстрационных данных для несуществующего поставщика"""
        with patch("db.DB_PATH", self.test_db_path):
            # Получаем историю для несуществующего поставщика
            history = get_supplier_history(999)

        assert isinstance(history, SupplierHistory)
        assert history.supplier_id == 999
        assert history.supplier_info.name == "ООО Поставщик 999"
        assert len(history.transactions) == 3  # Демонстрационные транзакции
        assert history.cooperation_status == "активный"
        assert history.overall_rating == 4.2

    def test_save_supplier_document_database_error(self):
        """Тест обработки ошибки базы данных при сохранении документа"""
        with patch("db.DB_PATH", "/invalid/path/database.db"):
            with pytest.raises(sqlite3.Error):
                save_supplier_document(
                    supplier_id=1,
                    document_type="тест",
                    document_name="Тестовый документ",
                )

    def test_create_supplier_database_error(self):
        """Тест обработки ошибки базы данных при создании поставщика"""
        with patch("db.DB_PATH", "/invalid/path/database.db"):
            with pytest.raises(sqlite3.Error):
                create_supplier(name="Тестовый поставщик")

    def test_get_supplier_documents_database_error(self):
        """Тест обработки ошибки базы данных при получении документов"""
        with patch("db.DB_PATH", "/invalid/path/database.db"):
            with pytest.raises(sqlite3.Error):
                get_supplier_documents(1)


class TestSupplierDatabaseIntegration:
    """Интеграционные тесты для работы с базой данных поставщиков"""

    @pytest.fixture(autouse=True)
    def setup_test_db(self):
        """Настройка тестовой базы данных"""
        self.test_db_fd, self.test_db_path = tempfile.mkstemp(suffix=".db")

        with patch("db.DB_PATH", self.test_db_path):
            init_db()

        yield

        os.close(self.test_db_fd)
        os.unlink(self.test_db_path)

    def test_full_supplier_workflow(self):
        """Тест полного рабочего процесса с поставщиком"""
        with patch("db.DB_PATH", self.test_db_path):
            # 1. Создаем поставщика
            supplier_id = create_supplier(
                name="ООО Полный тест", inn="1111111111", email="full@test.ru"
            )

            # 2. Добавляем документы
            doc1_id = save_supplier_document(
                supplier_id=supplier_id,
                document_type="коммерческое_предложение",
                document_name="КП от 15.01.2024",
                document_date="2024-01-15",
            )

            doc2_id = save_supplier_document(
                supplier_id=supplier_id,
                document_type="договор",
                document_name="Договор поставки №001",
                document_date="2024-01-20",
            )

            # 3. Получаем документы
            all_docs = get_supplier_documents(supplier_id)
            contract_docs = get_supplier_documents(supplier_id, "договор")

            # 4. Получаем историю поставщика
            history = get_supplier_history(supplier_id)

        # Проверяем результаты
        assert supplier_id > 0
        assert doc1_id > 0
        assert doc2_id > 0

        assert len(all_docs) == 2
        assert len(contract_docs) == 1
        assert contract_docs[0]["document_name"] == "Договор поставки №001"

        assert history.supplier_id == supplier_id
        assert history.supplier_info.name == "ООО Полный тест"
        assert history.supplier_info.inn == "1111111111"
        assert history.supplier_info.email == "full@test.ru"

    def test_multiple_suppliers_isolation(self):
        """Тест изоляции данных между разными поставщиками"""
        with patch("db.DB_PATH", self.test_db_path):
            # Создаем двух поставщиков
            supplier1_id = create_supplier(name="Поставщик 1")
            supplier2_id = create_supplier(name="Поставщик 2")

            # Добавляем документы каждому
            save_supplier_document(
                supplier_id=supplier1_id,
                document_type="договор",
                document_name="Договор поставщика 1",
            )

            save_supplier_document(
                supplier_id=supplier2_id,
                document_type="договор",
                document_name="Договор поставщика 2",
            )

            # Получаем документы каждого поставщика
            docs1 = get_supplier_documents(supplier1_id)
            docs2 = get_supplier_documents(supplier2_id)

        # Проверяем изоляцию
        assert len(docs1) == 1
        assert len(docs2) == 1
        assert docs1[0]["document_name"] == "Договор поставщика 1"
        assert docs2[0]["document_name"] == "Договор поставщика 2"
        assert docs1[0]["supplier_id"] == supplier1_id
        assert docs2[0]["supplier_id"] == supplier2_id
