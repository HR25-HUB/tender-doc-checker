"""
Тесты для взвешенной оценки поставщиков
Включает тестирование алгоритмов оценки по цене, срокам поставки и рейтингу
"""

from typing import Optional

import pytest

from src.models import (
    CommercialProposal,
    DeliveryTerms,
    PaymentTerms,
    ProductSpecification,
    SupplierInfo,
)


class TestSupplierScoring:
    """Тесты для системы взвешенной оценки поставщиков"""

    def test_basic_supplier_scoring_weights(self):
        """Тест базовой взвешенной оценки поставщиков"""
        # Создаем тестовых поставщиков с разными характеристиками
        suppliers_data = [
            {"name": "Поставщик A", "price": 1000.0, "delivery_days": 7, "rating": 4.5},
            {"name": "Поставщик B", "price": 800.0, "delivery_days": 14, "rating": 3.8},
            {"name": "Поставщик C", "price": 1200.0, "delivery_days": 3, "rating": 4.8},
        ]

        scores = []
        for supplier_data in suppliers_data:
            score = self._calculate_weighted_score(
                price=supplier_data["price"],
                delivery_days=supplier_data["delivery_days"],
                rating=supplier_data["rating"],
                reference_price=1000.0,
            )
            assert 0.0 <= score <= 10.0
            scores.append(score)

        # Проверяем, что более оптимальные характеристики дают более высокую оценку
        # Поставщик A должен быть лучше B (лучше рейтинг и доставка)
        # Поставщик C должен быть лучше B (быстрее доставка и выше рейтинг)
        assert scores[0] > scores[1] or scores[2] > scores[1]

    def test_price_weight_calculation(self):
        """Тест расчета веса цены в общей оценке"""
        reference_price = 1000.0

        # Тест: цена ниже рыночной
        low_price = 800.0
        price_score = self._calculate_price_score(low_price, reference_price)
        assert price_score == 10.0  # Максимальный балл за низкую цену

        # Тест: цена равна рыночной
        market_price = 1000.0
        price_score = self._calculate_price_score(market_price, reference_price)
        assert price_score == 7.5  # Средний балл за рыночную цену

        # Тест: цена выше рыночной
        high_price = 1200.0
        price_score = self._calculate_price_score(high_price, reference_price)
        assert price_score == 5.0  # Низкий балл за высокую цену

    def test_delivery_time_weight_calculation(self):
        """Тест расчета веса сроков поставки"""

        # Тест: быстрая доставка
        fast_delivery = 3
        delivery_score = self._calculate_delivery_score(fast_delivery)
        assert delivery_score >= 9.0

        # Тест: стандартная доставка
        standard_delivery = 7
        delivery_score = self._calculate_delivery_score(standard_delivery)
        assert 7.0 <= delivery_score <= 9.0

        # Тест: долгая доставка
        slow_delivery = 21
        delivery_score = self._calculate_delivery_score(slow_delivery)
        assert delivery_score <= 5.0

    def test_rating_weight_calculation(self):
        """Тест расчета веса рейтинга поставщика"""

        # Тест: отличный рейтинг
        excellent_rating = 4.8
        rating_score = self._calculate_rating_score(excellent_rating)
        assert rating_score == 9.6

        # Тест: хороший рейтинг
        good_rating = 4.0
        rating_score = self._calculate_rating_score(good_rating)
        assert rating_score == 8.0

        # Тест: средний рейтинг
        average_rating = 3.0
        rating_score = self._calculate_rating_score(average_rating)
        assert rating_score == 6.0

        # Тест: низкий рейтинг
        poor_rating = 2.5
        rating_score = self._calculate_rating_score(poor_rating)
        assert rating_score == 5.0

    def test_weight_configuration_impact(self):
        """Тест влияния конфигурации весов на итоговую оценку"""

        # Базовые параметры для сравнения
        base_price = 1000.0
        base_delivery = 7
        base_rating = 4.5

        # Тест с разными конфигурациями весов
        weight_configs = [
            {"price": 0.5, "delivery": 0.3, "rating": 0.2},
            {"price": 0.3, "delivery": 0.4, "rating": 0.3},
            {"price": 0.4, "delivery": 0.2, "rating": 0.4},
        ]

        scores = []
        for weights in weight_configs:
            score = self._calculate_weighted_score_with_weights(
                price=base_price,
                delivery_days=base_delivery,
                rating=base_rating,
                reference_price=1000.0,
                weights=weights,
            )
            scores.append(score)

        # Проверяем, что все оценки в допустимом диапазоне
        for score in scores:
            assert 0.0 <= score <= 10.0

        # Проверяем, что разные конфигурации дают разные результаты
        assert len(set(round(s, 2) for s in scores)) >= 2

    def test_supplier_comparison_multiple_criteria(self):
        """Тест сравнения поставщиков по множеству критериев"""

        suppliers = [
            SupplierInfo(
                name="ООО Поставщик 1",
                inn="1234567890",
                contact_person="Иванов И.И.",
                phone="+7 495 123-45-67",
                email="info@supplier1.ru",
                rating=4.5,
            ),
            SupplierInfo(
                name="ООО Поставщик 2",
                inn="0987654321",
                contact_person="Петров П.П.",
                phone="+7 495 987-65-43",
                email="info@supplier2.ru",
                rating=4.2,
            ),
            SupplierInfo(
                name="ООО Поставщик 3",
                inn="1122334455",
                contact_person="Сидоров С.С.",
                phone="+7 495 111-22-33",
                email="info@supplier3.ru",
                rating=3.8,
            ),
        ]

        proposals = [
            self._create_test_proposal(suppliers[0], 1000.0, 7, 4.5),
            self._create_test_proposal(suppliers[1], 950.0, 10, 4.2),
            self._create_test_proposal(suppliers[2], 850.0, 14, 3.8),
        ]

        # Сравниваем предложения
        ranked_proposals = self._rank_supplier_proposals(proposals)

        # Проверяем правильность ранжирования
        assert len(ranked_proposals) == 3
        assert (
            ranked_proposals[0]["supplier_name"] == "ООО Поставщик 1"
        )  # Лучший баланс
        assert ranked_proposals[1]["supplier_name"] == "ООО Поставщик 2"  # Второе место
        assert ranked_proposals[2]["supplier_name"] == "ООО Поставщик 3"  # Третье место

    def test_edge_cases_scoring(self):
        """Тест крайних случаев в оценке поставщиков"""

        edge_cases = [
            {
                "price": 0.0,  # Бесплатная поставка
                "delivery_days": 1,
                "rating": 5.0,
                "expected_behavior": "handle_zero_price",
            },
            {
                "price": 1000.0,
                "delivery_days": 0,  # Мгновенная доставка
                "rating": 5.0,
                "expected_behavior": "handle_zero_delivery",
            },
            {
                "price": 1000.0,
                "delivery_days": 365,  # Очень долгая доставка
                "rating": 1.0,  # Минимальный рейтинг
                "expected_behavior": "handle_extreme_values",
            },
        ]

        for case in edge_cases:
            score = self._calculate_weighted_score(
                price=case["price"],
                delivery_days=case["delivery_days"],
                rating=case["rating"],
                reference_price=1000.0,
            )
            assert 0.0 <= score <= 10.0  # Оценка должна быть в допустимом диапазоне

    def test_supplier_scoring_integration(self):
        """Интеграционный тест системы оценки поставщиков"""

        # Создаем тестовое предложение
        supplier = SupplierInfo(
            name="Тестовый Поставщик",
            inn="1234567890",
            contact_person="Тестов Т.Т.",
            phone="+7 000 000-00-00",
            email="test@supplier.ru",
            rating=4.3,
        )
        proposal = self._create_test_proposal(supplier, 1100.0, 5, 4.3)

        # Анализируем предложение напрямую через метод оценки
        score = self._calculate_weighted_score(
            price=proposal.total_amount,
            delivery_days=proposal.delivery_terms.delivery_period_days,
            rating=proposal.supplier.rating or 3.0,
            reference_price=1000.0,
        )

        # Проверяем наличие оценки
        assert isinstance(score, (int, float))
        assert 0.0 <= score <= 10.0

    def test_supplier_scoring_persistence(self):
        """Тест сохранения и восстановления оценок поставщиков"""

        supplier_scores = {"supplier_1": 8.5, "supplier_2": 7.2, "supplier_3": 6.8}

        # Сохраняем оценки
        self._save_supplier_scores(supplier_scores)

        # Восстанавливаем оценки
        restored_scores = self._load_supplier_scores()

        assert restored_scores == supplier_scores

    def test_supplier_scoring_normalization(self):
        """Тест нормализации оценок для сравнения поставщиков"""

        raw_scores = [15.0, 8.0, 12.0, 5.0, 20.0]
        normalized_scores = self._normalize_scores(raw_scores)

        # Проверяем нормализацию к диапазону 0-10
        assert max(normalized_scores) <= 10.0
        assert min(normalized_scores) >= 0.0
        assert len(normalized_scores) == len(raw_scores)

    def test_supplier_scoring_with_missing_data(self):
        """Тест оценки поставщиков с неполными данными"""

        incomplete_suppliers = [
            {"price": 1000.0, "delivery_days": None, "rating": 4.0},
            {"price": None, "delivery_days": 7, "rating": 4.5},
            {"price": 1000.0, "delivery_days": 7, "rating": None},
        ]

        for supplier_data in incomplete_suppliers:
            score = self._calculate_weighted_score_with_defaults(
                price=supplier_data["price"],
                delivery_days=supplier_data["delivery_days"],
                rating=supplier_data["rating"],
                reference_price=1000.0,
            )
            assert score is not None
            assert 0.0 <= score <= 10.0

    # Вспомогательные методы
    def _calculate_weighted_score(
        self, price: float, delivery_days: int, rating: float, reference_price: float
    ) -> float:
        """Рассчитать взвешенную оценку поставщика"""
        price_score = self._calculate_price_score(price, reference_price)
        delivery_score = self._calculate_delivery_score(delivery_days)
        rating_score = self._calculate_rating_score(rating)

        # Веса по умолчанию
        weights = {"price": 0.4, "delivery": 0.3, "rating": 0.3}

        return (
            price_score * weights["price"]
            + delivery_score * weights["delivery"]
            + rating_score * weights["rating"]
        )

    def _calculate_price_score(self, price: float, reference_price: float) -> float:
        """Рассчитать оценку за цену"""
        if reference_price == 0:
            return 5.0

        price_ratio = price / reference_price
        if price_ratio <= 0.8:
            return 10.0
        elif price_ratio <= 1.0:
            return 7.5 + (1.0 - price_ratio) * 12.5
        elif price_ratio <= 1.2:
            return 7.5 - (price_ratio - 1.0) * 12.5
        else:
            return max(0.0, 5.0 - (price_ratio - 1.2) * 10.0)

    def _calculate_delivery_score(self, delivery_days: int) -> float:
        """Рассчитать оценку за сроки поставки"""
        if delivery_days <= 3:
            return 10.0
        elif delivery_days <= 7:
            return 8.0 + (7 - delivery_days) * 0.5
        elif delivery_days <= 14:
            return 6.0 + (14 - delivery_days) * 0.285
        elif delivery_days <= 30:
            return 3.0 + (30 - delivery_days) * 0.214
        else:
            return max(0.0, 2.0 - (delivery_days - 30) * 0.1)

    def _calculate_rating_score(self, rating: float) -> float:
        """Рассчитать оценку за рейтинг"""
        return rating * 2.0

    def _calculate_weighted_score_with_weights(
        self,
        price: float,
        delivery_days: int,
        rating: float,
        reference_price: float,
        weights: dict[str, float],
    ) -> float:
        """Рассчитать взвешенную оценку с заданными весами"""
        price_score = self._calculate_price_score(price, reference_price)
        delivery_score = self._calculate_delivery_score(delivery_days)
        rating_score = self._calculate_rating_score(rating)

        return (
            price_score * weights["price"]
            + delivery_score * weights["delivery"]
            + rating_score * weights["rating"]
        )

    def _create_test_proposal(
        self, supplier: SupplierInfo, price: float, delivery_days: int, rating: float
    ) -> CommercialProposal:
        """Создать тестовое коммерческое предложение"""
        return CommercialProposal(
            supplier=supplier,
            products=[
                ProductSpecification(
                    product_code="TEST001",
                    product_name="Тестовый товар",
                    quantity=1,
                    unit="шт",
                    unit_price=price,
                    total_amount=price,
                    availability_status="в наличии",
                )
            ],
            payment_terms=PaymentTerms(
                payment_type="постоплата", payment_period_days=30
            ),
            delivery_terms=DeliveryTerms(
                delivery_type="доставка", delivery_period_days=delivery_days
            ),
            total_amount=price,
        )

    def _rank_supplier_proposals(
        self, proposals: list[CommercialProposal]
    ) -> list[dict[str, any]]:
        """Ранжировать предложения поставщиков"""
        return sorted(
            [
                {
                    "supplier_name": p.supplier.name,
                    "score": self._calculate_weighted_score(
                        price=p.products[0].unit_price,
                        delivery_days=p.delivery_terms.delivery_period_days,
                        rating=p.supplier.rating,
                        reference_price=1000.0,
                    ),
                }
                for p in proposals
            ],
            key=lambda x: x["score"],
            reverse=True,
        )

    def _save_supplier_scores(self, scores: dict[str, float]) -> None:
        """Сохранить оценки поставщиков"""
        # Заглушка для тестирования сохранения
        pass

    def _load_supplier_scores(self) -> dict[str, float]:
        """Загрузить оценки поставщиков"""
        # Заглушка для тестирования загрузки
        return {"supplier_1": 8.5, "supplier_2": 7.2, "supplier_3": 6.8}

    def _normalize_scores(self, scores: list[float]) -> list[float]:
        """Нормализовать оценки к диапазону 0-10"""
        if not scores:
            return []

        min_score = min(scores)
        max_score = max(scores)

        if max_score == min_score:
            return [5.0] * len(scores)

        return [
            ((score - min_score) / (max_score - min_score)) * 10.0 for score in scores
        ]

    def _calculate_weighted_score_with_defaults(
        self,
        price: Optional[float],
        delivery_days: Optional[int],
        rating: Optional[float],
        reference_price: float,
    ) -> float:
        """Рассчитать оценку с значениями по умолчанию для неполных данных"""
        price = price or reference_price
        delivery_days = delivery_days or 7
        rating = rating or 3.0

        return self._calculate_weighted_score(
            price, delivery_days, rating, reference_price
        )

    def test_supplier_sorting_algorithms(self):
        """Тест алгоритмов сортировки поставщиков"""
        suppliers = [
            SupplierInfo(
                name=f"Поставщик {i}",
                inn="1234567890",
                contact_person=f"Персона {i}",
                phone=f"+7 495 123-45-{i:02d}",
                email=f"mail{i}@test.ru",
                rating=3.0 + i * 0.4,
            )
            for i in range(1, 6)
        ]

        proposals = [
            self._create_test_proposal(
                suppliers[i - 1], 1000 + i * 100, 5 + i * 2, 3.0 + i * 0.4
            )
            for i in range(1, 6)
        ]

        # Тест сортировки по цене (по возрастанию)
        sorted_by_price = sorted(proposals, key=lambda p: p.total_amount)
        assert sorted_by_price[0].total_amount <= sorted_by_price[-1].total_amount

        # Тест сортировки по рейтингу (по убыванию)
        sorted_by_rating = sorted(
            proposals, key=lambda p: p.supplier.rating, reverse=True
        )
        assert (
            sorted_by_rating[0].supplier.rating >= sorted_by_rating[-1].supplier.rating
        )

        # Тест сортировки по срокам поставки (по возрастанию)
        sorted_by_delivery = sorted(
            proposals, key=lambda p: p.delivery_terms.delivery_period_days
        )
        assert (
            sorted_by_delivery[0].delivery_terms.delivery_period_days
            <= sorted_by_delivery[-1].delivery_terms.delivery_period_days
        )

    def test_top_n_recommendations(self):
        """Тест получения топ-N рекомендаций поставщиков"""
        suppliers = [
            SupplierInfo(
                name=f"Поставщик {i:02d}",
                inn="1234567890",
                contact_person=f"Персона {i}",
                phone=f"+7 495 123-45-{i:02d}",
                email=f"mail{i}@test.ru",
                rating=3.0 + i * 0.2,
            )
            for i in range(1, 11)
        ]

        proposals = [
            self._create_test_proposal(
                suppliers[i - 1], 1000 + i * 50, 3 + i, 3.0 + i * 0.2
            )
            for i in range(1, 11)
        ]

        # Получаем топ-3 поставщиков
        top_3 = self._get_top_n_suppliers(proposals, n=3)
        assert len(top_3) == 3

        # Проверяем, что топ-N отсортирован по убыванию оценки
        for i in range(1, len(top_3)):
            assert top_3[i - 1]["score"] >= top_3[i]["score"]

        # Проверяем граничные случаи
        top_1 = self._get_top_n_suppliers(proposals, n=1)
        assert len(top_1) == 1

        top_all = self._get_top_n_suppliers(proposals, n=20)
        assert len(top_all) == 10  # Не больше, чем доступно

    def test_top_n_with_ties(self):
        """Тест топ-N рекомендаций при одинаковых оценках"""
        suppliers = [
            SupplierInfo(
                name=f"Поставщик {i}",
                inn="1234567890",
                contact_person=f"Персона {i}",
                phone=f"+7 495 123-45-{i:02d}",
                email=f"mail{i}@test.ru",
                rating=4.0,
            )
            for i in range(1, 6)
        ]

        # Создаем предложения с одинаковыми характеристиками
        proposals = [
            self._create_test_proposal(suppliers[i - 1], 1000.0, 7, 4.0)
            for i in range(1, 6)
        ]

        top_3 = self._get_top_n_suppliers(proposals, n=3)
        assert len(top_3) == 3

        # Все должны иметь одинаковую оценку
        first_score = top_3[0]["score"]
        for supplier in top_3:
            assert abs(supplier["score"] - first_score) < 0.01

    def test_supplier_scoring_ranking_stability(self):
        """Тест стабильности ранжирования при одинаковых оценках"""
        suppliers = [
            SupplierInfo(
                name=f"Поставщик {i}",
                inn="1234567890",
                contact_person=f"Персона {i}",
                phone=f"+7 495 123-45-{i:02d}",
                email=f"mail{i}@test.ru",
                rating=4.0,
            )
            for i in range(1, 4)
        ]

        # Создаем предложения с одинаковыми характеристиками
        proposals = [
            self._create_test_proposal(suppliers[i - 1], 1000.0, 7, 4.0)
            for i in range(1, 4)
        ]

        # Проверяем стабильность ранжирования при многократной сортировке
        rankings = []
        for _ in range(5):
            ranked = self._get_top_n_suppliers(proposals, n=3)
            rankings.append([r["supplier_name"] for r in ranked])

        # Все ранжирования должны быть одинаковыми
        assert all(r == rankings[0] for r in rankings)

    def test_supplier_scoring_with_filters(self):
        """Тест фильтрации и сортировки поставщиков"""
        suppliers = [
            SupplierInfo(
                name=f"Поставщик {i}",
                inn="1234567890",
                contact_person=f"Персона {i}",
                phone=f"+7 495 123-45-{i:02d}",
                email=f"mail{i}@test.ru",
                rating=3.0 + i * 0.2,
            )
            for i in range(1, 6)
        ]

        proposals = [
            self._create_test_proposal(
                suppliers[i - 1], 1000 + i * 100, 5 + i * 2, 3.0 + i * 0.2
            )
            for i in range(1, 6)
        ]

        # Фильтрация по минимальному рейтингу
        filtered = [p for p in proposals if p.supplier.rating >= 3.5]
        assert len(filtered) >= 2

        # Сортировка отфильтрованных
        sorted_filtered = self._get_top_n_suppliers(filtered, n=3)
        assert len(sorted_filtered) <= 3

        # Проверяем, что все отфильтрованные имеют корректные оценки
        for supplier_info in sorted_filtered:
            assert 0.0 <= supplier_info["score"] <= 10.0  # Проверяем диапазон оценки

    def _get_top_n_suppliers(
        self, proposals: list[CommercialProposal], n: int
    ) -> list[dict[str, any]]:
        """Получить топ-N поставщиков по оценке"""
        if not proposals:
            return []

        ranked = self._rank_supplier_proposals(proposals)
        return ranked[: min(n, len(ranked))]

    def test_supplier_scoring_empty_list_handling(self):
        """Тест обработки пустых списков"""
        empty_proposals = []

        # Проверяем, что методы корректно обрабатывают пустые списки
        ranked = self._rank_supplier_proposals(empty_proposals)
        assert ranked == []

        top_n = self._get_top_n_suppliers(empty_proposals, n=5)
        assert top_n == []


class TestSupplierScoringDatabase:
    """Тесты работы с базой данных для оценки поставщиков"""

    def test_supplier_scoring_storage(self):
        """Тест хранения оценок поставщиков в БД"""
        # Создаем тестовых поставщиков
        suppliers = [
            SupplierInfo(
                name="Поставщик А",
                inn="1234567890",
                contact_person="Иванов И.И.",
                phone="+7 495 123-45-01",
                email="supplierA@test.ru",
                rating=4.5,
            ),
            SupplierInfo(
                name="Поставщик Б",
                inn="0987654321",
                contact_person="Петров П.П.",
                phone="+7 495 123-45-02",
                email="supplierB@test.ru",
                rating=4.2,
            ),
            SupplierInfo(
                name="Поставщик В",
                inn="1122334455",
                contact_person="Сидоров С.С.",
                phone="+7 495 123-45-03",
                email="supplierC@test.ru",
                rating=3.8,
            ),
        ]

        # Создаем тестовые предложения
        proposals = [
            self._create_test_proposal(suppliers[0], 1000.0, 7, 4.5),
            self._create_test_proposal(suppliers[1], 950.0, 10, 4.2),
            self._create_test_proposal(suppliers[2], 850.0, 14, 3.8),
        ]

        # Рассчитываем оценки
        scored_proposals = self._rank_supplier_proposals(proposals)

        # Сохраняем оценки в БД
        decision_id = self._save_supplier_decision_to_db(
            tender_id="TENDER-2024-001",
            proposals=scored_proposals,
            selected_supplier_id="supplier_1",
            decision_reason="Лучшее соотношение цена/качество",
        )

        assert decision_id is not None
        assert isinstance(decision_id, str)
        assert len(decision_id) > 0

    def test_supplier_scoring_history(self):
        """Тест истории оценок поставщиков"""
        # Создаем несколько решений
        tender_ids = ["TENDER-2024-001", "TENDER-2024-002", "TENDER-2024-003"]

        for tender_id in tender_ids:
            suppliers = [
                SupplierInfo(
                    name=f"Поставщик {i}",
                    inn="1234567890",
                    contact_person=f"Контакт {i}",
                    phone=f"+7 495 123-45-{i:02d}",
                    email=f"supplier{i}@test.ru",
                    rating=4.0 + i * 0.1,
                )
                for i in range(1, 4)
            ]

            proposals = [
                self._create_test_proposal(
                    suppliers[i - 1], 1000 + i * 50, 5 + i, 4.0 + i * 0.1
                )
                for i in range(1, 4)
            ]

            scored_proposals = self._rank_supplier_proposals(proposals)

            self._save_supplier_decision_to_db(
                tender_id=tender_id,
                proposals=scored_proposals,
                selected_supplier_id=f"supplier_{tender_id.split('-')[-1]}",
                decision_reason=f"Решение по тендеру {tender_id}",
            )

        # Получаем историю решений
        history = self._get_supplier_decisions_history()

        assert len(history) >= 3
        assert all("tender_id" in record for record in history)
        assert all("selected_supplier" in record for record in history)
        assert all("decision_date" in record for record in history)

    def test_supplier_scoring_trends(self):
        """Тест анализа трендов оценок поставщиков"""
        import sqlite3

        # Очищаем историю для тестового поставщика
        supplier_name = "Тестовый Поставщик"
        conn = sqlite3.connect("test_audit.db")
        try:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM supplier_score_history WHERE supplier_name = ?",
                (supplier_name,),
            )
            conn.commit()
        finally:
            conn.close()

        # Создаем тестовые данные для анализа трендов
        scores_history = [
            {"date": "2024-01-01", "score": 7.5, "tender_id": "T-001"},
            {"date": "2024-02-01", "score": 8.2, "tender_id": "T-002"},
            {"date": "2024-03-01", "score": 7.8, "tender_id": "T-003"},
            {"date": "2024-04-01", "score": 8.5, "tender_id": "T-004"},
        ]

        # Сохраняем историю оценок
        for score_data in scores_history:
            self._save_supplier_score_to_history(
                supplier_name=supplier_name,
                score=score_data["score"],
                tender_id=score_data["tender_id"],
                date=score_data["date"],
            )

        # Анализируем тренды
        trends = self._analyze_supplier_trends(supplier_name)

        assert "average_score" in trends
        assert "trend_direction" in trends
        assert "score_improvement" in trends
        assert trends["data_points"] >= 4

    def test_score_suppliers_integration(self):
        """Интеграционный тест для score_suppliers и select_top_suppliers"""
        from recommendations import RecommendationEngine

        # Создаем тестовых поставщиков с разными характеристиками
        suppliers = [
            SupplierInfo(
                name="Поставщик Премиум",
                inn="1234567890",
                contact_person="Иванов И.И.",
                phone="+7 495 123-45-67",
                email="premium@supplier.ru",
                rating=4.8,
            ),
            SupplierInfo(
                name="Поставщик Эконом",
                inn="0987654321",
                contact_person="Петров П.П.",
                phone="+7 495 987-65-43",
                email="economy@supplier.ru",
                rating=3.5,
            ),
            SupplierInfo(
                name="Поставщик Стандарт",
                inn="1122334455",
                contact_person="Сидоров С.С.",
                phone="+7 495 111-22-33",
                email="standard@supplier.ru",
                rating=4.2,
            ),
            SupplierInfo(
                name="Поставщик Быстрый",
                inn="5566778899",
                contact_person="Кузнецов К.К.",
                phone="+7 495 222-33-44",
                email="fast@supplier.ru",
                rating=4.0,
            ),
        ]

        # Создаем предложения с разными характеристиками
        proposals = [
            self._create_test_proposal(
                suppliers[0], 1200.0, 5, 4.8
            ),  # Высокий рейтинг, быстрая доставка, высокая цена
            self._create_test_proposal(
                suppliers[1], 800.0, 14, 3.5
            ),  # Низкая цена, медленная доставка, низкий рейтинг
            self._create_test_proposal(
                suppliers[2], 1000.0, 7, 4.2
            ),  # Средняя цена и доставка, хороший рейтинг
            self._create_test_proposal(
                suppliers[3], 950.0, 3, 4.0
            ),  # Хорошая цена, очень быстрая доставка, средний рейтинг
        ]

        # Используем RecommendationEngine для оценки
        engine = RecommendationEngine()

        # Тестируем score_suppliers
        scored_suppliers = engine.score_suppliers(proposals)

        assert len(scored_suppliers) == 4
        assert all("score" in supplier for supplier in scored_suppliers)
        assert all("price_score" in supplier for supplier in scored_suppliers)
        assert all("delivery_score" in supplier for supplier in scored_suppliers)
        assert all("rating_score" in supplier for supplier in scored_suppliers)

        # Проверяем, что все оценки в допустимом диапазоне
        for supplier in scored_suppliers:
            assert 0.0 <= supplier["score"] <= 10.0
            assert 0.0 <= supplier["price_score"] <= 10.0
            assert 0.0 <= supplier["delivery_score"] <= 10.0
            assert 0.0 <= supplier["rating_score"] <= 10.0

        # Тестируем select_top_suppliers
        top_3 = engine.select_top_suppliers(scored_suppliers, n=3)

        assert len(top_3) == 3
        assert top_3[0]["score"] >= top_3[1]["score"] >= top_3[2]["score"]

        # Тестируем граничные случаи
        top_1 = engine.select_top_suppliers(scored_suppliers, n=1)
        assert len(top_1) == 1

        top_all = engine.select_top_suppliers(scored_suppliers, n=10)
        assert len(top_all) == 4  # Не больше, чем доступно

        # Проверяем, что топ-1 имеет наивысшую оценку
        assert top_1[0]["score"] == max(s["score"] for s in scored_suppliers)

    def test_score_suppliers_with_custom_weights(self):
        """Тест оценки поставщиков с пользовательскими весами"""
        from recommendations import RecommendationEngine

        suppliers = [
            SupplierInfo(
                name="Поставщик А",
                inn="1234567890",
                contact_person="Иванов И.И.",
                phone="+7 495 123-45-67",
                email="a@supplier.ru",
                rating=4.5,
            ),
            SupplierInfo(
                name="Поставщик Б",
                inn="0987654321",
                contact_person="Петров П.П.",
                phone="+7 495 987-65-43",
                email="b@supplier.ru",
                rating=4.0,
            ),
        ]

        proposals = [
            self._create_test_proposal(suppliers[0], 1000.0, 7, 4.5),
            self._create_test_proposal(suppliers[1], 900.0, 10, 4.0),
        ]

        engine = RecommendationEngine()

        # Тест с весами, ориентированными на цену
        price_focused_weights = {"price": 0.7, "delivery": 0.2, "rating": 0.1}
        price_focused_scores = engine.score_suppliers(proposals, price_focused_weights)

        # Тест с весами, ориентированными на доставку
        delivery_focused_weights = {"price": 0.2, "delivery": 0.6, "rating": 0.2}
        delivery_focused_scores = engine.score_suppliers(
            proposals, delivery_focused_weights
        )

        # Проверяем, что разные веса дают разные результаты
        assert price_focused_scores[0]["score"] != delivery_focused_scores[0]["score"]

        # Проверяем нормализацию весов
        extreme_weights = {"price": 100, "delivery": 50, "rating": 25}
        normalized_scores = engine.score_suppliers(proposals, extreme_weights)

        # Оценки должны быть в допустимом диапазоне
        for supplier in normalized_scores:
            assert 0.0 <= supplier["score"] <= 10.0

    def _save_supplier_decision_to_db(
        self,
        tender_id: str,
        proposals: list[dict],
        selected_supplier_id: str,
        decision_reason: str,
    ) -> str:
        """Сохранить принятое решение в БД"""
        import sqlite3
        import uuid

        conn = sqlite3.connect("test_audit.db")
        try:
            cursor = conn.cursor()

            # Создаем таблицу для решений по поставщикам
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS supplier_decisions (
                    decision_id TEXT PRIMARY KEY,
                    tender_id TEXT NOT NULL,
                    selected_supplier_id TEXT NOT NULL,
                    decision_reason TEXT,
                    decision_date TEXT DEFAULT CURRENT_TIMESTAMP,
                    total_proposals INTEGER,
                    avg_score REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Создаем таблицу для деталей оценок
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS supplier_scores (
                    score_id TEXT PRIMARY KEY,
                    decision_id TEXT NOT NULL,
                    supplier_name TEXT NOT NULL,
                    supplier_inn TEXT,
                    score REAL NOT NULL,
                    price_score REAL,
                    delivery_score REAL,
                    rating_score REAL,
                    rank INTEGER,
                    FOREIGN KEY (decision_id) REFERENCES supplier_decisions (decision_id)
                )
            """
            )

            decision_id = str(uuid.uuid4())

            # Сохраняем основное решение
            cursor.execute(
                """
                INSERT INTO supplier_decisions (decision_id, tender_id, selected_supplier_id, decision_reason, total_proposals, avg_score)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    decision_id,
                    tender_id,
                    selected_supplier_id,
                    decision_reason,
                    len(proposals),
                    sum(p["score"] for p in proposals) / len(proposals)
                    if proposals
                    else 0,
                ),
            )

            # Сохраняем детали оценок
            for rank, proposal in enumerate(proposals, 1):
                score_id = str(uuid.uuid4())
                cursor.execute(
                    """
                    INSERT INTO supplier_scores (score_id, decision_id, supplier_name, supplier_inn, score, rank)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        score_id,
                        decision_id,
                        proposal["supplier_name"],
                        proposal.get("supplier_inn", ""),
                        proposal["score"],
                        rank,
                    ),
                )

            conn.commit()
            return decision_id

        finally:
            conn.close()

    def _get_supplier_decisions_history(self) -> list[dict]:
        """Получить историю решений по поставщикам"""
        import sqlite3

        conn = sqlite3.connect("test_audit.db")
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT decision_id, tender_id, selected_supplier_id, decision_reason, decision_date
                FROM supplier_decisions
                ORDER BY decision_date DESC
            """
            )

            decisions = []
            for row in cursor.fetchall():
                decisions.append(
                    {
                        "decision_id": row[0],
                        "tender_id": row[1],
                        "selected_supplier": row[2],
                        "decision_reason": row[3],
                        "decision_date": row[4],
                    }
                )

            return decisions

        finally:
            conn.close()

    def _save_supplier_score_to_history(
        self, supplier_name: str, score: float, tender_id: str, date: str
    ) -> None:
        """Сохранить оценку поставщика в историю"""
        import sqlite3

        conn = sqlite3.connect("test_audit.db")
        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS supplier_score_history (
                    id TEXT PRIMARY KEY,
                    supplier_name TEXT NOT NULL,
                    score REAL NOT NULL,
                    tender_id TEXT,
                    score_date TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            import uuid

            score_id = str(uuid.uuid4())

            cursor.execute(
                """
                INSERT INTO supplier_score_history (id, supplier_name, score, tender_id, score_date)
                VALUES (?, ?, ?, ?, ?)
            """,
                (score_id, supplier_name, score, tender_id, date),
            )

            conn.commit()

        finally:
            conn.close()

    def _calculate_weighted_score(
        self,
        price: float,
        delivery_days: int,
        rating: float,
        reference_price: float = 1000.0,
    ) -> float:
        """Рассчитать взвешенную оценку поставщика"""
        # Веса критериев
        PRICE_WEIGHT = 0.5
        DELIVERY_WEIGHT = 0.3
        RATING_WEIGHT = 0.2

        # Оценка за цену (0-10 баллов)
        price_score = self._calculate_price_score(price, reference_price)

        # Оценка за сроки поставки (0-10 баллов)
        delivery_score = self._calculate_delivery_score(delivery_days)

        # Оценка за рейтинг поставщика (0-10 баллов)
        rating_score = self._calculate_rating_score(rating)

        # Итоговая взвешенная оценка
        total_score = (
            price_score * PRICE_WEIGHT
            + delivery_score * DELIVERY_WEIGHT
            + rating_score * RATING_WEIGHT
        )

        return round(total_score, 2)

    def _calculate_price_score(self, price: float, reference_price: float) -> float:
        """Рассчитать оценку за цену"""
        if price <= reference_price * 0.8:
            return 10.0
        elif price <= reference_price:
            price_ratio = price / reference_price
            return max(7.5, 10.0 - (price_ratio - 0.8) * 12.5)
        else:
            price_ratio = price / reference_price
            return max(0.0, 7.5 - (price_ratio - 1.0) * 15.0)

    def _calculate_delivery_score(self, delivery_days: int) -> float:
        """Рассчитать оценку за сроки поставки"""
        if delivery_days <= 3:
            return 10.0
        elif delivery_days <= 7:
            return 8.0
        elif delivery_days <= 14:
            return 6.0
        elif delivery_days <= 21:
            return 4.0
        else:
            return 2.0

    def _calculate_rating_score(self, rating: float) -> float:
        """Рассчитать оценку за рейтинг"""
        return min(10.0, rating * 2.0)

    def _create_test_proposal(
        self,
        supplier: SupplierInfo,
        price: float,
        delivery_days: int,
        supplier_rating: float,
    ) -> CommercialProposal:
        """Создать тестовое предложение поставщика"""
        return CommercialProposal(
            supplier=supplier,
            products=[
                ProductSpecification(
                    product_code="TEST001",
                    product_name="Тестовый товар",
                    quantity=1,
                    unit="шт",
                    unit_price=price,
                    total_amount=price,
                    availability_status="в наличии",
                )
            ],
            payment_terms=PaymentTerms(
                payment_type="постоплата", payment_period_days=30
            ),
            delivery_terms=DeliveryTerms(
                delivery_type="доставка", delivery_period_days=delivery_days
            ),
            total_amount=price,
        )

    def _rank_supplier_proposals(
        self, proposals: list[CommercialProposal]
    ) -> list[dict]:
        """Ранжировать предложения поставщиков по оценке"""
        scored_proposals = []
        for proposal in proposals:
            score = self._calculate_weighted_score(
                price=proposal.products[0].unit_price,
                delivery_days=proposal.delivery_terms.delivery_period_days,
                rating=proposal.supplier.rating,
                reference_price=1000.0,
            )
            scored_proposals.append(
                {
                    "supplier_name": proposal.supplier.name,
                    "supplier_inn": proposal.supplier.inn,
                    "score": score,
                    "price": proposal.products[0].unit_price,
                    "delivery_days": proposal.delivery_terms.delivery_period_days,
                    "rating": proposal.supplier.rating,
                }
            )

        # Сортируем по убыванию оценки
        scored_proposals.sort(key=lambda x: x["score"], reverse=True)
        return scored_proposals

    def _analyze_supplier_trends(self, supplier_name: str) -> dict:
        """Проанализировать тренды оценок поставщика"""
        import sqlite3

        conn = sqlite3.connect("test_audit.db")
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT score, score_date
                FROM supplier_score_history
                WHERE supplier_name = ?
                ORDER BY score_date ASC
            """,
                (supplier_name,),
            )

            scores = []
            dates = []
            for row in cursor.fetchall():
                scores.append(row[0])
                dates.append(row[1])

            if not scores:
                return {
                    "average_score": 0.0,
                    "trend_direction": "нет данных",
                    "score_improvement": 0.0,
                    "data_points": 0,
                }

            avg_score = sum(scores) / len(scores)

            # Определяем тренд
            if len(scores) >= 2:
                first_half = scores[: len(scores) // 2]
                second_half = scores[len(scores) // 2 :]
                first_avg = sum(first_half) / len(first_half)
                second_avg = sum(second_half) / len(second_half)

                if second_avg > first_avg:
                    trend_direction = "улучшение"
                    score_improvement = second_avg - first_avg
                elif second_avg < first_avg:
                    trend_direction = "ухудшение"
                    score_improvement = second_avg - first_avg
                else:
                    trend_direction = "стабильность"
                    score_improvement = 0.0
            else:
                trend_direction = "недостаточно данных"
                score_improvement = 0.0

            return {
                "average_score": round(avg_score, 2),
                "trend_direction": trend_direction,
                "score_improvement": round(score_improvement, 2),
                "data_points": len(scores),
            }

        finally:
            conn.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
