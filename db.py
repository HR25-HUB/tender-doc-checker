import json
import sqlite3
from datetime import datetime
from typing import Optional

from src.models import (
    SupplierHistory,
    SupplierInfo,
    SupplierPerformanceMetrics,
    SupplierTransaction,
)

DB_PATH = "data/history.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)

    # Существующая таблица отчетов
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS report_history (
            id INTEGER PRIMARY KEY,
            filename TEXT,
            checked_at TEXT,
            result TEXT
        )
    """
    )

    # Добавляем новые столбцы в report_history при необходимости (идемпотентно)
    try:
        cursor = conn.cursor()
        existing_columns = [
            row[1]
            for row in cursor.execute("PRAGMA table_info(report_history)").fetchall()
        ]

        def _add_column_if_missing(col_name: str, col_def: str):
            nonlocal existing_columns
            if col_name not in existing_columns:
                cursor.execute(f"ALTER TABLE report_history ADD COLUMN {col_def}")
                # Обновляем список столбцов для последующих проверок
                existing_columns = [
                    row[1]
                    for row in cursor.execute(
                        "PRAGMA table_info(report_history)"
                    ).fetchall()
                ]

        # Новые поля для аудита и фильтрации
        _add_column_if_missing("user_id", "user_id TEXT")
        _add_column_if_missing("standard_version", "standard_version TEXT")
        _add_column_if_missing("source", "source TEXT")
        _add_column_if_missing("doc_type", "doc_type TEXT")
        _add_column_if_missing(
            "created_at", "created_at TEXT DEFAULT CURRENT_TIMESTAMP"
        )
    except Exception:
        # Безопасно игнорируем ошибки добавления столбцов, чтобы не нарушать инициализацию
        pass

    # === НОВЫЕ ТАБЛИЦЫ ДЛЯ ПОСТАВЩИКОВ (TASK 2.2.1) ===

    # Таблица поставщиков
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS suppliers (
            supplier_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            inn TEXT UNIQUE,
            kpp TEXT,
            contact_person TEXT,
            phone TEXT,
            email TEXT,
            address TEXT,
            rating REAL DEFAULT 0.0,
            cooperation_status TEXT DEFAULT 'на проверке',
            first_cooperation_date TEXT,
            last_transaction_date TEXT,
            overall_rating REAL DEFAULT 0.0,
            reliability_score REAL DEFAULT 0.0,
            risk_level TEXT DEFAULT 'средний',
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    # Таблица документов поставщиков
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS supplier_documents (
            document_id INTEGER PRIMARY KEY,
            supplier_id INTEGER NOT NULL,
            document_type TEXT NOT NULL,
            document_name TEXT NOT NULL,
            file_path TEXT,
            upload_date TEXT DEFAULT CURRENT_TIMESTAMP,
            document_date TEXT,
            status TEXT DEFAULT 'активный',
            checksum TEXT,
            file_size INTEGER,
            content_summary TEXT,
            FOREIGN KEY (supplier_id) REFERENCES suppliers (supplier_id)
        )
    """
    )

    # Таблица истории цен
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS price_history (
            price_id INTEGER PRIMARY KEY,
            supplier_id INTEGER NOT NULL,
            product_code TEXT NOT NULL,
            product_name TEXT,
            price REAL NOT NULL,
            currency TEXT DEFAULT 'RUB',
            price_type TEXT DEFAULT 'base',
            valid_from TEXT NOT NULL,
            valid_to TEXT,
            quantity_min REAL,
            quantity_max REAL,
            unit_of_measure TEXT,
            discount_rate REAL DEFAULT 0.0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (supplier_id) REFERENCES suppliers (supplier_id)
        )
    """
    )

    # Таблица транзакций поставщиков
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS supplier_transactions (
            transaction_id TEXT PRIMARY KEY,
            supplier_id INTEGER NOT NULL,
            transaction_date TEXT NOT NULL,
            transaction_type TEXT NOT NULL,
            amount REAL NOT NULL,
            currency TEXT DEFAULT 'RUB',
            status TEXT NOT NULL,
            description TEXT,
            order_number TEXT,
            invoice_number TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (supplier_id) REFERENCES suppliers (supplier_id)
        )
    """
    )

    # Таблица метрик производительности поставщиков
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS supplier_performance_metrics (
            metric_id INTEGER PRIMARY KEY,
            supplier_id INTEGER NOT NULL,
            period_start TEXT NOT NULL,
            period_end TEXT NOT NULL,
            total_orders INTEGER DEFAULT 0,
            completed_orders INTEGER DEFAULT 0,
            cancelled_orders INTEGER DEFAULT 0,
            total_amount REAL DEFAULT 0.0,
            on_time_delivery_rate REAL DEFAULT 0.0,
            quality_rating REAL DEFAULT 0.0,
            customer_satisfaction REAL DEFAULT 0.0,
            average_order_value REAL DEFAULT 0.0,
            payment_terms_compliance REAL DEFAULT 0.0,
            discount_rate REAL DEFAULT 0.0,
            complaints_count INTEGER DEFAULT 0,
            returns_count INTEGER DEFAULT 0,
            late_deliveries INTEGER DEFAULT 0,
            quality_issues INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (supplier_id) REFERENCES suppliers (supplier_id)
        )
    """
    )

    # === ДОБАВЛЕНИЕ НОВЫХ СТОЛБЦОВ И ОГРАНИЧЕНИЙ (TASK: статусы документов, уникальные ограничения, индексы) ===

    # Добавляем новые столбцы в supplier_documents при необходимости
    cursor = conn.cursor()
    existing_columns = [
        row[1]
        for row in cursor.execute("PRAGMA table_info(supplier_documents)").fetchall()
    ]

    if "contract_number" not in existing_columns:
        cursor.execute("ALTER TABLE supplier_documents ADD COLUMN contract_number TEXT")
    if "version" not in existing_columns:
        cursor.execute(
            "ALTER TABLE supplier_documents ADD COLUMN version INTEGER DEFAULT 1"
        )
    if "is_latest_version" not in existing_columns:
        cursor.execute(
            "ALTER TABLE supplier_documents ADD COLUMN is_latest_version BOOLEAN DEFAULT 1"
        )
    if "created_at" not in existing_columns:
        cursor.execute(
            "ALTER TABLE supplier_documents ADD COLUMN created_at TEXT DEFAULT CURRENT_TIMESTAMP"
        )
    if "updated_at" not in existing_columns:
        cursor.execute(
            "ALTER TABLE supplier_documents ADD COLUMN updated_at TEXT DEFAULT CURRENT_TIMESTAMP"
        )

    # Обновляем CHECK constraint для статуса документов
    try:
        cursor.execute(
            """
            UPDATE supplier_documents
            SET status = 'активный'
            WHERE status NOT IN ('активный', 'архивный', 'удален', 'на_проверке', 'отклонен', 'истекший')
        """
        )
    except sqlite3.OperationalError:
        # Если CHECK constraint не поддерживается, продолжаем без ошибок
        pass

    # === ИНДЕКСЫ ДЛЯ ОПТИМИЗАЦИИ ЗАПРОСОВ (TASK 2.2.3) ===

    # Индексы для таблицы suppliers
    conn.execute("CREATE INDEX IF NOT EXISTS idx_suppliers_inn ON suppliers (inn)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_suppliers_status ON suppliers (cooperation_status)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_suppliers_rating ON suppliers (rating)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_suppliers_last_transaction ON suppliers (last_transaction_date)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_suppliers_created_at ON suppliers (created_at)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_suppliers_updated_at ON suppliers (updated_at)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_suppliers_inn_kpp ON suppliers (inn, kpp)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_suppliers_risk_level ON suppliers (risk_level)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_suppliers_email ON suppliers (email)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_suppliers_name ON suppliers (name)")

    # Индексы для таблицы supplier_documents
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_supplier_documents_supplier_id ON supplier_documents (supplier_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_supplier_documents_type ON supplier_documents (document_type)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_supplier_documents_status ON supplier_documents (status)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_supplier_documents_upload_date ON supplier_documents (upload_date)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_supplier_documents_supplier_type ON supplier_documents (supplier_id, document_type)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_supplier_documents_contract_number ON supplier_documents (contract_number)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_supplier_documents_latest_version ON supplier_documents (supplier_id, is_latest_version)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_supplier_documents_created_at ON supplier_documents (created_at)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_supplier_documents_updated_at ON supplier_documents (updated_at)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_supplier_documents_status_date ON supplier_documents (status, upload_date)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_supplier_documents_checksum ON supplier_documents (checksum)"
    )

    # Уникальные ограничения для предотвращения дубликатов
    try:
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_document_version ON supplier_documents (supplier_id, document_name, document_type, version)"
        )
    except sqlite3.OperationalError:
        # Индекс может уже существовать, игнорируем ошибку
        pass

    try:
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_contract_number ON supplier_documents (contract_number) WHERE contract_number IS NOT NULL AND contract_number != ''"
        )
    except sqlite3.OperationalError:
        # Индекс может уже существовать, игнорируем ошибку
        pass

    # Индексы для таблицы price_history
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_price_history_supplier_id ON price_history (supplier_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_price_history_product_code ON price_history (product_code)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_price_history_valid_from ON price_history (valid_from)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_price_history_valid_to ON price_history (valid_to)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_price_history_supplier_product ON price_history (supplier_id, product_code)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_price_history_date_range ON price_history (valid_from, valid_to)"
    )

    # Индексы для таблицы supplier_transactions
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_supplier_transactions_supplier_id ON supplier_transactions (supplier_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_supplier_transactions_date ON supplier_transactions (transaction_date)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_supplier_transactions_type ON supplier_transactions (transaction_type)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_supplier_transactions_status ON supplier_transactions (status)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_supplier_transactions_supplier_date ON supplier_transactions (supplier_id, transaction_date)"
    )

    # Индексы для таблицы supplier_performance_metrics
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_performance_metrics_supplier_id ON supplier_performance_metrics (supplier_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_performance_metrics_period_end ON supplier_performance_metrics (period_end)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_performance_metrics_supplier_period ON supplier_performance_metrics (supplier_id, period_end)"
    )

    # Индексы для таблицы report_history (существующая таблица)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_report_history_checked_at ON report_history (checked_at)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_report_history_filename ON report_history (filename)"
    )
    # Новые индексы для расширенной фильтрации истории
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_report_history_user_id ON report_history (user_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_report_history_doc_type ON report_history (doc_type)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_report_history_created_at ON report_history (created_at)"
    )

    conn.commit()
    conn.close()


def save_report(filename, result: list):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        INSERT INTO report_history (filename, checked_at, result)
        VALUES (?, ?, ?)
    """,
        (filename, datetime.now().isoformat(), json.dumps(result, ensure_ascii=False)),
    )
    conn.commit()
    conn.close()


# === ФУНКЦИИ ДЛЯ РАБОТЫ С ПОСТАВЩИКАМИ (TASK 2.2.2) ===


def save_supplier_document(
    supplier_id: int,
    document_type: str,
    document_name: str,
    file_path: str = None,
    document_date: str = None,
    content_summary: str = None,
) -> int:
    """
    Сохраняет документ поставщика в базе данных.

    Args:
        supplier_id: ID поставщика
        document_type: Тип документа (например, 'коммерческое_предложение', 'договор', 'счет')
        document_name: Название документа
        file_path: Путь к файлу документа (опционально)
        document_date: Дата документа в формате ISO (опционально)
        content_summary: Краткое содержание документа (опционально)

    Returns:
        int: ID созданного документа

    Raises:
        sqlite3.Error: При ошибке работы с базой данных
    """
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()

        # Вычисляем размер файла и контрольную сумму, если файл существует
        file_size = None
        checksum = None
        if file_path:
            try:
                import hashlib
                import os

                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    with open(file_path, "rb") as f:
                        checksum = hashlib.md5(f.read()).hexdigest()
            except Exception:
                pass  # Игнорируем ошибки при работе с файлом

        cursor.execute(
            """
            INSERT INTO supplier_documents
            (supplier_id, document_type, document_name, file_path, document_date,
             checksum, file_size, content_summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                supplier_id,
                document_type,
                document_name,
                file_path,
                document_date,
                checksum,
                file_size,
                content_summary,
            ),
        )

        document_id = cursor.lastrowid
        conn.commit()
        return document_id

    finally:
        conn.close()


def get_supplier_history(supplier_id: int) -> SupplierHistory:
    """
    Получает историю поставщика по его ID из базы данных.

    Args:
        supplier_id: ID поставщика

    Returns:
        SupplierHistory: Объект с полной историей поставщика

    Note:
        Если поставщик не найден в БД, возвращает демонстрационные данные.
    """
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()

        # Получаем информацию о поставщике
        cursor.execute(
            """
            SELECT supplier_id, name, inn, kpp, contact_person, phone, email, address,
                   rating, cooperation_status, first_cooperation_date, last_transaction_date,
                   overall_rating, reliability_score, risk_level, notes
            FROM suppliers WHERE supplier_id = ?
        """,
            (supplier_id,),
        )

        supplier_row = cursor.fetchone()

        if supplier_row:
            # Создаем объект SupplierInfo из данных БД
            supplier_info = SupplierInfo(
                supplier_id=supplier_row[0],
                name=supplier_row[1],
                inn=supplier_row[2],
                kpp=supplier_row[3],
                contact_person=supplier_row[4],
                phone=supplier_row[5],
                email=supplier_row[6],
                address=supplier_row[7],
                rating=supplier_row[8] or 0.0,
            )

            # Получаем транзакции поставщика
            cursor.execute(
                """
                SELECT transaction_id, transaction_date, transaction_type, amount,
                       currency, status, description
                FROM supplier_transactions
                WHERE supplier_id = ?
                ORDER BY transaction_date DESC
            """,
                (supplier_id,),
            )

            transaction_rows = cursor.fetchall()
            transactions = []

            for row in transaction_rows:
                transactions.append(
                    SupplierTransaction(
                        transaction_id=row[0],
                        date=datetime.fromisoformat(row[1])
                        if row[1]
                        else datetime.now(),
                        transaction_type=row[2],
                        amount=row[3],
                        currency=row[4],
                        status=row[5],
                        description=row[6],
                    )
                )

            # Получаем последние метрики производительности
            cursor.execute(
                """
                SELECT period_start, period_end, total_orders, completed_orders,
                       cancelled_orders, total_amount, on_time_delivery_rate,
                       quality_rating, customer_satisfaction, average_order_value,
                       payment_terms_compliance, discount_rate, complaints_count,
                       returns_count, late_deliveries, quality_issues
                FROM supplier_performance_metrics
                WHERE supplier_id = ?
                ORDER BY period_end DESC
                LIMIT 1
            """,
                (supplier_id,),
            )

            metrics_row = cursor.fetchone()

            if metrics_row:
                performance_metrics = SupplierPerformanceMetrics(
                    period_start=datetime.fromisoformat(metrics_row[0]),
                    period_end=datetime.fromisoformat(metrics_row[1]),
                    total_orders=metrics_row[2],
                    completed_orders=metrics_row[3],
                    cancelled_orders=metrics_row[4],
                    total_amount=metrics_row[5],
                    on_time_delivery_rate=metrics_row[6],
                    quality_rating=metrics_row[7],
                    customer_satisfaction=metrics_row[8],
                    average_order_value=metrics_row[9],
                    payment_terms_compliance=metrics_row[10],
                    discount_rate=metrics_row[11],
                    complaints_count=metrics_row[12],
                    returns_count=metrics_row[13],
                    late_deliveries=metrics_row[14],
                    quality_issues=metrics_row[15],
                )
            else:
                # Создаем пустые метрики, если их нет
                performance_metrics = SupplierPerformanceMetrics(
                    period_start=datetime.now(),
                    period_end=datetime.now(),
                    total_orders=0,
                    completed_orders=0,
                    cancelled_orders=0,
                    total_amount=0.0,
                    on_time_delivery_rate=0.0,
                    quality_rating=0.0,
                    customer_satisfaction=0.0,
                    average_order_value=0.0,
                    payment_terms_compliance=0.0,
                    discount_rate=0.0,
                    complaints_count=0,
                    returns_count=0,
                    late_deliveries=0,
                    quality_issues=0,
                )

            return SupplierHistory(
                supplier_id=supplier_id,
                supplier_info=supplier_info,
                first_cooperation_date=datetime.fromisoformat(supplier_row[10])
                if supplier_row[10]
                else None,
                last_transaction_date=datetime.fromisoformat(supplier_row[11])
                if supplier_row[11]
                else None,
                cooperation_status=supplier_row[9] or "на проверке",
                transactions=transactions,
                total_transactions=len(transactions),
                current_metrics=performance_metrics,
                historical_metrics=[],
                overall_rating=supplier_row[12]
                if supplier_row[12] is not None
                else 0.0,
                reliability_score=supplier_row[13]
                if supplier_row[13] is not None
                else 0.0,
                risk_level=supplier_row[14] or "средний",
                product_categories=[],
                specializations=[],
                active_contracts=[],
                contract_history=[],
                notes=supplier_row[15],
                tags=[],
                last_updated=datetime.now(),
            )

        else:
            # Если поставщик не найден в БД, возвращаем демонстрационные данные
            return _get_demo_supplier_history(supplier_id)

    finally:
        conn.close()


def _get_demo_supplier_history(supplier_id: int) -> SupplierHistory:
    """
    Возвращает демонстрационные данные для поставщика.
    Используется как fallback, когда поставщик не найден в БД.
    """
    supplier_info = SupplierInfo(
        supplier_id=supplier_id,
        name=f"ООО Поставщик {supplier_id}",
        inn=f"123456789{supplier_id % 10}",
        kpp=f"12345678{supplier_id % 10}",
        contact_person="Иванов Иван Иванович",
        phone="+7 (495) 123-45-67",
        email=f"contact@supplier{supplier_id}.ru",
        address=f"г. Москва, ул. Поставщиков, д. {supplier_id}",
        rating=4.2 + (supplier_id % 10) * 0.05,
    )

    # Демонстрационные транзакции
    transactions = [
        SupplierTransaction(
            transaction_id=f"TXN-{supplier_id}-001",
            date=datetime(2024, 1, 15),
            transaction_type="заказ",
            amount=150000.00,
            currency="RUB",
            status="выполнена",
            description="Закупка офисного оборудования",
        ),
        SupplierTransaction(
            transaction_id=f"TXN-{supplier_id}-002",
            date=datetime(2024, 2, 20),
            transaction_type="поставка",
            amount=75000.00,
            currency="RUB",
            status="выполнена",
            description="Закупка канцелярских товаров",
        ),
        SupplierTransaction(
            transaction_id=f"TXN-{supplier_id}-003",
            date=datetime(2024, 3, 10),
            transaction_type="возврат",
            amount=5000.00,
            currency="RUB",
            status="выполнена",
            description="Возврат бракованного товара",
        ),
    ]

    # Демонстрационные метрики производительности
    performance_metrics = SupplierPerformanceMetrics(
        period_start=datetime(2024, 1, 1),
        period_end=datetime(2024, 12, 31),
        total_orders=25,
        completed_orders=23,
        cancelled_orders=2,
        total_amount=2500000.00,
        on_time_delivery_rate=84.0,
        quality_rating=4.3,
        customer_satisfaction=4.2,
        average_order_value=100000.00,
        payment_terms_compliance=95.0,
        discount_rate=5.0,
        complaints_count=1,
        returns_count=1,
        late_deliveries=2,
        quality_issues=1,
    )

    return SupplierHistory(
        supplier_id=supplier_id,
        supplier_info=supplier_info,
        first_cooperation_date=datetime(2023, 6, 1),
        last_transaction_date=datetime(2024, 3, 10),
        cooperation_status="активный",
        transactions=transactions,
        total_transactions=len(transactions),
        current_metrics=performance_metrics,
        historical_metrics=[],
        overall_rating=4.2,
        reliability_score=93.8,
        risk_level="низкий",
        product_categories=["офисное оборудование", "канцелярские товары"],
        specializations=["поставка офисной техники", "канцелярские принадлежности"],
        active_contracts=[f"CONTRACT-{supplier_id}-2024"],
        contract_history=[
            f"CONTRACT-{supplier_id}-2023",
            f"CONTRACT-{supplier_id}-2024",
        ],
        notes=f"Надежный поставщик с хорошей репутацией. Сотрудничество с {datetime(2023, 6, 1).strftime('%B %Y')}.",
        tags=["надежный", "проверенный"],
        last_updated=datetime.now(),
    )


# === ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ РАБОТЫ С ПОСТАВЩИКАМИ ===


def create_supplier(
    name: str,
    inn: str = None,
    kpp: str = None,
    contact_person: str = None,
    phone: str = None,
    email: str = None,
    address: str = None,
) -> int:
    """
    Создает нового поставщика в базе данных.

    Args:
        name: Название поставщика
        inn: ИНН поставщика
        kpp: КПП поставщика
        contact_person: Контактное лицо
        phone: Телефон
        email: Email
        address: Адрес

    Returns:
        int: ID созданного поставщика
    """
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO suppliers (name, inn, kpp, contact_person, phone, email, address)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (name, inn, kpp, contact_person, phone, email, address),
        )

        supplier_id = cursor.lastrowid
        conn.commit()
        return supplier_id

    finally:
        conn.close()


def get_supplier_documents(supplier_id: int, document_type: str = None) -> list[dict]:
    """
    Получает список документов поставщика.

    Args:
        supplier_id: ID поставщика
        document_type: Тип документа для фильтрации (опционально)

    Returns:
        List[dict]: Список документов поставщика
    """
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()

        if document_type:
            cursor.execute(
                """
                SELECT document_id, document_type, document_name, file_path,
                       upload_date, document_date, status, file_size, content_summary
                FROM supplier_documents
                WHERE supplier_id = ? AND document_type = ?
                ORDER BY upload_date DESC
            """,
                (supplier_id, document_type),
            )
        else:
            cursor.execute(
                """
                SELECT document_id, document_type, document_name, file_path,
                       upload_date, document_date, status, file_size, content_summary
                FROM supplier_documents
                WHERE supplier_id = ?
                ORDER BY upload_date DESC
            """,
                (supplier_id,),
            )

        rows = cursor.fetchall()
        documents = []

        for row in rows:
            documents.append(
                {
                    "supplier_id": supplier_id,
                    "document_id": row[0],
                    "document_type": row[1],
                    "document_name": row[2],
                    "file_path": row[3],
                    "upload_date": row[4],
                    "document_date": row[5],
                    "status": row[6],
                    "file_size": row[7],
                    "content_summary": row[8],
                }
            )

        return documents

    finally:
        conn.close()


def get_all_reports() -> list[dict]:
    """Получить все отчеты из базы данных"""
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, filename, checked_at, result
            FROM report_history
            ORDER BY checked_at DESC
        """
        )

        reports = []
        for row in cursor.fetchall():
            reports.append(
                {
                    "id": row[0],
                    "filename": row[1],
                    "checked_at": row[2],
                    "result": json.loads(row[3]) if row[3] else [],
                }
            )

        return reports

    finally:
        conn.close()


def get_all_suppliers() -> list[dict]:
    """Получить всех поставщиков из базы данных"""
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT supplier_id, name, inn, kpp, contact_person, phone, email,
                   address, rating, cooperation_status, first_cooperation_date,
                   last_transaction_date, overall_rating, reliability_score,
                   risk_level, notes, created_at, updated_at
            FROM suppliers
            ORDER BY name
        """
        )

        suppliers = []
        for row in cursor.fetchall():
            suppliers.append(
                {
                    "supplier_id": row[0],
                    "name": row[1],
                    "inn": row[2],
                    "kpp": row[3],
                    "contact_person": row[4],
                    "phone": row[5],
                    "email": row[6],
                    "address": row[7],
                    "rating": row[8],
                    "cooperation_status": row[9],
                    "first_cooperation_date": row[10],
                    "last_transaction_date": row[11],
                    "overall_rating": row[12],
                    "reliability_score": row[13],
                    "risk_level": row[14],
                    "notes": row[15],
                    "created_at": row[16],
                    "updated_at": row[17],
                }
            )

        return suppliers

    finally:
        conn.close()


def get_report_history(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    doc_type: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """Получить историю отчетов с фильтрами и пагинацией.
    Возвращает список записей и общее количество без учета пагинации.
    """
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()

        base_where = "WHERE 1=1"
        params: list = []
        params_count: list = []

        if start_date:
            base_where += " AND COALESCE(created_at, checked_at) >= ?"
            params.append(start_date)
            params_count.append(start_date)
        if end_date:
            base_where += " AND COALESCE(created_at, checked_at) <= ?"
            params.append(end_date)
            params_count.append(end_date)
        if doc_type:
            base_where += " AND doc_type = ?"
            params.append(doc_type)
            params_count.append(doc_type)
        if user_id:
            base_where += " AND user_id = ?"
            params.append(user_id)
            params_count.append(user_id)

        # Общее количество для пагинации
        count_sql = f"SELECT COUNT(*) FROM report_history {base_where}"
        cursor.execute(count_sql, tuple(params_count))
        total_count = cursor.fetchone()[0]

        # Данные с учетом лимита и смещения
        data_sql = f"""
            SELECT id, filename, checked_at, result, user_id, standard_version, source, doc_type, created_at
            FROM report_history
            {base_where}
            ORDER BY COALESCE(created_at, checked_at) DESC
            LIMIT ? OFFSET ?
        """
        cursor.execute(data_sql, (*params, limit, offset))

        rows = cursor.fetchall()
        history: list[dict] = []
        for row in rows:
            history.append(
                {
                    "id": row[0],
                    "filename": row[1],
                    "checked_at": row[2],
                    "result": json.loads(row[3]) if row[3] else [],
                    "user_id": row[4],
                    "standard_version": row[5],
                    "source": row[6],
                    "doc_type": row[7],
                    "created_at": row[8],
                }
            )

        return history, total_count
    finally:
        conn.close()
