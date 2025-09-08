"""Тесты для модуля checker."""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from checker import check_commercial_proposal, check_document, check_supplier_document
from inventory_checker import InventoryChecker
from price_checker import PriceChecker
from src.models import (
    CheckResult,
    CommercialProposal,
    DeliveryTerms,
    PaymentTerms,
    ProductSpecification,
    SupplierDocument,
    SupplierInfo,
)


def test_check_document_basic() -> None:
    doc = """
Техническое задание
Поставка кабеля — 1000 метров. Срок поставки — 30 дней. Приёмка по ГОСТ.

Форма договора
Оплата в рублях. Ответственность сторон указана. Есть пункт расторжения.
"""
    result = check_document(doc)
    assert isinstance(result, list)
    assert all("match" in item and "section" in item for item in result)


def test_commercial_proposal_check():
    """Тест проверки коммерческого предложения."""
    # Создаем тестовые данные
    supplier = SupplierInfo(
        name="ООО Тест Поставщик",
        inn="1234567890",
        kpp="123456789",
        contact_person="Иван Иванов",
        phone="+7-123-456-78-90",
        email="test@supplier.com",
        rating=4.5,
    )

    products = [
        ProductSpecification(
            product_code="CABLE_001",
            product_name="Кабель витая пара",
            quantity=100,
            unit="м",
            unit_price=50.0,
            total_amount=5000.0,
            availability_status="в наличии",
            specifications={"категория": "5e", "экранирование": "UTP"},
        ),
        ProductSpecification(
            product_code="SWITCH_001",
            product_name="Коммутатор 24 порта",
            quantity=2,
            unit="шт",
            unit_price=15000.0,
            total_amount=30000.0,
            availability_status="в наличии",
            specifications={"порты": "24", "скорость": "1Gbps"},
        ),
    ]

    payment_terms = PaymentTerms(
        payment_type="постоплата", payment_period_days=30, prepayment_percent=0
    )

    delivery_terms = DeliveryTerms(
        delivery_type="доставка",
        delivery_period_days=14,
        delivery_cost=0.0,
        delivery_address="Москва, ул. Тестовая, 1",
    )

    proposal = CommercialProposal(
        proposal_id="TEST_001",
        supplier=supplier,
        products=products,
        payment_terms=payment_terms,
        delivery_terms=delivery_terms,
        total_amount=35000.0,
        valid_until=datetime.now() + timedelta(days=30),
        created_at=datetime.now(),
    )

    # Мокаем проверщики
    mock_price_checker = Mock(spec=PriceChecker)
    mock_inventory_checker = Mock(spec=InventoryChecker)

    # Настраиваем моки для проверки цен
    mock_price_result = Mock()
    mock_price_result.expected_price = 45.0
    mock_price_result.actual_price = 50.0
    mock_price_result.match = "да"
    mock_price_result.comments = "Цена в пределах нормы"

    mock_price_checker.check_price.return_value = mock_price_result

    mock_comparison = Mock()
    mock_comparison.price_difference = 5.0
    mock_comparison.price_difference_percent = 11.1
    mock_price_checker.create_price_comparison.return_value = mock_comparison

    # Настраиваем моки для проверки наличия
    mock_availability_result = Mock()
    mock_availability_result.availability_check = "достаточно"
    mock_availability_result.actual_quantity = 150
    mock_inventory_checker.check_availability.return_value = mock_availability_result

    # Выполняем проверку
    analysis = check_commercial_proposal(
        proposal,
        price_checker=mock_price_checker,
        inventory_checker=mock_inventory_checker,
        tolerance_percent=10.0,
    )

    # Проверяем результат
    assert analysis.proposal_id == "TEST_001"
    assert analysis.supplier_name == "ООО Тест Поставщик"
    assert analysis.overall_score > 0
    assert analysis.overall_recommendation in [
        "принять",
        "требует согласования",
        "требует доработки",
        "отклонить",
    ]
    assert analysis.price_competitiveness in [
        "конкурентоспособные",
        "средние",
        "завышенные",
        "заниженные",
    ]
    assert 1.0 <= analysis.payment_terms_rating <= 5.0
    assert 1.0 <= analysis.delivery_terms_rating <= 5.0
    assert 1.0 <= analysis.supplier_reliability_score <= 5.0
    assert 1.0 <= analysis.product_availability_score <= 5.0
    assert analysis.risk_level in ["низкий", "средний", "высокий", "критический"]
    assert isinstance(analysis.supplier_strengths, list)
    assert isinstance(analysis.supplier_weaknesses, list)
    assert isinstance(analysis.identified_risks, list)
    assert isinstance(analysis.opportunities, list)
    assert isinstance(analysis.action_items, list)
    assert isinstance(analysis.negotiation_points, list)


def test_commercial_proposal_check_without_checkers():
    """Тест проверки коммерческого предложения без проверщиков цен и наличия."""
    supplier = SupplierInfo(name="ООО Простой Поставщик", inn="9876543210")

    products = [
        ProductSpecification(
            product_code="TEST_001",
            product_name="Тестовый товар",
            quantity=1,
            unit="шт",
            unit_price=1000.0,
            total_amount=1000.0,
            availability_status="в наличии",
        )
    ]

    payment_terms = PaymentTerms(payment_type="предоплата")
    delivery_terms = DeliveryTerms(delivery_type="доставка", delivery_period_days=7)

    proposal = CommercialProposal(
        proposal_id="SIMPLE_001",
        supplier=supplier,
        products=products,
        payment_terms=payment_terms,
        delivery_terms=delivery_terms,
        total_amount=1000.0,
    )

    # Проверяем без дополнительных проверщиков
    analysis = check_commercial_proposal(proposal)

    assert analysis.proposal_id == "SIMPLE_001"
    assert analysis.supplier_name == "ООО Простой Поставщик"
    assert analysis.overall_score > 0
    assert analysis.price_comparisons == []
    assert analysis.missing_products == []


def test_supplier_document_check():
    """Тест проверки документа поставщика."""
    supplier = SupplierInfo(
        name="ООО Документ Поставщик",
        inn="1111222233",
        kpp="111122223",
        contact_person="Петр Петров",
        phone="+7-987-654-32-10",
        email="doc@supplier.com",
    )

    document = SupplierDocument(
        document_id="DOC_001",
        document_type="коммерческое предложение",
        supplier=supplier,
        filename="commercial_proposal.pdf",
        upload_date=datetime.now(),
        status="новый",
        content_summary="Предложение на поставку кабеля по цене 50 руб/м в количестве 1000 м со сроком поставки 14 дней",
    )

    results = check_supplier_document(document)

    # Проверяем результаты
    assert isinstance(results, list)
    assert len(results) > 0

    # Проверяем, что все результаты имеют правильную структуру
    for result in results:
        assert isinstance(result, CheckResult)
        assert result.section is not None
        assert result.match in ["да", "нет", "частично"]
        assert result.check_type is not None

    # Проверяем наличие основных проверок
    sections = [result.section for result in results]
    assert "Тип документа" in sections
    assert "Информация о поставщике" in sections
    assert "Актуальность документа" in sections
    assert "Статус документа" in sections


def test_supplier_document_check_with_text():
    """Тест проверки документа поставщика с анализом текста."""
    supplier = SupplierInfo(name="ООО Текст Поставщик", inn="2222333344")

    document = SupplierDocument(
        document_id="DOC_TEXT_001",
        document_type="договор",
        supplier=supplier,
        filename="contract.pdf",
        upload_date=datetime.now() - timedelta(days=5),
        status="одобрен",
    )

    doc_text = """
Договор поставки
Поставщик обязуется поставить товар в срок до 30 дней.
Оплата производится в течение 14 дней после поставки.
Качество товара должно соответствовать ГОСТ.
"""

    with patch("checker.check_document") as mock_check_document:
        # Мокаем результат анализа текста
        mock_check_document.return_value = [
            {
                "section": "Договор поставки",
                "match": "да",
                "comments": "Соответствует требованиям",
            },
            {
                "section": "Условия оплаты",
                "match": "частично",
                "comments": "Требует уточнения",
            },
        ]

        results = check_supplier_document(document, doc_text)

    # Проверяем, что анализ текста был вызван
    mock_check_document.assert_called_once_with(doc_text)

    # Проверяем результаты
    assert len(results) > 4  # Базовые проверки + анализ содержания

    # Проверяем наличие результатов анализа содержания
    content_results = [
        r
        for r in results
        if r.check_type == "общий" and "Договор поставки" in r.section
    ]
    assert len(content_results) >= 1


def test_supplier_document_check_missing_info():
    """Тест проверки документа поставщика с неполной информацией."""
    supplier = SupplierInfo(
        name="ООО Неполный Поставщик"
        # Отсутствуют ИНН, контакты и другие данные
    )

    document = SupplierDocument(
        document_id="DOC_INCOMPLETE_001",
        document_type="сертификат",  # Используем валидный тип
        supplier=supplier,
        filename="incomplete_doc.pdf",
        upload_date=datetime.now() - timedelta(days=45),  # Старый документ
        status="отклонен",
    )

    results = check_supplier_document(document)

    # Проверяем, что найдены проблемы
    supplier_info_result = next(
        (r for r in results if r.section == "Информация о поставщике"), None
    )
    assert supplier_info_result is not None
    assert supplier_info_result.match == "нет"

    # Проверяем проблему с типом документа
    doc_type_result = next((r for r in results if r.section == "Тип документа"), None)
    assert doc_type_result is not None
    assert doc_type_result.match == "частично"

    # Проверяем проблему с актуальностью
    actuality_result = next(
        (r for r in results if r.section == "Актуальность документа"), None
    )
    assert actuality_result is not None
    assert actuality_result.match == "частично"

    # Проверяем статус
    status_result = next((r for r in results if r.section == "Статус документа"), None)
    assert status_result is not None
    assert status_result.match == "нет"


def test_commercial_proposal_check_high_risk():
    """Тест проверки коммерческого предложения с высоким риском."""
    supplier = SupplierInfo(
        name="ООО Рискованный Поставщик",
        # Отсутствует ИНН - это риск
        rating=2.0,  # Низкий рейтинг
    )

    products = [
        ProductSpecification(
            product_code="RISK_001",
            product_name="Рискованный товар",
            quantity=1,
            unit="шт",
            unit_price=10000.0,
            total_amount=10000.0,
            availability_status="под заказ",
        )
    ]

    payment_terms = PaymentTerms(
        payment_type="предоплата",
        prepayment_percent=100,  # 100% предоплата - риск
    )

    delivery_terms = DeliveryTerms(
        delivery_type="доставка", delivery_period_days=60
    )  # Долгая поставка

    proposal = CommercialProposal(
        proposal_id="RISK_001",
        supplier=supplier,
        products=products,
        payment_terms=payment_terms,
        delivery_terms=delivery_terms,
        total_amount=10000.0,
        valid_until=datetime.now() - timedelta(days=1),  # Просроченное предложение
    )

    analysis = check_commercial_proposal(proposal)

    # Проверяем, что выявлены риски
    assert analysis.risk_level in ["высокий", "критический"]
    assert len(analysis.identified_risks) > 0
    assert analysis.overall_recommendation in ["требует доработки", "отклонить"]

    # Проверяем конкретные риски
    risk_texts = " ".join(analysis.identified_risks)
    assert (
        "ИНН" in risk_texts or "предоплата" in risk_texts or "просрочено" in risk_texts
    )
