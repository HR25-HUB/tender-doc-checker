"""
Business logic module for Streamlit UI
Extracts business logic from UI layer to maintain clean separation of concerns
"""

import datetime
from dataclasses import dataclass
from typing import Any, Optional

import pandas as pd


@dataclass
class FilterCriteria:
    """Data class for filter criteria"""

    status: Optional[str] = None
    rating: Optional[float] = None
    search_term: Optional[str] = None
    priority: Optional[str] = None
    supplier: Optional[str] = None


class DocumentManager:
    """Business logic for document management"""

    @staticmethod
    def group_documents_by_status(
        documents: list[dict[str, Any]]
    ) -> dict[str, list[dict[str, Any]]]:
        """Group documents by their status"""
        status_groups = {
            "pending": [],
            "processing": [],
            "approved": [],
            "rejected": [],
        }

        for doc in documents:
            status = doc.get("status", "pending")
            if status in status_groups:
                status_groups[status].append(doc)

        return status_groups

    @staticmethod
    def filter_documents(
        documents: list[dict[str, Any]], criteria: FilterCriteria
    ) -> list[dict[str, Any]]:
        """Filter documents based on criteria"""
        filtered_docs = documents.copy()

        if criteria.priority and criteria.priority != "Все":
            filtered_docs = [
                doc for doc in filtered_docs if doc.get("priority") == criteria.priority
            ]

        if criteria.supplier and criteria.supplier != "Все":
            filtered_docs = [
                doc for doc in filtered_docs if doc.get("supplier") == criteria.supplier
            ]

        return filtered_docs

    @staticmethod
    def update_document_status(
        documents: list[dict[str, Any]], doc_id: int, new_status: str
    ) -> list[dict[str, Any]]:
        """Update document status by ID"""
        updated_docs = []
        for doc in documents:
            if doc.get("id") == doc_id:
                updated_doc = doc.copy()
                updated_doc["status"] = new_status
                updated_docs.append(updated_doc)
            else:
                updated_docs.append(doc)
        return updated_docs


class SupplierManager:
    """Business logic for supplier management"""

    @staticmethod
    def filter_suppliers(
        suppliers: list[dict[str, Any]], criteria: FilterCriteria
    ) -> list[dict[str, Any]]:
        """Filter suppliers based on criteria"""
        filtered_suppliers = suppliers.copy()

        if criteria.status and criteria.status != "Все":
            filtered_suppliers = [
                s for s in filtered_suppliers if s.get("status") == criteria.status
            ]

        if criteria.rating is not None and criteria.rating > 0:
            filtered_suppliers = [
                s for s in filtered_suppliers if s.get("rating", 0) >= criteria.rating
            ]

        if criteria.search_term:
            search_lower = criteria.search_term.lower()
            filtered_suppliers = [
                s
                for s in filtered_suppliers
                if search_lower in str(s.get("name", "")).lower()
            ]

        return filtered_suppliers

    @staticmethod
    def add_supplier(
        suppliers: list[dict[str, Any]], supplier_data: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Add new supplier to the list"""
        new_suppliers = suppliers.copy()

        # Generate new ID
        max_id = max([s.get("id", 0) for s in suppliers], default=0)
        supplier_data["id"] = max_id + 1

        new_suppliers.append(supplier_data)
        return new_suppliers

    @staticmethod
    def remove_supplier(
        suppliers: list[dict[str, Any]], supplier_id: int
    ) -> list[dict[str, Any]]:
        """Remove supplier by ID"""
        return [s for s in suppliers if s.get("id") != supplier_id]

    @staticmethod
    def get_supplier_statistics(suppliers: list[dict[str, Any]]) -> dict[str, Any]:
        """Calculate supplier statistics"""
        if not suppliers:
            return {"total_suppliers": 0, "active_suppliers": 0, "average_rating": 0.0}

        total_suppliers = len(suppliers)
        active_suppliers = len([s for s in suppliers if s.get("status") == "active"])
        average_rating = sum(s.get("rating", 0) for s in suppliers) / total_suppliers

        return {
            "total_suppliers": total_suppliers,
            "active_suppliers": active_suppliers,
            "average_rating": round(average_rating, 1),
        }


class AnalyticsEngine:
    """Business logic for analytics and reporting"""

    @staticmethod
    def generate_dashboard_metrics() -> dict[str, Any]:
        """Generate metrics for dashboard"""
        return {
            "processed_documents": 156,
            "approval_percentage": 87.5,
            "processing_time": 2.4,
            "active_suppliers": 23,
            "weekly_delta": {
                "processed_documents": "+12 за неделю",
                "approval_percentage": "+2.3%",
                "processing_time": "-0.3 часа",
                "active_suppliers": "+2",
            },
        }

    @staticmethod
    def generate_processing_trend_data() -> pd.DataFrame:
        """Generate processing trend data for charts"""
        dates = pd.date_range(start="2024-01-01", end="2024-01-31", freq="D")
        processed_docs = [15 + i % 10 + (i // 7) * 2 for i in range(len(dates))]

        return pd.DataFrame({"date": dates, "processed_documents": processed_docs})

    @staticmethod
    def generate_status_distribution() -> dict[str, int]:
        """Generate document status distribution"""
        return {"Одобрено": 45, "На рассмотрении": 12, "Отклонено": 8, "Ожидает": 15}

    @staticmethod
    def generate_recent_documents() -> pd.DataFrame:
        """Generate recent documents data"""
        return pd.DataFrame(
            [
                {
                    "document": "Коммерческое предложение №045",
                    "supplier": 'ООО "Альфа"',
                    "status": "✅ Одобрено",
                    "date": "2024-01-30",
                },
                {
                    "document": "Договор поставки №046",
                    "supplier": 'ЗАО "Бета"',
                    "status": "⏳ На рассмотрении",
                    "date": "2024-01-30",
                },
                {
                    "document": "Спецификация №047",
                    "supplier": "ИП Петров",
                    "status": "❌ Отклонено",
                    "date": "2024-01-29",
                },
                {
                    "document": "Счет №048",
                    "supplier": 'ООО "Гамма"',
                    "status": "✅ Одобрено",
                    "date": "2024-01-29",
                },
            ]
        )


class DataInitializer:
    """Business logic for initializing default data"""

    @staticmethod
    def get_default_suppliers() -> list[dict[str, Any]]:
        """Get default suppliers data"""
        return [
            {
                "id": 1,
                "name": 'ООО "Альфа Поставки"',
                "contact_person": "Иванов И.И.",
                "email": "ivanov@alpha-supply.ru",
                "phone": "+7 (495) 123-45-67",
                "rating": 4.5,
                "status": "active",
            },
            {
                "id": 2,
                "name": 'ЗАО "Бета Трейд"',
                "contact_person": "Петров П.П.",
                "email": "petrov@beta-trade.ru",
                "phone": "+7 (495) 987-65-43",
                "rating": 4.2,
                "status": "active",
            },
        ]

    @staticmethod
    def get_default_documents() -> list[dict[str, Any]]:
        """Get default documents data"""
        return [
            {
                "id": 1,
                "name": "Коммерческое предложение №001",
                "supplier": 'ООО "Альфа Поставки"',
                "status": "pending",
                "created_date": datetime.datetime.now() - datetime.timedelta(days=2),
                "priority": "high",
            },
            {
                "id": 2,
                "name": "Договор поставки №002",
                "supplier": 'ЗАО "Бета Трейд"',
                "status": "processing",
                "created_date": datetime.datetime.now() - datetime.timedelta(days=1),
                "priority": "medium",
            },
            {
                "id": 3,
                "name": "Спецификация товаров №003",
                "supplier": 'ООО "Альфа Поставки"',
                "status": "approved",
                "created_date": datetime.datetime.now() - datetime.timedelta(hours=6),
                "priority": "low",
            },
        ]


class SidebarStats:
    """Business logic for sidebar statistics"""

    @staticmethod
    def get_quick_stats(
        suppliers: list[dict[str, Any]], documents: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Get quick statistics for sidebar"""
        return {
            "documents_today": 12,
            "active_suppliers": len(
                [s for s in suppliers if s.get("status") == "active"]
            ),
            "processing_tasks": len(
                [d for d in documents if d.get("status") == "processing"]
            ),
        }
