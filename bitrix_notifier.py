"""Модуль для отправки уведомлений через Bitrix24."""

import os
from datetime import datetime
from enum import Enum
from typing import Any, Optional

import requests
from loguru import logger


class BitrixNotificationType(Enum):
    """Типы уведомлений для Bitrix24."""

    TASK_CREATED = "task_created"
    TASK_UPDATED = "task_updated"
    DOCUMENT_CHECK_COMPLETED = "document_check_completed"
    SUPPLIER_STATUS_CHANGED = "supplier_status_changed"
    SYSTEM_ERROR = "system_error"
    PRICE_ALERT = "price_alert"
    CONTRACT_EXPIRING = "contract_expiring"
    QUALITY_ISSUE = "quality_issue"
    BATCH_PROCESSING_COMPLETED = "batch_processing_completed"
    PAYMENT_REMINDER = "payment_reminder"


class BitrixPriority(Enum):
    """Приоритеты задач в Bitrix24."""

    LOW = "1"
    NORMAL = "2"
    HIGH = "3"


class BitrixNotifier:
    """Класс для работы с уведомлениями Bitrix24."""

    def __init__(self, webhook_url: Optional[str] = None):
        """Инициализация Bitrix24 нотификатора.

        Args:
            webhook_url: URL вебхука Bitrix24. Если не указан, берется из переменной окружения.
        """
        self.webhook_url = webhook_url or os.getenv("BITRIX24_WEBHOOK_URL")
        if not self.webhook_url:
            raise ValueError("Не указан BITRIX24_WEBHOOK_URL")

        self.default_user_id = os.getenv("BITRIX24_DEFAULT_USER_ID", "1")
        self.timeout = int(os.getenv("BITRIX24_TIMEOUT", "30"))

    def _make_request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Выполнить запрос к Bitrix24 API.

        Args:
            method: Метод API
            params: Параметры запроса

        Returns:
            Ответ от API

        Raises:
            requests.RequestException: При ошибке запроса
        """
        url = f"{self.webhook_url}/{method}"

        try:
            response = requests.post(
                url,
                json=params,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()

            result = response.json()

            if "error" in result:
                logger.error(f"Ошибка Bitrix24 API: {result['error']}")
                raise requests.RequestException(
                    f"Bitrix24 API Error: {result['error']}"
                )

            return result

        except requests.RequestException as e:
            logger.error(f"Ошибка запроса к Bitrix24: {e}")
            raise

    def create_task(
        self,
        title: str,
        description: str,
        responsible_id: Optional[str] = None,
        priority: BitrixPriority = BitrixPriority.NORMAL,
        deadline: Optional[str] = None,
        group_id: Optional[str] = None,
    ) -> Optional[str]:
        """Создать задачу в Bitrix24.

        Args:
            title: Заголовок задачи
            description: Описание задачи
            responsible_id: ID ответственного пользователя
            priority: Приоритет задачи
            deadline: Крайний срок (формат: Y-m-d H:i:s)
            group_id: ID группы/проекта

        Returns:
            ID созданной задачи или None при ошибке
        """
        try:
            params = {
                "fields": {
                    "TITLE": title,
                    "DESCRIPTION": description,
                    "RESPONSIBLE_ID": responsible_id or self.default_user_id,
                    "PRIORITY": priority.value,
                    "CREATED_BY": self.default_user_id,
                }
            }

            if deadline:
                params["fields"]["DEADLINE"] = deadline

            if group_id:
                params["fields"]["GROUP_ID"] = group_id

            result = self._make_request("tasks.task.add", params)

            task_id = result.get("result", {}).get("task", {}).get("id")
            if task_id:
                logger.info(f"Создана задача Bitrix24: {task_id}")
                return str(task_id)

            return None

        except Exception as e:
            logger.error(f"Ошибка создания задачи Bitrix24: {e}")
            return None

    def update_task(self, task_id: str, fields: dict[str, Any]) -> bool:
        """Обновить задачу в Bitrix24.

        Args:
            task_id: ID задачи
            fields: Поля для обновления

        Returns:
            True если обновление успешно
        """
        try:
            params = {"taskId": task_id, "fields": fields}

            self._make_request("tasks.task.update", params)
            logger.info(f"Обновлена задача Bitrix24: {task_id}")
            return True

        except Exception as e:
            logger.error(f"Ошибка обновления задачи Bitrix24: {e}")
            return False

    def add_task_comment(self, task_id: str, message: str) -> bool:
        """Добавить комментарий к задаче.

        Args:
            task_id: ID задачи
            message: Текст комментария

        Returns:
            True если комментарий добавлен
        """
        try:
            params = {
                "taskId": task_id,
                "fields": {"POST_MESSAGE": message, "AUTHOR_ID": self.default_user_id},
            }

            self._make_request("task.commentitem.add", params)
            logger.info(f"Добавлен комментарий к задаче {task_id}")
            return True

        except Exception as e:
            logger.error(f"Ошибка добавления комментария: {e}")
            return False

    def send_notification(
        self,
        user_ids: list[str],
        message: str,
        notification_type: BitrixNotificationType = BitrixNotificationType.SYSTEM_ERROR,
    ) -> bool:
        """Отправить уведомление пользователям.

        Args:
            user_ids: Список ID пользователей
            message: Текст уведомления
            notification_type: Тип уведомления

        Returns:
            True если уведомление отправлено
        """
        try:
            for user_id in user_ids:
                params = {
                    "to": user_id,
                    "message": message,
                    "type": "1",  # Системное уведомление
                    "tag": notification_type.value,
                }

                self._make_request("im.notify", params)

            logger.info(f"Отправлено уведомление {len(user_ids)} пользователям")
            return True

        except Exception as e:
            logger.error(f"Ошибка отправки уведомления: {e}")
            return False

    def create_lead(
        self,
        title: str,
        name: str,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        company: Optional[str] = None,
        source_description: Optional[str] = None,
    ) -> Optional[str]:
        """Создать лид в Bitrix24.

        Args:
            title: Название лида
            name: Имя контакта
            phone: Телефон
            email: Email
            company: Компания
            source_description: Описание источника

        Returns:
            ID созданного лида или None при ошибке
        """
        try:
            params = {
                "fields": {
                    "TITLE": title,
                    "NAME": name,
                    "OPENED": "Y",
                    "ASSIGNED_BY_ID": self.default_user_id,
                }
            }

            if phone:
                params["fields"]["PHONE"] = [{"VALUE": phone, "VALUE_TYPE": "WORK"}]

            if email:
                params["fields"]["EMAIL"] = [{"VALUE": email, "VALUE_TYPE": "WORK"}]

            if company:
                params["fields"]["COMPANY_TITLE"] = company

            if source_description:
                params["fields"]["SOURCE_DESCRIPTION"] = source_description

            result = self._make_request("crm.lead.add", params)

            lead_id = result.get("result")
            if lead_id:
                logger.info(f"Создан лид Bitrix24: {lead_id}")
                return str(lead_id)

            return None

        except Exception as e:
            logger.error(f"Ошибка создания лида Bitrix24: {e}")
            return None


# === СПЕЦИАЛИЗИРОВАННЫЕ ФУНКЦИИ УВЕДОМЛЕНИЙ ===


def notify_document_check_completed(
    notifier: BitrixNotifier,
    responsible_ids: list[str],
    document_name: str,
    overall_score: float,
    recommendation: str,
    violations_count: int,
    create_task: bool = True,
) -> Optional[str]:
    """Уведомление о завершении проверки документа.

    Args:
        notifier: Экземпляр BitrixNotifier
        responsible_ids: Список ID ответственных пользователей
        document_name: Название документа
        overall_score: Общая оценка
        recommendation: Рекомендация
        violations_count: Количество нарушений
        create_task: Создавать ли задачу

    Returns:
        ID созданной задачи или None
    """
    message = f"""Завершена проверка документа: {document_name}

Результаты:
• Общая оценка: {overall_score}/10
• Рекомендация: {recommendation}
• Найдено нарушений: {violations_count}

Время проверки: {datetime.now().strftime('%d.%m.%Y %H:%M')}"""

    # Отправляем уведомление
    notifier.send_notification(
        user_ids=responsible_ids,
        message=message,
        notification_type=BitrixNotificationType.DOCUMENT_CHECK_COMPLETED,
    )

    # Создаем задачу если требуется
    if create_task:
        priority = BitrixPriority.HIGH if overall_score < 5 else BitrixPriority.NORMAL

        return notifier.create_task(
            title=f"Проверка документа: {document_name}",
            description=message,
            responsible_id=responsible_ids[0] if responsible_ids else None,
            priority=priority,
        )

    return None


def notify_supplier_status_changed(
    notifier: BitrixNotifier,
    responsible_ids: list[str],
    supplier_name: str,
    supplier_inn: str,
    old_status: str,
    new_status: str,
    reason: str,
    create_task: bool = True,
) -> Optional[str]:
    """Уведомление об изменении статуса поставщика."""
    message = f"""Изменен статус поставщика: {supplier_name}

Детали:
• ИНН: {supplier_inn}
• Предыдущий статус: {old_status}
• Новый статус: {new_status}
• Причина: {reason}
• Дата изменения: {datetime.now().strftime('%d.%m.%Y %H:%M')}"""

    notifier.send_notification(
        user_ids=responsible_ids,
        message=message,
        notification_type=BitrixNotificationType.SUPPLIER_STATUS_CHANGED,
    )

    if create_task:
        priority = (
            BitrixPriority.HIGH
            if "заблокирован" in new_status.lower()
            else BitrixPriority.NORMAL
        )

        return notifier.create_task(
            title=f"Изменение статуса поставщика: {supplier_name}",
            description=message,
            responsible_id=responsible_ids[0] if responsible_ids else None,
            priority=priority,
        )

    return None


def notify_system_error(
    notifier: BitrixNotifier,
    admin_ids: list[str],
    error_type: str,
    error_description: str,
    error_traceback: str,
    create_task: bool = True,
) -> Optional[str]:
    """Уведомление о системной ошибке."""
    message = f"""🚨 СИСТЕМНАЯ ОШИБКА

Тип: {error_type}
Время: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
Описание: {error_description}

Требуется немедленное вмешательство!"""

    notifier.send_notification(
        user_ids=admin_ids,
        message=message,
        notification_type=BitrixNotificationType.SYSTEM_ERROR,
    )

    if create_task:
        return notifier.create_task(
            title=f"КРИТИЧЕСКАЯ ОШИБКА: {error_type}",
            description=f"{message}\n\nТрассировка:\n{error_traceback}",
            responsible_id=admin_ids[0] if admin_ids else None,
            priority=BitrixPriority.HIGH,
        )

    return None


def notify_price_alert(
    notifier: BitrixNotifier,
    responsible_ids: list[str],
    product_name: str,
    supplier_name: str,
    old_price: float,
    new_price: float,
    currency: str = "RUB",
    create_task: bool = True,
) -> Optional[str]:
    """Уведомление о значительном изменении цены."""
    price_change = ((new_price - old_price) / old_price) * 100
    change_symbol = "📈" if price_change > 0 else "📉"

    message = f"""{change_symbol} Ценовое предупреждение

Товар: {product_name}
Поставщик: {supplier_name}
Предыдущая цена: {old_price} {currency}
Новая цена: {new_price} {currency}
Изменение: {price_change:+.1f}%
Дата: {datetime.now().strftime('%d.%m.%Y')}

Рекомендуется проверить обоснованность изменения."""

    notifier.send_notification(
        user_ids=responsible_ids,
        message=message,
        notification_type=BitrixNotificationType.PRICE_ALERT,
    )

    if create_task:
        priority = (
            BitrixPriority.HIGH if abs(price_change) > 20 else BitrixPriority.NORMAL
        )

        return notifier.create_task(
            title=f"Изменение цены: {product_name}",
            description=message,
            responsible_id=responsible_ids[0] if responsible_ids else None,
            priority=priority,
        )

    return None


def notify_batch_processing_completed(
    notifier: BitrixNotifier,
    responsible_ids: list[str],
    batch_id: str,
    total_documents: int,
    processed_successfully: int,
    processing_errors: int,
    processing_time: str,
    create_task: bool = False,
) -> Optional[str]:
    """Уведомление о завершении пакетной обработки."""
    success_rate = (
        (processed_successfully / total_documents) * 100 if total_documents > 0 else 0
    )
    status_emoji = "✅" if success_rate >= 95 else "⚠️" if success_rate >= 80 else "❌"

    message = f"""{status_emoji} Пакетная обработка завершена

Идентификатор: {batch_id}
Всего документов: {total_documents}
Успешно обработано: {processed_successfully}
Ошибок: {processing_errors}
Успешность: {success_rate:.1f}%
Время обработки: {processing_time}
Завершено: {datetime.now().strftime('%d.%m.%Y %H:%M')}"""

    notifier.send_notification(
        user_ids=responsible_ids,
        message=message,
        notification_type=BitrixNotificationType.BATCH_PROCESSING_COMPLETED,
    )

    if create_task and processing_errors > 0:
        return notifier.create_task(
            title=f"Ошибки в пакетной обработке: {batch_id}",
            description=message,
            responsible_id=responsible_ids[0] if responsible_ids else None,
            priority=BitrixPriority.NORMAL,
        )

    return None


# === БЕЗОПАСНЫЕ ШЛЮЗЫ УВЕДОМЛЕНИЙ ===


class BitrixGateway:
    """Безопасный шлюз для работы с Bitrix24 API."""

    def __init__(self, webhook_url: Optional[str] = None, mock_mode: bool = False):
        """Инициализация шлюза.

        Args:
            webhook_url: URL вебхука Bitrix24
            mock_mode: Режим мок-тестирования (без реальных запросов)
        """
        self.mock_mode = mock_mode
        self.notifier = None if mock_mode else BitrixNotifier(webhook_url)
        self.mock_responses = {}
        self.call_history = []

    def set_mock_response(self, method: str, response: dict[str, Any]):
        """Установить мок-ответ для метода.

        Args:
            method: Название метода API
            response: Мок-ответ
        """
        self.mock_responses[method] = response

    def _mock_call(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Имитировать вызов API в режиме мока.

        Args:
            method: Метод API
            params: Параметры запроса

        Returns:
            Мок-ответ
        """
        self.call_history.append(
            {
                "method": method,
                "params": params,
                "timestamp": datetime.now().isoformat(),
            }
        )

        if method in self.mock_responses:
            return self.mock_responses[method]

        # Стандартные мок-ответы
        default_responses = {
            "tasks.task.add": {"result": {"task": {"id": "mock_task_123"}}},
            "tasks.task.update": {"result": True},
            "task.commentitem.add": {"result": True},
            "im.notify": {"result": True},
            "crm.lead.add": {"result": "mock_lead_456"},
            "profile": {"result": {"ID": "1", "NAME": "Test User"}},
        }

        return default_responses.get(method, {"result": True})

    def create_task(
        self,
        title: str,
        description: str,
        responsible_id: Optional[str] = None,
        priority: BitrixPriority = BitrixPriority.NORMAL,
        deadline: Optional[str] = None,
        group_id: Optional[str] = None,
    ) -> Optional[str]:
        """Создать задачу через безопасный шлюз."""
        if self.mock_mode:
            result = self._mock_call(
                "tasks.task.add",
                {
                    "fields": {
                        "TITLE": title,
                        "DESCRIPTION": description,
                        "RESPONSIBLE_ID": responsible_id or "1",
                        "PRIORITY": priority.value,
                    }
                },
            )
            return result.get("result", {}).get("task", {}).get("id", "mock_task_123")

        return self.notifier.create_task(
            title, description, responsible_id, priority, deadline, group_id
        )

    def send_notification(
        self,
        user_ids: list[str],
        message: str,
        notification_type: BitrixNotificationType = BitrixNotificationType.SYSTEM_ERROR,
    ) -> bool:
        """Отправить уведомление через безопасный шлюз."""
        if self.mock_mode:
            for user_id in user_ids:
                self._mock_call(
                    "im.notify",
                    {
                        "to": user_id,
                        "message": message,
                        "type": "1",
                        "tag": notification_type.value,
                    },
                )
            return True

        return self.notifier.send_notification(user_ids, message, notification_type)

    def set_mock_failure(self, method: str, should_fail: bool = True):
        """Установить мок-ошибку для конкретного метода.

        Args:
            method: Название метода API
            should_fail: Должен ли имитировать ошибку
        """
        self.mock_responses[method] = {"error": "mock_failure", "result": False}

    def get_call_history(self) -> list[dict[str, Any]]:
        """Получить историю вызовов (для тестирования)."""
        return self.call_history.copy()

    def clear_history(self):
        """Очистить историю вызовов."""
        self.call_history.clear()


class SecureBitrixNotifier:
    """Безопасный нотификатор с дополнительной валидацией."""

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """Инициализация безопасного нотификатора.

        Args:
            config: Конфигурация безопасности
        """
        self.config = config or {}
        self.gateway = None
        self.rate_limiter = {}
        self.max_retries = self.config.get("max_retries", 3)
        self.retry_delay = self.config.get("retry_delay", 1)
        self.enable_mock_fallback = self.config.get("enable_mock_fallback", True)

    def initialize(self, webhook_url: Optional[str] = None, mock_mode: bool = False):
        """Инициализировать шлюз."""
        try:
            self.gateway = BitrixGateway(webhook_url, mock_mode)
            logger.info("Безопасный шлюз Bitrix24 инициализирован")
        except Exception as e:
            if self.enable_mock_fallback and not mock_mode:
                logger.warning(f"Ошибка инициализации, переключение в мок-режим: {e}")
                self.gateway = BitrixGateway(webhook_url, True)
            else:
                raise

    def _validate_user_ids(self, user_ids: list[str]) -> list[str]:
        """Валидировать ID пользователей."""
        if not isinstance(user_ids, list):
            raise ValueError("user_ids должен быть списком")

        valid_ids = []
        for user_id in user_ids:
            if isinstance(user_id, str) and user_id.strip().isdigit():
                valid_ids.append(user_id.strip())
            elif isinstance(user_id, int):
                valid_ids.append(str(user_id))
            else:
                logger.warning(f"Пропущен невалидный ID пользователя: {user_id}")

        return valid_ids

    def create_secure_task(
        self,
        title: str,
        description: str,
        responsible_ids: list[str],
        priority: BitrixPriority = BitrixPriority.NORMAL,
    ) -> Optional[str]:
        """Создать задачу с безопасной валидацией."""
        if not self.gateway:
            raise RuntimeError("Шлюз не инициализирован")

        if not title or not title.strip():
            raise ValueError("Заголовок задачи не может быть пустым")

        if len(title) > 255:
            title = title[:252] + "..."

        valid_responsible_ids = self._validate_user_ids(responsible_ids)
        if not valid_responsible_ids:
            logger.warning("Нет валидных ID ответственных, используем default")
            valid_responsible_ids = ["1"]

        return self.gateway.create_task(
            title, description, valid_responsible_ids[0], priority
        )

    def send_secure_notification(
        self,
        user_ids: list[str],
        message: str,
        notification_type: BitrixNotificationType = BitrixNotificationType.SYSTEM_ERROR,
    ) -> bool:
        """Отправить безопасное уведомление."""
        if not self.gateway:
            raise RuntimeError("Шлюз не инициализирован")

        if not message or not message.strip():
            raise ValueError("Сообщение не может быть пустым")

        if len(message) > 10000:
            message = message[:9997] + "..."

        valid_user_ids = self._validate_user_ids(user_ids)
        if not valid_user_ids:
            logger.error("Нет валидных ID пользователей для отправки уведомления")
            return False

        return self.gateway.send_notification(
            valid_user_ids, message, notification_type
        )


# === УТИЛИТЫ И МОК-ТОЧКИ ===


def get_default_notifier() -> BitrixNotifier:
    """Получить настроенный по умолчанию нотификатор."""
    return BitrixNotifier()


def get_secure_notifier(
    config: Optional[dict[str, Any]] = None
) -> SecureBitrixNotifier:
    """Получить безопасный нотификатор."""
    return SecureBitrixNotifier(config)


def create_mock_gateway() -> BitrixGateway:
    """Создать мок-шлюз для тестирования."""
    gateway = BitrixGateway(mock_mode=True)

    # Настраиваем стандартные мок-ответы
    gateway.set_mock_response(
        "tasks.task.add", {"result": {"task": {"id": "mock_123"}}}
    )
    gateway.set_mock_response("im.notify", {"result": True})
    gateway.set_mock_response("crm.lead.add", {"result": "mock_lead_456"})

    return gateway


def test_connection(webhook_url: Optional[str] = None) -> bool:
    """Проверить подключение к Bitrix24.

    Args:
        webhook_url: URL вебхука для тестирования

    Returns:
        True если подключение успешно
    """
    try:
        notifier = BitrixNotifier(webhook_url)
        # Пробуем получить информацию о текущем пользователе
        result = notifier._make_request("profile", {})
        logger.info("Подключение к Bitrix24 успешно")
        return True

    except Exception as e:
        logger.error(f"Ошибка подключения к Bitrix24: {e}")
        return False
