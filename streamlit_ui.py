import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

# Импорты модулей системы
# Импорты бизнес-логики
from ui_business_logic import (
    AnalyticsEngine,
    DataInitializer,
    DocumentManager,
    FilterCriteria,
    SupplierManager,
)

# Конфигурация страницы
st.set_page_config(
    page_title="Tender Document Checker",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Стили CSS
st.markdown(
    """
<style>
.metric-card {
    background-color: #f0f2f6;
    padding: 1rem;
    border-radius: 0.5rem;
    border-left: 4px solid #1f77b4;
}
.status-pending { background-color: #fff3cd; }
.status-processing { background-color: #d1ecf1; }
.status-approved { background-color: #d4edda; }
.status-rejected { background-color: #f8d7da; }
.kanban-card {
    background-color: white;
    padding: 0.8rem;
    margin: 0.5rem 0;
    border-radius: 0.3rem;
    border: 1px solid #ddd;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}
</style>
""",
    unsafe_allow_html=True,
)


def init_session_state():
    """Инициализация состояния сессии"""
    if "suppliers" not in st.session_state:
        st.session_state.suppliers = DataInitializer.get_default_suppliers()

    if "documents" not in st.session_state:
        st.session_state.documents = DataInitializer.get_default_documents()


def render_dashboard():
    """Отображение дашборда с метриками"""
    st.title("📊 Дашборд аналитики")

    # Получение метрик из бизнес-логики
    metrics = AnalyticsEngine.generate_dashboard_metrics()

    # Основные метрики
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric(
            label="📄 Обработано документов",
            value=metrics["processed_documents"],
            delta=metrics["weekly_delta"]["processed_documents"],
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric(
            label="✅ Процент одобрений",
            value=f"{metrics['approval_percentage']}%",
            delta=metrics["weekly_delta"]["approval_percentage"],
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric(
            label="⏱️ Среднее время обработки",
            value=f"{metrics['processing_time']} часа",
            delta=metrics["weekly_delta"]["processing_time"],
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric(
            label="🏢 Активных поставщиков",
            value=metrics["active_suppliers"],
            delta=metrics["weekly_delta"]["active_suppliers"],
        )
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")

    # Графики
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📈 Динамика обработки документов")

        trend_data = AnalyticsEngine.generate_processing_trend_data()
        fig = px.line(
            trend_data,
            x="date",
            y="processed_documents",
            title="Количество обработанных документов по дням",
            labels={"date": "Дата", "processed_documents": "Количество документов"},
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("🎯 Статусы документов")

        status_data = AnalyticsEngine.generate_status_distribution()
        fig = px.pie(
            values=list(status_data.values()),
            names=list(status_data.keys()),
            title="Распределение по статусам",
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

    # Таблица последних документов
    st.subheader("📋 Последние обработанные документы")

    recent_docs = AnalyticsEngine.generate_recent_documents()
    st.dataframe(recent_docs, use_container_width=True)


def render_suppliers():
    """Отображение страницы управления поставщиками"""
    st.title("🏢 Управление поставщиками")

    # Вкладки для разных операций
    tab1, tab2, tab3 = st.tabs(
        ["📋 Список поставщиков", "➕ Добавить поставщика", "📊 Аналитика поставщиков"]
    )

    with tab1:
        st.subheader("Список поставщиков")

        # Расширенные фильтры поставщиков
        st.markdown("### 🔍 Фильтры поставщиков")

        with st.expander("Настроить фильтры", expanded=True):
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                status_filter = st.selectbox(
                    "Статус", ["Все", "active", "inactive", "blocked"]
                )

            with col2:
                search_term = st.text_input(
                    "Поиск", placeholder="Поиск по имени или email..."
                )

            with col3:
                category_filter = st.multiselect(
                    "Категория",
                    [
                        "Все категории",
                        "Производитель",
                        "Дистрибьютор",
                        "Сервис",
                        "Консультант",
                    ],
                    default=["Все категории"],
                )

            with col4:
                rating_filter = st.slider("Минимальный рейтинг", 0.0, 5.0, 0.0, 0.1)

            col_reset, col_apply = st.columns([1, 4])
            with col_reset:
                if st.button("🔄 Сбросить", key="reset_suppliers"):
                    st.rerun()
            with col_apply:
                if st.button(
                    "Применить фильтры", type="secondary", key="apply_suppliers"
                ):
                    st.rerun()

        # Создание критериев фильтрации
        criteria = FilterCriteria(
            status=status_filter if status_filter != "Все" else None,
            rating=rating_filter if rating_filter > 0 else None,
            search_term=search_term if search_term else None,
        )

        # Применение фильтров через бизнес-логику
        filtered_suppliers = SupplierManager.filter_suppliers(
            st.session_state.suppliers, criteria
        )

        # Отображение таблицы с возможностью редактирования
        if filtered_suppliers:
            for supplier in filtered_suppliers:
                with st.expander(
                    f"{supplier['name']} (Рейтинг: {supplier['rating']})⭐"
                ):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.write(f"**Контактное лицо:** {supplier['contact_person']}")
                        st.write(f"**Email:** {supplier['email']}")
                        st.write(f"**Телефон:** {supplier['phone']}")

                    with col2:
                        st.write(f"**Статус:** {supplier['status']}")
                        st.write(f"**ID:** {supplier['id']}")

                        # Кнопки действий
                        col_edit, col_delete = st.columns(2)
                        with col_edit:
                            if st.button(
                                "✏️ Редактировать", key=f"edit_{supplier['id']}"
                            ):
                                st.session_state[f"editing_{supplier['id']}"] = True
                        with col_delete:
                            if st.button("🗑️ Удалить", key=f"delete_{supplier['id']}"):
                                st.session_state.suppliers = (
                                    SupplierManager.remove_supplier(
                                        st.session_state.suppliers, supplier["id"]
                                    )
                                )
                                st.rerun()
        else:
            st.info("Поставщики не найдены")

    with tab2:
        st.subheader("Добавление нового поставщика")

        with st.form("add_supplier_form"):
            col1, col2 = st.columns(2)

            with col1:
                name = st.text_input("Название компании*")
                contact_person = st.text_input("Контактное лицо*")
                email = st.text_input("Email*")

            with col2:
                phone = st.text_input("Телефон")
                rating = st.slider("Начальный рейтинг", 0.0, 5.0, 3.0, 0.1)
                status = st.selectbox("Статус", ["active", "inactive"])

            submitted = st.form_submit_button("➕ Добавить поставщика")

            if submitted:
                if name and contact_person and email:
                    new_supplier = {
                        "name": name,
                        "contact_person": contact_person,
                        "email": email,
                        "phone": phone,
                        "rating": rating,
                        "status": status,
                    }
                    st.session_state.suppliers = SupplierManager.add_supplier(
                        st.session_state.suppliers, new_supplier
                    )
                    st.success(f"Поставщик '{name}' успешно добавлен!")
                    st.rerun()
                else:
                    st.error("Заполните все обязательные поля (отмечены *)")

    with tab3:
        st.subheader("Аналитика по поставщикам")

        # Получение статистики через бизнес-логику
        stats = SupplierManager.get_supplier_statistics(st.session_state.suppliers)

        if st.session_state.suppliers:
            suppliers_df = pd.DataFrame(st.session_state.suppliers)

            fig = px.bar(
                suppliers_df,
                x="name",
                y="rating",
                title="Рейтинги поставщиков",
                labels={"name": "Поставщик", "rating": "Рейтинг"},
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)

            # Статистика
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Всего поставщиков", stats["total_suppliers"])
            with col2:
                st.metric("Активных поставщиков", stats["active_suppliers"])
            with col3:
                st.metric("Средний рейтинг", str(stats["average_rating"]))


def render_kanban():
    """Отображение канбан-доски для документов"""
    st.title("📋 Канбан-доска документов")

    # Расширенные фильтры
    st.markdown("### 🔍 Фильтры документов")

    with st.expander("Настроить фильтры", expanded=True):
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            priority_filter = st.selectbox(
                "Приоритет", ["Все", "high", "medium", "low"]
            )

        with col2:
            supplier_filter = st.selectbox(
                "Поставщик",
                ["Все"]
                + list(set([doc["supplier"] for doc in st.session_state.documents])),
            )

        with col3:
            date_range = st.date_input(
                "Период",
                value=[
                    datetime.now().date() - timedelta(days=30),
                    datetime.now().date(),
                ],
                key="kanban_date_range",
            )

        with col4:
            search_term = st.text_input(
                "Поиск по названию", placeholder="Введите текст..."
            )

        col_reset, col_apply = st.columns([1, 4])
        with col_reset:
            if st.button("🔄 Сбросить"):
                st.rerun()
        with col_apply:
            if st.button("Применить фильтры", type="secondary"):
                st.rerun()

    # Создание критериев фильтрации
    criteria = FilterCriteria(
        priority=priority_filter if priority_filter != "Все" else None,
        supplier=supplier_filter if supplier_filter != "Все" else None,
    )

    # Фильтрация и группировка документов через бизнес-логику
    filtered_docs = DocumentManager.filter_documents(
        st.session_state.documents, criteria
    )
    status_groups = DocumentManager.group_documents_by_status(filtered_docs)

    # Колонки канбан-доски
    col1, col2, col3, col4 = st.columns(4)

    # Отображение колонок
    with col1:
        st.markdown("### 📥 Ожидают обработки")
        st.markdown(
            f"<div class='status-pending'>Документов: {len(status_groups['pending'])}</div>",
            unsafe_allow_html=True,
        )

        for doc in status_groups["pending"]:
            priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}[
                doc["priority"]
            ]
            st.markdown(
                f"""
            <div class="kanban-card">
                <strong>{doc['name']}</strong><br>
                <small>🏢 {doc['supplier']}</small><br>
                <small>📅 {doc['created_date'].strftime('%d.%m.%Y %H:%M')}</small><br>
                <small>{priority_emoji} {doc['priority']}</small>
            </div>
            """,
                unsafe_allow_html=True,
            )

            if st.button("▶️ Начать обработку", key=f"start_{doc['id']}"):
                st.session_state.documents = DocumentManager.update_document_status(
                    st.session_state.documents, doc["id"], "processing"
                )
                st.rerun()

    with col2:
        st.markdown("### ⚙️ В обработке")
        st.markdown(
            f"<div class='status-processing'>Документов: {len(status_groups['processing'])}</div>",
            unsafe_allow_html=True,
        )

        for doc in status_groups["processing"]:
            priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}[
                doc["priority"]
            ]
            st.markdown(
                f"""
            <div class="kanban-card">
                <strong>{doc['name']}</strong><br>
                <small>🏢 {doc['supplier']}</small><br>
                <small>📅 {doc['created_date'].strftime('%d.%m.%Y %H:%M')}</small><br>
                <small>{priority_emoji} {doc['priority']}</small>
            </div>
            """,
                unsafe_allow_html=True,
            )

            col_approve, col_reject = st.columns(2)
            with col_approve:
                if st.button("✅", key=f"approve_{doc['id']}"):
                    st.session_state.documents = DocumentManager.update_document_status(
                        st.session_state.documents, doc["id"], "approved"
                    )
                    st.rerun()
            with col_reject:
                if st.button("❌", key=f"reject_{doc['id']}"):
                    st.session_state.documents = DocumentManager.update_document_status(
                        st.session_state.documents, doc["id"], "rejected"
                    )
                    st.rerun()

    with col3:
        st.markdown("### ✅ Одобрено")
        st.markdown(
            f"<div class='status-approved'>Документов: {len(status_groups['approved'])}</div>",
            unsafe_allow_html=True,
        )

        for doc in status_groups["approved"]:
            priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}[
                doc["priority"]
            ]
            st.markdown(
                f"""
            <div class="kanban-card">
                <strong>{doc['name']}</strong><br>
                <small>🏢 {doc['supplier']}</small><br>
                <small>📅 {doc['created_date'].strftime('%d.%m.%Y %H:%M')}</small><br>
                <small>{priority_emoji} {doc['priority']}</small>
            </div>
            """,
                unsafe_allow_html=True,
            )

    with col4:
        st.markdown("### ❌ Отклонено")
        st.markdown(
            f"<div class='status-rejected'>Документов: {len(status_groups['rejected'])}</div>",
            unsafe_allow_html=True,
        )

        for doc in status_groups["rejected"]:
            priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}[
                doc["priority"]
            ]
            st.markdown(
                f"""
            <div class="kanban-card">
                <strong>{doc['name']}</strong><br>
                <small>🏢 {doc['supplier']}</small><br>
                <small>📅 {doc['created_date'].strftime('%d.%m.%Y %H:%M')}</small><br>
                <small>{priority_emoji} {doc['priority']}</small>
            </div>
            """,
                unsafe_allow_html=True,
            )

            if st.button("🔄 Вернуть в обработку", key=f"reprocess_{doc['id']}"):
                st.session_state.documents = DocumentManager.update_document_status(
                    st.session_state.documents, doc["id"], "pending"
                )
                st.rerun()


def render_document_checker():
    """Страница проверки документов"""
    st.title("📄 Проверка документов")

    # Валидация и загрузка файлов
    st.markdown("### 📁 Загрузка документов")

    uploaded_files = st.file_uploader(
        "Выберите файлы для проверки",
        type=["pdf", "docx", "xlsx", "png", "jpg", "jpeg"],
        accept_multiple_files=True,
        help="Поддерживаемые форматы: PDF, DOCX, XLSX, PNG, JPG, JPEG. Максимальный размер: 10MB на файл",
    )

    # Валидация файлов
    if uploaded_files:
        total_size = sum(file.size for file in uploaded_files)
        max_total_size = 50 * 1024 * 1024  # 50MB
        max_file_size = 10 * 1024 * 1024  # 10MB per file

        valid_files = []
        validation_errors = []

        for file in uploaded_files:
            if file.size > max_file_size:
                validation_errors.append(
                    f"❌ {file.name}: превышает 10MB ({file.size / 1024 / 1024:.1f}MB)"
                )
            else:
                valid_files.append(file)
                st.success(f"✅ {file.name}: {file.size / 1024:.1f}KB")

        if total_size > max_total_size:
            validation_errors.append("❌ Общий размер файлов превышает 50MB")

        if validation_errors:
            st.error("Ошибки валидации:")
            for error in validation_errors:
                st.write(error)
            uploaded_files = valid_files

        if uploaded_files:
            st.info(
                f"Валидных файлов: {len(uploaded_files)} из {len(uploaded_files) + len(validation_errors)}"
            )

            # Расширенные фильтры
            col1, col2, col3 = st.columns(3)

            with col1:
                suppliers = [s["name"] for s in st.session_state.suppliers]
                selected_supplier = st.selectbox("Выберите поставщика", suppliers)

            with col2:
                priority = st.selectbox("Приоритет", ["low", "medium", "high"])

            with col3:
                processing_mode = st.selectbox(
                    "Режим обработки", ["Стандартный", "Быстрый", "Тщательный"]
                )

            # Индикатор прогресса
            progress_bar = st.progress(0)
            status_text = st.empty()

            if st.button("🔍 Проверить документы", type="primary"):
                # Валидация перед обработкой
                if not selected_supplier:
                    st.error("Выберите поставщика")
                    return

                if not uploaded_files:
                    st.error("Загрузите хотя бы один файл")
                    return

                document_manager = DocumentManager()

                # Обработка с индикатором прогресса
                results = {}
                total_files = len(uploaded_files)

                for idx, file in enumerate(uploaded_files):
                    progress = (idx + 1) / total_files
                    progress_bar.progress(progress)
                    status_text.text(f"Обработка {idx + 1}/{total_files}: {file.name}")

                    # Обработка одного файла
                    file_results = document_manager.process_document_batch(
                        [file], selected_supplier, priority
                    )
                    if file_results:
                        results.update(file_results)

                    # Небольшая задержка для визуализации прогресса
                    import time

                    time.sleep(0.1)

                progress_bar.progress(1.0)
                status_text.text("Обработка завершена!")

                if results:
                    # Добавление нового документа
                    new_doc = document_manager.create_new_document(
                        selected_supplier,
                        priority,
                        [f.name for f in uploaded_files],
                        results,
                    )
                    st.session_state.documents.append(new_doc)

                    # Отображение результатов
                    st.success("Документы успешно обработаны!")

                    # Подробные результаты
                    with st.expander("📊 Подробные результаты"):
                        for file_name, result in results.items():
                            st.write(f"**{file_name}**:")
                            st.json(result)

                    # Действия после обработки
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        if st.button("📋 Сгенерировать отчет"):
                            report_path = document_manager.generate_document_report(
                                results, selected_supplier
                            )
                            with open(report_path, "rb") as f:
                                st.download_button(
                                    label="📥 Скачать отчет",
                                    data=f.read(),
                                    file_name=f"report_{selected_supplier}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                                    mime="application/pdf",
                                )

                    with col2:
                        email = st.text_input("Email для отправки отчета")
                        if email and st.button("📧 Отправить email"):
                            success = document_manager.send_document_email(
                                email, results, selected_supplier
                            )
                            if success:
                                st.success("Email отправлен!")

                    with col3:
                        if st.button("📋 Создать задачу в Bitrix24"):
                            task_id = document_manager.create_bitrix_document_task(
                                results, selected_supplier
                            )
                            if task_id:
                                st.success(f"Задача создана в Bitrix24: {task_id}")
                else:
                    st.error("Ошибка при обработке документов")


def main():
    """Главная функция приложения"""
    init_session_state()

    # Боковая панель навигации
    st.sidebar.title("🚀 Tender Document Checker")
    st.sidebar.markdown("---")

    page = st.sidebar.selectbox(
        "Выберите страницу",
        ["📊 Дашборд", "🏢 Поставщики", "📋 Канбан-доска", "📄 Проверка документов"],
    )

    # Отображение выбранной страницы
    if page == "📊 Дашборд":
        render_dashboard()
    elif page == "🏢 Поставщики":
        render_suppliers()
    elif page == "📋 Канбан-доска":
        render_kanban()
    elif page == "📄 Проверка документов":
        render_document_checker()

    # Информация в боковой панели
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📈 Быстрая статистика")
    st.sidebar.metric("Документов сегодня", "12")
    st.sidebar.metric(
        "Активных поставщиков",
        len([s for s in st.session_state.suppliers if s["status"] == "active"]),
    )
    st.sidebar.metric(
        "Задач в работе",
        len([d for d in st.session_state.documents if d["status"] == "processing"]),
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("### ℹ️ О системе")
    st.sidebar.info(
        "Tender Document Checker v2.0\n\n"
        "Система автоматизированной проверки\n"
        "тендерных документов с расширенной\n"
        "аналитикой и управлением поставщиками."
    )


if __name__ == "__main__":
    main()
