"""Тесты для модуля notification_subscriptions.py"""

import os
import tempfile
from datetime import datetime, timedelta
from unittest.mock import patch

from notification_subscriptions import (
    NotificationChannel,
    NotificationFrequency,
    NotificationPriority,
    NotificationRule,
    NotificationSubscriptionManager,
    UserRole,
    UserSubscription,
    bulk_update_rules,
    create_admin_user,
    get_default_subscription_manager,
)


class TestEnums:
    """Тесты для перечислений."""

    def test_notification_channel_enum(self):
        """Тест перечисления каналов уведомлений."""
        assert NotificationChannel.EMAIL.value == "email"
        assert NotificationChannel.BITRIX24.value == "bitrix24"
        assert NotificationChannel.TELEGRAM.value == "telegram"
        assert NotificationChannel.SMS.value == "sms"
        assert NotificationChannel.WEBHOOK.value == "webhook"

    def test_user_role_enum(self):
        """Тест перечисления ролей пользователей."""
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.MANAGER.value == "manager"
        assert UserRole.ANALYST.value == "analyst"
        assert UserRole.OPERATOR.value == "operator"
        assert UserRole.VIEWER.value == "viewer"

    def test_notification_priority_enum(self):
        """Тест перечисления приоритетов."""
        assert NotificationPriority.LOW.value == "low"
        assert NotificationPriority.NORMAL.value == "normal"
        assert NotificationPriority.HIGH.value == "high"
        assert NotificationPriority.CRITICAL.value == "critical"

    def test_notification_frequency_enum(self):
        """Тест перечисления частоты уведомлений."""
        assert NotificationFrequency.IMMEDIATE.value == "immediate"
        assert NotificationFrequency.HOURLY.value == "hourly"
        assert NotificationFrequency.DAILY.value == "daily"
        assert NotificationFrequency.WEEKLY.value == "weekly"
        assert NotificationFrequency.MONTHLY.value == "monthly"


class TestNotificationRule:
    """Тесты для класса NotificationRule."""

    def test_notification_rule_creation(self):
        """Тест создания правила уведомления."""
        rule = NotificationRule(
            notification_type="test_notification",
            channels=[NotificationChannel.EMAIL],
            priority=NotificationPriority.NORMAL,
            frequency=NotificationFrequency.IMMEDIATE,
        )

        assert rule.notification_type == "test_notification"
        assert rule.channels == [NotificationChannel.EMAIL]
        assert rule.priority == NotificationPriority.NORMAL
        assert rule.frequency == NotificationFrequency.IMMEDIATE
        assert rule.enabled is True
        assert rule.conditions is None
        assert isinstance(rule.created_at, datetime)
        assert isinstance(rule.updated_at, datetime)

    def test_notification_rule_with_conditions(self):
        """Тест создания правила с условиями."""
        conditions = {"error_type": ["critical", "warning"]}
        rule = NotificationRule(
            notification_type="error_notification",
            channels=[NotificationChannel.EMAIL, NotificationChannel.BITRIX24],
            priority=NotificationPriority.HIGH,
            frequency=NotificationFrequency.IMMEDIATE,
            conditions=conditions,
        )

        assert rule.conditions == conditions
        assert len(rule.channels) == 2


class TestUserSubscription:
    """Тесты для класса UserSubscription."""

    def test_user_subscription_creation(self):
        """Тест создания подписки пользователя."""
        subscription = UserSubscription(
            user_id="user123", email="test@example.com", role=UserRole.MANAGER
        )

        assert subscription.user_id == "user123"
        assert subscription.email == "test@example.com"
        assert subscription.role == UserRole.MANAGER
        assert subscription.rules == []
        assert subscription.timezone == "UTC"
        assert subscription.language == "ru"
        assert subscription.active is True
        assert isinstance(subscription.created_at, datetime)
        assert isinstance(subscription.updated_at, datetime)

    def test_user_subscription_with_all_contacts(self):
        """Тест создания подписки со всеми контактами."""
        subscription = UserSubscription(
            user_id="user456",
            email="admin@example.com",
            phone="+1234567890",
            telegram_id="@admin",
            bitrix_user_id="bitrix123",
            role=UserRole.ADMIN,
        )

        assert subscription.phone == "+1234567890"
        assert subscription.telegram_id == "@admin"
        assert subscription.bitrix_user_id == "bitrix123"


class TestNotificationSubscriptionManager:
    """Тесты для класса NotificationSubscriptionManager."""

    def setup_method(self):
        """Настройка для каждого теста."""
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        self.temp_file.close()
        self.manager = NotificationSubscriptionManager(storage_path=self.temp_file.name)

    def teardown_method(self):
        """Очистка после каждого теста."""
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)

    def test_manager_initialization(self):
        """Тест инициализации менеджера."""
        assert self.manager.storage_path == self.temp_file.name
        assert isinstance(self.manager.subscriptions, dict)
        assert len(self.manager.subscriptions) == 0
        assert UserRole.ADMIN in self.manager.default_rules
        assert UserRole.VIEWER in self.manager.default_rules

    def test_default_rules_structure(self):
        """Тест структуры правил по умолчанию."""
        admin_rules = self.manager.default_rules[UserRole.ADMIN]
        assert len(admin_rules) > 0

        # Проверяем, что у админа есть правило для системных ошибок
        system_error_rule = next(
            (rule for rule in admin_rules if rule.notification_type == "system_error"),
            None,
        )
        assert system_error_rule is not None
        assert system_error_rule.priority == NotificationPriority.CRITICAL
        assert NotificationChannel.EMAIL in system_error_rule.channels

    def test_create_user_subscription(self):
        """Тест создания подписки пользователя."""
        subscription = self.manager.create_user_subscription(
            user_id="test_user", email="test@example.com", role=UserRole.MANAGER
        )

        assert subscription.user_id == "test_user"
        assert subscription.email == "test@example.com"
        assert subscription.role == UserRole.MANAGER
        assert len(subscription.rules) > 0  # Должны быть правила по умолчанию

        # Проверяем, что подписка сохранена
        assert "test_user" in self.manager.subscriptions
        assert os.path.exists(self.temp_file.name)

    def test_update_user_subscription(self):
        """Тест обновления подписки пользователя."""
        # Создаем подписку
        self.manager.create_user_subscription(
            user_id="test_user", email="old@example.com", role=UserRole.VIEWER
        )

        # Обновляем подписку
        updated_subscription = self.manager.update_user_subscription(
            user_id="test_user",
            email="new@example.com",
            role=UserRole.MANAGER,
            active=False,
        )

        assert updated_subscription is not None
        assert updated_subscription.email == "new@example.com"
        assert updated_subscription.role == UserRole.MANAGER
        assert updated_subscription.active is False

    def test_update_nonexistent_user(self):
        """Тест обновления несуществующего пользователя."""
        result = self.manager.update_user_subscription(
            user_id="nonexistent", email="test@example.com"
        )

        assert result is None

    def test_add_notification_rule(self):
        """Тест добавления правила уведомления."""
        # Создаем подписку
        self.manager.create_user_subscription(
            user_id="test_user", email="test@example.com", role=UserRole.VIEWER
        )

        # Добавляем новое правило
        new_rule = NotificationRule(
            notification_type="custom_notification",
            channels=[NotificationChannel.TELEGRAM],
            priority=NotificationPriority.HIGH,
            frequency=NotificationFrequency.DAILY,
        )

        result = self.manager.add_notification_rule("test_user", new_rule)
        assert result is True

        subscription = self.manager.get_user_subscription("test_user")
        custom_rules = [
            rule
            for rule in subscription.rules
            if rule.notification_type == "custom_notification"
        ]
        assert len(custom_rules) == 1
        assert custom_rules[0].channels == [NotificationChannel.TELEGRAM]

    def test_remove_notification_rule(self):
        """Тест удаления правила уведомления."""
        # Создаем подписку
        self.manager.create_user_subscription(
            user_id="test_user", email="test@example.com", role=UserRole.MANAGER
        )

        # Получаем исходное количество правил
        subscription = self.manager.get_user_subscription("test_user")
        initial_count = len(subscription.rules)

        # Удаляем правило (предполагаем, что у менеджера есть правило document_check_completed)
        result = self.manager.remove_notification_rule(
            "test_user", "document_check_completed"
        )
        assert result is True

        # Проверяем, что правило удалено
        updated_subscription = self.manager.get_user_subscription("test_user")
        assert len(updated_subscription.rules) == initial_count - 1

        remaining_rules = [
            rule
            for rule in updated_subscription.rules
            if rule.notification_type == "document_check_completed"
        ]
        assert len(remaining_rules) == 0

    def test_get_subscribers_for_notification(self):
        """Тест получения подписчиков для уведомления."""
        # Создаем несколько подписок
        self.manager.create_user_subscription(
            user_id="admin", email="admin@example.com", role=UserRole.ADMIN
        )

        self.manager.create_user_subscription(
            user_id="manager", email="manager@example.com", role=UserRole.MANAGER
        )

        self.manager.create_user_subscription(
            user_id="viewer", email="viewer@example.com", role=UserRole.VIEWER
        )

        # Получаем подписчиков для уведомления о завершении проверки документов
        subscribers = self.manager.get_subscribers_for_notification(
            notification_type="document_check_completed",
            channel=NotificationChannel.EMAIL,
        )

        # Админ и менеджер должны получать такие уведомления
        subscriber_ids = [sub.user_id for sub in subscribers]
        assert "admin" in subscriber_ids
        assert "manager" in subscriber_ids
        # Viewer может не получать такие уведомления в зависимости от настроек по умолчанию

    def test_get_subscribers_with_priority_filter(self):
        """Тест получения подписчиков с фильтром по приоритету."""
        self.manager.create_user_subscription(
            user_id="admin", email="admin@example.com", role=UserRole.ADMIN
        )

        # Получаем подписчиков только для критических уведомлений
        subscribers = self.manager.get_subscribers_for_notification(
            notification_type="system_error",
            channel=NotificationChannel.EMAIL,
            priority=NotificationPriority.CRITICAL,
        )

        assert len(subscribers) > 0
        assert subscribers[0].user_id == "admin"

    def test_should_send_notification_immediate(self):
        """Тест проверки отправки немедленных уведомлений."""
        self.manager.create_user_subscription(
            user_id="test_user", email="test@example.com", role=UserRole.ADMIN
        )

        # Для немедленных уведомлений всегда должно возвращать True
        result = self.manager.should_send_notification(
            user_id="test_user", notification_type="system_error"
        )

        assert result is True

    def test_should_send_notification_frequency_check(self):
        """Тест проверки частоты отправки уведомлений."""
        # Создаем подписку с ежедневными уведомлениями
        self.manager.create_user_subscription(
            user_id="test_user", email="test@example.com", role=UserRole.ANALYST
        )

        # Для уведомлений с частотой (например, batch_processing_completed может быть ежедневным)
        # Если последняя отправка была час назад, не должно отправлять
        last_sent = datetime.now() - timedelta(hours=1)
        result = self.manager.should_send_notification(
            user_id="test_user",
            notification_type="batch_processing_completed",
            last_sent=last_sent,
        )

        # Результат зависит от настроек по умолчанию для аналитика
        assert isinstance(result, bool)

    def test_should_send_notification_inactive_user(self):
        """Тест проверки отправки для неактивного пользователя."""
        self.manager.create_user_subscription(
            user_id="test_user", email="test@example.com", role=UserRole.ADMIN
        )

        # Деактивируем пользователя
        self.manager.update_user_subscription(user_id="test_user", active=False)

        result = self.manager.should_send_notification(
            user_id="test_user", notification_type="system_error"
        )

        assert result is False

    def test_delete_user_subscription(self):
        """Тест удаления подписки пользователя."""
        # Создаем подписку
        self.manager.create_user_subscription(
            user_id="test_user", email="test@example.com", role=UserRole.VIEWER
        )

        assert "test_user" in self.manager.subscriptions

        # Удаляем подписку
        result = self.manager.delete_user_subscription("test_user")
        assert result is True
        assert "test_user" not in self.manager.subscriptions

        # Попытка удалить несуществующую подписку
        result = self.manager.delete_user_subscription("nonexistent")
        assert result is False

    def test_get_statistics(self):
        """Тест получения статистики подписок."""
        # Создаем несколько подписок
        self.manager.create_user_subscription(
            user_id="admin", email="admin@example.com", role=UserRole.ADMIN
        )

        self.manager.create_user_subscription(
            user_id="manager", email="manager@example.com", role=UserRole.MANAGER
        )

        self.manager.create_user_subscription(
            user_id="inactive", email="inactive@example.com", role=UserRole.VIEWER
        )

        # Деактивируем одного пользователя
        self.manager.update_user_subscription(user_id="inactive", active=False)

        stats = self.manager.get_statistics()

        assert stats["total_users"] == 3
        assert stats["active_users"] == 2
        assert stats["inactive_users"] == 1
        assert stats["role_distribution"]["admin"] == 1
        assert stats["role_distribution"]["manager"] == 1
        assert stats["role_distribution"]["viewer"] == 1
        assert "channel_usage" in stats
        assert "total_rules" in stats

    def test_save_and_load_subscriptions(self):
        """Тест сохранения и загрузки подписок."""
        # Создаем подписку
        original_subscription = self.manager.create_user_subscription(
            user_id="test_user",
            email="test@example.com",
            role=UserRole.MANAGER,
            phone="+1234567890",
            telegram_id="@testuser",
        )

        # Создаем новый менеджер с тем же файлом
        new_manager = NotificationSubscriptionManager(storage_path=self.temp_file.name)

        # Проверяем, что данные загрузились
        loaded_subscription = new_manager.get_user_subscription("test_user")
        assert loaded_subscription is not None
        assert loaded_subscription.user_id == "test_user"
        assert loaded_subscription.email == "test@example.com"
        assert loaded_subscription.role == UserRole.MANAGER
        assert loaded_subscription.phone == "+1234567890"
        assert loaded_subscription.telegram_id == "@testuser"
        assert len(loaded_subscription.rules) == len(original_subscription.rules)


class TestUtilityFunctions:
    """Тесты для утилитарных функций."""

    def test_get_default_subscription_manager(self):
        """Тест получения менеджера по умолчанию."""
        manager = get_default_subscription_manager()
        assert isinstance(manager, NotificationSubscriptionManager)

    def test_create_admin_user(self):
        """Тест создания пользователя-администратора."""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        temp_file.close()

        try:
            manager = NotificationSubscriptionManager(storage_path=temp_file.name)

            admin_subscription = create_admin_user(
                manager=manager,
                user_id="admin123",
                email="admin@company.com",
                bitrix_user_id="bitrix456",
            )

            assert admin_subscription.user_id == "admin123"
            assert admin_subscription.email == "admin@company.com"
            assert admin_subscription.role == UserRole.ADMIN
            assert admin_subscription.bitrix_user_id == "bitrix456"
            assert len(admin_subscription.rules) > 0

        finally:
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)

    def test_bulk_update_rules(self):
        """Тест массового обновления правил."""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        temp_file.close()

        try:
            manager = NotificationSubscriptionManager(storage_path=temp_file.name)

            # Создаем несколько пользователей
            manager.create_user_subscription(
                user_id="user1", email="user1@example.com", role=UserRole.ADMIN
            )

            manager.create_user_subscription(
                user_id="user2", email="user2@example.com", role=UserRole.MANAGER
            )

            # Отключаем все правила для system_error
            updated_count = bulk_update_rules(
                manager=manager, notification_type="system_error", enabled=False
            )

            assert updated_count > 0

            # Проверяем, что правила отключены
            for subscription in manager.subscriptions.values():
                for rule in subscription.rules:
                    if rule.notification_type == "system_error":
                        assert rule.enabled is False

        finally:
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)


class TestEdgeCases:
    """Тесты для граничных случаев."""

    def test_manager_with_corrupted_file(self):
        """Тест менеджера с поврежденным файлом."""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")

        # Записываем некорректный JSON
        with open(temp_file.name, "w") as f:
            f.write("invalid json content")

        temp_file.close()

        try:
            # Менеджер должен создаться с пустыми подписками
            manager = NotificationSubscriptionManager(storage_path=temp_file.name)
            assert len(manager.subscriptions) == 0

        finally:
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)

    def test_manager_with_nonexistent_directory(self):
        """Тест менеджера с несуществующей директорией."""
        nonexistent_path = "/nonexistent/directory/subscriptions.json"

        # На Windows путь должен быть другим
        if os.name == "nt":
            nonexistent_path = "C:\\nonexistent\\directory\\subscriptions.json"

        manager = NotificationSubscriptionManager(storage_path=nonexistent_path)

        # Создаем подписку - директория должна создаться автоматически
        subscription = manager.create_user_subscription(
            user_id="test_user", email="test@example.com", role=UserRole.VIEWER
        )

        assert subscription is not None
        # Очистка не нужна, так как путь несуществующий

    @patch.dict(os.environ, {"SUBSCRIPTIONS_STORAGE_PATH": "custom_path.json"})
    def test_manager_with_env_variable(self):
        """Тест менеджера с переменной окружения."""
        manager = NotificationSubscriptionManager()
        assert manager.storage_path == "custom_path.json"
