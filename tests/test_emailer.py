from unittest.mock import MagicMock, mock_open, patch

import pytest

from emailer import (
    EmailTemplate,
    NotificationType,
    notify_batch_processing_completed,
    notify_document_check_completed,
    notify_price_alert,
    notify_supplier_status_changed,
    notify_system_error,
    send_notification_email,
    send_simple_email,
)


class TestNotificationType:
    """Тесты для enum NotificationType."""

    def test_notification_types_exist(self):
        """Проверка существования всех типов уведомлений."""
        expected_types = [
            "document_check_completed",
            "document_check_failed",
            "supplier_status_changed",
            "system_error",
            "batch_processing_completed",
            "price_alert",
            "contract_expiring",
            "quality_issue",
            "payment_reminder",
        ]

        for expected_type in expected_types:
            assert any(nt.value == expected_type for nt in NotificationType)


class TestEmailTemplate:
    """Тесты для класса EmailTemplate."""

    def test_get_template_document_check_completed(self):
        """Тест шаблона для завершения проверки документа."""
        template = EmailTemplate.get_template(
            NotificationType.DOCUMENT_CHECK_COMPLETED,
            document_name="test.pdf",
            overall_score=8.5,
            recommendation="Одобрить",
            violations_count=2,
        )

        assert "test.pdf" in template["subject"]
        assert "test.pdf" in template["body"]
        assert "8.5" in template["body"]
        assert "Одобрить" in template["body"]
        assert "2" in template["body"]

    def test_get_template_supplier_status_changed(self):
        """Тест шаблона для изменения статуса поставщика."""
        template = EmailTemplate.get_template(
            NotificationType.SUPPLIER_STATUS_CHANGED,
            supplier_name="ООО Тест",
            supplier_inn="1234567890",
            old_status="Активный",
            new_status="Заблокирован",
            change_date="01.01.2024 12:00",
            reason="Нарушение условий",
        )

        assert "ООО Тест" in template["subject"]
        assert "1234567890" in template["body"]
        assert "Активный" in template["body"]
        assert "Заблокирован" in template["body"]
        assert "Нарушение условий" in template["body"]

    def test_get_template_system_error(self):
        """Тест шаблона для системной ошибки."""
        template = EmailTemplate.get_template(
            NotificationType.SYSTEM_ERROR,
            error_type="DatabaseError",
            error_time="01.01.2024 12:00:00",
            error_description="Ошибка подключения к БД",
            error_traceback="Traceback...",
        )

        assert "DatabaseError" in template["subject"]
        assert "Ошибка подключения к БД" in template["body"]
        assert "Traceback..." in template["body"]

    def test_get_template_price_alert(self):
        """Тест шаблона для ценового предупреждения."""
        template = EmailTemplate.get_template(
            NotificationType.PRICE_ALERT,
            product_name="Товар А",
            supplier_name="ООО Поставщик",
            old_price=100.0,
            new_price=150.0,
            currency="RUB",
            price_change="+50.0",
            change_date="01.01.2024",
        )

        assert "Товар А" in template["subject"]
        assert "ООО Поставщик" in template["body"]
        assert "100.0" in template["body"]
        assert "150.0" in template["body"]
        assert "+50.0" in template["body"]

    def test_get_template_unknown_type(self):
        """Тест обработки неизвестного типа уведомления."""
        with pytest.raises(ValueError, match="Неизвестный тип уведомления"):
            EmailTemplate.get_template("unknown_type")

    def test_get_template_missing_parameter(self):
        """Тест обработки отсутствующего параметра."""
        with pytest.raises(ValueError, match="Отсутствует обязательный параметр"):
            EmailTemplate.get_template(
                NotificationType.DOCUMENT_CHECK_COMPLETED,
                document_name="test.pdf",
                # Отсутствуют обязательные параметры
            )


class TestSendNotificationEmail:
    """Тесты для функции send_notification_email."""

    @patch("emailer.smtplib.SMTP_SSL")
    @patch("emailer.os.getenv")
    def test_send_notification_email_success(self, mock_getenv, mock_smtp):
        """Тест успешной отправки уведомления."""
        # Настройка моков
        mock_getenv.side_effect = lambda key: {
            "SMTP_FROM": "test@example.com",
            "SMTP_SERVER": "smtp.example.com",
            "SMTP_USER": "user",
            "SMTP_PASSWORD": "password",
        }.get(key)

        mock_smtp_instance = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_smtp_instance

        # Вызов функции
        result = send_notification_email(
            recipients=["recipient@example.com"],
            notification_type=NotificationType.DOCUMENT_CHECK_COMPLETED,
            document_name="test.pdf",
            overall_score=8.5,
            recommendation="Одобрить",
            violations_count=2,
        )

        # Проверки
        assert result is True
        mock_smtp_instance.login.assert_called_once_with("user", "password")
        mock_smtp_instance.send_message.assert_called_once()

    @patch("emailer.smtplib.SMTP_SSL")
    @patch("emailer.os.getenv")
    @patch("emailer.os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data=b"test file content")
    def test_send_notification_email_with_attachments(
        self, mock_file, mock_exists, mock_getenv, mock_smtp
    ):
        """Тест отправки уведомления с вложениями."""
        # Настройка моков
        mock_getenv.side_effect = lambda key: {
            "SMTP_FROM": "test@example.com",
            "SMTP_SERVER": "smtp.example.com",
            "SMTP_USER": "user",
            "SMTP_PASSWORD": "password",
        }.get(key)

        mock_exists.return_value = True
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_smtp_instance

        # Вызов функции
        result = send_notification_email(
            recipients=["recipient@example.com"],
            notification_type=NotificationType.DOCUMENT_CHECK_COMPLETED,
            attachments=["test.pdf", "test.txt", "test.json"],
            document_name="test.pdf",
            overall_score=8.5,
            recommendation="Одобрить",
            violations_count=2,
        )

        # Проверки
        assert result is True
        assert mock_file.call_count == 3  # Три файла вложения

    @patch("emailer.smtplib.SMTP_SSL")
    @patch("emailer.os.getenv")
    def test_send_notification_email_smtp_error(self, mock_getenv, mock_smtp):
        """Тест обработки ошибки SMTP."""
        # Настройка моков
        mock_getenv.side_effect = lambda key: {
            "SMTP_FROM": "test@example.com",
            "SMTP_SERVER": "smtp.example.com",
            "SMTP_USER": "user",
            "SMTP_PASSWORD": "password",
        }.get(key)

        mock_smtp.side_effect = Exception("SMTP Error")

        # Вызов функции
        result = send_notification_email(
            recipients=["recipient@example.com"],
            notification_type=NotificationType.DOCUMENT_CHECK_COMPLETED,
            document_name="test.pdf",
            overall_score=8.5,
            recommendation="Одобрить",
            violations_count=2,
        )

        # Проверки
        assert result is False


class TestSendSimpleEmail:
    """Тесты для функции send_simple_email."""

    @patch("emailer.smtplib.SMTP_SSL")
    @patch("emailer.os.getenv")
    def test_send_simple_email_success(self, mock_getenv, mock_smtp):
        """Тест успешной отправки простого email."""
        # Настройка моков
        mock_getenv.side_effect = lambda key: {
            "SMTP_FROM": "test@example.com",
            "SMTP_SERVER": "smtp.example.com",
            "SMTP_USER": "user",
            "SMTP_PASSWORD": "password",
        }.get(key)

        mock_smtp_instance = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_smtp_instance

        # Вызов функции
        result = send_simple_email(
            recipients=["recipient@example.com"],
            subject="Тестовая тема",
            body="Тестовое сообщение",
        )

        # Проверки
        assert result is True
        mock_smtp_instance.login.assert_called_once_with("user", "password")
        mock_smtp_instance.send_message.assert_called_once()


class TestNotificationHelpers:
    """Тесты для вспомогательных функций уведомлений."""

    @patch("emailer.send_notification_email")
    def test_notify_document_check_completed(self, mock_send):
        """Тест уведомления о завершении проверки документа."""
        mock_send.return_value = True

        result = notify_document_check_completed(
            recipients=["test@example.com"],
            document_name="test.pdf",
            overall_score=8.5,
            recommendation="Одобрить",
            violations_count=2,
            report_path="report.pdf",
        )

        assert result is True
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert (
            call_args[1]["notification_type"]
            == NotificationType.DOCUMENT_CHECK_COMPLETED
        )
        assert call_args[1]["attachments"] == ["report.pdf"]

    @patch("emailer.send_notification_email")
    def test_notify_supplier_status_changed(self, mock_send):
        """Тест уведомления об изменении статуса поставщика."""
        mock_send.return_value = True

        result = notify_supplier_status_changed(
            recipients=["test@example.com"],
            supplier_name="ООО Тест",
            supplier_inn="1234567890",
            old_status="Активный",
            new_status="Заблокирован",
            reason="Нарушение условий",
        )

        assert result is True
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert (
            call_args[1]["notification_type"]
            == NotificationType.SUPPLIER_STATUS_CHANGED
        )

    @patch("emailer.send_notification_email")
    def test_notify_system_error(self, mock_send):
        """Тест уведомления о системной ошибке."""
        mock_send.return_value = True

        result = notify_system_error(
            recipients=["admin@example.com"],
            error_type="DatabaseError",
            error_description="Ошибка подключения к БД",
            error_traceback="Traceback...",
        )

        assert result is True
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert call_args[1]["notification_type"] == NotificationType.SYSTEM_ERROR

    @patch("emailer.send_notification_email")
    def test_notify_batch_processing_completed(self, mock_send):
        """Тест уведомления о завершении пакетной обработки."""
        mock_send.return_value = True

        result = notify_batch_processing_completed(
            recipients=["test@example.com"],
            batch_id="batch_001",
            total_documents=100,
            processed_successfully=95,
            processing_errors=5,
            processing_time="10 минут",
            report_path="batch_report.pdf",
        )

        assert result is True
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert (
            call_args[1]["notification_type"]
            == NotificationType.BATCH_PROCESSING_COMPLETED
        )
        assert call_args[1]["attachments"] == ["batch_report.pdf"]

    @patch("emailer.send_notification_email")
    def test_notify_price_alert(self, mock_send):
        """Тест уведомления о ценовом предупреждении."""
        mock_send.return_value = True

        result = notify_price_alert(
            recipients=["test@example.com"],
            product_name="Товар А",
            supplier_name="ООО Поставщик",
            old_price=100.0,
            new_price=150.0,
        )

        assert result is True
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert call_args[1]["notification_type"] == NotificationType.PRICE_ALERT
        assert call_args[1]["price_change"] == "+50.0"


class TestEmailIntegration:
    """Интеграционные тесты для email функциональности."""

    @patch("emailer.smtplib.SMTP_SSL")
    @patch("emailer.os.getenv")
    def test_multiple_recipients(self, mock_getenv, mock_smtp):
        """Тест отправки уведомления нескольким получателям."""
        # Настройка моков
        mock_getenv.side_effect = lambda key: {
            "SMTP_FROM": "test@example.com",
            "SMTP_SERVER": "smtp.example.com",
            "SMTP_USER": "user",
            "SMTP_PASSWORD": "password",
        }.get(key)

        mock_smtp_instance = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_smtp_instance

        # Вызов функции
        result = send_notification_email(
            recipients=["user1@example.com", "user2@example.com", "user3@example.com"],
            notification_type=NotificationType.SYSTEM_ERROR,
            error_type="TestError",
            error_time="01.01.2024 12:00:00",
            error_description="Test error",
            error_traceback="Test traceback",
        )

        # Проверки
        assert result is True
        mock_smtp_instance.send_message.assert_called_once()

        # Проверяем, что сообщение отправлено всем получателям
        sent_message = mock_smtp_instance.send_message.call_args[0][0]
        assert (
            "user1@example.com, user2@example.com, user3@example.com"
            in sent_message["To"]
        )
