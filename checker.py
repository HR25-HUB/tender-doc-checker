import logging
from datetime import datetime
from typing import Optional

import yaml

from chunker import chunk_document
from inventory_checker import InventoryChecker
from llm_client import query_llm
from price_checker import PriceChecker
from src.models import (
    CheckResult,
    CommercialProposal,
    CommercialProposalAnalysis,
    ProductSpecification,
    SupplierDocument,
)

logger = logging.getLogger(__name__)


def load_standards(path="data/internal_standards.yaml"):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_prompt(chunk: dict, standards: dict) -> str:
    reqs = "\n".join(f"- {item}" for item in standards.get(chunk["title"], []))
    return f"""Ты юридический ассистент. Проанализируй следующий раздел документа:
Раздел: {chunk["title"]}
Текст: {chunk["content"]}

Сравни с внутренними требованиями компании:
{reqs}

Ответь в формате JSON:
{{
  "match": "да/нет/частично",
  "comments": "какие пункты не соответствуют"
}}
"""


def check_document(doc_text: str) -> list[dict[str, str]]:
    chunks = chunk_document(doc_text)
    standards = load_standards()
    results = []
    for ch in chunks:
        prompt = build_prompt(ch, standards)
        response = query_llm(prompt)
        results.append(
            {
                "section": ch["title"],
                "match": response.get("match"),
                "comments": response.get("comments", ""),
            }
        )
    return results


def check_commercial_proposal(
    proposal: CommercialProposal,
    price_checker: Optional[PriceChecker] = None,
    inventory_checker: Optional[InventoryChecker] = None,
    tolerance_percent: float = 10.0,
) -> CommercialProposalAnalysis:
    """
    Проверяет коммерческое предложение и создает детальный анализ.

    Args:
        proposal: Коммерческое предложение для анализа
        price_checker: Экземпляр проверщика цен (опционально)
        inventory_checker: Экземпляр проверщика наличия (опционально)
        tolerance_percent: Допустимое отклонение цен в процентах

    Returns:
        Анализ коммерческого предложения
    """
    logger.info(f"Начинаю анализ коммерческого предложения от {proposal.supplier.name}")

    analysis_start = datetime.now()

    # Инициализация анализа
    analysis = CommercialProposalAnalysis(
        proposal_id=proposal.proposal_id,
        supplier_name=proposal.supplier.name,
        overall_score=0.0,
        overall_recommendation="требует согласования",
        price_competitiveness="средние",
        payment_terms_rating=3.0,
        delivery_terms_rating=3.0,
        supplier_reliability_score=3.0,
        product_availability_score=3.0,
        risk_level="средний",
        confidence_level=0.8,
    )

    # === АНАЛИЗ ЦЕН ===
    price_comparisons = []
    total_cost_savings = 0.0
    price_issues = []

    if price_checker:
        for product in proposal.products:
            try:
                # Проверяем цену товара
                price_result = price_checker.check_price(
                    product.product_code, product.unit_price, tolerance_percent
                )

                if price_result.expected_price and price_result.actual_price:
                    # Создаем сравнение цен
                    comparison = price_checker.create_price_comparison(
                        product.product_code,
                        price_result.expected_price,
                        price_result.actual_price,
                    )
                    price_comparisons.append(comparison)

                    # Рассчитываем потенциальную экономию
                    if comparison.price_difference < 0:  # Цена ниже базовой
                        savings = abs(comparison.price_difference) * product.quantity
                        total_cost_savings += savings

                if price_result.match == "нет":
                    price_issues.append(
                        f"Товар {product.product_code}: {price_result.comments}"
                    )

            except Exception as e:
                logger.warning(
                    f"Ошибка при проверке цены товара {product.product_code}: {e}"
                )
                price_issues.append(
                    f"Товар {product.product_code}: ошибка проверки цены"
                )

    analysis.price_comparisons = price_comparisons
    analysis.cost_savings_potential = (
        total_cost_savings if total_cost_savings > 0 else None
    )

    # Определяем конкурентоспособность цен
    if price_comparisons:
        avg_deviation = sum(
            comp.price_difference_percent for comp in price_comparisons
        ) / len(price_comparisons)
        if avg_deviation < -5:
            analysis.price_competitiveness = "конкурентоспособные"
        elif avg_deviation > 15:
            analysis.price_competitiveness = "завышенные"
        elif avg_deviation < -15:
            analysis.price_competitiveness = "заниженные"
        else:
            analysis.price_competitiveness = "средние"

    # === АНАЛИЗ НАЛИЧИЯ ТОВАРОВ ===
    availability_issues = []
    missing_products = []

    if inventory_checker:
        for product in proposal.products:
            try:
                availability_result = inventory_checker.check_availability(
                    product.product_code, product.quantity
                )

                if availability_result.availability_check == "недостаточно":
                    availability_issues.append(
                        f"Товар {product.product_code}: недостаточно на складе "
                        f"(требуется {product.quantity}, доступно {availability_result.actual_quantity})"
                    )
                elif availability_result.availability_check == "нет в наличии":
                    missing_products.append(product.product_code)
                    availability_issues.append(
                        f"Товар {product.product_code}: отсутствует на складе"
                    )

            except Exception as e:
                logger.warning(
                    f"Ошибка при проверке наличия товара {product.product_code}: {e}"
                )
                availability_issues.append(
                    f"Товар {product.product_code}: ошибка проверки наличия"
                )

    analysis.missing_products = missing_products

    # Оценка доступности товаров
    if len(missing_products) == 0:
        analysis.product_availability_score = 5.0
    elif len(missing_products) < len(proposal.products) * 0.2:  # Менее 20% отсутствует
        analysis.product_availability_score = 4.0
    elif len(missing_products) < len(proposal.products) * 0.5:  # Менее 50% отсутствует
        analysis.product_availability_score = 3.0
    else:
        analysis.product_availability_score = 2.0

    # === АНАЛИЗ УСЛОВИЙ ОПЛАТЫ ===
    payment_rating = 3.0
    if proposal.payment_terms.payment_type == "постоплата":
        payment_rating += 1.0
    elif proposal.payment_terms.payment_type == "предоплата":
        payment_rating -= 0.5

    if proposal.payment_terms.payment_period_days:
        if proposal.payment_terms.payment_period_days <= 30:
            payment_rating += 0.5
        elif proposal.payment_terms.payment_period_days > 60:
            payment_rating -= 0.5

    analysis.payment_terms_rating = min(5.0, max(1.0, payment_rating))

    # === АНАЛИЗ УСЛОВИЙ ПОСТАВКИ ===
    delivery_rating = 3.0
    if proposal.delivery_terms.delivery_period_days:
        if proposal.delivery_terms.delivery_period_days <= 7:
            delivery_rating += 1.0
        elif proposal.delivery_terms.delivery_period_days <= 14:
            delivery_rating += 0.5
        elif proposal.delivery_terms.delivery_period_days > 30:
            delivery_rating -= 1.0

    if proposal.delivery_terms.delivery_cost:
        if proposal.delivery_terms.delivery_cost == 0:
            delivery_rating += 0.5
        elif (
            proposal.delivery_terms.delivery_cost > proposal.total_amount * 0.05
        ):  # Более 5% от суммы
            delivery_rating -= 0.5

    analysis.delivery_terms_rating = min(5.0, max(1.0, delivery_rating))

    # === АНАЛИЗ ПОСТАВЩИКА ===
    supplier_rating = 3.0
    supplier_strengths = []
    supplier_weaknesses = []

    if proposal.supplier.rating:
        supplier_rating = proposal.supplier.rating
        if proposal.supplier.rating >= 4.5:
            supplier_strengths.append("Высокий рейтинг поставщика")
        elif proposal.supplier.rating < 3.0:
            supplier_weaknesses.append("Низкий рейтинг поставщика")

    if proposal.supplier.inn and proposal.supplier.kpp:
        supplier_strengths.append("Полные реквизиты поставщика")
    else:
        supplier_weaknesses.append("Неполные реквизиты поставщика")

    if proposal.supplier.contact_person and proposal.supplier.phone:
        supplier_strengths.append("Указаны контактные данные")
    else:
        supplier_weaknesses.append("Отсутствуют контактные данные")

    analysis.supplier_reliability_score = supplier_rating
    analysis.supplier_strengths = supplier_strengths
    analysis.supplier_weaknesses = supplier_weaknesses

    # === ВЫЯВЛЕНИЕ РИСКОВ ===
    risks = []
    opportunities = []

    if price_issues:
        risks.extend(price_issues)

    if availability_issues:
        risks.extend(availability_issues)

    if proposal.valid_until and proposal.valid_until < datetime.now():
        risks.append("Предложение просрочено")

    if not proposal.supplier.inn:
        risks.append("Отсутствует ИНН поставщика")

    if (
        proposal.payment_terms.payment_type == "предоплата"
        and proposal.payment_terms.prepayment_percent == 100
    ):
        risks.append("Требуется 100% предоплата")

    if total_cost_savings > 0:
        opportunities.append(f"Потенциальная экономия: {total_cost_savings:.2f} руб.")

    if analysis.supplier_reliability_score >= 4.0:
        opportunities.append("Надежный поставщик")

    if analysis.delivery_terms_rating >= 4.0:
        opportunities.append("Выгодные условия поставки")

    analysis.identified_risks = risks
    analysis.opportunities = opportunities

    # === ОПРЕДЕЛЕНИЕ УРОВНЯ РИСКА ===
    risk_count = len(risks)
    if risk_count == 0:
        analysis.risk_level = "низкий"
    elif risk_count <= 2:
        analysis.risk_level = "средний"
    elif risk_count <= 4:
        analysis.risk_level = "высокий"
    else:
        analysis.risk_level = "критический"

    # === ОБЩАЯ ОЦЕНКА И РЕКОМЕНДАЦИЯ ===
    scores = [
        analysis.payment_terms_rating,
        analysis.delivery_terms_rating,
        analysis.supplier_reliability_score,
        analysis.product_availability_score,
    ]

    # Добавляем ценовую составляющую
    if analysis.price_competitiveness == "конкурентоспособные":
        scores.append(5.0)
    elif analysis.price_competitiveness == "средние":
        scores.append(3.0)
    elif analysis.price_competitiveness == "завышенные":
        scores.append(2.0)
    else:  # заниженные
        scores.append(4.0)

    analysis.overall_score = sum(scores) / len(scores) * 2  # Приводим к шкале 0-10

    # Определяем общую рекомендацию
    if analysis.overall_score >= 8.0 and analysis.risk_level in ["низкий", "средний"]:
        analysis.overall_recommendation = "принять"
    elif analysis.overall_score >= 6.0 and analysis.risk_level != "критический":
        analysis.overall_recommendation = "требует согласования"
    elif analysis.overall_score >= 4.0:
        analysis.overall_recommendation = "требует доработки"
    else:
        analysis.overall_recommendation = "отклонить"

    # === РЕКОМЕНДАЦИИ ===
    action_items = []
    negotiation_points = []

    if price_issues:
        action_items.append("Провести переговоры по ценам")
        negotiation_points.extend(
            [f"Пересмотр цены: {issue}" for issue in price_issues[:3]]
        )

    if availability_issues:
        action_items.append("Уточнить сроки поставки отсутствующих товаров")

    if analysis.payment_terms_rating < 3.0:
        negotiation_points.append("Улучшение условий оплаты")

    if analysis.delivery_terms_rating < 3.0:
        negotiation_points.append("Улучшение условий поставки")

    if not proposal.supplier.inn:
        action_items.append("Запросить полные реквизиты поставщика")

    analysis.action_items = action_items
    analysis.negotiation_points = negotiation_points

    # === ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ ===
    analysis_end = datetime.now()
    analysis.analysis_duration_minutes = int(
        (analysis_end - analysis_start).total_seconds() / 60
    )

    # Оценка полноты данных
    data_fields = [
        proposal.supplier.inn,
        proposal.supplier.contact_person,
        proposal.supplier.phone,
        proposal.valid_until,
        proposal.payment_terms.payment_period_days,
        proposal.delivery_terms.delivery_period_days,
    ]
    filled_fields = sum(1 for field in data_fields if field is not None)
    analysis.data_completeness_percent = (filled_fields / len(data_fields)) * 100

    logger.info(
        f"Анализ завершен. Общая оценка: {analysis.overall_score:.1f}, Рекомендация: {analysis.overall_recommendation}"
    )

    return analysis


def check_supplier_document(
    document: SupplierDocument, doc_text: Optional[str] = None
) -> list[CheckResult]:
    """
    Проверяет документ поставщика на соответствие требованиям.

    Args:
        document: Документ поставщика для проверки
        doc_text: Текст документа (опционально, для дополнительного анализа)

    Returns:
        Список результатов проверки
    """
    logger.info(
        f"Начинаю проверку документа {document.document_type} от {document.supplier.name}"
    )

    results = []

    # === БАЗОВЫЕ ПРОВЕРКИ ДОКУМЕНТА ===

    # Проверка типа документа
    if document.document_type in [
        "коммерческое предложение",
        "спецификация",
        "договор",
    ]:
        results.append(
            CheckResult(
                section="Тип документа",
                match="да",
                comments=f"Тип документа '{document.document_type}' корректен",
                check_type="общий",
            )
        )
    else:
        results.append(
            CheckResult(
                section="Тип документа",
                match="частично",
                comments=f"Тип документа '{document.document_type}' требует дополнительной проверки",
                check_type="общий",
            )
        )

    # Проверка информации о поставщике
    supplier_issues = []
    if not document.supplier.name:
        supplier_issues.append("отсутствует наименование поставщика")

    if not document.supplier.inn:
        supplier_issues.append("отсутствует ИНН поставщика")

    if not document.supplier.contact_person:
        supplier_issues.append("отсутствует контактное лицо")

    if not document.supplier.phone and not document.supplier.email:
        supplier_issues.append("отсутствуют контактные данные")

    if supplier_issues:
        results.append(
            CheckResult(
                section="Информация о поставщике",
                match="нет",
                comments=f"Проблемы с данными поставщика: {'; '.join(supplier_issues)}",
                check_type="общий",
                supplier_name=document.supplier.name,
            )
        )
    else:
        results.append(
            CheckResult(
                section="Информация о поставщике",
                match="да",
                comments="Информация о поставщике полная и корректная",
                check_type="общий",
                supplier_name=document.supplier.name,
            )
        )

    # Проверка даты загрузки
    if document.upload_date:
        days_old = (datetime.now() - document.upload_date).days
        if days_old > 30:
            results.append(
                CheckResult(
                    section="Актуальность документа",
                    match="частично",
                    comments=f"Документ загружен {days_old} дней назад, возможно требует обновления",
                    check_type="общий",
                )
            )
        else:
            results.append(
                CheckResult(
                    section="Актуальность документа",
                    match="да",
                    comments="Документ актуален",
                    check_type="общий",
                )
            )

    # Проверка статуса документа
    if document.status == "новый":
        results.append(
            CheckResult(
                section="Статус документа",
                match="частично",
                comments="Документ требует проверки",
                check_type="общий",
            )
        )
    elif document.status == "одобрен":
        results.append(
            CheckResult(
                section="Статус документа",
                match="да",
                comments="Документ одобрен",
                check_type="общий",
            )
        )
    elif document.status == "отклонен":
        results.append(
            CheckResult(
                section="Статус документа",
                match="нет",
                comments="Документ отклонен",
                check_type="общий",
            )
        )

    # === ДОПОЛНИТЕЛЬНЫЙ АНАЛИЗ ТЕКСТА ===
    if doc_text:
        try:
            # Используем существующую функцию проверки документа
            text_results = check_document(doc_text)

            # Преобразуем результаты в формат CheckResult
            for text_result in text_results:
                results.append(
                    CheckResult(
                        section=f"Содержание: {text_result['section']}",
                        match=text_result["match"],
                        comments=text_result["comments"],
                        check_type="общий",
                        supplier_name=document.supplier.name,
                    )
                )

        except Exception as e:
            logger.warning(f"Ошибка при анализе текста документа: {e}")
            results.append(
                CheckResult(
                    section="Анализ содержания",
                    match="нет",
                    comments=f"Ошибка при анализе содержания документа: {e}",
                    check_type="общий",
                )
            )

    # === СПЕЦИФИЧЕСКИЕ ПРОВЕРКИ ПО ТИПУ ДОКУМЕНТА ===

    if document.document_type == "коммерческое предложение":
        # Для коммерческих предложений проверяем наличие ключевых элементов
        if not document.content_summary:
            results.append(
                CheckResult(
                    section="Структура коммерческого предложения",
                    match="частично",
                    comments="Отсутствует краткое содержание предложения",
                    check_type="общий",
                )
            )
        else:
            # Проверяем ключевые слова в содержании
            key_elements = ["цена", "количество", "срок", "поставка"]
            missing_elements = []

            content_lower = document.content_summary.lower()
            for element in key_elements:
                if element not in content_lower:
                    missing_elements.append(element)

            if missing_elements:
                results.append(
                    CheckResult(
                        section="Структура коммерческого предложения",
                        match="частично",
                        comments=f"Возможно отсутствуют элементы: {', '.join(missing_elements)}",
                        check_type="общий",
                    )
                )
            else:
                results.append(
                    CheckResult(
                        section="Структура коммерческого предложения",
                        match="да",
                        comments="Коммерческое предложение содержит основные элементы",
                        check_type="общий",
                    )
                )

    elif document.document_type == "договор":
        # Для договоров проверяем обязательные реквизиты
        if not document.supplier.inn or not document.supplier.kpp:
            results.append(
                CheckResult(
                    section="Реквизиты для договора",
                    match="нет",
                    comments="Для заключения договора необходимы полные реквизиты поставщика (ИНН, КПП)",
                    check_type="общий",
                )
            )
        else:
            results.append(
                CheckResult(
                    section="Реквизиты для договора",
                    match="да",
                    comments="Реквизиты поставщика для договора в порядке",
                    check_type="общий",
                )
            )

    logger.info(
        f"Проверка документа завершена. Найдено {len(results)} результатов проверки"
    )

    return results


def check_product_specification(
    specifications: list[ProductSpecification],
    price_checker: Optional[PriceChecker] = None,
    inventory_checker: Optional[InventoryChecker] = None,
    tolerance_percent: float = 10.0,
) -> list[CheckResult]:
    """
    Проверяет список товарных спецификаций на соответствие требованиям.

    Args:
        specifications: Список товарных спецификаций для проверки
        price_checker: Экземпляр проверщика цен (опционально)
        inventory_checker: Экземпляр проверщика наличия (опционально)
        tolerance_percent: Допустимое отклонение цен в процентах

    Returns:
        Список результатов проверки
    """
    logger.info(f"Начинаю проверку {len(specifications)} товарных спецификаций")

    results = []

    for spec in specifications:
        # === БАЗОВЫЕ ПРОВЕРКИ СПЕЦИФИКАЦИИ ===

        # Проверка корректности данных спецификации
        spec_issues = []

        if not spec.product_code:
            spec_issues.append("отсутствует артикул товара")

        if not spec.product_name:
            spec_issues.append("отсутствует наименование товара")

        if spec.quantity <= 0:
            spec_issues.append("некорректное количество")

        if spec.unit_price < 0:
            spec_issues.append("некорректная цена")

        # Проверка соответствия общей суммы
        expected_total = spec.quantity * spec.unit_price
        if abs(spec.total_amount - expected_total) > 0.01:  # Допуск на округление
            spec_issues.append(
                f"несоответствие общей суммы (ожидается {expected_total:.2f}, указано {spec.total_amount:.2f})"
            )

        if spec_issues:
            results.append(
                CheckResult(
                    section=f"Спецификация товара {spec.product_code}",
                    match="нет",
                    comments=f"Ошибки в спецификации: {'; '.join(spec_issues)}",
                    check_type="товарный",
                    product_code=spec.product_code,
                )
            )
            continue
        else:
            results.append(
                CheckResult(
                    section=f"Спецификация товара {spec.product_code}",
                    match="да",
                    comments="Спецификация товара корректна",
                    check_type="товарный",
                    product_code=spec.product_code,
                )
            )

        # === ПРОВЕРКА ЦЕН ===
        if price_checker:
            try:
                price_result = price_checker.check_price(
                    spec.product_code, spec.unit_price, tolerance_percent
                )

                # Добавляем информацию из спецификации
                price_result.product_code = spec.product_code
                price_result.actual_quantity = spec.quantity
                price_result.section = f"Цена товара {spec.product_code}"

                results.append(price_result)

            except Exception as e:
                logger.warning(
                    f"Ошибка при проверке цены товара {spec.product_code}: {e}"
                )
                results.append(
                    CheckResult(
                        section=f"Цена товара {spec.product_code}",
                        match="нет",
                        comments=f"Ошибка проверки цены: {e}",
                        check_type="ценовой",
                        product_code=spec.product_code,
                    )
                )

        # === ПРОВЕРКА НАЛИЧИЯ ===
        if inventory_checker:
            try:
                availability_result = inventory_checker.check_availability(
                    spec.product_code, spec.quantity
                )

                # Обновляем информацию из спецификации
                availability_result.section = f"Наличие товара {spec.product_code}"
                availability_result.product_code = spec.product_code

                results.append(availability_result)

            except Exception as e:
                logger.warning(
                    f"Ошибка при проверке наличия товара {spec.product_code}: {e}"
                )
                results.append(
                    CheckResult(
                        section=f"Наличие товара {spec.product_code}",
                        match="нет",
                        comments=f"Ошибка проверки наличия: {e}",
                        check_type="складской",
                        product_code=spec.product_code,
                    )
                )

        # === ПРОВЕРКА СТАТУСА НАЛИЧИЯ ===
        if spec.availability_status:
            if spec.availability_status == "в наличии":
                availability_comment = "Товар заявлен как имеющийся в наличии"
                availability_match = "да"
            elif spec.availability_status == "под заказ":
                availability_comment = "Товар под заказ - требует уточнения сроков"
                availability_match = "частично"
            else:  # "нет в наличии"
                availability_comment = "Товар отсутствует в наличии"
                availability_match = "нет"

            results.append(
                CheckResult(
                    section=f"Статус наличия {spec.product_code}",
                    match=availability_match,
                    comments=availability_comment,
                    check_type="товарный",
                    product_code=spec.product_code,
                    availability_check=spec.availability_status,
                )
            )

        # === ДОПОЛНИТЕЛЬНЫЕ ПРОВЕРКИ ===

        # Проверка категории и бренда (если указаны)
        additional_info = []
        if spec.category:
            additional_info.append(f"категория: {spec.category}")
        if spec.brand:
            additional_info.append(f"бренд: {spec.brand}")
        if spec.supplier_code:
            additional_info.append(f"артикул поставщика: {spec.supplier_code}")

        if additional_info:
            results.append(
                CheckResult(
                    section=f"Дополнительная информация {spec.product_code}",
                    match="да",
                    comments=f"Указана дополнительная информация: {'; '.join(additional_info)}",
                    check_type="товарный",
                    product_code=spec.product_code,
                )
            )

    # === ОБЩАЯ СВОДКА ПО СПЕЦИФИКАЦИЯМ ===
    total_specs = len(specifications)
    total_amount = sum(spec.total_amount for spec in specifications)

    # Подсчет статистики по проверкам
    price_checks = [r for r in results if r.check_type == "ценовой"]
    availability_checks = [r for r in results if r.check_type == "складской"]

    price_issues = len([r for r in price_checks if r.match == "нет"])
    availability_issues = len([r for r in availability_checks if r.match == "нет"])

    summary_comments = [
        f"Проверено {total_specs} товарных позиций",
        f"Общая сумма спецификаций: {total_amount:.2f} руб.",
    ]

    if price_checks:
        summary_comments.append(
            f"Ценовых проблем: {price_issues} из {len(price_checks)}"
        )

    if availability_checks:
        summary_comments.append(
            f"Проблем с наличием: {availability_issues} из {len(availability_checks)}"
        )

    # Определяем общий статус
    if price_issues == 0 and availability_issues == 0:
        summary_match = "да"
        summary_comments.append("Все проверки пройдены успешно")
    elif price_issues > 0 or availability_issues > 0:
        if price_issues + availability_issues < total_specs * 0.3:  # Менее 30% проблем
            summary_match = "частично"
            summary_comments.append("Выявлены незначительные проблемы")
        else:
            summary_match = "нет"
            summary_comments.append("Выявлены серьезные проблемы")
    else:
        summary_match = "частично"

    results.append(
        CheckResult(
            section="Общая сводка по спецификациям",
            match=summary_match,
            comments="; ".join(summary_comments),
            check_type="товарный",
        )
    )

    logger.info(
        f"Проверка товарных спецификаций завершена. Найдено {len(results)} результатов проверки"
    )

    return results
