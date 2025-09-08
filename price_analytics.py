"""Модуль анализа ценовых тенденций и сравнения предложений поставщиков."""

import math
import sqlite3
import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional

from db import DB_PATH
from src.models import PriceRecord


@dataclass
class PriceTrend:
    """Тренд изменения цены для товара/услуги."""

    item_name: str
    supplier_id: str
    supplier_name: str
    price_history: list[tuple[datetime, float]]  # (дата, цена)
    trend_direction: str  # 'up', 'down', 'stable'
    trend_percentage: float  # процент изменения
    volatility_score: float  # 0-100, волатильность цен
    last_price: float
    avg_price: float
    min_price: float
    max_price: float


@dataclass
class MarketAnalysis:
    """Анализ рынка для конкретного товара/услуги."""

    item_name: str
    total_suppliers: int
    price_range: tuple[float, float]  # (мин, макс)
    market_avg_price: float
    market_median_price: float
    price_std_deviation: float
    competitive_suppliers: list[dict]  # топ поставщики по цене
    price_outliers: list[dict]  # аномально высокие/низкие цены
    market_concentration: float  # индекс концентрации рынка


@dataclass
class PriceAlert:
    """Ценовое предупреждение."""

    alert_type: str  # 'price_spike', 'price_drop', 'new_competitor', 'market_shift'
    severity: str  # 'low', 'medium', 'high', 'critical'
    item_name: str
    supplier_id: str
    supplier_name: str
    current_price: float
    reference_price: float
    price_change_percent: float
    description: str
    created_at: datetime
    recommendations: list[str]


@dataclass
class SupplierPriceProfile:
    """Ценовой профиль поставщика."""

    supplier_id: str
    supplier_name: str
    avg_price_position: str  # 'low', 'medium', 'high'
    price_stability_score: float  # 0-100
    competitive_advantage: float  # процент ниже среднерыночной
    price_update_frequency: float  # дней между обновлениями
    total_items: int
    items_below_market: int
    items_above_market: int
    risk_score: float  # 0-100, риск ценовых изменений


@dataclass
class SeasonalAnalysis:
    """Сезонный анализ цен."""

    item_name: str
    seasonal_patterns: dict[str, float]  # месяц -> средняя цена
    peak_season: str
    low_season: str
    seasonal_volatility: float
    year_over_year_change: float
    predicted_next_month: float


class PriceAnalyticsEngine:
    """Основной класс для анализа ценовых данных."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def _get_db_connection(self) -> sqlite3.Connection:
        """Получить соединение с базой данных."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def analyze_price_trends(
        self,
        item_name: Optional[str] = None,
        supplier_id: Optional[str] = None,
        days_back: int = 90,
    ) -> list[PriceTrend]:
        """Анализ ценовых трендов."""
        conn = self._get_db_connection()

        # Базовый запрос для получения истории цен
        query = """
            SELECT
                ph.product_name as item_name,
                ph.supplier_id,
                s.name as supplier_name,
                ph.price,
                ph.created_at as recorded_at
            FROM price_history ph
            JOIN suppliers s ON ph.supplier_id = s.supplier_id
            WHERE ph.created_at >= ?
        """

        params = [(datetime.now() - timedelta(days=days_back)).isoformat()]

        if item_name:
            query += " AND ph.product_name = ?"
            params.append(item_name)

        if supplier_id:
            query += " AND ph.supplier_id = ?"
            params.append(supplier_id)

        query += " ORDER BY ph.product_name, ph.supplier_id, ph.created_at"

        cursor = conn.execute(query, params)
        price_data = cursor.fetchall()
        conn.close()

        # Группируем данные по товару и поставщику
        grouped_data = defaultdict(list)
        for row in price_data:
            key = (row["item_name"], row["supplier_id"], row["supplier_name"])
            grouped_data[key].append(
                {
                    "date": datetime.fromisoformat(row["recorded_at"]),
                    "price": float(row["price"]),
                }
            )

        trends = []
        for (item, supplier_id, supplier_name), price_points in grouped_data.items():
            if len(price_points) < 2:
                continue

            # Сортируем по дате
            price_points.sort(key=lambda x: x["date"])

            # Извлекаем цены и даты
            prices = [p["price"] for p in price_points]
            dates = [p["date"] for p in price_points]
            price_history = [(d, p) for d, p in zip(dates, prices)]

            # Анализируем тренд
            first_price = prices[0]
            last_price = prices[-1]
            avg_price = statistics.mean(prices)
            min_price = min(prices)
            max_price = max(prices)

            # Определяем направление тренда
            trend_percentage = ((last_price - first_price) / first_price) * 100

            if trend_percentage > 5:
                trend_direction = "up"
            elif trend_percentage < -5:
                trend_direction = "down"
            else:
                trend_direction = "stable"

            # Рассчитываем волатильность
            if len(prices) > 1:
                price_changes = [
                    abs(prices[i] - prices[i - 1]) / prices[i - 1] * 100
                    for i in range(1, len(prices))
                ]
                volatility_score = (
                    statistics.mean(price_changes) if price_changes else 0
                )
            else:
                volatility_score = 0

            trend = PriceTrend(
                item_name=item,
                supplier_id=supplier_id,
                supplier_name=supplier_name,
                price_history=price_history,
                trend_direction=trend_direction,
                trend_percentage=round(trend_percentage, 2),
                volatility_score=round(min(100, volatility_score), 2),
                last_price=last_price,
                avg_price=round(avg_price, 2),
                min_price=min_price,
                max_price=max_price,
            )
            trends.append(trend)

        return trends

    def analyze_market_for_item(self, item_name: str) -> MarketAnalysis:
        """Анализ рынка для конкретного товара."""
        conn = self._get_db_connection()

        # Получаем последние цены от всех поставщиков для данного товара
        query = """
            SELECT
                ph.supplier_id,
                s.name as supplier_name,
                ph.price,
                ph.created_at as recorded_at
            FROM price_history ph
            JOIN suppliers s ON ph.supplier_id = s.supplier_id
            WHERE ph.product_name = ?
            AND ph.created_at = (
                SELECT MAX(created_at)
                FROM price_history ph2
                WHERE ph2.supplier_id = ph.supplier_id
                AND ph2.product_name = ph.product_name
            )
            ORDER BY ph.price
        """

        cursor = conn.execute(query, (item_name,))
        market_data = cursor.fetchall()
        conn.close()

        if not market_data:
            return MarketAnalysis(
                item_name=item_name,
                total_suppliers=0,
                price_range=(0, 0),
                market_avg_price=0,
                market_median_price=0,
                price_std_deviation=0,
                competitive_suppliers=[],
                price_outliers=[],
                market_concentration=0,
            )

        prices = [float(row["price"]) for row in market_data]
        suppliers_data = [
            {
                "supplier_id": row["supplier_id"],
                "supplier_name": row["supplier_name"],
                "price": float(row["price"]),
                "recorded_at": row["recorded_at"],
            }
            for row in market_data
        ]

        # Основная статистика
        total_suppliers = len(market_data)
        price_range = (min(prices), max(prices))
        market_avg = statistics.mean(prices)
        market_median = statistics.median(prices)
        price_std = statistics.stdev(prices) if len(prices) > 1 else 0

        # Топ конкурентных поставщиков (самые низкие цены)
        competitive_suppliers = sorted(suppliers_data, key=lambda x: x["price"])[:5]

        # Выявляем аномалии (цены выше/ниже 2 стандартных отклонений)
        outliers = []
        if price_std > 0:
            for supplier in suppliers_data:
                z_score = abs(supplier["price"] - market_avg) / price_std
                if z_score > 2:
                    outlier_type = "high" if supplier["price"] > market_avg else "low"
                    outliers.append(
                        {
                            **supplier,
                            "outlier_type": outlier_type,
                            "z_score": round(z_score, 2),
                        }
                    )

        # Индекс концентрации рынка (упрощенный)
        # Доля топ-3 поставщиков в общем объеме
        if total_suppliers >= 3:
            market_concentration = 3 / total_suppliers * 100
        else:
            market_concentration = 100

        return MarketAnalysis(
            item_name=item_name,
            total_suppliers=total_suppliers,
            price_range=price_range,
            market_avg_price=round(market_avg, 2),
            market_median_price=round(market_median, 2),
            price_std_deviation=round(price_std, 2),
            competitive_suppliers=competitive_suppliers,
            price_outliers=outliers,
            market_concentration=round(market_concentration, 2),
        )

    def generate_price_alerts(
        self, threshold_percent: float = 15.0, days_back: int = 7
    ) -> list[PriceAlert]:
        """Генерация ценовых предупреждений."""
        alerts = []

        # Получаем недавние изменения цен
        trends = self.analyze_price_trends(days_back=days_back)

        for trend in trends:
            alert_type = None
            severity = "low"
            recommendations = []

            # Проверяем резкие изменения цен
            if abs(trend.trend_percentage) >= threshold_percent:
                if trend.trend_percentage > 0:
                    alert_type = "price_spike"
                    severity = "high" if trend.trend_percentage > 30 else "medium"
                    recommendations = [
                        "Проверить обоснованность повышения цены",
                        "Рассмотреть альтернативных поставщиков",
                        "Провести переговоры о цене",
                    ]
                else:
                    alert_type = "price_drop"
                    severity = "medium" if abs(trend.trend_percentage) > 30 else "low"
                    recommendations = [
                        "Воспользоваться выгодным предложением",
                        "Проверить качество товара/услуги",
                        "Рассмотреть увеличение объема закупки",
                    ]

            # Проверяем высокую волатильность
            elif trend.volatility_score > 20:
                alert_type = "market_shift"
                severity = "medium"
                recommendations = [
                    "Мониторить ценовые изменения",
                    "Рассмотреть долгосрочные контракты",
                    "Диверсифицировать поставщиков",
                ]

            if alert_type:
                alert = PriceAlert(
                    alert_type=alert_type,
                    severity=severity,
                    item_name=trend.item_name,
                    supplier_id=trend.supplier_id,
                    supplier_name=trend.supplier_name,
                    current_price=trend.last_price,
                    reference_price=trend.avg_price,
                    price_change_percent=trend.trend_percentage,
                    description=self._generate_alert_description(alert_type, trend),
                    created_at=datetime.now(),
                    recommendations=recommendations,
                )
                alerts.append(alert)

        return sorted(alerts, key=lambda x: x.severity, reverse=True)

    def _generate_alert_description(self, alert_type: str, trend: PriceTrend) -> str:
        """Генерация описания для предупреждения."""
        if alert_type == "price_spike":
            return f"Цена на '{trend.item_name}' от поставщика '{trend.supplier_name}' выросла на {trend.trend_percentage:.1f}%"
        elif alert_type == "price_drop":
            return f"Цена на '{trend.item_name}' от поставщика '{trend.supplier_name}' снизилась на {abs(trend.trend_percentage):.1f}%"
        elif alert_type == "market_shift":
            return f"Высокая волатильность цен на '{trend.item_name}' от поставщика '{trend.supplier_name}' (волатильность: {trend.volatility_score:.1f}%)"
        else:
            return f"Изменение цены на '{trend.item_name}' от поставщика '{trend.supplier_name}'"

    def analyze_supplier_price_profile(self, supplier_id: str) -> SupplierPriceProfile:
        """Анализ ценового профиля поставщика."""
        conn = self._get_db_connection()

        # Получаем информацию о поставщике
        cursor = conn.execute(
            "SELECT name FROM suppliers WHERE supplier_id = ?", (supplier_id,)
        )
        supplier_info = cursor.fetchone()

        if not supplier_info:
            raise ValueError(f"Поставщик с ID {supplier_id} не найден")

        supplier_name = supplier_info["name"]

        # Получаем все товары поставщика с последними ценами
        query = """
            SELECT
                ph.product_name as item_name,
                ph.price,
                ph.created_at as recorded_at
            FROM price_history ph
            WHERE ph.supplier_id = ?
            AND ph.created_at = (
                SELECT MAX(created_at)
                FROM price_history ph2
                WHERE ph2.supplier_id = ph.supplier_id
                AND ph2.product_name = ph.product_name
            )
        """

        cursor = conn.execute(query, (supplier_id,))
        supplier_items = cursor.fetchall()

        total_items = len(supplier_items)
        if total_items == 0:
            conn.close()
            return SupplierPriceProfile(
                supplier_id=supplier_id,
                supplier_name=supplier_name,
                avg_price_position="unknown",
                price_stability_score=0,
                competitive_advantage=0,
                price_update_frequency=0,
                total_items=0,
                items_below_market=0,
                items_above_market=0,
                risk_score=0,
            )

        # Анализируем позицию поставщика относительно рынка
        items_below_market = 0
        items_above_market = 0
        competitive_advantages = []

        for item in supplier_items:
            market_analysis = self.analyze_market_for_item(item["item_name"])

            if market_analysis.market_avg_price > 0:
                supplier_price = float(item["price"])
                market_avg = market_analysis.market_avg_price

                if supplier_price < market_avg:
                    items_below_market += 1
                    advantage = (market_avg - supplier_price) / market_avg * 100
                    competitive_advantages.append(advantage)
                elif supplier_price > market_avg:
                    items_above_market += 1
                    disadvantage = (supplier_price - market_avg) / market_avg * 100
                    competitive_advantages.append(-disadvantage)
                else:
                    competitive_advantages.append(0)

        # Определяем общую ценовую позицию
        if items_below_market > items_above_market:
            avg_price_position = "low"
        elif items_above_market > items_below_market:
            avg_price_position = "high"
        else:
            avg_price_position = "medium"

        # Рассчитываем средний конкурентный показатель
        avg_competitive_advantage = (
            statistics.mean(competitive_advantages) if competitive_advantages else 0
        )

        # Анализируем стабильность цен (на основе истории изменений)
        trends = self.analyze_price_trends(supplier_id=supplier_id, days_back=90)
        volatilities = [trend.volatility_score for trend in trends]
        avg_volatility = statistics.mean(volatilities) if volatilities else 0
        price_stability_score = max(0, 100 - avg_volatility)

        # Частота обновления цен (упрощенная оценка)
        price_update_frequency = 30  # Предполагаем обновление раз в месяц

        # Оценка риска (на основе волатильности и позиции на рынке)
        risk_score = min(
            100, avg_volatility + (20 if avg_price_position == "high" else 0)
        )

        conn.close()

        return SupplierPriceProfile(
            supplier_id=supplier_id,
            supplier_name=supplier_name,
            avg_price_position=avg_price_position,
            price_stability_score=round(price_stability_score, 2),
            competitive_advantage=round(avg_competitive_advantage, 2),
            price_update_frequency=price_update_frequency,
            total_items=total_items,
            items_below_market=items_below_market,
            items_above_market=items_above_market,
            risk_score=round(risk_score, 2),
        )

    def analyze_seasonal_trends(
        self, item_name: str, years_back: int = 2
    ) -> SeasonalAnalysis:
        """Анализ сезонных тенденций цен."""
        conn = self._get_db_connection()

        # Получаем исторические данные за указанное количество лет
        start_date = datetime.now() - timedelta(days=years_back * 365)

        query = """
            SELECT
                ph.price,
                ph.created_at,
                strftime('%m', ph.created_at) as month,
                strftime('%Y', ph.created_at) as year
            FROM price_history ph
            WHERE ph.product_name = ?
            AND ph.created_at >= ?
            ORDER BY ph.created_at
        """

        cursor = conn.execute(query, (item_name, start_date.isoformat()))
        price_data = cursor.fetchall()
        conn.close()

        if not price_data:
            return SeasonalAnalysis(
                item_name=item_name,
                seasonal_patterns={},
                peak_season="",
                low_season="",
                seasonal_volatility=0,
                year_over_year_change=0,
                predicted_next_month=0,
            )

        # Анализируем сезонные паттерны
        monthly_prices = defaultdict(list)
        yearly_averages = defaultdict(list)

        for row in price_data:
            month = int(row["month"])
            year = int(row["year"])
            price = float(row["price"])

            monthly_prices[month].append(price)
            yearly_averages[year].append(price)

        # Средняя цена по месяцам
        seasonal_patterns = {}
        for month in range(1, 13):
            if month in monthly_prices:
                seasonal_patterns[str(month).zfill(2)] = statistics.mean(
                    monthly_prices[month]
                )

        # Определяем пиковый и низкий сезоны
        if seasonal_patterns:
            sorted_months = sorted(seasonal_patterns.items(), key=lambda x: x[1])
            low_season = sorted_months[0][0] if sorted_months else ""
            peak_season = sorted_months[-1][0] if sorted_months else ""
        else:
            low_season = peak_season = ""

        # Рассчитываем сезонную волатильность
        monthly_avg = (
            statistics.mean(seasonal_patterns.values()) if seasonal_patterns else 0
        )
        monthly_variance = (
            statistics.variance(seasonal_patterns.values())
            if len(seasonal_patterns) > 1
            else 0
        )
        seasonal_volatility = (
            (math.sqrt(monthly_variance) / monthly_avg * 100) if monthly_avg > 0 else 0
        )

        # Годовой рост/падение цен
        current_year = datetime.now().year
        previous_year = current_year - 1

        current_avg = statistics.mean(yearly_averages.get(current_year, [0]))
        previous_avg = statistics.mean(yearly_averages.get(previous_year, [0]))

        year_over_year_change = 0
        if previous_avg > 0:
            year_over_year_change = ((current_avg - previous_avg) / previous_avg) * 100

        # Прогноз на следующий месяц (упрощенный)
        next_month = (datetime.now().month % 12) + 1
        predicted_next_month = seasonal_patterns.get(
            str(next_month).zfill(2), current_avg
        )

        return SeasonalAnalysis(
            item_name=item_name,
            seasonal_patterns=seasonal_patterns,
            peak_season=peak_season,
            low_season=low_season,
            seasonal_volatility=round(seasonal_volatility, 2),
            year_over_year_change=round(year_over_year_change, 2),
            predicted_next_month=round(predicted_next_month, 2),
        )

    def analyze_price_correlation(
        self, item1: str, item2: str, days_back: int = 90
    ) -> dict[str, Any]:
        """Анализ корреляции цен между двумя товарами."""
        conn = self._get_db_connection()

        start_date = datetime.now() - timedelta(days=days_back)

        query = """
            SELECT
                ph.product_name,
                ph.price,
                ph.created_at
            FROM price_history ph
            WHERE ph.product_name IN (?, ?)
            AND ph.created_at >= ?
            ORDER BY ph.created_at
        """

        cursor = conn.execute(query, (item1, item2, start_date.isoformat()))
        price_data = cursor.fetchall()
        conn.close()

        # Группируем данные по дате
        price_pairs = defaultdict(dict)
        for row in price_data:
            date = datetime.fromisoformat(row["created_at"]).date()
            price_pairs[date][row["product_name"]] = float(row["price"])

        # Формируем пары цен для корреляции
        item1_prices = []
        item2_prices = []

        for date, prices in price_pairs.items():
            if item1 in prices and item2 in prices:
                item1_prices.append(prices[item1])
                item2_prices.append(prices[item2])

        if len(item1_prices) < 3:
            return {
                "item1": item1,
                "item2": item2,
                "correlation_coefficient": 0,
                "correlation_strength": "insufficient_data",
                "sample_size": len(item1_prices),
                "price_change_correlation": 0,
                "significance_level": 0,
            }

        # Рассчитываем коэффициент корреляции Пирсона
        n = len(item1_prices)
        mean1 = statistics.mean(item1_prices)
        mean2 = statistics.mean(item2_prices)

        numerator = sum(
            (x - mean1) * (y - mean2) for x, y in zip(item1_prices, item2_prices)
        )
        denominator1 = sum((x - mean1) ** 2 for x in item1_prices)
        denominator2 = sum((y - mean2) ** 2 for y in item2_prices)

        correlation = 0
        if denominator1 > 0 and denominator2 > 0:
            correlation = numerator / math.sqrt(denominator1 * denominator2)

        # Определяем силу корреляции
        abs_corr = abs(correlation)
        if abs_corr < 0.3:
            strength = "weak"
        elif abs_corr < 0.7:
            strength = "moderate"
        else:
            strength = "strong"

        # Корреляция изменений цен
        item1_changes = [
            item1_prices[i] - item1_prices[i - 1] for i in range(1, len(item1_prices))
        ]
        item2_changes = [
            item2_prices[i] - item2_prices[i - 1] for i in range(1, len(item2_prices))
        ]

        if len(item1_changes) >= 2:
            mean_change1 = statistics.mean(item1_changes)
            mean_change2 = statistics.mean(item2_changes)

            change_numerator = sum(
                (x - mean_change1) * (y - mean_change2)
                for x, y in zip(item1_changes, item2_changes)
            )
            change_denominator1 = sum((x - mean_change1) ** 2 for x in item1_changes)
            change_denominator2 = sum((y - mean_change2) ** 2 for y in item2_changes)

            change_correlation = 0
            if change_denominator1 > 0 and change_denominator2 > 0:
                change_correlation = change_numerator / math.sqrt(
                    change_denominator1 * change_denominator2
                )
        else:
            change_correlation = 0

        # Уровень значимости (упрощенный)
        significance = 0.05 if abs(correlation) > 0.5 else 0.1

        return {
            "item1": item1,
            "item2": item2,
            "correlation_coefficient": round(correlation, 3),
            "correlation_strength": strength,
            "sample_size": len(item1_prices),
            "price_change_correlation": round(change_correlation, 3),
            "significance_level": significance,
        }

    def forecast_price_trend(
        self, item_name: str, supplier_id: str, days_ahead: int = 30
    ) -> dict[str, Any]:
        """Прогноз тренда цен на основе исторических данных."""
        trends = self.analyze_price_trends(
            item_name=item_name, supplier_id=supplier_id, days_back=180
        )

        if not trends:
            return {
                "item_name": item_name,
                "supplier_id": supplier_id,
                "forecast": "insufficient_data",
                "confidence": 0,
                "predicted_change": 0,
                "price_range": (0, 0),
                "factors": [],
            }

        trend = next((t for t in trends if t.supplier_id == supplier_id), None)
        if not trend:
            return {
                "item_name": item_name,
                "supplier_id": supplier_id,
                "forecast": "no_data_for_supplier",
                "confidence": 0,
                "predicted_change": 0,
                "price_range": (0, 0),
                "factors": [],
            }

        # Простая линейная экстраполяция
        if len(trend.price_history) >= 3:
            # Рассчитываем скорость изменения
            days_span = (trend.price_history[-1][0] - trend.price_history[0][0]).days
            price_change = trend.price_history[-1][1] - trend.price_history[0][1]
            daily_change_rate = price_change / max(days_span, 1)

            # Прогнозируемое изменение
            predicted_change = daily_change_rate * days_ahead
            predicted_price = trend.last_price + predicted_change

            # Диапазон прогноза (с учетом волатильности)
            volatility_factor = trend.volatility_score / 100
            price_range = (
                predicted_price * (1 - volatility_factor),
                predicted_price * (1 + volatility_factor),
            )

            # Уровень доверия
            confidence = max(0, min(100, 100 - trend.volatility_score))

            # Определяем факторы
            factors = []
            if abs(trend.trend_percentage) > 10:
                factors.append("strong_trend")
            if trend.volatility_score > 30:
                factors.append("high_volatility")
            if len(trend.price_history) < 10:
                factors.append("limited_data")

            forecast = "upward" if predicted_change > 0 else "downward"

        else:
            forecast = "stable"
            predicted_change = 0
            price_range = (trend.last_price * 0.95, trend.last_price * 1.05)
            confidence = 50
            factors = ["insufficient_history"]

        return {
            "item_name": item_name,
            "supplier_id": supplier_id,
            "forecast": forecast,
            "confidence": round(confidence, 1),
            "predicted_change": round(predicted_change, 2),
            "price_range": (round(price_range[0], 2), round(price_range[1], 2)),
            "factors": factors,
        }

    def get_market_trend_summary(self, days_back: int = 30) -> dict[str, Any]:
        """Общий обзор рыночных трендов."""
        trends = self.analyze_price_trends(days_back=days_back)

        if not trends:
            return {
                "total_items": 0,
                "upward_trends": 0,
                "downward_trends": 0,
                "stable_trends": 0,
                "average_volatility": 0,
                "market_health": "no_data",
                "top_rising_items": [],
                "top_falling_items": [],
            }

        # Статистика трендов
        upward_trends = sum(1 for t in trends if t.trend_direction == "up")
        downward_trends = sum(1 for t in trends if t.trend_direction == "down")
        stable_trends = sum(1 for t in trends if t.trend_direction == "stable")

        avg_volatility = statistics.mean([t.volatility_score for t in trends])

        # Определяем здоровье рынка
        if upward_trends > downward_trends * 1.5:
            market_health = "inflationary"
        elif downward_trends > upward_trends * 1.5:
            market_health = "deflationary"
        else:
            market_health = "stable"

        # Топ товары с ростом/падением
        top_rising = sorted(
            [t for t in trends if t.trend_direction == "up"],
            key=lambda x: x.trend_percentage,
            reverse=True,
        )[:5]

        top_falling = sorted(
            [t for t in trends if t.trend_direction == "down"],
            key=lambda x: x.trend_percentage,
        )[:5]

        return {
            "total_items": len(trends),
            "upward_trends": upward_trends,
            "downward_trends": downward_trends,
            "stable_trends": stable_trends,
            "average_volatility": round(avg_volatility, 2),
            "market_health": market_health,
            "top_rising_items": [
                {
                    "item": t.item_name,
                    "supplier": t.supplier_name,
                    "change": t.trend_percentage,
                }
                for t in top_rising
            ],
            "top_falling_items": [
                {
                    "item": t.item_name,
                    "supplier": t.supplier_name,
                    "change": t.trend_percentage,
                }
                for t in top_falling
            ],
        }

    def compare_suppliers_for_item(self, item_name: str) -> dict[str, Any]:
        """Сравнение поставщиков для конкретного товара."""
        market_analysis = self.analyze_market_for_item(item_name)

        if not market_analysis.competitive_suppliers:
            return {
                "item_name": item_name,
                "comparison_available": False,
                "message": "Недостаточно данных для сравнения",
            }

        # Дополнительный анализ каждого поставщика
        detailed_comparison = []

        for supplier in market_analysis.competitive_suppliers:
            supplier_profile = self.analyze_supplier_price_profile(
                supplier["supplier_id"]
            )

            # Рассчитываем общий скор поставщика
            price_score = max(
                0,
                100
                - (
                    (supplier["price"] - market_analysis.market_avg_price)
                    / market_analysis.market_avg_price
                    * 100
                ),
            )
            stability_score = supplier_profile.price_stability_score
            risk_score = 100 - supplier_profile.risk_score

            overall_score = price_score * 0.4 + stability_score * 0.3 + risk_score * 0.3

            detailed_comparison.append(
                {
                    "supplier_id": supplier["supplier_id"],
                    "supplier_name": supplier["supplier_name"],
                    "price": supplier["price"],
                    "price_vs_market": round(
                        (
                            (supplier["price"] - market_analysis.market_avg_price)
                            / market_analysis.market_avg_price
                            * 100
                        ),
                        2,
                    ),
                    "price_score": round(price_score, 2),
                    "stability_score": round(stability_score, 2),
                    "risk_score": round(risk_score, 2),
                    "overall_score": round(overall_score, 2),
                    "recommendation": self._generate_supplier_recommendation(
                        overall_score,
                        supplier["price"],
                        market_analysis.market_avg_price,
                    ),
                }
            )

        # Сортируем по общему скору
        detailed_comparison.sort(key=lambda x: x["overall_score"], reverse=True)

        return {
            "item_name": item_name,
            "comparison_available": True,
            "market_summary": {
                "total_suppliers": market_analysis.total_suppliers,
                "price_range": market_analysis.price_range,
                "market_avg_price": market_analysis.market_avg_price,
                "market_median_price": market_analysis.market_median_price,
            },
            "supplier_comparison": detailed_comparison,
            "best_choice": detailed_comparison[0] if detailed_comparison else None,
            "analysis_date": datetime.now().isoformat(),
        }

    def _generate_supplier_recommendation(
        self, overall_score: float, price: float, market_avg: float
    ) -> str:
        """Генерация рекомендации по поставщику."""
        if overall_score >= 80:
            return (
                "Отличный выбор - оптимальное соотношение цены, качества и надежности"
            )
        elif overall_score >= 60:
            return "Хороший вариант - рекомендуется к рассмотрению"
        elif overall_score >= 40:
            return "Средний вариант - требует дополнительного анализа"
        else:
            return "Не рекомендуется - высокие риски или неконкурентная цена"

    def get_price_analytics_summary(self, days_back: int = 30) -> dict[str, Any]:
        """Получить сводку ценовой аналитики."""
        trends = self.analyze_price_trends(days_back=days_back)
        alerts = self.generate_price_alerts(days_back=days_back)

        # Статистика по трендам
        trend_stats = {
            "total_items_tracked": len(trends),
            "price_increases": len([t for t in trends if t.trend_direction == "up"]),
            "price_decreases": len([t for t in trends if t.trend_direction == "down"]),
            "stable_prices": len([t for t in trends if t.trend_direction == "stable"]),
            "avg_volatility": round(
                statistics.mean([t.volatility_score for t in trends]), 2
            )
            if trends
            else 0,
        }

        # Статистика по предупреждениям
        alert_stats = {
            "total_alerts": len(alerts),
            "critical_alerts": len([a for a in alerts if a.severity == "critical"]),
            "high_alerts": len([a for a in alerts if a.severity == "high"]),
            "medium_alerts": len([a for a in alerts if a.severity == "medium"]),
            "low_alerts": len([a for a in alerts if a.severity == "low"]),
        }

        # Топ изменения цен
        top_increases = sorted(
            [t for t in trends if t.trend_percentage > 0],
            key=lambda x: x.trend_percentage,
            reverse=True,
        )[:5]
        top_decreases = sorted(
            [t for t in trends if t.trend_percentage < 0],
            key=lambda x: x.trend_percentage,
        )[:5]

        return {
            "summary_period_days": days_back,
            "trend_statistics": trend_stats,
            "alert_statistics": alert_stats,
            "top_price_increases": [
                {
                    "item_name": t.item_name,
                    "supplier_name": t.supplier_name,
                    "price_change_percent": t.trend_percentage,
                    "current_price": t.last_price,
                }
                for t in top_increases
            ],
            "top_price_decreases": [
                {
                    "item_name": t.item_name,
                    "supplier_name": t.supplier_name,
                    "price_change_percent": abs(t.trend_percentage),
                    "current_price": t.last_price,
                }
                for t in top_decreases
            ],
            "recent_alerts": alerts[:10],  # Последние 10 предупреждений
            "generated_at": datetime.now().isoformat(),
        }


# Утилитарные функции для быстрого доступа


def get_item_price_trend(item_name: str, days_back: int = 90) -> list[PriceTrend]:
    """Получить тренд цен для конкретного товара."""
    engine = PriceAnalyticsEngine()
    return engine.analyze_price_trends(item_name=item_name, days_back=days_back)


def get_market_analysis(item_name: str) -> MarketAnalysis:
    """Получить анализ рынка для товара."""
    engine = PriceAnalyticsEngine()
    return engine.analyze_market_for_item(item_name)


def get_price_alerts(threshold_percent: float = 15.0) -> list[PriceAlert]:
    """Получить текущие ценовые предупреждения."""
    engine = PriceAnalyticsEngine()
    return engine.generate_price_alerts(threshold_percent=threshold_percent)


def compare_suppliers(item_name: str) -> dict[str, Any]:
    """Сравнить поставщиков для товара."""
    engine = PriceAnalyticsEngine()
    return engine.compare_suppliers_for_item(item_name)


def get_supplier_price_analysis(supplier_id: str) -> SupplierPriceProfile:
    """Получить ценовой анализ поставщика."""
    engine = PriceAnalyticsEngine()
    return engine.analyze_supplier_price_profile(supplier_id)


class PriceTrendResult:
    """
    Результат анализа тренда цен.
    """

    def __init__(
        self,
        sku: str,
        trend_direction: str,
        price_change_percent: float = 0.0,
        price_change: float = 0.0,
        data_points: int = 0,
        monthly_change_rate: float = 0.0,
        confidence_level: float = 0.0,
        volatility_index: float = 0.0,
    ):
        self.sku = sku
        self.trend_direction = trend_direction
        self.price_change_percent = price_change_percent
        self.price_change = price_change
        self.data_points = data_points
        self.monthly_change_rate = monthly_change_rate
        self.confidence_level = confidence_level
        self.volatility_index = volatility_index


class PriceTrendAnalyzer:
    """Анализатор трендов цен на основе исторических данных."""

    def __init__(self):
        pass

    def analyze_trend(self, price_records: list[PriceRecord]) -> PriceTrendResult:
        """
        Анализирует тренд цен на основе исторических данных.

        Args:
            price_records: Список записей о ценах

        Returns:
            Результат анализа тренда
        """
        if not price_records or len(price_records) < 2:
            return PriceTrendResult(
                sku=price_records[0].sku if price_records else "",
                trend_direction="insufficient_data",
                data_points=len(price_records),
                confidence_level=0.0,
            )

        # Все записи должны быть для одного SKU
        if not all(r.sku == price_records[0].sku for r in price_records):
            return PriceTrendResult(
                sku=price_records[0].sku,
                trend_direction="error",
                data_points=len(price_records),
                confidence_level=0.0,
            )

        # Сортируем по времени
        price_records.sort(key=lambda x: x.timestamp)

        # Рассчитываем изменение цены
        first_price = float(price_records[0].price)
        last_price = float(price_records[-1].price)

        if first_price <= 0:
            return PriceTrendResult(
                sku=price_records[0].sku,
                trend_direction="error",
                data_points=len(price_records),
                confidence_level=0.0,
            )

        price_change = last_price - first_price
        price_change_percent = ((last_price - first_price) / first_price) * 100

        # Определяем направление тренда и волатильность
        prices = [float(r.price) for r in price_records]
        volatility_index = 0.0

        if len(prices) > 2:
            price_std = statistics.stdev(prices)
            price_mean = statistics.mean(prices)
            volatility_ratio = price_std / price_mean if price_mean > 0 else 0
            volatility_index = volatility_ratio * 100  # В процентах

            if volatility_ratio > 0.3:  # Более 30% волатильности
                trend_direction = "volatile"
            elif abs(price_change_percent) < 2.0:
                trend_direction = "stable"
            elif price_change_percent > 0:
                trend_direction = "increasing"
            else:
                trend_direction = "decreasing"
        else:
            if abs(price_change_percent) < 2.0:
                trend_direction = "stable"
            elif price_change_percent > 0:
                trend_direction = "increasing"
            else:
                trend_direction = "decreasing"

        # Рассчитываем ежемесячное изменение
        time_span_days = (price_records[-1].timestamp - price_records[0].timestamp).days
        monthly_change_rate = 0.0
        if time_span_days > 0:
            monthly_change_rate = (price_change_percent / time_span_days) * 30

        # Рассчитываем уровень доверия (на основе количества точек данных)
        confidence_level = min(1.0, len(price_records) / 10.0)

        return PriceTrendResult(
            sku=price_records[0].sku,
            trend_direction=trend_direction,
            price_change_percent=round(price_change_percent, 2),
            price_change=round(price_change, 2),
            data_points=len(price_records),
            monthly_change_rate=round(monthly_change_rate, 2),
            confidence_level=round(confidence_level, 2),
            volatility_index=round(volatility_index, 2),
        )

    def get_monthly_changes(
        self, price_records: list[PriceRecord]
    ) -> dict[str, PriceTrendResult]:
        """
        Получает ежемесячные изменения цен.

        Args:
            price_records: Список записей о ценах

        Returns:
            Словарь с месячными изменениями по SKU
        """
        if not price_records:
            return {}

        # Группируем по месяцам
        monthly_groups = {}
        for record in price_records:
            month_key = record.timestamp.strftime("%Y-%m")
            if month_key not in monthly_groups:
                monthly_groups[month_key] = []
            monthly_groups[month_key].append(record)

        monthly_changes = {}

        for month_key, records in monthly_groups.items():
            trend = self.analyze_trend(records)
            monthly_changes[month_key] = trend

        return monthly_changes

    def analyze_supplier_trends(
        self, price_records: list[PriceRecord], supplier_id: str
    ) -> PriceTrendResult:
        """
        Анализирует тренды цен для конкретного поставщика.

        Args:
            price_records: Список записей о ценах
            supplier_id: ID поставщика

        Returns:
            Результат анализа трендов для поставщика
        """
        supplier_records = [r for r in price_records if r.supplier == supplier_id]
        return self.analyze_trend(supplier_records)


if __name__ == "__main__":
    # Пример использования
    engine = PriceAnalyticsEngine()

    print("=== Анализ ценовых трендов ===")
    trends = engine.analyze_price_trends(days_back=30)
    for trend in trends[:5]:  # Показываем первые 5
        print(
            f"{trend.item_name} ({trend.supplier_name}): {trend.trend_direction} {trend.trend_percentage}%"
        )

    print("\n=== Ценовые предупреждения ===")
    alerts = engine.generate_price_alerts()
    for alert in alerts[:3]:  # Показываем первые 3
        print(f"{alert.severity.upper()}: {alert.description}")

    print("\n=== Сводка ценовой аналитики ===")
    summary = engine.get_price_analytics_summary()
    print(
        f"Отслеживается товаров: {summary['trend_statistics']['total_items_tracked']}"
    )
    print(f"Всего предупреждений: {summary['alert_statistics']['total_alerts']}")
    print(f"Средняя волатильность: {summary['trend_statistics']['avg_volatility']}%")
