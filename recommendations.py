"""Модуль генерации рекомендаций на основе анализа данных о поставщиках и закупках."""

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional

from analytics import AnalyticsEngine
from db import DB_PATH
from price_analytics import MarketAnalysis, PriceAnalyticsEngine
from src.models import (
    CommercialProposal,
)


@dataclass
class SupplierRecommendation:
    """Рекомендация по поставщику."""

    supplier_id: str
    supplier_name: str
    recommendation_type: str  # 'preferred', 'alternative', 'avoid', 'new_opportunity'
    confidence_score: float  # 0-100
    reasons: list[str]
    risk_factors: list[str]
    advantages: list[str]
    suggested_actions: list[str]
    estimated_savings: Optional[float]  # потенциальная экономия в %
    priority: str  # 'high', 'medium', 'low'


@dataclass
class PurchaseRecommendation:
    """Рекомендация по закупке."""

    item_name: str
    recommended_supplier: str
    recommended_price: float
    market_price: float
    savings_percent: float
    optimal_quantity: Optional[int]
    best_timing: str  # 'immediate', 'wait_for_discount', 'seasonal_optimal'
    contract_type: str  # 'spot', 'short_term', 'long_term'
    confidence_score: float
    reasoning: list[str]
    alternatives: list[dict[str, Any]]


@dataclass
class MarketOpportunity:
    """Рыночная возможность."""

    opportunity_type: str  # 'price_drop', 'new_supplier', 'market_consolidation', 'seasonal'
    item_name: str
    description: str
    potential_savings: float
    time_sensitivity: str  # 'urgent', 'moderate', 'flexible'
    required_actions: list[str]
    risk_level: str  # 'low', 'medium', 'high'
    confidence_score: float


@dataclass
class OptimizationRecommendation:
    """Рекомендация по оптимизации закупок."""

    category: str  # 'supplier_consolidation', 'contract_optimization', 'timing_optimization'
    title: str
    description: str
    impact_assessment: dict[str, float]  # cost_savings, risk_reduction, efficiency_gain
    implementation_steps: list[str]
    timeline: str
    resources_required: list[str]
    success_metrics: list[str]
    priority_score: float


@dataclass
class RiskAlert:
    """Предупреждение о рисках."""

    risk_type: str  # 'supplier_dependency', 'price_volatility', 'quality_decline', 'delivery_risk'
    severity: str  # 'low', 'medium', 'high', 'critical'
    affected_items: list[str]
    affected_suppliers: list[str]
    description: str
    potential_impact: str
    mitigation_strategies: list[str]
    monitoring_recommendations: list[str]


class RecommendationEngine:
    """Основной класс для генерации рекомендаций."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.analytics_engine = AnalyticsEngine(db_path)
        self.price_engine = PriceAnalyticsEngine(db_path)

    def _get_db_connection(self) -> sqlite3.Connection:
        """Получить соединение с базой данных."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def score_suppliers(
        self,
        proposals: list[CommercialProposal],
        weights: Optional[dict[str, float]] = None,
    ) -> list[dict[str, Any]]:
        """Оценить поставщиков по многокритериальному анализу.

        Args:
            proposals: Список коммерческих предложений
            weights: Веса критериев (price, delivery, rating). По умолчанию: {'price': 0.5, 'delivery': 0.3, 'rating': 0.2}

        Returns:
            Список оцененных поставщиков с деталями оценки
        """
        if not proposals:
            return []

        if weights is None:
            weights = {"price": 0.5, "delivery": 0.3, "rating": 0.2}

        # Нормализуем веса
        total_weight = sum(weights.values())
        weights = {k: v / total_weight for k, v in weights.items()}

        scored_suppliers = []

        # Определяем опорную цену (средняя цена по всем предложениям)
        prices = [p.total_amount for p in proposals]
        reference_price = sum(prices) / len(prices) if prices else 1000.0

        for proposal in proposals:
            price = float(proposal.total_amount)
            delivery_days = proposal.delivery_terms.delivery_period_days
            rating = float(proposal.supplier.rating or 3.0)

            # Рассчитываем оценки по каждому критерию
            price_score = self._calculate_price_score(price, reference_price)
            delivery_score = self._calculate_delivery_score(delivery_days)
            rating_score = self._calculate_rating_score(rating)

            # Итоговая взвешенная оценка
            total_score = (
                price_score * weights["price"]
                + delivery_score * weights["delivery"]
                + rating_score * weights["rating"]
            )

            scored_suppliers.append(
                {
                    "supplier_id": proposal.supplier.inn,
                    "supplier_name": proposal.supplier.name,
                    "score": round(total_score, 2),
                    "price_score": round(price_score, 2),
                    "delivery_score": round(delivery_score, 2),
                    "rating_score": round(rating_score, 2),
                    "price": price,
                    "delivery_days": delivery_days,
                    "rating": rating,
                    "price_vs_reference": round((price / reference_price - 1) * 100, 2),
                    "proposal": proposal,
                }
            )

        return scored_suppliers

    def select_top_suppliers(
        self, scored_suppliers: list[dict[str, Any]], n: int = 3
    ) -> list[dict[str, Any]]:
        """Выбрать топ-N поставщиков по оценке.

        Args:
            scored_suppliers: Список оцененных поставщиков
            n: Количество поставщиков для выбора

        Returns:
            Топ-N поставщиков, отсортированных по убыванию оценки
        """
        if not scored_suppliers:
            return []

        # Сортируем по убыванию оценки
        sorted_suppliers = sorted(
            scored_suppliers, key=lambda x: x["score"], reverse=True
        )

        # Возвращаем топ-N или все доступные
        return sorted_suppliers[: min(n, len(sorted_suppliers))]

    def generate_supplier_recommendations(
        self, item_name: Optional[str] = None, min_confidence: float = 60.0
    ) -> list[SupplierRecommendation]:
        """Генерация рекомендаций по поставщикам."""
        conn = self._get_db_connection()

        # Получаем данные о поставщиках
        query = """
            SELECT
                s.supplier_id,
                s.name,
                s.overall_rating,
                s.cooperation_status,
                s.risk_level,
                spm.total_orders,
                spm.total_amount,
                spm.avg_delivery_time,
                spm.quality_rating,
                spm.price_competitiveness,
                spm.reliability_score,
                spm.complaints_count
            FROM suppliers s
            LEFT JOIN supplier_performance_metrics spm ON s.supplier_id = spm.supplier_id
            WHERE s.cooperation_status IN ('активный', 'потенциальный')
        """

        cursor = conn.execute(query)
        suppliers_data = cursor.fetchall()
        conn.close()

        recommendations = []

        for supplier in suppliers_data:
            # Анализируем каждого поставщика
            supplier_id = supplier["supplier_id"]
            supplier_name = supplier["name"]

            # Рассчитываем общий скор поставщика
            scores = self._calculate_supplier_scores(supplier)
            overall_score = scores["overall_score"]

            if overall_score < min_confidence:
                continue

            # Определяем тип рекомендации
            recommendation_type = self._determine_recommendation_type(scores, supplier)

            # Генерируем причины и преимущества
            reasons, advantages, risk_factors = self._analyze_supplier_factors(
                supplier, scores
            )

            # Предлагаем действия
            suggested_actions = self._generate_supplier_actions(
                recommendation_type, supplier, scores
            )

            # Оценка потенциальной экономии
            estimated_savings = self._estimate_supplier_savings(supplier_id, item_name)

            # Определяем приоритет
            priority = self._determine_priority(
                overall_score, estimated_savings, supplier
            )

            recommendation = SupplierRecommendation(
                supplier_id=supplier_id,
                supplier_name=supplier_name,
                recommendation_type=recommendation_type,
                confidence_score=round(overall_score, 2),
                reasons=reasons,
                risk_factors=risk_factors,
                advantages=advantages,
                suggested_actions=suggested_actions,
                estimated_savings=estimated_savings,
                priority=priority,
            )

            recommendations.append(recommendation)

        # Сортируем по приоритету и скору
        priority_order = {"high": 3, "medium": 2, "low": 1}
        recommendations.sort(
            key=lambda x: (priority_order.get(x.priority, 0), x.confidence_score),
            reverse=True,
        )

        return recommendations

    def _calculate_price_score(self, price: float, reference_price: float) -> float:
        """Рассчитать оценку за цену (0-10 баллов)."""
        if reference_price <= 0:
            return 5.0

        price_ratio = price / reference_price

        # Логика оценки цены
        if price_ratio <= 0.8:  # Цена на 20% ниже рыночной
            return 10.0
        elif price_ratio <= 1.0:  # Цена до рыночной
            return 8.0 + (1.0 - price_ratio) * 10.0
        elif price_ratio <= 1.2:  # Цена до 20% выше рыночной
            return 6.0 - (price_ratio - 1.0) * 10.0
        else:  # Цена более чем на 20% выше рыночной
            return max(0.0, 4.0 - (price_ratio - 1.2) * 5.0)

    def _calculate_delivery_score(self, delivery_days: int) -> float:
        """Рассчитать оценку за сроки поставки (0-10 баллов)."""
        if delivery_days <= 3:
            return 10.0
        elif delivery_days <= 7:
            return 8.5 - (delivery_days - 3) * 0.375
        elif delivery_days <= 14:
            return 6.5 - (delivery_days - 7) * 0.357
        elif delivery_days <= 30:
            return 4.0 - (delivery_days - 14) * 0.214
        else:
            return max(0.0, 1.5 - (delivery_days - 30) * 0.05)

    def _calculate_rating_score(self, rating: float) -> float:
        """Рассчитать оценку за рейтинг поставщика (0-10 баллов)."""
        return min(10.0, rating * 2.0)

    def _calculate_supplier_scores(self, supplier: sqlite3.Row) -> dict[str, float]:
        """Рассчитать различные скоры для поставщика."""
        # Базовые метрики
        overall_rating = float(supplier["overall_rating"] or 0)
        quality_rating = float(supplier["quality_rating"] or 0)
        price_competitiveness = float(supplier["price_competitiveness"] or 0)
        reliability_score = float(supplier["reliability_score"] or 0)

        # Нормализуем метрики к шкале 0-100
        rating_score = (overall_rating / 5.0) * 100 if overall_rating > 0 else 50
        quality_score = (quality_rating / 5.0) * 100 if quality_rating > 0 else 50
        price_score = price_competitiveness if price_competitiveness > 0 else 50
        reliability_score_norm = reliability_score if reliability_score > 0 else 50

        # Учитываем объем сотрудничества
        total_orders = int(supplier["total_orders"] or 0)
        total_amount = float(supplier["total_amount"] or 0)

        experience_score = min(100, (total_orders * 2) + (total_amount / 10000))

        # Штрафы за жалобы
        complaints = int(supplier["complaints_count"] or 0)
        complaint_penalty = min(30, complaints * 5)

        # Риск-фактор
        risk_level = supplier["risk_level"] or "средний"
        risk_penalty = {"низкий": 0, "средний": 10, "высокий": 25}.get(risk_level, 15)

        # Итоговый скор
        overall_score = (
            (
                rating_score * 0.25
                + quality_score * 0.25
                + price_score * 0.20
                + reliability_score_norm * 0.20
                + experience_score * 0.10
            )
            - complaint_penalty
            - risk_penalty
        )

        overall_score = max(0, min(100, overall_score))

        return {
            "overall_score": overall_score,
            "rating_score": rating_score,
            "quality_score": quality_score,
            "price_score": price_score,
            "reliability_score": reliability_score_norm,
            "experience_score": experience_score,
            "complaint_penalty": complaint_penalty,
            "risk_penalty": risk_penalty,
        }

    def _determine_recommendation_type(
        self, scores: dict[str, float], supplier: sqlite3.Row
    ) -> str:
        """Определить тип рекомендации для поставщика."""
        overall_score = scores["overall_score"]
        cooperation_status = supplier["cooperation_status"]

        if overall_score >= 80:
            return "preferred"
        elif overall_score >= 60:
            if cooperation_status == "потенциальный":
                return "new_opportunity"
            else:
                return "alternative"
        else:
            return "avoid"

    def _analyze_supplier_factors(
        self, supplier: sqlite3.Row, scores: dict[str, float]
    ) -> tuple[list[str], list[str], list[str]]:
        """Анализ факторов поставщика."""
        reasons = []
        advantages = []
        risk_factors = []

        # Анализируем сильные стороны
        if scores["quality_score"] >= 80:
            advantages.append("Высокое качество продукции/услуг")
            reasons.append("Отличные показатели качества")

        if scores["price_score"] >= 75:
            advantages.append("Конкурентоспособные цены")
            reasons.append("Привлекательное ценообразование")

        if scores["reliability_score"] >= 80:
            advantages.append("Высокая надежность поставок")
            reasons.append("Стабильность выполнения обязательств")

        if scores["experience_score"] >= 70:
            advantages.append("Большой опыт сотрудничества")
            reasons.append("Проверенный партнер с историей сотрудничества")

        # Анализируем риски
        if scores["complaint_penalty"] > 15:
            risk_factors.append("Повышенное количество жалоб")

        if scores["risk_penalty"] > 15:
            risk_factors.append("Высокий уровень риска")

        if supplier["cooperation_status"] == "потенциальный":
            risk_factors.append("Отсутствие опыта сотрудничества")

        delivery_time = float(supplier["avg_delivery_time"] or 0)
        if delivery_time > 14:
            risk_factors.append("Длительные сроки поставки")

        # Базовые причины, если нет специфических
        if not reasons:
            if scores["overall_score"] >= 70:
                reasons.append("Соответствует основным требованиям")
            else:
                reasons.append("Требует дополнительного анализа")

        return reasons, advantages, risk_factors

    def _generate_supplier_actions(
        self, recommendation_type: str, supplier: sqlite3.Row, scores: dict[str, float]
    ) -> list[str]:
        """Генерация предлагаемых действий для поставщика."""
        actions = []

        if recommendation_type == "preferred":
            actions.extend(
                [
                    "Рассмотреть заключение долгосрочного контракта",
                    "Увеличить объем закупок",
                    "Обсудить дополнительные скидки за объем",
                ]
            )

        elif recommendation_type == "alternative":
            actions.extend(
                [
                    "Использовать как альтернативного поставщика",
                    "Мониторить показатели качества",
                    "Рассмотреть пилотные закупки",
                ]
            )

        elif recommendation_type == "new_opportunity":
            actions.extend(
                [
                    "Провести тестовую закупку",
                    "Запросить детальное коммерческое предложение",
                    "Проверить репутацию и референсы",
                    "Оценить производственные мощности",
                ]
            )

        elif recommendation_type == "avoid":
            actions.extend(
                [
                    "Минимизировать объем закупок",
                    "Найти альтернативных поставщиков",
                    "Усилить контроль качества",
                ]
            )

        # Специфические действия на основе слабых мест
        if scores["price_score"] < 60:
            actions.append("Провести переговоры о снижении цен")

        if scores["quality_score"] < 70:
            actions.append("Ужесточить требования к качеству")

        if scores["complaint_penalty"] > 10:
            actions.append("Разработать план улучшения сервиса")

        return actions

    def _estimate_supplier_savings(
        self, supplier_id: str, item_name: Optional[str] = None
    ) -> Optional[float]:
        """Оценка потенциальной экономии от поставщика."""
        try:
            supplier_profile = self.price_engine.analyze_supplier_price_profile(
                supplier_id
            )
            return max(0, supplier_profile.competitive_advantage)
        except:
            return None

    def _determine_priority(
        self,
        overall_score: float,
        estimated_savings: Optional[float],
        supplier: sqlite3.Row,
    ) -> str:
        """Определение приоритета рекомендации."""
        priority_score = overall_score

        if estimated_savings and estimated_savings > 10:
            priority_score += 15

        total_amount = float(supplier["total_amount"] or 0)
        if total_amount > 100000:
            priority_score += 10

        if priority_score >= 85:
            return "high"
        elif priority_score >= 65:
            return "medium"
        else:
            return "low"

    def generate_purchase_recommendations(
        self, item_name: str
    ) -> list[PurchaseRecommendation]:
        """Генерация рекомендаций по закупке конкретного товара."""
        # Анализируем рынок для товара
        market_analysis = self.price_engine.analyze_market_for_item(item_name)

        if not market_analysis.competitive_suppliers:
            return []

        # Сравниваем поставщиков
        supplier_comparison = self.price_engine.compare_suppliers_for_item(item_name)

        if not supplier_comparison["comparison_available"]:
            return []

        recommendations = []

        for supplier_data in supplier_comparison["supplier_comparison"][
            :3
        ]:  # Топ-3 поставщика
            # Определяем оптимальное время закупки
            timing = self._determine_optimal_timing(item_name, supplier_data)

            # Определяем тип контракта
            contract_type = self._recommend_contract_type(
                supplier_data, market_analysis
            )

            # Рассчитываем экономию
            savings_percent = max(0, -supplier_data["price_vs_market"])

            # Генерируем обоснование
            reasoning = self._generate_purchase_reasoning(
                supplier_data, market_analysis, timing
            )

            # Альтернативы
            alternatives = self._generate_alternatives(
                supplier_comparison["supplier_comparison"], supplier_data["supplier_id"]
            )

            recommendation = PurchaseRecommendation(
                item_name=item_name,
                recommended_supplier=supplier_data["supplier_name"],
                recommended_price=supplier_data["price"],
                market_price=market_analysis.market_avg_price,
                savings_percent=round(savings_percent, 2),
                optimal_quantity=self._calculate_optimal_quantity(
                    item_name, supplier_data
                ),
                best_timing=timing,
                contract_type=contract_type,
                confidence_score=supplier_data["overall_score"],
                reasoning=reasoning,
                alternatives=alternatives,
            )

            recommendations.append(recommendation)

        return recommendations

    def _determine_optimal_timing(self, item_name: str, supplier_data: dict) -> str:
        """Определение оптимального времени закупки."""
        # Анализируем тренды цен
        trends = self.price_engine.analyze_price_trends(
            item_name=item_name, supplier_id=supplier_data["supplier_id"]
        )

        if trends:
            trend = trends[0]
            if trend.trend_direction == "down":
                return "wait_for_discount"
            elif trend.trend_direction == "up" and trend.trend_percentage > 10:
                return "immediate"

        # Проверяем сезонность (упрощенная логика)
        current_month = datetime.now().month
        if item_name.lower() in [
            "отопление",
            "зимняя",
            "обогрев",
        ] and current_month in [3, 4, 5]:
            return "seasonal_optimal"

        return "immediate"

    def _recommend_contract_type(
        self, supplier_data: dict, market_analysis: MarketAnalysis
    ) -> str:
        """Рекомендация типа контракта."""
        stability_score = supplier_data.get("stability_score", 50)
        price_volatility = (
            market_analysis.price_std_deviation / market_analysis.market_avg_price * 100
        )

        if stability_score >= 80 and price_volatility < 10:
            return "long_term"
        elif stability_score >= 60 and price_volatility < 20:
            return "short_term"
        else:
            return "spot"

    def _generate_purchase_reasoning(
        self, supplier_data: dict, market_analysis: MarketAnalysis, timing: str
    ) -> list[str]:
        """Генерация обоснования рекомендации по закупке."""
        reasoning = []

        if supplier_data["price"] < market_analysis.market_avg_price:
            savings = (
                (market_analysis.market_avg_price - supplier_data["price"])
                / market_analysis.market_avg_price
                * 100
            )
            reasoning.append(f"Цена на {savings:.1f}% ниже среднерыночной")

        if supplier_data["overall_score"] >= 80:
            reasoning.append("Высокий общий рейтинг поставщика")

        if supplier_data["stability_score"] >= 75:
            reasoning.append("Стабильные цены и надежность поставок")

        if timing == "immediate":
            reasoning.append("Рекомендуется немедленная закупка из-за роста цен")
        elif timing == "wait_for_discount":
            reasoning.append("Возможно дождаться дальнейшего снижения цен")
        elif timing == "seasonal_optimal":
            reasoning.append("Оптимальное время для сезонной закупки")

        return reasoning

    def _generate_alternatives(
        self, all_suppliers: list[dict], current_supplier_id: str
    ) -> list[dict[str, Any]]:
        """Генерация альтернативных вариантов."""
        alternatives = []

        for supplier in all_suppliers:
            if supplier["supplier_id"] != current_supplier_id:
                alternatives.append(
                    {
                        "supplier_name": supplier["supplier_name"],
                        "price": supplier["price"],
                        "overall_score": supplier["overall_score"],
                        "price_difference": supplier["price"]
                        - all_suppliers[0]["price"],
                    }
                )

        return alternatives[:2]  # Максимум 2 альтернативы

    def _calculate_optimal_quantity(
        self, item_name: str, supplier_data: dict
    ) -> Optional[int]:
        """Расчет оптимального количества для закупки."""
        # Упрощенная логика на основе исторических данных
        conn = self._get_db_connection()

        query = """
            SELECT AVG(amount) as avg_amount
            FROM supplier_transactions
            WHERE supplier_id = ? AND status = 'выполнена'
            AND transaction_date >= ?
        """

        month_ago = (datetime.now() - timedelta(days=30)).isoformat()
        cursor = conn.execute(query, (supplier_data["supplier_id"], month_ago))
        result = cursor.fetchone()
        conn.close()

        if result and result["avg_amount"]:
            # Предполагаем, что количество пропорционально сумме
            avg_amount = float(result["avg_amount"])
            estimated_quantity = int(avg_amount / supplier_data["price"])
            return max(1, estimated_quantity)

        return None

    def identify_market_opportunities(self) -> list[MarketOpportunity]:
        """Выявление рыночных возможностей."""
        opportunities = []

        # Анализируем ценовые тренды для выявления возможностей
        trends = self.price_engine.analyze_price_trends(days_back=30)

        for trend in trends:
            # Возможность при снижении цен
            if trend.trend_direction == "down" and trend.trend_percentage < -15:
                opportunity = MarketOpportunity(
                    opportunity_type="price_drop",
                    item_name=trend.item_name,
                    description=f"Значительное снижение цены на {abs(trend.trend_percentage):.1f}% у поставщика {trend.supplier_name}",
                    potential_savings=abs(trend.trend_percentage),
                    time_sensitivity="moderate",
                    required_actions=[
                        "Увеличить объем закупки",
                        "Рассмотреть заключение краткосрочного контракта",
                        "Проверить причины снижения цены",
                    ],
                    risk_level="low",
                    confidence_score=min(90, 70 + abs(trend.trend_percentage)),
                )
                opportunities.append(opportunity)

        # Выявляем новых поставщиков
        new_suppliers = self._identify_new_suppliers()
        for supplier_info in new_suppliers:
            opportunity = MarketOpportunity(
                opportunity_type="new_supplier",
                item_name="различные товары",
                description=f"Новый поставщик {supplier_info['name']} с потенциально выгодными условиями",
                potential_savings=supplier_info.get("estimated_savings", 5.0),
                time_sensitivity="flexible",
                required_actions=[
                    "Провести анализ предложений",
                    "Запросить коммерческие предложения",
                    "Оценить надежность поставщика",
                ],
                risk_level="medium",
                confidence_score=60.0,
            )
            opportunities.append(opportunity)

        # Сезонные возможности
        seasonal_opportunities = self._identify_seasonal_opportunities()
        opportunities.extend(seasonal_opportunities)

        return sorted(opportunities, key=lambda x: x.confidence_score, reverse=True)

    def _identify_new_suppliers(self) -> list[dict]:
        """Выявление новых поставщиков."""
        conn = self._get_db_connection()

        # Поставщики, добавленные за последний месяц
        month_ago = (datetime.now() - timedelta(days=30)).isoformat()
        query = """
            SELECT supplier_id, name, overall_rating
            FROM suppliers
            WHERE created_at >= ? AND cooperation_status = 'потенциальный'
            ORDER BY overall_rating DESC
        """

        cursor = conn.execute(query, (month_ago,))
        new_suppliers = cursor.fetchall()
        conn.close()

        return [
            {
                "supplier_id": row["supplier_id"],
                "name": row["name"],
                "estimated_savings": min(
                    15, max(5, float(row["overall_rating"] or 0) * 2)
                ),
            }
            for row in new_suppliers
        ]

    def _identify_seasonal_opportunities(self) -> list[MarketOpportunity]:
        """Выявление сезонных возможностей."""
        opportunities = []
        current_month = datetime.now().month

        # Примеры сезонных возможностей
        seasonal_items = {
            "зимние товары": {"months": [9, 10, 11], "savings": 20},
            "летние товары": {"months": [2, 3, 4], "savings": 15},
            "офисные принадлежности": {"months": [7, 8], "savings": 10},
            "строительные материалы": {"months": [3, 4, 5], "savings": 12},
        }

        for item_category, info in seasonal_items.items():
            if current_month in info["months"]:
                opportunity = MarketOpportunity(
                    opportunity_type="seasonal",
                    item_name=item_category,
                    description=f"Сезонная возможность для закупки {item_category} с потенциальной экономией",
                    potential_savings=info["savings"],
                    time_sensitivity="moderate",
                    required_actions=[
                        "Запланировать сезонные закупки",
                        "Согласовать объемы с поставщиками",
                        "Подготовить складские мощности",
                    ],
                    risk_level="low",
                    confidence_score=75.0,
                )
                opportunities.append(opportunity)

        return opportunities

    def generate_optimization_recommendations(self) -> list[OptimizationRecommendation]:
        """Генерация рекомендаций по оптимизации закупок."""
        recommendations = []

        # Анализ консолидации поставщиков
        consolidation_rec = self._analyze_supplier_consolidation()
        if consolidation_rec:
            recommendations.append(consolidation_rec)

        # Оптимизация контрактов
        contract_rec = self._analyze_contract_optimization()
        if contract_rec:
            recommendations.append(contract_rec)

        # Оптимизация времени закупок
        timing_rec = self._analyze_timing_optimization()
        if timing_rec:
            recommendations.append(timing_rec)

        return sorted(recommendations, key=lambda x: x.priority_score, reverse=True)

    def _analyze_supplier_consolidation(self) -> Optional[OptimizationRecommendation]:
        """Анализ возможности консолидации поставщиков."""
        conn = self._get_db_connection()

        # Подсчитываем количество поставщиков по категориям
        query = """
            SELECT COUNT(DISTINCT supplier_id) as supplier_count
            FROM supplier_transactions
            WHERE status = 'выполнена'
            AND transaction_date >= ?
        """

        month_ago = (datetime.now() - timedelta(days=90)).isoformat()
        cursor = conn.execute(query, (month_ago,))
        result = cursor.fetchone()
        conn.close()

        supplier_count = result["supplier_count"] if result else 0

        if supplier_count > 10:  # Если много поставщиков
            return OptimizationRecommendation(
                category="supplier_consolidation",
                title="Консолидация поставщиков",
                description=f"Выявлено {supplier_count} активных поставщиков. Рекомендуется консолидация для снижения затрат на управление.",
                impact_assessment={
                    "cost_savings": 15.0,
                    "risk_reduction": 10.0,
                    "efficiency_gain": 25.0,
                },
                implementation_steps=[
                    "Провести анализ поставщиков по категориям товаров",
                    "Выбрать топ-поставщиков для каждой категории",
                    "Провести переговоры о расширении ассортимента",
                    "Постепенно сократить количество мелких поставщиков",
                ],
                timeline="3-6 месяцев",
                resources_required=["Аналитик по закупкам", "Менеджер по переговорам"],
                success_metrics=[
                    "Сокращение количества поставщиков на 30%",
                    "Снижение административных затрат на 20%",
                    "Увеличение объема скидок",
                ],
                priority_score=85.0,
            )

        return None

    def _analyze_contract_optimization(self) -> Optional[OptimizationRecommendation]:
        """Анализ оптимизации контрактов."""
        # Упрощенный анализ - в реальности здесь был бы более сложный алгоритм
        return OptimizationRecommendation(
            category="contract_optimization",
            title="Оптимизация контрактных условий",
            description="Анализ показывает возможности улучшения условий существующих контрактов",
            impact_assessment={
                "cost_savings": 12.0,
                "risk_reduction": 15.0,
                "efficiency_gain": 20.0,
            },
            implementation_steps=[
                "Провести аудит действующих контрактов",
                "Выявить контракты с неоптимальными условиями",
                "Подготовить предложения по изменению условий",
                "Провести переговоры с ключевыми поставщиками",
            ],
            timeline="2-4 месяца",
            resources_required=["Юрист", "Менеджер по закупкам"],
            success_metrics=[
                "Улучшение условий в 70% контрактов",
                "Снижение средней цены на 8-15%",
                "Улучшение условий оплаты",
            ],
            priority_score=75.0,
        )

    def _analyze_timing_optimization(self) -> Optional[OptimizationRecommendation]:
        """Анализ оптимизации времени закупок."""
        return OptimizationRecommendation(
            category="timing_optimization",
            title="Оптимизация времени закупок",
            description="Анализ сезонных трендов показывает возможности экономии при правильном планировании закупок",
            impact_assessment={
                "cost_savings": 8.0,
                "risk_reduction": 5.0,
                "efficiency_gain": 15.0,
            },
            implementation_steps=[
                "Создать календарь сезонных закупок",
                "Внедрить систему прогнозирования потребности",
                "Настроить автоматические уведомления о оптимальном времени закупок",
                "Обучить команду принципам сезонного планирования",
            ],
            timeline="1-3 месяца",
            resources_required=["Аналитик", "Система планирования"],
            success_metrics=[
                "Снижение средней цены закупок на 5-10%",
                "Сокращение срочных закупок на 40%",
                "Улучшение планирования на 6 месяцев вперед",
            ],
            priority_score=70.0,
        )

    def generate_comprehensive_recommendations(self) -> dict[str, Any]:
        """Генерация комплексных рекомендаций."""
        return {
            "supplier_recommendations": self.generate_supplier_recommendations(),
            "market_opportunities": self.identify_market_opportunities(),
            "optimization_recommendations": self.generate_optimization_recommendations(),
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_recommendations": 0,  # Будет рассчитано
                "high_priority_items": 0,
                "potential_savings_percent": 0.0,
            },
        }


# Утилитарные функции


def get_supplier_recommendations(
    item_name: Optional[str] = None
) -> list[SupplierRecommendation]:
    """Получить рекомендации по поставщикам."""
    engine = RecommendationEngine()
    return engine.generate_supplier_recommendations(item_name=item_name)


def get_purchase_recommendations(item_name: str) -> list[PurchaseRecommendation]:
    """Получить рекомендации по закупке товара."""
    engine = RecommendationEngine()
    return engine.generate_purchase_recommendations(item_name)


def get_market_opportunities() -> list[MarketOpportunity]:
    """Получить рыночные возможности."""
    engine = RecommendationEngine()
    return engine.identify_market_opportunities()


def get_optimization_recommendations() -> list[OptimizationRecommendation]:
    """Получить рекомендации по оптимизации."""
    engine = RecommendationEngine()
    return engine.generate_optimization_recommendations()


if __name__ == "__main__":
    # Пример использования
    engine = RecommendationEngine()

    print("=== Рекомендации по поставщикам ===")
    supplier_recs = engine.generate_supplier_recommendations()
    for rec in supplier_recs[:3]:
        print(
            f"{rec.supplier_name}: {rec.recommendation_type} (скор: {rec.confidence_score})"
        )
        print(f"  Преимущества: {', '.join(rec.advantages[:2])}")

    print("\n=== Рыночные возможности ===")
    opportunities = engine.identify_market_opportunities()
    for opp in opportunities[:3]:
        print(f"{opp.opportunity_type}: {opp.description}")
        print(f"  Потенциальная экономия: {opp.potential_savings}%")

    print("\n=== Рекомендации по оптимизации ===")
    optimizations = engine.generate_optimization_recommendations()
    for opt in optimizations:
        print(f"{opt.title}: {opt.description}")
        print(f"  Экономия: {opt.impact_assessment['cost_savings']}%")
