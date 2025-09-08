"""
Тесты для валидации схем Pydantic ответов API.

Этот модуль содержит тесты для проверки корректности сериализации/десериализации
и валидации всех Pydantic моделей, используемых в API ответах.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from src.models import (
    BitrixTaskRequest,
    CheckResult,
    CommercialProposal,
    DeliveryTerms,
    DocumentChunk,
    DocumentReport,
    EmailRequest,
    PaymentTerms,
    ProductSpecification,
    SupplierDocument,
    SupplierInfo,
    UploadResponse,
    User,
)


class TestUserModel:
    """Тесты для модели User."""

    def test_user_creation_minimal(self):
        """Создание пользователя с минимальными данными."""
        user = User(username="testuser")
        assert user.username == "testuser"
        assert user.email is None
        assert user.full_name is None
        assert user.disabled is False
        assert user.role == "user"
        assert user.hashed_password is None

    def test_user_creation_full(self):
        """Создание пользователя со всеми полями."""
        user = User(
            username="admin",
            email="admin@example.com",
            full_name="Admin User",
            disabled=False,
            role="admin",
            hashed_password="hashed_password_here",
        )
        assert user.username == "admin"
        assert user.email == "admin@example.com"
        assert user.full_name == "Admin User"
        assert user.disabled is False
        assert user.role == "admin"
        assert user.hashed_password == "hashed_password_here"

    def test_user_serialization(self):
        """Тест сериализации пользователя в JSON."""
        user = User(username="testuser", email="test@example.com")
        json_data = user.model_dump_json()
        assert "testuser" in json_data
        assert "test@example.com" in json_data

    def test_user_deserialization(self):
        """Тест десериализации пользователя из JSON."""
        json_data = (
            '{"username": "testuser", "email": "test@example.com", "role": "user"}'
        )
        user = User.model_validate_json(json_data)
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.role == "user"

    def test_user_validation_empty_username(self):
        """Тест валидации при пустом имени пользователя."""
        user = User(username="")
        assert user.username == ""


class TestDocumentChunkModel:
    """Тесты для модели DocumentChunk."""

    def test_document_chunk_creation(self):
        """Создание части документа."""
        chunk = DocumentChunk(title="Раздел 1", content="Содержимое раздела 1")
        assert chunk.title == "Раздел 1"
        assert chunk.content == "Содержимое раздела 1"

    def test_document_chunk_validation_empty_title(self):
        """Тест валидации при пустом заголовке."""
        chunk = DocumentChunk(title="", content="Some content")
        assert chunk.title == ""

    def test_document_chunk_validation_empty_content(self):
        """Тест валидации при пустом содержимом."""
        chunk = DocumentChunk(title="Valid title", content="")
        assert chunk.content == ""


class TestCheckResultModel:
    """Тесты для модели CheckResult."""

    def test_check_result_creation_minimal(self):
        """Создание результата проверки с минимальными данными."""
        result = CheckResult(section="Техническое задание", match="да")
        assert result.section == "Техническое задание"
        assert result.match == "да"
        assert result.comments == ""
        assert result.confidence is None

    def test_check_result_creation_full(self):
        """Создание результата проверки со всеми полями."""
        result = CheckResult(
            section="Техническое задание",
            match="частично",
            comments="Некоторые требования не выполнены",
            confidence=0.75,
            price_check="завышена",
            availability_check="в наличии",
            quantity_check="достаточно",
            product_code="PROD001",
            expected_price=100.0,
            actual_price=120.0,
            price_deviation_percent=20.0,
            expected_quantity=10,
            actual_quantity=10,
            supplier_name="ООО Поставщик",
            check_type="товарный",
        )
        assert result.section == "Техническое задание"
        assert result.match == "частично"
        assert result.confidence == 0.75
        assert result.price_check == "завышена"
        assert result.price_deviation_percent == 20.0

    def test_check_result_invalid_match_value(self):
        """Тест валидации при недопустимом значении match."""
        with pytest.raises(ValidationError):
            CheckResult(section="test", match="invalid")

    def test_check_result_confidence_bounds(self):
        """Тест границ значения confidence."""
        # Допустимые значения
        CheckResult(section="test", match="да", confidence=0.0)
        CheckResult(section="test", match="да", confidence=1.0)
        CheckResult(section="test", match="да", confidence=0.5)

        # Недопустимые значения
        with pytest.raises(ValidationError):
            CheckResult(section="test", match="да", confidence=-0.1)
        with pytest.raises(ValidationError):
            CheckResult(section="test", match="да", confidence=1.1)


class TestDocumentReportModel:
    """Тесты для модели DocumentReport."""

    def test_document_report_creation(self):
        """Создание отчета о документе."""
        results = [
            CheckResult(section="Раздел 1", match="да"),
            CheckResult(section="Раздел 2", match="нет"),
        ]
        report = DocumentReport(
            filename="test.pdf", results=results, overall_status="не соответствует"
        )
        assert report.filename == "test.pdf"
        assert len(report.results) == 2
        assert report.overall_status == "не соответствует"
        assert isinstance(report.checked_at, datetime)

    def test_document_report_invalid_status(self):
        """Тест валидации при недопустимом статусе."""
        results = [CheckResult(section="test", match="да")]
        with pytest.raises(ValidationError):
            DocumentReport(
                filename="test.pdf", results=results, overall_status="invalid"
            )


class TestBitrixTaskRequestModel:
    """Тесты для модели BitrixTaskRequest."""

    def test_bitrix_task_creation_minimal(self):
        """Создание задачи Bitrix с минимальными данными."""
        task = BitrixTaskRequest(title="Тестовая задача", description="Описание задачи")
        assert task.title == "Тестовая задача"
        assert task.description == "Описание задачи"
        assert task.responsible_id is None
        assert task.deadline is None

    def test_bitrix_task_creation_full(self):
        """Создание задачи Bitrix со всеми полями."""
        deadline = datetime(2024, 12, 31, 23, 59, 59)
        task = BitrixTaskRequest(
            title="Важная задача",
            description="Очень важное описание",
            responsible_id=123,
            deadline=deadline,
        )
        assert task.title == "Важная задача"
        assert task.responsible_id == 123
        assert task.deadline == deadline


class TestEmailRequestModel:
    """Тесты для модели EmailRequest."""

    def test_email_request_creation_minimal(self):
        """Создание email запроса с минимальными данными."""
        email = EmailRequest(
            recipient="test@example.com", subject="Тест", body="Тестовое письмо"
        )
        assert email.recipient == "test@example.com"
        assert email.subject == "Тест"
        assert email.body == "Тестовое письмо"
        assert email.pdf_path is None

    def test_email_request_validation_invalid_email(self):
        """Тест валидации при неверном формате email."""
        email = EmailRequest(recipient="invalid-email", subject="test", body="test")
        assert email.recipient == "invalid-email"


class TestUploadResponseModel:
    """Тесты для модели UploadResponse."""

    def test_upload_response_creation(self):
        """Создание ответа на загрузку."""
        results = [CheckResult(section="test", match="да")]
        response = UploadResponse(filename="test.pdf", report=results)
        assert response.filename == "test.pdf"
        assert len(response.report) == 1
        assert response.task_id is None
        assert response.pdf_path is None

    def test_upload_response_creation_full(self):
        """Создание ответа на загрузку со всеми полями."""
        results = [CheckResult(section="test", match="да")]
        response = UploadResponse(
            filename="test.pdf",
            report=results,
            task_id=123,
            pdf_path="/reports/test_report.pdf",
        )
        assert response.task_id == 123
        assert response.pdf_path == "/reports/test_report.pdf"


class TestProductSpecificationModel:
    """Тесты для модели ProductSpecification."""

    def test_product_spec_creation(self):
        """Создание товарной спецификации."""
        spec = ProductSpecification(
            product_code="PROD001",
            product_name="Тестовый товар",
            quantity=10,
            unit="шт",
            unit_price=100.0,
            total_amount=1000.0,
            availability_status="в наличии",
        )
        assert spec.product_code == "PROD001"
        assert spec.quantity == 10
        assert spec.total_amount == 1000.0
        assert spec.availability_status == "в наличии"

    def test_product_spec_validation_zero_quantity(self):
        """Тест валидации при нулевом количестве."""
        with pytest.raises(ValidationError):
            ProductSpecification(
                product_code="PROD001",
                product_name="Товар",
                quantity=0,
                unit="шт",
                unit_price=100.0,
                total_amount=0.0,
                availability_status="в наличии",
            )

    def test_product_spec_validation_negative_price(self):
        """Тест валидации при отрицательной цене."""
        with pytest.raises(ValidationError):
            ProductSpecification(
                product_code="PROD001",
                product_name="Товар",
                quantity=1,
                unit="шт",
                unit_price=-100.0,
                total_amount=-100.0,
                availability_status="в наличии",
            )

    def test_product_spec_invalid_availability(self):
        """Тест валидации при недопустимом статусе наличия."""
        with pytest.raises(ValidationError):
            ProductSpecification(
                product_code="PROD001",
                product_name="Товар",
                quantity=1,
                unit="шт",
                unit_price=100.0,
                total_amount=100.0,
                availability_status="недопустимый",
            )


class TestSupplierInfoModel:
    """Тесты для модели SupplierInfo."""

    def test_supplier_info_creation_minimal(self):
        """Создание информации о поставщике с минимальными данными."""
        supplier = SupplierInfo(name="ООО Поставщик")
        assert supplier.name == "ООО Поставщик"
        assert supplier.supplier_id is None
        assert supplier.inn is None

    def test_supplier_info_creation_full(self):
        """Создание информации о поставщике со всеми полями."""
        supplier = SupplierInfo(
            supplier_id=123,
            name="ООО Тест Поставщик",
            inn="1234567890",
            kpp="123456789",
            contact_person="Иван Иванов",
            phone="+7 (123) 456-78-90",
            email="test@supplier.com",
            address="Москва, ул. Тестовая, д. 1",
            rating=4.5,
        )
        assert supplier.supplier_id == 123
        assert supplier.name == "ООО Тест Поставщик"
        assert supplier.inn == "1234567890"
        assert supplier.rating == 4.5

    def test_supplier_rating_bounds(self):
        """Тест границ значения рейтинга."""
        # Допустимые значения
        SupplierInfo(name="Поставщик", rating=0.0)
        SupplierInfo(name="Поставщик", rating=5.0)
        SupplierInfo(name="Поставщик", rating=3.5)

        # Недопустимые значения
        with pytest.raises(ValidationError):
            SupplierInfo(name="Поставщик", rating=-0.1)
        with pytest.raises(ValidationError):
            SupplierInfo(name="Поставщик", rating=5.1)


class TestPaymentTermsModel:
    """Тесты для модели PaymentTerms."""

    def test_payment_terms_creation(self):
        """Создание условий оплаты."""
        terms = PaymentTerms(payment_type="предоплата")
        assert terms.payment_type == "предоплата"
        assert terms.currency == "RUB"
        assert terms.prepayment_percent is None

    def test_payment_terms_invalid_type(self):
        """Тест валидации при недопустимом типе оплаты."""
        with pytest.raises(ValidationError):
            PaymentTerms(payment_type="недопустимый")

    def test_payment_terms_prepayment_bounds(self):
        """Тест границ процента предоплаты."""
        # Допустимые значения
        PaymentTerms(payment_type="частичная предоплата", prepayment_percent=0.0)
        PaymentTerms(payment_type="частичная предоплата", prepayment_percent=100.0)
        PaymentTerms(payment_type="частичная предоплата", prepayment_percent=50.0)

        # Недопустимые значения
        with pytest.raises(ValidationError):
            PaymentTerms(payment_type="частичная предоплата", prepayment_percent=-1.0)
        with pytest.raises(ValidationError):
            PaymentTerms(payment_type="частичная предоплата", prepayment_percent=101.0)


class TestDeliveryTermsModel:
    """Тесты для модели DeliveryTerms."""

    def test_delivery_terms_creation(self):
        """Создание условий поставки."""
        terms = DeliveryTerms(delivery_type="доставка")
        assert terms.delivery_type == "доставка"
        assert terms.delivery_period_days is None

    def test_delivery_terms_invalid_type(self):
        """Тест валидации при недопустимом типе доставки."""
        with pytest.raises(ValidationError):
            DeliveryTerms(delivery_type="недопустимый")


class TestCommercialProposalModel:
    """Тесты для модели CommercialProposal."""

    def test_commercial_proposal_creation(self):
        """Создание коммерческого предложения."""
        supplier = SupplierInfo(name="ООО Поставщик")
        products = [
            ProductSpecification(
                product_code="PROD001",
                product_name="Товар 1",
                quantity=5,
                unit="шт",
                unit_price=100.0,
                total_amount=500.0,
                availability_status="в наличии",
            )
        ]
        payment_terms = PaymentTerms(payment_type="постоплата")
        delivery_terms = DeliveryTerms(delivery_type="доставка")

        proposal = CommercialProposal(
            supplier=supplier,
            products=products,
            payment_terms=payment_terms,
            delivery_terms=delivery_terms,
            total_amount=500.0,
        )
        assert proposal.supplier.name == "ООО Поставщик"
        assert len(proposal.products) == 1
        assert proposal.total_amount == 500.0
        assert isinstance(proposal.created_at, datetime)

    def test_commercial_proposal_empty_products(self):
        """Тест создания предложения с пустым списком продуктов."""
        supplier = SupplierInfo(name="Поставщик")
        payment_terms = PaymentTerms(payment_type="предоплата")
        delivery_terms = DeliveryTerms(delivery_type="самовывоз")

        proposal = CommercialProposal(
            supplier=supplier,
            products=[],
            payment_terms=payment_terms,
            delivery_terms=delivery_terms,
            total_amount=0.0,
        )
        assert len(proposal.products) == 0

    def test_commercial_proposal_negative_total(self):
        """Тест валидации при отрицательной общей сумме."""
        supplier = SupplierInfo(name="Поставщик")
        products = [
            ProductSpecification(
                product_code="PROD001",
                product_name="Товар",
                quantity=1,
                unit="шт",
                unit_price=100.0,
                total_amount=100.0,
                availability_status="в наличии",
            )
        ]
        payment_terms = PaymentTerms(payment_type="предоплата")
        delivery_terms = DeliveryTerms(delivery_type="самовывоз")

        with pytest.raises(ValidationError):
            CommercialProposal(
                supplier=supplier,
                products=products,
                payment_terms=payment_terms,
                delivery_terms=delivery_terms,
                total_amount=-100.0,
            )


class TestSupplierDocumentModel:
    """Тесты для модели SupplierDocument."""

    def test_supplier_document_creation(self):
        """Создание документа поставщика."""
        supplier = SupplierInfo(name="ООО Поставщик")
        document = SupplierDocument(
            document_type="коммерческое предложение", supplier=supplier
        )
        assert document.document_type == "коммерческое предложение"
        assert document.supplier.name == "ООО Поставщик"
        assert document.document_id is None

    def test_supplier_document_invalid_type(self):
        """Тест валидации при недопустимом типе документа."""
        supplier = SupplierInfo(name="Поставщик")
        with pytest.raises(ValidationError):
            SupplierDocument(document_type="недопустимый", supplier=supplier)


class TestSchemaSerialization:
    """Тесты для проверки сериализации/десериализации схем."""

    def test_complex_nested_serialization(self):
        """Тест сериализации сложной вложенной структуры."""
        # Создаем полное коммерческое предложение
        supplier = SupplierInfo(
            name="ООО Тест Поставщик",
            inn="1234567890",
            contact_person="Иван Иванов",
            email="test@supplier.com",
            rating=4.8,
        )

        products = [
            ProductSpecification(
                product_code="PROD001",
                product_name="Тестовый товар 1",
                quantity=10,
                unit="шт",
                unit_price=150.0,
                total_amount=1500.0,
                availability_status="в наличии",
                category="Электроника",
                brand="ТестБренд",
            ),
            ProductSpecification(
                product_code="PROD002",
                product_name="Тестовый товар 2",
                quantity=5,
                unit="шт",
                unit_price=200.0,
                total_amount=1000.0,
                availability_status="под заказ",
            ),
        ]

        payment_terms = PaymentTerms(
            payment_type="частичная предоплата",
            prepayment_percent=30.0,
            payment_period_days=30,
            currency="RUB",
        )

        delivery_terms = DeliveryTerms(
            delivery_type="доставка",
            delivery_period_days=7,
            delivery_cost=500.0,
            delivery_address="Москва, ул. Тестовая, д. 1",
            min_order_amount=1000.0,
        )

        proposal = CommercialProposal(
            proposal_id="PROP-2024-001",
            supplier=supplier,
            products=products,
            payment_terms=payment_terms,
            delivery_terms=delivery_terms,
            total_amount=2500.0,
            notes="Тестовое коммерческое предложение",
        )

        # Сериализация
        json_str = proposal.model_dump_json()
        assert "PROP-2024-001" in json_str
        assert "ООО Тест Поставщик" in json_str
        assert "2500.0" in json_str

        # Десериализация
        parsed_proposal = CommercialProposal.model_validate_json(json_str)
        assert parsed_proposal.proposal_id == "PROP-2024-001"
        assert parsed_proposal.supplier.name == "ООО Тест Поставщик"
        assert len(parsed_proposal.products) == 2
        assert parsed_proposal.total_amount == 2500.0

    def test_response_schema_validation(self):
        """Тест валидации схем ответов API."""
        # Тест UploadResponse с различными типами результатов
        results = [
            CheckResult(
                section="Технические требования",
                match="да",
                comments="Все требования выполнены",
                confidence=0.95,
                check_type="общий",
            ),
            CheckResult(
                section="Проверка цен",
                match="нет",
                comments="Цена выше рыночной на 25%",
                confidence=0.8,
                price_check="завышена",
                expected_price=1000.0,
                actual_price=1250.0,
                price_deviation_percent=25.0,
                check_type="ценовой",
            ),
        ]

        upload_response = UploadResponse(
            filename="test_document.pdf",
            report=results,
            task_id=12345,
            pdf_path="/reports/test_document_report.pdf",
        )

        # Проверяем корректность структуры
        data = upload_response.model_dump()
        assert data["filename"] == "test_document.pdf"
        assert len(data["report"]) == 2
        assert data["report"][0]["section"] == "Технические требования"
        assert data["report"][1]["price_check"] == "завышена"
        assert data["task_id"] == 12345


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
