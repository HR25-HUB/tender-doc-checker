"""Модуль автоматических действий для workflow."""

import asyncio
import json
import logging
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any, Optional

from bitrix_api import create_task
from emailer import send_email
from src.models import (
    BitrixTaskRequest,
    EmailRequest,
)


class AutoActionExecutor:
    """Исполнитель автоматических действий."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.action_handlers: dict[str, Callable] = {}
        self.notification_templates: dict[str, dict[str, str]] = {}
        self.escalation_rules: list[dict[str, Any]] = []

        # Регистрируем базовые обработчики
        self._register_default_handlers()
        self._load_notification_templates()
        self._load_escalation_rules()

    def _register_default_handlers(self):
        """Регистрирует базовые обработчики действий."""
        self.action_handlers.update(
            {
                "send_email": self.send_email_action,
                "create_task": self.create_task_action,
                "update_status": self.update_status_action,
                "generate_report": self.generate_report_action,
                "escalate": self.escalate_action,
                "approve_document": self.approve_document_action,
                "reject_document": self.reject_document_action,
                "notify_supplier": self.notify_supplier_action,
                "create_order": self.create_order_action,
                "schedule_meeting": self.schedule_meeting_action,
                "send_contract": self.send_contract_action,
                "archive_document": self.archive_document_action,
            }
        )

    def _load_notification_templates(self):
        """Загружает шаблоны уведомлений."""
        self.notification_templates = {
            "document_approved": {
                "subject": "Документ одобрен: {document_name}",
                "body": """Уважаемый {recipient_name},

Ваш документ "{document_name}" был успешно одобрен.

Детали:
- Тип документа: {document_type}
- Дата одобрения: {approval_date}
- Одобрил: {approver_name}

Следующие шаги:
{next_steps}

С уважением,
Система управления документами""",
            },
            "document_rejected": {
                "subject": "Документ отклонен: {document_name}",
                "body": """Уважаемый {recipient_name},

Ваш документ "{document_name}" был отклонен.

Причина отклонения:
{rejection_reason}

Детали:
- Тип документа: {document_type}
- Дата отклонения: {rejection_date}
- Отклонил: {rejector_name}

Для исправления обратитесь к ответственному лицу.

С уважением,
Система управления документами""",
            },
            "sla_warning": {
                "subject": "Предупреждение о нарушении SLA: {document_name}",
                "body": """Внимание!

Документ "{document_name}" приближается к нарушению SLA.

Детали:
- Тип документа: {document_type}
- Время в обработке: {processing_time}
- Оставшееся время: {remaining_time}
- Ответственный: {responsible_person}

Требуется срочное внимание!

С уважением,
Система управления документами""",
            },
            "sla_violation": {
                "subject": "КРИТИЧНО: Нарушение SLA - {document_name}",
                "body": """КРИТИЧЕСКОЕ УВЕДОМЛЕНИЕ!

Документ "{document_name}" нарушил SLA.

Детали:
- Тип документа: {document_type}
- Время просрочки: {overdue_time}
- Ответственный: {responsible_person}
- Эскалация: {escalation_level}

Требуется немедленное вмешательство!

С уважением,
Система управления документами""",
            },
            "task_assigned": {
                "subject": "Назначена новая задача: {task_title}",
                "body": """Уважаемый {assignee_name},

Вам назначена новая задача.

Детали задачи:
- Название: {task_title}
- Описание: {task_description}
- Срок выполнения: {deadline}
- Приоритет: {priority}

Ссылка на задачу: {task_url}

С уважением,
Система управления задачами""",
            },
            "supplier_notification": {
                "subject": "Обновление по вашему предложению: {proposal_id}",
                "body": """Уважаемый {supplier_name},

Информируем вас об обновлении статуса вашего коммерческого предложения.

Детали:
- ID предложения: {proposal_id}
- Новый статус: {new_status}
- Дата обновления: {update_date}
- Комментарии: {comments}

{additional_info}

С уважением,
Отдел закупок""",
            },
        }

    def _load_escalation_rules(self):
        """Загружает правила эскалации."""
        self.escalation_rules = [
            {
                "name": "standard_document_processing",
                "document_types": ["коммерческое предложение", "спецификация"],
                "warning_hours": 24,
                "escalation_hours": 48,
                "escalation_levels": [
                    {"level": 1, "recipients": ["manager@company.com"], "hours": 48},
                    {"level": 2, "recipients": ["director@company.com"], "hours": 72},
                    {"level": 3, "recipients": ["ceo@company.com"], "hours": 96},
                ],
            },
            {
                "name": "contract_processing",
                "document_types": ["договор"],
                "warning_hours": 12,
                "escalation_hours": 24,
                "escalation_levels": [
                    {"level": 1, "recipients": ["legal@company.com"], "hours": 24},
                    {
                        "level": 2,
                        "recipients": ["legal_director@company.com"],
                        "hours": 48,
                    },
                ],
            },
            {
                "name": "urgent_processing",
                "document_types": ["счет", "накладная"],
                "warning_hours": 4,
                "escalation_hours": 8,
                "escalation_levels": [
                    {"level": 1, "recipients": ["accounting@company.com"], "hours": 8},
                    {
                        "level": 2,
                        "recipients": ["finance_director@company.com"],
                        "hours": 16,
                    },
                ],
            },
        ]

    async def execute_action(
        self,
        action_type: str,
        parameters: dict[str, Any],
        context: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Выполняет автоматическое действие."""

        if action_type not in self.action_handlers:
            raise ValueError(f"Неизвестный тип действия: {action_type}")

        handler = self.action_handlers[action_type]

        try:
            self.logger.info(
                f"Выполнение действия {action_type} с параметрами: {parameters}"
            )
            result = await handler(parameters, context or {})
            self.logger.info(f"Действие {action_type} выполнено успешно")
            return result

        except Exception as e:
            self.logger.error(f"Ошибка выполнения действия {action_type}: {e}")
            raise

    async def send_email_action(
        self, parameters: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """Отправляет email уведомление."""

        template_name = parameters.get("template")
        recipient = parameters.get("recipient")
        custom_subject = parameters.get("subject")
        custom_body = parameters.get("body")

        if template_name and template_name in self.notification_templates:
            template = self.notification_templates[template_name]
            subject = template["subject"].format(**parameters, **context)
            body = template["body"].format(**parameters, **context)
        else:
            subject = custom_subject or "Уведомление от системы"
            body = custom_body or "Автоматическое уведомление"

        email_request = EmailRequest(
            recipient=recipient,
            subject=subject,
            body=body,
            pdf_path=parameters.get("pdf_path"),
        )

        # Отправляем email через существующий модуль
        await send_email(email_request)

        return {"email_sent": True, "recipient": recipient, "subject": subject}

    async def create_task_action(
        self, parameters: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """Создает задачу в Bitrix24."""

        title = parameters.get("title", "Автоматически созданная задача")
        description = parameters.get("description", "")
        responsible_id = parameters.get("responsible_id")
        deadline_hours = parameters.get("deadline_hours", 24)

        # Вычисляем срок выполнения
        deadline = datetime.now() + timedelta(hours=deadline_hours)

        # Форматируем описание с контекстом
        if context:
            description += (
                f"\n\nКонтекст:\n{json.dumps(context, ensure_ascii=False, indent=2)}"
            )

        task_request = BitrixTaskRequest(
            title=title.format(**parameters, **context),
            description=description.format(**parameters, **context),
            responsible_id=responsible_id,
            deadline=deadline,
        )

        # Создаем задачу через существующий модуль
        task_id = await create_task(task_request)

        return {
            "task_created": True,
            "task_id": task_id,
            "title": task_request.title,
            "deadline": deadline.isoformat(),
        }

    async def update_status_action(
        self, parameters: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """Обновляет статус документа."""

        document_id = parameters.get("document_id")
        new_status = parameters.get("status")
        reason = parameters.get("reason", "Автоматическое обновление")

        # Здесь будет интеграция с базой данных для обновления статуса
        self.logger.info(f"Обновление статуса документа {document_id} на {new_status}")

        return {
            "status_updated": True,
            "document_id": document_id,
            "new_status": new_status,
            "updated_at": datetime.now().isoformat(),
            "reason": reason,
        }

    async def generate_report_action(
        self, parameters: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """Генерирует отчет по документу."""

        document_id = parameters.get("document_id")
        report_type = parameters.get("report_type", "standard")
        output_path = parameters.get("output_path")

        # Здесь будет интеграция с report_generator.py
        self.logger.info(f"Генерация отчета {report_type} для документа {document_id}")

        # Пример генерации отчета
        if output_path:
            report_path = output_path
        else:
            report_path = f"reports/report_{document_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        return {
            "report_generated": True,
            "document_id": document_id,
            "report_type": report_type,
            "report_path": report_path,
            "generated_at": datetime.now().isoformat(),
        }

    async def escalate_action(
        self, parameters: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """Выполняет эскалацию."""

        document_id = parameters.get("document_id")
        document_type = parameters.get("document_type")
        escalation_level = parameters.get("level", 1)
        reason = parameters.get("reason", "Превышение SLA")

        # Находим подходящее правило эскалации
        escalation_rule = self._find_escalation_rule(document_type)

        if escalation_rule and escalation_level <= len(
            escalation_rule["escalation_levels"]
        ):
            level_config = escalation_rule["escalation_levels"][escalation_level - 1]
            recipients = level_config["recipients"]

            # Отправляем уведомления о эскалации
            for recipient in recipients:
                await self.send_email_action(
                    {
                        "template": "sla_violation",
                        "recipient": recipient,
                        "document_name": context.get("document_name", document_id),
                        "document_type": document_type,
                        "overdue_time": parameters.get("overdue_time", "Неизвестно"),
                        "responsible_person": context.get(
                            "responsible_person", "Неизвестно"
                        ),
                        "escalation_level": escalation_level,
                    },
                    context,
                )

        return {
            "escalated": True,
            "document_id": document_id,
            "escalation_level": escalation_level,
            "reason": reason,
            "escalated_at": datetime.now().isoformat(),
        }

    async def approve_document_action(
        self, parameters: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """Одобряет документ."""

        document_id = parameters.get("document_id")
        approver_name = parameters.get("approver_name", "Система")
        comments = parameters.get("comments", "")

        # Обновляем статус документа
        await self.update_status_action(
            {
                "document_id": document_id,
                "status": "одобрен",
                "reason": f"Одобрено пользователем {approver_name}",
            },
            context,
        )

        # Отправляем уведомление об одобрении
        if parameters.get("notify_supplier"):
            await self.send_email_action(
                {
                    "template": "document_approved",
                    "recipient": parameters.get("supplier_email"),
                    "document_name": context.get("document_name", document_id),
                    "document_type": context.get("document_type", "документ"),
                    "approval_date": datetime.now().strftime("%d.%m.%Y %H:%M"),
                    "approver_name": approver_name,
                    "next_steps": parameters.get(
                        "next_steps", "Ожидайте дальнейших инструкций"
                    ),
                },
                context,
            )

        return {
            "approved": True,
            "document_id": document_id,
            "approver": approver_name,
            "approved_at": datetime.now().isoformat(),
            "comments": comments,
        }

    async def reject_document_action(
        self, parameters: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """Отклоняет документ."""

        document_id = parameters.get("document_id")
        rejector_name = parameters.get("rejector_name", "Система")
        rejection_reason = parameters.get("rejection_reason", "Не указана")

        # Обновляем статус документа
        await self.update_status_action(
            {
                "document_id": document_id,
                "status": "отклонен",
                "reason": f"Отклонено пользователем {rejector_name}: {rejection_reason}",
            },
            context,
        )

        # Отправляем уведомление об отклонении
        if parameters.get("notify_supplier"):
            await self.send_email_action(
                {
                    "template": "document_rejected",
                    "recipient": parameters.get("supplier_email"),
                    "document_name": context.get("document_name", document_id),
                    "document_type": context.get("document_type", "документ"),
                    "rejection_date": datetime.now().strftime("%d.%m.%Y %H:%M"),
                    "rejector_name": rejector_name,
                    "rejection_reason": rejection_reason,
                },
                context,
            )

        return {
            "rejected": True,
            "document_id": document_id,
            "rejector": rejector_name,
            "rejected_at": datetime.now().isoformat(),
            "rejection_reason": rejection_reason,
        }

    async def notify_supplier_action(
        self, parameters: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """Отправляет уведомление поставщику."""

        supplier_email = parameters.get("supplier_email")
        supplier_name = parameters.get("supplier_name", "Уважаемый партнер")
        proposal_id = parameters.get("proposal_id")
        new_status = parameters.get("new_status")
        comments = parameters.get("comments", "")
        additional_info = parameters.get("additional_info", "")

        await self.send_email_action(
            {
                "template": "supplier_notification",
                "recipient": supplier_email,
                "supplier_name": supplier_name,
                "proposal_id": proposal_id,
                "new_status": new_status,
                "update_date": datetime.now().strftime("%d.%m.%Y %H:%M"),
                "comments": comments,
                "additional_info": additional_info,
            },
            context,
        )

        return {
            "supplier_notified": True,
            "supplier_email": supplier_email,
            "proposal_id": proposal_id,
            "notified_at": datetime.now().isoformat(),
        }

    async def create_order_action(
        self, parameters: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """Создает заказ на основе одобренного предложения."""

        proposal_id = parameters.get("proposal_id")
        supplier_id = parameters.get("supplier_id")
        order_items = parameters.get("order_items", [])
        delivery_date = parameters.get("delivery_date")

        # Здесь будет интеграция с системой заказов
        order_id = f"ORD_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        self.logger.info(
            f"Создание заказа {order_id} на основе предложения {proposal_id}"
        )

        # Создаем задачу для обработки заказа
        await self.create_task_action(
            {
                "title": f"Обработка заказа {order_id}",
                "description": f"Создан автоматический заказ на основе предложения {proposal_id}",
                "responsible_id": parameters.get("responsible_id"),
                "deadline_hours": 48,
            },
            context,
        )

        return {
            "order_created": True,
            "order_id": order_id,
            "proposal_id": proposal_id,
            "supplier_id": supplier_id,
            "created_at": datetime.now().isoformat(),
        }

    async def schedule_meeting_action(
        self, parameters: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """Планирует встречу или звонок."""

        meeting_type = parameters.get("meeting_type", "звонок")
        participants = parameters.get("participants", [])
        subject = parameters.get("subject", "Обсуждение предложения")
        duration_minutes = parameters.get("duration_minutes", 30)

        # Здесь будет интеграция с календарем
        meeting_id = f"MEET_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Создаем задачу для организации встречи
        await self.create_task_action(
            {
                "title": f"Организовать {meeting_type}: {subject}",
                "description": f'Участники: {", ".join(participants)}\nДлительность: {duration_minutes} мин',
                "responsible_id": parameters.get("organizer_id"),
                "deadline_hours": 24,
            },
            context,
        )

        return {
            "meeting_scheduled": True,
            "meeting_id": meeting_id,
            "meeting_type": meeting_type,
            "participants": participants,
            "scheduled_at": datetime.now().isoformat(),
        }

    async def send_contract_action(
        self, parameters: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """Отправляет договор на подпись."""

        contract_id = parameters.get("contract_id")
        supplier_email = parameters.get("supplier_email")
        contract_path = parameters.get("contract_path")

        # Отправляем договор по email
        await self.send_email_action(
            {
                "recipient": supplier_email,
                "subject": f"Договор для подписания: {contract_id}",
                "body": f"""Уважаемый партнер,

Направляем вам договор {contract_id} для ознакомления и подписания.

Пожалуйста, ознакомьтесь с условиями и направьте подписанный экземпляр в течение 3 рабочих дней.

С уважением,
Юридический отдел""",
                "pdf_path": contract_path,
            },
            context,
        )

        # Создаем задачу для отслеживания подписания
        await self.create_task_action(
            {
                "title": f"Отслеживание подписания договора {contract_id}",
                "description": f"Договор отправлен поставщику {supplier_email}",
                "responsible_id": parameters.get("responsible_id"),
                "deadline_hours": 72,
            },
            context,
        )

        return {
            "contract_sent": True,
            "contract_id": contract_id,
            "supplier_email": supplier_email,
            "sent_at": datetime.now().isoformat(),
        }

    async def archive_document_action(
        self, parameters: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """Архивирует документ."""

        document_id = parameters.get("document_id")
        archive_reason = parameters.get("reason", "Завершение обработки")

        # Здесь будет интеграция с системой архивирования
        archive_path = (
            f"archive/{datetime.now().year}/{datetime.now().month}/{document_id}"
        )

        self.logger.info(f"Архивирование документа {document_id} в {archive_path}")

        return {
            "document_archived": True,
            "document_id": document_id,
            "archive_path": archive_path,
            "archive_reason": archive_reason,
            "archived_at": datetime.now().isoformat(),
        }

    def _find_escalation_rule(self, document_type: str) -> Optional[dict[str, Any]]:
        """Находит правило эскалации для типа документа."""
        for rule in self.escalation_rules:
            if document_type in rule["document_types"]:
                return rule
        return None

    async def check_sla_violations(self) -> list[dict[str, Any]]:
        """Проверяет нарушения SLA и запускает эскалации."""
        violations = []

        # Здесь будет интеграция с базой данных для получения активных документов
        # Пример логики проверки SLA

        self.logger.info("Проверка нарушений SLA")

        # Возвращаем список нарушений для дальнейшей обработки
        return violations

    async def process_scheduled_actions(self) -> list[dict[str, Any]]:
        """Обрабатывает запланированные действия."""
        processed_actions = []

        # Здесь будет логика обработки запланированных действий
        self.logger.info("Обработка запланированных действий")

        return processed_actions

    def register_custom_action(self, action_type: str, handler: Callable):
        """Регистрирует пользовательский обработчик действия."""
        self.action_handlers[action_type] = handler
        self.logger.info(f"Зарегистрирован пользовательский обработчик: {action_type}")

    def add_notification_template(self, template_name: str, subject: str, body: str):
        """Добавляет новый шаблон уведомления."""
        self.notification_templates[template_name] = {"subject": subject, "body": body}
        self.logger.info(f"Добавлен шаблон уведомления: {template_name}")

    def add_escalation_rule(self, rule: dict[str, Any]):
        """Добавляет новое правило эскалации."""
        self.escalation_rules.append(rule)
        self.logger.info(f"Добавлено правило эскалации: {rule['name']}")


# Глобальный экземпляр исполнителя автоматических действий
auto_action_executor = AutoActionExecutor()


# Функции для интеграции с workflow_engine
async def execute_workflow_action(
    action_type: str,
    parameters: dict[str, Any],
    context: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Выполняет действие workflow через автоматический исполнитель."""
    return await auto_action_executor.execute_action(action_type, parameters, context)


async def schedule_sla_check():
    """Запускает периодическую проверку SLA."""
    while True:
        try:
            violations = await auto_action_executor.check_sla_violations()
            if violations:
                logging.info(f"Обнаружено {len(violations)} нарушений SLA")

                for violation in violations:
                    await auto_action_executor.execute_action(
                        "escalate", violation, {"check_type": "sla_monitoring"}
                    )

            # Проверяем каждые 30 минут
            await asyncio.sleep(1800)

        except Exception as e:
            logging.error(f"Ошибка при проверке SLA: {e}")
            await asyncio.sleep(300)  # Повторяем через 5 минут при ошибке


async def schedule_action_processor():
    """Запускает периодическую обработку запланированных действий."""
    while True:
        try:
            processed = await auto_action_executor.process_scheduled_actions()
            if processed:
                logging.info(f"Обработано {len(processed)} запланированных действий")

            # Обрабатываем каждые 5 минут
            await asyncio.sleep(300)

        except Exception as e:
            logging.error(f"Ошибка при обработке запланированных действий: {e}")
            await asyncio.sleep(60)  # Повторяем через минуту при ошибке
