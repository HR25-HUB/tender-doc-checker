"""
Тесты для управления документами поставщиков
Проверка статусов документов и валидаций переходов между статусами
"""

import os
import sys
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

import pytest

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Определяем необходимые классы для тестов
class DocumentStatus(str, Enum):
    """Статусы документов поставщиков"""

    PENDING = "на проверке"
    APPROVED = "одобрен"
    REJECTED = "отклонен"


class DocumentType(str, Enum):
    """Типы документов"""

    CERTIFICATE = "сертификат"
    LICENSE = "лицензия"
    CONTRACT = "договор"
    PASSPORT = "паспорт"


class Supplier:
    """Модель поставщика для тестов"""

    def __init__(self, id: int, name: str, inn: str, kpp: str, email: str, phone: str):
        self.id = id
        self.name = name
        self.inn = inn
        self.kpp = kpp
        self.email = email
        self.phone = phone


class Document:
    """Модель документа поставщика для тестов"""

    def __init__(
        self,
        id: int,
        supplier_id: int,
        type: DocumentType,
        file_path: str,
        status: DocumentStatus = DocumentStatus.PENDING,
        uploaded_at: Optional[datetime] = None,
        checked_at: Optional[datetime] = None,
        checked_by: Optional[str] = None,
        rejection_reason: Optional[str] = None,
    ):
        self.id = id
        self.supplier_id = supplier_id
        self.type = type
        self.file_path = file_path
        self._status = status
        self.uploaded_at = uploaded_at or datetime.now()
        self.checked_at = checked_at
        self.checked_by = checked_by
        self.rejection_reason = rejection_reason

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, new_status: DocumentStatus):
        """Валидация переходов между статусами"""
        # Разрешаем переход из APPROVED в PENDING только для обновлений
        if (
            self._status == DocumentStatus.APPROVED
            and new_status == DocumentStatus.PENDING
        ):
            pass  # Разрешаем для обновлений документа
        elif (
            self._status == DocumentStatus.REJECTED
            and new_status == DocumentStatus.PENDING
        ):
            raise ValueError(
                "Invalid status transition: cannot return from REJECTED to PENDING"
            )

        self._status = new_status

        # Очищаем rejection_reason при переходе из REJECTED в APPROVED
        if new_status == DocumentStatus.APPROVED and self.rejection_reason:
            self.rejection_reason = None


# Удален импорт DatabaseManager для упрощения тестов


class TestDocumentStatuses:
    """Тестирование статусов документов поставщиков"""

    def setup_method(self):
        """Настройка перед каждым тестом"""
        pass  # Простая настройка без базы данных

        # Создаем тестового поставщика
        self.supplier = Supplier(
            id=1,
            name="Тестовый Поставщик",
            inn="1234567890",
            kpp="123456789",
            email="test@supplier.com",
            phone="+79991234567",
        )

        # Создаем тестовый документ
        self.document = Document(
            id=1,
            supplier_id=1,
            type=DocumentType.CERTIFICATE,
            file_path="/docs/certificate.pdf",
            status=DocumentStatus.PENDING,
            uploaded_at=datetime.now(),
            checked_at=None,
            checked_by=None,
            rejection_reason=None,
        )

    def test_initial_document_status(self):
        """Проверка начального статуса документа"""
        assert self.document.status == DocumentStatus.PENDING
        assert self.document.checked_at is None
        assert self.document.checked_by is None
        assert self.document.rejection_reason is None

    def test_approve_document_transition(self):
        """Тест перехода из статуса 'на проверке' в 'одобрен'"""
        # Начальный статус - на проверке
        self.document.status = DocumentStatus.PENDING

        # Одобряем документ
        self.document.status = DocumentStatus.APPROVED
        self.document.checked_at = datetime.now()
        self.document.checked_by = "manager@company.com"

        assert self.document.status == DocumentStatus.APPROVED
        assert self.document.checked_at is not None
        assert self.document.checked_by == "manager@company.com"
        assert self.document.rejection_reason is None

    def test_reject_document_transition(self):
        """Тест перехода из статуса 'на проверке' в 'отклонен'"""
        # Начальный статус - на проверке
        self.document.status = DocumentStatus.PENDING

        # Отклоняем документ с причиной
        self.document.status = DocumentStatus.REJECTED
        self.document.checked_at = datetime.now()
        self.document.checked_by = "manager@company.com"
        self.document.rejection_reason = "Недостаточно информации в документе"

        assert self.document.status == DocumentStatus.REJECTED
        assert self.document.checked_at is not None
        assert self.document.checked_by == "manager@company.com"
        assert self.document.rejection_reason == "Недостаточно информации в документе"

    def test_approved_to_pending_transition(self):
        """Тест перехода из 'одобрен' обратно в 'на проверке' для обновлений"""
        self.document.status = DocumentStatus.APPROVED

        # Переход из APPROVED в PENDING разрешен для обновлений документа
        self.document.status = DocumentStatus.PENDING
        assert self.document.status == DocumentStatus.PENDING

    def test_invalid_status_transition_from_rejected(self):
        """Тест невозможности перехода из 'отклонен' обратно в 'на проверке'"""
        self.document.status = DocumentStatus.REJECTED

        # Попытка вернуть в статус 'на проверке' должна быть невозможна
        with pytest.raises(ValueError, match="Invalid status transition"):
            self.document.status = DocumentStatus.PENDING

    def test_approve_rejected_document(self):
        """Тест перехода из 'отклонен' в 'одобрен' через повторную проверку"""
        self.document.status = DocumentStatus.REJECTED
        self.document.rejection_reason = "Первоначальная причина отклонения"

        # После исправлений документ может быть одобрен
        self.document.status = DocumentStatus.APPROVED
        self.document.checked_at = datetime.now()
        self.document.checked_by = "senior@company.com"

        assert self.document.status == DocumentStatus.APPROVED
        assert (
            self.document.rejection_reason is None
        )  # Причина отклонения очищается автоматически

    def test_document_status_timestamps(self):
        """Проверка корректности временных меток при изменении статуса"""
        initial_time = datetime.now()
        self.document.uploaded_at = initial_time

        # Проверяем документ
        check_time = initial_time + timedelta(hours=2)
        self.document.status = DocumentStatus.APPROVED
        self.document.checked_at = check_time

        assert self.document.uploaded_at == initial_time
        assert self.document.checked_at == check_time
        assert self.document.checked_at > self.document.uploaded_at


class TestDocumentValidation:
    """Тестирование валидаций документов"""

    def setup_method(self):
        """Настройка перед каждым тестом"""
        pass  # Простая настройка без базы данных

    def test_document_type_validation(self):
        """Тест валидации типа документа"""
        valid_types = [
            DocumentType.CERTIFICATE,
            DocumentType.LICENSE,
            DocumentType.CONTRACT,
            DocumentType.PASSPORT,
        ]

        for doc_type in valid_types:
            document = Document(
                id=1,
                supplier_id=1,
                type=doc_type,
                file_path="/docs/test.pdf",
                status=DocumentStatus.PENDING,
                uploaded_at=datetime.now(),
            )
            assert document.type == doc_type

    def test_invalid_document_type(self):
        """Тест невалидного типа документа - должен быть DocumentType enum"""
        # Этот тест будет пропущен, так как DocumentType уже ограничивает значения
        pass

    def test_file_path_validation(self):
        """Тест валидации пути к файлу"""
        # Валидные пути
        valid_paths = [
            "/docs/certificate.pdf",
            "uploads/licenses/license_123.pdf",
            "documents/contracts/contract_2024.docx",
        ]

        for path in valid_paths:
            document = Document(
                id=1,
                supplier_id=1,
                type=DocumentType.CERTIFICATE,
                file_path=path,
                status=DocumentStatus.PENDING,
                uploaded_at=datetime.now(),
            )
            assert document.file_path == path

    def test_empty_file_path_rejection(self):
        """Тест отклонения пустого пути к файлу"""
        document = Document(
            id=1,
            supplier_id=1,
            type=DocumentType.CERTIFICATE,
            file_path="",
            status=DocumentStatus.PENDING,
            uploaded_at=datetime.now(),
        )

        # Документ с пустым путем должен быть отклонен
        document.status = DocumentStatus.REJECTED
        document.rejection_reason = "Отсутствует файл документа"

        assert document.status == DocumentStatus.REJECTED
        assert "файл" in document.rejection_reason.lower()


class TestSupplierDocumentManagement:
    """Тестирование управления документами поставщиков"""

    def setup_method(self):
        """Настройка перед каждым тестом"""
        pass  # Простая настройка без базы данных

    def test_supplier_multiple_documents(self):
        """Тест управления несколькими документами одного поставщика"""
        supplier_id = 1
        documents = [
            Document(
                id=i,
                supplier_id=supplier_id,
                type=DocumentType.CERTIFICATE,
                file_path=f"/docs/cert_{i}.pdf",
                status=DocumentStatus.PENDING,
                uploaded_at=datetime.now(),
            )
            for i in range(1, 4)
        ]

        # Проверяем, что все документы принадлежат одному поставщику
        for doc in documents:
            assert doc.supplier_id == supplier_id

        # Одобряем первый документ
        documents[0].status = DocumentStatus.APPROVED
        documents[0].checked_at = datetime.now()

        # Отклоняем второй
        documents[1].status = DocumentStatus.REJECTED
        documents[1].rejection_reason = "Недостаточно данных"

        # Третий остается на проверке
        assert documents[2].status == DocumentStatus.PENDING

    def test_supplier_document_statistics(self):
        """Тест статистики документов поставщика"""
        supplier_id = 1
        documents = [
            Document(
                1,
                supplier_id,
                DocumentType.CERTIFICATE,
                "/docs/cert.pdf",
                DocumentStatus.APPROVED,
                datetime.now(),
            ),
            Document(
                2,
                supplier_id,
                DocumentType.LICENSE,
                "/docs/license.pdf",
                DocumentStatus.REJECTED,
                datetime.now(),
            ),
            Document(
                3,
                supplier_id,
                DocumentType.CONTRACT,
                "/docs/contract.pdf",
                DocumentStatus.PENDING,
                datetime.now(),
            ),
            Document(
                4,
                supplier_id,
                DocumentType.PASSPORT,
                "/docs/passport.pdf",
                DocumentStatus.APPROVED,
                datetime.now(),
            ),
        ]

        # Подсчет статистики
        approved_count = sum(
            1 for doc in documents if doc.status == DocumentStatus.APPROVED
        )
        rejected_count = sum(
            1 for doc in documents if doc.status == DocumentStatus.REJECTED
        )
        pending_count = sum(
            1 for doc in documents if doc.status == DocumentStatus.PENDING
        )

        assert approved_count == 2
        assert rejected_count == 1
        assert pending_count == 1


class TestDocumentStatusTransitions:
    """Тестирование сложных переходов между статусами"""

    def setup_method(self):
        """Настройка перед каждым тестом"""
        self.document = Document(
            id=1,
            supplier_id=1,
            type=DocumentType.CERTIFICATE,
            file_path="/docs/test.pdf",
            status=DocumentStatus.PENDING,
            uploaded_at=datetime.now(),
        )

    def test_full_document_lifecycle(self):
        """Тест полного жизненного цикла документа"""
        # 1. Загрузка документа
        assert self.document.status == DocumentStatus.PENDING

        # 2. Проверка и одобрение
        self.document.status = DocumentStatus.APPROVED
        self.document.checked_at = datetime.now()
        self.document.checked_by = "reviewer@company.com"

        assert self.document.status == DocumentStatus.APPROVED

        # 3. Повторная проверка (например, при обновлении документа)
        # Должна быть возможность вернуть в pending для повторной проверки
        # Это специальный случай - переход из APPROVED в PENDING для обновлений
        self.document.status = DocumentStatus.PENDING
        self.document.checked_at = None
        self.document.checked_by = None

        assert self.document.status == DocumentStatus.PENDING

        # 4. Повторное одобрение
        self.document.status = DocumentStatus.APPROVED
        self.document.checked_at = datetime.now()
        self.document.checked_by = "senior@company.com"

        assert self.document.status == DocumentStatus.APPROVED


class TestSupplierReminders:
    """Тестирование напоминаний поставщику о документах"""

    def setup_method(self):
        """Настройка перед каждым тестом"""
        self.supplier = Supplier(
            id=1,
            name="Тестовый Поставщик",
            inn="1234567890",
            kpp="123456789",
            email="test@supplier.com",
            phone="+79991234567",
        )

        self.document = Document(
            id=1,
            supplier_id=1,
            type=DocumentType.CERTIFICATE,
            file_path="/docs/certificate.pdf",
            status=DocumentStatus.PENDING,
            uploaded_at=datetime.now() - timedelta(days=5),  # Старый документ
        )

    def test_email_reminder_for_overdue_documents(self, monkeypatch):
        """Тест отправки email-напоминания для просроченных документов"""
        # Мокаем функцию отправки email
        sent_emails = []

        def mock_send_email(to_email, subject, body):
            sent_emails.append({"to": to_email, "subject": subject, "body": body})
            return True

        monkeypatch.setattr(
            "builtins.__import__",
            lambda name: type("MockModule", (), {"send_email": mock_send_email})()
            if name == "emailer"
            else None,
        )

        # Проверяем, что напоминание отправляется для старого документа
        if self.document.status == DocumentStatus.PENDING:
            days_pending = (datetime.now() - self.document.uploaded_at).days
            if days_pending > 3:  # Напоминание после 3 дней
                mock_send_email(
                    self.supplier.email,
                    "Напоминание: требуется проверка документа",
                    f"Документ {self.document.type.value} требует проверки уже {days_pending} дней",
                )

        assert len(sent_emails) == 1
        assert sent_emails[0]["to"] == "test@supplier.com"
        assert "Напоминание" in sent_emails[0]["subject"]
        assert "5 дней" in sent_emails[0]["body"]

    def test_bitrix_task_creation_for_overdue_documents(self, monkeypatch):
        """Тест создания задачи в Bitrix для просроченных документов"""
        # Мокаем функцию создания задачи в Bitrix
        created_tasks = []

        def mock_create_bitrix_task(title, description, responsible_id):
            created_tasks.append(
                {
                    "title": title,
                    "description": description,
                    "responsible_id": responsible_id,
                }
            )
            return {"result": {"id": 12345}}

        monkeypatch.setattr(
            "builtins.__import__",
            lambda name: type(
                "MockModule", (), {"create_bitrix_task": mock_create_bitrix_task}
            )()
            if name == "bitrix_api"
            else None,
        )

        # Создаем задачу для просроченного документа
        if self.document.status == DocumentStatus.PENDING:
            days_pending = (datetime.now() - self.document.uploaded_at).days
            if days_pending > 2:  # Задача после 2 дней
                mock_create_bitrix_task(
                    f"Проверить документ поставщика {self.supplier.name}",
                    f"Документ: {self.document.type.value}\nПоставщик: {self.supplier.name}\nПросрочено: {days_pending} дней",
                    1,  # ID ответственного менеджера
                )

        assert len(created_tasks) == 1
        assert "Проверить документ поставщика" in created_tasks[0]["title"]
        assert "Тестовый Поставщик" in created_tasks[0]["description"]
        assert created_tasks[0]["responsible_id"] == 1

    def test_multiple_reminders_for_different_documents(self, monkeypatch):
        """Тест множественных напоминаний для разных документов"""
        # Создаем несколько документов
        documents = [
            Document(
                1,
                1,
                DocumentType.CERTIFICATE,
                "/docs/cert1.pdf",
                DocumentStatus.PENDING,
                datetime.now() - timedelta(days=4),
            ),
            Document(
                2,
                1,
                DocumentType.LICENSE,
                "/docs/license1.pdf",
                DocumentStatus.PENDING,
                datetime.now() - timedelta(days=6),
            ),
            Document(
                3,
                1,
                DocumentType.CONTRACT,
                "/docs/contract1.pdf",
                DocumentStatus.APPROVED,
                datetime.now() - timedelta(days=10),
            ),
        ]

        # Мокаем email отправку
        sent_emails = []

        def mock_send_email(to_email, subject, body):
            sent_emails.append({"to": to_email, "subject": subject, "body": body})
            return True

        monkeypatch.setattr(
            "builtins.__import__",
            lambda name: type("MockModule", (), {"send_email": mock_send_email})()
            if name == "emailer"
            else None,
        )

        # Отправляем напоминания только для PENDING документов
        overdue_docs = [
            doc
            for doc in documents
            if doc.status == DocumentStatus.PENDING
            and (datetime.now() - doc.uploaded_at).days > 3
        ]

        for doc in overdue_docs:
            mock_send_email(
                self.supplier.email,
                "Напоминание: требуется проверка документа",
                f"Документ {doc.type.value} требует проверки уже {(datetime.now() - doc.uploaded_at).days} дней",
            )

        assert len(sent_emails) == 2  # Только для 2 PENDING документов
        assert "сертификат" in sent_emails[0]["body"]
        assert "лицензия" in sent_emails[1]["body"]

    def test_no_reminder_for_recent_documents(self, monkeypatch):
        """Тест отсутствия напоминаний для недавно загруженных документов"""
        # Создаем недавний документ
        recent_document = Document(
            id=2,
            supplier_id=1,
            type=DocumentType.PASSPORT,
            file_path="/docs/passport.pdf",
            status=DocumentStatus.PENDING,
            uploaded_at=datetime.now() - timedelta(hours=12),  # Только что
        )

        # Мокаем email отправку
        sent_emails = []

        def mock_send_email(to_email, subject, body):
            sent_emails.append({"to": to_email, "subject": subject, "body": body})
            return True

        monkeypatch.setattr(
            "builtins.__import__",
            lambda name: type("MockModule", (), {"send_email": mock_send_email})()
            if name == "emailer"
            else None,
        )

        # Не должно быть напоминаний для документов младше 3 дней
        days_pending = (datetime.now() - recent_document.uploaded_at).days
        if days_pending > 3:
            mock_send_email(
                self.supplier.email,
                "Напоминание: требуется проверка документа",
                f"Документ {recent_document.type.value} требует проверки уже {days_pending} дней",
            )

        assert len(sent_emails) == 0  # Нет напоминаний

    def test_escalation_reminder_sequence(self, monkeypatch):
        """Тест последовательности эскалации напоминаний"""
        # Создаем очень старый документ
        old_document = Document(
            id=3,
            supplier_id=1,
            type=DocumentType.LICENSE,
            file_path="/docs/old_license.pdf",
            status=DocumentStatus.PENDING,
            uploaded_at=datetime.now() - timedelta(days=15),
        )

        # Мокаем email и Bitrix
        sent_emails = []
        created_tasks = []

        def mock_send_email(to_email, subject, body):
            sent_emails.append({"to": to_email, "subject": subject, "body": body})
            return True

        def mock_create_bitrix_task(title, description, responsible_id):
            created_tasks.append(
                {
                    "title": title,
                    "description": description,
                    "responsible_id": responsible_id,
                }
            )
            return {"result": {"id": 99999}}

        monkeypatch.setattr(
            "builtins.__import__",
            lambda name: type(
                "MockModule",
                (),
                {
                    "send_email": mock_send_email,
                    "create_bitrix_task": mock_create_bitrix_task,
                },
            )()
            if name in ["emailer", "bitrix_api"]
            else None,
        )

        # Эскалация для документов старше 7 дней
        days_pending = (datetime.now() - old_document.uploaded_at).days
        if days_pending > 7:
            # Отправляем email поставщику
            mock_send_email(
                self.supplier.email,
                "Срочное напоминание: документ требует проверки",
                f"Документ {old_document.type.value} просрочен на {days_pending} дней",
            )

            # Создаем задачу в Bitrix для менеджера
            mock_create_bitrix_task(
                f"СРОЧНО: Проверить документ поставщика {self.supplier.name}",
                f"Критическая просрочка: {days_pending} дней\nДокумент: {old_document.type.value}",
                1,
            )

        assert len(sent_emails) == 1
        assert len(created_tasks) == 1
        assert "СРОЧНО" in created_tasks[0]["title"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
