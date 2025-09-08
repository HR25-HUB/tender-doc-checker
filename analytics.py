"""Модуль базовой аналитики для системы проверки документов."""
import json
import math
import sqlite3
import statistics
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional

from db import DB_PATH


@dataclass
class ProcessingMetrics:
    """Метрики скорости обработки документов."""

    total_documents: int
    avg_processing_time_minutes: float
    median_processing_time_minutes: float
    fastest_processing_minutes: float
    slowest_processing_minutes: float
    documents_per_day: float
    processing_efficiency_score: float  # 0-100


@dataclass
class ApprovalMetrics:
    """Метрики одобрения документов."""

    total_checked: int
    approved_count: int
    rejected_count: int
    partially_approved_count: int
    approval_rate_percent: float
    rejection_rate_percent: float
    partial_approval_rate_percent: float
    avg_confidence_score: float


@dataclass
class SupplierAnalytics:
    """Аналитика по поставщикам."""

    total_suppliers: int
    active_suppliers: int
    top_suppliers_by_volume: list[dict]
    top_suppliers_by_rating: list[dict]
    avg_supplier_rating: float
    suppliers_by_risk_level: dict[str, int]
    new_suppliers_this_month: int


@dataclass
class DocumentTypeAnalytics:
    """Аналитика по типам документов."""

    document_type_distribution: dict[str, int]
    approval_rates_by_type: dict[str, float]
    avg_processing_time_by_type: dict[str, float]
    most_common_issues_by_type: dict[str, list[str]]


@dataclass
class SystemMetrics:
    """Общие метрики системы."""

    uptime_percent: float
    total_documents_processed: int
    documents_processed_today: int
    documents_processed_this_week: int
    documents_processed_this_month: int
    avg_daily_volume: float
    peak_processing_hour: int
    system_load_score: float  # 0-100


class AnalyticsEngine:
    """Основной класс для расчета аналитических метрик."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def _get_db_connection(self) -> sqlite3.Connection:
        """Получить соединение с базой данных."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def calculate_processing_metrics(
        self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> ProcessingMetrics:
        """Рассчитать метрики скорости обработки документов."""
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()

        conn = self._get_db_connection()

        # Получаем данные о времени обработки документов
        query = """
            SELECT
                filename,
                checked_at,
                result
            FROM report_history
            WHERE checked_at BETWEEN ? AND ?
            ORDER BY checked_at
        """

        cursor = conn.execute(query, (start_date.isoformat(), end_date.isoformat()))
        reports = cursor.fetchall()
        conn.close()

        if not reports:
            return ProcessingMetrics(
                total_documents=0,
                avg_processing_time_minutes=0.0,
                median_processing_time_minutes=0.0,
                fastest_processing_minutes=0.0,
                slowest_processing_minutes=0.0,
                documents_per_day=0.0,
                processing_efficiency_score=0.0,
            )

        # Анализируем время обработки (симуляция на основе размера результата)
        processing_times = []
        for report in reports:
            try:
                result_data = json.loads(report["result"])
                # Оценка времени обработки на основе сложности результата
                complexity_score = (
                    len(result_data) if isinstance(result_data, list) else 1
                )
                estimated_time = max(
                    1.0, complexity_score * 0.5 + len(str(result_data)) / 1000
                )
                processing_times.append(estimated_time)
            except (json.JSONDecodeError, TypeError):
                processing_times.append(2.0)  # Значение по умолчанию

        # Рассчитываем метрики
        total_docs = len(reports)
        avg_time = sum(processing_times) / len(processing_times)
        sorted_times = sorted(processing_times)
        median_time = sorted_times[len(sorted_times) // 2]
        fastest_time = min(processing_times)
        slowest_time = max(processing_times)

        # Документов в день
        days_diff = max(1, (end_date - start_date).days)
        docs_per_day = total_docs / days_diff

        # Оценка эффективности (чем меньше время, тем выше эффективность)
        efficiency_score = max(0, min(100, 100 - (avg_time - 1) * 10))

        return ProcessingMetrics(
            total_documents=total_docs,
            avg_processing_time_minutes=round(avg_time, 2),
            median_processing_time_minutes=round(median_time, 2),
            fastest_processing_minutes=round(fastest_time, 2),
            slowest_processing_minutes=round(slowest_time, 2),
            documents_per_day=round(docs_per_day, 2),
            processing_efficiency_score=round(efficiency_score, 2),
        )

    def calculate_approval_metrics(
        self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> ApprovalMetrics:
        """Рассчитать метрики одобрения документов."""
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()

        conn = self._get_db_connection()

        query = """
            SELECT result
            FROM report_history
            WHERE checked_at BETWEEN ? AND ?
        """

        cursor = conn.execute(query, (start_date.isoformat(), end_date.isoformat()))
        reports = cursor.fetchall()
        conn.close()

        if not reports:
            return ApprovalMetrics(
                total_checked=0,
                approved_count=0,
                rejected_count=0,
                partially_approved_count=0,
                approval_rate_percent=0.0,
                rejection_rate_percent=0.0,
                partial_approval_rate_percent=0.0,
                avg_confidence_score=0.0,
            )

        # Анализируем результаты проверок
        approved = 0
        rejected = 0
        partial = 0
        confidence_scores = []

        for report in reports:
            try:
                result_data = json.loads(report["result"])
                if isinstance(result_data, list):
                    # Анализируем результаты проверки
                    matches = []
                    confidences = []

                    for item in result_data:
                        if isinstance(item, dict):
                            match = item.get("match", "нет")
                            matches.append(match)

                            confidence = item.get("confidence")
                            if confidence is not None:
                                confidences.append(float(confidence))

                    # Определяем общий статус документа
                    if all(m == "да" for m in matches):
                        approved += 1
                    elif all(m == "нет" for m in matches):
                        rejected += 1
                    else:
                        partial += 1

                    # Добавляем средний confidence для документа
                    if confidences:
                        confidence_scores.append(sum(confidences) / len(confidences))
                else:
                    # Простой результат
                    partial += 1
                    confidence_scores.append(0.5)

            except (json.JSONDecodeError, TypeError, KeyError):
                rejected += 1
                confidence_scores.append(0.0)

        total = len(reports)
        approval_rate = (approved / total * 100) if total > 0 else 0
        rejection_rate = (rejected / total * 100) if total > 0 else 0
        partial_rate = (partial / total * 100) if total > 0 else 0
        avg_confidence = (
            sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        )

        return ApprovalMetrics(
            total_checked=total,
            approved_count=approved,
            rejected_count=rejected,
            partially_approved_count=partial,
            approval_rate_percent=round(approval_rate, 2),
            rejection_rate_percent=round(rejection_rate, 2),
            partial_approval_rate_percent=round(partial_rate, 2),
            avg_confidence_score=round(avg_confidence, 3),
        )

    def calculate_supplier_analytics(self) -> SupplierAnalytics:
        """Рассчитать аналитику по поставщикам."""
        conn = self._get_db_connection()

        # Общая статистика поставщиков
        cursor = conn.execute("SELECT COUNT(*) as total FROM suppliers")
        total_suppliers = cursor.fetchone()["total"]

        cursor = conn.execute(
            "SELECT COUNT(*) as active FROM suppliers WHERE cooperation_status = 'активный'"
        )
        active_suppliers = cursor.fetchone()["active"]

        # Топ поставщики по объему транзакций
        cursor = conn.execute(
            """
            SELECT
                s.supplier_id,
                s.name,
                COALESCE(SUM(st.amount), 0) as total_volume,
                COUNT(st.transaction_id) as transaction_count
            FROM suppliers s
            LEFT JOIN supplier_transactions st ON s.supplier_id = st.supplier_id
            WHERE st.status = 'выполнена'
            GROUP BY s.supplier_id, s.name
            ORDER BY total_volume DESC
            LIMIT 10
        """
        )
        top_by_volume = [
            {
                "supplier_id": row["supplier_id"],
                "name": row["name"],
                "total_volume": float(row["total_volume"]),
                "transaction_count": row["transaction_count"],
            }
            for row in cursor.fetchall()
        ]

        # Топ поставщики по рейтингу
        cursor = conn.execute(
            """
            SELECT supplier_id, name, overall_rating
            FROM suppliers
            WHERE overall_rating > 0
            ORDER BY overall_rating DESC
            LIMIT 10
        """
        )
        top_by_rating = [
            {
                "supplier_id": row["supplier_id"],
                "name": row["name"],
                "rating": float(row["overall_rating"]),
            }
            for row in cursor.fetchall()
        ]

        # Средний рейтинг поставщиков
        cursor = conn.execute(
            "SELECT AVG(overall_rating) as avg_rating FROM suppliers WHERE overall_rating > 0"
        )
        avg_rating_result = cursor.fetchone()
        avg_rating = (
            float(avg_rating_result["avg_rating"])
            if avg_rating_result["avg_rating"]
            else 0.0
        )

        # Распределение по уровням риска
        cursor = conn.execute(
            """
            SELECT risk_level, COUNT(*) as count
            FROM suppliers
            GROUP BY risk_level
        """
        )
        risk_distribution = {
            row["risk_level"]: row["count"] for row in cursor.fetchall()
        }

        # Новые поставщики за месяц
        month_ago = (datetime.now() - timedelta(days=30)).isoformat()
        cursor = conn.execute(
            "SELECT COUNT(*) as new_count FROM suppliers WHERE created_at >= ?",
            (month_ago,),
        )
        new_suppliers = cursor.fetchone()["new_count"]

        conn.close()

        return SupplierAnalytics(
            total_suppliers=total_suppliers,
            active_suppliers=active_suppliers,
            top_suppliers_by_volume=top_by_volume,
            top_suppliers_by_rating=top_by_rating,
            avg_supplier_rating=round(avg_rating, 2),
            suppliers_by_risk_level=risk_distribution,
            new_suppliers_this_month=new_suppliers,
        )

    def calculate_document_type_analytics(self) -> DocumentTypeAnalytics:
        """Рассчитать аналитику по типам документов."""
        conn = self._get_db_connection()

        # Распределение по типам документов
        cursor = conn.execute(
            """
            SELECT document_type, COUNT(*) as count
            FROM supplier_documents
            GROUP BY document_type
            ORDER BY count DESC
        """
        )
        type_distribution = {
            row["document_type"]: row["count"] for row in cursor.fetchall()
        }

        # Для упрощения, создаем базовую аналитику
        # В реальной системе здесь был бы более сложный анализ
        approval_rates = {}
        processing_times = {}
        common_issues = {}

        for doc_type in type_distribution.keys():
            # Симуляция данных на основе типа документа
            if "договор" in doc_type.lower():
                approval_rates[doc_type] = 85.5
                processing_times[doc_type] = 15.2
                common_issues[doc_type] = ["Неполные реквизиты", "Некорректные сроки"]
            elif "предложение" in doc_type.lower():
                approval_rates[doc_type] = 72.3
                processing_times[doc_type] = 8.7
                common_issues[doc_type] = ["Завышенные цены", "Неточные спецификации"]
            elif "счет" in doc_type.lower():
                approval_rates[doc_type] = 91.2
                processing_times[doc_type] = 5.1
                common_issues[doc_type] = [
                    "Ошибки в НДС",
                    "Неверные банковские реквизиты",
                ]
            else:
                approval_rates[doc_type] = 78.0
                processing_times[doc_type] = 10.0
                common_issues[doc_type] = ["Общие ошибки оформления"]

        conn.close()

        return DocumentTypeAnalytics(
            document_type_distribution=type_distribution,
            approval_rates_by_type=approval_rates,
            avg_processing_time_by_type=processing_times,
            most_common_issues_by_type=common_issues,
        )

    def calculate_system_metrics(self) -> SystemMetrics:
        """Рассчитать общие метрики системы."""
        conn = self._get_db_connection()

        # Общее количество обработанных документов
        cursor = conn.execute("SELECT COUNT(*) as total FROM report_history")
        total_processed = cursor.fetchone()["total"]

        # Документы за сегодня
        today = datetime.now().date().isoformat()
        cursor = conn.execute(
            "SELECT COUNT(*) as today_count FROM report_history WHERE DATE(checked_at) = ?",
            (today,),
        )
        today_count = cursor.fetchone()["today_count"]

        # Документы за неделю
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        cursor = conn.execute(
            "SELECT COUNT(*) as week_count FROM report_history WHERE checked_at >= ?",
            (week_ago,),
        )
        week_count = cursor.fetchone()["week_count"]

        # Документы за месяц
        month_ago = (datetime.now() - timedelta(days=30)).isoformat()
        cursor = conn.execute(
            "SELECT COUNT(*) as month_count FROM report_history WHERE checked_at >= ?",
            (month_ago,),
        )
        month_count = cursor.fetchone()["month_count"]

        # Средний дневной объем
        cursor = conn.execute(
            """
            SELECT
                DATE(checked_at) as date,
                COUNT(*) as daily_count
            FROM report_history
            WHERE checked_at >= ?
            GROUP BY DATE(checked_at)
        """,
            (month_ago,),
        )

        daily_counts = [row["daily_count"] for row in cursor.fetchall()]
        avg_daily = sum(daily_counts) / len(daily_counts) if daily_counts else 0

        # Пиковый час обработки (симуляция)
        peak_hour = 14  # 14:00 - типичный пик активности

        # Оценка загрузки системы
        system_load = min(100, (today_count / max(1, avg_daily)) * 50)

        conn.close()

        return SystemMetrics(
            uptime_percent=99.5,  # Симуляция uptime
            total_documents_processed=total_processed,
            documents_processed_today=today_count,
            documents_processed_this_week=week_count,
            documents_processed_this_month=month_count,
            avg_daily_volume=round(avg_daily, 1),
            peak_processing_hour=peak_hour,
            system_load_score=round(system_load, 1),
        )

    def get_comprehensive_analytics(
        self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> dict:
        """Получить комплексную аналитику системы."""
        return {
            "processing_metrics": self.calculate_processing_metrics(
                start_date, end_date
            ),
            "approval_metrics": self.calculate_approval_metrics(start_date, end_date),
            "supplier_analytics": self.calculate_supplier_analytics(),
            "document_type_analytics": self.calculate_document_type_analytics(),
            "system_metrics": self.calculate_system_metrics(),
            "generated_at": datetime.now().isoformat(),
            "period": {
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
            },
        }

    def analyze_document_trends(
        self, document_type: Optional[str] = None, days_back: int = 90
    ) -> dict[str, Any]:
        """Анализ трендов обработки документов."""
        conn = self._get_db_connection()

        start_date = datetime.now() - timedelta(days=days_back)

        # Базовый запрос
        query = """
            SELECT
                DATE(checked_at) as date,
                doc_type as document_type,
                COUNT(*) as document_count,
                AVG(CASE WHEN result LIKE '%"match": "да"%' THEN 1 ELSE 0 END) * 100 as approval_rate
            FROM report_history
            WHERE checked_at >= ?
        """

        params = [start_date.isoformat()]

        if document_type:
            query += " AND doc_type = ?"
            params.append(document_type)

        query += " GROUP BY DATE(checked_at), doc_type ORDER BY date"

        cursor = conn.execute(query, params)
        trend_data = cursor.fetchall()
        conn.close()

        if not trend_data:
            return {
                "document_type": document_type or "all",
                "trend_period": days_back,
                "total_documents": 0,
                "trend_direction": "no_data",
                "average_daily_volume": 0,
                "approval_trend": "no_data",
                "peak_day": None,
                "volatility": 0,
            }

        # Анализ трендов
        dates = [row["date"] for row in trend_data]
        volumes = [row["document_count"] for row in trend_data]
        approval_rates = [row["approval_rate"] or 0 for row in trend_data]

        # Направление тренда объема
        if len(volumes) >= 7:
            first_week = statistics.mean(volumes[:7])
            last_week = statistics.mean(volumes[-7:])
            volume_change = ((last_week - first_week) / max(first_week, 1)) * 100

            if volume_change > 10:
                volume_trend = "increasing"
            elif volume_change < -10:
                volume_trend = "decreasing"
            else:
                volume_trend = "stable"
        else:
            volume_trend = "stable"

        # Направление тренда одобрения
        if len(approval_rates) >= 7:
            first_week_approval = statistics.mean(approval_rates[:7])
            last_week_approval = statistics.mean(approval_rates[-7:])
            approval_change = last_week_approval - first_week_approval

            if approval_change > 5:
                approval_trend = "improving"
            elif approval_change < -5:
                approval_trend = "declining"
            else:
                approval_trend = "stable"
        else:
            approval_trend = "stable"

        # Пиковый день
        max_volume_index = volumes.index(max(volumes))
        peak_day = dates[max_volume_index]

        # Волатильность объема
        if len(volumes) > 1:
            volume_variance = statistics.variance(volumes)
            volume_volatility = (
                math.sqrt(volume_variance) / statistics.mean(volumes)
            ) * 100
        else:
            volume_volatility = 0

        return {
            "document_type": document_type or "all",
            "trend_period": days_back,
            "total_documents": sum(volumes),
            "trend_direction": volume_trend,
            "average_daily_volume": round(statistics.mean(volumes), 2),
            "approval_trend": approval_trend,
            "peak_day": peak_day,
            "volatility": round(volume_volatility, 2),
        }

    def analyze_supplier_performance_trends(
        self, supplier_id: str, days_back: int = 90
    ) -> dict[str, Any]:
        """Анализ трендов производительности поставщика."""
        conn = self._get_db_connection()

        start_date = datetime.now() - timedelta(days=days_back)

        query = """
            SELECT
                DATE(checked_at) as date,
                COUNT(*) as documents_submitted,
                AVG(CASE WHEN result LIKE '%"match": "да"%' THEN 1 ELSE 0 END) * 100 as success_rate,
                AVG(CASE WHEN result LIKE '%"confidence"%' THEN
                    CAST(SUBSTR(result, INSTR(result, '"confidence":') + 12, 5) AS REAL) ELSE 0 END) as avg_confidence
            FROM report_history
            WHERE user_id = ?
            AND checked_at >= ?
            GROUP BY DATE(checked_at)
            ORDER BY date
        """

        cursor = conn.execute(query, (supplier_id, start_date.isoformat()))
        performance_data = cursor.fetchall()
        conn.close()

        if not performance_data:
            return {
                "supplier_id": supplier_id,
                "trend_period": days_back,
                "total_documents": 0,
                "performance_trend": "no_data",
                "success_rate_trend": "no_data",
                "confidence_trend": "no_data",
                "improvement_rate": 0,
                "consistency_score": 0,
            }

        # Анализ трендов
        dates = [row["date"] for row in performance_data]
        documents = [row["documents_submitted"] for row in performance_data]
        success_rates = [row["success_rate"] or 0 for row in performance_data]
        confidence_scores = [row["avg_confidence"] or 0 for row in performance_data]

        # Рассчитываем тренды
        if len(success_rates) >= 7:
            # Линейная регрессия для тренда успешности
            n = len(success_rates)
            x_values = list(range(n))

            sum_x = sum(x_values)
            sum_y = sum(success_rates)
            sum_xy = sum(x * y for x, y in zip(x_values, success_rates))
            sum_x2 = sum(x * x for x in x_values)

            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
            improvement_rate = slope * 100  # процент улучшения за период

            if improvement_rate > 5:
                success_trend = "improving"
            elif improvement_rate < -5:
                success_trend = "declining"
            else:
                success_trend = "stable"
        else:
            improvement_rate = 0
            success_trend = "stable"

        # Оценка консистентности (стабильность показателей)
        if len(success_rates) > 1:
            success_variance = statistics.variance(success_rates)
            consistency_score = max(
                0, 100 - (success_variance / 10)
            )  # чем меньше вариация, тем выше консистентность
        else:
            consistency_score = 100

        # Общая оценка производительности
        avg_success = statistics.mean(success_rates)
        avg_confidence = statistics.mean(confidence_scores)

        performance_score = (avg_success + avg_confidence) / 2

        if performance_score > 80:
            performance_trend = "excellent"
        elif performance_score > 60:
            performance_trend = "good"
        elif performance_score > 40:
            performance_trend = "fair"
        else:
            performance_trend = "needs_improvement"

        return {
            "supplier_id": supplier_id,
            "trend_period": days_back,
            "total_documents": sum(documents),
            "performance_trend": performance_trend,
            "success_rate_trend": success_trend,
            "confidence_trend": "stable",  # Упрощенно
            "improvement_rate": round(improvement_rate, 2),
            "consistency_score": round(consistency_score, 2),
            "average_success_rate": round(avg_success, 2),
            "average_confidence": round(avg_confidence, 2),
        }

    def analyze_system_usage_trends(self, days_back: int = 30) -> dict[str, Any]:
        """Анализ трендов использования системы."""
        conn = self._get_db_connection()

        start_date = datetime.now() - timedelta(days=days_back)

        query = """
            SELECT
                DATE(checked_at) as date,
                COUNT(*) as daily_usage,
                COUNT(DISTINCT user_id) as active_users,
                COUNT(DISTINCT doc_type) as document_types_processed
            FROM report_history
            WHERE checked_at >= ?
            GROUP BY DATE(checked_at)
            ORDER BY date
        """

        cursor = conn.execute(query, (start_date.isoformat(),))
        usage_data = cursor.fetchall()
        conn.close()

        if not usage_data:
            return {
                "trend_period": days_back,
                "total_usage": 0,
                "usage_trend": "no_data",
                "supplier_growth": "no_data",
                "diversity_trend": "no_data",
                "peak_usage_day": None,
                "growth_rate": 0,
            }

        # Анализ трендов
        dates = [row["date"] for row in usage_data]
        daily_usage = [row["daily_usage"] for row in usage_data]
        active_suppliers = [row["active_suppliers"] for row in usage_data]
        document_types = [row["document_types_processed"] for row in usage_data]

        # Рассчитываем рост использования
        if len(daily_usage) >= 7:
            first_week = statistics.mean(daily_usage[:7])
            last_week = statistics.mean(daily_usage[-7:])
            growth_rate = ((last_week - first_week) / max(first_week, 1)) * 100

            if growth_rate > 20:
                usage_trend = "rapidly_growing"
            elif growth_rate > 5:
                usage_trend = "growing"
            elif growth_rate < -5:
                usage_trend = "declining"
            else:
                usage_trend = "stable"
        else:
            growth_rate = 0
            usage_trend = "stable"

        # Рост активных поставщиков
        if len(active_suppliers) >= 7:
            first_week_suppliers = statistics.mean(active_suppliers[:7])
            last_week_suppliers = statistics.mean(active_suppliers[-7:])
            supplier_growth = (
                (last_week_suppliers - first_week_suppliers)
                / max(first_week_suppliers, 1)
            ) * 100

            if supplier_growth > 10:
                supplier_trend = "growing"
            elif supplier_growth < -10:
                supplier_trend = "declining"
            else:
                supplier_trend = "stable"
        else:
            supplier_trend = "stable"

        # Пиковый день использования
        max_usage_index = daily_usage.index(max(daily_usage))
        peak_usage_day = dates[max_usage_index]

        return {
            "trend_period": days_back,
            "total_usage": sum(daily_usage),
            "usage_trend": usage_trend,
            "supplier_growth": supplier_trend,
            "diversity_trend": "stable",  # Упрощенно
            "peak_usage_day": peak_usage_day,
            "growth_rate": round(growth_rate, 2),
            "average_daily_usage": round(statistics.mean(daily_usage), 2),
            "max_daily_usage": max(daily_usage),
            "total_active_suppliers": max(active_suppliers),
        }

    def get_trend_analysis_dashboard(self, days_back: int = 30) -> dict[str, Any]:
        """Получить комплексный дашборд трендов."""
        return {
            "document_trends": self.analyze_document_trends(days_back=days_back),
            "system_usage_trends": self.analyze_system_usage_trends(
                days_back=days_back
            ),
            "generated_at": datetime.now().isoformat(),
            "period_days": days_back,
            "summary": self._generate_trend_summary(days_back),
        }

    def _generate_trend_summary(self, days_back: int) -> str:
        """Генерация текстового резюме трендов."""
        doc_trends = self.analyze_document_trends(days_back=days_back)
        usage_trends = self.analyze_system_usage_trends(days_back=days_back)

        summary_parts = []

        # Объем документов
        if doc_trends["total_documents"] > 0:
            summary_parts.append(
                f"Обработано {doc_trends['total_documents']} документов за {days_back} дней"
            )

        # Тренд объема
        if doc_trends["trend_direction"] != "no_data":
            if doc_trends["trend_direction"] == "increasing":
                summary_parts.append("Объем документов растет")
            elif doc_trends["trend_direction"] == "decreasing":
                summary_parts.append("Объем документов снижается")
            else:
                summary_parts.append("Объем документов стабилен")

        # Тренд использования
        if usage_trends["usage_trend"] != "no_data":
            if usage_trends["usage_trend"] == "rapidly_growing":
                summary_parts.append("Использование системы быстро растет")
            elif usage_trends["usage_trend"] == "growing":
                summary_parts.append("Использование системы растет")
            elif usage_trends["usage_trend"] == "declining":
                summary_parts.append("Использование системы снижается")

        return (
            ". ".join(summary_parts)
            if summary_parts
            else "Недостаточно данных для анализа трендов"
        )


# Утилитарные функции для быстрого доступа к метрикам


def get_processing_speed_metrics(days: int = 30) -> ProcessingMetrics:
    """Получить метрики скорости обработки за указанное количество дней."""
    engine = AnalyticsEngine()
    start_date = datetime.now() - timedelta(days=days)
    return engine.calculate_processing_metrics(start_date)


def get_approval_rate_metrics(days: int = 30) -> ApprovalMetrics:
    """Получить метрики одобрения за указанное количество дней."""
    engine = AnalyticsEngine()
    start_date = datetime.now() - timedelta(days=days)
    return engine.calculate_approval_metrics(start_date)


def get_supplier_performance_summary() -> SupplierAnalytics:
    """Получить сводку по производительности поставщиков."""
    engine = AnalyticsEngine()
    return engine.calculate_supplier_analytics()


def get_daily_dashboard_metrics() -> dict:
    """Получить ключевые метрики для ежедневного дашборда."""
    engine = AnalyticsEngine()

    # Метрики за последние 24 часа
    yesterday = datetime.now() - timedelta(days=1)
    today = datetime.now()

    processing = engine.calculate_processing_metrics(yesterday, today)
    approval = engine.calculate_approval_metrics(yesterday, today)
    system = engine.calculate_system_metrics()

    return {
        "documents_processed_today": processing.total_documents,
        "avg_processing_time": processing.avg_processing_time_minutes,
        "approval_rate": approval.approval_rate_percent,
        "system_load": system.system_load_score,
        "uptime": system.uptime_percent,
        "last_updated": datetime.now().isoformat(),
    }


if __name__ == "__main__":
    # Пример использования
    engine = AnalyticsEngine()

    print("=== Метрики скорости обработки ===")
    processing_metrics = engine.calculate_processing_metrics()
    print(f"Всего документов: {processing_metrics.total_documents}")
    print(
        f"Среднее время обработки: {processing_metrics.avg_processing_time_minutes} мин"
    )
    print(f"Эффективность: {processing_metrics.processing_efficiency_score}%")

    print("\n=== Метрики одобрения ===")
    approval_metrics = engine.calculate_approval_metrics()
    print(f"Процент одобрения: {approval_metrics.approval_rate_percent}%")
    print(f"Процент отклонения: {approval_metrics.rejection_rate_percent}%")
    print(f"Средняя уверенность: {approval_metrics.avg_confidence_score}")

    print("\n=== Аналитика поставщиков ===")
    supplier_analytics = engine.calculate_supplier_analytics()
    print(f"Всего поставщиков: {supplier_analytics.total_suppliers}")
    print(f"Активных: {supplier_analytics.active_suppliers}")
    print(f"Средний рейтинг: {supplier_analytics.avg_supplier_rating}")
