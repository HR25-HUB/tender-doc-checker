"""Модуль для управления подписками на уведомления."""

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

from loguru import logger


class NotificationChannel(Enum):
    """Каналы доставки уведомлений."""

    EMAIL = "email"
    BITRIX24 = "bitrix24"
    TELEGRAM = "telegram"
    SMS = "sms"
    WEBHOOK = "webhook"


class UserRole(Enum):
    """Роли пользователей в системе."""

    ADMIN = "admin"
    MANAGER = "manager"
    ANALYST = "analyst"
    OPERATOR = "operator"
    VIEWER = "viewer"


class NotificationPriority(Enum):
    """Приоритеты уведомлений."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationFrequency(Enum):
    """Частота отправки уведомлений."""

    IMMEDIATE = "immediate"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass
class NotificationRule:
    """Правило уведомления."""

    notification_type: str
    channels: list[NotificationChannel]
    priority: NotificationPriority
    frequency: NotificationFrequency
    enabled: bool = True
    conditions: Optional[dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


@dataclass
class UserSubscription:
    """Подписка пользователя на уведомления."""

    user_id: str
    email: Optional[str] = None
    phone: Optional[str] = None
    telegram_id: Optional[str] = None
    bitrix_user_id: Optional[str] = None
    role: UserRole = UserRole.VIEWER
    rules: list[NotificationRule] = None
    timezone: str = "UTC"
    language: str = "ru"
    active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        if self.rules is None:
            self.rules = []
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


class NotificationSubscriptionManager:
    """Менеджер подписок на уведомления."""

    def __init__(self, storage_path: Optional[str] = None):
        """Инициализация менеджера подписок.

        Args:
            storage_path: Путь к файлу хранения подписок
        """
        self.storage_path = storage_path or os.getenv(
            "SUBSCRIPTIONS_STORAGE_PATH", "data/subscriptions.json"
        )
        self.subscriptions: dict[str, UserSubscription] = {}
        self.default_rules = self._get_default_rules()
        self._load_subscriptions()

    def _get_default_rules(self) -> dict[UserRole, list[NotificationRule]]:
        """Получить правила по умолчанию для каждой роли."""
        return {
            UserRole.ADMIN: [
                NotificationRule(
                    notification_type="system_error",
                    channels=[NotificationChannel.EMAIL, NotificationChannel.BITRIX24],
                    priority=NotificationPriority.CRITICAL,
                    frequency=NotificationFrequency.IMMEDIATE,
                ),
                NotificationRule(
                    notification_type="document_check_completed",
                    channels=[NotificationChannel.EMAIL],
                    priority=NotificationPriority.NORMAL,
                    frequency=NotificationFrequency.IMMEDIATE,
                ),
                NotificationRule(
                    notification_type="supplier_status_changed",
                    channels=[NotificationChannel.EMAIL, NotificationChannel.BITRIX24],
                    priority=NotificationPriority.HIGH,
                    frequency=NotificationFrequency.IMMEDIATE,
                ),
                NotificationRule(
                    notification_type="batch_processing_completed",
                    channels=[NotificationChannel.EMAIL],
                    priority=NotificationPriority.NORMAL,
                    frequency=NotificationFrequency.DAILY,
                ),
            ],
            UserRole.MANAGER: [
                NotificationRule(
                    notification_type="document_check_completed",
                    channels=[NotificationChannel.EMAIL, NotificationChannel.BITRIX24],
                    priority=NotificationPriority.NORMAL,
                    frequency=NotificationFrequency.IMMEDIATE,
                ),
                NotificationRule(
                    notification_type="supplier_status_changed",
                    channels=[NotificationChannel.EMAIL],
                    priority=NotificationPriority.HIGH,
                    frequency=NotificationFrequency.IMMEDIATE,
                ),
                NotificationRule(
                    notification_type="price_alert",
                    channels=[NotificationChannel.EMAIL],
                    priority=NotificationPriority.HIGH,
                    frequency=NotificationFrequency.IMMEDIATE,
                ),
            ],
            UserRole.ANALYST: [
                NotificationRule(
                    notification_type="document_check_completed",
                    channels=[NotificationChannel.EMAIL],
                    priority=NotificationPriority.NORMAL,
                    frequency=NotificationFrequency.HOURLY,
                ),
                NotificationRule(
                    notification_type="price_alert",
                    channels=[NotificationChannel.EMAIL],
                    priority=NotificationPriority.NORMAL,
                    frequency=NotificationFrequency.IMMEDIATE,
                ),
                NotificationRule(
                    notification_type="batch_processing_completed",
                    channels=[NotificationChannel.EMAIL],
                    priority=NotificationPriority.LOW,
                    frequency=NotificationFrequency.DAILY,
                ),
            ],
            UserRole.OPERATOR: [
                NotificationRule(
                    notification_type="document_check_completed",
                    channels=[NotificationChannel.EMAIL],
                    priority=NotificationPriority.NORMAL,
                    frequency=NotificationFrequency.IMMEDIATE,
                ),
                NotificationRule(
                    notification_type="system_error",
                    channels=[NotificationChannel.EMAIL],
                    priority=NotificationPriority.HIGH,
                    frequency=NotificationFrequency.IMMEDIATE,
                    conditions={"error_type": ["processing_error", "validation_error"]},
                ),
            ],
            UserRole.VIEWER: [
                NotificationRule(
                    notification_type="batch_processing_completed",
                    channels=[NotificationChannel.EMAIL],
                    priority=NotificationPriority.LOW,
                    frequency=NotificationFrequency.WEEKLY,
                )
            ],
        }

    def _load_subscriptions(self):
        """Загрузить подписки из файла."""
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, encoding="utf-8") as f:
                    data = json.load(f)

                for user_id, sub_data in data.items():
                    # Преобразуем строки обратно в объекты
                    rules = []
                    for rule_data in sub_data.get("rules", []):
                        rule_data["channels"] = [
                            NotificationChannel(ch) for ch in rule_data["channels"]
                        ]
                        rule_data["priority"] = NotificationPriority(
                            rule_data["priority"]
                        )
                        rule_data["frequency"] = NotificationFrequency(
                            rule_data["frequency"]
                        )
                        if rule_data.get("created_at"):
                            rule_data["created_at"] = datetime.fromisoformat(
                                rule_data["created_at"]
                            )
                        if rule_data.get("updated_at"):
                            rule_data["updated_at"] = datetime.fromisoformat(
                                rule_data["updated_at"]
                            )
                        rules.append(NotificationRule(**rule_data))

                    sub_data["rules"] = rules
                    sub_data["role"] = UserRole(sub_data["role"])
                    if sub_data.get("created_at"):
                        sub_data["created_at"] = datetime.fromisoformat(
                            sub_data["created_at"]
                        )
                    if sub_data.get("updated_at"):
                        sub_data["updated_at"] = datetime.fromisoformat(
                            sub_data["updated_at"]
                        )

                    self.subscriptions[user_id] = UserSubscription(**sub_data)

                logger.info(f"Загружено {len(self.subscriptions)} подписок")

        except Exception as e:
            logger.error(f"Ошибка загрузки подписок: {e}")
            self.subscriptions = {}

    def _save_subscriptions(self):
        """Сохранить подписки в файл."""
        try:
            # Создаем директорию если не существует
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)

            # Преобразуем объекты в сериализуемый формат
            data = {}
            for user_id, subscription in self.subscriptions.items():
                sub_dict = asdict(subscription)

                # Преобразуем enum в строки
                sub_dict["role"] = subscription.role.value

                for rule in sub_dict["rules"]:
                    rule["channels"] = [ch.value for ch in rule["channels"]]
                    rule["priority"] = rule["priority"].value
                    rule["frequency"] = rule["frequency"].value
                    if rule["created_at"]:
                        rule["created_at"] = rule["created_at"].isoformat()
                    if rule["updated_at"]:
                        rule["updated_at"] = rule["updated_at"].isoformat()

                if sub_dict["created_at"]:
                    sub_dict["created_at"] = sub_dict["created_at"].isoformat()
                if sub_dict["updated_at"]:
                    sub_dict["updated_at"] = sub_dict["updated_at"].isoformat()

                data[user_id] = sub_dict

            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info(f"Сохранено {len(self.subscriptions)} подписок")

        except Exception as e:
            logger.error(f"Ошибка сохранения подписок: {e}")

    def create_user_subscription(
        self,
        user_id: str,
        email: Optional[str] = None,
        role: UserRole = UserRole.VIEWER,
        phone: Optional[str] = None,
        telegram_id: Optional[str] = None,
        bitrix_user_id: Optional[str] = None,
    ) -> UserSubscription:
        """Создать подписку пользователя.

        Args:
            user_id: Идентификатор пользователя
            email: Email пользователя
            role: Роль пользователя
            phone: Телефон пользователя
            telegram_id: Telegram ID
            bitrix_user_id: Bitrix24 user ID

        Returns:
            Созданная подписка
        """
        # Создаем подписку с правилами по умолчанию для роли
        default_rules = self.default_rules.get(role, [])

        subscription = UserSubscription(
            user_id=user_id,
            email=email,
            phone=phone,
            telegram_id=telegram_id,
            bitrix_user_id=bitrix_user_id,
            role=role,
            rules=default_rules.copy(),
        )

        self.subscriptions[user_id] = subscription
        self._save_subscriptions()

        logger.info(f"Создана подписка для пользователя {user_id} с ролью {role.value}")
        return subscription

    def update_user_subscription(
        self, user_id: str, **kwargs
    ) -> Optional[UserSubscription]:
        """Обновить подписку пользователя.

        Args:
            user_id: Идентификатор пользователя
            **kwargs: Поля для обновления

        Returns:
            Обновленная подписка или None если не найдена
        """
        if user_id not in self.subscriptions:
            logger.warning(f"Подписка пользователя {user_id} не найдена")
            return None

        subscription = self.subscriptions[user_id]

        for key, value in kwargs.items():
            if hasattr(subscription, key):
                setattr(subscription, key, value)

        subscription.updated_at = datetime.now()
        self._save_subscriptions()

        logger.info(f"Обновлена подписка пользователя {user_id}")
        return subscription

    def add_notification_rule(self, user_id: str, rule: NotificationRule) -> bool:
        """Добавить правило уведомления пользователю.

        Args:
            user_id: Идентификатор пользователя
            rule: Правило уведомления

        Returns:
            True если правило добавлено
        """
        if user_id not in self.subscriptions:
            logger.warning(f"Подписка пользователя {user_id} не найдена")
            return False

        subscription = self.subscriptions[user_id]
        subscription.rules.append(rule)
        subscription.updated_at = datetime.now()
        self._save_subscriptions()

        logger.info(
            f"Добавлено правило {rule.notification_type} для пользователя {user_id}"
        )
        return True

    def remove_notification_rule(self, user_id: str, notification_type: str) -> bool:
        """Удалить правило уведомления.

        Args:
            user_id: Идентификатор пользователя
            notification_type: Тип уведомления

        Returns:
            True если правило удалено
        """
        if user_id not in self.subscriptions:
            return False

        subscription = self.subscriptions[user_id]
        original_count = len(subscription.rules)

        subscription.rules = [
            rule
            for rule in subscription.rules
            if rule.notification_type != notification_type
        ]

        if len(subscription.rules) < original_count:
            subscription.updated_at = datetime.now()
            self._save_subscriptions()
            logger.info(
                f"Удалено правило {notification_type} для пользователя {user_id}"
            )
            return True

        return False

    def get_subscribers_for_notification(
        self,
        notification_type: str,
        channel: NotificationChannel,
        priority: Optional[NotificationPriority] = None,
    ) -> list[UserSubscription]:
        """Получить подписчиков для определенного типа уведомления.

        Args:
            notification_type: Тип уведомления
            channel: Канал доставки
            priority: Минимальный приоритет (опционально)

        Returns:
            Список подписчиков
        """
        subscribers = []

        for subscription in self.subscriptions.values():
            if not subscription.active:
                continue

            for rule in subscription.rules:
                if (
                    rule.notification_type == notification_type
                    and rule.enabled
                    and channel in rule.channels
                ):
                    # Проверяем приоритет если указан
                    if priority is not None:
                        priority_order = {
                            NotificationPriority.LOW: 1,
                            NotificationPriority.NORMAL: 2,
                            NotificationPriority.HIGH: 3,
                            NotificationPriority.CRITICAL: 4,
                        }
                        if priority_order.get(rule.priority, 0) < priority_order.get(
                            priority, 0
                        ):
                            continue

                    subscribers.append(subscription)
                    break

        return subscribers

    def should_send_notification(
        self, user_id: str, notification_type: str, last_sent: Optional[datetime] = None
    ) -> bool:
        """Проверить, нужно ли отправлять уведомление пользователю.

        Args:
            user_id: Идентификатор пользователя
            notification_type: Тип уведомления
            last_sent: Время последней отправки

        Returns:
            True если нужно отправлять
        """
        if user_id not in self.subscriptions:
            return False

        subscription = self.subscriptions[user_id]
        if not subscription.active:
            return False

        for rule in subscription.rules:
            if rule.notification_type == notification_type and rule.enabled:
                if rule.frequency == NotificationFrequency.IMMEDIATE:
                    return True

                if last_sent is None:
                    return True

                now = datetime.now()
                time_diff = now - last_sent

                if rule.frequency == NotificationFrequency.HOURLY:
                    return time_diff >= timedelta(hours=1)
                elif rule.frequency == NotificationFrequency.DAILY:
                    return time_diff >= timedelta(days=1)
                elif rule.frequency == NotificationFrequency.WEEKLY:
                    return time_diff >= timedelta(weeks=1)
                elif rule.frequency == NotificationFrequency.MONTHLY:
                    return time_diff >= timedelta(days=30)

        return False

    def get_user_subscription(self, user_id: str) -> Optional[UserSubscription]:
        """Получить подписку пользователя.

        Args:
            user_id: Идентификатор пользователя

        Returns:
            Подписка пользователя или None
        """
        return self.subscriptions.get(user_id)

    def list_all_subscriptions(self) -> dict[str, UserSubscription]:
        """Получить все подписки.

        Returns:
            Словарь всех подписок
        """
        return self.subscriptions.copy()

    def delete_user_subscription(self, user_id: str) -> bool:
        """Удалить подписку пользователя.

        Args:
            user_id: Идентификатор пользователя

        Returns:
            True если подписка удалена
        """
        if user_id in self.subscriptions:
            del self.subscriptions[user_id]
            self._save_subscriptions()
            logger.info(f"Удалена подписка пользователя {user_id}")
            return True
        return False

    def get_statistics(self) -> dict[str, Any]:
        """Получить статистику подписок.

        Returns:
            Словарь со статистикой
        """
        total_users = len(self.subscriptions)
        active_users = sum(1 for sub in self.subscriptions.values() if sub.active)

        role_distribution = {}
        for role in UserRole:
            role_distribution[role.value] = sum(
                1 for sub in self.subscriptions.values() if sub.role == role
            )

        channel_usage = {}
        for channel in NotificationChannel:
            channel_usage[channel.value] = sum(
                1
                for sub in self.subscriptions.values()
                for rule in sub.rules
                if channel in rule.channels
            )

        return {
            "total_users": total_users,
            "active_users": active_users,
            "inactive_users": total_users - active_users,
            "role_distribution": role_distribution,
            "channel_usage": channel_usage,
            "total_rules": sum(len(sub.rules) for sub in self.subscriptions.values()),
        }


# === УТИЛИТАРНЫЕ ФУНКЦИИ ===


def get_default_subscription_manager() -> NotificationSubscriptionManager:
    """Получить менеджер подписок по умолчанию."""
    return NotificationSubscriptionManager()


def create_admin_user(
    manager: NotificationSubscriptionManager,
    user_id: str,
    email: str,
    bitrix_user_id: Optional[str] = None,
) -> UserSubscription:
    """Создать пользователя-администратора с полными правами."""
    return manager.create_user_subscription(
        user_id=user_id, email=email, role=UserRole.ADMIN, bitrix_user_id=bitrix_user_id
    )


def bulk_update_rules(
    manager: NotificationSubscriptionManager, notification_type: str, enabled: bool
) -> int:
    """Массовое обновление правил для всех пользователей.

    Args:
        manager: Менеджер подписок
        notification_type: Тип уведомления
        enabled: Включить/выключить

    Returns:
        Количество обновленных правил
    """
    updated_count = 0

    for user_id, subscription in manager.subscriptions.items():
        for rule in subscription.rules:
            if rule.notification_type == notification_type:
                rule.enabled = enabled
                rule.updated_at = datetime.now()
                updated_count += 1

        if any(
            rule.notification_type == notification_type for rule in subscription.rules
        ):
            subscription.updated_at = datetime.now()

    if updated_count > 0:
        manager._save_subscriptions()
        logger.info(f"Обновлено {updated_count} правил для типа {notification_type}")

    return updated_count
