"""
Smoke-тесты для Streamlit UI
Проверка импортов и вызова ключевых функций с мок-данными
"""

import datetime
import os
import sys
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

# Добавляем путь к корню проекта для импортов
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Мокаем streamlit для тестов
sys.modules["streamlit"] = MagicMock()
sys.modules["plotly"] = MagicMock()
sys.modules["plotly.express"] = MagicMock()
sys.modules["plotly.graph_objects"] = MagicMock()
sys.modules["plotly.subplots"] = MagicMock()


class TestUISmoke:
    """Smoke-тесты для Streamlit UI компонентов"""

    def test_imports(self):
        """Проверка базовых импортов модуля streamlit_ui"""
        try:
            import streamlit_ui

            assert streamlit_ui is not None
        except ImportError as e:
            pytest.fail(f"Не удалось импортировать streamlit_ui: {e}")

    def test_streamlit_import(self):
        """Проверка импорта streamlit"""
        try:
            import streamlit as st

            assert st is not None
        except ImportError as e:
            pytest.fail(f"Не удалось импортировать streamlit: {e}")

    @patch("streamlit_ui.st")
    def test_init_session_state(self, mock_st):
        """Тест инициализации состояния сессии с мок-данными"""
        from streamlit_ui import init_session_state

        # Мокаем session_state
        mock_st.session_state = {}

        # Вызываем функцию
        init_session_state()

        # Проверяем, что данные были инициализированы
        assert "suppliers" in mock_st.session_state
        assert "documents" in mock_st.session_state
        assert len(mock_st.session_state["suppliers"]) >= 2
        assert len(mock_st.session_state["documents"]) >= 3

        # Проверяем структуру данных
        supplier = mock_st.session_state["suppliers"][0]
        assert "id" in supplier
        assert "name" in supplier
        assert "rating" in supplier

        document = mock_st.session_state["documents"][0]
        assert "id" in document
        assert "name" in document
        assert "status" in document
        assert "created_date" in document

    @patch("streamlit_ui.st")
    @patch("streamlit_ui.pd")
    def test_render_dashboard_basic(self, mock_pd, mock_st):
        """Базовый тест отображения дашборда"""
        from streamlit_ui import render_dashboard

        # Мокаем необходимые компоненты
        mock_st.columns.return_value = [
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
        ]
        mock_st.markdown = MagicMock()
        mock_st.metric = MagicMock()
        mock_st.subheader = MagicMock()
        mock_st.title = MagicMock()

        # Мокаем pandas DataFrame
        mock_df = MagicMock()
        mock_pd.DataFrame.return_value = mock_df
        mock_pd.date_range.return_value = pd.date_range("2024-01-01", periods=5)

        # Вызываем функцию без ошибок
        try:
            render_dashboard()
        except Exception as e:
            pytest.fail(f"Ошибка при вызове render_dashboard: {e}")

    @patch("streamlit_ui.st")
    def test_render_suppliers_basic(self, mock_st):
        """Базовый тест отображения страницы поставщиков"""
        from streamlit_ui import render_suppliers

        # Мокаем session_state
        mock_st.session_state = {
            "suppliers": [
                {
                    "id": 1,
                    "name": "Тестовый поставщик",
                    "contact_person": "Иванов И.И.",
                    "email": "test@example.com",
                    "phone": "+7 999 123-45-67",
                    "rating": 4.5,
                    "status": "active",
                }
            ]
        }

        # Мокаем streamlit компоненты
        mock_st.title = MagicMock()
        mock_st.tabs.return_value = [MagicMock(), MagicMock(), MagicMock()]
        mock_st.columns.return_value = [MagicMock(), MagicMock(), MagicMock()]
        mock_st.selectbox = MagicMock()
        mock_st.slider = MagicMock()
        mock_st.text_input = MagicMock()
        mock_st.dataframe = MagicMock()

        # Вызываем функцию без ошибок
        try:
            render_suppliers()
        except Exception as e:
            pytest.fail(f"Ошибка при вызове render_suppliers: {e}")

    @patch("streamlit_ui.st")
    def test_render_kanban_basic(self, mock_st):
        """Базовый тест отображения канбан-доски"""
        from streamlit_ui import render_kanban

        # Мокаем session_state с документами
        mock_st.session_state = {
            "documents": [
                {
                    "id": 1,
                    "name": "Тестовый документ",
                    "supplier": "Тестовый поставщик",
                    "status": "pending",
                    "created_date": datetime.datetime.now(),
                    "priority": "high",
                }
            ]
        }

        # Мокаем streamlit компоненты
        mock_st.title = MagicMock()
        mock_st.columns.return_value = [
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
        ]
        mock_st.selectbox = MagicMock()
        mock_st.button = MagicMock()

        # Вызываем функцию без ошибок
        try:
            render_kanban()
        except Exception as e:
            pytest.fail(f"Ошибка при вызове render_kanban: {e}")

    @patch("streamlit_ui.st")
    def test_render_document_checker_basic(self, mock_st):
        """Базовый тест отображения страницы проверки документов"""
        from streamlit_ui import render_document_checker

        # Мокаем streamlit компоненты
        mock_st.title = MagicMock()
        mock_st.file_uploader = MagicMock(return_value=[])
        mock_st.text_input = MagicMock()
        mock_st.button = MagicMock(return_value=False)

        # Вызываем функцию без ошибок
        try:
            render_document_checker()
        except Exception as e:
            pytest.fail(f"Ошибка при вызове render_document_checker: {e}")

    @patch("streamlit_ui.st")
    @patch("streamlit_ui.init_session_state")
    def test_main_function_basic(self, mock_init, mock_st):
        """Базовый тест главной функции"""
        from streamlit_ui import main

        # Мокаем streamlit компоненты
        mock_st.sidebar.title = MagicMock()
        mock_st.sidebar.markdown = MagicMock()
        mock_st.sidebar.selectbox.return_value = "📊 Дашборд"
        mock_st.sidebar.metric = MagicMock()
        mock_st.sidebar.info = MagicMock()

        # Вызываем главную функцию без ошибок
        try:
            main()
            mock_init.assert_called_once()
        except Exception as e:
            pytest.fail(f"Ошибка при вызове main: {e}")

    def test_session_state_data_structure(self):
        """Проверка структуры данных в session_state"""
        from streamlit_ui import init_session_state

        # Создаем мок-объект для session_state
        class MockSessionState:
            def __init__(self):
                self.__dict__ = {}

        mock_state = MockSessionState()

        with patch("streamlit_ui.st.session_state", mock_state):
            init_session_state()

            # Проверяем структуру поставщиков
            assert hasattr(mock_state, "suppliers")
            suppliers = mock_state.suppliers
            assert isinstance(suppliers, list)
            assert len(suppliers) > 0

            supplier = suppliers[0]
            required_supplier_fields = [
                "id",
                "name",
                "contact_person",
                "email",
                "phone",
                "rating",
                "status",
            ]
            for field in required_supplier_fields:
                assert field in supplier

            # Проверяем структуру документов
            assert hasattr(mock_state, "documents")
            documents = mock_state.documents
            assert isinstance(documents, list)
            assert len(documents) > 0

            document = documents[0]
            required_document_fields = [
                "id",
                "name",
                "supplier",
                "status",
                "created_date",
                "priority",
            ]
            for field in required_document_fields:
                assert field in document


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
