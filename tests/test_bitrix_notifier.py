"""Тесты для модуля bitrix_notifier.py."""

from unittest.mock import Mock, patch

import pytest

from bitrix_notifier import (
    BitrixNotificationType,
    BitrixNotifier,
    BitrixPriority,
    get_default_notifier,
    notify_batch_processing_completed,
    notify_document_check_completed,
    notify_price_alert,
    notify_supplier_status_changed,
    notify_system_error,
    test_connection,
)


class TestBitrixNotificationType:
    """Тесты для enum BitrixNotificationType."""

    def test_notification_types_exist(self):
        """Проверка наличия всех типов уведомлений."""
        expected_types = {
            "task_created",
            "task_updated",
            "document_check_completed",
            "supplier_status_changed",
            "system_error",
            "price_alert",
            "contract_expiring",
            "quality_issue",
            "batch_processing_completed",
            "payment_reminder",
        }

        actual_types = {item.value for item in BitrixNotificationType}
        assert actual_types == expected_types


class TestBitrixPriority:
    """Тесты для enum BitrixPriority."""

    def test_priority_values(self):
        """Проверка значений приоритетов."""
        assert BitrixPriority.LOW.value == "1"
        assert BitrixPriority.NORMAL.value == "2"
        assert BitrixPriority.HIGH.value == "3"


class TestBitrixNotifier:
    """Тесты для класса BitrixNotifier."""

    @pytest.fixture
    def mock_env_vars(self):
        """Мок переменных окружения."""
        with patch.dict(
            "os.environ",
            {
                "BITRIX24_WEBHOOK_URL": "https://test.bitrix24.ru/rest/1/webhook_key/",
                "BITRIX24_DEFAULT_USER_ID": "123",
                "BITRIX24_TIMEOUT": "30",
            },
        ):
            yield

    @pytest.fixture
    def notifier(self, mock_env_vars):
        """Создание экземпляра BitrixNotifier для тестов."""
        return BitrixNotifier()

    def test_init_with_webhook_url(self):
        """Тест инициализации с явным указанием webhook URL."""
        webhook_url = "https://test.bitrix24.ru/rest/1/test_key/"
        notifier = BitrixNotifier(webhook_url)
        assert notifier.webhook_url == webhook_url

    def test_init_without_webhook_url_raises_error(self):
        """Тест ошибки при отсутствии webhook URL."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="Не указан BITRIX24_WEBHOOK_URL"):
                BitrixNotifier()

    @patch("requests.post")
    def test_make_request_success(self, mock_post, notifier):
        """Тест успешного запроса к API."""
        mock_response = Mock()
        mock_response.json.return_value = {"result": {"success": True}}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = notifier._make_request("test.method", {"param": "value"})

        assert result == {"result": {"success": True}}
        mock_post.assert_called_once()

    @patch("requests.post")
    def test_make_request_api_error(self, mock_post, notifier):
        """Тест обработки ошибки API."""
        mock_response = Mock()
        mock_response.json.return_value = {"error": "Invalid method"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        with pytest.raises(Exception):
            notifier._make_request("invalid.method", {})

    @patch("requests.post")
    def test_make_request_network_error(self, mock_post, notifier):
        """Тест обработки сетевой ошибки."""
        mock_post.side_effect = Exception("Network error")

        with pytest.raises(Exception):
            notifier._make_request("test.method", {})

    @patch.object(BitrixNotifier, "_make_request")
    def test_create_task_success(self, mock_request, notifier):
        """Тест успешного создания задачи."""
        mock_request.return_value = {"result": {"task": {"id": "456"}}}

        task_id = notifier.create_task(
            title="Test Task",
            description="Test Description",
            responsible_id="123",
            priority=BitrixPriority.HIGH,
        )

        assert task_id == "456"
        mock_request.assert_called_once_with(
            "tasks.task.add",
            {
                "fields": {
                    "TITLE": "Test Task",
                    "DESCRIPTION": "Test Description",
                    "RESPONSIBLE_ID": "123",
                    "PRIORITY": "3",
                    "CREATED_BY": "123",
                }
            },
        )

    @patch.object(BitrixNotifier, "_make_request")
    def test_create_task_with_deadline_and_group(self, mock_request, notifier):
        """Тест создания задачи с дедлайном и группой."""
        mock_request.return_value = {"result": {"task": {"id": "789"}}}

        task_id = notifier.create_task(
            title="Task with Deadline",
            description="Description",
            deadline="2024-12-31 23:59:59",
            group_id="10",
        )

        assert task_id == "789"
        call_args = mock_request.call_args[0][1]
        assert call_args["fields"]["DEADLINE"] == "2024-12-31 23:59:59"
        assert call_args["fields"]["GROUP_ID"] == "10"

    @patch.object(BitrixNotifier, "_make_request")
    def test_create_task_error(self, mock_request, notifier):
        """Тест ошибки при создании задачи."""
        mock_request.side_effect = Exception("API Error")

        task_id = notifier.create_task("Test", "Description")

        assert task_id is None

    @patch.object(BitrixNotifier, "_make_request")
    def test_update_task_success(self, mock_request, notifier):
        """Тест успешного обновления задачи."""
        mock_request.return_value = {"result": True}

        result = notifier.update_task("123", {"STATUS": "5"})

        assert result is True
        mock_request.assert_called_once_with(
            "tasks.task.update", {"taskId": "123", "fields": {"STATUS": "5"}}
        )

    @patch.object(BitrixNotifier, "_make_request")
    def test_add_task_comment_success(self, mock_request, notifier):
        """Тест добавления комментария к задаче."""
        mock_request.return_value = {"result": True}

        result = notifier.add_task_comment("123", "Test comment")

        assert result is True
        mock_request.assert_called_once_with(
            "task.commentitem.add",
            {
                "taskId": "123",
                "fields": {"POST_MESSAGE": "Test comment", "AUTHOR_ID": "123"},
            },
        )

    @patch.object(BitrixNotifier, "_make_request")
    def test_send_notification_success(self, mock_request, notifier):
        """Тест отправки уведомления."""
        mock_request.return_value = {"result": True}

        result = notifier.send_notification(
            user_ids=["1", "2"],
            message="Test notification",
            notification_type=BitrixNotificationType.SYSTEM_ERROR,
        )

        assert result is True
        assert mock_request.call_count == 2  # Два пользователя

    @patch.object(BitrixNotifier, "_make_request")
    def test_create_lead_success(self, mock_request, notifier):
        """Тест создания лида."""
        mock_request.return_value = {"result": "999"}

        lead_id = notifier.create_lead(
            title="Test Lead",
            name="John Doe",
            phone="+7 123 456 78 90",
            email="john@example.com",
            company="Test Company",
        )

        assert lead_id == "999"
        call_args = mock_request.call_args[0][1]
        fields = call_args["fields"]
        assert fields["TITLE"] == "Test Lead"
        assert fields["NAME"] == "John Doe"
        assert fields["PHONE"][0]["VALUE"] == "+7 123 456 78 90"
        assert fields["EMAIL"][0]["VALUE"] == "john@example.com"
        assert fields["COMPANY_TITLE"] == "Test Company"


class TestNotificationFunctions:
    """Тесты для специализированных функций уведомлений."""

    @pytest.fixture
    def mock_notifier(self):
        """Мок BitrixNotifier."""
        notifier = Mock(spec=BitrixNotifier)
        notifier.send_notification.return_value = True
        notifier.create_task.return_value = "task_123"
        return notifier

    def test_notify_document_check_completed(self, mock_notifier):
        """Тест уведомления о завершении проверки документа."""
        task_id = notify_document_check_completed(
            notifier=mock_notifier,
            responsible_ids=["1", "2"],
            document_name="test_doc.pdf",
            overall_score=7.5,
            recommendation="Принять",
            violations_count=2,
            create_task=True,
        )

        assert task_id == "task_123"
        mock_notifier.send_notification.assert_called_once()
        mock_notifier.create_task.assert_called_once()

        # Проверяем параметры уведомления
        call_args = mock_notifier.send_notification.call_args
        assert call_args[1]["user_ids"] == ["1", "2"]
        assert "test_doc.pdf" in call_args[1]["message"]
        assert (
            call_args[1]["notification_type"]
            == BitrixNotificationType.DOCUMENT_CHECK_COMPLETED
        )

    def test_notify_document_check_completed_without_task(self, mock_notifier):
        """Тест уведомления без создания задачи."""
        task_id = notify_document_check_completed(
            notifier=mock_notifier,
            responsible_ids=["1"],
            document_name="test_doc.pdf",
            overall_score=8.0,
            recommendation="Принять",
            violations_count=0,
            create_task=False,
        )

        assert task_id is None
        mock_notifier.send_notification.assert_called_once()
        mock_notifier.create_task.assert_not_called()

    def test_notify_supplier_status_changed(self, mock_notifier):
        """Тест уведомления об изменении статуса поставщика."""
        task_id = notify_supplier_status_changed(
            notifier=mock_notifier,
            responsible_ids=["1"],
            supplier_name="ООО Тест",
            supplier_inn="1234567890",
            old_status="Активный",
            new_status="Заблокирован",
            reason="Нарушение условий",
            create_task=True,
        )

        assert task_id == "task_123"
        mock_notifier.send_notification.assert_called_once()
        mock_notifier.create_task.assert_called_once()

        # Проверяем приоритет (должен быть высокий для блокировки)
        task_call_args = mock_notifier.create_task.call_args
        assert task_call_args[1]["priority"] == BitrixPriority.HIGH

    def test_notify_system_error(self, mock_notifier):
        """Тест уведомления о системной ошибке."""
        task_id = notify_system_error(
            notifier=mock_notifier,
            admin_ids=["admin1", "admin2"],
            error_type="DatabaseError",
            error_description="Connection timeout",
            error_traceback="Traceback...",
            create_task=True,
        )

        assert task_id == "task_123"
        mock_notifier.send_notification.assert_called_once()
        mock_notifier.create_task.assert_called_once()

        # Проверяем приоритет (должен быть высокий для системных ошибок)
        task_call_args = mock_notifier.create_task.call_args
        assert task_call_args[1]["priority"] == BitrixPriority.HIGH
        assert "🚨" in mock_notifier.send_notification.call_args[1]["message"]

    def test_notify_price_alert_increase(self, mock_notifier):
        """Тест уведомления о повышении цены."""
        task_id = notify_price_alert(
            notifier=mock_notifier,
            responsible_ids=["1"],
            product_name="Товар А",
            supplier_name="Поставщик Б",
            old_price=100.0,
            new_price=130.0,
            currency="RUB",
            create_task=True,
        )

        assert task_id == "task_123"
        mock_notifier.send_notification.assert_called_once()
        mock_notifier.create_task.assert_called_once()

        # Проверяем наличие символа роста и процента изменения
        message = mock_notifier.send_notification.call_args[1]["message"]
        assert "📈" in message
        assert "+30.0%" in message

    def test_notify_price_alert_decrease(self, mock_notifier):
        """Тест уведомления о снижении цены."""
        notify_price_alert(
            notifier=mock_notifier,
            responsible_ids=["1"],
            product_name="Товар А",
            supplier_name="Поставщик Б",
            old_price=100.0,
            new_price=80.0,
            currency="RUB",
            create_task=True,
        )

        # Проверяем наличие символа падения
        message = mock_notifier.send_notification.call_args[1]["message"]
        assert "📉" in message
        assert "-20.0%" in message

    def test_notify_batch_processing_completed_success(self, mock_notifier):
        """Тест уведомления об успешной пакетной обработке."""
        task_id = notify_batch_processing_completed(
            notifier=mock_notifier,
            responsible_ids=["1"],
            batch_id="batch_001",
            total_documents=100,
            processed_successfully=98,
            processing_errors=2,
            processing_time="5 минут",
            create_task=False,
        )

        assert task_id is None  # Задача не создается при успешной обработке
        mock_notifier.send_notification.assert_called_once()
        mock_notifier.create_task.assert_not_called()

        # Проверяем символ успеха
        message = mock_notifier.send_notification.call_args[1]["message"]
        assert "✅" in message
        assert "98.0%" in message

    def test_notify_batch_processing_completed_with_errors(self, mock_notifier):
        """Тест уведомления о пакетной обработке с ошибками."""
        task_id = notify_batch_processing_completed(
            notifier=mock_notifier,
            responsible_ids=["1"],
            batch_id="batch_002",
            total_documents=100,
            processed_successfully=70,
            processing_errors=30,
            processing_time="10 минут",
            create_task=True,
        )

        assert task_id == "task_123"  # Задача создается при наличии ошибок
        mock_notifier.send_notification.assert_called_once()
        mock_notifier.create_task.assert_called_once()

        # Проверяем символ предупреждения
        message = mock_notifier.send_notification.call_args[1]["message"]
        assert "❌" in message  # Низкая успешность (70%)


class TestUtilityFunctions:
    """Тесты для утилитарных функций."""

    @patch.dict(
        "os.environ",
        {"BITRIX24_WEBHOOK_URL": "https://test.bitrix24.ru/rest/1/webhook_key/"},
    )
    def test_get_default_notifier(self):
        """Тест получения нотификатора по умолчанию."""
        notifier = get_default_notifier()
        assert isinstance(notifier, BitrixNotifier)
        assert notifier.webhook_url == "https://test.bitrix24.ru/rest/1/webhook_key/"

    @patch.object(BitrixNotifier, "_make_request")
    def test_test_connection_success(self, mock_request):
        """Тест успешной проверки подключения."""
        mock_request.return_value = {"result": {"ID": "1", "NAME": "Test User"}}

        result = test_connection("https://test.bitrix24.ru/rest/1/test_key/")

        assert result is True
        mock_request.assert_called_once_with("profile", {})

    @patch.object(BitrixNotifier, "_make_request")
    def test_test_connection_failure(self, mock_request):
        """Тест неудачной проверки подключения."""
        mock_request.side_effect = Exception("Connection failed")

        result = test_connection("https://invalid.url/")

        assert result is False
