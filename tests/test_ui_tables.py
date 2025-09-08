"""
Тесты для формирования таблиц и фильтров на основе моков
Проверка генерации таблиц, фильтров и обработки данных в UI
"""

import datetime
import os
import sys
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

# Добавляем путь к корню проекта для импортов
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestUITableGeneration:
    """Тесты для генерации таблиц и фильтров на основе мок-данных"""

    def create_mock_suppliers_data(self):
        """Создание мок-данных для поставщиков"""
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
                "rating": 3.8,
                "status": "active",
            },
            {
                "id": 3,
                "name": 'ИП "Гамма Сервис"',
                "contact_person": "Сидоров С.С.",
                "email": "sidorov@gamma-service.ru",
                "phone": "+7 (495) 555-55-55",
                "rating": 2.5,
                "status": "inactive",
            },
            {
                "id": 4,
                "name": 'ООО "Дельта Логистик"',
                "contact_person": "Козлов К.К.",
                "email": "kozlov@delta-log.ru",
                "phone": "+7 (495) 777-77-77",
                "rating": 4.9,
                "status": "active",
            },
        ]

    def create_mock_documents_data(self):
        """Создание мок-данных для документов"""
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
            {
                "id": 4,
                "name": "Акт приемки №004",
                "supplier": 'ИП "Гамма Сервис"',
                "status": "rejected",
                "created_date": datetime.datetime.now() - datetime.timedelta(days=3),
                "priority": "high",
            },
        ]

    def test_suppliers_dataframe_creation(self):
        """Тест создания DataFrame для поставщиков"""
        suppliers_data = self.create_mock_suppliers_data()
        df = pd.DataFrame(suppliers_data)

        assert len(df) == 4
        assert list(df.columns) == [
            "id",
            "name",
            "contact_person",
            "email",
            "phone",
            "rating",
            "status",
        ]
        assert df["rating"].dtype == "float64"
        assert df["id"].dtype == "int64"

    def test_suppliers_filter_by_status(self):
        """Тест фильтрации поставщиков по статусу"""
        suppliers_data = self.create_mock_suppliers_data()
        df = pd.DataFrame(suppliers_data)

        # Фильтрация активных поставщиков
        active_suppliers = df[df["status"] == "active"]
        assert len(active_suppliers) == 3
        assert all(active_suppliers["status"] == "active")

        # Фильтрация неактивных поставщиков
        inactive_suppliers = df[df["status"] == "inactive"]
        assert len(inactive_suppliers) == 1
        assert inactive_suppliers.iloc[0]["name"] == 'ИП "Гамма Сервис"'

    def test_suppliers_filter_by_rating(self):
        """Тест фильтрации поставщиков по рейтингу"""
        suppliers_data = self.create_mock_suppliers_data()
        df = pd.DataFrame(suppliers_data)

        # Поставщики с рейтингом >= 4.0
        high_rated = df[df["rating"] >= 4.0]
        assert len(high_rated) == 2
        assert all(high_rated["rating"] >= 4.0)

    def test_suppliers_filter_by_name_search(self):
        """Тест поиска поставщиков по названию"""
        suppliers_data = self.create_mock_suppliers_data()
        df = pd.DataFrame(suppliers_data)

        # Поиск по части названия
        alpha_suppliers = df[df["name"].str.contains("Альфа", case=False, na=False)]
        assert len(alpha_suppliers) == 1
        assert alpha_suppliers.iloc[0]["name"] == 'ООО "Альфа Поставки"'

    def test_documents_dataframe_creation(self):
        """Тест создания DataFrame для документов"""
        documents_data = self.create_mock_documents_data()
        df = pd.DataFrame(documents_data)

        assert len(df) == 4
        assert list(df.columns) == [
            "id",
            "name",
            "supplier",
            "status",
            "created_date",
            "priority",
        ]
        assert df["created_date"].dtype == "datetime64[ns]"

    def test_documents_filter_by_status(self):
        """Тест фильтрации документов по статусу"""
        documents_data = self.create_mock_documents_data()
        df = pd.DataFrame(documents_data)

        # Фильтрация по статусу
        pending_docs = df[df["status"] == "pending"]
        assert len(pending_docs) == 1

        approved_docs = df[df["status"] == "approved"]
        assert len(approved_docs) == 1
        assert approved_docs.iloc[0]["name"] == "Спецификация товаров №003"

    def test_documents_filter_by_priority(self):
        """Тест фильтрации документов по приоритету"""
        documents_data = self.create_mock_documents_data()
        df = pd.DataFrame(documents_data)

        # Фильтрация по приоритету
        high_priority = df[df["priority"] == "high"]
        assert len(high_priority) == 2
        assert all(high_priority["priority"] == "high")

    def test_documents_filter_by_supplier(self):
        """Тест фильтрации документов по поставщику"""
        documents_data = self.create_mock_documents_data()
        df = pd.DataFrame(documents_data)

        # Фильтрация по поставщику
        alpha_docs = df[df["supplier"] == 'ООО "Альфа Поставки"']
        assert len(alpha_docs) == 2
        assert all(alpha_docs["supplier"] == 'ООО "Альфа Поставки"')

    def test_suppliers_grouping_by_status(self):
        """Тест группировки поставщиков по статусу"""
        suppliers_data = self.create_mock_suppliers_data()
        df = pd.DataFrame(suppliers_data)

        # Группировка
        grouped = df.groupby("status").size()
        assert "active" in grouped
        assert "inactive" in grouped
        assert grouped["active"] == 3
        assert grouped["inactive"] == 1

    def test_documents_grouping_by_status(self):
        """Тест группировки документов по статусу"""
        documents_data = self.create_mock_documents_data()
        df = pd.DataFrame(documents_data)

        # Группировка
        grouped = df.groupby("status").size()
        assert "pending" in grouped
        assert "processing" in grouped
        assert "approved" in grouped
        assert "rejected" in grouped
        assert grouped["pending"] == 1
        assert grouped["processing"] == 1
        assert grouped["approved"] == 1
        assert grouped["rejected"] == 1

    def test_suppliers_statistics_calculation(self):
        """Тест расчета статистики по поставщикам"""
        suppliers_data = self.create_mock_suppliers_data()
        df = pd.DataFrame(suppliers_data)

        # Расчет статистики
        total_suppliers = len(df)
        active_count = len(df[df["status"] == "active"])
        avg_rating = df["rating"].mean()

        assert total_suppliers == 4
        assert active_count == 3
        assert 3.0 <= avg_rating <= 5.0

    def test_documents_time_filtering(self):
        """Тест фильтрации документов по времени"""
        documents_data = self.create_mock_documents_data()
        df = pd.DataFrame(documents_data)

        # Фильтрация по дате создания (последние 24 часа)
        recent_docs = df[
            df["created_date"] > datetime.datetime.now() - datetime.timedelta(days=1)
        ]
        assert len(recent_docs) >= 1  # Должен быть хотя бы один документ

    def test_suppliers_rating_distribution(self):
        """Тест распределения рейтингов поставщиков"""
        suppliers_data = self.create_mock_suppliers_data()
        df = pd.DataFrame(suppliers_data)

        # Проверка диапазона рейтингов
        assert df["rating"].min() >= 0.0
        assert df["rating"].max() <= 5.0

        # Проверка наличия различных рейтингов
        unique_ratings = df["rating"].nunique()
        assert unique_ratings >= 3  # Должно быть несколько разных рейтингов

    def test_empty_data_handling(self):
        """Тест обработки пустых данных"""
        # Пустые списки
        empty_suppliers = []
        empty_documents = []

        suppliers_df = pd.DataFrame(empty_suppliers)
        documents_df = pd.DataFrame(empty_documents)

        assert len(suppliers_df) == 0
        assert len(documents_df) == 0
        assert list(suppliers_df.columns) == []  # Пустой DataFrame без колонок
        assert list(documents_df.columns) == []

    def test_mixed_data_types_handling(self):
        """Тест обработки смешанных типов данных"""
        # Данные с разными типами
        mixed_suppliers = [
            {
                "id": 1,
                "name": 'ООО "Тест"',
                "contact_person": "Иванов",
                "email": "test@test.ru",
                "phone": "1234567890",
                "rating": 4.5,
                "status": "active",
            },
            {
                "id": "2",  # Строковый ID
                "name": 'ЗАО "Тест2"',
                "contact_person": None,  # None значение
                "email": "",  # Пустая строка
                "phone": None,
                "rating": 3.7,
                "status": "inactive",
            },
        ]

        df = pd.DataFrame(mixed_suppliers)

        # Проверка типов данных после создания DataFrame
        assert df["id"].dtype == "object"  # Смешанные типы становятся object
        assert df["rating"].dtype == "float64"
        assert df["name"].dtype == "object"

    @patch("streamlit_ui.st")
    def test_render_suppliers_with_filters(self, mock_st):
        """Тест отображения поставщиков с фильтрами"""
        from streamlit_ui import render_suppliers

        # Мокаем session_state с тестовыми данными
        mock_st.session_state = {"suppliers": self.create_mock_suppliers_data()}

        # Мокаем streamlit компоненты
        mock_st.title = MagicMock()
        mock_st.tabs.return_value = [MagicMock(), MagicMock(), MagicMock()]
        mock_st.columns.return_value = [MagicMock(), MagicMock(), MagicMock()]
        mock_st.selectbox.side_effect = [
            "active",
            "active",
        ]  # status_filter, status_form
        mock_st.slider.return_value = 4.0  # rating_filter
        mock_st.text_input.return_value = "Альфа"  # search_term
        mock_st.dataframe = MagicMock()

        # Вызываем функцию
        try:
            render_suppliers()
            # Проверяем, что функция отработала без ошибок
            mock_st.title.assert_called()
        except Exception as e:
            pytest.fail(f"Ошибка при вызове render_suppliers с фильтрами: {e}")

    @patch("streamlit_ui.st")
    def test_render_kanban_with_filters(self, mock_st):
        """Тест отображения канбан-доски с фильтрами"""
        from streamlit_ui import render_kanban

        # Мокаем session_state с тестовыми данными
        mock_st.session_state = {"documents": self.create_mock_documents_data()}

        # Мокаем streamlit компоненты
        mock_st.title = MagicMock()
        mock_st.columns.return_value = [
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
        ]
        mock_st.selectbox.side_effect = [
            "Все",
            "Все",
        ]  # priority_filter, supplier_filter
        mock_st.button.return_value = False

        # Вызываем функцию
        try:
            render_kanban()
            mock_st.title.assert_called()
        except Exception as e:
            pytest.fail(f"Ошибка при вызове render_kanban с фильтрами: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
