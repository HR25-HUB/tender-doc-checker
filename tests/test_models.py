"""Тесты для Pydantic моделей."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from src.models import (
    BitrixTaskRequest,
    CheckResult,
    CommercialProposal,
    CommercialProposalAnalysis,
    DeliveryTerms,
    DocumentReport,
    EmailRequest,
    PaymentTerms,
    PriceComparison,
    ProductSpecification,
    SupplierDocument,
    SupplierInfo,
)


class TestCheckResult:
    """Тесты для модели CheckResult."""

    def test_valid_check_result(self):
        """Тест создания валидного результата проверки."""
        result = CheckResult(
            section="Техническое задание",
            match="да",
            comments="Все требования выполнены",
            confidence=0.95,
        )

        assert result.section == "Техническое задание"
        assert result.match == "да"
        assert result.comments == "Все требования выполнены"
        assert result.confidence == 0.95
        assert result.check_type == "общий"  # Значение по умолчанию

    def test_minimal_check_result(self):
        """Тест создания минимального результата проверки."""
        result = CheckResult(section="Общие требования", match="нет")
        assert result.section == "Общие требования"
        assert result.match == "нет"
        assert result.comments == ""
        assert result.confidence is None
        assert result.check_type == "общий"

    def test_invalid_match_value(self):
        """Тест с невалидным значением match."""
        with pytest.raises(ValidationError):
            CheckResult(
                section="Техническое задание",
                match="возможно",  # Невалидное значение
                comments="Комментарий",
            )

    def test_confidence_bounds(self):
        """Тест границ значения confidence."""
        # Валидные значения
        CheckResult(section="test", match="да", confidence=0.0)
        CheckResult(section="test", match="да", confidence=1.0)

        # Невалидные значения
        with pytest.raises(ValidationError):
            CheckResult(section="test", match="да", confidence=-0.1)

        with pytest.raises(ValidationError):
            CheckResult(section="test", match="да", confidence=1.1)

    def test_product_price_check(self):
        """Тест товарной проверки цены."""
        result = CheckResult(
            section="Проверка цены товара",
            match="частично",
            check_type="ценовой",
            price_check="завышена",
            product_code="ABC123",
            expected_price=1000.0,
            actual_price=1200.0,
            price_deviation_percent=20.0,
            supplier_name="ООО Поставщик",
            comments="Цена завышена на 20%",
        )
        assert result.check_type == "ценовой"
        assert result.price_check == "завышена"
        assert result.product_code == "ABC123"
        assert result.expected_price == 1000.0
        assert result.actual_price == 1200.0
        assert result.price_deviation_percent == 20.0
        assert result.supplier_name == "ООО Поставщик"

    def test_product_availability_check(self):
        """Тест проверки наличия товара."""
        result = CheckResult(
            section="Проверка наличия",
            match="да",
            check_type="складской",
            availability_check="в наличии",
            product_code="XYZ789",
            supplier_name="ООО Склад",
        )
        assert result.check_type == "складской"
        assert result.availability_check == "в наличии"
        assert result.product_code == "XYZ789"
        assert result.supplier_name == "ООО Склад"

    def test_product_quantity_check(self):
        """Тест проверки количества товара."""
        result = CheckResult(
            section="Проверка количества",
            match="нет",
            check_type="товарный",
            quantity_check="недостаточно",
            product_code="DEF456",
            expected_quantity=100,
            actual_quantity=80,
            comments="Недостаток 20 единиц",
        )
        assert result.check_type == "товарный"
        assert result.quantity_check == "недостаточно"
        assert result.expected_quantity == 100
        assert result.actual_quantity == 80

    def test_comprehensive_product_check(self):
        """Тест комплексной товарной проверки."""
        result = CheckResult(
            section="Комплексная проверка товара",
            match="частично",
            check_type="товарный",
            price_check="соответствует",
            availability_check="под заказ",
            quantity_check="достаточно",
            product_code="COMP001",
            expected_price=500.0,
            actual_price=500.0,
            price_deviation_percent=0.0,
            expected_quantity=50,
            actual_quantity=50,
            supplier_name="ООО Комплексный поставщик",
            confidence=0.85,
            comments="Цена и количество соответствуют, но товар под заказ",
        )
        assert result.check_type == "товарный"
        assert result.price_check == "соответствует"
        assert result.availability_check == "под заказ"
        assert result.quantity_check == "достаточно"
        assert result.price_deviation_percent == 0.0

    def test_invalid_negative_prices(self):
        """Тест валидации отрицательных цен."""
        with pytest.raises(ValidationError):
            CheckResult(
                section="Тест",
                match="да",
                expected_price=-100.0,  # Отрицательная цена
            )

        with pytest.raises(ValidationError):
            CheckResult(
                section="Тест",
                match="да",
                actual_price=-50.0,  # Отрицательная цена
            )

    def test_invalid_negative_quantities(self):
        """Тест валидации отрицательных количеств."""
        with pytest.raises(ValidationError):
            CheckResult(
                section="Тест",
                match="да",
                expected_quantity=-10,  # Отрицательное количество
            )

        with pytest.raises(ValidationError):
            CheckResult(
                section="Тест",
                match="да",
                actual_quantity=-5,  # Отрицательное количество
            )


class TestDocumentReport:
    """Тесты для модели DocumentReport."""

    def test_valid_document_report(self):
        """Тест создания валидного отчета."""
        results = [
            CheckResult(section="Раздел 1", match="да", comments="OK"),
            CheckResult(section="Раздел 2", match="нет", comments="Проблема"),
        ]

        report = DocumentReport(
            filename="test.pdf",
            results=results,
            overall_status="частично соответствует",
        )

        assert report.filename == "test.pdf"
        assert len(report.results) == 2
        assert report.overall_status == "частично соответствует"
        assert isinstance(report.checked_at, datetime)


class TestBitrixTaskRequest:
    """Тесты для модели BitrixTaskRequest."""

    def test_valid_task_request(self):
        """Тест создания валидного запроса задачи."""
        request = BitrixTaskRequest(
            title="Проверка документа",
            description="Описание задачи",
            responsible_id=123,
        )

        assert request.title == "Проверка документа"
        assert request.description == "Описание задачи"
        assert request.responsible_id == 123
        assert request.deadline is None


class TestEmailRequest:
    """Тесты для модели EmailRequest."""

    def test_valid_email_request(self):
        """Тест создания валидного email запроса."""
        request = EmailRequest(
            recipient="test@example.com",
            subject="Тема письма",
            body="Текст письма",
            pdf_path="/path/to/report.pdf",
        )

        assert request.recipient == "test@example.com"
        assert request.subject == "Тема письма"
        assert request.body == "Текст письма"
        assert request.pdf_path == "/path/to/report.pdf"


class TestProductSpecification:
    """Тесты для модели ProductSpecification."""

    def test_valid_product_specification(self):
        """Тест создания валидной спецификации товара."""
        spec = ProductSpecification(
            product_code="DL-5520-001",
            product_name="Ноутбук Dell Latitude 5520",
            quantity=10,
            unit="шт",
            unit_price=75000.00,
            total_amount=750000.00,
            availability_status="в наличии",
            category="Компьютеры",
            brand="Dell",
            description="Ноутбук для офисной работы",
        )

        assert spec.product_code == "DL-5520-001"
        assert spec.product_name == "Ноутбук Dell Latitude 5520"
        assert spec.quantity == 10
        assert spec.unit == "шт"
        assert spec.unit_price == 75000.00
        assert spec.total_amount == 750000.00
        assert spec.availability_status == "в наличии"
        assert spec.category == "Компьютеры"
        assert spec.brand == "Dell"

    def test_negative_quantity(self):
        """Тест с отрицательным количеством."""
        with pytest.raises(ValidationError):
            ProductSpecification(
                product_code="TEST-001",
                product_name="Товар",
                quantity=0,  # Должно быть >= 1
                unit="шт",
                unit_price=100.00,
                total_amount=100.00,
                availability_status="в наличии",
            )

    def test_negative_price(self):
        """Тест с отрицательной ценой."""
        with pytest.raises(ValidationError):
            ProductSpecification(
                product_code="TEST-001",
                product_name="Товар",
                quantity=1,
                unit="шт",
                unit_price=-100.00,
                total_amount=100.00,
                availability_status="в наличии",
            )


class TestSupplierInfo:
    """Тесты для модели SupplierInfo."""

    def test_valid_supplier_info(self):
        """Тест создания валидной информации о поставщике."""
        supplier = SupplierInfo(
            name="ООО 'Техносфера'",
            inn="7701234567",
            kpp="770101001",
            contact_person="Иванов Иван Иванович",
            phone="+7 (495) 123-45-67",
            email="info@technosphere.ru",
            address="г. Москва, ул. Тверская, д. 1",
            rating=4.5,
        )

        assert supplier.name == "ООО 'Техносфера'"
        assert supplier.inn == "7701234567"
        assert supplier.kpp == "770101001"
        assert supplier.contact_person == "Иванов Иван Иванович"
        assert supplier.phone == "+7 (495) 123-45-67"
        assert supplier.email == "info@technosphere.ru"
        assert supplier.address == "г. Москва, ул. Тверская, д. 1"
        assert supplier.rating == 4.5

    def test_minimal_supplier_info(self):
        """Тест создания минимальной информации о поставщике."""
        supplier = SupplierInfo(name="ООО 'Тест'")
        assert supplier.name == "ООО 'Тест'"
        assert supplier.inn is None


class TestPaymentTerms:
    """Тесты для модели PaymentTerms."""

    def test_valid_payment_terms(self):
        """Тест создания валидных условий оплаты."""
        terms = PaymentTerms(
            payment_type="частичная предоплата",
            payment_period_days=14,
            prepayment_percent=30,
            payment_method="Безналичный расчет",
            currency="RUB",
        )

        assert terms.payment_type == "частичная предоплата"
        assert terms.payment_period_days == 14
        assert terms.prepayment_percent == 30
        assert terms.payment_method == "Безналичный расчет"
        assert terms.currency == "RUB"

    def test_invalid_prepayment_percent(self):
        """Тест с невалидным процентом предоплаты."""
        with pytest.raises(ValidationError):
            PaymentTerms(
                payment_type="предоплата",
                prepayment_percent=150,  # Больше 100%
            )

    def test_negative_payment_period(self):
        """Тест с отрицательным периодом оплаты."""
        with pytest.raises(ValidationError):
            PaymentTerms(
                payment_type="постоплата",
                payment_period_days=-5,
            )


class TestDeliveryTerms:
    """Тесты для модели DeliveryTerms."""

    def test_valid_delivery_terms(self):
        """Тест создания валидных условий поставки."""
        terms = DeliveryTerms(
            delivery_type="доставка",
            delivery_period_days=7,
            delivery_cost=5000.00,
            delivery_address="г. Москва, ул. Складская, д. 10",
            min_order_amount=10000.00,
        )

        assert terms.delivery_type == "доставка"
        assert terms.delivery_period_days == 7
        assert terms.delivery_cost == 5000.00
        assert terms.delivery_address == "г. Москва, ул. Складская, д. 10"
        assert terms.min_order_amount == 10000.00

    def test_negative_delivery_period(self):
        """Тест с отрицательным периодом поставки."""
        with pytest.raises(ValidationError):
            DeliveryTerms(
                delivery_type="доставка",
                delivery_period_days=-1,
            )

    def test_negative_delivery_cost(self):
        """Тест с отрицательной стоимостью доставки."""
        with pytest.raises(ValidationError):
            DeliveryTerms(
                delivery_type="доставка",
                delivery_cost=-1000.00,
            )


class TestCommercialProposal:
    """Тесты для модели CommercialProposal."""

    def test_valid_commercial_proposal(self):
        """Тест создания валидного коммерческого предложения."""
        supplier = SupplierInfo(
            name="ООО 'Техносфера'",
            inn="7701234567",
        )

        products = [
            ProductSpecification(
                product_code="NB-001",
                product_name="Ноутбук",
                quantity=5,
                unit="шт",
                unit_price=50000.00,
                total_amount=250000.00,
                availability_status="в наличии",
            ),
        ]

        payment_terms = PaymentTerms(
            payment_type="предоплата",
        )

        delivery_terms = DeliveryTerms(
            delivery_type="доставка",
        )

        proposal = CommercialProposal(
            proposal_id="КП-2024-001",
            supplier=supplier,
            products=products,
            payment_terms=payment_terms,
            delivery_terms=delivery_terms,
            total_amount=250000.00,
            valid_until=datetime(2024, 12, 31),
        )

        assert proposal.proposal_id == "КП-2024-001"
        assert proposal.supplier.name == "ООО 'Техносфера'"
        assert len(proposal.products) == 1
        assert proposal.total_amount == 250000.00
        assert proposal.valid_until == datetime(2024, 12, 31)

    def test_negative_total_amount(self):
        """Тест с отрицательной общей суммой."""
        with pytest.raises(ValidationError):
            CommercialProposal(
                supplier=SupplierInfo(name="Тест"),
                products=[],
                payment_terms=PaymentTerms(payment_type="предоплата"),
                delivery_terms=DeliveryTerms(delivery_type="самовывоз"),
                total_amount=-1000.00,
            )


class TestSupplierDocument:
    """Тесты для модели SupplierDocument."""

    def test_valid_supplier_document(self):
        """Тест создания валидного документа поставщика."""
        supplier = SupplierInfo(name="ООО 'Техносфера'")

        doc = SupplierDocument(
            document_type="коммерческое предложение",
            supplier=supplier,
            filename="proposal_2024.pdf",
            content_summary="Предложение по поставке оборудования",
            status="новый",
        )

        assert doc.document_type == "коммерческое предложение"
        assert doc.supplier.name == "ООО 'Техносфера'"
        assert doc.filename == "proposal_2024.pdf"
        assert doc.content_summary == "Предложение по поставке оборудования"
        assert doc.status == "новый"
        assert isinstance(doc.upload_date, datetime)


class TestPriceComparison:
    """Тесты для модели PriceComparison."""

    def test_valid_price_comparison(self):
        """Тест создания валидного сравнения цен."""
        comparison = PriceComparison(
            product_code="ABC123",
            current_price=100.0,
            proposed_price=95.0,
            price_difference=-5.0,
            price_difference_percent=-5.0,
            recommendation="принять",
        )
        assert comparison.product_code == "ABC123"
        assert comparison.current_price == 100.0
        assert comparison.proposed_price == 95.0
        assert comparison.price_difference == -5.0
        assert comparison.price_difference_percent == -5.0
        assert comparison.recommendation == "принять"

    def test_invalid_negative_prices(self):
        """Тест валидации отрицательных цен."""
        with pytest.raises(ValidationError):
            PriceComparison(
                product_code="ABC123",
                current_price=-100.0,
                proposed_price=95.0,
                price_difference=-5.0,
                price_difference_percent=-5.0,
                recommendation="принять",
            )

    def test_invalid_recommendation(self):
        """Тест валидации неверной рекомендации."""
        with pytest.raises(ValidationError):
            PriceComparison(
                product_code="ABC123",
                current_price=100.0,
                proposed_price=95.0,
                price_difference=-5.0,
                price_difference_percent=-5.0,
                recommendation="неизвестно",
            )

    def test_negative_current_price(self):
        """Тест с отрицательной текущей ценой."""
        with pytest.raises(ValidationError):
            PriceComparison(
                product_code="TEST-001",
                current_price=-1000.00,
                proposed_price=900.00,
                price_difference=100.00,
                price_difference_percent=10.0,
                recommendation="принять",
            )

    def test_negative_proposed_price(self):
        """Тест с отрицательной предложенной ценой."""
        with pytest.raises(ValidationError):
            PriceComparison(
                product_code="TEST-001",
                current_price=1000.00,
                proposed_price=-900.00,
                price_difference=100.00,
                price_difference_percent=10.0,
                recommendation="принять",
            )


class TestCommercialProposalAnalysis:
    """Тесты для модели CommercialProposalAnalysis."""

    def test_valid_commercial_proposal_analysis(self):
        """Тест создания валидного анализа коммерческого предложения."""
        analysis = CommercialProposalAnalysis(
            proposal_id="PROP-001",
            supplier_name="ООО Поставщик",
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
        assert analysis.proposal_id == "PROP-001"
        assert analysis.supplier_name == "ООО Поставщик"
        assert analysis.overall_score == 8.5
        assert analysis.overall_recommendation == "принять"
        assert analysis.price_competitiveness == "конкурентоспособные"
        assert analysis.payment_terms_rating == 4.0
        assert analysis.delivery_terms_rating == 4.5
        assert analysis.supplier_reliability_score == 4.2
        assert analysis.product_availability_score == 4.8
        assert analysis.risk_level == "низкий"
        assert analysis.confidence_level == 0.85

    def test_analysis_with_price_comparisons(self):
        """Тест анализа с детальными сравнениями цен."""
        price_comparison = PriceComparison(
            product_code="ABC123",
            current_price=100.0,
            proposed_price=95.0,
            price_difference=-5.0,
            price_difference_percent=-5.0,
            recommendation="принять",
        )

        analysis = CommercialProposalAnalysis(
            supplier_name="ООО Поставщик",
            overall_score=7.5,
            overall_recommendation="принять",
            price_competitiveness="конкурентоспособные",
            payment_terms_rating=4.0,
            delivery_terms_rating=4.0,
            supplier_reliability_score=4.0,
            product_availability_score=4.0,
            risk_level="средний",
            confidence_level=0.8,
            price_comparisons=[price_comparison],
            cost_savings_potential=5000.0,
            cost_savings_percent=5.0,
        )

        assert len(analysis.price_comparisons) == 1
        assert analysis.price_comparisons[0].product_code == "ABC123"
        assert analysis.cost_savings_potential == 5000.0
        assert analysis.cost_savings_percent == 5.0

    def test_analysis_with_risks_and_opportunities(self):
        """Тест анализа с рисками и возможностями."""
        analysis = CommercialProposalAnalysis(
            supplier_name="ООО Поставщик",
            overall_score=6.0,
            overall_recommendation="требует согласования",
            price_competitiveness="завышенные",
            payment_terms_rating=3.0,
            delivery_terms_rating=3.5,
            supplier_reliability_score=3.8,
            product_availability_score=4.0,
            risk_level="высокий",
            confidence_level=0.7,
            identified_risks=["Высокие цены", "Длительные сроки поставки"],
            opportunities=["Возможность скидки при больших объемах"],
            supplier_strengths=["Качественная продукция", "Надежность"],
            supplier_weaknesses=["Высокие цены", "Медленная доставка"],
            missing_products=["Товар A", "Товар B"],
            alternative_products=["Аналог A", "Аналог B"],
        )

        assert len(analysis.identified_risks) == 2
        assert "Высокие цены" in analysis.identified_risks
        assert len(analysis.opportunities) == 1
        assert len(analysis.supplier_strengths) == 2
        assert len(analysis.supplier_weaknesses) == 2
        assert len(analysis.missing_products) == 2
        assert len(analysis.alternative_products) == 2

    def test_analysis_with_recommendations(self):
        """Тест анализа с рекомендациями."""
        from datetime import datetime, timedelta

        decision_deadline = datetime.now() + timedelta(days=7)

        analysis = CommercialProposalAnalysis(
            supplier_name="ООО Поставщик",
            overall_score=7.0,
            overall_recommendation="требует доработки",
            price_competitiveness="средние",
            payment_terms_rating=3.5,
            delivery_terms_rating=4.0,
            supplier_reliability_score=4.0,
            product_availability_score=3.5,
            risk_level="средний",
            confidence_level=0.75,
            action_items=["Запросить скидку", "Уточнить сроки поставки"],
            negotiation_points=["Цена", "Условия оплаты", "Гарантии"],
            decision_deadline=decision_deadline,
            analyst_name="Иванов И.И.",
            analysis_notes="Требуется дополнительное согласование цен",
        )

        assert len(analysis.action_items) == 2
        assert "Запросить скидку" in analysis.action_items
        assert len(analysis.negotiation_points) == 3
        assert analysis.decision_deadline == decision_deadline
        assert analysis.analyst_name == "Иванов И.И."
        assert analysis.analysis_notes == "Требуется дополнительное согласование цен"

    def test_invalid_overall_score(self):
        """Тест валидации неверной общей оценки."""
        with pytest.raises(ValidationError):
            CommercialProposalAnalysis(
                supplier_name="ООО Поставщик",
                overall_score=15.0,  # Больше 10
                overall_recommendation="принять",
                price_competitiveness="конкурентоспособные",
                payment_terms_rating=4.0,
                delivery_terms_rating=4.0,
                supplier_reliability_score=4.0,
                product_availability_score=4.0,
                risk_level="низкий",
                confidence_level=0.8,
            )

    def test_invalid_confidence_level(self):
        """Тест валидации неверного уровня уверенности."""
        with pytest.raises(ValidationError):
            CommercialProposalAnalysis(
                supplier_name="ООО Поставщик",
                overall_score=8.0,
                overall_recommendation="принять",
                price_competitiveness="конкурентоспособные",
                payment_terms_rating=4.0,
                delivery_terms_rating=4.0,
                supplier_reliability_score=4.0,
                product_availability_score=4.0,
                risk_level="низкий",
                confidence_level=1.5,  # Больше 1
            )

    def test_invalid_recommendation(self):
        """Тест валидации неверной рекомендации."""
        with pytest.raises(ValidationError):
            CommercialProposalAnalysis(
                supplier_name="ООО Поставщик",
                overall_score=8.0,
                overall_recommendation="неизвестно",  # Неверное значение
                price_competitiveness="конкурентоспособные",
                payment_terms_rating=4.0,
                delivery_terms_rating=4.0,
                supplier_reliability_score=4.0,
                product_availability_score=4.0,
                risk_level="низкий",
                confidence_level=0.8,
            )

    def test_analysis_with_metrics(self):
        """Тест анализа с метриками."""
        analysis = CommercialProposalAnalysis(
            supplier_name="ООО Поставщик",
            overall_score=8.0,
            overall_recommendation="принять",
            price_competitiveness="конкурентоспособные",
            payment_terms_rating=4.0,
            delivery_terms_rating=4.0,
            supplier_reliability_score=4.0,
            product_availability_score=4.0,
            risk_level="низкий",
            confidence_level=0.9,
            analysis_duration_minutes=45,
            data_completeness_percent=95.5,
        )

        assert analysis.analysis_duration_minutes == 45
        assert analysis.data_completeness_percent == 95.5
