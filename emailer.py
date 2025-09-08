import os
import smtplib
from datetime import datetime
from email.message import EmailMessage
from enum import Enum
from typing import Any, Optional

from loguru import logger


class NotificationType(Enum):
    """Типы уведомлений."""

    DOCUMENT_CHECK_COMPLETED = "document_check_completed"
    DOCUMENT_CHECK_FAILED = "document_check_failed"
    SUPPLIER_STATUS_CHANGED = "supplier_status_changed"
    SYSTEM_ERROR = "system_error"
    BATCH_PROCESSING_COMPLETED = "batch_processing_completed"
    PRICE_ALERT = "price_alert"
    CONTRACT_EXPIRING = "contract_expiring"
    QUALITY_ISSUE = "quality_issue"
    PAYMENT_REMINDER = "payment_reminder"


class EmailTemplate:
    """Шаблоны email уведомлений."""

    @staticmethod
    def get_template(notification_type: NotificationType, **kwargs) -> dict[str, str]:
        """Получить шаблон для указанного типа уведомления."""
        templates = {
            NotificationType.DOCUMENT_CHECK_COMPLETED: {
                "subject": "Проверка документа завершена - {document_name}",
                "body": """
Добрый день!

Проверка документа "{document_name}" завершена.

Результаты проверки:
- Общая оценка: {overall_score}/10
- Рекомендация: {recommendation}
- Найдено нарушений: {violations_count}

Детальный отчет во вложении.

С уважением,
Система проверки тендерных документов
""",
            },
            NotificationType.DOCUMENT_CHECK_FAILED: {
                "subject": "Ошибка при проверке документа - {document_name}",
                "body": """
Добрый день!

При проверке документа "{document_name}" произошла ошибка.

Описание ошибки: {error_message}

Пожалуйста, проверьте документ и повторите попытку.

С уважением,
Система проверки тендерных документов
""",
            },
            NotificationType.SUPPLIER_STATUS_CHANGED: {
                "subject": "Изменение статуса поставщика - {supplier_name}",
                "body": """
Добрый день!

Статус поставщика "{supplier_name}" (ИНН: {supplier_inn}) изменен.

Предыдущий статус: {old_status}
Новый статус: {new_status}
Дата изменения: {change_date}

Причина изменения: {reason}

С уважением,
Система управления поставщиками
""",
            },
            NotificationType.SYSTEM_ERROR: {
                "subject": "Системная ошибка - {error_type}",
                "body": """
Внимание! Обнаружена системная ошибка.

Тип ошибки: {error_type}
Время возникновения: {error_time}
Описание: {error_description}

Трассировка:
{error_traceback}

Требуется немедленное вмешательство администратора.

Система проверки тендерных документов
""",
            },
            NotificationType.BATCH_PROCESSING_COMPLETED: {
                "subject": "Пакетная обработка завершена - {batch_id}",
                "body": """
Добрый день!

Пакетная обработка документов завершена.

Идентификатор пакета: {batch_id}
Всего документов: {total_documents}
Успешно обработано: {processed_successfully}
Ошибок: {processing_errors}
Время обработки: {processing_time}

Детальный отчет во вложении.

С уважением,
Система проверки тендерных документов
""",
            },
            NotificationType.PRICE_ALERT: {
                "subject": "Ценовое предупреждение - {product_name}",
                "body": """
Добрый день!

Обнаружено значительное изменение цены.

Товар: {product_name}
Поставщик: {supplier_name}
Предыдущая цена: {old_price} {currency}
Новая цена: {new_price} {currency}
Изменение: {price_change}%

Дата изменения: {change_date}

Рекомендуется проверить обоснованность изменения цены.

С уважением,
Система мониторинга цен
""",
            },
            NotificationType.CONTRACT_EXPIRING: {
                "subject": "Истекает срок договора - {contract_number}",
                "body": """
Добрый день!

Приближается срок окончания договора.

Номер договора: {contract_number}
Поставщик: {supplier_name}
Дата окончания: {expiry_date}
Осталось дней: {days_remaining}

Рекомендуется начать процедуру продления или поиска нового поставщика.

С уважением,
Система управления договорами
""",
            },
            NotificationType.QUALITY_ISSUE: {
                "subject": "Проблема качества - {supplier_name}",
                "body": """
Добрый день!

Зафиксирована проблема качества у поставщика.

Поставщик: {supplier_name}
Тип проблемы: {issue_type}
Описание: {issue_description}
Дата возникновения: {issue_date}
Статус: {issue_status}

Требуется принятие мер по устранению проблемы.

С уважением,
Система контроля качества
""",
            },
            NotificationType.PAYMENT_REMINDER: {
                "subject": "Напоминание об оплате - {invoice_number}",
                "body": """
Добрый день!

Напоминаем о необходимости оплаты.

Номер счета: {invoice_number}
Поставщик: {supplier_name}
Сумма: {amount} {currency}
Дата выставления: {invoice_date}
Срок оплаты: {due_date}
Просрочка: {overdue_days} дней

Пожалуйста, произведите оплату в ближайшее время.

С уважением,
Финансовый отдел
""",
            },
        }

        template = templates.get(notification_type)
        if not template:
            raise ValueError(f"Неизвестный тип уведомления: {notification_type}")

        try:
            return {
                "subject": template["subject"].format(**kwargs),
                "body": template["body"].format(**kwargs),
            }
        except KeyError as e:
            logger.error(
                f"Отсутствует обязательный параметр для шаблона {notification_type}: {e}"
            )
            raise ValueError(f"Отсутствует обязательный параметр: {e}")


def send_email_with_pdf(recipient: str, subject: str, body: str, pdf_path: str) -> bool:
    """Отправить email с PDF вложением (оригинальная функция)."""
    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = os.getenv("SMTP_FROM")
        msg["To"] = recipient
        msg.set_content(body)

        with open(pdf_path, "rb") as f:
            msg.add_attachment(
                f.read(),
                maintype="application",
                subtype="pdf",
                filename=os.path.basename(pdf_path),
            )

        with smtplib.SMTP_SSL(os.getenv("SMTP_SERVER"), 465) as smtp:
            smtp.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD"))
            smtp.send_message(msg)

        logger.info(f"Email с PDF отправлен успешно: {recipient}")
        return True

    except Exception as e:
        logger.error(f"Ошибка отправки email с PDF: {e}")
        return False


def send_notification_email(
    recipients: list[str],
    notification_type: NotificationType,
    attachments: Optional[list[str]] = None,
    **kwargs,
) -> bool:
    """Отправить уведомление по email.

    Args:
        recipients: Список получателей
        notification_type: Тип уведомления
        attachments: Список путей к файлам для вложения
        **kwargs: Параметры для шаблона

    Returns:
        bool: True если отправка успешна
    """
    try:
        # Получаем шаблон
        template = EmailTemplate.get_template(notification_type, **kwargs)

        # Создаем сообщение
        msg = EmailMessage()
        msg["Subject"] = template["subject"]
        msg["From"] = os.getenv("SMTP_FROM")
        msg["To"] = ", ".join(recipients)
        msg.set_content(template["body"])

        # Добавляем вложения
        if attachments:
            for attachment_path in attachments:
                if os.path.exists(attachment_path):
                    with open(attachment_path, "rb") as f:
                        file_data = f.read()
                        filename = os.path.basename(attachment_path)

                        # Определяем тип файла
                        if filename.endswith(".pdf"):
                            msg.add_attachment(
                                file_data,
                                maintype="application",
                                subtype="pdf",
                                filename=filename,
                            )
                        elif filename.endswith((".txt", ".log")):
                            msg.add_attachment(
                                file_data,
                                maintype="text",
                                subtype="plain",
                                filename=filename,
                            )
                        elif filename.endswith(".json"):
                            msg.add_attachment(
                                file_data,
                                maintype="application",
                                subtype="json",
                                filename=filename,
                            )
                        else:
                            msg.add_attachment(
                                file_data,
                                maintype="application",
                                subtype="octet-stream",
                                filename=filename,
                            )
                else:
                    logger.warning(f"Файл вложения не найден: {attachment_path}")

        # Отправляем email
        with smtplib.SMTP_SSL(os.getenv("SMTP_SERVER"), 465) as smtp:
            smtp.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD"))
            smtp.send_message(msg)

        logger.info(f"Уведомление {notification_type.value} отправлено: {recipients}")
        return True

    except Exception as e:
        logger.error(f"Ошибка отправки уведомления {notification_type.value}: {e}")
        return False


def send_simple_email(
    recipients: list[str],
    subject: str,
    body: str,
    attachments: Optional[list[str]] = None,
) -> bool:
    """Отправить простое email сообщение.

    Args:
        recipients: Список получателей
        subject: Тема сообщения
        body: Текст сообщения
        attachments: Список путей к файлам для вложения

    Returns:
        bool: True если отправка успешна
    """
    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = os.getenv("SMTP_FROM")
        msg["To"] = ", ".join(recipients)
        msg.set_content(body)

        # Добавляем вложения
        if attachments:
            for attachment_path in attachments:
                if os.path.exists(attachment_path):
                    with open(attachment_path, "rb") as f:
                        file_data = f.read()
                        filename = os.path.basename(attachment_path)
                        msg.add_attachment(
                            file_data,
                            maintype="application",
                            subtype="octet-stream",
                            filename=filename,
                        )
                else:
                    logger.warning(f"Файл вложения не найден: {attachment_path}")

        # Отправляем email
        with smtplib.SMTP_SSL(os.getenv("SMTP_SERVER"), 465) as smtp:
            smtp.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD"))
            smtp.send_message(msg)

        logger.info(f"Простое email отправлено: {recipients}")
        return True

    except Exception as e:
        logger.error(f"Ошибка отправки простого email: {e}")
        return False


# === БЕЗОПАСНЫЕ ШЛЮЗЫ УВЕДОМЛЕНИЙ ===


class EmailGateway:
    """Безопасный шлюз для отправки email уведомлений."""

    def __init__(self, mock_mode: bool = False):
        """Инициализация email шлюза.

        Args:
            mock_mode: Режим мок-тестирования (без реальной отправки)
        """
        self.mock_mode = mock_mode
        self.sent_emails = []
        self.mock_failures = {}

    def set_mock_failure(self, recipient: str, should_fail: bool = True):
        """Установить мок-ошибку для конкретного получателя.

        Args:
            recipient: Email получателя
            should_fail: Должен ли имитировать ошибку
        """
        self.mock_failures[recipient] = should_fail

    def _mock_send(
        self,
        recipients: list[str],
        subject: str,
        body: str,
        attachments: Optional[list[str]] = None,
    ) -> bool:
        """Имитировать отправку email в режиме мока.

        Args:
            recipients: Список получателей
            subject: Тема сообщения
            body: Текст сообщения
            attachments: Вложения

        Returns:
            Успешность отправки
        """
        email_data = {
            "recipients": recipients,
            "subject": subject,
            "body": body,
            "attachments": attachments or [],
            "timestamp": datetime.now().isoformat(),
            "mock_mode": True,
        }

        self.sent_emails.append(email_data)

        # Проверяем мок-ошибки
        for recipient in recipients:
            if recipient in self.mock_failures and self.mock_failures[recipient]:
                logger.warning(f"Мок-ошибка отправки для {recipient}")
                return False

        return True

    def send_email(
        self,
        recipients: list[str],
        subject: str,
        body: str,
        attachments: Optional[list[str]] = None,
    ) -> bool:
        """Отправить email через безопасный шлюз."""
        if self.mock_mode:
            return self._mock_send(recipients, subject, body, attachments)

        return send_simple_email(recipients, subject, body, attachments)

    def send_notification(
        self,
        recipients: list[str],
        notification_type: NotificationType,
        attachments: Optional[list[str]] = None,
        **kwargs,
    ) -> bool:
        """Отправить уведомление через безопасный шлюз."""
        try:
            template = EmailTemplate.get_template(notification_type, **kwargs)

            if self.mock_mode:
                return self._mock_send(
                    recipients, template["subject"], template["body"], attachments
                )

            return send_notification_email(
                recipients, notification_type, attachments, **kwargs
            )

        except Exception as e:
            logger.error(f"Ошибка в email шлюзе: {e}")
            return False

    def get_sent_emails(self) -> list[dict[str, Any]]:
        """Получить список отправленных email (для тестирования)."""
        return self.sent_emails.copy()

    def clear_sent_emails(self):
        """Очистить список отправленных email."""
        self.sent_emails.clear()

    def clear_mock_failures(self):
        """Очистить мок-ошибки."""
        self.mock_failures.clear()


class SecureEmailNotifier:
    """Безопасный email нотификатор с валидацией и защитой."""

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """Инициализация безопасного email нотификатора.

        Args:
            config: Конфигурация безопасности
        """
        self.config = config or {}
        self.gateway = None
        self.rate_limiter = {}
        self.max_recipients = self.config.get("max_recipients", 50)
        self.max_attachment_size = self.config.get(
            "max_attachment_size", 10 * 1024 * 1024
        )  # 10MB
        self.enable_mock_fallback = self.config.get("enable_mock_fallback", True)

    def initialize(self, mock_mode: bool = False):
        """Инициализировать email шлюз."""
        try:
            self.gateway = EmailGateway(mock_mode)

            # Проверяем наличие необходимых переменных окружения
            if not mock_mode:
                required_vars = [
                    "SMTP_FROM",
                    "SMTP_SERVER",
                    "SMTP_USER",
                    "SMTP_PASSWORD",
                ]
                missing_vars = [var for var in required_vars if not os.getenv(var)]

                if missing_vars:
                    if self.enable_mock_fallback:
                        logger.warning(
                            f"Отсутствуют переменные окружения: {missing_vars}, переключение в мок-режим"
                        )
                        self.gateway = EmailGateway(True)
                    else:
                        raise ValueError(
                            f"Отсутствуют обязательные переменные окружения: {missing_vars}"
                        )

            logger.info("Безопасный email шлюз инициализирован")

        except Exception as e:
            if self.enable_mock_fallback and not mock_mode:
                logger.warning(
                    f"Ошибка инициализации email шлюза, переключение в мок-режим: {e}"
                )
                self.gateway = EmailGateway(True)
            else:
                raise

    def _validate_recipients(self, recipients: list[str]) -> list[str]:
        """Валидировать email адреса получателей."""
        if not isinstance(recipients, list):
            raise ValueError("recipients должен быть списком")

        if len(recipients) > self.max_recipients:
            logger.warning(
                f"Превышено максимальное количество получателей: {len(recipients)}"
            )
            recipients = recipients[: self.max_recipients]

        import re

        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        valid_emails = []

        for email in recipients:
            if isinstance(email, str) and re.match(email_pattern, email.strip()):
                valid_emails.append(email.strip().lower())
            else:
                logger.warning(f"Пропущен невалидный email: {email}")

        return valid_emails

    def _validate_attachments(
        self, attachments: Optional[list[str]]
    ) -> Optional[list[str]]:
        """Валидировать вложения."""
        if not attachments:
            return None

        valid_attachments = []
        for attachment_path in attachments:
            if os.path.exists(attachment_path):
                file_size = os.path.getsize(attachment_path)
                if file_size <= self.max_attachment_size:
                    valid_attachments.append(attachment_path)
                else:
                    logger.warning(
                        f"Файл превышает максимальный размер: {attachment_path}"
                    )
            else:
                logger.warning(f"Файл не найден: {attachment_path}")

        return valid_attachments if valid_attachments else None

    def send_secure_notification(
        self,
        recipients: list[str],
        notification_type: NotificationType,
        attachments: Optional[list[str]] = None,
        **kwargs,
    ) -> bool:
        """Отправить безопасное email уведомление."""
        if not self.gateway:
            raise RuntimeError("Email шлюз не инициализирован")

        valid_recipients = self._validate_recipients(recipients)
        if not valid_recipients:
            logger.error("Нет валидных email адресов для отправки")
            return False

        valid_attachments = self._validate_attachments(attachments)

        try:
            return self.gateway.send_notification(
                valid_recipients, notification_type, valid_attachments, **kwargs
            )
        except Exception as e:
            logger.error(f"Ошибка отправки безопасного уведомления: {e}")
            return False

    def send_secure_simple_email(
        self,
        recipients: list[str],
        subject: str,
        body: str,
        attachments: Optional[list[str]] = None,
    ) -> bool:
        """Отправить простое безопасное email сообщение."""
        if not self.gateway:
            raise RuntimeError("Email шлюз не инициализирован")

        valid_recipients = self._validate_recipients(recipients)
        if not valid_recipients:
            logger.error("Нет валидных email адресов для отправки")
            return False

        if not subject or not subject.strip():
            raise ValueError("Тема сообщения не может быть пустой")

        if len(subject) > 255:
            subject = subject[:252] + "..."

        valid_attachments = self._validate_attachments(attachments)

        try:
            return self.gateway.send_email(
                valid_recipients, subject, body, valid_attachments
            )
        except Exception as e:
            logger.error(f"Ошибка отправки безопасного email: {e}")
            return False


# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ СПЕЦИФИЧЕСКИХ УВЕДОМЛЕНИЙ ===


def notify_document_check_completed(
    recipients: list[str],
    document_name: str,
    overall_score: float,
    recommendation: str,
    violations_count: int,
    report_path: Optional[str] = None,
) -> bool:
    """Уведомление о завершении проверки документа."""
    attachments = [report_path] if report_path else None
    return send_notification_email(
        recipients=recipients,
        notification_type=NotificationType.DOCUMENT_CHECK_COMPLETED,
        attachments=attachments,
        document_name=document_name,
        overall_score=overall_score,
        recommendation=recommendation,
        violations_count=violations_count,
    )


def notify_supplier_status_changed(
    recipients: list[str],
    supplier_name: str,
    supplier_inn: str,
    old_status: str,
    new_status: str,
    reason: str,
) -> bool:
    """Уведомление об изменении статуса поставщика."""
    return send_notification_email(
        recipients=recipients,
        notification_type=NotificationType.SUPPLIER_STATUS_CHANGED,
        supplier_name=supplier_name,
        supplier_inn=supplier_inn,
        old_status=old_status,
        new_status=new_status,
        change_date=datetime.now().strftime("%d.%m.%Y %H:%M"),
        reason=reason,
    )


def notify_system_error(
    recipients: list[str], error_type: str, error_description: str, error_traceback: str
) -> bool:
    """Уведомление о системной ошибке."""
    return send_notification_email(
        recipients=recipients,
        notification_type=NotificationType.SYSTEM_ERROR,
        error_type=error_type,
        error_time=datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
        error_description=error_description,
        error_traceback=error_traceback,
    )


def notify_batch_processing_completed(
    recipients: list[str],
    batch_id: str,
    total_documents: int,
    processed_successfully: int,
    processing_errors: int,
    processing_time: str,
    report_path: Optional[str] = None,
) -> bool:
    """Уведомление о завершении пакетной обработки."""
    attachments = [report_path] if report_path else None
    return send_notification_email(
        recipients=recipients,
        notification_type=NotificationType.BATCH_PROCESSING_COMPLETED,
        attachments=attachments,
        batch_id=batch_id,
        total_documents=total_documents,
        processed_successfully=processed_successfully,
        processing_errors=processing_errors,
        processing_time=processing_time,
    )


def notify_price_alert(
    recipients: list[str],
    product_name: str,
    supplier_name: str,
    old_price: float,
    new_price: float,
    currency: str = "RUB",
) -> bool:
    """Уведомление о значительном изменении цены."""
    price_change = ((new_price - old_price) / old_price) * 100
    return send_notification_email(
        recipients=recipients,
        notification_type=NotificationType.PRICE_ALERT,
        product_name=product_name,
        supplier_name=supplier_name,
        old_price=old_price,
        new_price=new_price,
        currency=currency,
        price_change=f"{price_change:+.1f}",
        change_date=datetime.now().strftime("%d.%m.%Y"),
    )


# === УТИЛИТЫ И МОК-ТОЧКИ ===


def get_secure_email_notifier(
    config: Optional[dict[str, Any]] = None
) -> SecureEmailNotifier:
    """Получить безопасный email нотификатор."""
    return SecureEmailNotifier(config)


def create_email_mock_gateway() -> EmailGateway:
    """Создать мок-шлюз для email тестирования."""
    return EmailGateway(mock_mode=True)


def test_email_config() -> dict[str, bool]:
    """Проверить конфигурацию email."""
    config_status = {
        "smtp_from": bool(os.getenv("SMTP_FROM")),
        "smtp_server": bool(os.getenv("SMTP_SERVER")),
        "smtp_user": bool(os.getenv("SMTP_USER")),
        "smtp_password": bool(os.getenv("SMTP_PASSWORD")),
    }

    config_status["all_configured"] = all(config_status.values())

    return config_status
