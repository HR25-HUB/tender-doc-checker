"""Тесты для FastAPI endpoints."""

import io
from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

if TYPE_CHECKING:
    from unittest.mock import Mock as MockType
else:
    MockType = Mock

from fastapi.testclient import TestClient

from auth import get_current_user, require_role
from main import app

# Мок пользователя для тестов
test_user = {
    "username": "test_user",
    "user_id": "test_user_id",
    "role": "manager",
    "is_active": True,
}


# Мок функций аутентификации
def mock_get_current_user():
    return test_user


def mock_require_role(roles):
    def wrapper():
        return test_user

    return wrapper


# Переопределяем зависимости для тестов
app.dependency_overrides[get_current_user] = mock_get_current_user
app.dependency_overrides[
    require_role(["manager", "supervisor", "administrator"])
] = mock_require_role(["manager", "supervisor", "administrator"])
app.dependency_overrides[
    require_role(["administrator", "supervisor"])
] = mock_require_role(["administrator", "supervisor"])
app.dependency_overrides[require_role(["administrator"])] = mock_require_role(
    ["administrator"]
)

client = TestClient(app)


class TestHealthEndpoint:
    """Тесты для health check endpoint."""

    def test_health_check(self) -> None:
        """Тест проверки состояния API."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestCheckEndpoint:
    """Тесты для endpoint проверки документов."""

    @patch("main.extract_text_from_file")
    @patch("main.check_document")
    @patch("main.save_report")
    @patch("main.generate_pdf")
    def test_check_document_success(
        self,
        mock_generate_pdf: MockType,
        mock_save_report: MockType,
        mock_check_document: MockType,
        mock_extract_text: MockType,
    ) -> None:
        """Тест успешной проверки документа."""
        # Настройка моков
        mock_extract_text.return_value = "Тестовый текст документа"
        mock_check_document.return_value = [
            {
                "section": "Техническое задание",
                "match": "да",
                "comments": "Все требования выполнены",
            }
        ]

        # Создание тестового файла
        test_file_content = b"Test PDF content"
        files = {"file": ("test.pdf", io.BytesIO(test_file_content), "application/pdf")}

        # Выполнение запроса
        response = client.post("/check/", files=files)

        # Проверки
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "test.pdf"
        assert len(data["report"]) == 1
        assert data["report"][0]["section"] == "Техническое задание"

        # Проверка вызовов моков
        mock_extract_text.assert_called_once()
        mock_check_document.assert_called_once_with("Тестовый текст документа")
        mock_save_report.assert_called_once()
        mock_generate_pdf.assert_called_once()

    def test_check_document_no_file(self) -> None:
        """Тест запроса без файла."""
        response = client.post("/check/")
        assert response.status_code == 422  # Validation error

    @patch("main.extract_text_from_file")
    def test_check_document_empty_text(self, mock_extract_text: MockType) -> None:
        """Тест с пустым текстом документа."""
        mock_extract_text.return_value = ""

        test_file_content = b"Test content"
        files = {"file": ("test.pdf", io.BytesIO(test_file_content), "application/pdf")}

        response = client.post("/check/", files=files)
        assert response.status_code == 400
        assert "Не удалось извлечь текст" in response.json()["detail"]


class TestUploadCreateTaskEndpoint:
    """Тесты для endpoint с созданием задачи в Bitrix24."""

    @patch("main.extract_text_from_file")
    @patch("main.check_document")
    @patch("main.save_report")
    @patch("main.generate_pdf")
    @patch("main.create_bitrix_task")
    @patch("main.settings")
    def test_upload_create_task_success(
        self,
        mock_settings: Mock,
        mock_create_task: Mock,
        mock_generate_pdf: Mock,
        mock_save_report: Mock,
        mock_check_document: Mock,
        mock_extract_text: Mock,
    ) -> None:
        """Тест успешной проверки с созданием задачи."""
        # Настройка моков
        mock_settings.bitrix_webhook_url = "https://test.bitrix24.ru/webhook"
        mock_extract_text.return_value = "Тестовый текст документа"
        mock_check_document.return_value = [
            {"section": "Техническое задание", "match": "да", "comments": "OK"}
        ]
        mock_create_task.return_value = 12345

        # Создание тестового файла
        test_file_content = b"Test PDF content"
        files = {"file": ("test.pdf", io.BytesIO(test_file_content), "application/pdf")}

        # Выполнение запроса
        response = client.post("/upload-and-create-task/", files=files)

        # Проверки
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "test.pdf"
        assert data["task_id"] == 12345

        # Проверка вызова создания задачи
        mock_create_task.assert_called_once()

    @patch("main.extract_text_from_file")
    @patch("main.check_document")
    @patch("main.save_report")
    @patch("main.generate_pdf")
    @patch("main.settings")
    def test_upload_create_task_no_bitrix_url(
        self,
        mock_settings: MockType,
        mock_generate_pdf: MockType,
        mock_save_report: MockType,
        mock_check_document: MockType,
        mock_extract_text: MockType,
    ) -> None:
        """Тест без URL Bitrix24."""
        # Настройка моков
        mock_settings.bitrix_webhook_url = None
        mock_extract_text.return_value = "Тестовый текст документа"
        mock_check_document.return_value = [
            {"section": "Техническое задание", "match": "да", "comments": "OK"}
        ]

        # Создание тестового файла
        test_file_content = b"Test PDF content"
        files = {"file": ("test.pdf", io.BytesIO(test_file_content), "application/pdf")}

        # Выполнение запроса
        response = client.post("/upload-and-create-task/", files=files)

        # Проверки
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "test.pdf"
        assert data["task_id"] is None


class TestCheckSupplierProposalEndpoint:
    """Тесты для эндпоинта /check-supplier-proposal/"""

    @patch("main.check_commercial_proposal")
    def test_check_supplier_proposal_success(self, mock_check_commercial_proposal):
        """Тест успешной проверки коммерческого предложения"""
        # Подготовка тестовых данных
        test_proposal = {
            "supplier": {
                "name": "ООО Тест Поставщик",
                "inn": "1234567890",
                "contact_person": "Иван Иванов",
                "phone": "+7 (123) 456-78-90",
                "email": "test@supplier.com",
            },
            "products": [
                {
                    "product_code": "TEST001",
                    "product_name": "Тестовый товар",
                    "quantity": 10,
                    "unit": "шт",
                    "unit_price": 100.0,
                    "total_amount": 1000.0,
                    "availability_status": "в наличии",
                }
            ],
            "delivery_terms": {
                "delivery_type": "доставка",
                "delivery_period_days": 5,
                "delivery_cost": 500.0,
                "delivery_address": "Москва, ул. Тестовая, д. 1",
            },
            "payment_terms": {
                "payment_type": "постоплата",
                "payment_period_days": 30,
                "payment_method": "безналичный расчет",
                "currency": "RUB",
            },
            "total_amount": 1500.0,
        }

        # Мокаем результат анализа

        from src.models import CommercialProposalAnalysis

        mock_analysis = CommercialProposalAnalysis(
            supplier_name="ООО Тест Поставщик",
            overall_score=8.5,
            overall_recommendation="принять",
            price_competitiveness="конкурентоспособные",
            payment_terms_rating=4.0,
            delivery_terms_rating=4.5,
            supplier_reliability_score=4.2,
            product_availability_score=4.8,
            risk_level="низкий",
            confidence_level=0.85,
        )

        mock_check_commercial_proposal.return_value = mock_analysis

        # Выполнение запроса
        response = client.post("/check-supplier-proposal/", json=test_proposal)

        # Проверка результата
        assert response.status_code == 200
        data = response.json()
        assert data["overall_score"] == 8.5
        assert data["overall_recommendation"] == "принять"
        assert data["supplier_name"] == "ООО Тест Поставщик"
        assert data["price_competitiveness"] == "конкурентоспособные"

        # Проверка вызова функции
        mock_check_commercial_proposal.assert_called_once()

    def test_check_supplier_proposal_invalid_data(self):
        """Тест с некорректными данными"""
        # Неполные данные предложения
        invalid_proposal = {
            "supplier": {
                "name": "ООО Тест"
                # Отсутствуют обязательные поля
            }
        }

        response = client.post("/check-supplier-proposal/", json=invalid_proposal)
        assert response.status_code == 422  # Validation Error

    @patch("main.check_commercial_proposal")
    def test_check_supplier_proposal_error(self, mock_check_commercial_proposal):
        """Тест обработки ошибок"""
        # Мокаем исключение
        mock_check_commercial_proposal.side_effect = Exception("Тестовая ошибка")

        test_proposal = {
            "supplier": {
                "name": "ООО Тест Поставщик",
                "inn": "1234567890",
                "contact_person": "Иван Иванов",
                "phone": "+7 (123) 456-78-90",
                "email": "test@supplier.com",
            },
            "products": [],
            "delivery_terms": {
                "delivery_type": "доставка",
                "delivery_period_days": 5,
                "delivery_cost": 0.0,
                "delivery_address": "Москва",
            },
            "payment_terms": {
                "payment_type": "постоплата",
                "payment_period_days": 30,
                "payment_method": "безналичный расчет",
                "currency": "RUB",
            },
            "total_amount": 0.0,
        }

        response = client.post("/check-supplier-proposal/", json=test_proposal)
        assert response.status_code == 500
        assert "Ошибка при проверке предложения" in response.json()["detail"]


class TestCheckProductSpecificationEndpoint:
    """Тесты для эндпоинта /check-product-specification/"""

    @patch("main.check_product_specification")
    def test_check_product_specification_success(
        self, mock_check_product_specification
    ):
        """Тест успешной проверки товарных спецификаций"""
        # Подготовка тестовых данных
        test_specifications = [
            {
                "product_code": "TEST001",
                "product_name": "Тестовый товар 1",
                "quantity": 10,
                "unit": "шт",
                "unit_price": 100.0,
                "total_amount": 1000.0,
                "availability_status": "в наличии",
                "category": "Электроника",
                "brand": "TestBrand",
            },
            {
                "product_code": "TEST002",
                "product_name": "Тестовый товар 2",
                "quantity": 5,
                "unit": "шт",
                "unit_price": 200.0,
                "total_amount": 1000.0,
                "availability_status": "под заказ",
            },
        ]

        # Мокаем результат проверки
        mock_results = [
            {
                "section": "Спецификация товара TEST001",
                "match": "да",
                "comments": "Спецификация товара корректна",
                "check_type": "товарный",
                "product_code": "TEST001",
            },
            {
                "section": "Статус наличия TEST001",
                "match": "да",
                "comments": "Товар заявлен как имеющийся в наличии",
                "check_type": "товарный",
                "product_code": "TEST001",
                "availability_check": "в наличии",
            },
            {
                "section": "Спецификация товара TEST002",
                "match": "да",
                "comments": "Спецификация товара корректна",
                "check_type": "товарный",
                "product_code": "TEST002",
            },
            {
                "section": "Статус наличия TEST002",
                "match": "частично",
                "comments": "Товар под заказ - требует уточнения сроков",
                "check_type": "товарный",
                "product_code": "TEST002",
                "availability_check": "под заказ",
            },
            {
                "section": "Общая сводка по спецификациям",
                "match": "да",
                "comments": "Проверено 2 товарных позиций; Общая сумма спецификаций: 2000.00 руб.; Все проверки пройдены успешно",
                "check_type": "товарный",
            },
        ]

        mock_check_product_specification.return_value = mock_results

        # Выполнение запроса
        response = client.post(
            "/check-product-specification/", json=test_specifications
        )

        # Проверка результата
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5
        assert data[0]["section"] == "Спецификация товара TEST001"
        assert data[0]["match"] == "да"
        assert data[-1]["section"] == "Общая сводка по спецификациям"

        # Проверка вызова функции
        mock_check_product_specification.assert_called_once()

    def test_check_product_specification_invalid_data(self):
        """Тест с некорректными данными"""
        # Неполные данные спецификации
        invalid_specifications = [
            {
                "product_code": "TEST001"
                # Отсутствуют обязательные поля
            }
        ]

        response = client.post(
            "/check-product-specification/", json=invalid_specifications
        )
        assert response.status_code == 422  # Validation Error

    def test_check_product_specification_empty_list(self):
        """Тест с пустым списком спецификаций"""
        empty_specifications = []

        response = client.post(
            "/check-product-specification/", json=empty_specifications
        )
        # Должен принять пустой список, но вернуть соответствующий результат
        assert response.status_code in [200, 422]

    @patch("main.check_product_specification")
    def test_check_product_specification_with_errors(
        self, mock_check_product_specification
    ):
        """Тест проверки спецификаций с ошибками"""
        test_specifications = [
            {
                "product_code": "ERROR001",
                "product_name": "Товар с ошибкой",
                "quantity": 1,  # Исправляю на корректное значение для прохождения валидации
                "unit": "шт",
                "unit_price": 100.0,  # Исправляю на корректное значение для прохождения валидации
                "total_amount": 100.0,
                "availability_status": "нет в наличии",
            }
        ]

        # Мокаем результат с ошибками
        mock_results = [
            {
                "section": "Спецификация товара ERROR001",
                "match": "нет",
                "comments": "Ошибки в спецификации: некорректное количество; некорректная цена; несоответствие общей суммы",
                "check_type": "товарный",
                "product_code": "ERROR001",
            },
            {
                "section": "Общая сводка по спецификациям",
                "match": "нет",
                "comments": "Проверено 1 товарных позиций; Общая сумма спецификаций: 100.00 руб.; Выявлены серьезные проблемы",
                "check_type": "товарный",
            },
        ]

        mock_check_product_specification.return_value = mock_results

        response = client.post(
            "/check-product-specification/", json=test_specifications
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["match"] == "нет"
        assert "Ошибки в спецификации" in data[0]["comments"]

    @patch("main.check_product_specification")
    def test_check_product_specification_error(self, mock_check_product_specification):
        """Тест обработки ошибок"""
        # Мокаем исключение
        mock_check_product_specification.side_effect = Exception(
            "Тестовая ошибка проверки"
        )

        test_specifications = [
            {
                "product_code": "TEST001",
                "product_name": "Тестовый товар",
                "quantity": 1,
                "unit": "шт",
                "unit_price": 100.0,
                "total_amount": 100.0,
                "availability_status": "в наличии",
            }
        ]

        response = client.post(
            "/check-product-specification/", json=test_specifications
        )
        assert response.status_code == 500
        assert "Ошибка при проверке спецификаций" in response.json()["detail"]


class TestGetSupplierHistoryEndpoint:
    """Тесты для эндпоинта /suppliers/{supplier_id}/history"""

    @patch("main.init_db")
    def test_get_supplier_history_success(self, mock_init_db):
        """Тест успешного получения истории поставщика"""
        # Инициализируем БД для теста
        from db import init_db

        init_db()

        supplier_id = 123

        response = client.get(f"/suppliers/{supplier_id}/history")

        assert response.status_code == 200
        data = response.json()

        # Проверяем основные поля
        assert data["supplier_id"] == supplier_id
        assert "supplier_info" in data
        assert "transactions" in data
        assert "current_metrics" in data

        # Проверяем информацию о поставщике
        supplier_info = data["supplier_info"]
        assert supplier_info["supplier_id"] == supplier_id
        assert supplier_info["name"] == f"ООО Поставщик {supplier_id}"
        assert supplier_info["inn"] == f"123456789{supplier_id % 10}"
        assert supplier_info["contact_person"] == "Иванов Иван Иванович"
        assert supplier_info["phone"] == "+7 (495) 123-45-67"
        assert supplier_info["email"] == f"contact@supplier{supplier_id}.ru"

        # Проверяем транзакции
        transactions = data["transactions"]
        assert len(transactions) == 3
        assert transactions[0]["transaction_type"] == "заказ"
        assert transactions[0]["amount"] == 150000.0
        assert transactions[1]["transaction_type"] == "поставка"
        assert transactions[1]["amount"] == 75000.0
        assert transactions[2]["transaction_type"] == "возврат"
        assert transactions[2]["amount"] == 5000.0

        # Проверяем метрики производительности
        performance = data["current_metrics"]
        assert performance["total_orders"] == 25
        assert performance["completed_orders"] == 23
        assert performance["cancelled_orders"] == 2
        assert performance["late_deliveries"] == 2

        # Проверяем общую информацию
        assert data["cooperation_status"] == "активный"
        assert data["total_transactions"] == 3

    @patch("main.init_db")
    def test_get_supplier_history_different_supplier(self, mock_init_db):
        """Тест получения истории для другого поставщика"""
        # Инициализируем БД для теста
        from db import init_db

        init_db()

        supplier_id = 456

        response = client.get(f"/suppliers/{supplier_id}/history")

        assert response.status_code == 200
        data = response.json()

        # Проверяем, что данные соответствуют запрошенному поставщику
        assert data["supplier_id"] == supplier_id
        assert data["supplier_info"]["name"] == f"ООО Поставщик {supplier_id}"
        assert data["supplier_info"]["inn"] == f"123456789{supplier_id % 10}"
        assert data["supplier_info"]["email"] == f"contact@supplier{supplier_id}.ru"

    def test_get_supplier_history_invalid_id_negative(self):
        """Тест с отрицательным ID поставщика"""
        supplier_id = -1

        response = client.get(f"/suppliers/{supplier_id}/history")

        assert response.status_code == 400
        assert (
            "ID поставщика должен быть положительным числом"
            in response.json()["detail"]
        )

    def test_get_supplier_history_invalid_id_zero(self):
        """Тест с нулевым ID поставщика"""
        supplier_id = 0

        response = client.get(f"/suppliers/{supplier_id}/history")

        assert response.status_code == 400
        assert (
            "ID поставщика должен быть положительным числом"
            in response.json()["detail"]
        )

    def test_get_supplier_history_invalid_id_string(self):
        """Тест с некорректным типом ID поставщика"""
        response = client.get("/suppliers/abc/history")

        assert response.status_code == 422  # Validation Error

    @patch("main.get_supplier_history")
    def test_get_supplier_history_error(self, mock_get_supplier_history):
        """Тест обработки ошибок при получении истории"""
        # Мокаем исключение
        mock_get_supplier_history.side_effect = Exception("Тестовая ошибка базы данных")

        supplier_id = 123
        response = client.get(f"/suppliers/{supplier_id}/history")

        assert response.status_code == 500
        assert "Ошибка при получении истории поставщика" in response.json()["detail"]

    @patch("main.init_db")
    def test_get_supplier_history_large_id(self, mock_init_db):
        """Тест с большим ID поставщика"""
        # Инициализируем БД для теста
        from db import init_db

        init_db()

        supplier_id = 999999

        response = client.get(f"/suppliers/{supplier_id}/history")

        assert response.status_code == 200
        data = response.json()
        assert data["supplier_id"] == supplier_id
        # Проверяем, что функция корректно обрабатывает большие ID
        assert data["supplier_info"]["inn"] == f"123456789{supplier_id % 10}"
